"""FSRS scheduling (§3, §3.3) plus the interval-fuzzing guardrail (§3.1).

Deviation from the §3.3 sketch, driven by the actual library: py-fsrs 6.x
renamed the entry point ``FSRS`` -> ``Scheduler``, moved ``Optimizer`` behind
the ``fsrs[optimizer]`` extra (it pulls in torch), and has no ``new`` state —
a fresh Card starts in ``Learning``. We keep ``new`` as an app-level state
meaning "never reviewed" and map it onto the library's Learning state on the
way in. Everything else follows the spec: card state lives on the ``cards``
row as stability/difficulty/state/due/last_review.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

from fsrs import Card as FSRSCard
from fsrs import Rating, Scheduler, State

GRADE_TO_RATING: dict[str, Rating] = {
    "again": Rating.Again,
    "hard": Rating.Hard,
    "good": Rating.Good,
    "easy": Rating.Easy,
}
RATING_TO_GRADE = {v: k for k, v in GRADE_TO_RATING.items()}

_STATE_TO_DB = {State.Learning: "learning", State.Review: "review", State.Relearning: "relearning"}
_DB_TO_STATE = {
    "new": State.Learning,
    "learning": State.Learning,
    "review": State.Review,
    "relearning": State.Relearning,
}

DEFAULT_PARAMETERS = list(Scheduler().parameters)
FUZZ_FACTOR = 0.05  # §3.1: ±5%
# The library's Card carries its own id; we key on our UUIDs and never read it.
# Supplying one skips py-fsrs's collision-avoidance sleep (see to_fsrs_card).
PLACEHOLDER_CARD_ID = 1


class FSRSService:
    """One instance per (user, deck) scheduling context — cheap to construct."""

    def __init__(
        self,
        weights: list[float] | None = None,
        desired_retention: float = 0.9,
        *,
        fuzz: bool = True,
    ) -> None:
        kwargs = {"desired_retention": desired_retention, "enable_fuzzing": False}
        if weights:
            kwargs["parameters"] = tuple(weights)
        # Library-side fuzzing is disabled so we own it: our fuzz applies to
        # review-state intervals only and is unit-testable in isolation (§3.1).
        self.scheduler = Scheduler(**kwargs)
        self.fuzz = fuzz

    # ── conversion between the DB row and the library's Card ────────────────

    @staticmethod
    def to_fsrs_card(
        *,
        state: str,
        stability: float | None,
        difficulty: float | None,
        step: int | None,
        due: datetime | None,
        last_review: datetime | None,
    ) -> FSRSCard:
        """Build the library's Card from a persisted row.

        ``card_id`` is passed explicitly and never omitted. Left to default,
        py-fsrs derives one from the clock and then ``time.sleep(0.001)`` to
        avoid collisions — a millisecond per construction, which turns ranking
        a few hundred candidates or replaying an import into seconds of pure
        sleeping. We key cards by our own UUIDs and never read this field, so a
        constant is correct.
        """
        now = datetime.now(UTC)
        if state == "new":
            return FSRSCard(card_id=PLACEHOLDER_CARD_ID, state=State.Learning, step=0, due=now)
        return FSRSCard(
            card_id=PLACEHOLDER_CARD_ID,
            state=_DB_TO_STATE[state],
            step=step if state in ("learning", "relearning") else None,
            stability=stability,
            difficulty=difficulty,
            due=_aware(due) or now,
            last_review=_aware(last_review),
        )

    @staticmethod
    def from_fsrs_card(card: FSRSCard) -> dict:
        return {
            "state": _STATE_TO_DB[card.state],
            "stability": card.stability,
            "difficulty": card.difficulty,
            "step": card.step,
            "due": card.due,
            "last_review": card.last_review,
        }

    # ── scheduling ──────────────────────────────────────────────────────────

    def schedule(
        self, card_state: FSRSCard, grade: Rating, reviewed_at: datetime, duration_ms: int | None = None
    ) -> tuple[FSRSCard, dict]:
        """Advance one card by one review.

        ``grade`` is Again|Hard|Good|Easy, already mapped from the LLM's grading
        output (§4) or a manual button press. Called from
        POST /api/review/{card_id}/confirm (§7.1).

        Per FSRS correctness decoupling: latency is not an input to the review
        scheduling algorithm; review_duration is strictly None.
        """
        updated, _log = self.scheduler.review_card(
            card_state, grade, reviewed_at, review_duration=None
        )
        if self.fuzz:
            updated.due = self._fuzz_due(updated, reviewed_at)
        return updated, self.from_fsrs_card(updated)

    def _fuzz_due(self, card: FSRSCard, reviewed_at: datetime) -> datetime:
        """±5% jitter so cards learned together don't clump on one future day.

        Only applied to review-state intervals of >= 2 days; sub-day learning
        steps must stay exact or the learning ladder breaks.
        """
        if card.state is not State.Review:
            return card.due
        interval = card.due - reviewed_at
        if interval < timedelta(days=2):
            return card.due
        jitter = 1.0 + random.uniform(-FUZZ_FACTOR, FUZZ_FACTOR)
        return reviewed_at + timedelta(seconds=interval.total_seconds() * jitter)

    def retrievability(self, card: FSRSCard, at: datetime | None = None) -> float:
        """R — probability of recall right now. Drives overdue-boost in §9."""
        return self.scheduler.get_card_retrievability(card, at or datetime.now(UTC))

    @staticmethod
    def compress_for_event_horizon(
        due: datetime,
        reviewed_at: datetime,
        target_event_date: datetime | None,
        taper_buffer_days: float = 1.5,
    ) -> datetime:
        """Compresses interval if scheduled due date extends past the target event date.

        Ensures cards peak during the competition/exam overlearning window (1-2 days prior).
        """
        if not target_event_date:
            return due

        event_aware = (
            target_event_date if target_event_date.tzinfo else target_event_date.replace(tzinfo=UTC)
        )
        review_aware = (
            reviewed_at if reviewed_at.tzinfo else reviewed_at.replace(tzinfo=UTC)
        )
        due_aware = due if due.tzinfo else due.replace(tzinfo=UTC)

        time_to_event = event_aware - review_aware
        if time_to_event <= timedelta(hours=6):
            return due

        if due_aware >= event_aware:
            buffer_seconds = min(time_to_event.total_seconds() * 0.25, taper_buffer_days * 86400.0)
            target_due = event_aware - timedelta(seconds=buffer_seconds)
            if target_due > review_aware:
                return target_due

        return due

    # ── parameter optimization (§3) ─────────────────────────────────────────

    @staticmethod
    def optimizer_available() -> bool:
        """Whether a *real* optimizer is installed.

        Importing ``fsrs.Optimizer`` always succeeds: without the extra, the
        library substitutes a stub whose ``__init__`` raises ImportError. So the
        honest check is for torch, which is what ``fsrs[optimizer]`` pulls in.
        """
        import importlib.util

        if importlib.util.find_spec("torch") is None:
            return False
        try:
            from fsrs import Optimizer  # noqa: F401
        except ImportError:
            return False
        return True

    @staticmethod
    def optimize(review_logs: list[dict]) -> list[float]:
        """Refit the 21 weights from a user's full review history.

        Runs nightly per user (app/jobs/optimize_fsrs.py). Requires the
        ``optimizer`` extra; callers should check ``optimizer_available()`` first.
        """
        from fsrs import Optimizer  # imported lazily: torch is optional

        return list(Optimizer(review_logs).compute_optimal_parameters())


def _aware(dt: datetime | None) -> datetime | None:
    """SQLite round-trips datetimes without tzinfo; FSRS requires aware ones."""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def build_review_log_payload(card_id: int, grade: str, reviewed_at: datetime, duration_ms: int | None = None):
    """Shape a persisted review_logs row the way the FSRS Optimizer expects.

    Review duration is set to None so the optimizer fits parameters purely on
    interval retrievability without latency distortion.
    """
    from fsrs import ReviewLog as FSRSReviewLog

    return FSRSReviewLog(
        card_id=card_id,
        rating=GRADE_TO_RATING[grade],
        review_datetime=_aware(reviewed_at),
        review_duration=None,
    )
