"""Regressions for defects found reviewing the Alpha-inspired features.

Each test here failed before its fix. They are grouped by the property that
broke rather than by feature, because that's what has to keep holding.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.services.grading_service import leaks_reference_answer
from app.services.stuck_service import _check_latency


async def _deck(client, name: str) -> str:
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


async def _confirm(client, card_id: str, grade: str = "easy", **kw) -> dict:
    resp = await client.post(
        f"/api/review/{card_id}/confirm",
        json={"final_grade": grade, "overridden": False, **kw},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestSocraticLeakGuardShortAnswers:
    """The guard used to fire on *every* message for a card whose answer was
    under three characters: `_tokens` drops those, and an empty reference
    scores a perfect 1.0 overlap. The feature was dead on numeric cards."""

    @pytest.mark.parametrize("back", ["4", "42", "pH", "Paris", "the powerhouse of the cell"])
    def test_an_innocuous_hint_is_never_treated_as_a_leak(self, back):
        assert leaks_reference_answer(back, "What have you ruled out so far?") is False

    @pytest.mark.parametrize(
        ("back", "message"),
        [
            ("4", "The answer is 4."),
            ("42", "It comes out to 42."),
            ("pH", "You want the pH scale."),
            ("Paris", "The answer is Paris."),
            ("the powerhouse of the cell", "It is the powerhouse of the cell."),
            # Paraphrase, caught by overlap rather than containment.
            ("debt minimization", "Firms shift to minimization of debt after a crash."),
        ],
    )
    def test_an_actual_leak_is_still_caught(self, back, message):
        assert leaks_reference_answer(back, message) is True

    @pytest.mark.parametrize(
        ("back", "message"),
        [
            ("4", "Think about 40 years of history."),  # substring, not the answer
            ("pH", "Consider the phase change."),
        ],
    )
    def test_a_word_that_merely_contains_the_answer_is_not_a_leak(self, back, message):
        assert leaks_reference_answer(back, message) is False


class TestVelocityRate:
    """`per_hour` divided *every* graduation by timed-block hours only, so
    mastering cards outside a block inflated the rate without bound."""

    async def test_untimed_masteries_do_not_inflate_the_rate(self, auth_client):
        deck_id = await _deck(auth_client, "Untimed")
        for i in range(20):
            await _confirm(auth_client, await _card(auth_client, deck_id, f"untimed{i}"))

        session = (
            await auth_client.post(
                "/api/sessions/start", json={"planned_minutes": 30, "goal_cards": 0}
            )
        ).json()
        await auth_client.post(
            f"/api/sessions/{session['id']}/finish", json={"remaining_seconds": 25 * 60}
        )

        v = (await auth_client.get("/api/stats")).json()["velocity"]
        # 5 minutes of block time in which nothing was mastered.
        assert v["active_hours"] == pytest.approx(5 / 60, abs=0.01)
        assert v["mastered"] == 0
        assert v["per_hour"] == 0.0
        # The work still shows up as progress, just not as a rate.
        assert v["mastered_total"] == 20

    async def test_masteries_inside_a_block_do_count(self, auth_client):
        deck_id = await _deck(auth_client, "Timed")
        session = (
            await auth_client.post(
                "/api/sessions/start", json={"planned_minutes": 30, "goal_cards": 0}
            )
        ).json()
        for i in range(3):
            await _confirm(auth_client, await _card(auth_client, deck_id, f"timed{i}"))
        await auth_client.post(
            f"/api/sessions/{session['id']}/finish", json={"remaining_seconds": 24 * 60}
        )

        v = (await auth_client.get("/api/stats")).json()["velocity"]
        assert v["mastered"] == 3
        assert v["per_hour"] == pytest.approx(3 / (6 / 60), abs=0.01)

    async def test_a_relapsed_card_is_not_counted_as_two_concepts(self, auth_client):
        """review -> relearning -> review graduates twice; it is still one
        concept, and the tile says "concepts mastered"."""
        deck_id = await _deck(auth_client, "Relapse")
        card = await _card(auth_client, deck_id, "q")

        await _confirm(auth_client, card, "easy")  # new -> review (graduation 1)
        await _confirm(auth_client, card, "again")  # review -> relearning
        await _confirm(auth_client, card, "good")  # relearning -> review (graduation 2)

        v = (await auth_client.get("/api/stats")).json()["velocity"]
        assert v["mastered_total"] == 1


class TestLatencyBaselineIsRobust:
    """A mean baseline let one walked-away answer switch the detector off."""

    async def test_one_huge_outlier_does_not_suppress_a_real_spike(self, auth_client, monkeypatch):
        import uuid as _uuid

        from app.db import SessionLocal
        from app.models import Card, Deck, ReviewLog, User

        deck_id = await _deck(auth_client, "Latency")
        card_id = await _card(auth_client, deck_id, "q")

        # 12 normal answers plus a single 30-minute one the user walked away from.
        latencies = [2000] * 12 + [1_800_000]
        async with SessionLocal() as db:
            card = await db.get(Card, _uuid.UUID(card_id))
            deck = await db.get(Deck, card.deck_id)
            user = await db.get(User, deck.user_id)
            now = datetime.now(UTC)
            for i, ms in enumerate(latencies):
                db.add(
                    ReviewLog(
                        card_id=card.id,
                        reviewed_at=now - timedelta(seconds=len(latencies) - i),
                        final_grade="good",
                        latency_ms=ms,
                    )
                )
            await db.commit()

            # 20s is >3x the 2s median but well under 3x the poisoned mean.
            alert = await _check_latency(db, user, 20_000)

        assert alert is not None, "a genuine stall was suppressed by one outlier"
        assert alert.reason == "latency"


class TestExportCompleteness:
    """The dump is documented as complete; new columns kept being left out."""

    async def test_new_columns_reach_the_json_export(self, auth_client):
        deck_id = await _deck(auth_client, "Export")
        card = await _card(auth_client, deck_id, "q")
        await _confirm(auth_client, card, "easy")

        session = (
            await auth_client.post(
                "/api/sessions/start", json={"planned_minutes": 5, "goal_cards": 0}
            )
        ).json()
        await auth_client.post(
            f"/api/sessions/{session['id']}/finish", json={"remaining_seconds": 0}
        )
        await auth_client.post(
            f"/api/sessions/{session['id']}/reflect",
            json={"distraction": "phone", "next_time_plan": "airplane mode"},
        )

        dump = (await auth_client.get("/api/export")).json()

        log = next(r for r in dump["review_logs"] if r["card_id"] == card)
        assert log["graduated_to_review"] is True

        s = next(x for x in dump["study_sessions"] if x["id"] == session["id"])
        assert s["distraction"] == "phone"
        assert s["next_time_plan"] == "airplane mode"

    async def test_the_csv_carries_the_graduation_flag(self, auth_client):
        deck_id = await _deck(auth_client, "CSV")
        await _confirm(auth_client, await _card(auth_client, deck_id, "q"), "easy")

        resp = await auth_client.get("/api/export/review-logs.csv")
        assert resp.status_code == 200, resp.text
        lines = resp.text.strip().splitlines()
        assert lines[0].endswith("graduated_to_review")
        # Header plus at least one row, and the row has a value in that column.
        assert len(lines[-1].split(",")) == len(lines[0].split(","))


class TestStuckAccuracyIsScopedToNow:
    """The window had no time bound, so failures from days ago could combine
    with one today into a "you are stuck right now" alert."""

    async def test_stale_failures_do_not_trigger_a_fresh_alert(self, auth_client):
        import uuid as _uuid

        from app.db import SessionLocal
        from app.models import Card, ReviewLog

        deck_id = await _deck(auth_client, "Stale")
        old_card = await _card(auth_client, deck_id, "old")

        # Four failures, yesterday.
        async with SessionLocal() as db:
            card = await db.get(Card, _uuid.UUID(old_card))
            yesterday = datetime.now(UTC) - timedelta(days=1)
            for i in range(4):
                db.add(
                    ReviewLog(
                        card_id=card.id,
                        reviewed_at=yesterday + timedelta(seconds=i),
                        final_grade="again",
                    )
                )
            await db.commit()

        # One failure today must not complete a "slump" out of stale history.
        outcome = await _confirm(auth_client, await _card(auth_client, deck_id, "new"), "again")
        assert outcome["stuck_alert"] is None

    async def test_a_slump_within_the_hour_still_alerts(self, auth_client):
        deck_id = await _deck(auth_client, "Fresh")
        outcomes = [
            await _confirm(auth_client, await _card(auth_client, deck_id, f"q{i}"), "again")
            for i in range(5)
        ]
        assert outcomes[4]["stuck_alert"] is not None
        assert outcomes[4]["stuck_alert"]["reason"] == "accuracy"


class TestOwnershipStillHolds:
    async def test_export_never_leaks_another_users_sessions(self, auth_client, client):
        session = (
            await auth_client.post(
                "/api/sessions/start", json={"planned_minutes": 5, "goal_cards": 0}
            )
        ).json()
        await auth_client.post(
            f"/api/sessions/{session['id']}/finish", json={"remaining_seconds": 0}
        )

        stranger = await client.post(
            "/api/auth/register",
            json={"email": "stranger-export@example.com", "password": "hunter2hunter2"},
        )
        headers = {"Authorization": f"Bearer {stranger.json()['access_token']}"}
        dump = (await client.get("/api/export", headers=headers)).json()
        assert all(s["id"] != session["id"] for s in dump["study_sessions"])
