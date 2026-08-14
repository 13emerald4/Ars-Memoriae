"""Velocity (§ Velocity dashboard): mastered concepts per active hour, read
off the Time Bank's own ledger rather than wall-clock elapsed time — the
same "efficiency, not seat time" idea the Time Bank itself is built on."""

from __future__ import annotations


async def _deck(client, name: str = "Velocity deck") -> str:
    resp = await client.post("/api/decks", json={"name": name})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _card(client, deck_id: str, front: str) -> str:
    resp = await client.post(
        "/api/notes",
        json={
            "deck_id": deck_id,
            "template_kind": "basic",
            "field_values": {"Front": front, "Back": "a"},
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["cards"][0]["id"]


async def _confirm(client, card_id: str, grade: str = "good") -> dict:
    resp = await client.post(
        f"/api/review/{card_id}/confirm", json={"final_grade": grade, "overridden": False}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _stats(client) -> dict:
    resp = await client.get("/api/stats")
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestVelocity:
    async def test_no_timed_blocks_means_no_divide_by_zero(self, auth_client):
        deck_id = await _deck(auth_client)
        card = await _card(auth_client, deck_id, "q")
        # "easy" on a new card graduates it straight into FSRS's review state.
        await _confirm(auth_client, card, "easy")

        velocity = (await _stats(auth_client))["velocity"]
        # The card was mastered, but outside any timed block — so it counts
        # toward progress and not toward the rate, whose denominator only
        # measures block time. See TestVelocityRate in test_review_regressions.
        assert velocity["mastered_total"] == 1
        assert velocity["mastered"] == 0
        assert velocity["active_hours"] == 0
        assert velocity["per_hour"] == 0.0

    async def test_mastering_inside_a_finished_block_computes_a_rate(self, auth_client):
        deck_id = await _deck(auth_client)
        cards = [await _card(auth_client, deck_id, f"q{i}") for i in range(3)]

        session = (
            await auth_client.post(
                "/api/sessions/start", json={"planned_minutes": 30, "goal_cards": 0}
            )
        ).json()
        for card in cards:
            await _confirm(auth_client, card, "easy")
        # 6 of the 30 planned minutes spent -> 24 banked, 6 active.
        finished = (
            await auth_client.post(
                f"/api/sessions/{session['id']}/finish", json={"remaining_seconds": 24 * 60}
            )
        ).json()
        assert finished["active_seconds"] == 6 * 60

        velocity = (await _stats(auth_client))["velocity"]
        assert velocity["mastered"] == 3
        assert velocity["active_hours"] == round(6 / 60, 2)
        assert velocity["per_hour"] == round(3 / (6 / 60), 2)

    async def test_a_review_that_does_not_graduate_the_card_does_not_count(self, auth_client):
        deck_id = await _deck(auth_client)
        card = await _card(auth_client, deck_id, "q")
        await _confirm(auth_client, card, "good")  # -> "learning", not "review"
        # (No timed block here either, so mastered_total is the honest check.)

        velocity = (await _stats(auth_client))["velocity"]
        assert velocity["mastered"] == 0
        assert velocity["mastered_total"] == 0
