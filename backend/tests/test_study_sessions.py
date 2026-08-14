"""Timed study sessions and the Time Bank.

The mechanic only means anything if the number can't be gamed: work is
counted from the review log rather than asserted by the client, and time is
banked only by *finishing* a target, never by quitting early.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


async def _deck(client, name: str = "Bank deck") -> str:
    resp = await client.post("/api/decks", json={"name": name})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _card(client, deck_id: str, front: str = "q", back: str = "a") -> str:
    note_types = (await client.get("/api/note-types")).json()
    basic = next(nt for nt in note_types if nt["template_kind"] == "basic")
    resp = await client.post(
        "/api/notes",
        json={
            "deck_id": deck_id,
            "note_type_id": basic["id"],
            "field_values": {"Front": front, "Back": back},
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["cards"][0]["id"]


async def _review(client, card_id: str) -> None:
    resp = await client.post(
        f"/api/review/{card_id}/confirm", json={"final_grade": "good", "overridden": False}
    )
    assert resp.status_code == 200, resp.text


async def _start(client, **kw) -> dict:
    body = {"planned_minutes": 30, "goal_cards": 0, **kw}
    resp = await client.post("/api/sessions/start", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _finish(client, session_id: str, remaining_seconds: int) -> dict:
    resp = await client.post(
        f"/api/sessions/{session_id}/finish", json={"remaining_seconds": remaining_seconds}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestBankMath:
    async def test_hitting_the_target_early_banks_the_unspent_time(self, auth_client):
        deck_id = await _deck(auth_client)
        card = await _card(auth_client, deck_id)

        session = await _start(auth_client, planned_minutes=30, goal_cards=1)
        await _review(auth_client, card)
        # 10 minutes left on a 30-minute block.
        done = await _finish(auth_client, session["id"], remaining_seconds=600)

        assert done["cards_reviewed"] == 1
        assert done["goal_met"] is True
        assert done["active_seconds"] == 1200
        assert done["banked_seconds"] == 600

    async def test_missing_the_target_banks_nothing(self, auth_client):
        """Otherwise "banked time" would just be a synonym for quitting
        early — the incentive this feature exists to avoid."""
        deck_id = await _deck(auth_client)
        await _card(auth_client, deck_id)

        session = await _start(auth_client, planned_minutes=30, goal_cards=5)
        done = await _finish(auth_client, session["id"], remaining_seconds=1500)

        assert done["cards_reviewed"] == 0
        assert done["goal_met"] is False
        assert done["banked_seconds"] == 0

    async def test_running_the_clock_out_banks_nothing_even_when_the_goal_is_met(
        self, auth_client
    ):
        deck_id = await _deck(auth_client)
        card = await _card(auth_client, deck_id)

        session = await _start(auth_client, planned_minutes=30, goal_cards=1)
        await _review(auth_client, card)
        done = await _finish(auth_client, session["id"], remaining_seconds=0)

        assert done["goal_met"] is True
        assert done["active_seconds"] == 1800
        assert done["banked_seconds"] == 0

    async def test_a_session_with_no_card_target_can_never_bank(self, auth_client):
        """goal_cards=0 is a plain timed block: there is no goal to have met,
        so there is nothing to have earned."""
        session = await _start(auth_client, planned_minutes=30, goal_cards=0)
        done = await _finish(auth_client, session["id"], remaining_seconds=900)
        assert done["goal_met"] is False
        assert done["banked_seconds"] == 0

    async def test_banking_may_exceed_elapsed_wall_clock_time(self, auth_client):
        """Finishing fast is the whole point: a 30-minute block whose target
        you hit in seconds banks nearly the full 30, even though barely any
        wall-clock time has passed."""
        deck_id = await _deck(auth_client)
        card = await _card(auth_client, deck_id)
        session = await _start(auth_client, planned_minutes=30, goal_cards=1)
        await _review(auth_client, card)

        done = await _finish(auth_client, session["id"], remaining_seconds=1750)
        assert done["active_seconds"] == 50
        assert done["banked_seconds"] == 1750

    async def test_absurd_remaining_is_clamped_to_the_planned_duration(self, auth_client):
        deck_id = await _deck(auth_client)
        card = await _card(auth_client, deck_id)
        session = await _start(auth_client, planned_minutes=10, goal_cards=1)
        await _review(auth_client, card)

        done = await _finish(auth_client, session["id"], remaining_seconds=999_999)
        assert done["active_seconds"] == 0
        assert done["banked_seconds"] == 600  # never more than the block itself


class TestWorkIsCountedServerSide:
    async def test_only_reviews_inside_the_window_count(self, auth_client):
        deck_id = await _deck(auth_client)
        before = await _card(auth_client, deck_id, "before", "a")
        during = await _card(auth_client, deck_id, "during", "a")

        await _review(auth_client, before)  # before the session opens
        session = await _start(auth_client, planned_minutes=30, goal_cards=1)
        await _review(auth_client, during)
        done = await _finish(auth_client, session["id"], remaining_seconds=600)

        assert done["cards_reviewed"] == 1, "the earlier review must not count"

    async def test_reading_extracts_do_not_count_toward_a_card_target(self, auth_client):
        """The target is expressed in cards; an extract produces no review log
        row and shouldn't quietly satisfy it."""
        await auth_client.post(
            "/api/sources",
            json={"title": "Reading", "raw_text": "Paragraph one.\n\nParagraph two here."},
        )
        extracts = (await auth_client.get("/api/extracts")).json()
        session = await _start(auth_client, planned_minutes=30, goal_cards=1)
        if extracts:
            await auth_client.post(
                f"/api/extracts/{extracts[0]['id']}/schedule", json={"days": 3}
            )
        done = await _finish(auth_client, session["id"], remaining_seconds=600)

        assert done["cards_reviewed"] == 0
        assert done["banked_seconds"] == 0


