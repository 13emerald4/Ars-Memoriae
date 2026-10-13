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
    desired_retention: Mapped[float] = mapped_column(Float, nullable=False, default=0.90)
    grading_model: Mapped[str] = mapped_column(Text, nullable=False, default="qwen2.5-coder:7b")
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
    # Memory Champion / Automaticity & Event Horizon fields
    automaticity_threshold_ms: Mapped[int | None] = mapped_column(Integer, nullable=True, default=3000)
    target_event_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    target_event_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    peak_retention_target: Mapped[float | None] = mapped_column(Float, nullable=True, default=0.95)
    # Module navigation visibility toggles
    show_pre_leetcode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    show_code_lab: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    show_thematic_context: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
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
    target_event_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    target_event_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    documentation: Mapped[str | None] = mapped_column(Text, nullable=True)
    thematic_nature: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_documents: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
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
    # False for a document uploaded purely to generate cards from: its extracts
    # exist to be cited, not to be surfaced as something to read, so they must
    # never enter the composed queue's IR stream (§9). True (the default) is
    # the original Incremental Reading source — paste text/URL, read it.
    for_reading: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
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
    # Where in the document this came from — "p. 42", "§ 3.1". Populated when a
    # source was uploaded as a document; NULL for pasted text and URLs, whose
    # chunks have no citable location.
    locator: Mapped[str | None] = mapped_column(Text)
    next_shown_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")

    __table_args__ = (
        CheckConstraint("priority BETWEEN 0 AND 100", name="ck_extracts_priority"),
        CheckConstraint("status IN ('active','done')", name="ck_extracts_status"),
        Index("idx_extracts_next_shown", "next_shown_at"),
        Index("idx_extracts_source_status", "source_id", "status"),
    )

    source: Mapped[Source] = relationship(back_populates="extracts")


class KnowledgeNode(Base):
    """A node in the unified knowledge tree — SuperMemo's contribution (§2).

    Decks hold cards and sources hold reading material, but neither can hold
    the *other*, so "everything I know about pharmacology" had nowhere to live.
    This is one hierarchy over both: a branch can mix topics, decks, sources
    and extracts freely, and an extract carved out of another extract hangs
    beneath it, which is the lineage the IR loop was already creating but
    throwing away.

    The tree *overlays* the existing tables rather than replacing them — a node
    points at the deck/source/extract it stands for, and pure ``topic`` nodes
    point at nothing. Scheduling still reads priority off the entities
    themselves, so there is exactly one number the scheduler can see; the tree
    is what *writes* that number down a branch (see tree_service.cascade).
    """

    __tablename__ = "knowledge_nodes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("knowledge_nodes.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False, default="topic")
    title: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # NULL = inherit from the nearest ancestor that sets one (§9 priority).
    priority: Mapped[int | None] = mapped_column(SmallInteger)
    collapsed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Mastery gating: this node stays locked (its cards excluded from the
    # queue) until `requires_node_id`'s subtree mastery reaches
    # `mastery_threshold`. NULL requires_node_id = ungated, the default for
    # every node. SET NULL on delete: removing the prerequisite un-gates
    # rather than cascading the lock into a dangling reference.
    requires_node_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("knowledge_nodes.id", ondelete="SET NULL")
    )
    mastery_threshold: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=90)

    deck_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("decks.id", ondelete="CASCADE")
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("sources.id", ondelete="CASCADE")
    )
    extract_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("extracts.id", ondelete="CASCADE")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    __table_args__ = (
        CheckConstraint(
            "kind IN ('topic','deck','source','extract')", name="ck_nodes_kind"
        ),
        CheckConstraint("priority BETWEEN 0 AND 100", name="ck_nodes_priority"),
        Index("idx_nodes_user_parent", "user_id", "parent_id", "position"),
        # The gating check runs on every review (queue composition, §9) as a
        # short-circuit "does this user use gating at all" existence scan —
        # keeps it index-only for the common case of no prerequisites set.
        Index("idx_nodes_user_requires", "user_id", "requires_node_id"),
        # One node per entity, so the backfill in tree_service is idempotent.
        UniqueConstraint("deck_id", name="uq_nodes_deck"),
        UniqueConstraint("source_id", name="uq_nodes_source"),
        UniqueConstraint("extract_id", name="uq_nodes_extract"),
    )

    @property
    def entity_id(self) -> uuid.UUID | None:
        return self.deck_id or self.source_id or self.extract_id


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
    active_weaknesses: Mapped[list[str]] = mapped_column(JSONType, nullable=False, default=list)
    weakness_history: Mapped[list[dict]] = mapped_column(JSONType, nullable=False, default=list)
    # Documentation, thematic nature & source document provenance
    documentation: Mapped[str | None] = mapped_column(Text, nullable=True)
    thematic_nature: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_documents: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)

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


