"""Drop the stored Google API key; grading runs on local Ollama only

Grading moved to a local Ollama model, so the per-user Google key is never
read. The column is dropped rather than left behind holding encrypted
credentials nobody uses.

Users still pointing at a Gemini/Gemma model name are moved to the Ollama
default: those names don't exist in Ollama, so every grading call would fail
with "model not found". The column's server default changes to match.

Downgrade restores the column empty. The dropped keys cannot be recovered.

Revision ID: 0017
Revises: 0016
Create Date: 2026-10-08
"""

import sqlalchemy as sa

from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None

OLLAMA_DEFAULT_MODEL = "qwen2.5-coder:7b"
LEGACY_DEFAULT_MODEL = "gemma-4-e4b-it"


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE users SET grading_model = :model "
            "WHERE grading_model LIKE 'gemini%' OR grading_model LIKE 'gemma%'"
        ).bindparams(model=OLLAMA_DEFAULT_MODEL)
    )
    # Batch mode: SQLite can't drop a column or change a default in place, so
    # Alembic rebuilds the table. A no-op wrapper on Postgres.
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("google_api_key_encrypted")
        batch_op.alter_column(
            "grading_model",
            existing_type=sa.Text(),
            existing_nullable=False,
            server_default=OLLAMA_DEFAULT_MODEL,
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("google_api_key_encrypted", sa.LargeBinary()))
        batch_op.alter_column(
            "grading_model",
            existing_type=sa.Text(),
            existing_nullable=False,
            server_default=LEGACY_DEFAULT_MODEL,
        )
