"""LLM grading subsystem (§4): parsing, rubric selection, escalation,
the heuristic sanity check, caching, calibration, and the manual fallback."""

from __future__ import annotations

import pytest

from app.routers.review import format_latency
from app.services.grading_profiles import PROFILES, build_prompt
from app.services.grading_service import (
    GradingService,
    GradingUnavailable,
    apply_bias,
    disagrees_with_heuristic,
    grade_for_score,
    heuristic_overlap,
    parse_json,
    parse_score,
)


class TestParsing:
    """Models aren't schema-constrained, so the parser has
    to survive whatever prose the model wraps its JSON in (§4.6)."""

    def test_plain_json(self):
        assert parse_json('{"score": 85}')["score"] == 85

    def test_fenced_json(self):
        raw = 'Here you go:\n```json\n{"score": 55, "confidence": 0.7}\n```\nHope that helps!'
        assert parse_json(raw)["score"] == 55

    def test_bare_fence(self):
        assert parse_json('```\n{"score": 95}\n```')["score"] == 95

    def test_json_embedded_in_prose(self):
        assert parse_json('The answer is {"score": 10} because it was wrong.')["score"] == 10

    def test_unparseable_raises_rather_than_guessing(self):
        with pytest.raises(GradingUnavailable):
            parse_json("I think the answer was pretty good, honestly.")

    def test_empty_raises(self):
        with pytest.raises(GradingUnavailable):
            parse_json("")


class TestHeuristicSanityCheck:
    """§4.3 — the cheap keyword check that runs alongside the model."""

    def test_overlap_is_content_words_reproduced(self):
        assert heuristic_overlap("The mitochondrion is the powerhouse", "mitochondrion powerhouse") == 1.0
        assert heuristic_overlap("mitochondrion powerhouse", "banana") == 0.0

    def test_stopwords_do_not_inflate_overlap(self):
        assert heuristic_overlap("the and of a", "the and of a") == 0.0

    def test_flags_confident_pass_on_an_unrelated_answer(self):
        assert disagrees_with_heuristic("good", 0.0) is True

    def test_flags_fail_on_a_near_verbatim_answer(self):
        assert disagrees_with_heuristic("again", 0.95) is True

    def test_stays_quiet_when_they_agree(self):
        assert disagrees_with_heuristic("good", 0.9) is False
        assert disagrees_with_heuristic("again", 0.05) is False

    def test_paraphrase_is_not_flagged_as_disagreement(self):
        # A correct paraphrase sits in the middle; only the extremes are flagged,
        # otherwise semantic grading is pointless.
        assert disagrees_with_heuristic("good", 0.4) is False


class TestCalibration:
    """§4.3 — per-user bias correction, not fine-tuning. Applied to the score
    so the % shown and the grade suggested can never contradict each other."""

    def test_zero_bias_changes_nothing(self):
        assert apply_bias(80, 0.0) == 80

    def test_small_bias_nudges_proportionally(self):
        assert apply_bias(80, 0.2) == 84

    def test_positive_bias_can_carry_a_score_into_the_next_band(self):
        score = apply_bias(55, 1.0)  # mid "hard"
        assert score == 75
        assert grade_for_score(score) == "good"

    def test_negative_bias_nudges_down(self):
        score = apply_bias(75, -1.0)
        assert score == 55
        assert grade_for_score(score) == "hard"

    def test_bias_clamps_at_the_ends_of_the_scale(self):
        assert apply_bias(95, 3.0) == 100
        assert apply_bias(10, -3.0) == 0

    def test_calibrated_score_always_falls_inside_its_own_grade_band(self):
        """The regression this replaced: biasing the grade alone produced an
        85% answer suggested as "easy", sitting next to an Easy button
        labelled 90-100%. Whatever the bias, the score has to land inside the
        band of the grade derived from it — that band is what the UI shows."""
        bands = {"again": (0, 39), "hard": (40, 69), "good": (70, 89), "easy": (90, 100)}
        for raw in range(0, 101):
            for bias in (-3.0, -1.5, -1.0, -0.4, 0.0, 0.4, 1.0, 1.5, 3.0):
                score = apply_bias(raw, bias)
                low, high = bands[grade_for_score(score)]
                assert low <= score <= high, f"{score} outside band for raw={raw} bias={bias}"


