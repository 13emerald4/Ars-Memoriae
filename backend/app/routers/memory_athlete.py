"""Memory Champion / Athlete Router (§Features 4, 5, & 6).

Endpoints for:
  - Real-time card atomicity linting
  - Sequential overlapping chain cloze generation
  - AI-assisted card decomposition
  - Event horizon countdown & readiness calculations
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_api_key
from app.db import get_db
from app.models import Card, Deck, Note, NoteType, User
from app.routers.deps import current_user, parse_uuid
from app.schemas.core import (
    AtomicityIssueOut,
    AtomicityLintRequest,
    AtomicityLintResponse,
    DecomposeCardRequest,
    DecomposeCardResponse,
    DecomposedCardItem,
    EventReadinessResponse,
    SequentialClozeItem,
    SequentialClozeRequest,
    SequentialClozeResponse,
)
from app.services.atomicity_service import generate_sequential_clozes, lint_card_atomicity
from app.services.fsrs_service import FSRSService
from app.services.grading_service import GradingService, GradingUnavailable
from app.services.note_service import default_note_type, sync_cards

router = APIRouter(prefix="/api/memory", tags=["memory_athlete"])


@router.post("/lint-atomicity", response_model=AtomicityLintResponse)
async def lint_atomicity(
    body: AtomicityLintRequest,
    user: User = Depends(current_user),
) -> AtomicityLintResponse:
    """Real-time atomicity assessment of card front and back content."""
    res = lint_card_atomicity(body.front, body.back, body.template_kind)
    return AtomicityLintResponse(
        score=res.score,
        is_atomic=res.is_atomic,
        word_count_front=res.word_count_front,
        word_count_back=res.word_count_back,
        word_count_total=res.word_count_total,
        issues=[
            AtomicityIssueOut(
                severity=i.severity,
                code=i.code,
                message=i.message,
                suggestion=i.suggestion,
            )
            for i in res.issues
        ],
    )


@router.post("/sequential-cloze", response_model=SequentialClozeResponse)
async def create_sequential_cloze(
    body: SequentialClozeRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> SequentialClozeResponse:
    """Generates progressive overlapping chain clozes from an ordered list of steps.

    If deck_id is supplied, persists the notes & cards directly to the database.
    """
    cards = generate_sequential_clozes(body.title, body.steps, body.window_size)
    items = [
        SequentialClozeItem(
            step_index=c.step_index,
            total_steps=c.total_steps,
            front=c.front,
            back=c.back,
            target_step=c.target_step,
            context_before=c.context_before,
            context_after=c.context_after,
        )
        for c in cards
    ]

    notes_created = 0
    cards_created = 0

    if body.deck_id:
        deck = await db.get(Deck, parse_uuid(body.deck_id, "deck_id"))
        if deck is None or deck.user_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "deck not found")

        note_type = await default_note_type(db, user, "basic")

        for item in items:
            note = Note(
                user_id=user.id,
                note_type_id=note_type.id,
                field_values={"Front": item.front, "Back": item.back},
            )
            db.add(note)
            await db.flush()
            new_cards = sync_cards(note, deck.id, origin="sequential_cloze")
            for c in new_cards:
                db.add(c)
            notes_created += 1
            cards_created += len(new_cards)

        await db.commit()

    return SequentialClozeResponse(
        cards=items,
        notes_created=notes_created,
        cards_created=cards_created,
    )


@router.post("/decompose", response_model=DecomposeCardResponse)
async def decompose_card(
    body: DecomposeCardRequest,
    user: User = Depends(current_user),
) -> DecomposeCardResponse:
    """Uses LLM reasoning to decompose a non-atomic card into atomic question-answer pairs."""
    if not user.llm_grading_consent:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "LLM consent is required for AI card decomposition"
        )
    api_key = decrypt_api_key(user.google_api_key_encrypted)
    if not api_key:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Google GenAI API key is required")

    service = GradingService(api_key, user.grading_model)
    try:
        cards = await service.decompose_card_atomicity(body.front, body.back)
        return DecomposeCardResponse(
            cards=[DecomposedCardItem(front=c["front"], back=c["back"]) for c in cards]
        )
    except GradingUnavailable as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc


@router.get("/event-readiness", response_model=EventReadinessResponse)
async def get_event_readiness(
    deck_id: str | None = None,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> EventReadinessResponse:
    """Calculates Event Horizon countdown, projected retrievability, and readiness velocity."""
    target_event_date = user.target_event_date
    target_event_title = user.target_event_title

    deck = None
    if deck_id:
        deck = await db.get(Deck, parse_uuid(deck_id, "deck_id"))
        if deck and deck.user_id == user.id:
            if deck.target_event_date:
                target_event_date = deck.target_event_date
                target_event_title = deck.target_event_title or deck.name

    now = datetime.now(UTC)

    if not target_event_date:
        return EventReadinessResponse(
            target_event_date=None,
            target_event_title=None,
            days_remaining=None,
            is_active=False,
            status_label="No target event horizon set",
        )

    event_aware = target_event_date if target_event_date.tzinfo else target_event_date.replace(tzinfo=UTC)
    delta_seconds = (event_aware - now).total_seconds()
    days_remaining = max(0.0, round(delta_seconds / 86400.0, 1))

    # Query card stats
    card_query = select(Card).join(Deck, Deck.id == Card.deck_id).where(
        Deck.user_id == user.id, Card.suspended.is_(False)
    )
    if deck:
        card_query = card_query.where(Card.deck_id == deck.id)

    cards = (await db.scalars(card_query)).all()
    total_count = len(cards)
    if total_count == 0:
        return EventReadinessResponse(
            target_event_date=event_aware,
            target_event_title=target_event_title or "Upcoming Event",
            days_remaining=days_remaining,
            is_active=True,
            projected_retention=1.0,
            total_cards_count=0,
            status_label="No cards in scope",
        )

    fsrs = FSRSService(weights=user.fsrs_parameters, desired_retention=user.desired_retention)
    due_count = 0
    unstable_count = 0
    retrievability_sum = 0.0

    for c in cards:
        fsrs_card = FSRSService.to_fsrs_card(
            state=c.state,
            stability=c.stability,
            difficulty=c.difficulty,
            step=c.step,
            due=c.due,
            last_review=c.last_review,
        )
        r = fsrs.retrievability(fsrs_card, event_aware)
        retrievability_sum += r

        c_due = c.due if (c.due and c.due.tzinfo) else (c.due.replace(tzinfo=UTC) if c.due else None)
        if c.state == "new" or (c_due and c_due <= now):
            due_count += 1
        if (c.stability or 0.0) < 7.0:
            unstable_count += 1

    projected_retention = round(retrievability_sum / total_count, 3)

    # Estimate daily review velocity needed to peak all unstable/due cards
    daily_needed = math.ceil((due_count + unstable_count * 1.5) / max(1.0, days_remaining))

    status_label = "Optimal Peak" if projected_retention >= 0.90 else "Taper Needed"

    return EventReadinessResponse(
        target_event_date=event_aware,
        target_event_title=target_event_title or "Target Event",
        days_remaining=days_remaining,
        is_active=True,
        projected_retention=projected_retention,
        total_cards_count=total_count,
        due_cards_count=due_count,
        unstable_cards_count=unstable_count,
        estimated_daily_reviews_needed=daily_needed,
        status_label=status_label,
    )
