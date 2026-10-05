"""Tests for the Persist Deck Review endpoint GET /api/decks/{deck_id}/persist-items."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_deck_persist_items(auth_client: AsyncClient):
    # 1. Create a deck
    create_resp = await auth_client.post("/api/decks", json={"name": "Persist Test Deck"})
    assert create_resp.status_code == 201
    deck_id = create_resp.json()["id"]

    # 2. Persist items for empty deck
    empty_resp = await auth_client.get(f"/api/decks/{deck_id}/persist-items")
    assert empty_resp.status_code == 200
    assert empty_resp.json() == []

    # 3. Add notes
    await auth_client.post(
        "/api/notes",
        json={
            "deck_id": deck_id,
            "template_kind": "basic",
            "field_values": {"Front": "Q1", "Back": "A1"},
        },
    )
    await auth_client.post(
        "/api/notes",
        json={
            "deck_id": deck_id,
            "template_kind": "basic",
            "field_values": {"Front": "Q2", "Back": "A2"},
        },
    )

    # 4. Fetch persist items
    resp = await auth_client.get(f"/api/decks/{deck_id}/persist-items")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2
    assert all(i["kind"] == "card" for i in items)
    assert all(i["deck_or_source_id"] == deck_id for i in items)
    assert all(i["deck_name"] == "Persist Test Deck" for i in items)
    fronts = {i["front"] for i in items}
    assert "Q1" in fronts
    assert "Q2" in fronts

    # 5. Suspend one card -> only 1 item returned
    card_id = items[0]["id"]
    suspend_resp = await auth_client.post(f"/api/cards/{card_id}/suspend?suspended=true")
    assert suspend_resp.status_code == 200

    resp_after_suspend = await auth_client.get(f"/api/decks/{deck_id}/persist-items")
    assert resp_after_suspend.status_code == 200
    assert len(resp_after_suspend.json()) == 1


@pytest.mark.asyncio
async def test_deck_persist_items_tenant_isolation(client: AsyncClient):
    # Register user 1
    r1 = await client.post("/api/auth/register", json={"email": "u1@example.com", "password": "password1234"})
    token1 = r1.json()["access_token"]
    c1 = AsyncClient(transport=client._transport, base_url="http://test", headers={"Authorization": f"Bearer {token1}"})

    # Register user 2
    r2 = await client.post("/api/auth/register", json={"email": "u2@example.com", "password": "password1234"})
    token2 = r2.json()["access_token"]
    c2 = AsyncClient(transport=client._transport, base_url="http://test", headers={"Authorization": f"Bearer {token2}"})

    # User 1 creates deck
    d_resp = await c1.post("/api/decks", json={"name": "U1 Secret Deck"})
    deck_id = d_resp.json()["id"]

    # User 2 tries to fetch persist items -> 404
    resp = await c2.get(f"/api/decks/{deck_id}/persist-items")
    assert resp.status_code == 404

