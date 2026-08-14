"""Auth, settings, deck/note/card CRUD, IR, import and stats schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator

# ── auth & settings ─────────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    email: str
    desired_retention: float
    grading_model: str
    queue_time_budget_minutes: int
    leech_remediation_opt_in: bool
    daily_new_limit: int
    daily_review_limit: int
    backlog_spread_days: int
    leech_threshold: int
    llm_grading_consent: bool
    has_api_key: bool
    api_key_masked: str | None = None
    fsrs_optimized_at: datetime | None = None
    grading_bias: float = 0.0


class UserUpdate(BaseModel):
    desired_retention: float | None = Field(default=None, ge=0.7, le=0.99)
    grading_model: str | None = None
    queue_time_budget_minutes: int | None = Field(default=None, ge=1, le=600)
    leech_remediation_opt_in: bool | None = None
    daily_new_limit: int | None = Field(default=None, ge=0, le=9999)
    daily_review_limit: int | None = Field(default=None, ge=0, le=99999)
    backlog_spread_days: int | None = Field(default=None, ge=1, le=60)
    leech_threshold: int | None = Field(default=None, ge=2, le=100)
    llm_grading_consent: bool | None = None


class ApiKeyRequest(BaseModel):
    api_key: str = Field(min_length=10)


class ApiKeyResponse(BaseModel):
    stored: bool
    masked: str | None = None
    available_models: list[str] = Field(default_factory=list)
    warning: str | None = None


class QueueConfigOut(BaseModel):
    review_weight: float
    new_weight: float
    ir_weight: float
    seconds_per_review: float
    seconds_per_ir_extract: float


class QueueConfigUpdate(BaseModel):
    review_weight: float | None = Field(default=None, ge=0, le=1)
    new_weight: float | None = Field(default=None, ge=0, le=1)
    ir_weight: float | None = Field(default=None, ge=0, le=1)
    seconds_per_review: float | None = Field(default=None, gt=0, le=600)
    seconds_per_ir_extract: float | None = Field(default=None, gt=0, le=3600)


# ── decks / notes / cards ───────────────────────────────────────────────────


class DeckCreate(BaseModel):
    name: str
    parent_id: str | None = None
    desired_retention_override: float | None = Field(default=None, ge=0.7, le=0.99)
    default_priority: int = Field(default=50, ge=0, le=100)


class DeckUpdate(BaseModel):
    name: str | None = None
    parent_id: str | None = None
    desired_retention_override: float | None = Field(default=None, ge=0.7, le=0.99)
    default_priority: int | None = Field(default=None, ge=0, le=100)


class DeckOut(BaseModel):
    id: str
    name: str
    parent_id: str | None
    desired_retention_override: float | None
    default_priority: int
    card_count: int = 0
    due_count: int = 0
    new_count: int = 0


class NoteTypeCreate(BaseModel):
    name: str
    template_kind: str = "basic"
    fields: dict = Field(default_factory=dict)
    grading_profile: str = "short_answer"


class NoteTypeOut(BaseModel):
    id: str
    name: str
    template_kind: str
    fields: dict
    grading_profile: str


class NoteCreate(BaseModel):
    deck_id: str
    note_type_id: str | None = None
    template_kind: str | None = None  # convenience: pick/create a default note type
    field_values: dict
    tags: list[str] = Field(default_factory=list)
    priority: int | None = Field(default=None, ge=0, le=100)


class NoteUpdate(BaseModel):
    field_values: dict | None = None
    tags: list[str] | None = None


class CardOut(BaseModel):
    id: str
    note_id: str
    deck_id: str
    deck_name: str | None = None
    template_slot: str
    state: str
    due: datetime | None
    stability: float | None
    difficulty: float | None
    priority: int
    lapse_count: int
    leech_flag: bool
    suspended: bool
    tags: list[str]
    front: str
    back: str
    occlusion: dict | None = None


class NoteOut(BaseModel):
    id: str
    note_type_id: str
    template_kind: str
    field_values: dict
    created_at: datetime
    cards: list[CardOut] = Field(default_factory=list)


class SisterPairOut(BaseModel):
    """A pair of notes detected as confusable (§2, §14 Phase 4)."""

    id: str
    kind: str  # interference | duplicate | convergent
    status: str
    front_similarity: float
    back_similarity: float
    note_a_id: str
    note_b_id: str
    front_a: str = ""
    back_a: str = ""
    front_b: str = ""
    back_b: str = ""


class PriorityUpdate(BaseModel):
    """PATCH /api/priority — one endpoint for deck | card | source (§7)."""

    target: str  # "deck" | "card" | "source" | "extract"
    id: str
    priority: int = Field(ge=0, le=100)


# ── incremental reading (§8) ────────────────────────────────────────────────


class SourceCreate(BaseModel):
    title: str | None = None
    raw_text: str | None = None
    url: str | None = None
    priority: int = Field(default=50, ge=0, le=100)
    # File the new source under a knowledge-tree branch instead of the root.
    parent_node_id: str | None = None


class SourceOut(BaseModel):
    id: str
    title: str
    url: str | None
    priority: int
    status: str
    created_at: datetime
    extract_count: int = 0
    active_extract_count: int = 0
    # False for a document uploaded to generate cards from — it never appears
    # in the composed Review queue as something to read (§9).
    for_reading: bool = True


class ExtractOut(BaseModel):
    id: str
    source_id: str
    source_title: str | None = None
    content: str
    priority: int
    position: int
    # "p. 42" / "§ 3.1" for uploaded documents; None for pasted text and URLs.
    locator: str | None = None
    next_shown_at: datetime | None
    status: str


class ExtractSplitRequest(BaseModel):
    """Carve a child extract out of a parent (§7). Either supply the exact
    text, or a character span within the parent's content."""

    text: str | None = None
    start: int | None = None
    end: int | None = None
    priority: int | None = Field(default=None, ge=0, le=100)
    remove_from_parent: bool = True


