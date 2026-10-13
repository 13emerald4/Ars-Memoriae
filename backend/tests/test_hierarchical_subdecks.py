import pytest
from httpx import AsyncClient


async def _create_note(client: AsyncClient, deck_id: str, front: str, back: str):
    res = await client.post(
        "/api/notes",
        json={
            "deck_id": deck_id,
            "template_kind": "basic",
            "field_values": {"Front": front, "Back": back},
        },
    )
    assert res.status_code == 201, res.text
    return res.json()


@pytest.mark.asyncio
async def test_hierarchical_subdeck_scoping_and_rollups(auth_client: AsyncClient):
    # 1. Create parent deck: "Sciences"
    res = await auth_client.post("/api/decks", json={"name": "Sciences"})
    assert res.status_code == 201
    parent_id = res.json()["id"]

    # 2. Create child subdeck: "Physiology" under "Sciences"
    res = await auth_client.post("/api/decks", json={"name": "Physiology", "parent_id": parent_id})
    assert res.status_code == 201
    child_id = res.json()["id"]

    # 3. Create grandchild subdeck: "Neurophysiology" under "Physiology"
    res = await auth_client.post(
        "/api/decks", json={"name": "Neurophysiology", "parent_id": child_id}
    )
    assert res.status_code == 201
    grandchild_id = res.json()["id"]

    # 4. Create an independent deck: "History"
    res = await auth_client.post("/api/decks", json={"name": "History"})
    assert res.status_code == 201
    other_id = res.json()["id"]

    # Add notes to each deck
    await _create_note(auth_client, parent_id, "Science 1", "Ans 1")
    await _create_note(auth_client, child_id, "Physio 1", "Ans 2")
    await _create_note(auth_client, grandchild_id, "Neuro 1", "Ans 3")
    await _create_note(auth_client, other_id, "History 1", "Ans 4")

    # 5. Verify list_decks rollup counts
    res = await auth_client.get("/api/decks")
    assert res.status_code == 200
    decks_by_name = {d["name"]: d for d in res.json()}

    # Parent "Sciences" has 1 own card, but 3 total cards across its subdecks!
    assert decks_by_name["Sciences"]["card_count"] == 1
    assert decks_by_name["Sciences"]["total_card_count"] == 3

    # Child "Physiology" has 1 own card, but 2 total cards across itself and grandchild!
    assert decks_by_name["Physiology"]["card_count"] == 1
    assert decks_by_name["Physiology"]["total_card_count"] == 2

    # Grandchild "Neurophysiology" has 1 card
    assert decks_by_name["Neurophysiology"]["card_count"] == 1
    assert decks_by_name["Neurophysiology"]["total_card_count"] == 1

    # Independent "History" has 1 card
    assert decks_by_name["History"]["card_count"] == 1
    assert decks_by_name["History"]["total_card_count"] == 1

    # 6. Test studying the child subdeck: only Physio + Neuro cards
    res = await auth_client.get(f"/api/queue/session?deck={child_id}")
    assert res.status_code == 200
    items = res.json()["items"]
    fronts = {item["front"] for item in items}
    assert "Physio 1" in fronts
    assert "Neuro 1" in fronts
    assert "Science 1" not in fronts
    assert "History 1" not in fronts

    # 7. Test studying the parent deck: includes Science 1, Physio 1, Neuro 1
    res = await auth_client.get(f"/api/queue/session?deck={parent_id}")
    assert res.status_code == 200
    items = res.json()["items"]
    fronts = {item["front"] for item in items}
    assert "Science 1" in fronts
    assert "Physio 1" in fronts
    assert "Neuro 1" in fronts
    assert "History 1" not in fronts

    # 8. Test studying the grandchild only: only Neuro 1
    res = await auth_client.get(f"/api/queue/session?deck={grandchild_id}")
    assert res.status_code == 200
    items = res.json()["items"]
    fronts = {item["front"] for item in items}
    assert fronts == {"Neuro 1"}

    # 9. Test studying Collection (All): includes everything!
    res = await auth_client.get("/api/queue/session")
    assert res.status_code == 200
    items = res.json()["items"]
    fronts = {item["front"] for item in items}
    assert "Science 1" in fronts
    assert "Physio 1" in fronts
    assert "Neuro 1" in fronts
    assert "History 1" in fronts
