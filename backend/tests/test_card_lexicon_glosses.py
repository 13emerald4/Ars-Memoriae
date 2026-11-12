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

    # 5. Append single gloss via POST without overwriting existing items
    add_resp = await auth_client.post(
        f"/api/cards/{card_id}/lexicon-glosses",
        json={
            "gloss": {
                "term": "Siglo de Oro",
                "definition": "Period of flourishing in Spanish arts and literature.",
                "source": "AI Lexicon",
            }
        },
    )
    assert add_resp.status_code == 200, add_resp.text
    after_add = add_resp.json()["lexicon_glosses"]
    assert [g["term"] for g in after_add] == ["hidalgo", "hidalguía", "Siglo de Oro"]

    # Duplicate canonical term should not append a second copy
    dup_resp = await auth_client.post(
        f"/api/cards/{card_id}/lexicon-glosses",
        json={
            "gloss": {
                "term": "hidalgo",
                "definition": "Duplicate definition",
                "context_explanation": "Extra context",
            }
        },
    )
    assert dup_resp.status_code == 200, dup_resp.text
    after_dup = dup_resp.json()["lexicon_glosses"]
    assert len(after_dup) == 3
    assert after_dup[0]["context_explanation"] == "Extra context"


def test_extract_term_definitions_from_qa_and_merge():
    from app.services.code_ai_service import (
        canonical_term_key,
        extract_term_definitions_from_qa,
        merge_lexicon_glosses,
    )

    sample_answer = (
        "* `this`: Refers to the current instance of the `Playlist` class.\n"
        "* `songs`: An array of `Song` objects that represents the songs in the playlist.\n"
        "* `s`: A variable used in the `filter` method to represent each `Song` object.\n"
        "* `getGenres()`: A method of the `Song` class that returns an array of genres.\n"
        "* `.includes(genre)`: A method that checks if `genre` is present in the array.\n"
        "* `.length`: A property that gives the count of filtered songs.\n"
        "* **Summary**: Overall filter and count."
    )

    extracted = extract_term_definitions_from_qa(
        question="explain following terms: this,songs,s,getGenres,.includes,length",
        answer=sample_answer,
        doc_citation="[CPSC 210 · p. 16]",
        language="typescript",
    )

    terms = [e["term"] for e in extracted]
    assert terms == ["this", "songs", "s", "getGenres()", ".includes(genre)", ".length"]
    assert extracted[0]["context_explanation"] == "Cited: [CPSC 210 · p. 16]"
    assert canonical_term_key(".includes(genre)") == "includes"
    assert canonical_term_key("getGenres()") == "getgenres"

    # Follow-up prose without bullets
    prose_extracted = extract_term_definitions_from_qa(
        question="what does .filter do?",
        answer="The `.filter()` method creates a new array containing all elements matching the predicate.",
        selected_code=".filter",
        language="typescript",
    )
    assert len(prose_extracted) == 1
    assert prose_extracted[0]["term"] == ".filter"

    # Deduplication merge
    merged = merge_lexicon_glosses(
        extracted,
        [
            {"term": "length", "definition": "Duplicate length"},
            {"term": "filter", "definition": "Creates filtered shallow array copy."},
        ],
    )
    assert [m["term"] for m in merged] == [
        "this",
        "songs",
        "s",
        "getGenres()",
        ".includes(genre)",
        ".length",
        "filter",
    ]


@pytest.mark.asyncio
async def test_ask_docs_auto_populates_card_lexicon_glosses(auth_client: AsyncClient, monkeypatch):
    from app.services.code_ai_service import CodeAiService

    deck_resp = await auth_client.post("/api/decks", json={"name": "CPSC 210 MT3"})
    assert deck_resp.status_code == 201, deck_resp.text
    deck_id = deck_resp.json()["id"]

    note_resp = await auth_client.post(
        "/api/notes",
        json={
            "deck_id": deck_id,
            "template_kind": "basic",
            "field_values": {
                "Front": "Implement getGenreFrequency",
                "Back": "return this.songs.filter((s: Song) => s.getGenres().includes(genre)).length;",
            },
        },
    )
    assert note_resp.status_code == 201, note_resp.text
    card_id = note_resp.json()["cards"][0]["id"]

    async def fake_generate(self, prompt: str, model=None, allow_smaller_model=True):
        return (
            "* `this`: Current instance of `Playlist`.\n"
            "* `getGenres()`: Returns the array of `Genre` values for a `Song`."
        )

    async def fake_verify(self):
        return ["qwen2.5-coder:7b"]

    monkeypatch.setattr("app.services.grading_service.GradingService._generate", fake_generate)
    monkeypatch.setattr("app.services.grading_service.GradingService.verify_engine", fake_verify)

    resp = await auth_client.post(
        "/api/code/ask-docs",
        json={
            "question": "explain this and getGenres()",
            "selected_code": "this.songs.filter((s: Song) => s.getGenres())",
            "language": "typescript",
            "deck_id": deck_id,
            "card_id": card_id,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data["extracted_glosses"]) == 2
    assert data["updated_card_glosses"] is not None
    assert [g["term"] for g in data["updated_card_glosses"]] == ["this", "getGenres()"]

    # Confirm persisted in queue session
    queue_resp = await auth_client.get(f"/api/queue/session?deck={deck_id}")
    assert queue_resp.status_code == 200
    items = queue_resp.json()["items"]
    matching = [item for item in items if item.get("id") == card_id]
    assert len(matching) == 1
    assert [g["term"] for g in matching[0]["lexicon_glosses"]] == ["this", "getGenres()"]

