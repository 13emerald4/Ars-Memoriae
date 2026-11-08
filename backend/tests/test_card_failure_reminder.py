from __future__ import annotations

import uuid
import pytest
from datetime import UTC, datetime

from app.models import Card, Deck, Note, NoteType, ReviewLog, User
from app.services.queue_service import ComposedItem, attach_failure_memories


@pytest.mark.asyncio
async def test_attach_failure_memories_active_weaknesses():
    """Card with active weaknesses generates a direct failure reminder."""
    item = ComposedItem(
        kind="card",
        id=str(uuid.uuid4()),
        deck_or_source_id=str(uuid.uuid4()),
        priority=50,
        effective_priority=50.0,
        front="What is 2+2?",
        back="4",
        deck_name="Math",
        active_weaknesses=["Confused addition with multiplication."],
    )

    # Calling with None for db is fine because Tier 1 does not need DB lookup
    await attach_failure_memories(None, [item])
    assert item.failure_reminder is not None
    assert "Where you stumbled: Confused addition with multiplication" in item.failure_reminder


@pytest.mark.asyncio
async def test_attach_failure_memories_multiple_active_weaknesses():
    """Card with multiple active weaknesses mentions other flaws."""
    item = ComposedItem(
        kind="card",
        id=str(uuid.uuid4()),
        deck_or_source_id=str(uuid.uuid4()),
        priority=50,
        effective_priority=50.0,
        front="Implement binary search",
        back="code",
        deck_name="Algorithms",
        active_weaknesses=["Off-by-one boundary", "Integer overflow on mid"],
    )

    await attach_failure_memories(None, [item])
    assert item.failure_reminder is not None
    assert "Where you stumbled: Off-by-one boundary (+1 other flaw)" == item.failure_reminder


@pytest.mark.asyncio
async def test_attach_failure_memories_weakness_history():
    """Card with weakness history (but no active weakness) recalls the recent stumbling block."""
    item = ComposedItem(
        kind="card",
        id=str(uuid.uuid4()),
        deck_or_source_id=str(uuid.uuid4()),
        priority=50,
        effective_priority=50.0,
        front="What is recursion?",
        back="A function calling itself",
        deck_name="CS",
        active_weaknesses=[],
        weakness_history=[
            {
                "reviewed_at": "2026-10-20T10:00:00Z",
                "final_grade": "again",
                "weaknesses_identified": ["Forgot to mention the base termination case."],
            }
        ],
    )

    await attach_failure_memories(None, [item])
    assert item.failure_reminder is not None
    assert "Recent stumbling block: Forgot to mention the base termination case" in item.failure_reminder


@pytest.mark.asyncio
async def test_attach_failure_memories_from_review_log(auth_client):
    """Card without active weaknesses or weakness_history falls back to ReviewLog critique."""
    # Create deck and note via API
    deck_resp = await auth_client.post("/api/decks", json={"name": "Memory Deck", "default_priority": 50})
    assert deck_resp.status_code == 201
    deck_id = deck_resp.json()["id"]

    note_resp = await auth_client.post(
        "/api/notes",
        json={
            "deck_id": deck_id,
            "template_kind": "basic",
            "field_values": {"Front": "Explain event loop", "Back": "Single-threaded concurrency mechanism"},
        },
    )
    assert note_resp.status_code == 201
    card_id = note_resp.json()["cards"][0]["id"]

    # Before any review, failure_reminder must be None in queue
    q_resp = await auth_client.get("/api/queue/session")
    assert q_resp.status_code == 200
    items = q_resp.json()["items"]
    target_item = next((i for i in items if i["id"] == card_id), None)
    assert target_item is not None
    assert target_item.get("failure_reminder") is None

    # Submit a failed review with 'again'
    review_resp = await auth_client.post(
        f"/api/review/{card_id}/confirm",
        json={
            "final_grade": "again",
            "typed_answer": "It is multi-threaded",
            "latency_ms": 2500,
        },
    )
    assert review_resp.status_code == 200

    # Next fetch of deck cards should have failure_reminder populated from ReviewLog!
    run_resp = await auth_client.get(f"/api/decks/{deck_id}/all-cards-run-items")
    assert run_resp.status_code == 200
    items2 = run_resp.json()
    target_item2 = next((i for i in items2 if i["id"] == card_id), None)
    assert target_item2 is not None
    assert target_item2.get("failure_reminder") is not None
    assert "Lapsed on previous review" in target_item2["failure_reminder"]
