import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_deck_and_card_documentation(auth_client: AsyncClient):
    # 1. Create deck with thematic nature, documentation, and source documents
    deck_resp = await auth_client.post(
        "/api/decks",
        json={
            "name": "Distributed Systems",
            "thematic_nature": "Consensus Protocols & Fault Tolerance",
            "documentation": "Covers Paxos, Raft, and Viewstamped Replication for high-availability clusters.",
            "source_documents": [
                {"title": "In Search of an Understandable Consensus Algorithm (Ongaro, Ousterhout)", "type": "paper"},
                {"title": "Paxos Made Simple (Lamport)", "type": "paper"},
            ],
        },
    )
    assert deck_resp.status_code == 201, deck_resp.text
    deck = deck_resp.json()
    assert deck["thematic_nature"] == "Consensus Protocols & Fault Tolerance"
    assert "Covers Paxos, Raft" in deck["documentation"]
    assert len(deck["source_documents"]) == 2
    deck_id = deck["id"]

    # 2. Check list_decks returns the documentation fields
    list_resp = await auth_client.get("/api/decks")
    assert list_resp.status_code == 200
    found = next((d for d in list_resp.json() if d["id"] == deck_id), None)
    assert found is not None
    assert found["thematic_nature"] == "Consensus Protocols & Fault Tolerance"
    assert len(found["source_documents"]) == 2

    # 3. Create a card in this deck (without explicit card documentation)
    # It should automatically inherit the deck's theme, documentation, and source documents
    note_resp = await auth_client.post(
        "/api/notes",
        json={
            "deck_id": deck_id,
            "template_kind": "basic",
            "field_values": {
                "Front": "What is the primary role of the leader in Raft?",
                "Back": "To manage log replication and maintain strong consistency across follower nodes.",
            },
        },
    )
    assert note_resp.status_code == 201, note_resp.text
    note = note_resp.json()
    assert len(note["cards"]) >= 1
    card = note["cards"][0]
    assert card["thematic_nature"] == "Consensus Protocols & Fault Tolerance"
    assert "Covers Paxos, Raft" in card["documentation"]
    assert len(card["source_documents"]) == 2

    # 4. Create another card with card-specific documentation override
    note_override_resp = await auth_client.post(
        "/api/notes",
        json={
            "deck_id": deck_id,
            "template_kind": "basic",
            "field_values": {
                "Front": "What is split brain in Paxos?",
                "Back": "When network partitioning causes multiple leaders to accept conflicting writes.",
            },
            "thematic_nature": "Network Partitions & Safety",
            "documentation": "Specifically addresses CAP theorem network split failure modes.",
            "source_documents": [{"title": "Brewer's Conjecture & CAP Theorem"}],
        },
    )
    assert note_override_resp.status_code == 201
    card2 = note_override_resp.json()["cards"][0]
    assert card2["thematic_nature"] == "Network Partitions & Safety"
    assert "specifically addresses cap" in card2["documentation"].lower()
    assert len(card2["source_documents"]) == 1

    # 5. Verify queue item has deck and card documentation attached
    session_resp = await auth_client.get(f"/api/queue/session?deck={deck_id}")
    assert session_resp.status_code == 200, session_resp.text
    items = session_resp.json()["items"]
    assert len(items) >= 2
    item1 = next((i for i in items if i["id"] == card["id"]), None)
    assert item1 is not None
    assert item1["deck_thematic_nature"] == "Consensus Protocols & Fault Tolerance"
    assert item1["card_thematic_nature"] == "Consensus Protocols & Fault Tolerance"
    assert len(item1["deck_source_documents"]) == 2

    # 6. Verify PATCH deck updates documentation
    patch_deck_resp = await auth_client.patch(
        f"/api/decks/{deck_id}",
        json={"thematic_nature": "Modern Distributed Consensus & Byzantine Fault Tolerance"},
    )
    assert patch_deck_resp.status_code == 200
    assert patch_deck_resp.json()["thematic_nature"] == "Modern Distributed Consensus & Byzantine Fault Tolerance"

    # 7. Test show_thematic_context toggle in user profile
    me_resp = await auth_client.get("/api/me")
    assert me_resp.json()["show_thematic_context"] is True

    patch_me = await auth_client.patch("/api/me", json={"show_thematic_context": False})
    assert patch_me.status_code == 200
    assert patch_me.json()["show_thematic_context"] is False
