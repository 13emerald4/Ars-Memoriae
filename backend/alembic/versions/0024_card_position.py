"""Add position column to cards

Revision ID: 0024
Revises: 0023
Create Date: 2026-11-05
"""

import sqlalchemy as sa
from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("cards") as batch_op:
        batch_op.add_column(sa.Column("position", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("cards") as batch_op:
        batch_op.drop_column("position")
