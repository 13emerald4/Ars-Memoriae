"""Learn & Practice — teach from the card's citations before testing recall.

The property that matters most: a lesson is only ever offered when there is a
real source behind it. The user reads a lesson *because* they don't know the
material, which is the worst possible moment to hand them a fabrication.
"""

from __future__ import annotations

import io

MARKDOWN = """# Balance Sheet Recessions

## The Behavioral Shift

During such a recession the private sector shifts from profit maximization to
debt minimization. Instead of maximizing profit, businesses and households
prioritize paying down debt and repairing their balance sheets.
"""


async def _card_with_citation(client) -> tuple[str, str]:
    """(card_id, deck_id) for a card carrying a real document citation."""
    doc = (
        await client.post(
            "/api/documents",
            files={"file": ("notes.md", io.BytesIO(MARKDOWN.encode()), "text/markdown")},
        )
    ).json()
    extracts = (await client.get(f"/api/sources/{doc['source_id']}/extracts")).json()
    cited = next(e for e in extracts if e["locator"] == "The Behavioral Shift")

    accepted = (
        await client.post(
            f"/api/documents/{doc['source_id']}/accept-deck",
            json={
                "deck": "Macro",
                "cards": [
                    {
                        "kind": "qa",
                        "front": "What replaces profit maximization after a bubble bursts?",
                        "back": "Debt minimization.",
                        "quote": "shifts from profit maximization to debt minimization",
                        "quote_verified": True,
                        "locator": cited["locator"],
                        "extract_id": cited["id"],
                    }
                ],
            },
        )
    ).json()
    cards = (await client.get(f"/api/cards?deck_id={accepted['deck_id']}")).json()
    return cards[0]["id"], accepted["deck_id"]


async def _plain_card(client) -> str:
    """A hand-made card with no citations behind it."""
    deck_id = (await client.post("/api/decks", json={"name": "Plain"})).json()["id"]
    note = (
        await client.post(
            "/api/notes",
            json={
                "deck_id": deck_id,
                "template_kind": "basic",
                "field_values": {"Front": "2 + 2?", "Back": "4"},
            },
        )
    ).json()
    return note["cards"][0]["id"]


class TestRequiresCitations:
    async def test_a_card_with_no_source_is_not_teachable(self, auth_client):
        card_id = await _plain_card(auth_client)
        resp = await auth_client.get(f"/api/review/{card_id}/lesson")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["available"] is False
        assert body["reason"] == "no_citations"
        assert body["body"] == ""
        assert body["citations"] == []

    async def test_a_cited_card_is_teachable(self, auth_client):
        card_id, _ = await _card_with_citation(auth_client)
        body = (await auth_client.get(f"/api/review/{card_id}/lesson")).json()
        assert body["available"] is True
        assert len(body["citations"]) == 1
        assert body["citations"][0]["locator"] == "The Behavioral Shift"


class TestSourceFallback:
    async def test_without_consent_the_passage_itself_is_the_lesson(self, auth_client):
        """No key is a full path, not an error — you still get something to
        read, just labelled as the raw source rather than a written lesson."""
        card_id, _ = await _card_with_citation(auth_client)
        body = (await auth_client.get(f"/api/review/{card_id}/lesson")).json()

        assert body["available"] is True
        assert body["reason"] == "consent_not_given"
        assert body["generated"] is False
        assert body["model_used"] is None
        assert "debt minimization" in body["body"]
        assert body["key_points"] == []

    async def test_the_fallback_is_not_cached(self, auth_client, monkeypatch):
        """Adding a key later must produce a real lesson, not replay the
        stand-in forever."""
        card_id, _ = await _card_with_citation(auth_client)
        first = (await auth_client.get(f"/api/review/{card_id}/lesson")).json()
        assert first["generated"] is False

        import app.services.lesson_service as svc

        async def fake_lesson(self, **kwargs):
            return {"lesson": "Written lesson.", "key_points": ["a point"]}

        monkeypatch.setattr(svc.GradingService, "generate_lesson", fake_lesson)
        await auth_client.patch("/api/me", json={"llm_grading_consent": True})

        second = (await auth_client.get(f"/api/review/{card_id}/lesson")).json()
        assert second["generated"] is True
        assert second["body"] == "Written lesson."


