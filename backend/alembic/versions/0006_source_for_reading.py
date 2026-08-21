"""Sources can opt out of the Incremental Reading queue

A document uploaded purely to generate cards from is reference material, not
something to surface as "reading" — its extracts must never enter the
composed queue's IR stream the way a pasted article does. `for_reading`
defaults true so every existing/pasted source keeps behaving exactly as
before; only the new document-upload path sets it false.

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-11
"""

import sqlalchemy as sa

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sources",
        sa.Column("for_reading", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("sources", "for_reading")
