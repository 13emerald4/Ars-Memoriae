"""Add users.timezone (study-day boundary) and an index on review_logs.reviewed_at

Revision ID: 0020
Revises: 0019
Create Date: 2026-10-13
"""

import sqlalchemy as sa

from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        # IANA name, e.g. "America/Vancouver". NULL = UTC.
        batch_op.add_column(sa.Column("timezone", sa.Text(), nullable=True))

    # Daily caps, stats, and analytics all filter logs by reviewed_at; the
    # only existing index leads with card_id.
    op.create_index("idx_review_logs_reviewed_at", "review_logs", ["reviewed_at"])


def downgrade() -> None:
    op.drop_index("idx_review_logs_reviewed_at", table_name="review_logs")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("timezone")
