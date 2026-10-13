"""Add module visibility toggles for pre-leetcode and code lab

Revision ID: 0018
Revises: 0017
Create Date: 2026-10-12
"""

import sqlalchemy as sa
from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("show_pre_leetcode", sa.Boolean(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("show_code_lab", sa.Boolean(), nullable=False, server_default="0")
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("show_code_lab")
        batch_op.drop_column("show_pre_leetcode")
