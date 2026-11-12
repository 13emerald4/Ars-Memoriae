import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from starlette.testclient import TestClient

from app.core.security import create_access_token
from app.main import app
from app.models import Card, Deck, Note, NoteType, User
from app.services.sync_service import sync_manager


@pytest.mark.anyio
async def test_sync_status(auth_client):
    resp = await auth_client.get("/api/sync/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "lan_ip" in data
    assert "pairing_url" in data
    assert data["port"] == 8000
    assert "active_connections" in data
    assert "server_time" in data


@pytest.mark.anyio
async def test_batch_sync_reviews(auth_client):
    # First, fetch decks to find a card
    decks_resp = await auth_client.get("/api/decks")
    assert decks_resp.status_code == 200
    decks = decks_resp.json()
    deck_id = decks[0]["id"]

    # Create a note & card
    note_resp = await auth_client.post(
        "/api/notes",
        json={
            "deck_id": deck_id,
            "field_values": {"front": "Capital of France?", "back": "Paris"},
        },
    )
    assert note_resp.status_code == 201
    card_id = note_resp.json()["cards"][0]["id"]

    # Submit batch review
    batch_payload = {
        "reviews": [
            {
                "card_id": card_id,
                "final_grade": "good",
                "typed_answer": "Paris",
                "latency_ms": 1200,
                "confidence": 4,
                "is_blitz": False,
                "reviewed_at": datetime.now(UTC).isoformat(),
            }
        ]
    }
    sync_resp = await auth_client.post("/api/sync/batch", json=batch_payload)
    assert sync_resp.status_code == 200
    res = sync_resp.json()
    assert res["synced_count"] == 1
    assert len(res["failed_items"]) == 0

    # Verify card updated in database via analytics endpoint
    card_resp = await auth_client.get(f"/api/cards/{card_id}/analytics")
    assert card_resp.status_code == 200
    card_data = card_resp.json()
    assert card_data["card"]["state"] in ("learning", "review")
    assert card_data["card"]["stability"] is not None
    assert len(card_data["review_logs"]) >= 1


from starlette.websockets import WebSocketDisconnect


def test_websocket_sync_authentication():
    client = TestClient(app)
    # A socket that connects without identifying itself is closed with a
    # policy violation (1008) as soon as its first frame is not a valid AUTH.
    with client.websocket_connect("/api/sync/ws") as ws:
        ws.send_json({"type": "PING"})
        with pytest.raises(WebSocketDisconnect) as exc_info:
            ws.receive_json()
    assert exc_info.value.code == 1008

    # Generating a valid token for a dummy user id that doesn't exist in DB
    fake_token = create_access_token(str(uuid.uuid4()))
    with (
        pytest.raises(WebSocketDisconnect) as exc_info,
        client.websocket_connect(f"/api/sync/ws?token={fake_token}"),
    ):
        pass
    assert exc_info.value.code == 1008


@pytest.mark.anyio
async def test_websocket_sync_authenticated_communication(auth_client):
    from app.db import SessionLocal

    async with SessionLocal() as db:
        user = (await db.scalars(select(User))).first()
        assert user is not None
        user_token = create_access_token(str(user.id))

    client = TestClient(app)
    with client.websocket_connect(f"/api/sync/ws?token={user_token}") as ws:
        # First frame is the CONNECTED greeting
        greeting = ws.receive_json()
        assert greeting["type"] == "CONNECTED"
        assert greeting["data"]["user_id"] == str(user.id)

        # Ping-pong round trip
        ws.send_json({"type": "PING"})
        pong = ws.receive_json()
        assert pong["type"] == "PONG"
        assert "timestamp" in pong["data"]
