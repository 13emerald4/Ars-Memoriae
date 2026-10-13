"""Timed study sessions and the Time Bank.

The mechanic: commit to a duration and a card target, and whatever time you
don't spend once the target is met is banked as earned free time. It rewards
finishing, not sitting — the opposite of measuring seat time.

Two rules keep the number honest:

**Work is counted server-side.** ``cards_reviewed`` comes from the review log
between the session's start and end, never from the client. A bank you can
inflate by editing a request body measures nothing.

**Time is only banked when the target is met.** Stopping a 60-minute session
after four minutes banks nothing; it just records a short session. Otherwise
"banked time" would be a synonym for "quit early", which is the incentive
this feature exists to avoid creating.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.timeutil import day_start
from app.models import Card, Deck, ReviewLog, StudySession, User

# A session longer than this is almost certainly one someone forgot to close
# rather than a real study block; see close_stale.
MAX_SESSION_HOURS = 12


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


async def current_session(db: AsyncSession, user: User) -> StudySession | None:
    """The user's open session, if any. At most one is ever open."""
    return await db.scalar(
        select(StudySession)
        .where(StudySession.user_id == user.id, StudySession.ended_at.is_(None))
        .order_by(StudySession.started_at.desc())
        .limit(1)
    )


async def count_reviews_between(
    db: AsyncSession, user: User, start: datetime, end: datetime
) -> int:
    """Cards reviewed in a window, straight from the review log.

    Reading extracts don't count: they produce no review log row, and "I read
    three paragraphs" isn't the unit the card target is expressed in.
    """
    return int(
        await db.scalar(
            select(func.count())
            .select_from(ReviewLog)
            .join(Card, Card.id == ReviewLog.card_id)
            .join(Deck, Deck.id == Card.deck_id)
            .where(
                Deck.user_id == user.id,
                ReviewLog.reviewed_at >= start,
                ReviewLog.reviewed_at <= end,
            )
        )
        or 0
    )


async def live_progress(db: AsyncSession, user: User, session: StudySession) -> int:
    """Cards reviewed so far in a session that is still open.

    ``cards_reviewed`` is only written at close, so the stored value on an
    open session is always 0 — the UI needs this to show progress toward the
    target while there is still time to act on it.
    """
    started = _aware(session.started_at)
    if started is None:
        return 0
    return await count_reviews_between(db, user, started, datetime.now(UTC))


async def start_session(
    db: AsyncSession,
    user: User,
    *,
    planned_seconds: int,
    goal_cards: int,
    focus_goal: str | None,
) -> StudySession:
    """Open a session, closing any previous one that was left hanging.

    Only one session is open at a time: a forgotten session from yesterday
    would otherwise keep accruing wall-clock time and quietly poison every
    number derived from it.
    """
    stale = await current_session(db, user)
    if stale is not None:
        await finish_session(db, user, stale, remaining_seconds=0)

    session = StudySession(
        user_id=user.id,
        started_at=datetime.now(UTC),
        planned_seconds=max(0, planned_seconds),
        goal_cards=max(0, goal_cards),
        focus_goal=(focus_goal or "").strip()[:500] or None,
    )
    db.add(session)
    await db.flush()
    return session


async def finish_session(
    db: AsyncSession, user: User, session: StudySession, *, remaining_seconds: int
) -> StudySession:
    """Close a session and settle the bank.

    ``remaining_seconds`` is what was left on the client's countdown, which is
    where the clock actually lives. Active time is derived from it rather than
    reported directly, so pausing correctly costs no study time.

    The only bound applied is ``0 <= banked <= planned``, via clamping
    remaining to the planned duration. Deliberately *not* clamped to wall
    clock: banking legitimately exceeds elapsed time whenever you finish
    fast — a 30-minute block whose target you hit in five banks 25 — so that
    bound would penalise exactly the behaviour the feature rewards. The
    client owns the clock here, and the guard that matters is that you can
    never bank more time than you set aside.
    """
    now = datetime.now(UTC)
    started = _aware(session.started_at) or now

    remaining = max(0, min(remaining_seconds, session.planned_seconds))
    active = max(0, session.planned_seconds - remaining)

    session.ended_at = now
    session.active_seconds = active
    session.cards_reviewed = await count_reviews_between(db, user, started, now)
    # Time is only earned by *finishing*, never by stopping early.
    session.banked_seconds = (
        max(0, session.planned_seconds - active) if session.goal_met else 0
    )
    await db.flush()
    return session


