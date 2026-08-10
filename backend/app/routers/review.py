"""The review cycle (§4.1, §7.1).

  POST /api/review/{card_id}/answer   typed answer -> LLM grade + reasoning
  POST /api/review/{card_id}/confirm  (possibly overridden) grade -> FSRS

The split matters: the LLM's grade is only a *suggestion*. What FSRS consumes
is whatever the user confirmed, and every override is logged (§4.1 step 6) so
the calibration loop in §4.3 has something to learn from.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_api_key, new_answer_hash
from app.db import get_db
from app.models import Card, Deck, GradingCache, ReviewLog, User
from app.routers.deps import current_user, parse_uuid
from app.schemas.review import (
    ConfirmReviewRequest,
    ConfirmReviewResponse,
    Grade,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
)
from app.services import leech_service
from app.services.fsrs_service import GRADE_TO_RATING, FSRSService
from app.services.grading_service import (
    GRADES,
    GradingService,
    GradingUnavailable,
    apply_bias,
    disagrees_with_heuristic,
    heuristic_overlap,
)
from app.services.rendering import render, select_grading_profile

router = APIRouter(prefix="/api/review", tags=["review"])

BIAS_LEARNING_RATE = 0.1


async def _owned_card(db: AsyncSession, user: User, card_id: uuid.UUID) -> Card:
    card = await db.get(Card, card_id)
    if card is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "card not found")
    deck = await db.get(Deck, card.deck_id)
    if deck is None or deck.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "card not found")
    return card


async def _disputed_recently(db: AsyncSession, card_id: uuid.UUID) -> bool:
    """§4.2: two overrides in a row on this card escalates the next grading."""
    rows = await db.execute(
        select(ReviewLog.overridden)
        .where(ReviewLog.card_id == card_id)
        .order_by(ReviewLog.reviewed_at.desc())
        .limit(2)
    )
    flags = [r[0] for r in rows.all()]
    return len(flags) == 2 and all(flags)


def _manual(reference: str, reason: str) -> SubmitAnswerResponse:
    """§4.3 — the fallback is a real opt-out, not a degraded error state: the
    user gets the reference answer and the four buttons, same as Phase 1."""
    return SubmitAnswerResponse(
        suggested_grade=Grade.good,
        confidence=0.0,
        reasoning="",
        degraded_to_manual=True,
        degraded_reason=reason,
        reference_answer=reference,
        needs_confirmation=True,
    )


@router.post("/{card_id}/answer", response_model=SubmitAnswerResponse)
async def submit_answer(
    card_id: str,
    body: SubmitAnswerRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> SubmitAnswerResponse:
    card = await _owned_card(db, user, parse_uuid(card_id))
    note = card.note
    front, back = render(
        note.note_type.template_kind, note.field_values or {}, card.template_slot
    )

    if not user.llm_grading_consent:
        return _manual(back, "consent_not_given")

    api_key = decrypt_api_key(user.google_api_key_encrypted)
    if not api_key:
        return _manual(back, "no_api_key")

    # §4.3 cache: identical resubmits must not burn API calls.
    answer_hash = new_answer_hash(body.typed_answer)
    cached = await db.get(GradingCache, (card.id, answer_hash))
    overlap = heuristic_overlap(back, body.typed_answer)

    if cached is not None:
        result = dict(cached.response)
        return _build_response(result, back, overlap, user, cached=True)

    profile = select_grading_profile(note.note_type.grading_profile, note.note_type.template_kind)
    service = GradingService(api_key, user.grading_model)
    try:
        result = await service.grade_with_escalation(
            front=front,
            back=back,
            user_answer=body.typed_answer,
            latency_ms=body.latency_ms,
            profile=profile,
            card_type=note.note_type.template_kind,
            force_escalate=await _disputed_recently(db, card.id),
        )
    except GradingUnavailable as exc:
        return _manual(back, str(exc))

    db.add(GradingCache(card_id=card.id, answer_hash=answer_hash, response=result))
    await db.commit()
    return _build_response(result, back, overlap, user)


def _build_response(
    result: dict, reference: str, overlap: float, user: User, cached: bool = False
) -> SubmitAnswerResponse:
    grade = apply_bias(result["grade"], user.grading_bias)
    # §4.3 sanity check: the model and the cheap heuristic disagreeing, or the
    # model being unsure, means asking the user instead of auto-accepting.
    needs_confirmation = disagrees_with_heuristic(grade, overlap) or result["confidence"] < 0.5
    return SubmitAnswerResponse(
        suggested_grade=Grade(grade),
        confidence=result["confidence"],
        matched_points=result.get("matched_points", []),
        missed_points=result.get("missed_points", []),
        reasoning=result.get("reasoning", ""),
        reference_answer=reference,
        needs_confirmation=needs_confirmation,
        heuristic_overlap=round(overlap, 3),
        model_used=result.get("model_used"),
        cached=cached,
    )


@router.post("/{card_id}/confirm", response_model=ConfirmReviewResponse)
async def confirm_review(
    card_id: str,
    body: ConfirmReviewRequest,
    background: BackgroundTasks,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> ConfirmReviewResponse:
    card = await _owned_card(db, user, parse_uuid(card_id))
    deck = await db.get(Deck, card.deck_id)
    now = datetime.now(UTC)

    state_before = card.state
    last_review = card.last_review
    elapsed_days = None
    if last_review:
        lr = last_review if last_review.tzinfo else last_review.replace(tzinfo=UTC)
        elapsed_days = (now - lr).total_seconds() / 86400.0

    # Per-deck desired retention is the "% bias per subject" knob (§16 Appendix).
    retention = deck.desired_retention_override or user.desired_retention
    fsrs = FSRSService(weights=user.fsrs_parameters, desired_retention=retention)

    fsrs_card = FSRSService.to_fsrs_card(
        state=card.state,
        stability=card.stability,
        difficulty=card.difficulty,
        step=card.step,
        due=card.due,
        last_review=card.last_review,
    )
    _, new_state = fsrs.schedule(
        fsrs_card, GRADE_TO_RATING[body.final_grade.value], now, body.latency_ms
    )

    # A lapse is a *review-state* card being failed — relearning failures inside
    # the same lapse do not each count again (matches Anki's definition).
    if body.final_grade == Grade.again and state_before == "review":
        card.lapse_count += 1

    for key, value in new_state.items():
        setattr(card, key, value)

    # Recover the LLM's own verdict for the log, if the answer was graded.
    llm_grade = llm_reasoning = None
    llm_confidence = None
    if body.typed_answer:
        cached = await db.get(GradingCache, (card.id, new_answer_hash(body.typed_answer)))
        if cached:
            llm_grade = cached.response.get("grade")
            llm_reasoning = cached.response.get("reasoning")
            llm_confidence = cached.response.get("confidence")

    db.add(
        ReviewLog(
            card_id=card.id,
            reviewed_at=now,
            typed_answer=body.typed_answer,
            latency_ms=body.latency_ms,
            llm_grade=llm_grade,
            llm_reasoning=llm_reasoning,
            llm_confidence=llm_confidence,
            final_grade=body.final_grade.value,
            overridden=body.overridden,
            state_before=state_before,
            elapsed_days=elapsed_days,
        )
    )

    # §4.3 per-user calibration: a running average of the user's own overrides,
    # not a fine-tune. Positive bias => the model grades this user too harshly.
    if body.overridden and llm_grade in GRADES:
        delta = GRADES.index(body.final_grade.value) - GRADES.index(llm_grade)
        user.grading_bias = round(
            (1 - BIAS_LEARNING_RATE) * user.grading_bias + BIAS_LEARNING_RATE * delta, 4
        )

    leech_flagged = leech_service.check_leech(card, user.leech_threshold)
    if leech_flagged:
        await leech_service.flag_leech(db, card)
        if user.leech_remediation_opt_in and user.llm_grading_consent:
            background.add_task(leech_service.generate_remediation, card.id)

    await db.commit()
    await db.refresh(card)

    due = card.due if card.due.tzinfo else card.due.replace(tzinfo=UTC)
    return ConfirmReviewResponse(
        next_due=due,
        new_stability=card.stability or 0.0,
        new_difficulty=card.difficulty or 0.0,
        state=card.state,
        interval_days=round((due - now).total_seconds() / 86400.0, 4),
        lapse_count=card.lapse_count,
        leech_flagged=leech_flagged,
    )
