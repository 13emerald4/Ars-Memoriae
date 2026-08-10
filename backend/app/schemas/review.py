"""Review-cycle contract (§7.1) — the three types Review.tsx needs."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Grade(str, Enum):
    again = "again"
    hard = "hard"
    good = "good"
    easy = "easy"


class QueueItem(BaseModel):
    kind: str  # "card" | "extract"
    id: str
    deck_or_source_id: str
    front: str | None = None  # populated when kind == "card"
    extract_content: str | None = None  # populated when kind == "extract"
    priority: int
    # Beyond the §7.1 minimum, so the UI can label and route without a
    # second round-trip per item.
    effective_priority: float = 0
    deck_name: str | None = None
    source_title: str | None = None
    state: str | None = None
    template_kind: str | None = None
    grading_profile: str | None = None
    note_id: str | None = None
    # Populated for image-occlusion cards so the UI can draw the masks (Phase 4).
    occlusion: dict | None = None


class SessionSummary(BaseModel):
    """What GET /api/queue/session returns — the composed plan's shape, used to
    render the session header and the §3.1 guardrail notices."""

    counts: dict[str, int]
    caps: dict[str, int]
    budget_seconds: float
    notes: list[str] = Field(default_factory=list)
    items: list[QueueItem] = Field(default_factory=list)


class SubmitAnswerRequest(BaseModel):
    typed_answer: str
    latency_ms: int


class SubmitAnswerResponse(BaseModel):
    suggested_grade: Grade
    confidence: float
    matched_points: list[str] = Field(default_factory=list)
    missed_points: list[str] = Field(default_factory=list)
    reasoning: str
    degraded_to_manual: bool = False  # true when §4.3 fallback triggered
    # §4.3 extras
    reference_answer: str = ""
    needs_confirmation: bool = False
    heuristic_overlap: float | None = None
    model_used: str | None = None
    cached: bool = False
    degraded_reason: str | None = None


class ConfirmReviewRequest(BaseModel):
    final_grade: Grade
    overridden: bool = False
    typed_answer: str | None = None
    latency_ms: int | None = None


class ConfirmReviewResponse(BaseModel):
    next_due: datetime
    new_stability: float
    new_difficulty: float
    state: str
    interval_days: float
    lapse_count: int
    leech_flagged: bool = False
