"""Tests for the Deck Stats endpoint GET /api/decks/{deck_id}/stats."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_deck_stats_empty_and_populated(auth_client: AsyncClient):
    # 1. Create a deck
    create_resp = await auth_client.post("/api/decks", json={"name": "Algorithms Test Deck"})
    assert create_resp.status_code == 201
    deck_id = create_resp.json()["id"]

    # 2. Check stats for empty deck
    empty_stats_resp = await auth_client.get(f"/api/decks/{deck_id}/stats")
    assert empty_stats_resp.status_code == 200
    empty_stats = empty_stats_resp.json()
    assert empty_stats["total_cards"] == 0
    assert empty_stats["viewed_cards"] == 0
    assert empty_stats["viewed_ratio"] == 0.0

    # 3. Add notes with different difficulties
    # Easy card
    await auth_client.post(
        "/api/notes",
        json={
            "deck_id": deck_id,
            "template_kind": "basic",
            "field_values": {"front": "Binary Search?", "back": "O(log n)", "difficulty": "Easy"},
        },
    )
    # Medium card
    await auth_client.post(
        "/api/notes",
        json={
            "deck_id": deck_id,
            "template_kind": "basic",
            "field_values": {"front": "Dijkstra?", "back": "O(E log V)", "difficulty": "Medium"},
        },
    )
    # Hard card
    await auth_client.post(
        "/api/notes",
        json={
            "deck_id": deck_id,
            "template_kind": "basic",
            "field_values": {"front": "A* Heuristic?", "back": "Admissible & consistent", "difficulty": "Hard"},
        },
    )

    # 4. Check populated deck stats
    stats_resp = await auth_client.get(f"/api/decks/{deck_id}/stats")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["total_cards"] == 3
    assert stats["new_cards"] == 3
    assert stats["viewed_cards"] == 0
    assert stats["viewed_ratio"] == 0.0
    assert stats["difficulty_counts"]["Easy"] == 1
    assert stats["difficulty_counts"]["Medium"] == 1
    assert stats["difficulty_counts"]["Hard"] == 1
    assert round(stats["difficulty_proportions"]["Easy"], 2) == 0.33
    assert round(stats["difficulty_proportions"]["Medium"], 2) == 0.33
    assert round(stats["difficulty_proportions"]["Hard"], 2) == 0.33
    assert "rating_counts" in stats
    assert "rating_proportions" in stats
    assert stats["total_reviews"] == 0
    assert stats["rating_counts"]["Unrated"] == 3


@pytest.mark.asyncio
async def test_hierarchical_deck_stats_and_collection(auth_client: AsyncClient):
    # 1. Create a parent deck and child subdeck
    p_resp = await auth_client.post("/api/decks", json={"name": "Parent Deck"})
    assert p_resp.status_code == 201
    parent_id = p_resp.json()["id"]

    c_resp = await auth_client.post(
        "/api/decks", json={"name": "Child Subdeck", "parent_id": parent_id}
    )
    assert c_resp.status_code == 201
    child_id = c_resp.json()["id"]

    # 2. Add notes only to the child subdeck
    await auth_client.post(
        "/api/notes",
        json={
            "deck_id": child_id,
            "template_kind": "basic",
            "field_values": {"front": "Q1", "back": "A1", "difficulty": "Easy"},
        },
    )
    await auth_client.post(
        "/api/notes",
        json={
            "deck_id": child_id,
            "template_kind": "basic",
            "field_values": {"front": "Q2", "back": "A2", "difficulty": "Hard"},
        },
    )

    # 3. GET /api/decks should include stats on each deck, and parent should roll up child
    decks_resp = await auth_client.get("/api/decks")
    assert decks_resp.status_code == 200
    decks = decks_resp.json()
    parent_deck = next(d for d in decks if d["id"] == parent_id)
    child_deck = next(d for d in decks if d["id"] == child_id)

    assert child_deck["card_count"] == 2
    assert child_deck["stats"]["total_cards"] == 2
    assert child_deck["stats"]["difficulty_counts"]["Easy"] == 1
    assert child_deck["stats"]["difficulty_counts"]["Hard"] == 1

    assert parent_deck["card_count"] == 0
    assert parent_deck["total_card_count"] == 2
    assert parent_deck["stats"] is not None
    assert parent_deck["stats"]["total_cards"] == 2
    assert parent_deck["stats"]["difficulty_counts"]["Easy"] == 1
    assert parent_deck["stats"]["difficulty_counts"]["Hard"] == 1

    # 4. GET /api/decks/{parent_id}/stats should hierarchically include child cards
    parent_stats_resp = await auth_client.get(f"/api/decks/{parent_id}/stats")
    assert parent_stats_resp.status_code == 200
    parent_stats = parent_stats_resp.json()
    assert parent_stats["total_cards"] == 2
    assert parent_stats["difficulty_counts"]["Easy"] == 1
    assert parent_stats["difficulty_counts"]["Hard"] == 1

    # 5. GET /api/decks/__root__/stats should return collection stats
    root_stats_resp = await auth_client.get("/api/decks/__root__/stats")
    assert root_stats_resp.status_code == 200
    root_stats = root_stats_resp.json()
    assert root_stats["id"] == "__root__"
    assert root_stats["total_cards"] >= 2

