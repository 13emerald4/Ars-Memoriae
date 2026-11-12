"""Recording one confirmed review.

There is exactly one way a grade reaches FSRS. The desktop's confirm endpoint
and the mobile app's offline batch both come through `record_review`, so a
review means the same thing wherever it was made: the same retention target,
the same lapse and leech accounting, the same weakness bookkeeping.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import new_answer_hash
from app.models import Card, Deck, GradingCache, ReviewLog, User
from app.services import leech_service
from app.services.fsrs_service import GRADE_TO_RATING, FSRSService
from app.services.grading_service import GRADES

# §4.3: how fast the per-user calibration follows the user's own overrides.
BIAS_LEARNING_RATE = 0.1


@dataclass
class ReviewOutcome:
    reviewed_at: datetime
    state_before: str
    leech_flagged: bool


def aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def upcoming(event: datetime | None, now: datetime) -> datetime | None:
    """The event date if it is still ahead of `now`, else None."""
    if event is None:
        return None
    event = aware(event)
    return event if event > now else None


async def record_review(
    db: AsyncSession,
    user: User,
    card: Card,
    deck: Deck,
    *,
    grade: str,
    reviewed_at: datetime,
    typed_answer: str | None = None,
    latency_ms: int | None = None,
    overridden: bool = False,
    confidence: int | None = None,
    is_blitz: bool = False,
) -> ReviewOutcome:
    """Schedules `card` for `grade` as of `reviewed_at` and writes the log row.

    Adds to the session but does not commit; the caller owns the transaction.
    """
    now = aware(reviewed_at)
    state_before = card.state
    elapsed_days = None
    if card.last_review:
        elapsed_days = (now - aware(card.last_review)).total_seconds() / 86400.0

    # Per-deck desired retention is the "% bias per subject" knob (§16 Appendix).
    # In Event Horizon mode, retention target dynamically ramps to peak_retention_target.
    # A past event no longer ramps retention or compresses intervals.
    target_event = upcoming(deck.target_event_date or user.target_event_date, now)
    retention = deck.desired_retention_override or (
        user.peak_retention_target if target_event else user.desired_retention
    )
    fsrs = FSRSService(weights=user.fsrs_parameters, desired_retention=retention)
    fsrs_card = FSRSService.to_fsrs_card(
        state=card.state,
        stability=card.stability,
        difficulty=card.difficulty,
        step=card.step,
        due=card.due,
        last_review=card.last_review,
    )
    _, new_state = fsrs.schedule(fsrs_card, GRADE_TO_RATING[grade], now)

    # Event Horizon interval compression: ensure scheduled card due date
    # does not drift past the target competition/exam date.
    if target_event and new_state.get("due"):
        new_state["due"] = FSRSService.compress_for_event_horizon(
            new_state["due"], now, target_event
        )

    # A lapse is a *review-state* card being failed — relearning failures inside
    # the same lapse do not each count again (matches standard lapse definition).
    if grade == "again" and state_before == "review":
        card.lapse_count += 1

    for key, value in new_state.items():
        setattr(card, key, value)

    # Recover the LLM's own verdict for the log, if the answer was graded.
    llm_grade = llm_reasoning = None
    llm_confidence = None
    identified_weaknesses: list[str] = []
    improvements: list[str] = []
    persistent_weaknesses: list[str] = []
    if typed_answer:
        cached = await db.get(GradingCache, (card.id, new_answer_hash(typed_answer)))
        if cached:
            llm_grade = cached.response.get("grade")
            llm_reasoning = cached.response.get("reasoning")
            llm_confidence = cached.response.get("confidence")
            identified_weaknesses = cached.response.get("weaknesses") or []
            improvements = cached.response.get("improvements") or []
            persistent_weaknesses = cached.response.get("persistent_weaknesses") or []

    # Update Card longitudinal weakness state:
    # 1. Any weakness listed in 'improvements' is resolved.
    # 2. Any weakness in 'persistent_weaknesses' or 'identified_weaknesses' is active.
    current_active = set(card.active_weaknesses or [])
    current_active.difference_update(improvements)
    current_active.update(persistent_weaknesses)
    current_active.update(identified_weaknesses)

    # A clean good/easy with nothing flagged resolves whatever was still open.
    if grade in ("good", "easy") and not identified_weaknesses and not persistent_weaknesses:
        current_active.clear()

    updated_active = sorted(current_active)
    card.active_weaknesses = updated_active

    history = list(card.weakness_history or [])
    history.append(
        {
            "reviewed_at": now.isoformat(),
            "final_grade": grade,
            "weaknesses_identified": identified_weaknesses,
            "improvements": improvements,
            "persistent_weaknesses": persistent_weaknesses,
            "active_remaining": updated_active,
        }
    )
    card.weakness_history = history[-50:]

    db.add(
        ReviewLog(
            card_id=card.id,
            reviewed_at=now,
            typed_answer=typed_answer,
            latency_ms=latency_ms,
            llm_grade=llm_grade,
            llm_reasoning=llm_reasoning,
            llm_confidence=llm_confidence,
            final_grade=grade,
            overridden=overridden,
            state_before=state_before,
            elapsed_days=elapsed_days,
            graduated_to_review=state_before != "review" and new_state.get("state") == "review",
            user_confidence=confidence,
            is_blitz=is_blitz,
            weaknesses=identified_weaknesses,
            improvements=improvements,
            persistent_weaknesses=persistent_weaknesses,
        )
    )

    # §4.3 per-user calibration: a running average of the user's own overrides,
    # not a fine-tune. Positive bias => the model grades this user too harshly.
    if overridden and llm_grade in GRADES:
        delta = GRADES.index(grade) - GRADES.index(llm_grade)
        user.grading_bias = round(
            (1 - BIAS_LEARNING_RATE) * user.grading_bias + BIAS_LEARNING_RATE * delta, 4
        )

    leech_flagged = leech_service.check_leech(card, user.leech_threshold)
    if leech_flagged:
        await leech_service.flag_leech(db, card)

    return ReviewOutcome(reviewed_at=now, state_before=state_before, leech_flagged=leech_flagged)
