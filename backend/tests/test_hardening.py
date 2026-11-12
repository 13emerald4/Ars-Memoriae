"""Regression tests for the security and consistency hardening pass.

Each block pins one property that was missing before: graph endpoints leaking
across accounts, tokens that could not be revoked, code execution reachable
from anywhere, a second review path that scheduled differently, and so on.
"""

from __future__ import annotations

import io
import subprocess
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import func, select
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core import login_throttle
from app.core.config import settings
from app.core.security import SCOPE_MOBILE, decode_token
from app.db import SessionLocal
from app.main import app
from app.models import Card, ReviewLog

BACKEND_DIR = Path(__file__).resolve().parents[1]

PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


async def _register(client, password: str = "password123") -> tuple[dict, str]:
    email = f"u{uuid.uuid4().hex[:10]}@example.com"
    resp = await client.post("/api/auth/register", json={"email": email, "password": password})
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}, email


async def _card(client, headers: dict, front: str = "front", back: str = "back") -> str:
    deck = (await client.post("/api/decks", json={"name": f"d-{uuid.uuid4().hex[:6]}"}, headers=headers)).json()
    note = await client.post(
        "/api/notes",
        headers=headers,
        json={
            "deck_id": deck["id"],
            "template_kind": "basic",
            "field_values": {"Front": front, "Back": back},
        },
    )
    assert note.status_code == 201, note.text
    return note.json()["cards"][0]["id"]


async def _log_count(card_id: str) -> int:
    async with SessionLocal() as db:
        return await db.scalar(
            select(func.count(ReviewLog.id)).where(ReviewLog.card_id == uuid.UUID(card_id))
        )


# ── tenant isolation on the graph endpoints ─────────────────────────────────


async def test_graph_never_reveals_another_accounts_card(client):
    owner, _ = await _register(client)
    other, _ = await _register(client)
    secret = await _card(client, owner, front="OWNER-ONLY what is the vault code")
    mine = await _card(client, other, front="mine")

    # Reading it directly answers like a card that does not exist.
    direct = await client.get(f"/api/graph/related/{secret}", headers=other)
    assert direct.status_code == 404
    assert "OWNER-ONLY" not in direct.text

    # Nor can an edge be drawn to it in either direction.
    for src, tgt in ((mine, secret), (secret, mine)):
        edge = await client.post(
            "/api/graph/edges",
            headers=other,
            json={"source_card_id": src, "target_card_id": tgt},
        )
        assert edge.status_code == 404

    related = await client.get(f"/api/graph/related/{mine}", headers=other)
    assert related.status_code == 200
    assert "OWNER-ONLY" not in related.text

    # The owner still sees their own card.
    assert (await client.get(f"/api/graph/related/{secret}", headers=owner)).status_code == 200


# ── token revocation, password change, pairing tokens ───────────────────────


async def test_sign_out_everywhere_revokes_earlier_tokens(client):
    old, _ = await _register(client)
    assert (await client.get("/api/me", headers=old)).status_code == 200

    resp = await client.post("/api/auth/logout-all", headers=old)
    assert resp.status_code == 200
    new = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    assert (await client.get("/api/me", headers=old)).status_code == 401
    assert (await client.get("/api/me", headers=new)).status_code == 200


async def test_change_password(client):
    login_throttle.reset()
    old, email = await _register(client, password="first-password")

    wrong = await client.post(
        "/api/auth/change-password",
        headers=old,
        json={"current_password": "not-it", "new_password": "second-password"},
    )
    assert wrong.status_code == 400

    ok = await client.post(
        "/api/auth/change-password",
        headers=old,
        json={"current_password": "first-password", "new_password": "second-password"},
    )
    assert ok.status_code == 200
    new = {"Authorization": f"Bearer {ok.json()['access_token']}"}

    # The session that changed it carries on; every older token is dead.
    assert (await client.get("/api/me", headers=new)).status_code == 200
    assert (await client.get("/api/me", headers=old)).status_code == 401

    stale = await client.post("/api/auth/login", json={"email": email, "password": "first-password"})
    assert stale.status_code == 401
    fresh = await client.post("/api/auth/login", json={"email": email, "password": "second-password"})
    assert fresh.status_code == 200
    login_throttle.reset()


