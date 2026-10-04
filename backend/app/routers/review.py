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
    LessonOut,
    SocraticRequest,
    SocraticResponse,
    StuckAlertOut,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
    WeaknessHintResponse,
    RunReviewCodeRequest,
)
from app.services import leech_service, lesson_service, stuck_service
from app.services.code_runner_service import run_code, run_python_code
from app.services.fsrs_service import GRADE_TO_RATING, FSRSService
from app.services.grading_service import (
    GRADES,
    GradingService,
    GradingUnavailable,
    apply_bias,
    disagrees_with_heuristic,
    grade_for_score,
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


def format_latency(latency_ms: int | None) -> str | None:
    """A neutral FYI about response time, shown to the user but never fed to
    the grader — how long recall took says nothing about whether it was
    correct, which is the whole reason grading no longer sees it (§4.1)."""
    if not latency_ms or latency_ms <= 0:
        return None
    seconds = latency_ms // 1000
    if seconds < 1:
        return "answered in under a second"
    if seconds < 60:
        return f"answered in {seconds}s"
    minutes, rem = divmod(seconds, 60)
    return f"answered in {minutes}m {rem}s" if rem else f"answered in {minutes}m"


def _manual(
    reference: str,
    reason: str,
    latency_note: str | None = None,
    automaticity_exceeded: bool = False,
    automaticity_threshold_ms: int | None = None,
    automaticity_note: str | None = None,
) -> SubmitAnswerResponse:
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
        latency_note=latency_note,
        automaticity_exceeded=automaticity_exceeded,
        automaticity_threshold_ms=automaticity_threshold_ms,
        automaticity_note=automaticity_note,
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
    # Computed once and attached to every response shape below — including the
    # manual fallback — since it's informational only and has no bearing on
    # whether grading is available.
    latency_note = format_latency(body.latency_ms)

    auto_exceeded = bool(
        user.automaticity_threshold_ms
        and body.latency_ms
        and body.latency_ms > user.automaticity_threshold_ms
    )
    auto_note = (
        f"Latency ({round(body.latency_ms / 1000.0, 1)}s) exceeded automaticity threshold ({round(user.automaticity_threshold_ms / 1000.0, 1)}s)."
        if auto_exceeded and user.automaticity_threshold_ms
        else None
    )

    if not user.llm_grading_consent:
        return _manual(
            back,
            "consent_not_given",
            latency_note,
            auto_exceeded,
            user.automaticity_threshold_ms,
            auto_note,
        )

    api_key = decrypt_api_key(user.google_api_key_encrypted)

    # §4.3 cache: identical resubmits must not burn API calls.
    answer_hash = new_answer_hash(body.typed_answer)
    cached = await db.get(GradingCache, (card.id, answer_hash))
    overlap = heuristic_overlap(back, body.typed_answer)

    if cached is not None:
        result = dict(cached.response)
        return _build_response(
            result,
            back,
            overlap,
            user,
            cached=True,
            latency_note=latency_note,
            latency_ms=body.latency_ms,
        )

    profile = select_grading_profile(note.note_type.grading_profile, note.note_type.template_kind)
    service = GradingService(api_key, user.grading_model)
    try:
        result = await service.grade_with_escalation(
            front=front,
            back=back,
            user_answer=body.typed_answer,
            profile=profile,
            card_type=note.note_type.template_kind,
            previous_weaknesses=card.active_weaknesses or [],
            force_escalate=await _disputed_recently(db, card.id),
        )
    except GradingUnavailable as exc:
        return _manual(
            back,
            str(exc),
            latency_note,
            auto_exceeded,
            user.automaticity_threshold_ms,
            auto_note,
        )

    db.add(GradingCache(card_id=card.id, answer_hash=answer_hash, response=result))
    await db.commit()
    return _build_response(
        result,
        back,
        overlap,
        user,
        latency_note=latency_note,
        latency_ms=body.latency_ms,
    )


def _build_response(
    result: dict,
    reference: str,
    overlap: float,
    user: User,
    cached: bool = False,
    latency_note: str | None = None,
    latency_ms: int | None = None,
) -> SubmitAnswerResponse:
    # Calibration is applied to the score, and the suggested grade is derived
    # from that same calibrated number — so the % the user reads and the grade
    # button highlighted for them always agree.
    raw_score = result.get("score")
    if raw_score is None:
        # A cache entry written before scoring existed: no score to show, but
        # its stored grade is still perfectly usable.
        score = None
        grade = result["grade"]
    else:
        score = apply_bias(int(raw_score), user.grading_bias)
        grade = grade_for_score(score)

    automaticity_exceeded = False
    automaticity_note = None
    if user.automaticity_threshold_ms and latency_ms and latency_ms > user.automaticity_threshold_ms:
        automaticity_exceeded = True
        automaticity_note = (
            f"Latency ({round(latency_ms / 1000.0, 1)}s) exceeded target automaticity threshold "
            f"({round(user.automaticity_threshold_ms / 1000.0, 1)}s). Graded purely on correctness."
        )

    # §4.3 sanity check: the model and the cheap heuristic disagreeing, or the
    # model being unsure, means asking the user instead of auto-accepting.
    needs_confirmation = (
        disagrees_with_heuristic(grade, overlap)
        or result["confidence"] < 0.5
    )
    return SubmitAnswerResponse(
        suggested_grade=Grade(grade),
        score=score,
        confidence=result["confidence"],
        matched_points=result.get("matched_points", []),
        missed_points=result.get("missed_points", []),
        overlooked_phrases=result.get("overlooked_phrases", []),
        weaknesses=result.get("weaknesses", []),
        improvements=result.get("improvements", []),
        persistent_weaknesses=result.get("persistent_weaknesses", []),
        reasoning=result.get("reasoning", ""),
        reference_answer=reference,
        needs_confirmation=needs_confirmation,
        heuristic_overlap=round(overlap, 3),
        model_used=result.get("model_used"),
        cached=cached,
        latency_note=latency_note,
        automaticity_exceeded=automaticity_exceeded,
        automaticity_threshold_ms=user.automaticity_threshold_ms,
        automaticity_note=automaticity_note,
    )


@router.get("/{card_id}/lesson", response_model=LessonOut)
async def card_lesson(
    card_id: str,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> LessonOut:
    """Learn & Practice: the lesson to read before answering this card.

    Fetched on demand rather than bundled into the queue item — the mode is
    opt-in and each lesson may cost a generation, so composing a session
    shouldn't pay for lessons nobody asked to see.
    """
    card = await _owned_card(db, user, parse_uuid(card_id))
    return LessonOut(**await lesson_service.get_lesson(db, user, card))


@router.post("/{card_id}/guide", response_model=SocraticResponse)
async def socratic_guide(
    card_id: str,
    body: SocraticRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> SocraticResponse:
    """The Socratic AI Guide: one diagnostic question at a time, never the
    answer. Stateless — the client resends the conversation each turn, same
    as the lesson gate needs no citation to exist here (this works off any
    card's front/back, not just ones carved from a document)."""
    card = await _owned_card(db, user, parse_uuid(card_id))
    note = card.note
    front, back = render(
        note.note_type.template_kind, note.field_values or {}, card.template_slot
    )

    if not user.llm_grading_consent:
        return SocraticResponse(message="", degraded=True, degraded_reason="consent_not_given")
    api_key = decrypt_api_key(user.google_api_key_encrypted)

    service = GradingService(api_key, user.grading_model)
    try:
        result = await service.ask_socratic_question(
            front=front,
            back=back,
            history=[(t.role, t.text) for t in body.history],
            latest=body.message,
            active_weaknesses=card.active_weaknesses or [],
        )
    except GradingUnavailable as exc:
        return SocraticResponse(message="", degraded=True, degraded_reason=str(exc))

    return SocraticResponse(
        message=result["message"], on_track=result["on_track"], model_used=user.grading_model
    )


@router.post("/{card_id}/weakness-hint", response_model=WeaknessHintResponse)
async def card_weakness_hint(
    card_id: str,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> WeaknessHintResponse:
    """Targeted hint addressing previous weaknesses on this card without spoiling the solution."""
    card = await _owned_card(db, user, parse_uuid(card_id))
    note = card.note
    front, back = render(
        note.note_type.template_kind, note.field_values or {}, card.template_slot
    )

    if not card.active_weaknesses:
        return WeaknessHintResponse(
            hint="No prior weaknesses recorded for this card. Focus on recalling the core definitions and logic.",
            active_weaknesses=[],
            has_past_weaknesses=False,
        )

    if not user.llm_grading_consent:
        # Fallback without LLM generation
        return WeaknessHintResponse(
            hint=f"Focus on your previous stumbling block: {card.active_weaknesses[0]}.",
            active_weaknesses=card.active_weaknesses,
            has_past_weaknesses=True,
        )

    api_key = decrypt_api_key(user.google_api_key_encrypted)
    service = GradingService(api_key, user.grading_model)
    try:
        result = await service.generate_weakness_hint(
            front=front,
            back=back,
            active_weaknesses=card.active_weaknesses,
        )
        return WeaknessHintResponse(
            hint=result["hint"],
            active_weaknesses=card.active_weaknesses,
            has_past_weaknesses=result.get("has_past_weaknesses", True),
        )
    except GradingUnavailable as exc:
        return WeaknessHintResponse(
            hint=f"Watch out for previous difficulty: {card.active_weaknesses[0]}.",
            active_weaknesses=card.active_weaknesses,
            has_past_weaknesses=True,
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
    # In Event Horizon mode, retention target dynamically ramps to peak_retention_target.
    target_event = deck.target_event_date or user.target_event_date
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
    _, new_state = fsrs.schedule(
        fsrs_card, GRADE_TO_RATING[body.final_grade.value], now
    )

    # Event Horizon interval compression: ensure scheduled card due date
    # does not drift past the target competition/exam date.
    if target_event and "due" in new_state and new_state["due"]:
        new_state["due"] = FSRSService.compress_for_event_horizon(
            new_state["due"], now, target_event
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
    identified_weaknesses: list[str] = []
    improvements: list[str] = []
    persistent_weaknesses: list[str] = []
    if body.typed_answer:
        cached = await db.get(GradingCache, (card.id, new_answer_hash(body.typed_answer)))
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

    # If final grade is 'easy' or 'good' and no weaknesses/persistent weaknesses were flagged, resolve active weaknesses
    if body.final_grade in (Grade.good, Grade.easy) and not identified_weaknesses and not persistent_weaknesses:
        current_active.clear()

    updated_active = sorted(list(current_active))
    card.active_weaknesses = updated_active

    history_entry = {
        "reviewed_at": now.isoformat(),
        "final_grade": body.final_grade.value,
        "weaknesses_identified": identified_weaknesses,
        "improvements": improvements,
        "persistent_weaknesses": persistent_weaknesses,
        "active_remaining": updated_active,
    }
    history = list(card.weakness_history or [])
    history.append(history_entry)
    card.weakness_history = history[-50:]

    # Computed against history only — called before this review's own row
    # exists, so the query never has to exclude its own result.
    stuck_alert = await stuck_service.check_stuck(
        db, user, final_grade=body.final_grade.value, latency_ms=body.latency_ms
    )

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
            graduated_to_review=state_before != "review" and new_state.get("state") == "review",
            user_confidence=body.confidence,
            is_blitz=body.is_blitz,
            weaknesses=identified_weaknesses,
            improvements=improvements,
            persistent_weaknesses=persistent_weaknesses,
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

    auto_exceeded = bool(
        user.automaticity_threshold_ms
        and body.latency_ms
        and body.latency_ms > user.automaticity_threshold_ms
    )
    due = card.due if card.due.tzinfo else card.due.replace(tzinfo=UTC)
    return ConfirmReviewResponse(
        next_due=due,
        new_stability=card.stability or 0.0,
        new_difficulty=card.difficulty or 0.0,
        state=card.state,
        interval_days=round((due - now).total_seconds() / 86400.0, 4),
        lapse_count=card.lapse_count,
        leech_flagged=leech_flagged,
        stuck_alert=(
            StuckAlertOut(
                reason=stuck_alert.reason,
                message=stuck_alert.message,
                suggested_break_minutes=stuck_alert.suggested_break_minutes,
            )
            if stuck_alert
            else None
        ),
        automaticity_exceeded=auto_exceeded,
    )


@router.post("/{card_id}/run-code")
async def run_card_code(
    card_id: str,
    body: RunReviewCodeRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """Executes Python code against sample or custom testcases in an isolated sandbox for review cards."""
    cid = parse_uuid(card_id, "card_id")
    card = await _owned_card(db, user, cid)

    # Use custom test cases if provided, or pull test cases from note field_values
    test_cases = body.custom_test_cases
    if not test_cases and card.note and card.note.field_values:
        test_cases = card.note.field_values.get("test_cases") or []

    res = await run_code(
        code=body.code,
        test_cases=test_cases,
        language=body.language,
        timeout_sec=4.0,
    )
    return res
