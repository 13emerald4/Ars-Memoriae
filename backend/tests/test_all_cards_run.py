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

    # 4. Fetch all-cards-run items in difficulty order
    resp = await auth_client.get(f"/api/decks/{deck_id}/all-cards-run-items?order=difficulty")
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

    resp_after_suspend = await auth_client.get(f"/api/decks/{deck_id}/all-cards-run-items?order=difficulty")
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


@pytest.mark.asyncio
async def test_only_the_latest_grade_moves_a_card(auth_client: AsyncClient):
    """A card's *latest* grade sets its place; older history doesn't."""
    import uuid
    from datetime import UTC, datetime, timedelta

    from app.db import SessionLocal
    from app.models import ReviewLog

    deck_id = (await auth_client.post("/api/decks", json={"name": "Latest Grade"})).json()["id"]
    ids = {}
    for front in ("Recovered", "Slipped"):
        note = (
            await auth_client.post(
                "/api/notes",
                json={
                    "deck_id": deck_id,
                    "template_kind": "basic",
                    "field_values": {"Front": front, "Back": "x"},
                },
            )
        ).json()
        ids[front] = uuid.UUID(note["cards"][0]["id"])

    now = datetime.now(UTC)
    history = {"Recovered": ["again", "again", "easy"], "Slipped": ["easy", "easy", "again"]}
    async with SessionLocal() as db:
        for front, grades in history.items():
            for i, grade in enumerate(grades):
                db.add(
                    ReviewLog(
                        card_id=ids[front],
                        reviewed_at=now - timedelta(days=3 - i),
                        final_grade=grade,
                        state_before="review",
                    )
                )
        await db.commit()

    items = (await auth_client.get(f"/api/decks/{deck_id}/all-cards-run-items?order=difficulty")).json()
    assert [i["front"] for i in items] == ["Recovered", "Slipped"]


@pytest.mark.asyncio
async def test_deck_all_cards_run_items_ordered_by_curriculum(auth_client: AsyncClient):
    """Curriculum order returns items in depth-first deck order and card position order (1 -> N)."""
    # 1. Root course deck
    root_resp = await auth_client.post("/api/decks", json={"name": "Course Root", "position": 0})
    root_id = root_resp.json()["id"]

    # 2. Subdeck 1 (position 0) and Subdeck 2 (position 1)
    sub1_resp = await auth_client.post("/api/decks", json={"name": "01 Intro", "parent_id": root_id, "position": 0})
    sub1_id = sub1_resp.json()["id"]

    sub2_resp = await auth_client.post("/api/decks", json={"name": "02 Advanced", "parent_id": root_id, "position": 1})
    sub2_id = sub2_resp.json()["id"]

    # 3. Add cards to Subdeck 1 with explicit positions
    note_a1 = (await auth_client.post("/api/notes", json={
        "deck_id": sub1_id,
        "template_kind": "basic",
        "field_values": {"Front": "Card 1.1", "Back": "Answer 1.1"},
    })).json()
    card_a1_id = note_a1["cards"][0]["id"]
    await auth_client.post("/api/cards/reorder", json={"items": [{"id": card_a1_id, "position": 0}]})

    note_a2 = (await auth_client.post("/api/notes", json={
        "deck_id": sub1_id,
        "template_kind": "basic",
        "field_values": {"Front": "Card 1.2", "Back": "Answer 1.2"},
    })).json()
    card_a2_id = note_a2["cards"][0]["id"]
    await auth_client.post("/api/cards/reorder", json={"items": [{"id": card_a2_id, "position": 1}]})

    # 4. Add cards to Subdeck 2 with explicit positions
    note_b1 = (await auth_client.post("/api/notes", json={
        "deck_id": sub2_id,
        "template_kind": "basic",
        "field_values": {"Front": "Card 2.1", "Back": "Answer 2.1"},
    })).json()
    card_b1_id = note_b1["cards"][0]["id"]
    await auth_client.post("/api/cards/reorder", json={"items": [{"id": card_b1_id, "position": 0}]})

    note_b2 = (await auth_client.post("/api/notes", json={
        "deck_id": sub2_id,
        "template_kind": "basic",
        "field_values": {"Front": "Card 2.2", "Back": "Answer 2.2"},
    })).json()
    card_b2_id = note_b2["cards"][0]["id"]
    await auth_client.post("/api/cards/reorder", json={"items": [{"id": card_b2_id, "position": 1}]})

    # 5. Fetch all-cards-run items for root deck with default order (curriculum)
    resp = await auth_client.get(f"/api/decks/{root_id}/all-cards-run-items")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 4
    # Must follow subdeck 1 position 0, 1 then subdeck 2 position 0, 1
    fronts = [i["front"] for i in items]
    assert fronts == ["Card 1.1", "Card 1.2", "Card 2.1", "Card 2.2"]

    # 6. Explicit order=curriculum matches
    resp_curriculum = await auth_client.get(f"/api/decks/{root_id}/all-cards-run-items?order=curriculum")
    assert resp_curriculum.status_code == 200
    assert [i["front"] for i in resp_curriculum.json()] == ["Card 1.1", "Card 1.2", "Card 2.1", "Card 2.2"]

    # 7. Subdeck-scoped run only returns that subdeck's cards
    sub1_run = await auth_client.get(f"/api/decks/{sub1_id}/all-cards-run-items")
    assert sub1_run.status_code == 200
    assert [i["front"] for i in sub1_run.json()] == ["Card 1.1", "Card 1.2"]
