"""Add Memory Champion features (automaticity, event horizons, blitz logging)

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-18
"""

import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("automaticity_threshold_ms", sa.Integer(), nullable=True, server_default="3000")
        )
        batch_op.add_column(
            sa.Column("target_event_date", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(sa.Column("target_event_title", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("peak_retention_target", sa.Float(), nullable=True, server_default="0.95")
        )

    with op.batch_alter_table("decks") as batch_op:
        batch_op.add_column(
            sa.Column("target_event_date", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(sa.Column("target_event_title", sa.Text(), nullable=True))

    with op.batch_alter_table("review_logs") as batch_op:
        batch_op.add_column(
            sa.Column("is_blitz", sa.Boolean(), nullable=False, server_default="0")
        )


def downgrade() -> None:
    with op.batch_alter_table("review_logs") as batch_op:
        batch_op.drop_column("is_blitz")

    with op.batch_alter_table("decks") as batch_op:
        batch_op.drop_column("target_event_title")
        batch_op.drop_column("target_event_date")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("peak_retention_target")
        batch_op.drop_column("target_event_title")
        batch_op.drop_column("target_event_date")
        batch_op.drop_column("automaticity_threshold_ms")
