"""Mastery velocity: flag the review that graduates a card into "review" state

Alpha-style "mastered concepts per active hour," not seat time. The flag is
written at review time (confirm_review already computes the post-review state
to update the card, so this costs nothing extra to know) rather than
re-derived later from review history, which would need the state *after*
each past review — a fact only ``Card.state`` currently remembers, and only
for the card's *latest* review.

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-12
"""

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("review_logs") as batch_op:
        batch_op.add_column(
            sa.Column(
                "graduated_to_review",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("review_logs") as batch_op:
        batch_op.drop_column("graduated_to_review")
