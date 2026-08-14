"""Timed study sessions and the Time Bank.

Start a block with a duration and a card target; finish it and whatever time
you didn't spend — provided you hit the target — is banked as earned free
time. See services/session_service.py for why the work count is server-side
and why missing the target banks nothing.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import StudySession, User
from app.routers.deps import current_user, parse_uuid
from app.schemas.sessions import (
    BankOut,
    SessionFinish,
    SessionReflect,
    SessionStart,
    StudySessionOut,
)
from app.services import session_service

router = APIRouter(prefix="/api/sessions", tags=["study-sessions"])


def _out(session: StudySession) -> StudySessionOut:
    return StudySessionOut(
        id=str(session.id),
        started_at=session.started_at,
        ended_at=session.ended_at,
        planned_seconds=session.planned_seconds,
        active_seconds=session.active_seconds,
        focus_goal=session.focus_goal,
        goal_cards=session.goal_cards,
        cards_reviewed=session.cards_reviewed,
        banked_seconds=session.banked_seconds,
        goal_met=session.goal_met,
        distraction=session.distraction,
        next_time_plan=session.next_time_plan,
    )


@router.post("/start", response_model=StudySessionOut, status_code=201)
async def start(
    body: SessionStart,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> StudySessionOut:
    """Open a timed block. Any session left hanging is settled first."""
    session = await session_service.start_session(
        db,
        user,
        planned_seconds=body.planned_minutes * 60,
        goal_cards=body.goal_cards,
        focus_goal=body.focus_goal,
    )
    await db.commit()
    await db.refresh(session)
    return _out(session)


@router.post("/{session_id}/finish", response_model=StudySessionOut)
async def finish(
    session_id: str,
    body: SessionFinish,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> StudySessionOut:
    session = await session_service.owned_session(db, user, parse_uuid(session_id))
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "session not found")
    if session.ended_at is not None:
        # Already settled — return it as-is rather than re-banking. Double
        # submits happen (timer fires and the user also clicks End).
        return _out(session)

    await session_service.finish_session(
        db, user, session, remaining_seconds=body.remaining_seconds
    )
    await db.commit()
    await db.refresh(session)
    return _out(session)


@router.post("/{session_id}/reflect", response_model=StudySessionOut)
async def reflect(
    session_id: str,
    body: SessionReflect,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> StudySessionOut:
    """The exit half of the focus prompt (§2) — asked after the block ends,
    never blocking the finish itself (that has to complete even when nobody's
    there to answer, e.g. a countdown that runs out unattended)."""
    session = await session_service.owned_session(db, user, parse_uuid(session_id))
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "session not found")
    if session.ended_at is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "session hasn't finished yet")

    await session_service.reflect(
        db, session, distraction=body.distraction, next_time_plan=body.next_time_plan
    )
    await db.commit()
    await db.refresh(session)
    return _out(session)


@router.get("/bank", response_model=BankOut)
async def bank(
    recent: int = Query(default=8, ge=0, le=50),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> BankOut:
    """Banked time plus the open session, if there is one."""
    # A session left open overnight settles itself here rather than showing a
    # 14-hour timer the next morning.
    open_session = await session_service.close_stale(db, user)
    totals = await session_service.bank_totals(db, user)

    current = None
    if open_session is not None:
        current = _out(open_session)
        # cards_reviewed is only written at close, so an open session's stored
        # value is always 0. Fill in live progress here — a target you can't
        # watch yourself approach is just a number you typed once.
        current.cards_reviewed = await session_service.live_progress(db, user, open_session)
        current.goal_met = (
            open_session.goal_cards > 0 and current.cards_reviewed >= open_session.goal_cards
        )

    return BankOut(
        today_seconds=totals.today_seconds,
        week_seconds=totals.week_seconds,
        total_seconds=totals.total_seconds,
        sessions_today=totals.sessions_today,
        goals_met_today=totals.goals_met_today,
        current=current,
        recent=[_out(s) for s in await session_service.recent_sessions(db, user, recent)],
    )
