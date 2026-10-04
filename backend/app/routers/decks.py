"""Deck / note_type / note / card CRUD, plus PATCH /api/priority (§7)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Card, Deck, Extract, KnowledgeNode, Note, NoteType, Source, User
from app.routers.deps import current_user, parse_uuid
from app.schemas.core import (
    CardOut,
    DeckCreate,
    DeckOut,
    DeckStatsOut,
    DeckUpdate,
    NoteCreate,
    NoteOut,
    NoteTypeCreate,
    NoteTypeOut,
    NoteUpdate,
    PriorityUpdate,
)
from app.services import tree_service
from app.services.note_service import default_note_type, sync_cards
from app.services.rendering import occlusion_payload, render

router = APIRouter(prefix="/api", tags=["decks"])


async def _owned_deck(db: AsyncSession, user: User, deck_id: uuid.UUID) -> Deck:
    deck = await db.get(Deck, deck_id)
    if deck is None or deck.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "deck not found")
    return deck


async def _owned_card(db: AsyncSession, user: User, card_id: uuid.UUID) -> Card:
    card = await db.get(Card, card_id)
    if card is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "card not found")
    deck = await db.get(Deck, card.deck_id)
    if deck is None or deck.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "card not found")
    return card


def card_out(card: Card, deck_name: str | None = None) -> CardOut:
    front, back = render(
        card.note.note_type.template_kind, card.note.field_values or {}, card.template_slot
    )
    return CardOut(
        id=str(card.id),
        note_id=str(card.note_id),
        deck_id=str(card.deck_id),
        deck_name=deck_name or (card.deck.name if card.deck else None),
        template_slot=card.template_slot,
        state=card.state,
        due=card.due,
        stability=card.stability,
        difficulty=card.difficulty,
        priority=card.effective_priority,
        lapse_count=card.lapse_count,
        leech_flag=card.leech_flag,
        suspended=card.suspended,
        tags=list(card.tags or []),
        front=front,
        back=back,
        occlusion=occlusion_payload(card.note.field_values or {}, card.template_slot)
        if card.note.note_type.template_kind == "image_occlusion"
        else None,
    )


# ── decks ───────────────────────────────────────────────────────────────────


@router.get("/decks", response_model=list[DeckOut])
async def list_decks(
    user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> list[DeckOut]:
    now = datetime.now(UTC)
    decks = (await db.scalars(select(Deck).where(Deck.user_id == user.id).order_by(Deck.name))).all()

    counts = {
        row[0]: row[1]
        for row in (
            await db.execute(
                select(Card.deck_id, func.count())
                .join(Deck, Deck.id == Card.deck_id)
                .where(Deck.user_id == user.id, Card.suspended.is_(False))
                .group_by(Card.deck_id)
            )
        ).all()
    }
    due = {
        row[0]: row[1]
        for row in (
            await db.execute(
                select(Card.deck_id, func.count())
                .join(Deck, Deck.id == Card.deck_id)
                .where(
                    Deck.user_id == user.id,
                    Card.suspended.is_(False),
                    Card.leech_flag.is_(False),
                    Card.state != "new",
                    Card.due <= now,
                )
                .group_by(Card.deck_id)
            )
        ).all()
    }
    new = {
        row[0]: row[1]
        for row in (
            await db.execute(
                select(Card.deck_id, func.count())
                .join(Deck, Deck.id == Card.deck_id)
                .where(Deck.user_id == user.id, Card.suspended.is_(False), Card.state == "new")
                .group_by(Card.deck_id)
            )
        ).all()
    }

    return [
        DeckOut(
            id=str(d.id),
            name=d.name,
            parent_id=str(d.parent_id) if d.parent_id else None,
            desired_retention_override=d.desired_retention_override,
            default_priority=d.default_priority,
            card_count=counts.get(d.id, 0),
            due_count=due.get(d.id, 0),
            new_count=new.get(d.id, 0),
            target_event_date=d.target_event_date,
            target_event_title=d.target_event_title,
        )
        for d in decks
    ]


@router.post("/decks", response_model=DeckOut, status_code=201)
async def create_deck(
    body: DeckCreate, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> DeckOut:
    parent_id = None
    if body.parent_id:
        parent = await _owned_deck(db, user, parse_uuid(body.parent_id, "parent_id"))
        parent_id = parent.id
    deck = Deck(
        user_id=user.id,
        name=body.name,
        parent_id=parent_id,
        desired_retention_override=body.desired_retention_override,
        default_priority=body.default_priority,
        target_event_date=body.target_event_date,
        target_event_title=body.target_event_title,
    )
    db.add(deck)
    await db.commit()
    await db.refresh(deck)
    return DeckOut(
        id=str(deck.id),
        name=deck.name,
        parent_id=str(deck.parent_id) if deck.parent_id else None,
        desired_retention_override=deck.desired_retention_override,
        default_priority=deck.default_priority,
        target_event_date=deck.target_event_date,
        target_event_title=deck.target_event_title,
    )


@router.patch("/decks/{deck_id}", response_model=DeckOut)
async def update_deck(
    deck_id: str,
    body: DeckUpdate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> DeckOut:
    deck = await _owned_deck(db, user, parse_uuid(deck_id))
    data = body.model_dump(exclude_unset=True)
    if "parent_id" in data:
        raw = data.pop("parent_id")
        if raw:
            parent = await _owned_deck(db, user, parse_uuid(raw, "parent_id"))
            if parent.id == deck.id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "a deck cannot be its own parent")
            deck.parent_id = parent.id
        else:
            deck.parent_id = None
    for key, value in data.items():
        setattr(deck, key, value)
    await db.commit()
    await db.refresh(deck)
    return DeckOut(
        id=str(deck.id),
        name=deck.name,
        parent_id=str(deck.parent_id) if deck.parent_id else None,
        desired_retention_override=deck.desired_retention_override,
        default_priority=deck.default_priority,
        target_event_date=deck.target_event_date,
        target_event_title=deck.target_event_title,
    )


@router.get("/decks/{deck_id}/stats", response_model=DeckStatsOut)
async def deck_stats(
    deck_id: str,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> DeckStatsOut:
    """Return live review progress and difficulty distribution stats for a specific deck."""
    deck = await _owned_deck(db, user, parse_uuid(deck_id))
    now = datetime.now(UTC)

    stmt = (
        select(Card, Note)
        .join(Note, Card.note_id == Note.id)
        .where(Card.deck_id == deck.id, Card.suspended.is_(False))
    )
    rows = (await db.execute(stmt)).all()

    total_cards = len(rows)
    viewed_cards = sum(1 for c, _ in rows if c.state != "new")
    new_cards = sum(1 for c, _ in rows if c.state == "new")
    learning_cards = sum(1 for c, _ in rows if c.state in ("learning", "relearning"))
    review_cards = sum(1 for c, _ in rows if c.state == "review")
    due_cards = sum(
        1 for c, _ in rows
        if c.due and (c.due if c.due.tzinfo else c.due.replace(tzinfo=UTC)) <= now and c.state != "new"
    )

    viewed_ratio = round(viewed_cards / total_cards, 4) if total_cards > 0 else 0.0

    diff_counts: dict[str, int] = {"Easy": 0, "Medium": 0, "Hard": 0, "Unrated": 0}

    for card, note in rows:
        fv = note.field_values or {}
        raw_diff = fv.get("difficulty") or fv.get("Difficulty") or fv.get("diff")
        if raw_diff and isinstance(raw_diff, str) and raw_diff.strip():
            label = raw_diff.strip().capitalize()
            if label not in diff_counts:
                diff_counts[label] = 0
            diff_counts[label] += 1
        elif card.difficulty is not None:
            if card.difficulty <= 4.0:
                diff_counts["Easy"] += 1
            elif card.difficulty <= 7.0:
                diff_counts["Medium"] += 1
            else:
                diff_counts["Hard"] += 1
        else:
            diff_counts["Unrated"] += 1

    cleaned_counts = {
        k: v for k, v in diff_counts.items() if v > 0 or k in ("Easy", "Medium", "Hard")
    }
    diff_props = {
        k: round(v / total_cards, 4) if total_cards > 0 else 0.0
        for k, v in cleaned_counts.items()
    }

    return DeckStatsOut(
        id=str(deck.id),
        name=deck.name,
        total_cards=total_cards,
        viewed_cards=viewed_cards,
        new_cards=new_cards,
        learning_cards=learning_cards,
        review_cards=review_cards,
        due_cards=due_cards,
        viewed_ratio=viewed_ratio,
        difficulty_counts=cleaned_counts,
        difficulty_proportions=diff_props,
    )


@router.delete("/decks", status_code=204)
async def delete_all_decks(
    user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> None:
    """Delete all decks belonging to the current user, cascading associated notes and cards."""
    deck_ids = (await db.scalars(select(Deck.id).where(Deck.user_id == user.id))).all()
    if not deck_ids:
        return

    note_ids = (
        await db.scalars(
            select(Card.note_id).where(Card.deck_id.in_(deck_ids)).distinct()
        )
    ).all()

    for deck_id in deck_ids:
        await tree_service.detach_entity_node(db, KnowledgeNode.deck_id == deck_id)

    if note_ids:
        notes = (await db.scalars(select(Note).where(Note.id.in_(note_ids)))).all()
        for note in notes:
            await db.delete(note)

    decks = (await db.scalars(select(Deck).where(Deck.id.in_(deck_ids)))).all()
    for deck in decks:
        await db.delete(deck)

    await db.commit()


@router.delete("/decks/{deck_id}", status_code=204)
async def delete_deck(
    deck_id: str,
    cascade: bool = Query(default=True),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    deck = await _owned_deck(db, user, parse_uuid(deck_id))
    count = await db.scalar(select(func.count()).select_from(Card).where(Card.deck_id == deck.id))
    if count and not cascade:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"deck still holds {count} cards — move or delete them first, or pass cascade=true",
        )
    if count and cascade:
        note_ids = (
            await db.scalars(select(Card.note_id).where(Card.deck_id == deck.id).distinct())
        ).all()
        if note_ids:
            notes = (await db.scalars(select(Note).where(Note.id.in_(note_ids)))).all()
            for note in notes:
                await db.delete(note)

    # Topics filed under this deck in the knowledge tree outlive it; lift them
    # to its parent rather than letting the node's FK cascade delete them.
    await tree_service.detach_entity_node(db, KnowledgeNode.deck_id == deck.id)
    await db.delete(deck)
    await db.commit()


# ── note types ──────────────────────────────────────────────────────────────


@router.get("/note-types", response_model=list[NoteTypeOut])
async def list_note_types(
    user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> list[NoteTypeOut]:
    rows = (await db.scalars(select(NoteType).where(NoteType.user_id == user.id))).all()
    return [
        NoteTypeOut(
            id=str(n.id),
            name=n.name,
            template_kind=n.template_kind,
            fields=n.fields or {},
            grading_profile=n.grading_profile,
        )
        for n in rows
    ]


@router.post("/note-types", response_model=NoteTypeOut, status_code=201)
async def create_note_type(
    body: NoteTypeCreate, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> NoteTypeOut:
    nt = NoteType(
        user_id=user.id,
        name=body.name,
        template_kind=body.template_kind,
        fields=body.fields,
        grading_profile=body.grading_profile,
    )
    db.add(nt)
    await db.commit()
    await db.refresh(nt)
    return NoteTypeOut(
        id=str(nt.id),
        name=nt.name,
        template_kind=nt.template_kind,
        fields=nt.fields or {},
        grading_profile=nt.grading_profile,
    )


# ── notes & cards ───────────────────────────────────────────────────────────


@router.post("/notes", response_model=NoteOut, status_code=201)
async def create_note(
    body: NoteCreate, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> NoteOut:
    deck = await _owned_deck(db, user, parse_uuid(body.deck_id, "deck_id"))

    if body.note_type_id:
        nt = await db.get(NoteType, parse_uuid(body.note_type_id, "note_type_id"))
        if nt is None or nt.user_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "note type not found")
    else:
        nt = await default_note_type(db, user, body.template_kind or "basic")

    note = Note(user_id=user.id, note_type_id=nt.id, field_values=body.field_values)
    db.add(note)
    await db.flush()
    await sync_cards(db, note, nt, deck.id, tags=body.tags, priority=body.priority)
    await db.commit()
    return await _note_out(db, note.id)


@router.get("/notes/{note_id}", response_model=NoteOut)
async def get_note(
    note_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> NoteOut:
    note = await db.get(Note, parse_uuid(note_id))
    if note is None or note.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "note not found")
    return await _note_out(db, note.id)


@router.patch("/notes/{note_id}", response_model=NoteOut)
async def update_note(
    note_id: str,
    body: NoteUpdate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> NoteOut:
    note = await db.get(Note, parse_uuid(note_id))
    if note is None or note.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "note not found")
    if body.field_values is not None:
        note.field_values = body.field_values
    nt = await db.get(NoteType, note.note_type_id)
    cards = (await db.scalars(select(Card).where(Card.note_id == note.id))).all()
    deck_id = cards[0].deck_id if cards else None
    if deck_id is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "note has no cards to update")
    await sync_cards(db, note, nt, deck_id, tags=body.tags)
    await db.commit()
    return await _note_out(db, note.id)


@router.delete("/notes/{note_id}", status_code=204)
async def delete_note(
    note_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> None:
    note = await db.get(Note, parse_uuid(note_id))
    if note is None or note.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "note not found")
    await db.delete(note)
    await db.commit()


@router.get("/cards", response_model=list[CardOut])
async def list_cards(
    deck_id: str | None = None,
    tag: str | None = None,
    search: str | None = None,
    include_suspended: bool = False,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CardOut]:
    """Browse — also serves §9.5's "everything else" manual-override view."""
    stmt = select(Card).join(Deck, Deck.id == Card.deck_id).where(Deck.user_id == user.id)
    if deck_id:
        stmt = stmt.where(Card.deck_id == parse_uuid(deck_id, "deck_id"))
    if not include_suspended:
        stmt = stmt.where(Card.suspended.is_(False))
    stmt = stmt.order_by(Card.due.is_(None), Card.due).limit(limit + offset)

    cards = list((await db.scalars(stmt)).all())
    # Tag filtering happens here rather than in SQL: TEXT[] degrades to JSON on
    # SQLite, so array containment is not portable (see app/models docstring).
    if tag:
        cards = [c for c in cards if tag in (c.tags or [])]
    out = [card_out(c) for c in cards]
    if search:
        needle = search.lower()
        out = [c for c in out if needle in c.front.lower() or needle in c.back.lower()]
    return out[offset : offset + limit]


