"""Stuck-state detection — catch a bad stretch while it's happening.

Two independent signals, either can fire:

**Accuracy.** The last :data:`ACCURACY_WINDOW` reviews (across all decks —
the queue mixes them in one sitting, so "session" means recent wall-clock
activity, not one deck) average below :data:`ACCURACY_THRESHOLD`.

**Latency.** This review took :data:`LATENCY_SPIKE_MULTIPLIER` times longer
than the user's own recent baseline — a personal number, not a fixed
threshold, since normal answer time varies enormously by card type and person.

Both are edge-triggered: they fire on the review that *crosses* the line, not
on every review while the line stays crossed. Without that, a genuine slump
would alert on every single card until accuracy recovered, which trains
exactly the alert-blindness the feature exists to avoid.

Called with the just-graded review's own grade/latency *before* its
:class:`~app.models.ReviewLog` row is written, so the history query never has
to exclude its own result.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Card, Deck, ReviewLog, User

ACCURACY_WINDOW = 5
ACCURACY_THRESHOLD = 0.6
# How far back a review can be and still count as part of "this stretch".
# Without it, four failures today and one after a week away would read as a
# slump happening right now, which is the opposite of what this detects.
ACCURACY_WINDOW_MINUTES = 60
LATENCY_SPIKE_MULTIPLIER = 3.0
# Below this many prior timed answers, "3x the baseline" is noise, not a signal.
LATENCY_BASELINE_MIN_SAMPLES = 8
LATENCY_BASELINE_LIMIT = 200
BREAK_MINUTES = 5


@dataclass
class StuckAlert:
    reason: str  # "accuracy" | "latency"
    message: str
    suggested_break_minutes: int = BREAK_MINUTES


async def _recent_grades(db: AsyncSession, user: User, limit: int) -> list[str]:
    """The user's last `limit` grades, newest first, from this stretch only."""
    since = datetime.now(UTC) - timedelta(minutes=ACCURACY_WINDOW_MINUTES)
    rows = await db.execute(
        select(ReviewLog.final_grade)
        .join(Card, Card.id == ReviewLog.card_id)
        .join(Deck, Deck.id == Card.deck_id)
        .where(Deck.user_id == user.id, ReviewLog.reviewed_at >= since)
        .order_by(ReviewLog.reviewed_at.desc())
        .limit(limit)
    )
    return [r[0] for r in rows.all()]


def _accuracy(grades: list[str]) -> float:
    if not grades:
        return 1.0
    return sum(1 for g in grades if g != "again") / len(grades)


async def _check_accuracy(db: AsyncSession, user: User, final_grade: str) -> StuckAlert | None:
    prior = await _recent_grades(db, user, ACCURACY_WINDOW)
    window = [final_grade, *prior][:ACCURACY_WINDOW]
    if len(window) < ACCURACY_WINDOW:
        return None

    accuracy = _accuracy(window)
    if accuracy >= ACCURACY_THRESHOLD:
        return None

    # Edge-trigger: don't re-alert every card while the slump continues.
    if len(prior) >= ACCURACY_WINDOW and _accuracy(prior[:ACCURACY_WINDOW]) < ACCURACY_THRESHOLD:
        return None

    return StuckAlert(
        reason="accuracy",
        message=f"Accuracy dropped to {round(accuracy * 100)}% over your last {ACCURACY_WINDOW} cards.",
    )


async def _check_latency(db: AsyncSession, user: User, latency_ms: int | None) -> StuckAlert | None:
    if not latency_ms or latency_ms <= 0:
        return None

    rows = await db.execute(
        select(ReviewLog.latency_ms)
        .join(Card, Card.id == ReviewLog.card_id)
        .join(Deck, Deck.id == Card.deck_id)
        .where(Deck.user_id == user.id, ReviewLog.latency_ms.isnot(None))
        .order_by(ReviewLog.reviewed_at.desc())
        .limit(LATENCY_BASELINE_LIMIT)
    )
    samples = [r[0] for r in rows.all() if r[0]]
    if len(samples) < LATENCY_BASELINE_MIN_SAMPLES:
        return None

    # Median, not mean. Answer times are heavily right-skewed: one card the
    # user walked away from drags a mean baseline up enough to switch the
    # detector off. With 199 answers at 2s and a single 30-minute outlier the
    # mean alerts only above 33s, so a genuine 20s stall passes unnoticed —
    # the median is 2s either way.
    baseline = statistics.median(samples)
    if baseline <= 0 or latency_ms < baseline * LATENCY_SPIKE_MULTIPLIER:
        return None

    return StuckAlert(
        reason="latency",
        message=f"That took {round(latency_ms / baseline, 1)}x longer than your usual pace.",
    )


async def check_stuck(
    db: AsyncSession, user: User, *, final_grade: str, latency_ms: int | None
) -> StuckAlert | None:
    """The alert for the review just graded, or None. Accuracy wins ties —
    it's the more actionable signal (latency alone is common and often benign:
    a hard card, a phone call, nothing wrong)."""
    accuracy_alert = await _check_accuracy(db, user, final_grade)
    if accuracy_alert is not None:
        return accuracy_alert
    return await _check_latency(db, user, latency_ms)
