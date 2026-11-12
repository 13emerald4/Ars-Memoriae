"""Neuroscience Enhancements: Schema Checkpoints, Concept Edges, Spatial Memory Loci, Prompt Mutation, Mnemonic Vignettes

Revision ID: 0025
Revises: 0024
Create Date: 2026-11-05
"""

import sqlalchemy as sa

from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. User settings
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("enable_schema_checkpoints", sa.Boolean(), nullable=False, server_default=sa.true())
        )
        batch_op.add_column(
            sa.Column("enable_prompt_mutation", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(
            sa.Column("enable_prediction_mode", sa.Boolean(), nullable=False, server_default=sa.false())
        )

    # 2. Card attributes: schema checkpoint, spatial memory palace locus, mnemonic vignette
    with op.batch_alter_table("cards") as batch_op:
        batch_op.add_column(
            sa.Column("is_schema_checkpoint", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(sa.Column("spatial_x", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("spatial_y", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("spatial_locus", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("mnemonic_vignette", sa.Text(), nullable=True))

    # 3. KnowledgeNode attributes: spatial coordinates and room name
    with op.batch_alter_table("knowledge_nodes") as batch_op:
        batch_op.add_column(sa.Column("spatial_x", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("spatial_y", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("spatial_room", sa.Text(), nullable=True))

    # 4. ReviewLog attributes: prediction error tracking & mutation type
    with op.batch_alter_table("review_logs") as batch_op:
        batch_op.add_column(
            sa.Column("is_pretest_prediction", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(
            sa.Column("prediction_error_detected", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(sa.Column("mutation_type", sa.Text(), nullable=True))

    # 5. ConceptEdge table: Associative Networks & Spreading Activation
    op.create_table(
        "concept_edges",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_card_id", sa.Uuid(), sa.ForeignKey("cards.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_card_id", sa.Uuid(), sa.ForeignKey("cards.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relationship_type", sa.Text(), nullable=False, server_default="associative"),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "relationship_type IN ('associative', 'prerequisite_of', 'contrasts_with', 'implements', 'analogous_to', 'component_of', 'failure_mode_of')",
            name="ck_concept_edges_relationship",
        ),
    )
    op.create_index("idx_concept_edges_user_source", "concept_edges", ["user_id", "source_card_id"])
    op.create_index("idx_concept_edges_user_target", "concept_edges", ["user_id", "target_card_id"])


def downgrade() -> None:
    op.drop_index("idx_concept_edges_user_target", table_name="concept_edges")
    op.drop_index("idx_concept_edges_user_source", table_name="concept_edges")
    op.drop_table("concept_edges")

    with op.batch_alter_table("review_logs") as batch_op:
        batch_op.drop_column("mutation_type")
        batch_op.drop_column("prediction_error_detected")
        batch_op.drop_column("is_pretest_prediction")

    with op.batch_alter_table("knowledge_nodes") as batch_op:
        batch_op.drop_column("spatial_room")
        batch_op.drop_column("spatial_y")
        batch_op.drop_column("spatial_x")

    with op.batch_alter_table("cards") as batch_op:
        batch_op.drop_column("mnemonic_vignette")
        batch_op.drop_column("spatial_locus")
        batch_op.drop_column("spatial_y")
        batch_op.drop_column("spatial_x")
        batch_op.drop_column("is_schema_checkpoint")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("enable_prediction_mode")
        batch_op.drop_column("enable_prompt_mutation")
        batch_op.drop_column("enable_schema_checkpoints")
