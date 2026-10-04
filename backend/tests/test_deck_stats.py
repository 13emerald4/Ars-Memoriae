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
