"""Nightly per-user FSRS parameter refit (§3, §14.1 Phase 3).

Anki needs ~1000 reviews for a good fit; below that we ship the library
defaults rather than overfitting to noise. The optimizer itself lives behind
the ``fsrs[optimizer]`` extra because it pulls in torch, so this job degrades
to a no-op (with a log line) on the default image instead of crashing.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.models import Card, Deck, ReviewLog, User
from app.services.fsrs_service import GRADE_TO_RATING, FSRSService

log = logging.getLogger(__name__)

MIN_REVIEWS_FOR_FIT = 1000


async def collect_review_logs(db: AsyncSession, user: User) -> list:
    """Shape the persisted rows into what the FSRS Optimizer expects."""
    from fsrs import ReviewLog as FSRSReviewLog

    rows = (
        await db.execute(
            select(ReviewLog.card_id, ReviewLog.reviewed_at, ReviewLog.final_grade, ReviewLog.latency_ms)
            .join(Card, Card.id == ReviewLog.card_id)
            .join(Deck, Deck.id == Card.deck_id)
            .where(Deck.user_id == user.id)
            .order_by(ReviewLog.card_id, ReviewLog.reviewed_at)
        )
    ).all()

    out = []
    for card_id, reviewed_at, grade, _latency in rows:
        when = reviewed_at if reviewed_at.tzinfo else reviewed_at.replace(tzinfo=UTC)
        out.append(
            FSRSReviewLog(
                card_id=int(card_id.int % (2**63)),  # optimizer keys on an int id
                rating=GRADE_TO_RATING[grade],
                review_datetime=when,
                review_duration=None,
            )
        )
    return out


async def optimize_user(db: AsyncSession, user: User) -> bool:
    if not FSRSService.optimizer_available():
        log.info("fsrs optimizer extra not installed; skipping refit for %s", user.email)
        return False

    count = await db.scalar(
        select(func.count())
        .select_from(ReviewLog)
        .join(Card, Card.id == ReviewLog.card_id)
        .join(Deck, Deck.id == Card.deck_id)
        .where(Deck.user_id == user.id)
    )
    if (count or 0) < MIN_REVIEWS_FOR_FIT:
        log.info("user %s has %s reviews (<%s); keeping defaults", user.email, count, MIN_REVIEWS_FOR_FIT)
        return False

    logs = await collect_review_logs(db, user)
    try:
        # Fitting is CPU-bound; keep it off the event loop.
        weights = await asyncio.to_thread(FSRSService.optimize, logs)
    except Exception as exc:
        log.warning("FSRS optimize failed for %s: %s", user.email, exc)
        return False

    user.fsrs_parameters = [float(w) for w in weights]
    user.fsrs_optimized_at = datetime.now(UTC)
    await db.commit()
    log.info("refit FSRS parameters for %s from %s reviews", user.email, count)
    return True


async def run_for_all_users() -> dict:
    """Entry point for the nightly APScheduler job."""
    results = {"optimized": 0, "skipped": 0}
    async with SessionLocal() as db:
        users = (await db.scalars(select(User))).all()
        for user in users:
            if await optimize_user(db, user):
                results["optimized"] += 1
            else:
                results["skipped"] += 1
    return results