class TestProfiles:
    """§4.5 — one rubric per card type, merged into the §4.4 base prompt."""

    def test_all_three_profiles_exist(self):
        assert set(PROFILES) == {"short_answer", "conceptual", "math_code"}

    def test_prompt_carries_the_card_and_the_rubric(self):
        prompt = build_prompt(
            "math_code", front="2+2", back="4", user_answer="four", card_type="basic"
        )
        assert "2+2" in prompt and "four" in prompt
        assert "worked solution" in prompt  # math rubric merged in
        assert "0-39" in prompt  # base 0-100 scoring scale preserved

    def test_prompt_never_asks_for_or_mentions_response_time(self):
        """§4.1: grading must be content-only — response time isn't even in
        the prompt for the model to be tempted by."""
        prompt = build_prompt(
            "short_answer", front="f", back="b", user_answer="u", card_type="basic"
        )
        assert "latency" not in prompt.lower()
        assert "response time" not in prompt.lower()
        lowered = prompt.lower()
        assert "must not" in lowered and "response" in lowered and "speed" in lowered

    def test_conceptual_grades_content_not_prose(self):
        prompt = build_prompt(
            "conceptual", front="f", back="b", user_answer="u", card_type="basic"
        )
        assert "NOT the prose quality" in prompt

    def test_unknown_profile_falls_back_to_short_answer(self):
        prompt = build_prompt(
            "nonsense", front="f", back="b", user_answer="u", card_type="basic"
        )
        assert "short answer / vocabulary" in prompt

    def test_short_answer_rubric_emphasizes_keyword_and_concept_match(self):
        assert "keyword/concept coverage" in PROFILES["short_answer"]


class TestEscalation:
    """The grading evaluation path, with the transport stubbed out."""

    @staticmethod
    def _service(responses):
        svc = GradingService("small-model", "big-model")
        calls = []

        async def fake_generate(prompt, model=None, schema=None, **kwargs):
            calls.append(model or svc.model)
            return responses[min(len(calls) - 1, len(responses) - 1)]

        svc._generate = fake_generate
        svc.calls = calls
        return svc

    async def test_direct_model_evaluation(self):
        svc = self._service(['{"score":85,"confidence":0.92,"reasoning":"ok"}'])
        result = await svc.grade_with_escalation("f", "b", "a", "short_answer")
        assert svc.calls == ["small-model"]
        assert result["escalated"] is False
        assert result["score"] == 85
        assert result["grade"] == "good"

    async def test_math_code_evaluation(self):
        svc = self._service(['{"score":95,"confidence":0.95,"reasoning":"equivalent"}'])
        result = await svc.grade_with_escalation("f", "b", "a", "math_code")
        assert svc.calls == ["small-model"]
        assert result["score"] == 95

    async def test_missing_score_is_rejected(self):
        svc = self._service(['{"confidence":0.9,"reasoning":"no score field"}'])
        with pytest.raises(GradingUnavailable):
            await svc.grade_with_escalation("f", "b", "a", "short_answer")

    async def test_non_numeric_score_is_rejected(self):
        svc = self._service(['{"score":"excellent","confidence":0.9,"reasoning":"x"}'])
        with pytest.raises(GradingUnavailable):
            await svc.grade_with_escalation("f", "b", "a", "short_answer")

    async def test_unreachable_endpoint_raises_unavailable(self):
        svc = GradingService(base_url="http://127.0.0.1:59999")
        with pytest.raises(GradingUnavailable):
            await svc.grade("f", "b", "a")


