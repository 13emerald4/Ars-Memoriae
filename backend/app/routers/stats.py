"""GET /api/stats (§7) — heatmap, retention curve, forecast, leech list with
LLM remediation suggestions (§3.2), and IR throughput (§14 Phase 3)."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.timeutil import day_key
from app.db import get_db
from app.models import (
    Card,
    Deck,
    Extract,
    LeechSuggestion,
    Note,
    ReviewLog,
    Source,
    StudySession,
    User,
)
from app.routers.deps import current_user, parse_uuid
from app.schemas.analytics import LearningAnalyticsOut
from app.schemas.core import LeechOut, StatsOut
from app.services.learning_analytics_service import compute_learning_analytics
from app.services.note_service import default_note_type, sync_cards
from app.services.rendering import render

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats", response_model=StatsOut)
async def stats(
    days: int = Query(default=365, ge=7, le=1095),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> StatsOut:
    now = datetime.now(UTC)
    since = now - timedelta(days=days)

    logs = (
        await db.execute(
            select(
                ReviewLog.reviewed_at,
                ReviewLog.final_grade,
                ReviewLog.llm_grade,
                ReviewLog.overridden,
                ReviewLog.state_before,
                ReviewLog.elapsed_days,
                ReviewLog.latency_ms,
                ReviewLog.graduated_to_review,
                ReviewLog.card_id,
            )
            .join(Card, Card.id == ReviewLog.card_id)
            .join(Deck, Deck.id == Card.deck_id)
            .where(Deck.user_id == user.id, ReviewLog.reviewed_at >= since)
        )
    ).all()

    heatmap: dict[str, int] = defaultdict(int)
    total_latency = 0
    latency_n = 0
    graded_by_llm = agreed = overridden = 0
    # A set, not a counter: a lapsed card graduates again on recovery, and
    # "concepts mastered" means the concept, not the graduation event.
    mastered_cards: set[uuid.UUID] = set()
    # Retention bucketed by how long the card was left — the "did I actually
    # remember it after N days" curve, not a running average.
    bucket_hit: dict[str, int] = defaultdict(int)
    bucket_total: dict[str, int] = defaultdict(int)

    for (
        reviewed_at,
        final_grade,
        llm_grade,
        was_overridden,
        state_before,
        elapsed,
        latency,
        graduated,
        log_card_id,
    ) in logs:
        heatmap[day_key(reviewed_at, user.timezone)] += 1
        if latency:
            total_latency += latency
            latency_n += 1
        if llm_grade:
            graded_by_llm += 1
            if llm_grade == final_grade:
                agreed += 1
        if was_overridden:
            overridden += 1
        if graduated:
            mastered_cards.add(log_card_id)
        if state_before == "review" and elapsed is not None:
            bucket_total[_interval_bucket(elapsed)] += 1
            if final_grade != "again":
                bucket_hit[_interval_bucket(elapsed)] += 1

    # Velocity (§ Velocity dashboard): mastered concepts per active hour, not
    # seat time. Active hours come from the Time Bank's own ledger — the same
    # server-counted number bank_totals reports — rather than wall-clock
    # elapsed, so a session left open overnight can't inflate the divisor.
    active_seconds_in_window = await db.scalar(
        select(func.sum(StudySession.active_seconds)).where(
            StudySession.user_id == user.id,
            StudySession.ended_at.isnot(None),
            StudySession.started_at >= since,
        )
    )
    active_hours = (active_seconds_in_window or 0) / 3600.0

    # The rate's numerator must be drawn from the same time the denominator
    # measures. Counting *every* graduation against only timed-block hours
    # lets untimed study inflate the rate without bound — 20 cards mastered
    # outside any block, divided by one five-minute block, reported "240 an
    # hour". So only graduations that happened inside a completed session
    # count here; `mastered_total` below still reports the rest.
    #
    # DISTINCT card: a card that lapses and recovers graduates more than once,
    # and "concepts mastered" should count the concept, not the event.
    mastered_in_sessions = await db.scalar(
        select(func.count(func.distinct(ReviewLog.card_id)))
        .select_from(ReviewLog)
        .join(Card, Card.id == ReviewLog.card_id)
        .join(Deck, Deck.id == Card.deck_id)
        .where(
            Deck.user_id == user.id,
            ReviewLog.reviewed_at >= since,
            ReviewLog.graduated_to_review.is_(True),
            select(StudySession.id)
            .where(
                StudySession.user_id == user.id,
                StudySession.ended_at.isnot(None),
                StudySession.started_at <= ReviewLog.reviewed_at,
                StudySession.ended_at >= ReviewLog.reviewed_at,
            )
            .exists(),
        )
    )
    mastered_in_sessions = int(mastered_in_sessions or 0)

    retention = {
        bucket: round(bucket_hit[bucket] / bucket_total[bucket], 4)
        for bucket in bucket_total
        if bucket_total[bucket] >= 3
    }

    # Forecast: how many cards come due each of the next 30 days.
    forecast: dict[str, int] = defaultdict(int)
    horizon = now + timedelta(days=30)
    upcoming = (
        await db.execute(
            select(Card.due)
            .join(Deck, Deck.id == Card.deck_id)
            .where(
                Deck.user_id == user.id,
                Card.suspended.is_(False),
                Card.state != "new",
                Card.due.isnot(None),
                Card.due <= horizon,
            )
        )
    ).all()
    for (due,) in upcoming:
        forecast[day_key(max(due if due.tzinfo else due.replace(tzinfo=UTC), now), user.timezone)] += 1

    state_counts = {
        row[0]: row[1]
        for row in (
            await db.execute(
                select(Card.state, func.count())
                .join(Deck, Deck.id == Card.deck_id)
                .where(Deck.user_id == user.id, Card.suspended.is_(False))
                .group_by(Card.state)
            )
        ).all()
    }
    avg_stability = await db.scalar(
        select(func.avg(Card.stability))
        .join(Deck, Deck.id == Card.deck_id)
        .where(Deck.user_id == user.id, Card.stability.isnot(None))
    )
    avg_difficulty = await db.scalar(
        select(func.avg(Card.difficulty))
        .join(Deck, Deck.id == Card.deck_id)
        .where(Deck.user_id == user.id, Card.difficulty.isnot(None))
    )

    # IR throughput (§14 Phase 3): extracts worked and cards born from reading.
    extracts_done = await db.scalar(
        select(func.count())
        .select_from(Extract)
        .join(Source, Source.id == Extract.source_id)
        .where(Source.user_id == user.id, Extract.status == "done")
    )
    extracts_active = await db.scalar(
        select(func.count())
        .select_from(Extract)
        .join(Source, Source.id == Extract.source_id)
        .where(Source.user_id == user.id, Extract.status == "active")
    )
    cards_from_ir = await db.scalar(
        select(func.count())
        .select_from(Card)
        .join(Deck, Deck.id == Card.deck_id)
        .where(Deck.user_id == user.id, Card.origin == "extract")
    )
    sources_active = await db.scalar(
        select(func.count()).select_from(Source).where(Source.user_id == user.id, Source.status == "active")
    )

    return StatsOut(
        heatmap=dict(heatmap),
        forecast=dict(forecast),
        retention=retention,
        totals={
            "cards": float(sum(state_counts.values())),
            "new": float(state_counts.get("new", 0)),
            "learning": float(state_counts.get("learning", 0) + state_counts.get("relearning", 0)),
            "review": float(state_counts.get("review", 0)),
            "reviews_logged": float(len(logs)),
            "avg_stability_days": round(float(avg_stability or 0), 2),
            "avg_difficulty": round(float(avg_difficulty or 0), 2),
            "avg_latency_ms": round(total_latency / latency_n, 1) if latency_n else 0.0,
        },
        grading={
            "llm_graded": float(graded_by_llm),
            "agreement_rate": round(agreed / graded_by_llm, 4) if graded_by_llm else 0.0,
            "override_rate": round(overridden / len(logs), 4) if logs else 0.0,
            "bias": user.grading_bias,
        },
        ir_throughput={
            "sources_active": int(sources_active or 0),
            "extracts_active": int(extracts_active or 0),
            "extracts_done": int(extracts_done or 0),
            "cards_from_reading": int(cards_from_ir or 0),
        },
        velocity={
            # The pair that forms the rate: both measured over timed blocks.
            "mastered": float(mastered_in_sessions),
            "active_hours": round(active_hours, 2),
            "per_hour": (
                round(mastered_in_sessions / active_hours, 2) if active_hours > 0 else 0.0
            ),
            # Everything mastered in the window, timed or not — progress, not rate.
            "mastered_total": float(len(mastered_cards)),
        },
        leeches=await _leeches(db, user),
    )


def _interval_bucket(elapsed_days: float) -> str:
    for edge, label in ((1, "0-1d"), (3, "1-3d"), (7, "3-7d"), (21, "1-3w"), (60, "3w-2m"), (180, "2-6m")):
        if elapsed_days < edge:
            return label
    return "6m+"


async def _leeches(db: AsyncSession, user: User) -> list[LeechOut]:
    cards = (
        await db.scalars(
            select(Card)
            .join(Deck, Deck.id == Card.deck_id)
            .where(Deck.user_id == user.id, Card.leech_flag.is_(True))
            .order_by(Card.lapse_count.desc())
            .limit(50)
        )
    ).all()

    out: list[LeechOut] = []
    for card in cards:
        front, back = render(
            card.note.note_type.template_kind, card.note.field_values or {}, card.template_slot
        )
        suggestion = await db.scalar(
            select(LeechSuggestion)
            .where(LeechSuggestion.card_id == card.id, LeechSuggestion.status == "pending")
            .order_by(LeechSuggestion.created_at.desc())
        )
        out.append(
            LeechOut(
                card_id=str(card.id),
                front=front,
                back=back,
                lapse_count=card.lapse_count,
                deck_name=card.deck.name if card.deck else None,
                suggestion_id=str(suggestion.id) if suggestion else None,
                suggestion_kind=suggestion.kind if suggestion else None,
                suggestion_rationale=suggestion.rationale if suggestion else None,
                suggested_cards=(suggestion.payload or {}).get("cards", []) if suggestion else [],
            )
        )
    return out


@router.post("/leeches/{card_id}/dismiss")
async def dismiss_leech(
    card_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> dict:
    """Clear the flag and return the card to rotation unchanged (§3.2 step 3)."""
    card = await _owned_leech(db, user, parse_uuid(card_id))
    card.leech_flag = False
    card.lapse_count = 0
    for s in (
        await db.scalars(
            select(LeechSuggestion).where(
                LeechSuggestion.card_id == card.id, LeechSuggestion.status == "pending"
            )
        )
    ).all():
        s.status = "dismissed"
    await db.commit()
    return {"card_id": str(card.id), "leech_flag": False}


@router.post("/leeches/{card_id}/suspend")
async def suspend_leech(
    card_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> dict:
    """Plain auto-suspend — the opt-out for users who don't want remediation."""
    card = await _owned_leech(db, user, parse_uuid(card_id))
    card.suspended = True
    await db.commit()
    return {"card_id": str(card.id), "suspended": True}


