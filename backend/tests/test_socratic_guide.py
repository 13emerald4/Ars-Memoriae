"""Socratic AI Guide: one diagnostic question at a time, never the answer.

Two layers get tested separately: the service method's answer-leak guard in
isolation (no transport, no HTTP), and the endpoint's consent/key gating the
same way test_grading.py exercises the grading path."""

from __future__ import annotations

from app.services.grading_service import GradingService


class TestLeakGuard:
    """§Socratic AI Guide's defense-in-depth: the prompt says never reveal the
    answer, but the reply is also checked, same as §4.3 cross-checks a grade."""

    @staticmethod
    def _service(raw_response: str) -> GradingService:
        svc = GradingService("fake-key", "small-model")

        async def fake_generate(prompt, model, schema=None):
            return raw_response

        svc._generate = fake_generate
        return svc

    async def test_a_genuine_hint_passes_through_unchanged(self):
        svc = self._service('{"message": "What do you call the capital of a country?", "on_track": false}')
        result = await svc.ask_socratic_question("Capital of France?", "Paris", [], "")
        assert result["message"] == "What do you call the capital of a country?"
        assert result["on_track"] is False

    async def test_a_reply_that_echoes_the_answer_is_replaced(self):
        svc = self._service('{"message": "The answer is Paris, the capital of France.", "on_track": true}')
        result = await svc.ask_socratic_question("Capital of France?", "Paris", [], "")
        assert "Paris" not in result["message"]
        assert "hold off" in result["message"]

    async def test_history_is_passed_through_as_guide_and_student_turns(self):
        svc = self._service('{"message": "ok", "on_track": false}')
        captured = {}

        async def fake_generate(prompt, model, schema=None):
            captured["prompt"] = prompt
            return '{"message": "ok", "on_track": false}'

        svc._generate = fake_generate
        await svc.ask_socratic_question(
            "Capital of France?",
            "Paris",
            [("guide", "What continent is it in?"), ("student", "Europe")],
            "I think it starts with P",
        )
        assert "Guide: What continent is it in?" in captured["prompt"]
        assert "Student: Europe" in captured["prompt"]
        assert "I think it starts with P" in captured["prompt"]


class TestGuideEndpoint:
    async def test_degrades_without_consent(self, auth_client):
        deck_id = (await auth_client.post("/api/decks", json={"name": "D"})).json()["id"]
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
        card_id = note["cards"][0]["id"]

        resp = await auth_client.post(f"/api/review/{card_id}/guide", json={"history": []})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["degraded"] is True
        assert body["degraded_reason"] == "consent_not_given"

    async def test_degrades_when_engine_unavailable(self, auth_client, monkeypatch):
        import app.routers.review as review_router
        from app.services.grading_service import GradingUnavailable

        async def fail_ask(*args, **kwargs):
            raise GradingUnavailable("engine offline")

        monkeypatch.setattr(review_router.GradingService, "ask_socratic_question", fail_ask)
        await auth_client.patch("/api/me", json={"llm_grading_consent": True})
        deck_id = (await auth_client.post("/api/decks", json={"name": "D"})).json()["id"]
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
        card_id = note["cards"][0]["id"]

        resp = await auth_client.post(f"/api/review/{card_id}/guide", json={"history": []})
        assert resp.status_code == 200, resp.text
        assert resp.json()["degraded"] is True
        assert "engine offline" in resp.json()["degraded_reason"]

    async def test_a_hint_reaches_the_response(self, auth_client, monkeypatch):
        import app.routers.review as review_router

        async def fake_ask(self, **kwargs):
            return {"message": "What continent has Paris?", "on_track": False}

        monkeypatch.setattr(review_router.GradingService, "ask_socratic_question", fake_ask)
        monkeypatch.setattr(review_router, "decrypt_api_key", lambda _: "fake-key")
        await auth_client.patch("/api/me", json={"llm_grading_consent": True})

        deck_id = (await auth_client.post("/api/decks", json={"name": "D"})).json()["id"]
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

        resp = await auth_client.post(f"/api/review/{card_id}/guide", json={"history": []})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["degraded"] is False
        assert body["message"] == "What continent has Paris?"

    async def test_a_stranger_cannot_ask_about_someone_elses_card(self, auth_client, client):
        deck_id = (await auth_client.post("/api/decks", json={"name": "D"})).json()["id"]
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
        card_id = note["cards"][0]["id"]

        stranger = await client.post(
            "/api/auth/register",
            json={"email": "stranger-guide@example.com", "password": "hunter2hunter2"},
        )
        assert stranger.status_code == 201, stranger.text
        headers = {"Authorization": f"Bearer {stranger.json()['access_token']}"}

        resp = await client.post(
            f"/api/review/{card_id}/guide", json={"history": []}, headers=headers
        )
        assert resp.status_code == 404, resp.text
