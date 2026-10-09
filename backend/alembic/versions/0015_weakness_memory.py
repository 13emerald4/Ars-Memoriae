"""Add longitudinal weakness memory tracking to cards and review logs

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-03
"""

import sqlalchemy as sa

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cards", sa.Column("active_weaknesses", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("cards", sa.Column("weakness_history", sa.JSON(), nullable=False, server_default="[]"))

    op.add_column("review_logs", sa.Column("weaknesses", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("review_logs", sa.Column("improvements", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("review_logs", sa.Column("persistent_weaknesses", sa.JSON(), nullable=False, server_default="[]"))


def downgrade() -> None:
    op.drop_column("review_logs", "persistent_weaknesses")
    op.drop_column("review_logs", "improvements")
    op.drop_column("review_logs", "weaknesses")

    op.drop_column("cards", "weakness_history")
    op.drop_column("cards", "active_weaknesses")
