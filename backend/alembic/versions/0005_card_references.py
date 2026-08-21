"""Card citations back into an uploaded document

A card generated from a document records the passage that supports it, so
after answering the user is shown the reading rather than only the card's
back. Extracts gain a `locator` ("p. 42") so the citation points somewhere a
reader can actually turn to.

source_id/extract_id are SET NULL rather than CASCADE: deleting the reading
material must not strip provenance off cards that are still being studied.

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-10
"""

import sqlalchemy as sa

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("extracts", sa.Column("locator", sa.Text(), nullable=True))

    op.create_table(
        "card_references",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "card_id", sa.Uuid(), sa.ForeignKey("cards.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "source_id", sa.Uuid(), sa.ForeignKey("sources.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column(
            "extract_id",
            sa.Uuid(),
            sa.ForeignKey("extracts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("quote", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "quote_verified", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("locator", sa.Text(), nullable=True),
        sa.Column("source_title", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_card_references_card", "card_references", ["card_id", "position"])


def downgrade() -> None:
    op.drop_index("idx_card_references_card", table_name="card_references")
    op.drop_table("card_references")
    op.drop_column("extracts", "locator")
