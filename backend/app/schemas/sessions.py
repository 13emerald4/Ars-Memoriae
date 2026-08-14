"""Timed study sessions and the Time Bank."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SessionStart(BaseModel):
    planned_minutes: int = Field(ge=1, le=600)
    # 0 means "no card target" — the session is then just a timed block and
    # can never bank time, since there is no goal to have met.
    goal_cards: int = Field(default=0, ge=0, le=10_000)
    focus_goal: str | None = Field(default=None, max_length=500)


class SessionFinish(BaseModel):
    # What was left on the client's countdown. Active time is derived from
    # this rather than reported directly, so pausing costs no study time.
    remaining_seconds: int = Field(default=0, ge=0)


class SessionReflect(BaseModel):
    """The exit half of the executive-function prompt (§2). Both optional —
    reflecting is a nudge, not a gate on anything."""

    distraction: str | None = Field(default=None, max_length=500)
    next_time_plan: str | None = Field(default=None, max_length=500)


class StudySessionOut(BaseModel):
    id: str
    started_at: datetime
    ended_at: datetime | None
    planned_seconds: int
    active_seconds: int
    focus_goal: str | None
    goal_cards: int
    cards_reviewed: int
    banked_seconds: int
    goal_met: bool
    distraction: str | None = None
    next_time_plan: str | None = None


class BankOut(BaseModel):
    today_seconds: int
    week_seconds: int
    total_seconds: int
    sessions_today: int
    goals_met_today: int
    current: StudySessionOut | None = None
    recent: list[StudySessionOut] = Field(default_factory=list)
