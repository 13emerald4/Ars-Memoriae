"""Mastery gating on the knowledge tree

A node can require another node's subtree to reach a mastery threshold before
its own cards enter the queue — "can't unlock Calculus without 90% on
Algebraic Functions." `requires_node_id` names the prerequisite;
`mastery_threshold` is the bar (default 90, matching the 90-100% commonly
cited for mastery-gated curricula). Both default to "ungated" so every
existing node is unaffected until a user explicitly wires up a gate.

No DB-level CHECK on mastery_threshold's range: every write path goes through
the API's Pydantic validation (ge=1, le=100), and adding a CHECK to an
existing SQLite table forces a batch-mode table rebuild for what the API layer
already guarantees — not worth the migration risk on an additive change.

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-12
"""

import sqlalchemy as sa

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Batch mode: adding a column with a FK constraint is an ALTER SQLite
    # can't do directly (it has no ALTER-ADD-CONSTRAINT), so Alembic rebuilds
    # the table under the hood. A no-op wrapper on Postgres, which supports
    # this natively.
    with op.batch_alter_table("knowledge_nodes") as batch_op:
        batch_op.add_column(
            sa.Column(
                "requires_node_id",
                sa.Uuid(),
                sa.ForeignKey(
                    "knowledge_nodes.id", ondelete="SET NULL", name="fk_nodes_requires"
                ),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "mastery_threshold", sa.SmallInteger(), nullable=False, server_default="90"
            )
        )
        batch_op.create_index(
            "idx_nodes_user_requires", ["user_id", "requires_node_id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("knowledge_nodes") as batch_op:
        batch_op.drop_index("idx_nodes_user_requires")
        batch_op.drop_column("mastery_threshold")
        batch_op.drop_column("requires_node_id")
