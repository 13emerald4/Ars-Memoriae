"""Leech detection + LLM-assisted remediation (§3.2).

Trigger is Anki's transparent lapse counter rather than SuperMemo's opaque
forgetting index, since FSRS already exposes lapse count per card. A flagged
leech is pulled from the active queue, never deleted; if the user opted in, the
same local model used for grading proposes a fix.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.models import Card, Deck, LeechSuggestion, ReviewLog, User
from app.services.grading_service import GradingService, GradingUnavailable
from app.services.rendering import render

log = logging.getLogger(__name__)


def check_leech(card: Card, threshold: int) -> bool:
    """True when this review just pushed the card over the threshold."""
    return not card.leech_flag and card.lapse_count >= threshold


async def flag_leech(db: AsyncSession, card: Card) -> None:
    card.leech_flag = True
    await db.flush()


async def recent_failed_answers(db: AsyncSession, card_id: uuid.UUID, limit: int = 8) -> list[str]:
    rows = await db.execute(
        select(ReviewLog.typed_answer)
        .where(
            ReviewLog.card_id == card_id,
            ReviewLog.final_grade == "again",
            ReviewLog.typed_answer.isnot(None),
        )
        .order_by(ReviewLog.reviewed_at.desc())
        .limit(limit)
    )
    return [r[0] for r in rows.all() if r[0]]


async def generate_remediation(card_id: uuid.UUID) -> None:
    """Background task: ask the model why this card keeps failing (§3.2 step 2).

    Opens its own session because it runs after the review response has already
    been returned — one extra LLM call per *leech*, not per review.
    """
    async with SessionLocal() as db:
        card = await db.get(Card, card_id)
        if card is None:
            return
        deck = await db.get(Deck, card.deck_id)
        user = await db.get(User, deck.user_id) if deck else None
        if user is None or not user.leech_remediation_opt_in or not user.llm_grading_consent:
            return

        existing = await db.scalar(
            select(LeechSuggestion).where(
                LeechSuggestion.card_id == card_id, LeechSuggestion.status == "pending"
            )
        )
        if existing:
            return

        front, back = render(
            card.note.note_type.template_kind, card.note.field_values or {}, card.template_slot
        )
        failed = await recent_failed_answers(db, card_id)
        service = GradingService(model=user.grading_model)
        try:
            result = await service.suggest_leech_remediation(front, back, card.lapse_count, failed)
        except GradingUnavailable as exc:
            log.info("leech remediation unavailable for card %s: %s", card_id, exc)
            return

        db.add(
            LeechSuggestion(
                card_id=card_id,
                kind=result["kind"],
                payload={"cards": result.get("cards", [])},
                rationale=result.get("rationale") or None,
            )
        )
        await db.commit()
