"""Indexes for bounded queue composition (§9)

GET /api/queue/next runs after every review, so its queries are the hottest
path in the app. It filters cards by owner + state + suspension and orders by
priority or due date; these cover those shapes so an imported collection with
tens of thousands of cards doesn't force a full scan each time.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-09
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # New-card intake: filter by state, order by priority within a deck.
    op.create_index(
        "idx_cards_state_deck_priority", "cards", ["state", "deck_id", "priority"]
    )
    # Due-review selection and the overdue/due COUNTs.
    op.create_index("idx_cards_state_due", "cards", ["state", "due"])
    # Extract release + the IR eligibility count.
    op.create_index("idx_extracts_source_status", "extracts", ["source_id", "status"])


def downgrade() -> None:
    op.drop_index("idx_extracts_source_status", table_name="extracts")
    op.drop_index("idx_cards_state_due", table_name="cards")
    op.drop_index("idx_cards_state_deck_priority", table_name="cards")
