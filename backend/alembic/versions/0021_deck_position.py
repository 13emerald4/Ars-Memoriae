"""Add decks.position for reordering branches

Revision ID: 0021
Revises: 0020
Create Date: 2026-10-14
"""

import sqlalchemy as sa

from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("decks") as batch_op:
        batch_op.add_column(sa.Column("position", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    with op.batch_alter_table("decks") as batch_op:
        batch_op.drop_column("position")
