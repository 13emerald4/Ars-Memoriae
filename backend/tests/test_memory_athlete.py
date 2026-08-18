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