class TestScoring:
    """§4.1 — a 0-100 correctness score is what the user sees and what
    grading reasons about; it buckets into the 4-point scale FSRS actually
    schedules on, since py-fsrs's transitions are only defined per rating."""

    def test_bucket_boundaries(self):
        assert grade_for_score(0) == "again"
        assert grade_for_score(39) == "again"
        assert grade_for_score(40) == "hard"
        assert grade_for_score(69) == "hard"
        assert grade_for_score(70) == "good"
        assert grade_for_score(89) == "good"
        assert grade_for_score(90) == "easy"
        assert grade_for_score(100) == "easy"

    @staticmethod
    def _service(response: str):
        svc = GradingService()

        async def fake_generate(prompt, model, schema=None):
            return response

        svc._generate = fake_generate
        return svc

    async def test_out_of_range_score_is_clamped(self):
        svc = self._service('{"score": 150, "confidence": 0.9, "reasoning": "over"}')
        result = await svc.grade("f", "b", "a")
        assert result["score"] == 100
        assert result["grade"] == "easy"

        svc = self._service('{"score": -20, "confidence": 0.9, "reasoning": "under"}')
        result = await svc.grade("f", "b", "a")
        assert result["score"] == 0
        assert result["grade"] == "again"

    def test_score_is_rounded_before_bucketing(self):
        """A fractional score bucketed raw but displayed rounded would
        contradict itself: 89.6 renders as "90%" but bands as "good" (70-89).
        One integer has to decide both."""
        assert parse_score(89.6) == 90
        assert grade_for_score(parse_score(89.6)) == "easy"
        assert parse_score(69.5) == 70
        assert grade_for_score(parse_score(69.5)) == "good"

    def test_percent_suffixed_score_is_accepted(self):
        """Models write "85%" often enough that rejecting it — and collapsing
        the whole call into the manual fallback — is a silly way to lose an
        otherwise good response."""
        assert parse_score("85%") == 85
        assert parse_score(" 42 % ".replace(" %", "%").strip()) == 42
        assert parse_score("77") == 77

    def test_genuinely_unparseable_score_still_raises(self):
        for bad in ("excellent", "", None, "%"):
            with pytest.raises(GradingUnavailable):
                parse_score(bad)


