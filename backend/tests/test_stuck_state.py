"""Stuck-state detection: a real-time nudge when a sitting is going badly —
an accuracy slump or an answer that took far longer than usual — distinct
from leech flagging, which is a per-card verdict over the card's whole
history rather than a signal about the sitting happening right now."""

from __future__ import annotations


async def _deck(client, name: str = "Stuck deck") -> str:
    resp = await client.post("/api/decks", json={"name": name})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _card(client, deck_id: str, front: str, back: str = "a") -> str:
    resp = await client.post(
        "/api/notes",
        json={
            "deck_id": deck_id,
            "template_kind": "basic",
            "field_values": {"Front": front, "Back": back},
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["cards"][0]["id"]


async def _cards(client, n: int) -> list[str]:
    deck_id = await _deck(client)
    return [await _card(client, deck_id, f"q{i}") for i in range(n)]


async def _confirm(client, card_id: str, grade: str = "good", latency_ms: int | None = None) -> dict:
    body: dict = {"final_grade": grade, "overridden": False}
    if latency_ms is not None:
        body["latency_ms"] = latency_ms
    resp = await client.post(f"/api/review/{card_id}/confirm", json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestAccuracyTrigger:
    async def test_a_run_of_failures_triggers_on_the_fifth(self, auth_client):
        cards = await _cards(auth_client, 5)
        outcomes = [await _confirm(auth_client, c, "again") for c in cards]

        assert all(o["stuck_alert"] is None for o in outcomes[:4])
        assert outcomes[4]["stuck_alert"]["reason"] == "accuracy"

    async def test_it_does_not_realert_every_card_while_the_slump_continues(self, auth_client):
        cards = await _cards(auth_client, 6)
        outcomes = [await _confirm(auth_client, c, "again") for c in cards]

        assert outcomes[4]["stuck_alert"] is not None
        assert outcomes[5]["stuck_alert"] is None

    async def test_good_accuracy_never_triggers(self, auth_client):
        cards = await _cards(auth_client, 10)
        outcomes = [await _confirm(auth_client, c, "good") for c in cards]

        assert all(o["stuck_alert"] is None for o in outcomes)

    async def test_fewer_than_the_window_never_triggers(self, auth_client):
        cards = await _cards(auth_client, 4)
        outcomes = [await _confirm(auth_client, c, "again") for c in cards]

        assert all(o["stuck_alert"] is None for o in outcomes)


class TestLatencyTrigger:
    async def test_a_spike_over_baseline_triggers(self, auth_client):
        cards = await _cards(auth_client, 9)
        for c in cards[:8]:
            outcome = await _confirm(auth_client, c, "good", latency_ms=2000)
            assert outcome["stuck_alert"] is None

        spiked = await _confirm(auth_client, cards[8], "good", latency_ms=20_000)
        assert spiked["stuck_alert"]["reason"] == "latency"

    async def test_a_modest_variation_does_not_trigger(self, auth_client):
        cards = await _cards(auth_client, 9)
        for c in cards[:8]:
            await _confirm(auth_client, c, "good", latency_ms=2000)

        outcome = await _confirm(auth_client, cards[8], "good", latency_ms=2500)
        assert outcome["stuck_alert"] is None

    async def test_too_little_history_never_triggers(self, auth_client):
        cards = await _cards(auth_client, 3)
        for c in cards[:2]:
            await _confirm(auth_client, c, "good", latency_ms=1000)

        outcome = await _confirm(auth_client, cards[2], "good", latency_ms=50_000)
        assert outcome["stuck_alert"] is None
