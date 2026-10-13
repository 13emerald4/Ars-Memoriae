"""Add documentation, thematic_nature, and source_documents to decks and cards, and show_thematic_context to users

Revision ID: 0019
Revises: 0018
Create Date: 2026-10-12
"""

import sqlalchemy as sa

from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("decks") as batch_op:
        batch_op.add_column(sa.Column("documentation", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("thematic_nature", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("source_documents", sa.JSON(), nullable=False, server_default="[]")
        )

    with op.batch_alter_table("cards") as batch_op:
        batch_op.add_column(sa.Column("documentation", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("thematic_nature", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("source_documents", sa.JSON(), nullable=False, server_default="[]")
        )

    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("show_thematic_context", sa.Boolean(), nullable=False, server_default="1")
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("show_thematic_context")

    with op.batch_alter_table("cards") as batch_op:
        batch_op.drop_column("source_documents")
        batch_op.drop_column("thematic_nature")
        batch_op.drop_column("documentation")

    with op.batch_alter_table("decks") as batch_op:
        batch_op.drop_column("source_documents")
        batch_op.drop_column("thematic_nature")
        batch_op.drop_column("documentation")
