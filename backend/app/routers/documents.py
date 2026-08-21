"""Upload a document, generate a deck from it, keep the citations.

The chain is: upload -> the document becomes an IR source whose extracts each
remember their page/heading -> the model proposes cards, each quoting the span
it used -> the user approves -> cards are created with those citations
attached, so review can show the reading behind the answer.

Generation is deliberately a *proposal*: nothing is written until
``/accept-deck``, matching how grading and IR card generation already work.
Approving LLM output before it becomes durable is the pattern this app is
built around, and bulk-generating a hundred cards is the last place to break
it.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_api_key
from app.db import get_db
from app.models import CardReference, Deck, Extract, KnowledgeNode, Note, Source, User
from app.routers.deps import current_user, parse_uuid
from app.schemas.documents import (
    AcceptDeckRequest,
    AcceptDeckResponse,
    CitedCard,
    DocumentOut,
    GenerateDeckRequest,
    GenerateDeckResponse,
)
from app.services import document_service, ir_service, tree_service
from app.services.document_service import DocumentError
from app.services.grading_service import GradingService, GradingUnavailable
from app.services.note_service import default_note_type, sync_cards

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])

# Sections are generated concurrently, but capped to 2 to prevent free-tier
# Gemini rate spikes (503/429) on large document chunks.
GENERATION_CONCURRENCY = 2


async def _owned_source(db: AsyncSession, user: User, source_id: uuid.UUID) -> Source:
    source = await db.get(Source, source_id)
    if source is None or source.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "document not found")
    return source


@router.post("", response_model=DocumentOut, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    parent_node_id: str | None = Form(default=None),
    priority: int = Form(default=50),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentOut:
    """Ingest a document as reading material with citable segments."""
    if not document_service.supported(file.filename or ""):
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"unsupported file type; upload one of: "
            f"{', '.join(document_service.SUPPORTED_SUFFIXES)}",
        )

    data = b""
    while chunk := await file.read(1 << 20):
        data += chunk
        if len(data) > document_service.MAX_DOCUMENT_BYTES:
            raise HTTPException(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                f"file exceeds {document_service.MAX_DOCUMENT_BYTES // (1024 * 1024)} MB",
            )

    try:
        # Parsing a large PDF is CPU-bound; keep it off the event loop.
        parsed_title, segments = await asyncio.to_thread(
            document_service.extract_document, file.filename or "document", data
        )
    except DocumentError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    node_id = None
    if parent_node_id:
        node = await db.get(KnowledgeNode, parse_uuid(parent_node_id, "parent_node_id"))
        if node is None or node.user_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "parent node not found")
        node_id = node.id

    target_title = (title or "").strip() or parsed_title
    raw_text = "\n\n".join(s.text for s in segments)

    # Check for exact identical source for this user to prevent duplicate tree nodes
    existing_source = await db.scalar(
        select(Source).where(
            Source.user_id == user.id,
            Source.title == target_title,
            Source.raw_text == raw_text,
        )
    )
    if existing_source is not None:
        source_node = await db.scalar(
            select(KnowledgeNode).where(KnowledgeNode.source_id == existing_source.id)
        )
        return DocumentOut(
            source_id=str(existing_source.id),
            title=existing_source.title,
            segment_count=len(segments),
            locators=_distinct_locators([s.locator for s in segments]),
            node_id=str(source_node.id) if source_node else None,
        )

    # Clean up any un-cited draft source with the same title from previous upload attempts
    existing_draft = await db.scalar(
        select(Source).where(
            Source.user_id == user.id,
            Source.title == target_title,
            Source.for_reading.is_(False),
        )
    )
    if existing_draft is not None:
        has_citations = await db.scalar(
            select(func.count(CardReference.id))
            .join(Extract, Extract.id == CardReference.extract_id)
            .where(Extract.source_id == existing_draft.id)
        )
        if not has_citations:
            await tree_service.detach_entity_node(db, KnowledgeNode.source_id == existing_draft.id)
            await db.delete(existing_draft)
            await db.flush()

    source = await ir_service.create_source(
        db,
        user.id,
        title=target_title,
        raw_text=raw_text,
        priority=max(0, min(100, priority)),
        parent_node_id=node_id,
        segments=[(s.locator, s.text) for s in segments],
        # This document exists to generate and cite cards from — it must never
        # be auto-surfaced in Review as something to read (see Source.for_reading).
        for_reading=False,
    )
    await db.commit()

    source_node = await db.scalar(
        select(KnowledgeNode).where(KnowledgeNode.source_id == source.id)
    )
    return DocumentOut(
        source_id=str(source.id),
        title=source.title,
        segment_count=len(segments),
        locators=_distinct_locators([s.locator for s in segments]),
        node_id=str(source_node.id) if source_node else None,
    )


def _distinct_locators(locators: list[str], limit: int = 12) -> list[str]:
    seen: list[str] = []
    for loc in locators:
        if loc and loc not in seen:
            seen.append(loc)
        if len(seen) >= limit:
            break
    return seen


@router.post("/{source_id}/generate-deck", response_model=GenerateDeckResponse)
async def generate_deck(
    source_id: str,
    body: GenerateDeckRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> GenerateDeckResponse:
    """Propose cards for a slice of the document, each citing its passage.

    Returns ``degraded`` rather than an error when the key or consent is
    missing, so the caller gets the same "this is off, here's why" shape the
    grading path uses instead of a 4xx it has to special-case.
    """
    source = await _owned_source(db, user, parse_uuid(source_id))

    extracts = list(
        (
            await db.scalars(
                select(Extract)
                .where(Extract.source_id == source.id)
                .order_by(Extract.position)
            )
        ).all()
    )
    total = len(extracts)
    window = extracts[body.start_section : body.start_section + body.max_sections]

    if not user.llm_grading_consent:
        return GenerateDeckResponse(
            source_id=str(source.id), title=source.title, sections_total=total,
            degraded=True, reason="consent_not_given",
        )
    api_key = decrypt_api_key(user.google_api_key_encrypted)
    if not api_key:
        return GenerateDeckResponse(
            source_id=str(source.id), title=source.title, sections_total=total,
            degraded=True, reason="no_api_key",
        )
    if not window:
        return GenerateDeckResponse(
            source_id=str(source.id), title=source.title, sections_total=total,
            degraded=True, reason="no_sections_in_range",
        )

    service = GradingService(api_key, body.model or user.grading_model)
    semaphore = asyncio.Semaphore(GENERATION_CONCURRENCY)

    async def one(extract: Extract, idx: int) -> tuple[Extract, list[dict] | str]:
        async with semaphore:
            if idx > 0:
                await asyncio.sleep(0.4 * idx)
            try:
                return extract, await service.generate_cards_with_citations(
                    extract.content,
                    extract.locator or "",
                    body.max_cards_per_section,
                    model=body.model or user.grading_model,
                    thinking_budget=body.thinking_budget,
                )
            except GradingUnavailable as exc:
                return extract, str(exc)

    results = await asyncio.gather(*(one(e, i) for i, e in enumerate(window)))

    cards: list[CitedCard] = []
    warnings: list[str] = []
    failures = 0
    for extract, outcome in results:
        where = extract.locator or f"section {extract.position + 1}"
        if isinstance(outcome, str):
            failures += 1
            warnings.append(f"{where}: {outcome}")
            continue
        for c in outcome:
            if not c["quote_verified"] and c["quote"]:
                warnings.append(
                    f"{where}: a quote could not be found in the source text and was "
                    "dropped — the full passage is cited instead"
                )
            cards.append(
                CitedCard(
                    kind=c["kind"],
                    front=c["front"],
                    back=c["back"],
                    cloze_text=c["cloze_text"],
                    quote=c["quote"] if c["quote_verified"] else "",
                    quote_verified=c["quote_verified"],
                    locator=extract.locator,
                    extract_id=str(extract.id),
                )
            )

    next_section = body.start_section + len(window)
    return GenerateDeckResponse(
        source_id=str(source.id),
        title=source.title,
        cards=cards,
        sections_used=len(window),
        sections_total=total,
        next_section=next_section if next_section < total else None,
        # Every section failing is a real outage, not a partial result.
        degraded=failures == len(window),
        reason="generation_failed" if failures == len(window) else None,
        warnings=sorted(set(warnings))[:20],
    )


@router.post("/{source_id}/accept-deck", response_model=AcceptDeckResponse, status_code=201)
async def accept_deck(
    source_id: str,
    body: AcceptDeckRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> AcceptDeckResponse:
    """Create the approved cards, each keeping its citation into the document."""
    source = await _owned_source(db, user, parse_uuid(source_id))

    existing = await db.scalar(select(Deck).where(Deck.user_id == user.id, Deck.name == body.deck))
    deck_created = existing is None
    deck = existing or Deck(
        user_id=user.id,
        name=body.deck,
        default_priority=body.priority if body.priority is not None else 50,
    )
    if deck_created:
        db.add(deck)
        await db.flush()

    # Only extracts belonging to *this* document are citable, so a crafted
    # extract_id can't attach another user's reading to a card.
    owned_extracts = {
        e_id
        for (e_id,) in (
            await db.execute(select(Extract.id).where(Extract.source_id == source.id))
        ).all()
    }

    warnings: list[str] = []
    notes_created = 0
    cards_created = 0
    references_created = 0

    for i, item in enumerate(body.cards):
        is_cloze = item.kind == "cloze"
        if is_cloze:
            if not (item.cloze_text or "").strip():
                warnings.append(f"card {i}: cloze with no cloze_text — skipped")
                continue
            fields = {"Text": item.cloze_text, "Extra": item.back or ""}
        else:
            if not item.front.strip() or not item.back.strip():
                warnings.append(f"card {i}: front and back are both required — skipped")
                continue
            fields = {"Front": item.front, "Back": item.back}

        extract_id = None
        if item.extract_id:
            candidate = parse_uuid(item.extract_id, "extract_id")
            if candidate in owned_extracts:
                extract_id = candidate
            else:
                warnings.append(f"card {i}: citation did not belong to this document — dropped")

        nt = await default_note_type(db, user, "cloze" if is_cloze else "basic")
        note = Note(user_id=user.id, note_type_id=nt.id, field_values=fields)
        db.add(note)
        await db.flush()
        new_cards = await sync_cards(
            db,
            note,
            nt,
            deck.id,
            tags=["document", source.title[:40]],
            origin="extract" if extract_id else "manual",
            origin_extract_id=extract_id,
        )
        notes_created += 1
        cards_created += len(new_cards)

        for card in new_cards:
            db.add(
                CardReference(
                    card_id=card.id,
                    source_id=source.id,
                    extract_id=extract_id,
                    quote=item.quote if item.quote_verified else "",
                    quote_verified=item.quote_verified,
                    locator=item.locator,
                    source_title=source.title,
                )
            )
            references_created += 1

    await db.commit()
    return AcceptDeckResponse(
        deck_id=str(deck.id),
        deck_created=deck_created,
        notes_created=notes_created,
        cards_created=cards_created,
        references_created=references_created,
        warnings=warnings,
    )
