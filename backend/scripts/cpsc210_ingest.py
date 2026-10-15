"""Shared card-ingest helper for the CPSC 210 deck scripts.

Extracted from the nested ``ingest_notes_list`` in ``populate_cpsc210.py`` so that
``populate_cpsc210.py`` and ``build_mt3_decks.py`` create notes, cards and citations the
same way. One addition: ingestion is idempotent per deck. A note whose Front already exists
in the target deck is skipped, so re-running a script never duplicates cards.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy import select

from app.models import Card, CardReference, Deck, Note, User
from app.services.note_service import default_note_type, sync_cards

logger = logging.getLogger(__name__)


@dataclass
class IngestResult:
    notes: int = 0
    cards: int = 0
    citations: int = 0
    skipped: int = 0
    created_card_ids: list = field(default_factory=list)


async def all_user_fronts(db, user: User) -> set[str]:
    """Front texts of every note the user owns."""
    rows = await db.execute(select(Note.field_values).where(Note.user_id == user.id))
    return {str((fv or {}).get("Front", "")).strip() for (fv,) in rows.all()}


async def existing_fronts(db, deck: Deck) -> set[str]:
    """Front texts of every note that already has a card in ``deck``."""
    rows = await db.execute(
        select(Note.field_values).join(Card, Card.note_id == Note.id).where(Card.deck_id == deck.id)
    )
    return {str((fv or {}).get("Front", "")).strip() for (fv,) in rows.all()}


def _is_code(item: dict) -> bool:
    return (
        item.get("card_type") == "code"
        or bool(item.get("starter_code"))
        or bool(item.get("test_cases"))
    )


async def ingest_notes_list(
    db,
    user: User,
    notes_raw: list[dict],
    target_deck: Deck,
    source_label: str,
    *,
    default_priority: int | None = None,
    extra_tags: list[str] | None = None,
    dry_run: bool = False,
    seen_fronts: set[str] | None = None,
) -> IngestResult:
    """Create one note (and its card) per item in ``notes_raw`` inside ``target_deck``.

    Items use the CPSC 210 card JSON format: front, back, quote, locator, tags, and for code
    cards starter_code / test_cases / title / category / difficulty / complexity fields.
    """
    result = IngestResult()
    # By default a note is skipped when its Front is already in the target deck. Pass
    # ``seen_fronts`` to widen that check (populate_cpsc210 passes every Front the user has,
    # because cleanup may have moved cards out of the deck they were first imported into).
    seen = seen_fronts if seen_fronts is not None else await existing_fronts(db, target_deck)

    for item in notes_raw:
        front = (item.get("front") or "").strip()
        back = (item.get("back") or "").strip()
        if not front or not back:
            continue
        if front in seen:
            result.skipped += 1
            continue
        seen.add(front)
        if dry_run:
            result.notes += 1
            result.cards += 1
            continue

        is_code = _is_code(item)
        quote = (item.get("quote") or "").strip()
        locator = (item.get("locator") or "").strip()

        field_values: dict = {"Front": front, "Back": back}
        if is_code:
            for k in ("starter_code", "test_cases", "title", "category", "difficulty",
                      "time_complexity", "space_complexity", "edge_cases"):
                if item.get(k):
                    field_values[k] = item[k]

        profile = "math_code" if is_code else "short_answer"
        nt = await default_note_type(db, user, "basic", grading_profile=profile)
        note_row = Note(user_id=user.id, note_type_id=nt.id, field_values=field_values)
        db.add(note_row)
        await db.flush()

        tags = list(item.get("tags") or [])
        for t in [*(extra_tags or []), *(["code"] if is_code else []), "cpsc210"]:
            if t not in tags:
                tags.append(t)
        name = target_deck.name.removeprefix("! ")
        if name.startswith("Ch "):
            ch_tag = "ch" + name.split(":")[0].replace("Ch ", "").strip()
            if ch_tag not in tags:
                tags.append(ch_tag)

        doc_parts = []
        if locator:
            doc_parts.append(f"**Locator**: {locator}")
        if quote:
            doc_parts.append(f'**Key Quote**: "{quote}"')
        if item.get("time_complexity") or item.get("space_complexity"):
            doc_parts.append(
                f"**Complexity**: Time `{item.get('time_complexity', 'N/A')}`, "
                f"Space `{item.get('space_complexity', 'N/A')}`"
            )
        if item.get("edge_cases"):
            doc_parts.append("**Edge Cases**: " + ", ".join(item["edge_cases"]))
        card_documentation = "\n\n".join(doc_parts) if doc_parts else target_deck.documentation

        priority = item.get("priority", default_priority)
        cards = await sync_cards(
            db,
            note_row,
            nt,
            target_deck.id,
            tags=tags,
            priority=priority,
            origin="manual",
            documentation=card_documentation,
            thematic_nature=item.get("category") or target_deck.thematic_nature,
            source_documents=[{
                "name": "CPSC210_2026W1_Master.pdf",
                "locator": locator,
                "quote": quote,
                "source_file": source_label,
            }],
        )
        result.notes += 1
        result.cards += len(cards)
        result.created_card_ids.extend(c.id for c in cards)

        if quote or locator:
            for c in cards:
                db.add(CardReference(
                    card_id=c.id,
                    quote=quote or (f"Excerpt from {locator}" if locator else ""),
                    quote_verified=True,
                    locator=locator,
                    source_title=f"CPSC 210 — {name}",
                ))
                result.citations += 1

    return result
