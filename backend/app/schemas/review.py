"""Review-cycle contract (§7.1) — the three types Review.tsx needs."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


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
    # The card's reference answer, sent up front so "show answer" is a local
    # UI reveal rather than a round trip — grading (POST .../answer) is a
    # separate, LLM-backed opinion about a *typed* answer, not the only way
    # to learn what the card's back says.
    back: str | None = None
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
    # Where this card's answer comes from in the uploaded document. Sent with
    # the card so the reveal can show the reading without a round trip.
    references: list[dict] = Field(default_factory=list)
    # Coding problem metadata for the LeetCode 50/50 Split IDE
    starter_code: str | None = None
    starter_tests: str | None = None
    test_cases: list[dict] = Field(default_factory=list)
    time_complexity: str | None = None
    space_complexity: str | None = None
    edge_cases: list[str] = Field(default_factory=list)
    title: str | None = None
    difficulty: str | None = None
    category: str | None = None
    # Longitudinal Weakness Memory
    active_weaknesses: list[str] = Field(default_factory=list)
    weakness_history: list[dict] = Field(default_factory=list)
    # Thematic context, documentation & source documents
    deck_documentation: str | None = None
    deck_thematic_nature: str | None = None
    deck_source_documents: list[dict | str] = Field(default_factory=list)
    card_documentation: str | None = None
    card_thematic_nature: str | None = None
    card_source_documents: list[dict | str] = Field(default_factory=list)
    lexicon_glosses: list[dict] = Field(default_factory=list)


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
    test_code: str | None = None
    latency_ms: int
    model: str | None = None
    allow_smaller_model: bool = True

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str | None) -> str | None:
        if v is not None:
            from app.services.grading_service import is_allowed_qwen_coder_model

            if not is_allowed_qwen_coder_model(v):
                raise ValueError(
                    f"Model '{v}' is not permitted. Only quantized Qwen 2.5 Coder models in 7B, 3B, or 1.5B sizes are allowed."
                )
        return v


class RunReviewCodeRequest(BaseModel):
    code: str
    test_code: str | None = None
    custom_test_cases: list[dict] = Field(default_factory=list)
    language: str = "python"


class SubmitAnswerResponse(BaseModel):
    suggested_grade: Grade
    # 0-100 correctness score — the primary grading feedback (§4.1). None in
    # manual/degraded mode, where there is no automated assessment to show.
    score: float | None = None
    confidence: float
    matched_points: list[str] = Field(default_factory=list)
    missed_points: list[str] = Field(default_factory=list)
    overlooked_phrases: list[str] = Field(default_factory=list)
    # Longitudinal Weakness Tracking
    weaknesses: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    persistent_weaknesses: list[str] = Field(default_factory=list)
    reasoning: str
    degraded_to_manual: bool = False  # true when §4.3 fallback triggered
    # §4.3 extras
    reference_answer: str = ""
    needs_confirmation: bool = False
    heuristic_overlap: float | None = None
    model_used: str | None = None
    cached: bool = False
    degraded_reason: str | None = None
    # Informational only — response time never factors into the grade (§4.1).
    latency_note: str | None = None
    # Memory Athlete / Automaticity Latency Thresholding (§Feature 4)
    automaticity_exceeded: bool = False
    automaticity_threshold_ms: int | None = None
    automaticity_note: str | None = None
    # VRAM / Memory Constraint Interactivity
    vram_constrained: bool = False
    failed_model: str | None = None
    fallback_model: str | None = None
    available_fallback_models: list[str] = Field(default_factory=list)


class WeaknessHintResponse(BaseModel):
    hint: str
    active_weaknesses: list[str] = Field(default_factory=list)
    has_past_weaknesses: bool = False


class LessonOut(BaseModel):
    """Learn & Practice: what to teach before this card's question."""

    # False only when the card has no citations to teach from — the mode is
    # built on the document-import path's references.
    available: bool
    # Why the lesson is absent, or why it fell back to the raw source.
    reason: str | None = None
    body: str = ""
    key_points: list[str] = Field(default_factory=list)
    # False when the body is the cited passage verbatim rather than a written
    # lesson, so the UI can label it honestly.
    generated: bool = False
    model_used: str | None = None
    cached: bool = False
    citations: list[dict] = Field(default_factory=list)


class SocraticTurn(BaseModel):
    role: str  # "guide" | "student"
    text: str = Field(max_length=1000)


class SocraticRequest(BaseModel):
    """The conversation so far, plus whatever the student just typed. Empty
    `message` on an empty `history` means "just started — ask an opener"."""

    history: list[SocraticTurn] = Field(default_factory=list, max_length=20)
    message: str = Field(default="", max_length=1000)
    model: str | None = None
    allow_smaller_model: bool = True

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str | None) -> str | None:
        if v is not None:
            from app.services.grading_service import is_allowed_qwen_coder_model

            if not is_allowed_qwen_coder_model(v):
                raise ValueError(
                    f"Model '{v}' is not permitted. Only quantized Qwen 2.5 Coder models in 7B, 3B, or 1.5B sizes are allowed."
                )
        return v


class SocraticResponse(BaseModel):
    message: str
    on_track: bool = False
    degraded: bool = False
    degraded_reason: str | None = None
    model_used: str | None = None
    vram_constrained: bool = False
    failed_model: str | None = None
    fallback_model: str | None = None
    available_fallback_models: list[str] = Field(default_factory=list)


class SocraticLineHintRequest(BaseModel):
    code: str
    line_number: int
    language: str = "typescript"
    test_code: str | None = None
    model: str | None = None
    allow_smaller_model: bool = True

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str | None) -> str | None:
        if v is not None:
            from app.services.grading_service import is_allowed_qwen_coder_model

            if not is_allowed_qwen_coder_model(v):
                raise ValueError(
                    f"Model '{v}' is not permitted. Only quantized Qwen 2.5 Coder models in 7B, 3B, or 1.5B sizes are allowed."
                )
        return v


class SocraticLineHintResponse(BaseModel):
    hint: str
    target_concept: str | None = None
    line_number: int
    current_line_text: str
    degraded: bool = False
    degraded_reason: str | None = None


class ConfirmReviewRequest(BaseModel):
    final_grade: Grade
    overridden: bool = False
    typed_answer: str | None = None
    latency_ms: int | None = None
    confidence: int | None = Field(default=None, ge=1, le=4)
    is_blitz: bool = False


class StuckAlertOut(BaseModel):
    """A real-time nudge that this stretch is going badly (§ Stuck-state
    detector) — accuracy or per-answer time crossing a line, not a per-card
    verdict like leech flagging."""

    reason: str  # "accuracy" | "latency"
    message: str
    suggested_break_minutes: int


class ConfirmReviewResponse(BaseModel):
    next_due: datetime
    new_stability: float
    new_difficulty: float
    state: str
    interval_days: float
    lapse_count: int
    leech_flagged: bool = False
    stuck_alert: StuckAlertOut | None = None
    automaticity_exceeded: bool = False
