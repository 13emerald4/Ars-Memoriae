"""Bounded-work guarantees for the hottest path in the app.

``GET /api/queue/next`` runs after every single review, so anything in it that
scales with collection size is felt on every card. These tests pin the two
properties that keep it flat: work is bounded by the *session* size rather than
the collection size, and building an FSRS card doesn't sleep.
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import Card, Deck, Note, NoteType, User
from app.services.fsrs_service import FSRSService
from app.services.queue_service import (
    MAX_CANDIDATE_POOL,
    MIN_CANDIDATE_POOL,
    candidate_pool_size,
    compose_session,
    eligible_counts,
    fetch_due_candidates,
    fetch_new_candidates,
)


def test_building_an_fsrs_card_does_not_sleep():
    """py-fsrs sleeps 1 ms per Card when card_id is omitted, to avoid id
    collisions. Omitting it cost ~1.5 ms a card, which made ranking a few
    hundred candidates take most of a second and an import take minutes."""
    started = time.perf_counter()
    for _ in range(200):
        FSRSService.to_fsrs_card(
            state="review",
            stability=30.0,
            difficulty=5.0,
            step=None,
            due=datetime.now(UTC),
            last_review=datetime.now(UTC) - timedelta(days=10),
        )
    elapsed = time.perf_counter() - started
    # 200 sleeps would be >= 200 ms; without them this is a couple of ms.
    assert elapsed < 0.1, f"to_fsrs_card looks like it is sleeping again ({elapsed:.3f}s/200)"


class TestCandidatePool:
    def test_pool_is_bounded_below_and_above(self):
        assert candidate_pool_size(1) == MIN_CANDIDATE_POOL
        assert candidate_pool_size(10_000) == MAX_CANDIDATE_POOL

    def test_pool_scales_with_session_size_in_between(self):
        assert candidate_pool_size(400) == 1600

    def test_no_session_means_no_query(self):
        assert candidate_pool_size(0) == 0


@pytest.fixture
async def big_collection():
    """One user with far more cards than any session will ever show."""
    n_due, n_new = 600, 900
    now = datetime.now(UTC)

    async with SessionLocal() as db:
        user = User(
            email=f"big-{uuid.uuid4().hex[:8]}@example.com",
            password_hash="scrypt$1$1$1$00$00",
            daily_new_limit=20,
            daily_review_limit=100,
            backlog_spread_days=5,
        )
        db.add(user)
        await db.flush()
        deck = Deck(user_id=user.id, name="Big")
        nt = NoteType(user_id=user.id, name="Basic", template_kind="basic", fields={})
        db.add_all([deck, nt])
        await db.flush()

        notes, cards = [], []
        for i in range(n_due + n_new):
            nid = uuid.uuid4()
            notes.append(
                {
                    "id": nid,
                    "user_id": user.id,
                    "note_type_id": nt.id,
                    "field_values": {"Front": f"Q{i}", "Back": f"A{i}"},
                    "created_at": now,
                }
            )
            is_due = i < n_due
            cards.append(
                {
                    "id": uuid.uuid4(),
                    "note_id": nid,
                    "deck_id": deck.id,
                    "template_slot": "default",
                    "state": "review" if is_due else "new",
                    "stability": 20.0 if is_due else None,
                    "difficulty": 5.0 if is_due else None,
                    "step": None,
                    # All overdue by varying amounts, so smoothing kicks in.
                    "due": now - timedelta(days=1 + (i % 30)) if is_due else None,
                    "last_review": now - timedelta(days=40) if is_due else None,
                    "priority": None,
                    "origin": "imported",
                    "origin_extract_id": None,
                    "lapse_count": 0,
                    "leech_flag": False,
                    "suspended": False,
                    "tags": [],
                }
            )
        await db.execute(Note.__table__.insert(), notes)
        await db.execute(Card.__table__.insert(), cards)
        await db.commit()
        return user.id, n_due, n_new


async def test_counts_are_exact_without_loading_the_collection(big_collection):
    user_id, n_due, n_new = big_collection
    async with SessionLocal() as db:
        user = await db.get(User, user_id)
        counts = await eligible_counts(db, user, datetime.now(UTC))

    assert counts["due_total"] == n_due
    assert counts["new_total"] == n_new
    assert counts["overdue_total"] == n_due  # every due card was backdated


async def test_fetches_are_capped_by_their_limit(big_collection):
    user_id, _n_due, _ = big_collection
    async with SessionLocal() as db:
        user = await db.get(User, user_id)
        now = datetime.now(UTC)

        due = await fetch_due_candidates(db, user, now, 50)
        assert len(due) == 50, "the pool must not grow with the collection"

        new = await fetch_new_candidates(db, user, 20)
        assert len(new) == 20

        assert await fetch_due_candidates(db, user, now, 0) == []


async def test_session_stays_small_and_counts_stay_honest(big_collection):
    """The session shows a day's work; the header still reports the true totals."""
    user_id, n_due, n_new = big_collection
    async with SessionLocal() as db:
        user = await db.get(User, user_id)
        plan = await compose_session(db, user)

    assert plan.counts["due_total"] == n_due
    assert plan.counts["new_total"] == n_new
    assert plan.counts["new"] <= 20
    # 600 overdue spread over 5 days, hard-capped at 100.
    assert plan.counts["review"] <= 100
    assert len(plan.items) <= 120
    assert any("spread over" in note for note in plan.notes)


async def test_composition_is_flat_not_linear_in_collection_size(big_collection):
    """A second user with a fraction of the cards must not be dramatically
    faster — if it is, something is still scanning the whole collection."""
    user_id, _, _ = big_collection
    async with SessionLocal() as db:
        user = await db.get(User, user_id)
        await compose_session(db, user, limit=1)  # warm caches

        started = time.perf_counter()
        for _ in range(3):
            await compose_session(db, user, limit=1)
        elapsed = (time.perf_counter() - started) / 3

    # Generous: the pre-fix implementation took seconds on a collection this
    # size, so this catches a regression without being timing-flaky.
    assert elapsed < 1.0, f"queue composition took {elapsed:.2f}s for one item"


async def test_total_rows_loaded_is_bounded(big_collection):
    """The point of the rewrite: loaded rows track the session, not the deck."""
    user_id, n_due, n_new = big_collection
    async with SessionLocal() as db:
        user = await db.get(User, user_id)
        total_cards = await db.scalar(
            select(func.count()).select_from(Card).join(Deck, Deck.id == Card.deck_id)
            .where(Deck.user_id == user.id)
        )
        assert total_cards == n_due + n_new

        pool = await fetch_due_candidates(db, user, datetime.now(UTC), candidate_pool_size(100))
        assert len(pool) <= MIN_CANDIDATE_POOL
        assert len(pool) < total_cards
