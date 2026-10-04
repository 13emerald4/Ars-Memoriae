"""Phase-1 acceptance check (§14.1): create a deck, add cards, review them
with FSRS scheduling, and confirm the guardrails and queue behave."""

from __future__ import annotations

import pytest


async def _deck(client, name="Test Deck", priority=50):
    resp = await client.post("/api/decks", json={"name": name, "default_priority": priority})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _note(client, deck_id, front, back, **kw):
    resp = await client.post(
        "/api/notes",
        json={"deck_id": deck_id, "template_kind": "basic",
              "field_values": {"Front": front, "Back": back}, **kw},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_register_seeds_starter_content(auth_client):
    decks = (await auth_client.get("/api/decks")).json()
    assert [d["name"] for d in decks] == ["Default"]

    note_types = (await auth_client.get("/api/note-types")).json()
    kinds = {nt["name"]: nt["grading_profile"] for nt in note_types}
    assert kinds == {
        "Basic": "short_answer",
        "Cloze": "short_answer",
        "Conceptual": "conceptual",
        "Math / Code": "math_code",
    }


async def test_basic_note_makes_one_card(auth_client):
    deck_id = await _deck(auth_client, "Basic deck")
    note = await _note(auth_client, deck_id, "Capital of France?", "Paris")
    assert len(note["cards"]) == 1
    card = note["cards"][0]
    assert card["front"] == "Capital of France?"
    assert card["back"] == "Paris"
    assert card["state"] == "new"


async def test_cloze_note_makes_one_card_per_deletion(auth_client):
    deck_id = await _deck(auth_client, "Cloze deck")
    resp = await auth_client.post(
        "/api/notes",
        json={
            "deck_id": deck_id,
            "template_kind": "cloze",
            "field_values": {
                "Text": "The {{c1::mitochondrion}} is the {{c2::powerhouse}} of the cell.",
                "Extra": "Biology 101",
            },
        },
    )
    assert resp.status_code == 201, resp.text
    cards = resp.json()["cards"]
    assert sorted(c["template_slot"] for c in cards) == ["c1", "c2"]

    c1 = next(c for c in cards if c["template_slot"] == "c1")
    # The tested deletion is blanked; the *other* deletion stays as context.
    assert "[…]" in c1["front"]
    assert "powerhouse" in c1["front"]
    assert c1["back"].startswith("mitochondrion")


async def test_full_review_cycle_advances_fsrs_state(auth_client):
    deck_id = await _deck(auth_client, "Review deck")
    note = await _note(auth_client, deck_id, "2 + 2?", "4")
    card_id = note["cards"][0]["id"]

    # No API key/consent -> the §4.3 manual fallback, not an error.
    answer = await auth_client.post(
        f"/api/review/{card_id}/answer", json={"typed_answer": "4", "latency_ms": 900}
    )
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["degraded_to_manual"] is True
    assert body["degraded_reason"] == "consent_not_given"
    assert body["reference_answer"] == "4"

    confirm = await auth_client.post(
        f"/api/review/{card_id}/confirm",
        json={"final_grade": "good", "overridden": False, "typed_answer": "4", "latency_ms": 900},
    )
    assert confirm.status_code == 200, confirm.text
    result = confirm.json()
    assert result["state"] == "learning"
    assert result["interval_days"] > 0

    # Second "good" graduates the card out of learning into review.
    confirm2 = await auth_client.post(
        f"/api/review/{card_id}/confirm", json={"final_grade": "good", "overridden": False}
    )
    assert confirm2.json()["state"] == "review"
    assert confirm2.json()["new_stability"] > 0
    assert confirm2.json()["interval_days"] >= 1


async def test_lapse_counter_only_counts_review_state_failures(auth_client):
    deck_id = await _deck(auth_client, "Lapse deck")
    note = await _note(auth_client, deck_id, "Q", "A")
    card_id = note["cards"][0]["id"]

    async def grade(g):
        r = await auth_client.post(
            f"/api/review/{card_id}/confirm", json={"final_grade": g, "overridden": False}
        )
        assert r.status_code == 200, r.text
        return r.json()

    # Failing while still in learning is not a lapse.
    assert (await grade("again"))["lapse_count"] == 0
    await grade("good")
    assert (await grade("good"))["state"] == "review"
    # Failing from the review state is.
    lapsed = await grade("again")
    assert lapsed["lapse_count"] == 1
    assert lapsed["state"] == "relearning"


async def test_queue_returns_items_and_respects_new_limit(auth_client):
    deck_id = await _deck(auth_client, "Queue deck")
    for i in range(6):
        await _note(auth_client, deck_id, f"Q{i}", f"A{i}")

    await auth_client.patch("/api/me", json={"daily_new_limit": 3})
    session = (await auth_client.get("/api/queue/session")).json()
    assert session["counts"]["new"] == 3
    assert session["caps"]["new_remaining"] == 3

    nxt = await auth_client.get("/api/queue/next")
    assert nxt.status_code == 200
    assert nxt.json()["kind"] == "card"


async def test_queue_item_carries_the_reference_answer(auth_client):
    """The whole point of §4.3's "leaving LLM grading off is a full path, not
    a degraded one" promise: with no consent/API key, "show answer" has
    nothing to fetch it from except the queue item itself."""
    deck_id = await _deck(auth_client, "Reveal deck")
    await _note(auth_client, deck_id, "2 + 2?", "4")

    nxt = await auth_client.get("/api/queue/next")
    assert nxt.status_code == 200, nxt.text
    body = nxt.json()
    assert body["kind"] == "card"
    assert body["back"] == "4"


async def test_queue_orders_by_priority(auth_client):
    deck_id = await _deck(auth_client, "Priority deck")
    await _note(auth_client, deck_id, "low priority", "x", priority=10)
    await _note(auth_client, deck_id, "high priority", "y", priority=95)

    await auth_client.patch("/api/me", json={"daily_new_limit": 50})
    session = (await auth_client.get("/api/queue/session")).json()
    fronts = [i["front"] for i in session["items"] if i["kind"] == "card"]
    assert fronts.index("high priority") < fronts.index("low priority")


async def test_empty_queue_returns_204(auth_client):
    await auth_client.patch("/api/me", json={"daily_new_limit": 0, "daily_review_limit": 0})
    resp = await auth_client.get("/api/queue/next")
    assert resp.status_code == 204


async def test_export_round_trips_everything(auth_client):
    deck_id = await _deck(auth_client, "Export deck")
    note = await _note(auth_client, deck_id, "exported?", "yes")
    await auth_client.post(
        f"/api/review/{note['cards'][0]['id']}/confirm",
        json={"final_grade": "good", "overridden": False},
    )

    resp = await auth_client.get("/api/export")
    assert resp.status_code == 200
    data = resp.json()
    assert data["export_version"] == 1
    assert any(d["name"] == "Export deck" for d in data["decks"])
    assert any(n["field_values"]["Front"] == "exported?" for n in data["notes"])
    assert len(data["review_logs"]) >= 1
    # The BYOK key must never leave the box.
    assert "google_api_key" not in str(data["user"])


async def test_priority_patch_endpoint(auth_client):
    deck_id = await _deck(auth_client, "Patch deck")
    note = await _note(auth_client, deck_id, "p", "q")
    card_id = note["cards"][0]["id"]

    resp = await auth_client.patch(
        "/api/priority", json={"target": "card", "id": card_id, "priority": 88}
    )
    assert resp.status_code == 200
    cards = (await auth_client.get(f"/api/cards?deck_id={deck_id}")).json()
    assert next(c for c in cards if c["id"] == card_id)["priority"] == 88


@pytest.mark.parametrize("bad", ["not-a-uuid", "00000000-0000-0000-0000-000000000000"])
async def test_unknown_card_ids_are_rejected(auth_client, bad):
    resp = await auth_client.post(
        f"/api/review/{bad}/confirm", json={"final_grade": "good", "overridden": False}
    )
    assert resp.status_code in (400, 404)


async def test_auth_is_required(client):
    client.headers.pop("Authorization", None)
    assert (await client.get("/api/decks")).status_code == 401


async def test_weakness_hint_and_progression_loop(auth_client):
    from app.core.security import new_answer_hash
    from app.db import get_db
    from app.models import Card, GradingCache
    import uuid

    deck_id = await _deck(auth_client, "Weakness Deck")
    note = await _note(auth_client, deck_id, "What happens with zero?", "Special handling needed")
    card_id = note["cards"][0]["id"]

    # 1. First review without previous weaknesses -> hint reports no past weaknesses
    hint_resp = await auth_client.post(f"/api/review/{card_id}/weakness-hint")
    assert hint_resp.status_code == 200
    assert hint_resp.json()["has_past_weaknesses"] is False

    # 2. Simulate graded answer with a captured weakness in GradingCache
    ans_text = "Just normal handling"
    h = new_answer_hash(ans_text)
    from app.main import app
    from app.db import SessionLocal

    async with SessionLocal() as db:
        db.add(
            GradingCache(
                card_id=uuid.UUID(card_id),
                answer_hash=h,
                response={
                    "score": 45,
                    "grade": "hard",
                    "confidence": 0.9,
                    "matched_points": [],
                    "missed_points": ["Special handling needed"],
                    "weaknesses": ["Omitted zero boundary condition"],
                    "improvements": [],
                    "persistent_weaknesses": [],
                    "reasoning": "Missing special condition for zero.",
                },
            )
        )
        await db.commit()

    # Confirm the review
    conf1 = await auth_client.post(
        f"/api/review/{card_id}/confirm",
        json={"final_grade": "hard", "overridden": False, "typed_answer": ans_text, "latency_ms": 1200},
    )
    assert conf1.status_code == 200

    # Verify Card now has the active weakness and history entry
    async with SessionLocal() as db:
        card = await db.get(Card, uuid.UUID(card_id))
        assert card.active_weaknesses == ["Omitted zero boundary condition"]
        assert len(card.weakness_history) == 1
        assert card.weakness_history[0]["weaknesses_identified"] == ["Omitted zero boundary condition"]

    # 3. Next time card is seen: request hint -> should report past weaknesses
    hint_resp2 = await auth_client.post(f"/api/review/{card_id}/weakness-hint")
    assert hint_resp2.status_code == 200
    h_data = hint_resp2.json()
    assert h_data["has_past_weaknesses"] is True
    assert "Omitted zero boundary condition" in h_data["active_weaknesses"]

    # 4. Next review: user provides improved answer that resolves the weakness
    ans_text_2 = "Special handling is required because zero cannot be divided"
    h2 = new_answer_hash(ans_text_2)
    async with SessionLocal() as db:
        db.add(
            GradingCache(
                card_id=uuid.UUID(card_id),
                answer_hash=h2,
                response={
                    "score": 95,
                    "grade": "easy",
                    "confidence": 0.95,
                    "matched_points": ["Special handling"],
                    "missed_points": [],
                    "weaknesses": [],
                    "improvements": ["Omitted zero boundary condition"],
                    "persistent_weaknesses": [],
                    "reasoning": "Flawless recall.",
                },
            )
        )
        await db.commit()

    conf2 = await auth_client.post(
        f"/api/review/{card_id}/confirm",
        json={"final_grade": "easy", "overridden": False, "typed_answer": ans_text_2, "latency_ms": 1000},
    )
    assert conf2.status_code == 200

    # Verify active weaknesses are now resolved!
    async with SessionLocal() as db:
        card = await db.get(Card, uuid.UUID(card_id))
        assert card.active_weaknesses == []
        assert len(card.weakness_history) == 2
        assert card.weakness_history[1]["improvements"] == ["Omitted zero boundary condition"]