class CardReference(Base):
    """Where in the source document a card's answer actually comes from.

    A card generated from an uploaded document carries the passage that
    supports it, so after answering you are shown *the reading*, not just the
    back of the card — which is the difference between "you got it wrong" and
    "go read this paragraph".

    ``quote`` is a verbatim span the model copied out of the passage, and
    ``quote_verified`` records whether we actually found that span in the
    source text. An unverified quote is a hallucinated citation, and the whole
    point of a citation is that it can be trusted, so the UI shows the real
    extract instead of a quote we could not confirm.

    ``source_id``/``extract_id`` are SET NULL rather than CASCADE: deleting the
    reading material should not silently strip the provenance off cards that
    are still being studied.
    """

    __tablename__ = "card_references"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    card_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("cards.id", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("sources.id", ondelete="SET NULL")
    )
    extract_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("extracts.id", ondelete="SET NULL")
    )
    quote: Mapped[str] = mapped_column(Text, nullable=False, default="")
    quote_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    locator: Mapped[str | None] = mapped_column(Text)
    source_title: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    __table_args__ = (Index("idx_card_references_card", "card_id", "position"),)


class CardLesson(Base):
    """The short teaching text shown before a card in Learn & Practice mode.

    Written from the card's own citations (see :class:`CardReference`) — which
    is why the mode is only offered on cards that have them. A lesson invented
    without a source is exactly the failure this app refuses elsewhere.

    Cached per card because it is deterministic teaching material, not a
    response to anything the user typed: regenerating it on every pass would
    burn a call per card per review and, worse, let the explanation drift
    between sessions when the underlying passage never changed.
    """

    __tablename__ = "card_lessons"

    card_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("cards.id", ondelete="CASCADE"), primary_key=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    key_points: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    model_used: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class StudySession(Base):
    """One timed study block, and the free time finishing it early earned.

    The Time Bank mechanic: you commit to a duration and a card target up
    front, and whatever you *don't* spend once the target is met is banked as
    time you've earned back. Tracking velocity rather than seat time is the
    point — an hour billed for twenty minutes of real work is not an hour of
    study, and a system that rewards the clock teaches you to sit still.

    Server-side rather than localStorage (where the countdown itself lives):
    a bank that evaporates when browser storage is cleared isn't a record of
    anything. This is longitudinal data like the review log — it belongs in
    the database and in the export.
    """

    __tablename__ = "study_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    # NULL while the session is still open.
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    planned_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Time actually spent: planned minus whatever was left on the clock at the
    # end. Pausing therefore doesn't count as study time, which is correct and
    # needs no separate pause ledger.
    active_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # The §2 micro-goal: "what one thing will you master in this block?"
    focus_goal: Mapped[str | None] = mapped_column(Text)
    goal_cards: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Counted server-side from review_logs at close — the client never gets to
    # assert how much work it did.
    cards_reviewed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Only earned when the card target was actually met.
    banked_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Post-session reflection — the executive-function coach's exit half of
    # the focus_goal question. Filled in after the block ends, never during,
    # so it's separate from finish_session rather than an argument to it.
    distraction: Mapped[str | None] = mapped_column(Text)
    next_time_plan: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("idx_study_sessions_user", "user_id", "started_at"),
    )

    @property
    def goal_met(self) -> bool:
        return self.goal_cards > 0 and self.cards_reviewed >= self.goal_cards


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
    # True when this review is the one that graduated the card into FSRS's
    # "review" state — the app's definition of "mastered" (see tree_service's
    # is_mastered). Drives the velocity stat (mastered / active hour).
    graduated_to_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Metacognitive Judgment of Learning (1: Guess, 2: Unsure, 3: Confident, 4: Solid).
    user_confidence: Mapped[int | None] = mapped_column(SmallInteger)
    # Memory Champion: Flag indicating if review was performed during a timed Blitz Sprint.
    is_blitz: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Longitudinal Weakness Memory: specific flaws identified, resolved, or persisting across reviews
    weaknesses: Mapped[list[str]] = mapped_column(JSONType, nullable=False, default=list)
    improvements: Mapped[list[str]] = mapped_column(JSONType, nullable=False, default=list)
    persistent_weaknesses: Mapped[list[str]] = mapped_column(JSONType, nullable=False, default=list)

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