class TestReviewIntegration:
    """The grading path as the review endpoints actually use it."""

    async def test_llm_grade_is_cached_and_feeds_the_confirm_log(self, auth_client, monkeypatch):
        import app.routers.review as review_router

        calls = {"n": 0}
        seen_kwargs: dict = {}

        async def fake_grade(self, **kwargs):
            calls["n"] += 1
            seen_kwargs.update(kwargs)
            return {
                "score": 85,
                "grade": "good",
                "confidence": 0.9,
                "matched_points": ["named the capital"],
                "missed_points": [],
                "reasoning": "Correct city, minor spelling slip.",
                "model_used": "stub-model",
                "escalated": False,
            }

        monkeypatch.setattr(
            review_router.GradingService, "grade_with_escalation", fake_grade, raising=True
        )

        await auth_client.patch("/api/me", json={"llm_grading_consent": True})
        deck_id = (await auth_client.post("/api/decks", json={"name": "Graded"})).json()["id"]
        note = (
            await auth_client.post(
                "/api/notes",
                json={
                    "deck_id": deck_id,
                    "template_kind": "basic",
                    "field_values": {"Front": "Capital of France?", "Back": "Paris"},
                },
            )
        ).json()
        card_id = note["cards"][0]["id"]

        first = await auth_client.post(
            f"/api/review/{card_id}/answer", json={"typed_answer": "Pariss", "latency_ms": 2400}
        )
        body = first.json()
        assert body["degraded_to_manual"] is False
        assert body["suggested_grade"] == "good"
        assert body["score"] == 85
        assert body["reasoning"].startswith("Correct city")
        assert body["reference_answer"] == "Paris"
        assert body["cached"] is False
        # The response carries a latency note for the UI, but the grading call
        # itself never receives latency — the whole point of this change.
        assert body["latency_note"] == "answered in 2s"
        assert "latency_ms" not in seen_kwargs

        # §4.3: an identical resubmit must not burn a second API call.
        again = await auth_client.post(
            f"/api/review/{card_id}/answer", json={"typed_answer": "Pariss", "latency_ms": 2400}
        )
        assert again.json()["cached"] is True
        assert calls["n"] == 1
        # The score has to survive the cache round-trip, not just the grade —
        # it's the number the user is actually shown.
        assert again.json()["score"] == 85
        assert again.json()["suggested_grade"] == "good"

        # The user overrides down to "hard"; the log keeps both verdicts.
        await auth_client.post(
            f"/api/review/{card_id}/confirm",
            json={
                "final_grade": "hard",
                "overridden": True,
                "typed_answer": "Pariss",
                "latency_ms": 2400,
            },
        )
        logs = (await auth_client.get("/api/export")).json()["review_logs"]
        entry = next(x for x in logs if x["typed_answer"] == "Pariss")
        assert entry["llm_grade"] == "good"
        assert entry["final_grade"] == "hard"
        assert entry["overridden"] is True
        assert entry["llm_confidence"] == 0.9

        # And the override moved the calibration bias downward (§4.3).
        me = (await auth_client.get("/api/me")).json()
        assert me["grading_bias"] < 0

    async def test_api_failure_degrades_to_manual(self, auth_client, monkeypatch):
        import app.routers.review as review_router

        async def boom(self, **kwargs):
            raise GradingUnavailable("429 quota exceeded")

        monkeypatch.setattr(review_router.GradingService, "grade_with_escalation", boom)

        await auth_client.patch("/api/me", json={"llm_grading_consent": True})
        deck_id = (await auth_client.post("/api/decks", json={"name": "Quota"})).json()["id"]
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

        resp = await auth_client.post(
            f"/api/review/{note['cards'][0]['id']}/answer",
            json={"typed_answer": "a", "latency_ms": 100},
        )
        assert resp.status_code == 200
        assert resp.json()["degraded_to_manual"] is True
        assert "quota" in resp.json()["degraded_reason"]
        assert resp.json()["reference_answer"] == "a"
        # No automated assessment in manual mode — nothing to show a % for.
        assert resp.json()["score"] is None
        # The note is informational and shows up on every fallback path too —
        # it isn't gated behind grading actually succeeding.
        assert resp.json()["latency_note"] == "answered in under a second"

    async def test_no_consent_manual_fallback_still_carries_the_latency_note(self, auth_client):
        deck_id = (await auth_client.post("/api/decks", json={"name": "NoConsent"})).json()["id"]
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
        resp = await auth_client.post(
            f"/api/review/{note['cards'][0]['id']}/answer",
            json={"typed_answer": "a", "latency_ms": 75_000},
        )
        body = resp.json()
        assert body["degraded_to_manual"] is True
        assert body["degraded_reason"] == "consent_not_given"
        assert body["latency_note"] == "answered in 1m 15s"


class TestLatencyNote:
    """§4.1 — informational only, computed without any LLM involvement."""

    def test_none_or_non_positive_is_no_note(self):
        assert format_latency(None) is None
        assert format_latency(0) is None
        assert format_latency(-500) is None

    def test_sub_second(self):
        assert format_latency(400) == "answered in under a second"

    def test_whole_seconds(self):
        assert format_latency(2_400) == "answered in 2s"
        assert format_latency(59_000) == "answered in 59s"

    def test_minutes_with_and_without_remainder(self):
        assert format_latency(60_000) == "answered in 1m"
        assert format_latency(75_000) == "answered in 1m 15s"
        assert format_latency(125_000) == "answered in 2m 5s"