class TestGeneration:
    async def test_lesson_is_generated_then_cached(self, auth_client, monkeypatch):
        import app.services.lesson_service as svc

        calls = {"n": 0}
        seen: dict = {}

        async def fake_lesson(self, **kwargs):
            calls["n"] += 1
            seen.update(kwargs)
            return {
                "lesson": "When a bubble bursts, firms switch to paying down debt.",
                "key_points": ["Profit maximization gives way to debt minimization"],
            }

        monkeypatch.setattr(svc.GradingService, "generate_lesson", fake_lesson)
        await auth_client.patch("/api/me", json={"llm_grading_consent": True})

        card_id, _ = await _card_with_citation(auth_client)
        first = (await auth_client.get(f"/api/review/{card_id}/lesson")).json()

        assert first["available"] is True
        assert first["generated"] is True
        assert first["cached"] is False
        assert first["body"].startswith("When a bubble bursts")
        assert first["key_points"] == ["Profit maximization gives way to debt minimization"]

        # The model teaches from the surrounding passage, not the answer-span
        # quote — a quote is too narrow to explain anything.
        assert any("prioritize paying down debt" in p for p in seen["passages"])

        second = (await auth_client.get(f"/api/review/{card_id}/lesson")).json()
        assert second["cached"] is True
        assert second["body"] == first["body"]
        assert calls["n"] == 1, "a cached lesson must not re-hit the model"

    async def test_generation_failure_falls_back_to_the_source(self, auth_client, monkeypatch):
        import app.services.lesson_service as svc
        from app.services.grading_service import GradingUnavailable

        async def boom(self, **kwargs):
            raise GradingUnavailable("429 quota exceeded")

        monkeypatch.setattr(svc.GradingService, "generate_lesson", boom)
        await auth_client.patch("/api/me", json={"llm_grading_consent": True})

        card_id, _ = await _card_with_citation(auth_client)
        body = (await auth_client.get(f"/api/review/{card_id}/lesson")).json()

        assert body["available"] is True
        assert body["generated"] is False
        assert "quota" in body["reason"]
        assert "debt minimization" in body["body"]


class TestLessonPrompt:
    def test_prompt_forbids_going_beyond_the_passages(self):
        from app.services.grading_profiles import LESSON_PROMPT

        prompt = LESSON_PROMPT.format(
            front="q", back="a", passages="some source text", max_words=160
        )
        lowered = prompt.lower()
        assert "only the source passage" in lowered
        assert "do not add" in lowered
        # The answer belongs in the lesson: the student reads it, then recalls it.
        assert "do include the answer" in lowered

    async def test_generate_lesson_refuses_with_no_passages(self):
        import pytest

        from app.services.grading_service import GradingService, GradingUnavailable

        with pytest.raises(GradingUnavailable, match="no source passages"):
            await GradingService().generate_lesson("q", "a", [])


class TestTenantIsolation:
    async def test_another_users_card_lesson_is_not_reachable(self, client):
        import uuid

        async def register() -> str:
            email = f"lesson-{uuid.uuid4().hex[:8]}@example.com"
            resp = await client.post(
                "/api/auth/register", json={"email": email, "password": "hunter2hunter2"}
            )
            return resp.json()["access_token"]

        alice, bob = await register(), await register()

        client.headers["Authorization"] = f"Bearer {alice}"
        card_id, _ = await _card_with_citation(client)

        client.headers["Authorization"] = f"Bearer {bob}"
        assert (await client.get(f"/api/review/{card_id}/lesson")).status_code == 404
