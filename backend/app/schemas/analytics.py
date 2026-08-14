"""Schemas for Learning Sciences Statistical Analytics.

Grounded in Cognitive Load Theory, Chronobiology, Item Response Theory,
Desirable Difficulties, Metacognitive Calibration, and Sequential Testing (Wald's SPRT / EWMA).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class FatiguePoint(BaseModel):
    minute_bucket: str
    elapsed_minutes: float
    review_count: int
    accuracy: float
    avg_latency_ms: float


class SessionFatigueOut(BaseModel):
    curve: list[FatiguePoint] = Field(default_factory=list)
    optimal_focus_minutes: int = 25
    baseline_accuracy: float = 0.0
    breakpoint_accuracy: float = 0.0
    recommendation: str = ""


class ChronotypeHour(BaseModel):
    hour: int
    review_count: int
    accuracy: float
    avg_latency_ms: float
    avg_stability_gain: float
    efficiency_score: float


class ChronotypeOut(BaseModel):
    hourly: list[ChronotypeHour] = Field(default_factory=list)
    peak_window_start: int = 9
    peak_window_end: int = 12
    optimal_study_time: str = ""
    summary: str = ""


class DiscriminatedCard(BaseModel):
    card_id: str
    front: str
    back: str
    deck_name: str | None = None
    review_count: int
    pass_rate: float
    point_biserial_r: float
    classification: str  # "high" | "moderate" | "ambiguous"
    rationale: str


class ItemDiscriminationOut(BaseModel):
    high_discrimination: list[DiscriminatedCard] = Field(default_factory=list)
    ambiguous_cards: list[DiscriminatedCard] = Field(default_factory=list)
    overall_deck_r: float = 0.0


class YieldPoint(BaseModel):
    retrievability_bucket: str
    avg_retrievability: float
    review_count: int
    avg_stability_gain: float
    yield_ratio: float


class DesirableDifficultyOut(BaseModel):
    curve: list[YieldPoint] = Field(default_factory=list)
    optimal_retention_target: float = 0.90
    summary: str = ""


class CalibrationBucket(BaseModel):
    confidence_level: int
    label: str
    predicted_prob: float
    observed_accuracy: float
    review_count: int


class MetacognitiveOut(BaseModel):
    calibration_curve: list[CalibrationBucket] = Field(default_factory=list)
    brier_score: float = 0.0
    overconfidence_index: float = 0.0
    hypercorrection_retention: float = 0.0
    calibration_verdict: str = ""


class EWMAScore(BaseModel):
    node_id: str
    title: str
    kind: str
    ewma_pct: float
    sample_size: int


class SPRTVerdictOut(BaseModel):
    node_id: str
    title: str
    log_likelihood_ratio: float
    threshold_upper: float
    threshold_lower: float
    verdict: str  # "mastered" | "unmastered" | "testing"
    cards_evaluated: int


class LearningAnalyticsOut(BaseModel):
    fatigue: SessionFatigueOut
    chronotype: ChronotypeOut
    item_discrimination: ItemDiscriminationOut
    desirable_difficulty: DesirableDifficultyOut
    metacognition: MetacognitiveOut
    ewma_mastery: list[EWMAScore] = Field(default_factory=list)
    sprt_gating: list[SPRTVerdictOut] = Field(default_factory=list)