async def test_pairing_token_can_review_but_not_escalate(client):
    full, _ = await _register(client)
    card = await _card(client, full)

    resp = await client.post("/api/auth/pairing-token", headers=full)
    assert resp.status_code == 200
    body = resp.json()
    claims = decode_token(body["access_token"])
    assert claims is not None and claims.scope == SCOPE_MOBILE
    assert body["scope"] == SCOPE_MOBILE
    mobile = {"Authorization": f"Bearer {body['access_token']}"}

    # It is a working login for studying...
    assert (await client.get("/api/me", headers=mobile)).status_code == 200
    confirm = await client.post(
        f"/api/review/{card}/confirm", headers=mobile, json={"final_grade": "good"}
    )
    assert confirm.status_code == 200

    # ...but it cannot run code on the host,
    run = await client.post(
        f"/api/review/{card}/run-code", headers=mobile, json={"code": "print(1)", "language": "python"}
    )
    assert run.status_code == 403

    # or touch the account.
    assert (await client.post("/api/auth/pairing-token", headers=mobile)).status_code == 403
    assert (await client.post("/api/auth/logout-all", headers=mobile)).status_code == 403
    changed = await client.post(
        "/api/auth/change-password",
        headers=mobile,
        json={"current_password": "password123", "new_password": "another-password"},
    )
    assert changed.status_code == 403

    # Revoking from the browser unpairs the phone.
    await client.post("/api/auth/logout-all", headers=full)
    assert (await client.get("/api/me", headers=mobile)).status_code == 401


async def test_passwords_have_a_length_ceiling(client):
    resp = await client.post(
        "/api/auth/register",
        json={"email": f"long{uuid.uuid4().hex[:6]}@example.com", "password": "x" * 5000},
    )
    assert resp.status_code == 422


async def test_registration_status_reflects_the_gate(client, monkeypatch):
    await _register(client)  # at least one account exists
    monkeypatch.setattr(settings, "allow_registration", True)
    assert (await client.get("/api/auth/registration-status")).json() == {"open": True}
    monkeypatch.setattr(settings, "allow_registration", False)
    assert (await client.get("/api/auth/registration-status")).json() == {"open": False}


# ── code execution is for the machine the app runs on ───────────────────────

RUN_BODY = {
    "code": "def add(a, b):\n    return a + b\n",
    "language": "python",
    "custom_test_cases": [{"input": {"a": 1, "b": 2}, "expected": 3}],
}


async def test_code_runs_locally_but_not_through_a_proxy(client, monkeypatch):
    monkeypatch.setattr(settings, "allow_remote_code_execution", False)
    headers, _ = await _register(client)
    card = await _card(client, headers)
    url = f"/api/review/{card}/run-code"

    local = await client.post(url, headers=headers, json=RUN_BODY)
    assert local.status_code == 200, local.text

    # A local dev proxy forwarding a local browser is still local.
    proxied_local = await client.post(
        url, headers={**headers, "X-Forwarded-For": "127.0.0.1"}, json=RUN_BODY
    )
    assert proxied_local.status_code == 200

    for forwarded in (
        {"X-Forwarded-For": "203.0.113.7"},
        {"CF-Connecting-IP": "203.0.113.7"},
        # A client-supplied first hop must not vouch for the real one behind it.
        {"X-Forwarded-For": "127.0.0.1, 203.0.113.7"},
        {"Forwarded": "for=203.0.113.7"},
        # A tunnel that adds no forwarding header still passes on the public
        # name the browser used.
        {"Host": "quiet-river.trycloudflare.com"},
        {"X-Forwarded-Host": "192.168.1.20:5173"},
    ):
        remote = await client.post(url, headers={**headers, **forwarded}, json=RUN_BODY)
        assert remote.status_code == 403, forwarded
        assert "ALLOW_REMOTE_CODE_EXECUTION" in remote.json()["detail"]


async def test_operator_can_opt_in_to_remote_code_execution(client, monkeypatch):
    monkeypatch.setattr(settings, "allow_remote_code_execution", True)
    headers, _ = await _register(client)
    card = await _card(client, headers)
    remote = await client.post(
        f"/api/review/{card}/run-code",
        headers={**headers, "CF-Connecting-IP": "203.0.113.7"},
        json=RUN_BODY,
    )
    assert remote.status_code == 200


async def test_code_lab_run_and_submit_are_gated_too(client, monkeypatch):
    monkeypatch.setattr(settings, "allow_remote_code_execution", False)
    headers, _ = await _register(client)
    problems = (await client.get("/api/code/problems", headers=headers)).json()
    if not problems:
        pytest.skip("no seeded code problems")
    slug = problems[0].get("slug") or problems[0]["id"]
    remote = {**headers, "CF-Connecting-IP": "203.0.113.7"}
    for action in ("run", "submit"):
        resp = await client.post(
            f"/api/code/problems/{slug}/{action}",
            headers=remote,
            json={"code": "pass", "language": "python"},
        )
        assert resp.status_code == 403, action


# ── one review path ─────────────────────────────────────────────────────────


