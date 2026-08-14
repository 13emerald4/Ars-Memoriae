"""Add user_confidence to review_logs

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-13
"""

import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("review_logs") as batch_op:
        batch_op.add_column(sa.Column("user_confidence", sa.SmallInteger(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("review_logs") as batch_op:
        batch_op.drop_column("user_confidence")
