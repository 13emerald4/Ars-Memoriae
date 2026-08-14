"""Post-session reflection (§2): the exit half of the focus-goal prompt —
"what distracted you, how will you fix it" — asked after a block ends and
never blocking the finish itself."""

from __future__ import annotations


async def _start(client, **kw) -> dict:
    body = {"planned_minutes": 30, "goal_cards": 0, **kw}
    resp = await client.post("/api/sessions/start", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _finish(client, session_id: str, remaining_seconds: int = 0) -> dict:
    resp = await client.post(
        f"/api/sessions/{session_id}/finish", json={"remaining_seconds": remaining_seconds}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _reflect(client, session_id: str, **kw) -> object:
    return await client.post(f"/api/sessions/{session_id}/reflect", json=kw)


class TestReflection:
    async def test_reflecting_on_a_finished_session_saves_both_fields(self, auth_client):
        session = await _start(auth_client)
        await _finish(auth_client, session["id"])

        resp = await _reflect(
            auth_client,
            session["id"],
            distraction="phone notifications",
            next_time_plan="put it in another room",
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["distraction"] == "phone notifications"
        assert body["next_time_plan"] == "put it in another room"

    async def test_reflecting_on_an_open_session_is_rejected(self, auth_client):
        session = await _start(auth_client)
        resp = await _reflect(auth_client, session["id"], distraction="x")
        assert resp.status_code == 400, resp.text

    async def test_both_fields_are_optional(self, auth_client):
        session = await _start(auth_client)
        await _finish(auth_client, session["id"])

        resp = await _reflect(auth_client, session["id"])
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["distraction"] is None
        assert body["next_time_plan"] is None

    async def test_blank_text_clears_rather_than_being_stored(self, auth_client):
        session = await _start(auth_client)
        await _finish(auth_client, session["id"])
        await _reflect(auth_client, session["id"], distraction="  ")

        recent = (await auth_client.get("/api/sessions/bank")).json()["recent"]
        this_one = next(s for s in recent if s["id"] == session["id"])
        assert this_one["distraction"] is None

    async def test_a_stranger_cannot_reflect_on_someone_elses_session(self, auth_client, client):
        session = await _start(auth_client)
        await _finish(auth_client, session["id"])

        stranger = await client.post(
            "/api/auth/register",
            json={"email": "stranger-reflect@example.com", "password": "hunter2hunter2"},
        )
        assert stranger.status_code == 201, stranger.text
        stranger_headers = {"Authorization": f"Bearer {stranger.json()['access_token']}"}

        resp = await client.post(
            f"/api/sessions/{session['id']}/reflect",
            json={"distraction": "nope"},
            headers=stranger_headers,
        )
        assert resp.status_code == 404, resp.text