class TestSessionLifecycle:
    async def test_only_one_session_is_open_at_a_time(self, auth_client):
        """A forgotten session would otherwise keep accruing wall-clock time
        and poison everything derived from it."""
        first = await _start(auth_client, planned_minutes=30)
        second = await _start(auth_client, planned_minutes=45)
        assert first["id"] != second["id"]

        bank = (await auth_client.get("/api/sessions/bank")).json()
        assert bank["current"]["id"] == second["id"]
        assert any(s["id"] == first["id"] for s in bank["recent"])

    async def test_finishing_twice_does_not_bank_twice(self, auth_client):
        """The timer firing and the user clicking End is a real double
        submit, not a hypothetical one."""
        deck_id = await _deck(auth_client)
        card = await _card(auth_client, deck_id)
        session = await _start(auth_client, planned_minutes=30, goal_cards=1)
        await _review(auth_client, card)

        first = await _finish(auth_client, session["id"], remaining_seconds=600)
        second = await _finish(auth_client, session["id"], remaining_seconds=0)
        assert second == first

        bank = (await auth_client.get("/api/sessions/bank")).json()
        assert bank["total_seconds"] == first["banked_seconds"]

    async def test_the_focus_goal_is_kept(self, auth_client):
        session = await _start(
            auth_client, planned_minutes=20, focus_goal="Master the Krebs cycle"
        )
        assert session["focus_goal"] == "Master the Krebs cycle"
        bank = (await auth_client.get("/api/sessions/bank")).json()
        assert bank["current"]["focus_goal"] == "Master the Krebs cycle"

    async def test_a_blank_focus_goal_is_stored_as_none(self, auth_client):
        session = await _start(auth_client, planned_minutes=20, focus_goal="   ")
        assert session["focus_goal"] is None

    async def test_finishing_an_unknown_session_is_404(self, auth_client):
        resp = await auth_client.post(
            "/api/sessions/00000000-0000-0000-0000-000000000000/finish",
            json={"remaining_seconds": 0},
        )
        assert resp.status_code == 404

    async def test_a_session_left_open_overnight_settles_itself(self, auth_client):
        """Rather than showing a 14-hour countdown the next morning."""
        import uuid as _uuid

        from app.db import SessionLocal
        from app.models import StudySession

        opened = await _start(auth_client, planned_minutes=30, goal_cards=1)

        async with SessionLocal() as db:
            row = await db.get(StudySession, _uuid.UUID(opened["id"]))
            row.started_at = datetime.now(UTC) - timedelta(hours=20)
            await db.commit()

        bank = (await auth_client.get("/api/sessions/bank")).json()
        assert bank["current"] is None
        stale = next(s for s in bank["recent"] if s["id"] == opened["id"])
        assert stale["ended_at"] is not None
        assert stale["banked_seconds"] == 0


class TestLiveProgress:
    """An open session reports progress toward its target, so the number you
    committed to is one you can watch yourself approach."""

    async def test_open_session_reports_cards_reviewed_so_far(self, auth_client):
        deck_id = await _deck(auth_client)
        first = await _card(auth_client, deck_id, "q1", "a")
        await _card(auth_client, deck_id, "q2", "a")

        await _start(auth_client, planned_minutes=30, goal_cards=2)
        bank = (await auth_client.get("/api/sessions/bank")).json()
        assert bank["current"]["cards_reviewed"] == 0
        assert bank["current"]["goal_met"] is False

        await _review(auth_client, first)
        bank = (await auth_client.get("/api/sessions/bank")).json()
        assert bank["current"]["cards_reviewed"] == 1, "stored value alone would stay 0"
        assert bank["current"]["goal_met"] is False

    async def test_open_session_flags_the_target_as_met(self, auth_client):
        deck_id = await _deck(auth_client)
        card = await _card(auth_client, deck_id)

        await _start(auth_client, planned_minutes=30, goal_cards=1)
        await _review(auth_client, card)

        bank = (await auth_client.get("/api/sessions/bank")).json()
        assert bank["current"]["cards_reviewed"] == 1
        assert bank["current"]["goal_met"] is True

    async def test_progress_ignores_reviews_from_before_the_session(self, auth_client):
        deck_id = await _deck(auth_client)
        earlier = await _card(auth_client, deck_id, "earlier", "a")
        await _review(auth_client, earlier)

        await _start(auth_client, planned_minutes=30, goal_cards=1)
        bank = (await auth_client.get("/api/sessions/bank")).json()
        assert bank["current"]["cards_reviewed"] == 0

    async def test_a_targetless_session_is_never_reported_as_met(self, auth_client):
        deck_id = await _deck(auth_client)
        card = await _card(auth_client, deck_id)
        await _start(auth_client, planned_minutes=30, goal_cards=0)
        await _review(auth_client, card)

        bank = (await auth_client.get("/api/sessions/bank")).json()
        assert bank["current"]["cards_reviewed"] == 1
        assert bank["current"]["goal_met"] is False


