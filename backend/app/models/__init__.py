"""ORM models — 1:1 with the DDL in §5.1 of the spec.

Two deliberate portability choices so the same models run on Postgres (the
deployment target) and SQLite (local dev + the test suite):
  * JSONB / TEXT[] are declared as dialect variants of JSON, so PG keeps the
    native types from the spec DDL while SQLite gets a JSON column.
  * UUID columns use SQLAlchemy's portable ``Uuid`` type (native uuid on PG,
    CHAR(32) on SQLite).
Because TEXT[] degrades to JSON on SQLite, tag *filtering* is done in Python
(see queue_service) rather than in SQL, which behaves identically on both.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    SmallInteger,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

JSONType = JSON().with_variant(JSONB(), "postgresql")
StringArray = JSON().with_variant(ARRAY(Text()), "postgresql")


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    google_api_key_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    desired_retention: Mapped[float] = mapped_column(Float, nullable=False, default=0.90)
    grading_model: Mapped[str] = mapped_column(Text, nullable=False, default="gemma-4-e4b-it")
    queue_time_budget_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    leech_remediation_opt_in: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # §3.1 review-load guardrails
    daily_new_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    daily_review_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=200)
    backlog_spread_days: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    leech_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    # §3 personalized FSRS weights, filled in by the optimizer job.
    fsrs_parameters: Mapped[list | None] = mapped_column(JSONType)
    fsrs_optimized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # §15 privacy: explicit consent before any answer text leaves the box.
    llm_grading_consent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # §4.3 per-user calibration bias (signed, in grade steps).
    grading_bias: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    decks: Mapped[list[Deck]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Deck(Base):
    __tablename__ = "decks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("decks.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    desired_retention_override: Mapped[float | None] = mapped_column(Float)
    default_priority: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=50)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    __table_args__ = (
        CheckConstraint("default_priority BETWEEN 0 AND 100", name="ck_decks_priority"),
    )

    user: Mapped[User] = relationship(back_populates="decks")
    cards: Mapped[list[Card]] = relationship(back_populates="deck")


class NoteType(Base):
    __tablename__ = "note_types"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    template_kind: Mapped[str] = mapped_column(Text, nullable=False, default="basic")
    fields: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    grading_profile: Mapped[str] = mapped_column(Text, nullable=False, default="short_answer")

    __table_args__ = (
        CheckConstraint(
            "template_kind IN ('basic','cloze','image_occlusion')", name="ck_note_types_kind"
        ),
        CheckConstraint(
            "grading_profile IN ('short_answer','conceptual','math_code')",
            name="ck_note_types_profile",
        ),
    )


class Source(Base):
    """Incremental Reading source material (§8)."""

    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    raw_text: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=50)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    __table_args__ = (
        CheckConstraint("priority BETWEEN 0 AND 100", name="ck_sources_priority"),
        CheckConstraint("status IN ('active','postponed','done')", name="ck_sources_status"),
    )

    extracts: Mapped[list[Extract]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )


class Extract(Base):
    __tablename__ = "extracts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int | None] = mapped_column(SmallInteger)  # NULL = inherit source
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_shown_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")

    __table_args__ = (
        CheckConstraint("priority BETWEEN 0 AND 100", name="ck_extracts_priority"),
        CheckConstraint("status IN ('active','done')", name="ck_extracts_status"),
        Index("idx_extracts_next_shown", "next_shown_at"),
        Index("idx_extracts_source_status", "source_id", "status"),
    )

    source: Mapped[Source] = relationship(back_populates="extracts")


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    note_type_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("note_types.id"), nullable=False
    )
    field_values: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    note_type: Mapped[NoteType] = relationship(lazy="selectin")
    cards: Mapped[list[Card]] = relationship(
        back_populates="note", cascade="all, delete-orphan"
    )
    media: Mapped[list[MediaAsset]] = relationship(cascade="all, delete-orphan")


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    note_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False
    )
    deck_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("decks.id"), nullable=False)
    template_slot: Mapped[str] = mapped_column(Text, nullable=False, default="default")
    state: Mapped[str] = mapped_column(Text, nullable=False, default="new")
    stability: Mapped[float | None] = mapped_column(Float)
    difficulty: Mapped[float | None] = mapped_column(Float)
    # FSRS learning/relearning sub-step index; None once in the review state.
    step: Mapped[int | None] = mapped_column(Integer)
    due: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_review: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    priority: Mapped[int | None] = mapped_column(SmallInteger)  # NULL = inherit deck default
    origin: Mapped[str] = mapped_column(Text, nullable=False, default="manual")
    origin_extract_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("extracts.id"))
    lapse_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    leech_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    suspended: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tags: Mapped[list[str]] = mapped_column(StringArray, nullable=False, default=list)

    __table_args__ = (
        CheckConstraint(
            "state IN ('new','learning','review','relearning')", name="ck_cards_state"
        ),
        CheckConstraint("priority BETWEEN 0 AND 100", name="ck_cards_priority"),
        CheckConstraint("origin IN ('manual','extract','imported')", name="ck_cards_origin"),
        Index("idx_cards_due", "deck_id", "due"),
        Index("idx_cards_priority", "priority"),
        # Queue-composition hot paths (§9) — see migration 0003.
        Index("idx_cards_state_deck_priority", "state", "deck_id", "priority"),
        Index("idx_cards_state_due", "state", "due"),
    )

    note: Mapped[Note] = relationship(back_populates="cards", lazy="selectin")
    deck: Mapped[Deck] = relationship(back_populates="cards", lazy="selectin")

    @property
    def effective_priority(self) -> int:
        return self.priority if self.priority is not None else self.deck.default_priority


class ReviewLog(Base):
    __tablename__ = "review_logs"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    card_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("cards.id", ondelete="CASCADE"), nullable=False
    )
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    typed_answer: Mapped[str | None] = mapped_column(Text)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    llm_grade: Mapped[str | None] = mapped_column(Text)
    llm_reasoning: Mapped[str | None] = mapped_column(Text)
    llm_confidence: Mapped[float | None] = mapped_column(Float)
    final_grade: Mapped[str] = mapped_column(Text, nullable=False)
    overridden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Retained for the FSRS optimizer, which needs the pre-review state.
    state_before: Mapped[str | None] = mapped_column(Text)
    elapsed_days: Mapped[float | None] = mapped_column(Float)

    __table_args__ = (
        CheckConstraint(
            "final_grade IN ('again','hard','good','easy')", name="ck_review_logs_grade"
        ),
        Index("idx_review_logs_card", "card_id", "reviewed_at"),
    )


class GradingCache(Base):
    __tablename__ = "grading_cache"

    card_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("cards.id", ondelete="CASCADE"), primary_key=True
    )
    answer_hash: Mapped[str] = mapped_column(Text, primary_key=True)
    response: Mapped[dict] = mapped_column(JSONType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    note_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    original_name: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (CheckConstraint("kind IN ('image','audio')", name="ck_media_kind"),)


class QueueConfig(Base):
    __tablename__ = "queue_config"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    review_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    new_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.3)
    ir_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.2)
    seconds_per_review: Mapped[float] = mapped_column(Float, nullable=False, default=12)
    seconds_per_ir_extract: Mapped[float] = mapped_column(Float, nullable=False, default=60)


class Import(Base):
    __tablename__ = "imports"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    notes_mapped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cards_mapped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warnings: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)


class LeechSuggestion(Base):
    """LLM remediation output for a flagged leech (§3.2)."""

    __tablename__ = "leech_suggestions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    card_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("cards.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)  # rewrite | split | ambiguous
    payload: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    rationale: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    __table_args__ = (
        CheckConstraint("kind IN ('rewrite','split','ambiguous')", name="ck_leech_kind"),
        CheckConstraint(
            "status IN ('pending','accepted','dismissed')", name="ck_leech_status"
        ),
    )


class SisterPair(Base):
    """Two notes detected as confusable with each other (§2, §14 Phase 4)."""

    __tablename__ = "sister_pairs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    note_a_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False
    )
    note_b_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False
    )
    front_similarity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    back_similarity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    kind: Mapped[str] = mapped_column(Text, nullable=False, default="interference")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    __table_args__ = (
        CheckConstraint(
            "kind IN ('interference','duplicate','convergent')", name="ck_sister_kind"
        ),
        CheckConstraint("status IN ('open','dismissed')", name="ck_sister_status"),
        UniqueConstraint("note_a_id", "note_b_id", name="uq_sister_pair"),
        Index("idx_sister_user", "user_id", "status"),
    )


__all__ = [
    "Base",
    "Card",
    "Deck",
    "Extract",
    "GradingCache",
    "Import",
    "LeechSuggestion",
    "MediaAsset",
    "Note",
    "NoteType",
    "QueueConfig",
    "ReviewLog",
    "SisterPair",
    "Source",
    "User",
    "utcnow",
]