@router.post("/cards/{card_id}/suspend", response_model=CardOut)
async def toggle_suspend(
    card_id: str,
    suspended: bool = True,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> CardOut:
    card = await _owned_card(db, user, parse_uuid(card_id))
    card.suspended = suspended
    await db.commit()
    await db.refresh(card)
    return card_out(card)


@router.patch("/priority")
async def set_priority(
    body: PriorityUpdate, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> dict:
    """One endpoint for deck | card | source | extract priority (§7)."""
    target_id = parse_uuid(body.id)
    if body.target == "deck":
        obj = await _owned_deck(db, user, target_id)
        obj.default_priority = body.priority
    elif body.target == "card":
        obj = await _owned_card(db, user, target_id)
        obj.priority = body.priority
    elif body.target == "source":
        obj = await db.get(Source, target_id)
        if obj is None or obj.user_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "source not found")
        obj.priority = body.priority
    elif body.target == "extract":
        obj = await db.get(Extract, target_id)
        source = await db.get(Source, obj.source_id) if obj else None
        if obj is None or source is None or source.user_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "extract not found")
        obj.priority = body.priority
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"unknown target {body.target!r}")
    await db.commit()
    return {"target": body.target, "id": body.id, "priority": body.priority}


async def _note_out(db: AsyncSession, note_id: uuid.UUID) -> NoteOut:
    note = await db.get(Note, note_id)
    nt = await db.get(NoteType, note.note_type_id)
    cards = (await db.scalars(select(Card).where(Card.note_id == note.id))).all()
    return NoteOut(
        id=str(note.id),
        note_type_id=str(note.note_type_id),
        template_kind=nt.template_kind,
        field_values=note.field_values or {},
        created_at=note.created_at,
        cards=[card_out(c) for c in cards],
    )