class TestBankTotals:
    async def test_totals_accumulate_across_sessions(self, auth_client):
        deck_id = await _deck(auth_client)
        for i in range(2):
            card = await _card(auth_client, deck_id, f"q{i}", "a")
            session = await _start(auth_client, planned_minutes=10, goal_cards=1)
            await _review(auth_client, card)
            await _finish(auth_client, session["id"], remaining_seconds=300)

        bank = (await auth_client.get("/api/sessions/bank")).json()
        # Each 10-minute block finished with 5 minutes left: 300s banked twice.
        assert bank["total_seconds"] == 600
        assert bank["today_seconds"] == 600
        assert bank["week_seconds"] == 600
        assert bank["sessions_today"] == 2
        assert bank["goals_met_today"] == 2

    async def test_totals_bucket_correctly_across_day_and_week_boundaries(self, auth_client):
        """started_at is stored naive on SQLite but compared against aware
        datetimes — the same shape as the bug that made GET /api/extracts
        raise. Placing sessions either side of each boundary pins it."""
        import uuid as _uuid

        from sqlalchemy import select

        from app.db import SessionLocal
        from app.models import StudySession, User

        me = (await auth_client.get("/api/me")).json()
        now = datetime.now(UTC)
        placements = [
            (now - timedelta(hours=2), 100),  # today
            (now - timedelta(hours=30), 200),  # yesterday, still this week
            (now - timedelta(days=3), 400),  # this week
            (now - timedelta(days=10), 800),  # older than a week
        ]

        async with SessionLocal() as db:
            user = await db.scalar(select(User).where(User.id == _uuid.UUID(me["id"])))
            for started, banked in placements:
                db.add(
                    StudySession(
                        user_id=user.id,
                        started_at=started,
                        ended_at=started + timedelta(minutes=5),
                        planned_seconds=1800,
                        active_seconds=1800 - banked,
                        goal_cards=1,
                        cards_reviewed=1,
                        banked_seconds=banked,
                    )
                )
            await db.commit()

        bank = (await auth_client.get("/api/sessions/bank")).json()
        assert bank["today_seconds"] == 100
        assert bank["week_seconds"] == 700
        assert bank["total_seconds"] == 1500
        assert bank["sessions_today"] == 1

    async def test_an_empty_bank_is_zeroes_not_an_error(self, auth_client):
        bank = (await auth_client.get("/api/sessions/bank")).json()
        assert bank["total_seconds"] == 0
        assert bank["current"] is None
        assert bank["recent"] == []


class TestExport:
    async def test_sessions_are_in_the_full_export(self, auth_client):
        """Data ownership is a first-class feature here — the bank is
        longitudinal data and has to come with you."""
        deck_id = await _deck(auth_client)
        card = await _card(auth_client, deck_id)
        session = await _start(
            auth_client, planned_minutes=15, goal_cards=1, focus_goal="Exported goal"
        )
        await _review(auth_client, card)
        await _finish(auth_client, session["id"], remaining_seconds=300)

        data = (await auth_client.get("/api/export")).json()
        assert "study_sessions" in data
        row = next(s for s in data["study_sessions"] if s["id"] == session["id"])
        assert row["focus_goal"] == "Exported goal"
        assert row["banked_seconds"] > 0


class TestTenantIsolation:
    async def test_another_users_session_cannot_be_finished(self, client):
        import uuid

        async def register() -> str:
            email = f"bank-{uuid.uuid4().hex[:8]}@example.com"
            resp = await client.post(
                "/api/auth/register", json={"email": email, "password": "hunter2hunter2"}
            )
            return resp.json()["access_token"]

        alice, bob = await register(), await register()

        client.headers["Authorization"] = f"Bearer {alice}"
        session = await _start(client, planned_minutes=30)

        client.headers["Authorization"] = f"Bearer {bob}"
        resp = await client.post(
            f"/api/sessions/{session['id']}/finish", json={"remaining_seconds": 0}
        )
        assert resp.status_code == 404

        bank = (await client.get("/api/sessions/bank")).json()
        assert bank["current"] is None
        assert bank["total_seconds"] == 0
