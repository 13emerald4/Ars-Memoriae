"""Unit and integration tests for Memory Champion / Athlete features (§Features 4, 5, & 6)."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.models import Deck, User
from app.services.atomicity_service import generate_sequential_clozes, lint_card_atomicity
from app.services.fsrs_service import FSRSService


def test_atomicity_linter_concise():
    res = lint_card_atomicity(
        front="What is the symbol for Gold?",
        back="Au",
        template_kind="basic",
    )
    assert res.score == 100
    assert res.is_atomic is True
    assert res.word_count_back == 1
    assert len(res.issues) == 0


def test_atomicity_linter_penalties():
    # Long multi-clause list answer with multiple questions
    res = lint_card_atomicity(
        front="What is the capital of France and what is its currency?",
        back="1. Paris is the capital; 2. Euro is the official currency; Furthermore both X and Y apply as well as Z.",
        template_kind="basic",
    )
    assert res.score < 70
    assert res.is_atomic is False
    assert any(i.code == "MULTIPLE_QUESTIONS" for i in res.issues)
    assert any(i.code == "ENUMERATED_LIST" or i.code == "MULTIPLE_CLAUSES" for i in res.issues)


def test_sequential_cloze_generator():
    steps = [
        "Identify the core problem",
        "Formulate testable hypotheses",
        "Execute empirical experiment",
        "Analyze statistical variance",
    ]
    cards = generate_sequential_clozes("Scientific Method", steps, window_size=1)
    assert len(cards) == 4
    assert cards[0].step_index == 1
    assert cards[0].back == "Identify the core problem"
    assert "Step 1: [ ? ]" in cards[0].front
    assert "Step 2: Formulate testable hypotheses" in cards[0].front

    assert cards[1].step_index == 2
    assert "Step 1: Identify the core problem" in cards[1].front
    assert "Step 2: [ ? ]" in cards[1].front


def test_event_horizon_compression():
    now = datetime.now(UTC)
    event_date = now + timedelta(days=10)

    # 1. Normal interval past event date -> compressed before event
    due_far = now + timedelta(days=25)
    compressed = FSRSService.compress_for_event_horizon(due_far, now, event_date)
    assert compressed < event_date
    assert compressed > now

    # 2. Due date already before event date -> preserved
    due_near = now + timedelta(days=4)
    preserved = FSRSService.compress_for_event_horizon(due_near, now, event_date)
    assert preserved == due_near


@pytest.mark.asyncio
async def test_memory_athlete_endpoints(auth_client):
    # Lint atomicity
    resp = await auth_client.post(
        "/api/memory/lint-atomicity",
        json={"front": "What is 2+2?", "back": "4"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["score"] == 100
    assert data["is_atomic"] is True

    # Sequential clozes
    resp = await auth_client.post(
        "/api/memory/sequential-cloze",
        json={
            "title": "Algorithm Steps",
            "steps": ["Step A", "Step B", "Step C"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["cards"]) == 3

    # Event readiness (no event set)
    resp = await auth_client.get("/api/memory/event-readiness")
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_latency_does_not_downgrade_grade_or_force_confirmation(auth_client, monkeypatch):
    import app.routers.review as review_router

    async def mock_grade(self, **kwargs):
        return {
            "score": 95,
            "confidence": 0.95,
            "matched_points": ["correct answer"],
            "missed_points": [],
            "reasoning": "Accurate answer",
        }

    monkeypatch.setattr(review_router.GradingService, "grade_with_escalation", mock_grade)

    await auth_client.patch(
        "/api/me",
        json={"llm_grading_consent": True, "automaticity_threshold_ms": 3000},
    )

    deck_resp = await auth_client.post("/api/decks", json={"name": "Purity Deck"})
    deck_id = deck_resp.json()["id"]

    note_resp = await auth_client.post(
        "/api/notes",
        json={
            "deck_id": deck_id,
            "template_kind": "basic",
            "field_values": {"Front": "Capital of Japan?", "Back": "Tokyo"},
        },
    )
    card_id = note_resp.json()["cards"][0]["id"]

    # Submit with 25 seconds of latency (threshold is 3s)
    ans_resp = await auth_client.post(
        f"/api/review/{card_id}/answer",
        json={"typed_answer": "Tokyo", "latency_ms": 25000},
    )
    assert ans_resp.status_code == 200
    data = ans_resp.json()

    # Crucial assertion: score 95 maps to "good" (or "easy"), NOT "hard"
    assert data["score"] == 95
    assert data["suggested_grade"] in ("good", "easy")
    assert data["suggested_grade"] != "hard"
    # Latency alone must not force confirmation
    assert data["needs_confirmation"] is False
    # Informational telemetry is still tracked
    assert data["automaticity_exceeded"] is True
    assert "Graded purely on correctness" in data["automaticity_note"]



async def test_event_horizon_can_be_cleared(auth_client):
    """Settings clears the event by sending null; that must not be ignored."""
    event = (datetime.now(UTC) + timedelta(days=10)).isoformat()
    me = await auth_client.patch(
        "/api/me", json={"target_event_date": event, "target_event_title": "Final"}
    )
    assert me.json()["target_event_date"] is not None

    me = await auth_client.patch(
        "/api/me", json={"target_event_date": None, "target_event_title": None}
    )
    assert me.json()["target_event_date"] is None
    assert me.json()["target_event_title"] is None
    # Fields left out are still untouched by a PATCH.
    me = await auth_client.patch("/api/me", json={"daily_new_limit": 7})
    assert me.json()["daily_new_limit"] == 7


@pytest.mark.parametrize(
    ("offset_days", "expected"), [(-3, "desired_retention"), (5, "peak_retention_target")]
)
async def test_only_an_upcoming_event_ramps_retention(
    auth_client, monkeypatch, offset_days, expected
):
    import app.routers.review as review_router

    seen: list[float] = []
    real_init = review_router.FSRSService.__init__

    def spy_init(self, *args, **kwargs):
        seen.append(kwargs["desired_retention"])
        real_init(self, *args, **kwargs)

    monkeypatch.setattr(review_router.FSRSService, "__init__", spy_init)

    event = (datetime.now(UTC) + timedelta(days=offset_days)).isoformat()
    me = (
        await auth_client.patch(
            "/api/me",
            json={
                "target_event_date": event,
                "desired_retention": 0.8,
                "peak_retention_target": 0.97,
            },
        )
    ).json()
    deck_id = (await auth_client.post("/api/decks", json={"name": "Exam"})).json()["id"]
    note = (
        await auth_client.post(
            "/api/notes",
            json={
                "deck_id": deck_id,
                "template_kind": "basic",
                "field_values": {"Front": "q", "Back": "a"},
            },
        )
    ).json()
    resp = await auth_client.post(
        f"/api/review/{note['cards'][0]['id']}/confirm",
        json={"final_grade": "good", "overridden": False},
    )
    assert resp.status_code == 200, resp.text
    assert seen == [me[expected]]