class ExtractScheduleRequest(BaseModel):
    days: int | None = Field(default=None, ge=0, le=3650)
    status: str | None = None  # "active" | "done"
    priority: int | None = Field(default=None, ge=0, le=100)


class GenerateCardsRequest(BaseModel):
    text: str | None = None  # highlighted span; defaults to the whole extract
    max_cards: int = Field(default=5, ge=1, le=10)
    model: str | None = None
    thinking_budget: int | None = Field(default=None)


class SuggestedCard(BaseModel):
    kind: str
    front: str
    back: str
    cloze_text: str | None = None


class GenerateCardsResponse(BaseModel):
    suggestions: list[SuggestedCard] = Field(default_factory=list)
    degraded: bool = False
    reason: str | None = None


class AcceptCardsRequest(BaseModel):
    deck_id: str
    cards: list[SuggestedCard]
    priority: int | None = Field(default=None, ge=0, le=100)


# ── import (§11) ────────────────────────────────────────────────────────────


class JsonImportNote(BaseModel):
    kind: str = "basic"  # "basic" | "cloze"
    front: str | None = Field(default=None, max_length=20_000)
    back: str | None = Field(default=None, max_length=20_000)
    cloze_text: str | None = Field(default=None, max_length=20_000)
    tags: list[str] = Field(default_factory=list, max_length=50)
    priority: int | None = Field(default=None, ge=0, le=100)

    @model_validator(mode="before")
    @classmethod
    def _accept_common_flashcard_shapes(cls, data):
        """LLM flashcard generators overwhelmingly export ``card_type`` /
        ``question`` / ``answer`` rather than our ``kind`` / ``front`` /
        ``back`` — translate instead of forcing every upload through one exact
        vocabulary. Only fills in fields the caller didn't already set, so an
        upload already using our names is untouched."""
        if not isinstance(data, dict):
            return data
        data = dict(data)
        card_type = data.get("card_type")
        if "kind" not in data and card_type:
            data["kind"] = "cloze" if str(card_type).strip().lower() == "cloze" else "basic"
        is_cloze = data.get("kind", "basic") == "cloze"

        question = data.get("question")
        if question is not None:
            data.setdefault("cloze_text" if is_cloze else "front", question)
        answer = data.get("answer")
        if answer is not None:
            data.setdefault("back", answer)
        return data


class JsonImportRequest(BaseModel):
    deck: str = Field(min_length=1, max_length=200)
    # Only applied if `deck` doesn't already exist — an upload into an
    # existing deck should never silently change its priority.
    priority: int | None = Field(default=None, ge=0, le=100)
    notes: list[JsonImportNote] = Field(min_length=1, max_length=5000)


class JsonImportResult(BaseModel):
    deck_id: str
    deck_created: bool
    notes_created: int
    cards_created: int
    warnings: list[str] = Field(default_factory=list)


class ImportResult(BaseModel):
    id: str
    filename: str
    notes_mapped: int
    cards_mapped: int
    review_logs_mapped: int = 0
    media_copied: int = 0
    decks_created: int = 0
    warnings: list[str] = Field(default_factory=list)
    fsrs_optimized: bool = False


# ── stats (§7) ──────────────────────────────────────────────────────────────


class LeechOut(BaseModel):
    card_id: str
    front: str
    back: str
    lapse_count: int
    deck_name: str | None
    suggestion_id: str | None = None
    suggestion_kind: str | None = None
    suggestion_rationale: str | None = None
    suggested_cards: list[dict] = Field(default_factory=list)


class StatsOut(BaseModel):
    heatmap: dict[str, int]
    forecast: dict[str, int]
    retention: dict[str, float]
    totals: dict[str, float]
    grading: dict[str, float]
    ir_throughput: dict[str, int]
    velocity: dict[str, float]
    leeches: list[LeechOut] = Field(default_factory=list)
