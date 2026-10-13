"""Tests for the All Cards Run endpoint GET /api/decks/{deck_id}/all-cards-run-items.

Verifies:
- All cards in deck are returned consecutively
- Ordered ascending from easiest to hardest
- Suspended cards are excluded
- Tenant isolation is respected
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_deck_all_cards_run_items_ordered_by_difficulty(auth_client: AsyncClient):
    # 1. Create a deck
    create_resp = await auth_client.post("/api/decks", json={"name": "Difficulty Sort Run Deck"})
    assert create_resp.status_code == 201
    deck_id = create_resp.json()["id"]

    # 2. Run items for empty deck
    empty_resp = await auth_client.get(f"/api/decks/{deck_id}/all-cards-run-items")
    assert empty_resp.status_code == 200
    assert empty_resp.json() == []

    # 3. Add 3 notes with different difficulties: Hard, Easy, Medium
    # Hard note
    await auth_client.post(
        "/api/notes",
        json={
            "deck_id": deck_id,
            "template_kind": "basic",
            "field_values": {"Front": "Hard Question", "Back": "Hard Answer", "difficulty": "Hard"},
        },
    )
    # Easy note
    await auth_client.post(
        "/api/notes",
        json={
            "deck_id": deck_id,
            "template_kind": "basic",
            "field_values": {"Front": "Easy Question", "Back": "Easy Answer", "difficulty": "Easy"},
        },
    )
    # Medium note
    await auth_client.post(
        "/api/notes",
        json={
            "deck_id": deck_id,
            "template_kind": "basic",
            "field_values": {"Front": "Medium Question", "Back": "Medium Answer", "difficulty": "Medium"},
        },
    )

    # 4. Fetch all-cards-run items
    resp = await auth_client.get(f"/api/decks/{deck_id}/all-cards-run-items")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 3
    assert all(i["kind"] == "card" for i in items)
    assert all(i["deck_or_source_id"] == deck_id for i in items)
    assert all(i["deck_name"] == "Difficulty Sort Run Deck" for i in items)

    # Must be ordered easiest first, then medium, then hard
    fronts = [i["front"] for i in items]
    assert fronts[0] == "Easy Question"
    assert fronts[1] == "Medium Question"
    assert fronts[2] == "Hard Question"

    # 5. Suspend the easy card -> remaining 2 items in order: Medium, then Hard
    easy_card_id = items[0]["id"]
    suspend_resp = await auth_client.post(f"/api/cards/{easy_card_id}/suspend?suspended=true")
    assert suspend_resp.status_code == 200

    resp_after_suspend = await auth_client.get(f"/api/decks/{deck_id}/all-cards-run-items")
    assert resp_after_suspend.status_code == 200
    remaining_items = resp_after_suspend.json()
    assert len(remaining_items) == 2
    assert [i["front"] for i in remaining_items] == ["Medium Question", "Hard Question"]


@pytest.mark.asyncio
async def test_deck_all_cards_run_tenant_isolation(client: AsyncClient):
    # Register user 1
    r1 = await client.post("/api/auth/register", json={"email": "run_u1@example.com", "password": "password1234"})
    token1 = r1.json()["access_token"]
    c1 = AsyncClient(transport=client._transport, base_url="http://test", headers={"Authorization": f"Bearer {token1}"})

    # Register user 2
    r2 = await client.post("/api/auth/register", json={"email": "run_u2@example.com", "password": "password1234"})
    token2 = r2.json()["access_token"]
    c2 = AsyncClient(transport=client._transport, base_url="http://test", headers={"Authorization": f"Bearer {token2}"})

    # User 1 creates deck
    d_resp = await c1.post("/api/decks", json={"name": "User 1 Run Deck"})
    deck_id = d_resp.json()["id"]

    # User 2 tries to fetch all cards run items -> 404
    resp = await c2.get(f"/api/decks/{deck_id}/all-cards-run-items")
    assert resp.status_code == 404
