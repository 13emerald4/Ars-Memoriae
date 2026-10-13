"""Note -> card materialization (Anki-style note/card separation, §2)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Card, Deck, Note, NoteType, User
from app.services.rendering import slots_for


async def default_note_type(
    db: AsyncSession,
    user: User,
    template_kind: str,
    grading_profile: str = "short_answer",
) -> NoteType:
    nt = await db.scalar(
        select(NoteType).where(
            NoteType.user_id == user.id,
            NoteType.template_kind == template_kind,
            NoteType.grading_profile == grading_profile,
        )
    )
    if nt is None:
        fields = (
            {"fields": ["Text", "Extra"]}
            if template_kind == "cloze"
            else {"fields": ["Front", "Back"]}
        )
        name = "Code Exercise" if grading_profile == "math_code" else template_kind.replace("_", " ").title()
        nt = NoteType(
            user_id=user.id,
            name=name,
            template_kind=template_kind,
            grading_profile=grading_profile,
            fields=fields,
        )
        db.add(nt)
        await db.flush()
    return nt


async def sync_cards(
    db: AsyncSession,
    note: Note,
    note_type: NoteType,
    deck_id: uuid.UUID,
    *,
    tags: list[str] | None = None,
    priority: int | None = None,
    origin: str = "manual",
    origin_extract_id: uuid.UUID | None = None,
    documentation: str | None = None,
    thematic_nature: str | None = None,
    source_documents: list | None = None,
) -> list[Card]:
    """Create the cards a note implies, and retire cards whose slot vanished.

    Editing a cloze note to drop ``{{c3::…}}`` should not leave a c3 card
    scheduled forever; but a card with review history is suspended rather than
    deleted so the history survives (it still exports, and still feeds the
    optimizer).
    """
    wanted = slots_for(note_type.template_kind, note.field_values or {})
    existing = {
        c.template_slot: c
        for c in (await db.scalars(select(Card).where(Card.note_id == note.id))).all()
    }

    # If documentation/thematic_nature/source_documents are not provided, inherit from deck
    if documentation is None and thematic_nature is None and source_documents is None:
        deck = await db.get(Deck, deck_id)
        if deck:
            documentation = deck.documentation
            thematic_nature = deck.thematic_nature
            source_documents = list(deck.source_documents or [])

    cards: list[Card] = []
    for slot in wanted:
        card = existing.get(slot)
        if card is None:
            card = Card(
                note_id=note.id,
                deck_id=deck_id,
                template_slot=slot,
                priority=priority,
                origin=origin,
                origin_extract_id=origin_extract_id,
                tags=list(tags or []),
                documentation=documentation,
                thematic_nature=thematic_nature,
                source_documents=list(source_documents or []),
            )
            db.add(card)
        else:
            card.suspended = False
            if tags is not None:
                card.tags = list(tags)
            if priority is not None:
                card.priority = priority
            if documentation is not None:
                card.documentation = documentation
            if thematic_nature is not None:
                card.thematic_nature = thematic_nature
            if source_documents is not None:
                card.source_documents = list(source_documents)
        cards.append(card)

    for slot, card in existing.items():
        if slot not in wanted:
            card.suspended = True

    await db.flush()
    return cards
