"""Initial schema (spec §5.1)

Revision ID: 0001
Revises:
Create Date: 2026-08-08
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# Frozen copies of the portability aliases from app/models (see module docstring
# there): JSONB/TEXT[] on Postgres, JSON on SQLite.
JSONType = sa.JSON().with_variant(JSONB(), "postgresql")
StringArray = sa.JSON().with_variant(ARRAY(sa.Text()), "postgresql")
TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.Text(), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("google_api_key_encrypted", sa.LargeBinary()),
        sa.Column("desired_retention", sa.Float(), nullable=False, server_default="0.90"),
        sa.Column("grading_model", sa.Text(), nullable=False, server_default="gemma-4-e4b-it"),
        sa.Column("queue_time_budget_minutes", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("leech_remediation_opt_in", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("daily_new_limit", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("daily_review_limit", sa.Integer(), nullable=False, server_default="200"),
        sa.Column("backlog_spread_days", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("leech_threshold", sa.Integer(), nullable=False, server_default="8"),
        sa.Column("fsrs_parameters", JSONType),
        sa.Column("fsrs_optimized_at", TS),
        sa.Column("llm_grading_consent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("grading_bias", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", TS, nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "decks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_id", sa.Uuid(), sa.ForeignKey("decks.id", ondelete="CASCADE")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("desired_retention_override", sa.Float()),
        sa.Column("default_priority", sa.SmallInteger(), nullable=False, server_default="50"),
        sa.Column("created_at", TS, nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("default_priority BETWEEN 0 AND 100", name="ck_decks_priority"),
    )

    op.create_table(
        "note_types",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("template_kind", sa.Text(), nullable=False, server_default="basic"),
        sa.Column("fields", JSONType, nullable=False),
        sa.Column("grading_profile", sa.Text(), nullable=False, server_default="short_answer"),
        sa.CheckConstraint(
            "template_kind IN ('basic','cloze','image_occlusion')", name="ck_note_types_kind"
        ),
        sa.CheckConstraint(
            "grading_profile IN ('short_answer','conceptual','math_code')",
            name="ck_note_types_profile",
        ),
    )

    op.create_table(
        "sources",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("raw_text", sa.Text()),
        sa.Column("url", sa.Text()),
        sa.Column("priority", sa.SmallInteger(), nullable=False, server_default="50"),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column("created_at", TS, nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("priority BETWEEN 0 AND 100", name="ck_sources_priority"),
        sa.CheckConstraint("status IN ('active','postponed','done')", name="ck_sources_status"),
    )

    op.create_table(
        "extracts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source_id", sa.Uuid(), sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("priority", sa.SmallInteger()),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_shown_at", TS),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.CheckConstraint("priority BETWEEN 0 AND 100", name="ck_extracts_priority"),
        sa.CheckConstraint("status IN ('active','done')", name="ck_extracts_status"),
    )
    op.create_index("idx_extracts_next_shown", "extracts", ["next_shown_at"])

    op.create_table(
        "notes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("note_type_id", sa.Uuid(), sa.ForeignKey("note_types.id"), nullable=False),
        sa.Column("field_values", JSONType, nullable=False),
        sa.Column("created_at", TS, nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "cards",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("note_id", sa.Uuid(), sa.ForeignKey("notes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("deck_id", sa.Uuid(), sa.ForeignKey("decks.id"), nullable=False),
        sa.Column("template_slot", sa.Text(), nullable=False, server_default="default"),
        sa.Column("state", sa.Text(), nullable=False, server_default="new"),
        sa.Column("stability", sa.Float()),
        sa.Column("difficulty", sa.Float()),
        sa.Column("step", sa.Integer()),
        sa.Column("due", TS),
        sa.Column("last_review", TS),
        sa.Column("priority", sa.SmallInteger()),
        sa.Column("origin", sa.Text(), nullable=False, server_default="manual"),
        sa.Column("origin_extract_id", sa.Uuid(), sa.ForeignKey("extracts.id")),
        sa.Column("lapse_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("leech_flag", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("suspended", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("tags", StringArray, nullable=False),
        sa.CheckConstraint("state IN ('new','learning','review','relearning')", name="ck_cards_state"),
        sa.CheckConstraint("priority BETWEEN 0 AND 100", name="ck_cards_priority"),
        sa.CheckConstraint("origin IN ('manual','extract','imported')", name="ck_cards_origin"),
    )
    op.create_index("idx_cards_due", "cards", ["deck_id", "due"])
    op.create_index("idx_cards_priority", "cards", ["priority"])

    op.create_table(
        "review_logs",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer, "sqlite"),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column("card_id", sa.Uuid(), sa.ForeignKey("cards.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewed_at", TS, nullable=False, server_default=sa.func.now()),
        sa.Column("typed_answer", sa.Text()),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("llm_grade", sa.Text()),
        sa.Column("llm_reasoning", sa.Text()),
        sa.Column("llm_confidence", sa.Float()),
        sa.Column("final_grade", sa.Text(), nullable=False),
        sa.Column("overridden", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("state_before", sa.Text()),
        sa.Column("elapsed_days", sa.Float()),
        sa.CheckConstraint(
            "final_grade IN ('again','hard','good','easy')", name="ck_review_logs_grade"
        ),
    )
    op.create_index("idx_review_logs_card", "review_logs", ["card_id", "reviewed_at"])

    op.create_table(
        "grading_cache",
        sa.Column("card_id", sa.Uuid(), sa.ForeignKey("cards.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("answer_hash", sa.Text(), primary_key=True),
        sa.Column("response", JSONType, nullable=False),
        sa.Column("created_at", TS, nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "media_assets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("note_id", sa.Uuid(), sa.ForeignKey("notes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("original_name", sa.Text()),
        sa.CheckConstraint("kind IN ('image','audio')", name="ck_media_kind"),
    )

    op.create_table(
        "queue_config",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("review_weight", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("new_weight", sa.Float(), nullable=False, server_default="0.3"),
        sa.Column("ir_weight", sa.Float(), nullable=False, server_default="0.2"),
        sa.Column("seconds_per_review", sa.Float(), nullable=False, server_default="12"),
        sa.Column("seconds_per_ir_extract", sa.Float(), nullable=False, server_default="60"),
    )

    op.create_table(
        "imports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("imported_at", TS, nullable=False, server_default=sa.func.now()),
        sa.Column("notes_mapped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cards_mapped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warnings", JSONType, nullable=False),
    )

    op.create_table(
        "leech_suggestions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("card_id", sa.Uuid(), sa.ForeignKey("cards.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("payload", JSONType, nullable=False),
        sa.Column("rationale", sa.Text()),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("created_at", TS, nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("kind IN ('rewrite','split','ambiguous')", name="ck_leech_kind"),
        sa.CheckConstraint("status IN ('pending','accepted','dismissed')", name="ck_leech_status"),
    )


def downgrade() -> None:
    for table in (
        "leech_suggestions",
        "imports",
        "queue_config",
        "media_assets",
        "grading_cache",
        "review_logs",
        "cards",
        "notes",
        "extracts",
        "sources",
        "note_types",
        "decks",
        "users",
    ):
        op.drop_table(table)
