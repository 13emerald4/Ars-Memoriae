"""Pydantic schemas for Coding Practice and Pre-LeetCode Fundamentals."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CodeProblemSummary(BaseModel):
    id: str
    kind: str  # "fundamental" | "problem"
    track: str | None = None
    title: str
    slug: str
    difficulty: str
    category: str
    tags: list[str] = Field(default_factory=list)
    has_submission: bool = False
    last_status: str | None = None


class CodeProblemOut(BaseModel):
    id: str
    kind: str
    track: str | None = None
    title: str
    slug: str
    difficulty: str
    category: str
    tags: list[str] = Field(default_factory=list)
    description: str
    examples: list[dict[str, Any]] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    starter_codes: dict[str, str] = Field(default_factory=dict)
    solutions: dict[str, str] = Field(default_factory=dict)
    editorial: str | None = None
    test_cases: list[dict[str, Any]] = Field(default_factory=list)
    hints: list[str] = Field(default_factory=list)
    created_at: datetime


class TestCaseResult(BaseModel):
    test_index: int
    passed: bool
    input: Any
    expected: Any
    actual: Any
    stdout: str = ""
    error: str | None = None
    runtime_ms: float = 0.0


class RunCodeRequest(BaseModel):
    code: str
    language: str = "python"
    custom_test_cases: list[dict[str, Any]] | None = None


class RunCodeResponse(BaseModel):
    status: str
    passed_count: int
    total_count: int
    runtime_ms: float
    error: str | None = None
    results: list[TestCaseResult] = Field(default_factory=list)


class SubmitCodeRequest(BaseModel):
    code: str
    language: str = "python"


class SubmitCodeResponse(BaseModel):
    submission_id: str
    status: str
    passed_count: int
    total_count: int
    runtime_ms: float
    results: list[TestCaseResult] = Field(default_factory=list)


class SocraticCodeRequest(BaseModel):
    code: str
    language: str = "python"
    hint_type: str = "conceptual"  # "conceptual" | "edge_case" | "complexity" | "debug"


class SocraticCodeResponse(BaseModel):
    hint: str


class ForgeProblemRequest(BaseModel):
    topic: str
    difficulty: str = "Medium"
    target_language: str = "python"


class ExportToDeckRequest(BaseModel):
    deck_id: str


class CodeSubmissionOut(BaseModel):
    id: str
    problem_id: str
    language: str
    code: str
    status: str
    passed_tests: int
    total_tests: int
    runtime_ms: float | None
    created_at: datetime


class CodeLeechOut(BaseModel):
    problem_id: str
    slug: str
    title: str
    difficulty: str
    category: str
    lapse_count: int
    last_error: str | None = None
    suggestion_kind: str = "conceptual"
    suggestion_rationale: str = "Focus on the core algorithmic pattern and dry-run small test cases."


class CategoryProgression(BaseModel):
    category: str
    total: int
    solved: int
    attempted: int
    percentage: float


class DifficultyTierProgression(BaseModel):
    total: int
    solved: int
    attempted: int
    percentage: float


class CodeProgressionStats(BaseModel):
    totals: dict[str, float]  # cards, in_review, reviews_logged, avg_stability_days, avg_difficulty, solved, attempted
    velocity: dict[str, float]  # rate, mastered_in_sessions, mastered_total, active_hours
    retention: dict[str, float]  # "<1d", "1-3d", "3-7d", etc.
    heatmap: dict[str, int]  # YYYY-MM-DD -> count
    forecast: dict[str, int]  # YYYY-MM-DD -> count
    leeches: list[CodeLeechOut] = Field(default_factory=list)
    categories: list[CategoryProgression] = Field(default_factory=list)
    difficulty: dict[str, DifficultyTierProgression] = Field(default_factory=dict)
    recent_activity: list[CodeSubmissionOut] = Field(default_factory=list)