async def test_resending_a_confirm_records_one_review(client):
    headers, _ = await _register(client)
    card = await _card(client, headers)
    body = {"final_grade": "good", "client_review_id": uuid.uuid4().hex}

    first = await client.post(f"/api/review/{card}/confirm", headers=headers, json=body)
    again = await client.post(f"/api/review/{card}/confirm", headers=headers, json=body)
    assert first.status_code == again.status_code == 200
    assert first.json() == again.json()
    assert await _log_count(card) == 1

    # A new attempt at the same card is a new review.
    body["client_review_id"] = uuid.uuid4().hex
    assert (await client.post(f"/api/review/{card}/confirm", headers=headers, json=body)).status_code == 200
    assert await _log_count(card) == 2


async def test_offline_batch_uses_the_same_scheduling_as_confirm(client):
    headers, _ = await _register(client)
    desk = await _card(client, headers)
    phone = await _card(client, headers)

    confirmed = await client.post(f"/api/review/{desk}/confirm", headers=headers, json={"final_grade": "good"})
    assert confirmed.status_code == 200

    batch = await client.post(
        "/api/sync/batch",
        headers=headers,
        json={"reviews": [{"card_id": phone, "final_grade": "good", "reviewed_at": datetime.now(UTC).isoformat()}]},
    )
    assert batch.json() == {"synced_count": 1, "failed_items": []}

    async with SessionLocal() as db:
        a = await db.get(Card, uuid.UUID(desk))
        b = await db.get(Card, uuid.UUID(phone))
        # Same grade on a fresh card, by either route: same state and the same
        # bookkeeping (the batch used to skip the weakness history entirely).
        assert a.state == b.state
        assert a.stability == pytest.approx(b.stability)
        assert a.difficulty == pytest.approx(b.difficulty)
        assert len(a.weakness_history or []) == len(b.weakness_history or []) == 1


async def test_offline_batch_rejects_bad_clocks_and_stale_reviews(client):
    headers, _ = await _register(client)
    card = await _card(client, headers)
    now = datetime.now(UTC)

    future = await client.post(
        "/api/sync/batch",
        headers=headers,
        json={"reviews": [{"card_id": card, "final_grade": "good", "reviewed_at": (now + timedelta(days=400)).isoformat()}]},
    )
    assert future.json()["synced_count"] == 0
    assert "future" in future.json()["failed_items"][0]["error"]
    assert await _log_count(card) == 0

    # Reviewed on the desktop just now; an older offline answer must not be
    # replayed over it.
    await client.post(f"/api/review/{card}/confirm", headers=headers, json={"final_grade": "good"})
    stale = await client.post(
        "/api/sync/batch",
        headers=headers,
        json={"reviews": [{"card_id": card, "final_grade": "again", "reviewed_at": (now - timedelta(hours=3)).isoformat()}]},
    )
    assert stale.json()["synced_count"] == 0
    assert "superseded" in stale.json()["failed_items"][0]["error"]
    assert await _log_count(card) == 1


async def test_offline_batch_is_bounded_and_isolated(client):
    headers, _ = await _register(client)
    other, _ = await _register(client)
    mine = await _card(client, headers)
    theirs = await _card(client, other)

    too_many = await client.post(
        "/api/sync/batch",
        headers=headers,
        json={"reviews": [{"card_id": mine, "final_grade": "good"}] * 501},
    )
    assert too_many.status_code == 422

    mixed = await client.post(
        "/api/sync/batch",
        headers=headers,
        json={
            "reviews": [
                {"card_id": theirs, "final_grade": "good"},
                {"card_id": "not-a-uuid", "final_grade": "good"},
                {"card_id": mine, "final_grade": "good"},
            ]
        },
    )
    data = mixed.json()
    assert data["synced_count"] == 1
    assert {f["error"] for f in data["failed_items"]} == {"card not found", "invalid card id"}
    assert await _log_count(theirs) == 0


# ── websocket: token in the first frame, not the URL ────────────────────────


async def test_websocket_authenticates_with_a_first_frame(client):
    headers, _ = await _register(client)
    token = headers["Authorization"].split(" ", 1)[1]
    me = (await client.get("/api/me", headers=headers)).json()

    ws_client = TestClient(app)
    with ws_client.websocket_connect("/api/sync/ws") as ws:
        ws.send_json({"type": "AUTH", "token": token})
        greeting = ws.receive_json()
        assert greeting["type"] == "CONNECTED"
        assert greeting["data"]["user_id"] == me["id"]
        ws.send_json({"type": "PING"})
        assert ws.receive_json()["type"] == "PONG"

    for first_frame in ({"type": "PING"}, {"type": "AUTH", "token": "garbage"}):
        with ws_client.websocket_connect("/api/sync/ws") as ws:
            ws.send_json(first_frame)
            with pytest.raises(WebSocketDisconnect) as closed:
                ws.receive_json()
            assert closed.value.code == 1008


