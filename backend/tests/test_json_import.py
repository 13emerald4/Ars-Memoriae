"""POST /api/import/json — bulk note/card creation from a JSON payload."""

from __future__ import annotations


async def test_creates_a_new_deck_and_basic_notes(auth_client):
    resp = await auth_client.post(
        "/api/import/json",
        json={
            "deck": "Spanish",
            "priority": 70,
            "notes": [
                {"front": "hablar", "back": "to speak", "tags": ["verbs"]},
                {"front": "comer", "back": "to eat"},
            ],
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["deck_created"] is True
    assert body["notes_created"] == 2
    assert body["cards_created"] == 2
    assert body["warnings"] == []

    decks = (await auth_client.get("/api/decks")).json()
    deck = next(d for d in decks if d["id"] == body["deck_id"])
    assert deck["name"] == "Spanish"
    assert deck["default_priority"] == 70
    assert deck["card_count"] == 2

    cards = (await auth_client.get(f"/api/cards?deck_id={deck['id']}")).json()
    fronts = {c["front"] for c in cards}
    assert fronts == {"hablar", "comer"}
    verbs_card = next(c for c in cards if c["front"] == "hablar")
    assert "verbs" in verbs_card["tags"]


async def test_reuses_an_existing_deck_by_name_and_ignores_priority_on_reuse(auth_client):
    existing = (
        await auth_client.post(
            "/api/decks", json={"name": "Reused", "default_priority": 33}
        )
    ).json()

    resp = await auth_client.post(
        "/api/import/json",
        json={
            "deck": "Reused",
            "priority": 99,
            "notes": [{"front": "q", "back": "a"}],
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["deck_created"] is False
    assert body["deck_id"] == existing["id"]

    decks = (await auth_client.get("/api/decks")).json()
    deck = next(d for d in decks if d["id"] == existing["id"])
    assert deck["default_priority"] == 33, "priority must not change on an existing deck"


async def test_cloze_notes_use_the_cloze_note_type(auth_client):
    resp = await auth_client.post(
        "/api/import/json",
        json={
            "deck": "Biology",
            "notes": [
                {
                    "kind": "cloze",
                    "cloze_text": "The {{c1::mitochondrion}} is the powerhouse.",
                    "back": "cell biology",
                }
            ],
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["notes_created"] == 1
    assert body["cards_created"] == 1

    cards = (await auth_client.get(f"/api/cards?deck_id={body['deck_id']}")).json()
    # Cloze rendering redacts the deletion on the front (tested elsewhere) —
    # here we only need to confirm it landed as a cloze card, not a basic one.
    assert cards[0]["template_slot"] == "c1"
    assert "mitochondrion" in cards[0]["back"]


async def test_a_malformed_row_is_skipped_and_reported_not_fatal(auth_client):
    """A bad row in a hand-edited file shouldn't cost the other rows."""
    resp = await auth_client.post(
        "/api/import/json",
        json={
            "deck": "Mixed",
            "notes": [
                {"front": "good one", "back": "yes"},
                {"front": "", "back": "missing front"},
                {"kind": "cloze", "cloze_text": "  "},
                {"front": "also good", "back": "yes"},
            ],
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["notes_created"] == 2
    assert len(body["warnings"]) == 2

    cards = (await auth_client.get(f"/api/cards?deck_id={body['deck_id']}")).json()
    assert {c["front"] for c in cards} == {"good one", "also good"}


async def test_appears_in_the_knowledge_tree_like_any_other_deck(auth_client):
    resp = await auth_client.post(
        "/api/import/json",
        json={"deck": "Tree Check", "notes": [{"front": "q", "back": "a"}]},
    )
    deck_id = resp.json()["deck_id"]

    tree = (await auth_client.get("/api/tree")).json()["nodes"]
    node = next((n for n in tree if n.get("deck_id") == deck_id), None)
    assert node is not None
    assert node["card_count"] == 1


async def test_rejects_an_empty_notes_list(auth_client):
    resp = await auth_client.post(
        "/api/import/json", json={"deck": "Empty", "notes": []}
    )
    assert resp.status_code == 422


async def test_shows_up_in_import_history(auth_client):
    await auth_client.post(
        "/api/import/json",
        json={"deck": "Historied", "notes": [{"front": "q", "back": "a"}]},
    )
    history = (await auth_client.get("/api/import/history")).json()
    assert any("Historied" in h["filename"] for h in history)


async def test_accepts_a_bare_array_with_deck_name_as_a_query_param(auth_client):
    """The common shape for a scripted/LLM flashcard export: no envelope."""
    resp = await auth_client.post(
        "/api/import/json?deck=Bare%20Array",
        json=[{"front": "q1", "back": "a1"}, {"front": "q2", "back": "a2"}],
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["deck_created"] is True
    assert body["notes_created"] == 2


async def test_bare_array_without_a_deck_name_is_a_clean_400(auth_client):
    resp = await auth_client.post(
        "/api/import/json", json=[{"front": "q", "back": "a"}]
    )
    assert resp.status_code == 400
    assert "deck name" in resp.json()["detail"]


async def test_accepts_the_card_type_question_answer_vocabulary(auth_client):
    """Real-world shape from an LLM flashcard generator: card_type/question/
    answer instead of kind/front/back, plus an unrelated extra field."""
    resp = await auth_client.post(
        "/api/import/json?deck=Economics",
        json=[
            {
                "card_type": "qa",
                "question": "What is a Balance Sheet Recession?",
                "answer": "A recession following a bursting credit bubble.",
                "tags": ["balance-sheet-recession"],
                "estimated_difficulty": 0.2,
            },
            {
                "card_type": "cloze",
                "question": "Monetary policy tightens, causing the {{c1::bubble to collapse}}.",
                "answer": "bubble to collapse",
                "estimated_difficulty": 0.4,
            },
        ],
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["notes_created"] == 2
    assert body["warnings"] == []

    cards = (await auth_client.get(f"/api/cards?deck_id={body['deck_id']}")).json()
    assert any(c["template_slot"] == "default" and "Balance Sheet" in c["front"] for c in cards)
    assert any(c["template_slot"] == "c1" for c in cards)


async def test_explicit_kind_front_back_takes_priority_over_aliases(auth_client):
    """A row that already uses our vocabulary must not be overwritten by an
    incidentally-present card_type/question/answer key."""
    resp = await auth_client.post(
        "/api/import/json?deck=Explicit",
        json=[
            {
                "kind": "basic",
                "front": "real front",
                "back": "real back",
                "card_type": "cloze",
                "question": "ignored",
                "answer": "ignored too",
            }
        ],
    )
    assert resp.status_code == 201, resp.text
    cards = (await auth_client.get(f"/api/cards?deck_id={resp.json()['deck_id']}")).json()
    assert cards[0]["front"] == "real front"
    assert cards[0]["template_slot"] == "default"


async def test_a_quote_creates_a_citation_that_powers_learn_and_practice(auth_client):
    """A JSON import can hand-supply what a document upload would otherwise
    generate: a citation, so Learn & Practice has something to teach from."""
    resp = await auth_client.post(
        "/api/import/json",
        json={
            "deck": "Cited",
            "notes": [
                {
                    "front": "What replaces profit maximization after a bubble bursts?",
                    "back": "Debt minimization.",
                    "quote": (
                        "During such a recession the private sector shifts from profit "
                        "maximization to debt minimization."
                    ),
                    "locator": "The Behavioral Shift",
                    "source_title": "Balance Sheet Recessions",
                }
            ],
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["citations_created"] == 1

    cards = (await auth_client.get(f"/api/cards?deck_id={body['deck_id']}")).json()
    card_id = cards[0]["id"]

    lesson = (await auth_client.get(f"/api/review/{card_id}/lesson")).json()
    assert lesson["available"] is True
    assert len(lesson["citations"]) == 1
    citation = lesson["citations"][0]
    assert citation["quote_verified"] is True
    assert citation["locator"] == "The Behavioral Shift"
    assert citation["source_title"] == "Balance Sheet Recessions"
    assert "debt minimization" in citation["quote"]


async def test_no_quote_means_no_citation_and_no_learn_and_practice(auth_client):
    resp = await auth_client.post(
        "/api/import/json",
        json={"deck": "Uncited", "notes": [{"front": "q", "back": "a"}]},
    )
    body = resp.json()
    assert body["citations_created"] == 0

    cards = (await auth_client.get(f"/api/cards?deck_id={body['deck_id']}")).json()
    lesson = (await auth_client.get(f"/api/review/{cards[0]['id']}/lesson")).json()
    assert lesson["available"] is False
    assert lesson["reason"] == "no_citations"


async def test_a_blank_quote_is_treated_as_no_citation(auth_client):
    resp = await auth_client.post(
        "/api/import/json",
        json={"deck": "Blank Quote", "notes": [{"front": "q", "back": "a", "quote": "   "}]},
    )
    assert resp.json()["citations_created"] == 0


async def test_json_import_is_tenant_isolated(client):
    import uuid

    async def register() -> str:
        email = f"json-import-{uuid.uuid4().hex[:8]}@example.com"
        resp = await client.post(
            "/api/auth/register", json={"email": email, "password": "hunter2hunter2"}
        )
        return resp.json()["access_token"]

    alice, bob = await register(), await register()

    client.headers["Authorization"] = f"Bearer {alice}"
    await client.post(
        "/api/import/json",
        json={"deck": "Alice's deck", "notes": [{"front": "q", "back": "a"}]},
    )

    client.headers["Authorization"] = f"Bearer {bob}"
    decks = (await client.get("/api/decks")).json()
    assert not any(d["name"] == "Alice's deck" for d in decks)


async def test_code_card_with_starter_tests_and_priority(auth_client):
    """Importing a code card with starter_tests saves starter_tests and sets math_code profile."""
    resp = await auth_client.post(
        "/api/import/json",
        json={
            "deck": "CPSC 210 Practice",
            "notes": [
                {
                    "title": "Unwrap Result with assertOk",
                    "front": "Write unwrapResult function and test it",
                    "back": "export function unwrapResult(r) { return assertOk(r); }",
                    "starter_code": "export function unwrapResult(r) {\n  // TODO\n}",
                    "starter_tests": "test('sample', () => { assertOk({ ok: true, value: 42 }); });",
                    "test_cases": [{"input": {"r": {"ok": True, "value": 42}}, "expected": 42}],
                    "priority": 85,
                    "difficulty": "Medium",
                    "category": "Testing",
                    "tags": ["Result", "cpsc210"],
                }
            ],
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["notes_created"] == 1
    assert body["cards_created"] == 1

    deck_id = body["deck_id"]
    cards = (await auth_client.get(f"/api/cards?deck_id={deck_id}")).json()
    assert len(cards) == 1
    card = cards[0]
    assert card["priority"] == 85
    assert "code" in card["tags"]
    assert "Medium" in card["tags"]
    assert "Result" in card["tags"]

    # Verify that the card's note holds starter_tests in field_values
    note_resp = await auth_client.get(f"/api/notes/{card['note_id']}")
    assert note_resp.status_code == 200
    fv = note_resp.json()["field_values"]
    assert fv["starter_code"] == "export function unwrapResult(r) {\n  // TODO\n}"
    assert fv["starter_tests"] == "test('sample', () => { assertOk({ ok: true, value: 42 }); });"
    assert fv["difficulty"] == "Medium"
    assert fv["category"] == "Testing"


async def test_import_cpsc210_mt2_supplemental_deck(auth_client):
    import json
    from pathlib import Path
    deck_path = Path(r"C:\Users\micha\OneDrive\Documents\UBC BCS ICS\CPSC 210\Midterm 2\Cards\cpsc210_mt2_supplemental.json")
    if not deck_path.exists():
        return

    with open(deck_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    resp = await auth_client.post("/api/import/json", json=payload)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["notes_created"] == 22
    assert body["cards_created"] == 22
    assert body["warnings"] == []


