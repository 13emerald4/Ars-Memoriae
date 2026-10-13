"""FSRS wrapper, interval fuzzing, and the §3.1 review-load guardrails."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fsrs import Rating, State

from app.services.fsrs_service import FSRSService
from app.services.queue_service import review_allowance


def _fresh() -> object:
    return FSRSService.to_fsrs_card(
        state="new", stability=None, difficulty=None, step=None, due=None, last_review=None
    )


def test_new_card_maps_onto_the_libraries_learning_state():
    card = _fresh()
    assert card.state is State.Learning
    assert card.step == 0


def test_grades_produce_increasing_intervals():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    svc = FSRSService(fuzz=False)
    intervals = {}
    for grade in ("again", "hard", "good", "easy"):
        card = _fresh()
        # Graduate it into the review state first so intervals are comparable.
        card, _ = svc.schedule(card, Rating.Good, now)
        card, _ = svc.schedule(card, Rating.Good, now + timedelta(minutes=10))
        after, _ = svc.schedule(
            card, {"again": Rating.Again, "hard": Rating.Hard, "good": Rating.Good,
                   "easy": Rating.Easy}[grade], now + timedelta(days=3)
        )
        intervals[grade] = (after.due - (now + timedelta(days=3))).total_seconds()

    assert intervals["again"] < intervals["hard"] < intervals["good"] < intervals["easy"]


def test_state_round_trips_through_the_db_shape():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    svc = FSRSService(fuzz=False)
    card, state = svc.schedule(_fresh(), Rating.Good, now)

    rebuilt = FSRSService.to_fsrs_card(
        state=state["state"],
        stability=state["stability"],
        difficulty=state["difficulty"],
        step=state["step"],
        due=state["due"],
        last_review=state["last_review"],
    )
    assert rebuilt.state == card.state
    assert rebuilt.stability == card.stability
    assert rebuilt.difficulty == card.difficulty


def test_fuzzing_jitters_long_intervals_but_not_learning_steps():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    fuzzed = FSRSService(fuzz=True)
    exact = FSRSService(fuzz=False)

    # A sub-day learning step must stay exact or the learning ladder breaks.
    step_card, _ = fuzzed.schedule(_fresh(), Rating.Good, now)
    step_exact, _ = exact.schedule(_fresh(), Rating.Good, now)
    assert step_card.due == step_exact.due

    # A multi-day review interval should land near, but rarely exactly on, the
    # unfuzzed value — and always within the ±5% band.
    base = _fresh()
    base, _ = exact.schedule(base, Rating.Good, now)
    base, _ = exact.schedule(base, Rating.Good, now + timedelta(minutes=10))
    reviewed_at = now + timedelta(days=2)
    target, _ = exact.schedule(base, Rating.Good, reviewed_at)
    target_seconds = (target.due - reviewed_at).total_seconds()

    seen = set()
    for _ in range(40):
        got, _ = fuzzed.schedule(base, Rating.Good, reviewed_at)
        secs = (got.due - reviewed_at).total_seconds()
        assert abs(secs - target_seconds) <= target_seconds * 0.05 + 1
        seen.add(round(secs))
    assert len(seen) > 1, "fuzzing produced identical intervals every time"


class TestReviewAllowance:
    """§3.1: a backlog from missed days is spread, not dumped."""

    def test_no_backlog_shows_todays_cards(self):
        assert review_allowance(30, 0, 5, 200, 0) == 30

    def test_backlog_is_spread_over_the_configured_window(self):
        # 400 overdue + 20 due today, spread over 5 days -> 20 + 80, not 420.
        assert review_allowance(20, 400, 5, 200, 0) == 100

    def test_hard_cap_still_wins(self):
        assert review_allowance(20, 4000, 5, 200, 0) == 200

    def test_work_already_done_today_is_deducted(self):
        assert review_allowance(30, 0, 5, 200, 25) == 5

    def test_allowance_never_goes_negative(self):
        assert review_allowance(5, 0, 5, 200, 99) == 0


def test_retrievability_decays_with_time():
    svc = FSRSService(fuzz=False)
    now = datetime(2026, 1, 1, tzinfo=UTC)
    card, _ = svc.schedule(_fresh(), Rating.Good, now)
    card, _ = svc.schedule(card, Rating.Good, now + timedelta(minutes=10))

    fresh = svc.retrievability(card, now + timedelta(minutes=10))
    later = svc.retrievability(card, now + timedelta(days=30))
    assert fresh > later
    assert 0.0 <= later <= fresh <= 1.0


def test_optimizer_availability_reflects_torch_not_just_the_import():
    """py-fsrs always exports an Optimizer symbol; without the extra it is a
    stub that raises at construction. The probe must not be fooled by that."""
    import importlib.util

    expected = importlib.util.find_spec("torch") is not None
    assert FSRSService.optimizer_available() is expected

    if not expected:
        import pytest
        from fsrs import Optimizer

        with pytest.raises(ImportError):
            Optimizer([])


def test_schedule_is_invariant_to_response_duration():
    """FSRS schedule must not use response latency/duration as an input."""
    now = datetime(2026, 1, 1, tzinfo=UTC)
    svc = FSRSService(fuzz=False)

    card1, state1 = svc.schedule(_fresh(), Rating.Good, now, duration_ms=200)
    card2, state2 = svc.schedule(_fresh(), Rating.Good, now, duration_ms=45000)
    card3, state3 = svc.schedule(_fresh(), Rating.Good, now, duration_ms=None)

    assert card1.due == card2.due == card3.due
    assert card1.stability == card2.stability == card3.stability
    assert card1.difficulty == card2.difficulty == card3.difficulty
    assert state1 == state2 == state3


class TestStudyDay:
    """Daily caps and day buckets follow the user's local study day, which
    rolls over at 04:00 local — not at UTC midnight (4-5 pm in Vancouver)."""

    def test_day_start_is_local_four_am(self):
        from app.core.timeutil import day_key, day_start

        afternoon = datetime(2026, 10, 13, 23, 30, tzinfo=UTC)  # 16:30 PDT
        assert day_start(afternoon, "America/Vancouver") == datetime(2026, 10, 13, 11, tzinfo=UTC)
        assert day_key(afternoon, "America/Vancouver") == "2026-10-13"
        # 03:00 local still belongs to the previous study day.
        late_night = datetime(2026, 10, 14, 10, 0, tzinfo=UTC)
        assert day_key(late_night, "America/Vancouver") == "2026-10-13"
        # Unset or unknown zone falls back to UTC.
        assert day_start(afternoon, None) == datetime(2026, 10, 13, 4, tzinfo=UTC)
        assert day_start(afternoon, "Not/AZone") == day_start(afternoon, None)

    async def test_timezone_is_validated_and_stored(self, auth_client):
        bad = await auth_client.patch("/api/me", json={"timezone": "Mars/Olympus"})
        assert bad.status_code == 422
        ok = await auth_client.patch("/api/me", json={"timezone": "America/Vancouver"})
        assert ok.status_code == 200
        assert ok.json()["timezone"] == "America/Vancouver"

    async def test_new_card_cap_counts_the_local_study_day(self, auth_client):
        """A review logged before today's local 04:00 no longer counts
        against today's new-card cap."""
        import uuid

        from sqlalchemy import select

        from app.core.timeutil import day_start
        from app.db import SessionLocal
        from app.models import ReviewLog, User
        from app.services.queue_service import _counts_today

        me = (await auth_client.patch("/api/me", json={"timezone": "Asia/Tokyo"})).json()
        deck_id = (await auth_client.post("/api/decks", json={"name": "TZ"})).json()["id"]
        note = (
            await auth_client.post(
                "/api/notes",
                json={
                    "deck_id": deck_id,
                    "template_kind": "basic",
                    "field_values": {"Front": "q", "Back": "a"},
                },
            )
        ).json()
        card_id = uuid.UUID(note["cards"][0]["id"])
        now = datetime.now(UTC)
        boundary = day_start(now, "Asia/Tokyo")

        async with SessionLocal() as db:
            for at in (boundary - timedelta(minutes=1), boundary + timedelta(minutes=1)):
                db.add(
                    ReviewLog(
                        card_id=card_id, reviewed_at=at, final_grade="good", state_before="new"
                    )
                )
            await db.commit()
            user = await db.scalar(select(User).where(User.id == uuid.UUID(me["id"])))
            reviews, news = await _counts_today(db, user, now)
        assert (reviews, news) == (0, 1)
