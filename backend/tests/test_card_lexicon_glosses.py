import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_card_lexicon_glosses_endpoint_and_queue(auth_client: AsyncClient):
    # 1. Create a deck
    deck_resp = await auth_client.post(
        "/api/decks",
        json={"name": "Spanish Literature"},
    )
    assert deck_resp.status_code == 201, deck_resp.text
    deck_id = deck_resp.json()["id"]

    # 2. Create a card
    note_resp = await auth_client.post(
        "/api/notes",
        json={
            "deck_id": deck_id,
            "template_kind": "basic",
            "field_values": {
                "Front": "Cervantes y el término hidalgo",
                "Back": "Un hidalgo es miembro de la nobleza o hidalguía.",
            },
        },
    )
    assert note_resp.status_code == 201, note_resp.text
    note = note_resp.json()
    assert len(note["cards"]) >= 1
    card = note["cards"][0]
    card_id = card["id"]
    assert card.get("lexicon_glosses") == []

    # 3. Patch lexicon glosses
    sample_glosses = [
        {
            "term": "hidalgo",
            "source": "RAE Lexicon",
            "definitions": ["Persona que por su sangre es de una clase noble y distinguida."],
            "pinned_at": "2026-10-20T00:00:00Z",
        },
        {
            "term": "hidalguía",
            "source": "Concordance",
            "definitions": ["Nobleza de ánimo; generosidad."],
            "pinned_at": "2026-10-20T00:01:00Z",
        },
    ]

    patch_resp = await auth_client.patch(
        f"/api/cards/{card_id}/lexicon-glosses",
        json={"glosses": sample_glosses},
    )
    assert patch_resp.status_code == 200, patch_resp.text
    updated_card = patch_resp.json()
    assert len(updated_card["lexicon_glosses"]) == 2
    assert updated_card["lexicon_glosses"][0]["term"] == "hidalgo"

    # 4. Verify in queue item
    queue_resp = await auth_client.get(
        f"/api/queue/session?deck={deck_id}",
    )
    assert queue_resp.status_code == 200, queue_resp.text
    items = queue_resp.json()["items"]
    matching = [item for item in items if item.get("id") == card_id]
    assert len(matching) == 1
    queue_item = matching[0]
    assert len(queue_item.get("lexicon_glosses", [])) == 2
    assert queue_item["lexicon_glosses"][0]["term"] == "hidalgo"