class TestWeaknessMemory:
    """Longitudinal weakness memory prompt construction, normalization, and hinting."""

    def test_build_prompt_injects_previous_weaknesses(self):
        prompt = build_prompt(
            "short_answer",
            front="What is TCP?",
            back="Transmission Control Protocol",
            user_answer="A network protocol",
            card_type="basic",
            previous_weaknesses=["Forgot connection-oriented property", "Omitted handshake details"],
        )
        assert "Previous recorded weaknesses" in prompt
        assert "Forgot connection-oriented property" in prompt
        assert "Omitted handshake details" in prompt
        assert "improvements" in prompt
        assert "persistent_weaknesses" in prompt

    def test_normalize_result_extracts_weakness_fields(self):
        from app.services.grading_service import _normalize_result

        raw = {
            "score": 75,
            "confidence": 0.9,
            "matched_points": ["transport layer"],
            "missed_points": ["handshake"],
            "overlooked_phrases": [],
            "weaknesses": ["Missed 3-way handshake detail"],
            "improvements": ["Now correctly identified as transport protocol"],
            "persistent_weaknesses": ["Still missing handshake"],
            "reasoning": "Good answer with a minor omission.",
        }
        res = _normalize_result(raw)
        assert res["score"] == 75
        assert res["weaknesses"] == ["Missed 3-way handshake detail"]
        assert res["improvements"] == ["Now correctly identified as transport protocol"]
        assert res["persistent_weaknesses"] == ["Still missing handshake"]

    def test_normalize_result_handles_missing_weakness_fields_gracefully(self):
        from app.services.grading_service import _normalize_result

        raw = {
            "score": 90,
            "confidence": 0.95,
            "reasoning": "Complete answer.",
        }
        res = _normalize_result(raw)
        assert res["score"] == 90
        assert res["weaknesses"] == []
        assert res["improvements"] == []
        assert res["persistent_weaknesses"] == []

    @pytest.mark.asyncio
    async def test_generate_weakness_hint_empty_weaknesses(self):
        svc = GradingService()
        hint_res = await svc.generate_weakness_hint("Question", "Answer", [])
        assert hint_res["has_past_weaknesses"] is False
        assert "No prior weaknesses" in hint_res["hint"]

    def test_build_prompt_with_tdd_test_code(self):
        from app.services.grading_profiles import build_prompt

        prompt = build_prompt(
            "math_code",
            front="Implement clamp function",
            back="Math.max(min, Math.min(val, max))",
            user_answer="function clamp(v, lo, hi) { return v < lo ? lo : v > hi ? hi : v; }",
            card_type="code",
            test_code="assertEquals(0, clamp(-5, 0, 10));\nassertEquals(10, clamp(15, 0, 10));",
        )
        assert "Authored Unit Test Suite:" in prompt
        assert "assertEquals(0, clamp(-5, 0, 10))" in prompt
        assert "Unit Testing / TDD Evaluation" in prompt

    @pytest.mark.asyncio
    async def test_tdd_review_answer_forwards_test_code(self, auth_client, monkeypatch):
        import app.routers.review as review_router

        captured = {}

        async def fake_grade(self, **kwargs):
            captured.update(kwargs)
            return {
                "score": 95,
                "grade": "easy",
                "confidence": 0.95,
                "matched_points": ["correct solution", "comprehensive test suite"],
                "missed_points": [],
                "reasoning": "Solid implementation and boundary tests.",
                "model_used": "qwen2.5-coder:7b",
                "escalated": False,
            }

        monkeypatch.setattr(
            review_router.GradingService, "grade_with_escalation", fake_grade, raising=True
        )

        await auth_client.patch("/api/me", json={"llm_grading_consent": True})
        deck_id = (await auth_client.post("/api/decks", json={"name": "TDD Deck"})).json()["id"]
        note = (
            await auth_client.post(
                "/api/notes",
                json={
                    "deck_id": deck_id,
                    "template_kind": "basic",
                    "field_values": {"Front": "Write clamp", "Back": "return max(min, ...)"},
                },
            )
        ).json()
        card_id = note["cards"][0]["id"]

        resp = await auth_client.post(
            f"/api/review/{card_id}/answer",
            json={
                "typed_answer": "function clamp() {}",
                "test_code": "assertEquals(0, clamp(-1, 0, 5));",
                "latency_ms": 1500,
            },
        )
        assert resp.status_code == 200
        assert captured.get("test_code") == "assertEquals(0, clamp(-1, 0, 5));"


