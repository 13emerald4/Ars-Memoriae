"""Add lexicon_cache table for technical terms concordance and definitions

Revision ID: 0016
Revises: 0015
Create Date: 2026-10-03
"""

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lexicon_cache",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("term_normalized", sa.Text(), nullable=False),
        sa.Column("term_display", sa.Text(), nullable=False),
        sa.Column("definition", sa.Text(), nullable=False),
        sa.Column("context_explanation", sa.Text(), nullable=True),
        sa.Column("example", sa.Text(), nullable=True),
        sa.Column("domain", sa.Text(), nullable=True),
        sa.Column("related_terms", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("model_used", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_lexicon_term_normalized", "lexicon_cache", ["term_normalized"])


def downgrade() -> None:
    op.drop_index("idx_lexicon_term_normalized", table_name="lexicon_cache")
    op.drop_table("lexicon_cache")
