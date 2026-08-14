"""Post-session reflection on study_sessions

Closes the executive-function loop the Time Bank started: `focus_goal` is
asked going in ("what will you master?"), these two are asked coming out
("what distracted you?", "how will you fix it next time?"). Nullable and
never required — a block that ends by auto-settling at zero (nobody there to
answer) is just as valid a row as one someone reflects on by hand.

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-12
"""

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("study_sessions") as batch_op:
        batch_op.add_column(sa.Column("distraction", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("next_time_plan", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("study_sessions") as batch_op:
        batch_op.drop_column("next_time_plan")
        batch_op.drop_column("distraction")
