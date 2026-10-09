"""POST /api/import/json, GET /api/import/history (§11)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import (
    CardReference,
    Deck,
    Import,
    Note,
    User,
)
from app.routers.deps import current_user
from app.schemas.core import JsonImportNote, JsonImportRequest, JsonImportResult
from app.services.note_service import default_note_type, sync_cards

router = APIRouter(prefix="/api/import", tags=["import"])


@router.post("/json", response_model=JsonImportResult, status_code=201)
async def import_json(
    body: JsonImportRequest | list[JsonImportNote],
    deck: str | None = Query(
        default=None, max_length=200, description="Deck name — required when the body is a bare array"
    ),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> JsonImportResult:
    """Bulk-create notes/cards from a JSON payload.

    Accepts either ``{"deck": "...", "notes": [...]}`` or a bare array of
    notes with the deck name given as ``?deck=`` — a plain array is what most
    scripted/LLM flashcard exports actually look like, and there's no reason
    to make every caller hand-wrap one in an envelope first.

    One request targets one deck (created if it doesn't already exist by
    name). A malformed row is skipped and reported in ``warnings`` rather than
    failing the whole batch: a hand-edited JSON file is exactly the case where
    one bad entry in five hundred shouldn't cost you the other 499.

    A note carrying ``quote`` gets a :class:`CardReference` too, which is what
    Learn & Practice needs to teach from. There's no uploaded document behind
    this path to verify the quote against, so it's trusted as given rather
    than checked — the same way ``accept-deck`` trusts an already-verified
    quote.
    """
    if isinstance(body, list):
        deck_name = (deck or "").strip()
        if not deck_name:
            for n in body:
                d = getattr(n, "deck", None)
                if d and d.strip():
                    deck_name = d.strip()
                    break
        if not deck_name:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "a bare array of notes needs a deck name — pass ?deck=<name> or include 'deck' in note objects",
            )
        notes, deck_priority = body, None
    else:
        deck_name, notes, deck_priority = body.deck, body.notes, body.priority

    # `JsonImportRequest.notes` already enforces this via Field(), but a bare
    # array bypasses that schema entirely, so it's checked again here.
    if not notes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "at least one note is required")
    if len(notes) > 5000:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "at most 5000 notes per import")

    existing = await db.scalar(select(Deck).where(Deck.user_id == user.id, Deck.name == deck_name))
    deck_created = existing is None
    deck_row = existing or Deck(
        user_id=user.id, name=deck_name, default_priority=deck_priority if deck_priority is not None else 50
    )
    if deck_created:
        db.add(deck_row)
        await db.flush()

    warnings: list[str] = []
    notes_created = 0
    cards_created = 0
    citations_created = 0

    for i, item in enumerate(notes):
        is_cloze = item.kind == "cloze"
        is_code = (
            item.kind == "code"
            or getattr(item, "card_type", None) == "code"
            or bool(item.starter_code)
            or bool(item.starter_tests)
        )
        if is_cloze:
            if not (item.cloze_text or "").strip():
                warnings.append(f"note {i}: kind is \"cloze\" but cloze_text is empty — skipped")
                continue
            field_values = {"Text": item.cloze_text, "Extra": item.back or ""}
        else:
            if not (item.front or "").strip() or not (item.back or "").strip():
                warnings.append(f"note {i}: front and back are both required — skipped")
                continue
            field_values = {"Front": item.front, "Back": item.back}
            if is_code:
                if item.starter_code:
                    field_values["starter_code"] = item.starter_code
                if item.starter_tests:
                    field_values["starter_tests"] = item.starter_tests
                if item.test_cases:
                    field_values["test_cases"] = item.test_cases
                if item.time_complexity:
                    field_values["time_complexity"] = item.time_complexity
                if item.space_complexity:
                    field_values["space_complexity"] = item.space_complexity
                if item.edge_cases:
                    field_values["edge_cases"] = item.edge_cases
                if item.title:
                    field_values["title"] = item.title
                if item.difficulty:
                    field_values["difficulty"] = item.difficulty
                if item.category:
                    field_values["category"] = item.category

        profile = "math_code" if is_code else "short_answer"
        nt = await default_note_type(db, user, "cloze" if is_cloze else "basic", grading_profile=profile)
        note = Note(user_id=user.id, note_type_id=nt.id, field_values=field_values)
        db.add(note)
        await db.flush()

        tags = list(item.tags)
        if is_code:
            if "code" not in tags:
                tags.append("code")
            if item.difficulty and item.difficulty not in tags:
                tags.append(item.difficulty)
            if item.category and item.category not in tags:
                tags.append(item.category)

        cards = await sync_cards(
            db, note, nt, deck_row.id, tags=tags, priority=item.priority, origin="manual"
        )
        notes_created += 1
        cards_created += len(cards)

        quote = (item.quote or "").strip()
        if quote:
            for card in cards:
                db.add(
                    CardReference(
                        card_id=card.id,
                        quote=quote,
                        # Nothing here was extracted from a document we can
                        # check against, so there's no hallucination risk to
                        # flag — the caller supplied this text directly.
                        quote_verified=True,
                        locator=item.locator,
                        source_title=item.source_title,
                    )
                )
                citations_created += 1

    record = Import(
        user_id=user.id,
        filename=f"json:{deck_name}",
        notes_mapped=notes_created,
        cards_mapped=cards_created,
        warnings=warnings,
    )
    db.add(record)
    await db.commit()

    return JsonImportResult(
        deck_id=str(deck_row.id),
        deck_created=deck_created,
        notes_created=notes_created,
        cards_created=cards_created,
        citations_created=citations_created,
        warnings=warnings,
    )


@router.get("/history")
async def import_history(
    user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> list[dict]:
    rows = (
        await db.scalars(
            select(Import).where(Import.user_id == user.id).order_by(Import.imported_at.desc())
        )
    ).all()
    return [
        {
            "id": str(r.id),
            "filename": r.filename,
            "imported_at": r.imported_at,
            "notes_mapped": r.notes_mapped,
            "cards_mapped": r.cards_mapped,
            "warnings": r.warnings or [],
        }
        for r in rows
    ]
