"""Incremental Reading endpoints (§7, §8)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Card, Deck, Extract, KnowledgeNode, Note, Source, User
from app.routers.deps import current_user, parse_uuid
from app.schemas.core import (
    AcceptCardsRequest,
    ExtractOut,
    ExtractScheduleRequest,
    ExtractSplitRequest,
    GenerateCardsRequest,
    GenerateCardsResponse,
    SourceCreate,
    SourceOut,
    SuggestedCard,
)
from app.services import ir_service, tree_service
from app.services.grading_service import GradingService, GradingUnavailable
from app.services.note_service import default_note_type, sync_cards

router = APIRouter(prefix="/api", tags=["incremental-reading"])


async def _owned_source(db: AsyncSession, user: User, source_id: uuid.UUID) -> Source:
    source = await db.get(Source, source_id)
    if source is None or source.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "source not found")
    return source


async def _owned_extract(db: AsyncSession, user: User, extract_id: uuid.UUID) -> tuple[Extract, Source]:
    extract = await db.get(Extract, extract_id)
    if extract is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "extract not found")
    source = await _owned_source(db, user, extract.source_id)
    return extract, source


def _extract_out(extract: Extract, source: Source) -> ExtractOut:
    return ExtractOut(
        id=str(extract.id),
        source_id=str(extract.source_id),
        source_title=source.title,
        content=extract.content,
        priority=extract.priority if extract.priority is not None else source.priority,
        position=extract.position,
        locator=extract.locator,
        next_shown_at=extract.next_shown_at,
        status=extract.status,
    )


@router.post("/sources", response_model=SourceOut, status_code=201)
async def create_source(
    body: SourceCreate, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> SourceOut:
    """Import raw text, or a URL the server fetches and strips (§7, §8.1)."""
    title, text = body.title, body.raw_text

    if body.url and not text:
        try:
            fetched_title, text = await ir_service.fetch_url(body.url)
        except ir_service.FetchError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"could not fetch URL: {exc}") from exc
        title = title or fetched_title

    if not text or not text.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "supply raw_text or a fetchable url")

    parent_node_id = None
    if body.parent_node_id:
        node = await db.get(KnowledgeNode, parse_uuid(body.parent_node_id, "parent_node_id"))
        if node is None or node.user_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "parent node not found")
        parent_node_id = node.id

    target_title = title or text.strip().split("\n", 1)[0][:120] or "Untitled"
    if body.url:
        existing = await db.scalar(
            select(Source).where(Source.user_id == user.id, Source.url == body.url)
        )
        if existing:
            total, active = await ir_service.source_progress(db, existing.id)
            return SourceOut(
                id=str(existing.id),
                title=existing.title,
                url=existing.url,
                priority=existing.priority,
                status=existing.status,
                created_at=existing.created_at,
                extract_count=total,
                active_extract_count=active,
                for_reading=existing.for_reading,
            )
    else:
        existing = await db.scalar(
            select(Source).where(
                Source.user_id == user.id,
                Source.title == target_title,
                Source.raw_text == text,
            )
        )
        if existing:
            total, active = await ir_service.source_progress(db, existing.id)
            return SourceOut(
                id=str(existing.id),
                title=existing.title,
                url=existing.url,
                priority=existing.priority,
                status=existing.status,
                created_at=existing.created_at,
                extract_count=total,
                active_extract_count=active,
                for_reading=existing.for_reading,
            )

    source = await ir_service.create_source(
        db,
        user.id,
        title=target_title,
        raw_text=text,
        url=body.url,
        priority=body.priority,
        parent_node_id=parent_node_id,
    )
    await db.commit()
    total, active = await ir_service.source_progress(db, source.id)
    return SourceOut(
        id=str(source.id),
        title=source.title,
        url=source.url,
        priority=source.priority,
        status=source.status,
        created_at=source.created_at,
        extract_count=total,
        active_extract_count=active,
        for_reading=source.for_reading,
    )


@router.get("/sources", response_model=list[SourceOut])
async def list_sources(
    user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> list[SourceOut]:
    sources = (
        await db.scalars(
            select(Source).where(Source.user_id == user.id).order_by(Source.created_at.desc())
        )
    ).all()
    out = []
    for s in sources:
        total, active = await ir_service.source_progress(db, s.id)
        out.append(
            SourceOut(
                id=str(s.id),
                title=s.title,
                url=s.url,
                priority=s.priority,
                status=s.status,
                created_at=s.created_at,
                extract_count=total,
                active_extract_count=active,
                for_reading=s.for_reading,
            )
        )
    return out


@router.get("/sources/{source_id}/extracts", response_model=list[ExtractOut])
async def list_extracts(
    source_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> list[ExtractOut]:
    source = await _owned_source(db, user, parse_uuid(source_id))
    rows = (
        await db.scalars(
            select(Extract).where(Extract.source_id == source.id).order_by(Extract.position)
        )
    ).all()
    return [_extract_out(e, source) for e in rows]


@router.patch("/sources/{source_id}")
async def update_source(
    source_id: str,
    status_value: str | None = None,
    priority: int | None = None,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    source = await _owned_source(db, user, parse_uuid(source_id))
    if status_value in ("active", "postponed", "done"):
        source.status = status_value
    if priority is not None:
        source.priority = max(0, min(100, priority))
    await db.commit()
    return {"id": str(source.id), "status": source.status, "priority": source.priority}


@router.delete("/sources", status_code=204)
async def delete_all_sources(
    user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> None:
    """Delete all reading sources/documents belonging to the user."""
    sources = (await db.scalars(select(Source).where(Source.user_id == user.id))).all()
    if not sources:
        return

    source_ids = [s.id for s in sources]
    extract_ids = (
        await db.scalars(select(Extract.id).where(Extract.source_id.in_(source_ids)))
    ).all()

    if extract_ids:
        for card in (
            await db.scalars(select(Card).where(Card.origin_extract_id.in_(extract_ids)))
        ).all():
            card.origin_extract_id = None

    for source in sources:
        await tree_service.detach_entity_node(db, KnowledgeNode.source_id == source.id)
        await db.delete(source)

    await db.commit()


@router.delete("/sources/{source_id}", status_code=204)
async def delete_source(
    source_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> None:
    source = await _owned_source(db, user, parse_uuid(source_id))
    # Cards carved out of this source keep their scheduling; only the reading
    # material goes away. Detach them first so the FK does not block the delete.
    extract_ids = (
        await db.scalars(select(Extract.id).where(Extract.source_id == source.id))
    ).all()
    if extract_ids:
        for card in (
            await db.scalars(select(Card).where(Card.origin_extract_id.in_(extract_ids)))
        ).all():
            card.origin_extract_id = None
    # Anything the user filed *under* this source in the tree is theirs, not the
    # source's — lift it out before the node's FK cascade takes the subtree.
    await tree_service.detach_entity_node(db, KnowledgeNode.source_id == source.id)
    await db.delete(source)
    await db.commit()


@router.get("/extracts/{extract_id}", response_model=ExtractOut)
async def get_extract(
    extract_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> ExtractOut:
    extract, source = await _owned_extract(db, user, parse_uuid(extract_id))
    return _extract_out(extract, source)


@router.delete("/extracts/{extract_id}", status_code=204)
async def delete_extract(
    extract_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> None:
    extract, _ = await _owned_extract(db, user, parse_uuid(extract_id))
    for card in (
        await db.scalars(select(Card).where(Card.origin_extract_id == extract.id))
    ).all():
        card.origin_extract_id = None
    await tree_service.detach_entity_node(db, KnowledgeNode.extract_id == extract.id)
    await db.delete(extract)
    await db.commit()


@router.post("/extracts/{extract_id}/split", response_model=ExtractOut, status_code=201)
async def split_extract(
    extract_id: str,
    body: ExtractSplitRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> ExtractOut:
    extract, source = await _owned_extract(db, user, parse_uuid(extract_id))
    try:
        child = await ir_service.split_extract(
            db,
            extract,
            text=body.text,
            start=body.start,
            end=body.end,
            priority=body.priority,
            remove_from_parent=body.remove_from_parent,
            source=source,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await ir_service.retire_if_complete(db, source)
    await db.commit()
    await db.refresh(child)
    return _extract_out(child, source)


@router.post("/extracts/{extract_id}/schedule", response_model=ExtractOut)
async def schedule_extract(
    extract_id: str,
    body: ExtractScheduleRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> ExtractOut:
    """Postpone, re-prioritise, or finish an extract (§8.4)."""
    extract, source = await _owned_extract(db, user, parse_uuid(extract_id))
    if body.priority is not None:
        extract.priority = body.priority
    if body.status == "done":
        extract.status = "done"
        extract.next_shown_at = None
    else:
        ir_service.postpone(extract, body.days, inherited_priority=source.priority)
        if body.status == "active":
            extract.status = "active"
    await ir_service.retire_if_complete(db, source)
    await db.commit()
    await db.refresh(extract)
    return _extract_out(extract, source)


@router.post("/extracts/{extract_id}/generate-cards", response_model=GenerateCardsResponse)
async def generate_cards(
    extract_id: str,
    body: GenerateCardsRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> GenerateCardsResponse:
    """LLM-assisted cloze/Q&A suggestions from a highlighted span (§7, §8.3).

    Reuses the grading connection — no new integration surface — and mirrors
    the grade-then-confirm pattern: nothing becomes a card until the user
    accepts it via /accept-cards.
    """
    extract, _ = await _owned_extract(db, user, parse_uuid(extract_id))
    passage = (body.text or extract.content).strip()
    if not passage:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "nothing to generate from")

    if not user.llm_grading_consent:
        return GenerateCardsResponse(degraded=True, reason="consent_not_given")

    target_model = body.model or user.grading_model
    try:
        raw = await GradingService(model=target_model).generate_cards(
            passage, body.max_cards, model=target_model, thinking_budget=body.thinking_budget
        )
    except GradingUnavailable as exc:
        return GenerateCardsResponse(degraded=True, reason=str(exc))

    return GenerateCardsResponse(suggestions=[SuggestedCard(**c) for c in raw])


@router.post("/extracts/{extract_id}/accept-cards", status_code=201)
async def accept_cards(
    extract_id: str,
    body: AcceptCardsRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Turn approved suggestions (or a manual highlight-to-cloze) into cards."""
    extract, source = await _owned_extract(db, user, parse_uuid(extract_id))
    deck = await db.get(Deck, parse_uuid(body.deck_id, "deck_id"))
    if deck is None or deck.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "deck not found")

    created = 0
    for suggestion in body.cards:
        if suggestion.kind == "cloze" and suggestion.cloze_text:
            nt = await default_note_type(db, user, "cloze")
            fields = {"Text": suggestion.cloze_text, "Extra": suggestion.back or ""}
        else:
            nt = await default_note_type(db, user, "basic")
            fields = {"Front": suggestion.front, "Back": suggestion.back}
        note = Note(user_id=user.id, note_type_id=nt.id, field_values=fields)
        db.add(note)
        await db.flush()
        cards = await sync_cards(
            db,
            note,
            nt,
            deck.id,
            priority=body.priority if body.priority is not None else extract.priority,
            origin="extract",
            origin_extract_id=extract.id,
            tags=["ir", source.title[:40]],
        )
        created += len(cards)

    # Working an extract into cards is progress: shed priority and resurface later.
    ir_service.postpone(extract, inherited_priority=source.priority)
    await db.commit()
    return {"cards_created": created, "extract_id": str(extract.id)}


@router.get("/extracts")
async def due_extracts(
    user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> list[ExtractOut]:
    now = datetime.now(UTC)
    rows = await db.execute(
        select(Extract, Source)
        .join(Source, Source.id == Extract.source_id)
        .where(Source.user_id == user.id, Source.for_reading.is_(True), Extract.status == "active")
        .order_by(Extract.next_shown_at.is_(None), Extract.next_shown_at)
        .limit(100)
    )

    def due(extract: Extract) -> bool:
        # SQLite hands back naive datetimes even for timezone-aware columns
        # (see the models docstring on dialect portability), so comparing one
        # straight against an aware `now` raises. Same normalisation as
        # queue_service._aware.
        shown_at = extract.next_shown_at
        if shown_at is None:
            return True
        return (shown_at if shown_at.tzinfo else shown_at.replace(tzinfo=UTC)) <= now

    return [_extract_out(e, s) for e, s in rows.all() if due(e)]
