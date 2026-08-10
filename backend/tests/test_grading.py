"""LLM grading subsystem (§4): parsing, rubric selection, escalation,
the heuristic sanity check, caching, calibration, and the manual fallback."""

from __future__ import annotations

import pytest

from app.services.grading_profiles import PROFILES, build_prompt
from app.services.grading_service import (
    GradingService,
    GradingUnavailable,
    apply_bias,
    disagrees_with_heuristic,
    heuristic_overlap,
    parse_json,
)


class TestParsing:
    """Gemma via the Gemini API can't be schema-constrained, so the parser has
    to survive whatever prose the model wraps its JSON in (§4.6)."""

    def test_plain_json(self):
        assert parse_json('{"grade": "good"}')["grade"] == "good"

    def test_fenced_json(self):
        raw = 'Here you go:\n```json\n{"grade": "hard", "confidence": 0.7}\n```\nHope that helps!'
        assert parse_json(raw)["grade"] == "hard"

    def test_bare_fence(self):
        assert parse_json('```\n{"grade": "easy"}\n```')["grade"] == "easy"

    def test_json_embedded_in_prose(self):
        assert parse_json('The answer is {"grade": "again"} because it was wrong.')["grade"] == "again"

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
    """§4.3 — per-user bias correction, not fine-tuning."""

    def test_small_bias_changes_nothing(self):
        assert apply_bias("good", 0.2) == "good"

    def test_positive_bias_nudges_up(self):
        assert apply_bias("hard", 1.0) == "good"

    def test_negative_bias_nudges_down(self):
        assert apply_bias("good", -1.0) == "hard"

    def test_bias_clamps_at_the_ends_of_the_scale(self):
        assert apply_bias("easy", 3.0) == "easy"
        assert apply_bias("again", -3.0) == "again"


class TestProfiles:
    """§4.5 — one rubric per card type, merged into the §4.4 base prompt."""

    def test_all_three_profiles_exist(self):
        assert set(PROFILES) == {"short_answer", "conceptual", "math_code"}

    def test_prompt_carries_the_card_and_the_rubric(self):
        prompt = build_prompt(
            "math_code", front="2+2", back="4", user_answer="four", latency_ms=500, card_type="basic"
        )
        assert "2+2" in prompt and "four" in prompt and "500 ms" in prompt
        assert "worked solution" in prompt  # math rubric merged in
        assert "again: wrong" in prompt  # base 4-point scale preserved

    def test_conceptual_grades_content_not_prose(self):
        prompt = build_prompt(
            "conceptual", front="f", back="b", user_answer="u", latency_ms=1, card_type="basic"
        )
        assert "NOT the prose quality" in prompt

    def test_unknown_profile_falls_back_to_short_answer(self):
        prompt = build_prompt(
            "nonsense", front="f", back="b", user_answer="u", latency_ms=1, card_type="basic"
        )
        assert "short answer / vocabulary" in prompt


class TestEscalation:
    """§4.2 — the escalation path, with the transport stubbed out."""

    @staticmethod
    def _service(responses):
        svc = GradingService("fake-key", "small-model", "big-model")
        calls = []

        async def fake_generate(prompt, model, schema=None):
            calls.append(model)
            return responses[min(len(calls) - 1, len(responses) - 1)]

        svc._generate = fake_generate
        svc.calls = calls
        return svc

    async def test_confident_answer_stays_on_the_small_model(self):
        svc = self._service(['{"grade":"good","confidence":0.92,"reasoning":"ok"}'])
        result = await svc.grade_with_escalation("f", "b", "a", 100, "short_answer")
        assert svc.calls == ["small-model"]
        assert result["escalated"] is False
        assert result["grade"] == "good"

    async def test_low_confidence_retries_on_the_larger_model(self):
        svc = self._service(
            [
                '{"grade":"hard","confidence":0.3,"reasoning":"unsure"}',
                '{"grade":"good","confidence":0.9,"reasoning":"clear on retry"}',
            ]
        )
        result = await svc.grade_with_escalation("f", "b", "a", 100, "short_answer")
        assert svc.calls == ["small-model", "big-model"]
        assert result["grade"] == "good"
        assert result["escalated"] is True

    async def test_math_code_goes_straight_to_the_larger_model(self):
        svc = self._service(['{"grade":"good","confidence":0.95,"reasoning":"equivalent"}'])
        result = await svc.grade_with_escalation("f", "b", "a", 100, "math_code")
        assert svc.calls == ["big-model"]
        assert result["escalated"] is True

    async def test_disputed_card_forces_escalation(self):
        svc = self._service(['{"grade":"good","confidence":0.99,"reasoning":"ok"}'])
        await svc.grade_with_escalation("f", "b", "a", 100, "short_answer", force_escalate=True)
        assert svc.calls == ["big-model"]

    async def test_escalation_does_not_stick_to_the_instance(self):
        """The §4.6 sketch mutated self.model, which would leave every later
        card permanently escalated. It must not."""
        svc = self._service(['{"grade":"good","confidence":0.95,"reasoning":"ok"}'])
        await svc.grade_with_escalation("f", "b", "a", 100, "math_code")
        assert svc.model == "small-model"

    async def test_invalid_grade_is_rejected(self):
        svc = self._service(['{"grade":"excellent","confidence":0.9,"reasoning":"x"}'])
        with pytest.raises(GradingUnavailable):
            await svc.grade_with_escalation("f", "b", "a", 100, "short_answer")

    async def test_missing_key_is_unavailable_not_a_crash(self):
        svc = GradingService(None)
        with pytest.raises(GradingUnavailable):
            await svc.grade("f", "b", "a", 100)


class TestReviewIntegration:
    """The grading path as the review endpoints actually use it."""

    async def test_llm_grade_is_cached_and_feeds_the_confirm_log(self, auth_client, monkeypatch):
        import app.routers.review as review_router

        calls = {"n": 0}

        async def fake_grade(self, **kwargs):
            calls["n"] += 1
            return {
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
        monkeypatch.setattr(review_router, "decrypt_api_key", lambda _: "fake-key")

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
        assert body["reasoning"].startswith("Correct city")
        assert body["reference_answer"] == "Paris"
        assert body["cached"] is False

        # §4.3: an identical resubmit must not burn a second API call.
        again = await auth_client.post(
            f"/api/review/{card_id}/answer", json={"typed_answer": "Pariss", "latency_ms": 2400}
        )
        assert again.json()["cached"] is True
        assert calls["n"] == 1

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
        monkeypatch.setattr(review_router, "decrypt_api_key", lambda _: "fake-key")

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