async def close_stale(db: AsyncSession, user: User) -> StudySession | None:
    """Close an open session that has outlived any plausible study block.

    Called on read so a session left open overnight settles itself rather than
    showing a 14-hour timer the next morning.
    """
    session = await current_session(db, user)
    if session is None:
        return None
    started = _aware(session.started_at) or datetime.now(UTC)
    if datetime.now(UTC) - started < timedelta(hours=MAX_SESSION_HOURS):
        return session
    # Nothing left on the clock: a forgotten session banks nothing.
    await finish_session(db, user, session, remaining_seconds=0)
    await db.commit()
    return None


@dataclass
class BankTotals:
    today_seconds: int = 0
    week_seconds: int = 0
    total_seconds: int = 0
    sessions_today: int = 0
    goals_met_today: int = 0


async def bank_totals(db: AsyncSession, user: User, *, now: datetime | None = None) -> BankTotals:
    """Banked time for today, the last 7 days, and all time.

    "Today" is the user's study day (app.core.timeutil), the same boundary
    the queue's daily caps and the stats heatmap use.
    """
    now = now or datetime.now(UTC)
    today = day_start(now, user.timezone)
    week = now - timedelta(days=7)

    async def banked_since(since: datetime | None) -> int:
        stmt = select(func.sum(StudySession.banked_seconds)).where(
            StudySession.user_id == user.id, StudySession.ended_at.isnot(None)
        )
        if since is not None:
            stmt = stmt.where(StudySession.started_at >= since)
        return int(await db.scalar(stmt) or 0)

    sessions_today = int(
        await db.scalar(
            select(func.count())
            .select_from(StudySession)
            .where(
                StudySession.user_id == user.id,
                StudySession.ended_at.isnot(None),
                StudySession.started_at >= today,
            )
        )
        or 0
    )
    goals_met_today = int(
        await db.scalar(
            select(func.count())
            .select_from(StudySession)
            .where(
                StudySession.user_id == user.id,
                StudySession.ended_at.isnot(None),
                StudySession.started_at >= today,
                StudySession.goal_cards > 0,
                StudySession.cards_reviewed >= StudySession.goal_cards,
            )
        )
        or 0
    )

    return BankTotals(
        today_seconds=await banked_since(today),
        week_seconds=await banked_since(week),
        total_seconds=await banked_since(None),
        sessions_today=sessions_today,
        goals_met_today=goals_met_today,
    )


async def recent_sessions(
    db: AsyncSession, user: User, limit: int = 10
) -> list[StudySession]:
    return list(
        (
            await db.scalars(
                select(StudySession)
                .where(StudySession.user_id == user.id, StudySession.ended_at.isnot(None))
                .order_by(StudySession.started_at.desc())
                .limit(limit)
            )
        ).all()
    )


async def owned_session(
    db: AsyncSession, user: User, session_id: uuid.UUID
) -> StudySession | None:
    session = await db.get(StudySession, session_id)
    if session is None or session.user_id != user.id:
        return None
    return session


async def reflect(
    db: AsyncSession,
    session: StudySession,
    *,
    distraction: str | None,
    next_time_plan: str | None,
) -> StudySession:
    """Record the exit half of the focus prompt. Blank text clears a field
    rather than being ignored — editing a reflection down to nothing is a
    valid way to retract it."""
    session.distraction = (distraction or "").strip()[:500] or None
    session.next_time_plan = (next_time_plan or "").strip()[:500] or None
    await db.flush()
    return session
