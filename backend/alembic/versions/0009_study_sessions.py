"""Timed study sessions and the Time Bank

A session commits to a duration and a card target up front; whatever time
isn't spent once the target is met is banked as earned free time. Stored
server-side rather than in localStorage (where the countdown itself lives)
because a bank that evaporates with browser storage isn't a record of
anything — this is longitudinal data like the review log.

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-12
"""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "study_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("planned_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("focus_goal", sa.Text(), nullable=True),
        sa.Column("goal_cards", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cards_reviewed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("banked_seconds", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("idx_study_sessions_user", "study_sessions", ["user_id", "started_at"])


def downgrade() -> None:
    op.drop_index("idx_study_sessions_user", table_name="study_sessions")
    op.drop_table("study_sessions")
