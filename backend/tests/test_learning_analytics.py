"""Tests for Learning Sciences Statistical Analytics.

Verifies:
- Session fatigue curve and optimal focus breakpoint detection
- Chronotype circadian learning efficiency map
- Psychometric item discrimination (point-biserial r_pb)
- Desirable difficulty retrievability vs stability gain yield curve
- Metacognitive calibration, Brier score, and hypercorrection retention
- EWMA skill health calculation
- Wald's SPRT log-likelihood accumulator and mastery verdicts
- End-to-end GET /api/stats/learning-analytics API
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Card, Deck, KnowledgeNode, Note, NoteType, ReviewLog, StudySession, User
from app.services.learning_analytics_service import compute_learning_analytics


@pytest.fixture
async def sample_deck_with_notes(auth_client: AsyncClient):
    """Seed a test user with a deck, notes, cards, and review logs."""
    me = (await auth_client.get("/api/me")).json()
    user_id = uuid.UUID(me["id"])

    async with SessionLocal() as db:
        user = await db.get(User, user_id)
        deck = Deck(user_id=user.id, name="Neuroscience & Learning")
        db.add(deck)
        await db.flush()

        nt = await db.scalar(select(NoteType).where(NoteType.user_id == user.id))
        if not nt:
            nt = NoteType(user_id=user.id, name="Basic", template_kind="basic")
            db.add(nt)
            await db.flush()

        cards = []
        for i in range(10):
            note = Note(
                user_id=user.id,
                note_type_id=nt.id,
                field_values={"Front": f"Concept {i+1} Question?", "Back": f"Answer {i+1}"},
            )
            db.add(note)
            await db.flush()
            card = Card(
                deck_id=deck.id,
                note_id=note.id,
                template_slot="0",
                state="review",
                stability=5.0,
                difficulty=3.0,
            )
            db.add(card)
            cards.append(card)
        await db.flush()

        now = datetime.now(UTC)
        # Create a study session starting 30 minutes ago
        session = StudySession(
            user_id=user.id,
            started_at=now - timedelta(minutes=35),
            ended_at=now,
            planned_seconds=1800,
            active_seconds=1800,
            goal_cards=10,
            cards_reviewed=10,
            banked_seconds=0,
        )
        db.add(session)
        await db.flush()

        # Seed review logs across session minutes (early high accuracy, later slump)
        for i, card in enumerate(cards):
            elapsed_m = i * 3  # 0m, 3m, 6m, ..., 27m
            reviewed_at = now - timedelta(minutes=35 - elapsed_m)
            # Early cards pass (high accuracy), later cards fail (fatigue)
            is_pass = i < 7
            db.add(
                ReviewLog(
                    card_id=card.id,
                    reviewed_at=reviewed_at,
                    final_grade="good" if is_pass else "again",
                    latency_ms=1500 if is_pass else 7000,
                    state_before="review",
                    elapsed_days=3.0,
                    user_confidence=4 if is_pass else 1,
                )
            )

        # Add a gated knowledge node relationship
        node_prereq = KnowledgeNode(
            user_id=user.id,
            title="Prerequisite Skill",
            kind="deck",
            deck_id=deck.id,
        )
        db.add(node_prereq)
        await db.flush()

        node_gated = KnowledgeNode(
            user_id=user.id,
            title="Advanced Neurobiology",
            kind="topic",
            requires_node_id=node_prereq.id,
            mastery_threshold=85,
        )
        db.add(node_gated)
        await db.commit()

    return {"user_id": user_id, "deck_id": deck.id}


class TestLearningAnalytics:
    async def test_empty_analytics_returns_clean_defaults(self, auth_client: AsyncClient):
        me = (await auth_client.get("/api/me")).json()
        user_id = uuid.UUID(me["id"])

        async with SessionLocal() as db:
            user = await db.get(User, user_id)
            res = await compute_learning_analytics(db, user, days=30)

        assert res.fatigue.optimal_focus_minutes == 25
        assert len(res.chronotype.hourly) == 24
        assert res.metacognition.brier_score == 0.0
        assert isinstance(res.ewma_mastery, list)

    async def test_fatigue_and_breakpoint_detection(
        self, auth_client: AsyncClient, sample_deck_with_notes: dict
    ):
        user_id = sample_deck_with_notes["user_id"]

        async with SessionLocal() as db:
            user = await db.get(User, user_id)
            res = await compute_learning_analytics(db, user, days=30)

        assert len(res.fatigue.curve) > 0
        assert res.fatigue.baseline_accuracy > 0.5
        assert 15 <= res.fatigue.optimal_focus_minutes <= 45
        assert "recommend" in res.fatigue.recommendation.lower()

    async def test_chronotype_hourly_efficiency(
        self, auth_client: AsyncClient, sample_deck_with_notes: dict
    ):
        user_id = sample_deck_with_notes["user_id"]

        async with SessionLocal() as db:
            user = await db.get(User, user_id)
            res = await compute_learning_analytics(db, user, days=30)

        assert len(res.chronotype.hourly) == 24
        total_reviews = sum(h.review_count for h in res.chronotype.hourly)
        assert total_reviews == 10
        assert 0 <= res.chronotype.peak_window_start <= 23
        assert res.chronotype.optimal_study_time != ""

    async def test_item_discrimination_and_ambiguity(
        self, auth_client: AsyncClient, sample_deck_with_notes: dict
    ):
        user_id = sample_deck_with_notes["user_id"]

        async with SessionLocal() as db:
            user = await db.get(User, user_id)
            res = await compute_learning_analytics(db, user, days=30)

        # We had 10 reviews
        assert isinstance(res.item_discrimination.high_discrimination, list)
        assert isinstance(res.item_discrimination.ambiguous_cards, list)

    async def test_desirable_difficulty_yield_curve(
        self, auth_client: AsyncClient, sample_deck_with_notes: dict
    ):
        user_id = sample_deck_with_notes["user_id"]

        async with SessionLocal() as db:
            user = await db.get(User, user_id)
            res = await compute_learning_analytics(db, user, days=30)

        assert len(res.desirable_difficulty.curve) > 0
        point = res.desirable_difficulty.curve[0]
        assert point.avg_retrievability > 0.0
        assert point.avg_stability_gain > 0.0

    async def test_metacognitive_calibration_and_brier(
        self, auth_client: AsyncClient, sample_deck_with_notes: dict
    ):
        user_id = sample_deck_with_notes["user_id"]

        async with SessionLocal() as db:
            user = await db.get(User, user_id)
            res = await compute_learning_analytics(db, user, days=30)

        assert len(res.metacognition.calibration_curve) == 4
        assert 0.0 <= res.metacognition.brier_score <= 1.0
        assert res.metacognition.calibration_verdict != ""

    async def test_ewma_and_sprt_gating(
        self, auth_client: AsyncClient, sample_deck_with_notes: dict
    ):
        user_id = sample_deck_with_notes["user_id"]

        async with SessionLocal() as db:
            user = await db.get(User, user_id)
            res = await compute_learning_analytics(db, user, days=30)

        assert len(res.ewma_mastery) > 0
        ewma_score = res.ewma_mastery[0]
        assert 0.0 <= ewma_score.ewma_pct <= 100.0

        assert len(res.sprt_gating) > 0
        sprt = res.sprt_gating[0]
        assert sprt.verdict in ("mastered", "unmastered", "testing")
        assert sprt.cards_evaluated == 10

    async def test_api_endpoint_learning_analytics(
        self, auth_client: AsyncClient, sample_deck_with_notes: dict
    ):
        resp = await auth_client.get("/api/stats/learning-analytics?days=30")
        assert resp.status_code == 200
        data = resp.json()
        assert "fatigue" in data
        assert "chronotype" in data
        assert "item_discrimination" in data
        assert "desirable_difficulty" in data
        assert "metacognition" in data
        assert "ewma_mastery" in data
        assert "sprt_gating" in data

    async def test_review_submission_with_confidence(
        self, auth_client: AsyncClient, sample_deck_with_notes: dict
    ):
        me = (await auth_client.get("/api/me")).json()
        user_id = uuid.UUID(me["id"])

        async with SessionLocal() as db:
            card = await db.scalar(
                select(Card).join(Deck, Deck.id == Card.deck_id).where(Deck.user_id == user_id)
            )
            card_id = str(card.id)

        resp = await auth_client.post(
            f"/api/review/{card_id}/confirm",
            json={
                "final_grade": "good",
                "overridden": False,
                "latency_ms": 2100,
                "confidence": 4,
            },
        )
        assert resp.status_code == 200

        async with SessionLocal() as db:
            latest_log = await db.scalar(
                select(ReviewLog)
                .where(ReviewLog.card_id == uuid.UUID(card_id))
                .order_by(ReviewLog.reviewed_at.desc())
            )
            assert latest_log.user_confidence == 4
