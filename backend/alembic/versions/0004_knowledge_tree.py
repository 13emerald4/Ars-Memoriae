"""Unified knowledge tree over decks, sources and extracts

SuperMemo's knowledge tree: one hierarchy that spans reading material *and*
cards, instead of a deck tree for one and a flat source list for the other.

Nodes are an overlay — each points at the deck / source / extract it stands
for, and a pure ``topic`` node points at nothing. No existing table changes, so
this is additive and reversible; the backfill that populates nodes for data
that already exists runs lazily in tree_service.ensure_tree rather than here,
because it has to keep working for rows created after this migration (Anki
imports, new decks) too.

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-10
"""

import sqlalchemy as sa

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_nodes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_id",
            sa.Uuid(),
            sa.ForeignKey("knowledge_nodes.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("kind", sa.Text(), nullable=False, server_default="topic"),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("priority", sa.SmallInteger(), nullable=True),
        sa.Column(
            "collapsed", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "deck_id", sa.Uuid(), sa.ForeignKey("decks.id", ondelete="CASCADE"), nullable=True
        ),
        sa.Column(
            "source_id",
            sa.Uuid(),
            sa.ForeignKey("sources.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "extract_id",
            sa.Uuid(),
            sa.ForeignKey("extracts.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "kind IN ('topic','deck','source','extract')", name="ck_nodes_kind"
        ),
        sa.CheckConstraint("priority BETWEEN 0 AND 100", name="ck_nodes_priority"),
        # NULL repeats freely under a UNIQUE constraint on both Postgres and
        # SQLite, so topic nodes (all three FKs NULL) don't collide.
        sa.UniqueConstraint("deck_id", name="uq_nodes_deck"),
        sa.UniqueConstraint("source_id", name="uq_nodes_source"),
        sa.UniqueConstraint("extract_id", name="uq_nodes_extract"),
    )
    op.create_index(
        "idx_nodes_user_parent", "knowledge_nodes", ["user_id", "parent_id", "position"]
    )


def downgrade() -> None:
    op.drop_index("idx_nodes_user_parent", table_name="knowledge_nodes")
    op.drop_table("knowledge_nodes")
