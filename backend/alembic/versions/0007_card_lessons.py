"""Cached Learn & Practice lessons

The short teaching text shown before a card, written from that card's own
citations. Cached per card: it is deterministic teaching material derived from
a fixed passage, not a response to anything the user typed, so regenerating it
every pass would burn an API call per card and let the wording drift between
sessions for no reason.

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-11
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "card_lessons",
        sa.Column(
            "card_id",
            sa.Uuid(),
            sa.ForeignKey("cards.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        # Matches the JSONType variant used across the models: native JSONB on
        # Postgres, plain JSON on SQLite.
        sa.Column(
            "key_points",
            sa.JSON().with_variant(JSONB(), "postgresql"),
            nullable=False,
        ),
        sa.Column("model_used", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("card_lessons")
