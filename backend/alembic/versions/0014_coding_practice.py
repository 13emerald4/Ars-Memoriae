"""Add Coding Practice and Pre-LeetCode Fundamentals tables

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-18
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

JSONType = sa.JSON().with_variant(JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "code_problems",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("kind", sa.String(32), nullable=False, server_default="problem"),
        sa.Column("track", sa.String(64), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("slug", sa.String(128), nullable=False, index=True),
        sa.Column("difficulty", sa.String(32), nullable=False, server_default="Easy"),
        sa.Column("category", sa.String(64), nullable=False, server_default="General"),
        sa.Column("tags", JSONType, nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("examples", JSONType, nullable=False),
        sa.Column("constraints", JSONType, nullable=False),
        sa.Column("starter_codes", JSONType, nullable=False),
        sa.Column("solutions", JSONType, nullable=False),
        sa.Column("editorial", sa.Text(), nullable=True),
        sa.Column("test_cases", JSONType, nullable=False),
        sa.Column("hints", JSONType, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "code_submissions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("problem_id", sa.Uuid(), sa.ForeignKey("code_problems.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("language", sa.String(32), nullable=False, server_default="python"),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="Accepted"),
        sa.Column("passed_tests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("runtime_ms", sa.Float(), nullable=True),
        sa.Column("memory_kb", sa.Float(), nullable=True),
        sa.Column("ai_feedback", JSONType, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("code_submissions")
    op.drop_table("code_problems")