class CodeProblem(Base):
    """A coding challenge or Pre-LeetCode fundamental drill."""

    __tablename__ = "code_problems"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False, default="problem")  # "fundamental" | "problem"
    track: Mapped[str | None] = mapped_column(Text, nullable=True)  # track_0_python_basics, track_1_pythonic_fluency, etc.
    title: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    difficulty: Mapped[str] = mapped_column(Text, nullable=False, default="Easy")  # Easy, Medium, Hard
    category: Mapped[str] = mapped_column(Text, nullable=False, default="General")
    tags: Mapped[list[str]] = mapped_column(JSONType, nullable=False, default=list)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    examples: Mapped[list[dict]] = mapped_column(JSONType, nullable=False, default=list)
    constraints: Mapped[list[str]] = mapped_column(JSONType, nullable=False, default=list)
    starter_codes: Mapped[dict[str, str]] = mapped_column(JSONType, nullable=False, default=dict)
    solutions: Mapped[dict[str, str]] = mapped_column(JSONType, nullable=False, default=dict)
    editorial: Mapped[str | None] = mapped_column(Text, nullable=True)
    test_cases: Mapped[list[dict]] = mapped_column(JSONType, nullable=False, default=list)
    hints: Mapped[list[str]] = mapped_column(JSONType, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )


class CodeSubmission(Base):
    """User code submission record and execution history."""

    __tablename__ = "code_submissions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    problem_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("code_problems.id", ondelete="CASCADE"), nullable=False, index=True
    )
    language: Mapped[str] = mapped_column(Text, nullable=False, default="python")
    code: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="Accepted")
    passed_tests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    runtime_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    memory_kb: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_feedback: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class LexiconCache(Base):
    """Cached technical definitions and concordance entries."""

    __tablename__ = "lexicon_cache"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    term_normalized: Mapped[str] = mapped_column(Text, index=True, nullable=False)
    term_display: Mapped[str] = mapped_column(Text, nullable=False)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    context_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    example: Mapped[str | None] = mapped_column(Text, nullable=True)
    domain: Mapped[str | None] = mapped_column(Text, nullable=True, default="Computer Science")
    related_terms: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    model_used: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    __table_args__ = (
        Index("idx_lexicon_term_normalized", "term_normalized"),
    )


__all__ = [
    "Base",
    "Card",
    "CardLesson",
    "CardReference",
    "CodeProblem",
    "CodeSubmission",
    "Deck",
    "Extract",
    "GradingCache",
    "Import",
    "KnowledgeNode",
    "LeechSuggestion",
    "LexiconCache",
    "MediaAsset",
    "Note",
    "NoteType",
    "QueueConfig",
    "ReviewLog",
    "SisterPair",
    "Source",
    "StudySession",
    "User",
    "utcnow",
]
