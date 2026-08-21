"""Sister-card interference pairs (§2, §14 Phase 4)

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-08
"""

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "sister_pairs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("note_a_id", sa.Uuid(), sa.ForeignKey("notes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("note_b_id", sa.Uuid(), sa.ForeignKey("notes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("front_similarity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("back_similarity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("kind", sa.Text(), nullable=False, server_default="interference"),
        sa.Column("status", sa.Text(), nullable=False, server_default="open"),
        sa.Column("created_at", TS, nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "kind IN ('interference','duplicate','convergent')", name="ck_sister_kind"
        ),
        sa.CheckConstraint("status IN ('open','dismissed')", name="ck_sister_status"),
        sa.UniqueConstraint("note_a_id", "note_b_id", name="uq_sister_pair"),
    )
    op.create_index("idx_sister_user", "sister_pairs", ["user_id", "status"])


def downgrade() -> None:
    op.drop_index("idx_sister_user", table_name="sister_pairs")
    op.drop_table("sister_pairs")
