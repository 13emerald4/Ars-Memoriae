"""Tests for card analytics and memory notes endpoints:
- GET /api/cards/{card_id}/analytics
- PATCH /api/cards/{card_id}/memory-note
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_card_analytics_new_card(auth_client: AsyncClient):
    # 1. Create a deck and card
    deck_resp = await auth_client.post("/api/decks", json={"name": "Analytics Test Deck"})
    assert deck_resp.status_code == 201
    deck_id = deck_resp.json()["id"]

    note_resp = await auth_client.post(
        "/api/notes",
        json={
            "deck_id": deck_id,
            "template_kind": "basic",
            "field_values": {"Front": "What is Python?", "Back": "A high-level programming language."},
        },
    )
    assert note_resp.status_code == 201
    card_id = note_resp.json()["cards"][0]["id"]

    # 2. Query analytics for brand new card
    resp = await auth_client.get(f"/api/cards/{card_id}/analytics")
    assert resp.status_code == 200
    data = resp.json()

    assert data["card"]["id"] == card_id
    assert data["card"]["front"] == "What is Python?"
    assert data["card"]["state"] == "new"
    assert data["total_reviews"] == 0
    assert data["recall_rate"] == 0.0
    assert data["rating_counts"] == {"again": 0, "hard": 0, "good": 0, "easy": 0}
    assert data["retrievability"] is None
    assert data["avg_latency_ms"] is None
    assert data["next_intervals"] is not None
    assert "again" in data["next_intervals"]
    assert "good" in data["next_intervals"]
    assert data["review_logs"] == []


@pytest.mark.asyncio
async def test_card_analytics_with_reviews(auth_client: AsyncClient):
    # 1. Create deck and card
    deck_resp = await auth_client.post("/api/decks", json={"name": "Review Analytics Deck"})
    assert deck_resp.status_code == 201
    deck_id = deck_resp.json()["id"]

    note_resp = await auth_client.post(
        "/api/notes",
        json={
            "deck_id": deck_id,
            "template_kind": "basic",
            "field_values": {"Front": "What is 2+2?", "Back": "4"},
        },
    )
    assert note_resp.status_code == 201
    card_id = note_resp.json()["cards"][0]["id"]

    # 2. Perform two reviews
    rev1 = await auth_client.post(
        f"/api/review/{card_id}/confirm",
        json={"final_grade": "good", "overridden": False, "typed_answer": "4", "latency_ms": 1200},
    )
    assert rev1.status_code == 200

    rev2 = await auth_client.post(
        f"/api/review/{card_id}/confirm",
        json={"final_grade": "again", "overridden": False, "typed_answer": "5", "latency_ms": 2800},
    )
    assert rev2.status_code == 200

    # 3. Query analytics
    resp = await auth_client.get(f"/api/cards/{card_id}/analytics")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_reviews"] == 2
    assert data["rating_counts"]["good"] == 1
    assert data["rating_counts"]["again"] == 1
    assert data["recall_rate"] == 50.0  # 1 out of 2 recall
    assert data["avg_latency_ms"] == 2000  # (1200 + 2800) / 2
    assert data["fastest_latency_ms"] == 1200
    assert data["slowest_latency_ms"] == 2800
    assert len(data["review_logs"]) == 2
    # Verify review log item details
    log0 = data["review_logs"][0]
    assert log0["final_grade"] in ("good", "again")
    assert log0["typed_answer"] in ("4", "5")


@pytest.mark.asyncio
async def test_update_card_memory_note(auth_client: AsyncClient):
    # 1. Create card
    deck_resp = await auth_client.post("/api/decks", json={"name": "Memory Note Deck"})
    assert deck_resp.status_code == 201
    deck_id = deck_resp.json()["id"]

    note_resp = await auth_client.post(
        "/api/notes",
        json={
            "deck_id": deck_id,
            "template_kind": "basic",
            "field_values": {"Front": "DNS Port?", "Back": "53"},
        },
    )
    card_id = note_resp.json()["cards"][0]["id"]

    # 2. Patch memory note
    anchor_text = "Anchor mnemonic: DNS -> 5 letters in Domain, 3 in Net -> 53"
    patch_resp = await auth_client.patch(
        f"/api/cards/{card_id}/memory-note",
        json={"memory_note": anchor_text},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["documentation"] == anchor_text

    # 3. Verify in analytics
    analytics_resp = await auth_client.get(f"/api/cards/{card_id}/analytics")
    assert analytics_resp.status_code == 200
    assert analytics_resp.json()["card"]["documentation"] == anchor_text

    # 4. Clear memory note
    clear_resp = await auth_client.patch(
        f"/api/cards/{card_id}/memory-note",
        json={"memory_note": "   "},
    )
    assert clear_resp.status_code == 200
    assert clear_resp.json()["documentation"] is None


@pytest.mark.asyncio
async def test_card_analytics_not_found(auth_client: AsyncClient):
    import uuid
    random_id = str(uuid.uuid4())
    resp = await auth_client.get(f"/api/cards/{random_id}/analytics")
    assert resp.status_code == 404
