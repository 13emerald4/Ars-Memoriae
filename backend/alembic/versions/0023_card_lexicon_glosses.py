"""Add cards.lexicon_glosses for persistent margin word lookups and glosses

Revision ID: 0023
Revises: 0022
Create Date: 2026-10-19
"""

import sqlalchemy as sa
from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("cards") as batch_op:
        batch_op.add_column(
            sa.Column("lexicon_glosses", sa.JSON(), nullable=False, server_default="[]")
        )


def downgrade() -> None:
    with op.batch_alter_table("cards") as batch_op:
        batch_op.drop_column("lexicon_glosses")