@router.post("/leeches/{card_id}/accept")
async def accept_leech_suggestion(
    card_id: str,
    suggestion_id: str | None = None,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Apply the model's proposal (§3.2 step 3).

    A "rewrite" replaces the note's text in place, keeping the card's schedule.
    A "split" creates the smaller cards and suspends the original, because the
    thing that kept failing is the card that tested too much at once.
    """
    card = await _owned_leech(db, user, parse_uuid(card_id))
    stmt = select(LeechSuggestion).where(
        LeechSuggestion.card_id == card.id, LeechSuggestion.status == "pending"
    )
    if suggestion_id:
        stmt = stmt.where(LeechSuggestion.id == parse_uuid(suggestion_id, "suggestion_id"))
    suggestion = await db.scalar(stmt.order_by(LeechSuggestion.created_at.desc()))
    if suggestion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no pending suggestion for this card")

    proposed = (suggestion.payload or {}).get("cards", [])
    created = 0

    if suggestion.kind == "rewrite" and proposed:
        note = card.note
        first = proposed[0]
        if note.note_type.template_kind == "cloze":
            note.field_values = {**(note.field_values or {}), "Text": first.get("front", "")}
        else:
            note.field_values = {
                **(note.field_values or {}),
                "Front": first.get("front", ""),
                "Back": first.get("back", ""),
            }
        card.leech_flag = False
        card.lapse_count = 0
    elif suggestion.kind == "split" and proposed:
        nt = await default_note_type(db, user, "basic")
        for item in proposed[:4]:
            note = Note(
                user_id=user.id,
                note_type_id=nt.id,
                field_values={"Front": item.get("front", ""), "Back": item.get("back", "")},
            )
            db.add(note)
            await db.flush()
            created += len(
                await sync_cards(
                    db, note, nt, card.deck_id, tags=[*list(card.tags or []), "split-from-leech"]
                )
            )
        card.suspended = True
        card.leech_flag = False
    else:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "this suggestion needs a manual edit — the model flagged the card as ambiguous",
        )

    suggestion.status = "accepted"
    await db.commit()
    return {"card_id": str(card.id), "applied": suggestion.kind, "cards_created": created}


async def _owned_leech(db: AsyncSession, user: User, card_id: uuid.UUID) -> Card:
    card = await db.get(Card, card_id)
    if card is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "card not found")
    deck = await db.get(Deck, card.deck_id)
    if deck is None or deck.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "card not found")
    return card


@router.get("/stats/learning-analytics", response_model=LearningAnalyticsOut)
async def learning_analytics(
    days: int = Query(default=365, ge=1, le=1095),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> LearningAnalyticsOut:
    """Learning Sciences statistical analytics: fatigue curve, chronotype peak,
    item discrimination (r_pb), desirable difficulty yield, and EWMA/SPRT mastery."""
    return await compute_learning_analytics(db, user, days=days)