async def test_websocket_rejects_a_revoked_token(client):
    headers, _ = await _register(client)
    token = headers["Authorization"].split(" ", 1)[1]
    await client.post("/api/auth/logout-all", headers=headers)

    with (
        pytest.raises(WebSocketDisconnect) as closed,
        TestClient(app).websocket_connect(f"/api/sync/ws?token={token}"),
    ):
        pass
    assert closed.value.code == 1008


# ── uploads, headers, routing, throttle ─────────────────────────────────────


async def test_upload_type_is_decided_by_content_not_by_the_label(client):
    headers, _ = await _register(client)
    disguised = await client.post(
        "/api/media",
        headers=headers,
        files={"file": ("pic.png", io.BytesIO(b"<html><script>alert(1)</script></html>"), "image/png")},
    )
    assert disguised.status_code == 415

    # A real PNG is accepted whatever the client calls it, and stored as .png.
    mislabeled = await client.post(
        "/api/media",
        headers=headers,
        files={"file": ("pic.bin", io.BytesIO(PNG), "application/octet-stream")},
    )
    assert mislabeled.status_code == 201
    assert mislabeled.json()["url"].endswith(".png")


async def test_media_quota(client, monkeypatch):
    headers, _ = await _register(client)
    monkeypatch.setattr(settings, "media_quota_mb", 1)
    big_png = PNG + b"\x00" * (700 * 1024)
    first = await client.post("/api/media", headers=headers, files={"file": ("a.png", io.BytesIO(big_png), "image/png")})
    assert first.status_code == 201
    second = await client.post("/api/media", headers=headers, files={"file": ("b.png", io.BytesIO(big_png), "image/png")})
    assert second.status_code == 413
    assert "storage is full" in second.json()["detail"]


async def test_security_headers_and_spa_route_matching(client):
    resp = await client.get("/health")
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"

    # Unknown API paths are a JSON 404, never the SPA shell.
    assert (await client.get("/api/does-not-exist")).json() == {"detail": "Not Found"}
    # A client route that merely starts with "api" is not an API path.
    assert (await client.get("/apiary")).text != '{"detail":"Not Found"}'


async def test_login_lockout_survives_a_rotating_address(client):
    login_throttle.reset()
    _, email = await _register(client)
    statuses = []
    for i in range(login_throttle.EMAIL_FREE_ATTEMPTS + 1):
        resp = await client.post(
            "/api/auth/login",
            json={"email": email, "password": "wrong-password"},
            # A different "client address" every time dodges the per-address count.
            headers={"CF-Connecting-IP": f"198.51.100.{i % 250}"},
        )
        statuses.append(resp.status_code)
    assert statuses[0] == 401
    assert statuses[-1] == 429
    login_throttle.reset()


# ── migrations ──────────────────────────────────────────────────────────────

_MIGRATION_PROBE = """
import asyncio, logging, sys
logging.getLogger("uvicorn.error")
logging.getLogger("app.probe")
logging.getLogger().setLevel(logging.INFO)

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy.ext.asyncio import create_async_engine

from app import models  # noqa: F401
from app.core.config import settings
from app.db import Base

cfg = Config("alembic.ini")
cfg.attributes["configure_logger"] = False
command.upgrade(cfg, "head")

silenced = [n for n in ("uvicorn.error", "app.probe") if logging.getLogger(n).disabled]
root_level = logging.getLogger().level

async def drift():
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as conn:
        # Tables, columns and indexes. Column *types* are left out: several
        # migrations declare VARCHAR(n) where the model says Text, which is the
        # same thing to SQLite and not what this test is guarding.
        found = await conn.run_sync(
            lambda c: compare_metadata(
                MigrationContext.configure(c, opts={"compare_type": False}), Base.metadata
            )
        )
    await engine.dispose()
    return found

found = asyncio.run(drift())
print("SILENCED", silenced)
print("ROOT_INFO", root_level == logging.INFO)
print("DRIFT", [str(d)[:160] for d in found])
"""


def test_migrations_build_the_schema_the_models_describe(tmp_path):
    """Upgrades an empty database to head, then diffs it against the ORM.

    The rest of the suite builds its schema from the models, so without this
    nothing runs the migrations a real install depends on. It also pins that
    migrating in-process leaves the server's logging alone.
    """
    env = {
        "PATH": __import__("os").environ.get("PATH", ""),
        "DATABASE_URL": f"sqlite+aiosqlite:///{(tmp_path / 'migrated.db').as_posix()}",
        "SECRET_KEY": "migration-test-key",
        "ENABLE_BACKGROUND_JOBS": "0",
    }
    proc = subprocess.run(
        [sys.executable, "-c", _MIGRATION_PROBE],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "SILENCED []" in proc.stdout, proc.stdout
    assert "ROOT_INFO True" in proc.stdout, proc.stdout
    assert "DRIFT []" in proc.stdout, proc.stdout
