"""Real-time synchronization router.

Provides:
- Authenticated WebSocket endpoint (`/api/sync/ws`) for instant desktop <-> mobile state updates.
- Server pairing & network discovery endpoint (`/api/sync/status`).
- Offline batch review ingestion (`/api/sync/batch`).
"""

from __future__ import annotations

import asyncio
import logging
import socket
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db import SessionLocal, get_db
from app.models import Card, Deck, ReviewLog, User
from app.routers.deps import current_user, parse_uuid, user_for_claims
from app.schemas.review import Grade
from app.services import review_service
from app.services.sync_service import sync_manager

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sync", tags=["sync"])

# One offline session's worth. A phone that somehow queued more sends the rest
# in its next batch.
MAX_BATCH_REVIEWS = 500
# A phone's clock may run a little fast; anything further ahead is a wrong
# clock, and scheduling from it would push the card's next due date with it.
MAX_CLOCK_SKEW = timedelta(minutes=5)
# How long a socket may sit connected without identifying itself.
WS_AUTH_TIMEOUT_SECONDS = 10.0


def get_lan_ip() -> str:
    """Returns the host machine's primary local LAN IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class SyncStatusResponse(BaseModel):
    lan_ip: str
    port: int
    pairing_url: str
    active_connections: int
    user_connections: int
    server_time: datetime


class BatchReviewItem(BaseModel):
    card_id: str
    final_grade: Grade
    typed_answer: str | None = None
    latency_ms: int | None = None
    confidence: int | None = Field(default=None, ge=1, le=4)
    is_blitz: bool = False
    reviewed_at: datetime | None = None


class BatchSyncRequest(BaseModel):
    reviews: list[BatchReviewItem] = Field(default_factory=list, max_length=MAX_BATCH_REVIEWS)


class BatchSyncResponse(BaseModel):
    synced_count: int
    failed_items: list[dict[str, str]]


@router.get("/status", response_model=SyncStatusResponse)
async def sync_status(request: Request, user: User = Depends(current_user)) -> SyncStatusResponse:
    """Returns local network details for 1-click mobile companion pairing."""
    lan_ip = await asyncio.to_thread(get_lan_ip)
    # The port this server is actually answering on, not an assumed 8000.
    server = request.scope.get("server")
    port = int(server[1]) if server and server[1] else 8000
    pairing_url = f"http://{lan_ip}:{port}"
    return SyncStatusResponse(
        lan_ip=lan_ip,
        port=port,
        pairing_url=pairing_url,
        active_connections=sync_manager.active_connections_count(),
        user_connections=sync_manager.active_connections_count(user.id),
        server_time=datetime.now(UTC),
    )


@router.post("/batch", response_model=BatchSyncResponse)
async def sync_batch_reviews(
    body: BatchSyncRequest,
    background: BackgroundTasks,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> BatchSyncResponse:
    """Ingests reviews recorded while the mobile app was offline.

    Each review goes through the same `record_review` as a desktop confirm.
    Reviews are applied oldest first, each in its own savepoint, so one bad
    item is rolled back alone and reported instead of poisoning the batch.
    """
    synced_count = 0
    failed_items: list[dict[str, str]] = []
    now = datetime.now(UTC)

    def _when(item: BatchReviewItem) -> datetime:
        return review_service.aware(item.reviewed_at) if item.reviewed_at else now

    for item in sorted(body.reviews, key=_when):
        review_time = _when(item)

        def fail(reason: str, card_id: str = item.card_id) -> None:
            failed_items.append({"card_id": card_id, "error": reason})

        try:
            cid = parse_uuid(item.card_id)
        except Exception:
            fail("invalid card id")
            continue
        if review_time > now + MAX_CLOCK_SKEW:
            fail("review time is in the future; check the device clock")
            continue

        try:
            async with db.begin_nested():
                card = await db.get(Card, cid)
                deck = await db.get(Deck, card.deck_id) if card else None
                # Missing and not-yours answer alike.
                if card is None or deck is None or deck.user_id != user.id:
                    fail("card not found")
                    continue

                # Idempotency: the same review sent twice is recorded once.
                already = await db.scalar(
                    select(ReviewLog.id)
                    .where(ReviewLog.card_id == card.id)
                    .where(ReviewLog.reviewed_at == review_time)
                    .limit(1)
                )
                if already:
                    continue

                # The card was reviewed elsewhere after this offline answer was
                # given. Replaying it now would schedule backwards in time.
                if card.last_review and review_service.aware(card.last_review) > review_time:
                    fail("superseded by a newer review of this card")
                    continue

                await review_service.record_review(
                    db,
                    user,
                    card,
                    deck,
                    grade=item.final_grade.value,
                    reviewed_at=review_time,
                    typed_answer=item.typed_answer,
                    latency_ms=item.latency_ms,
                    confidence=item.confidence,
                    is_blitz=item.is_blitz,
                )
            synced_count += 1
        except Exception as exc:
            log.warning("Offline review for card %s could not be applied: %s", item.card_id, exc)
            fail("could not be applied")

    if synced_count > 0:
        await db.commit()
        # Broadcast queue invalidation so desktop re-fetches latest queue & stats
        background.add_task(
            sync_manager.broadcast_to_user,
            user.id,
            "QUEUE_INVALIDATED",
            {"synced_count": synced_count, "timestamp": datetime.now(UTC).isoformat()},
        )

    return BatchSyncResponse(synced_count=synced_count, failed_items=failed_items)


async def _user_id_for_token(token: str) -> uuid.UUID | None:
    """Resolves a token to a current user id on its own short-lived session.

    A socket stays open for hours. Holding a request-scoped session for that
    long keeps a transaction (and, on Postgres, a pooled connection) pinned
    per open tab.
    """
    claims = decode_token(token)
    if claims is None:
        return None
    async with SessionLocal() as db:
        user = await user_for_claims(db, claims)
        return user.id if user else None


@router.websocket("/ws")
async def websocket_sync_endpoint(
    websocket: WebSocket,
    token: str | None = Query(None),
) -> None:
    """Authenticated WebSocket endpoint for real-time mobile <-> desktop synchronization.

    A client identifies itself by sending ``{"type": "AUTH", "token": ...}`` as
    its first frame. ``?token=`` in the URL is still accepted for clients that
    predate that, but URLs end up in access logs and a token should not.
    """
    user_id: uuid.UUID | None = None
    if token:
        user_id = await _user_id_for_token(token)
        if user_id is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        await sync_manager.connect(user_id, websocket)
    else:
        await websocket.accept()
        try:
            first = await asyncio.wait_for(
                websocket.receive_json(), timeout=WS_AUTH_TIMEOUT_SECONDS
            )
        except WebSocketDisconnect:
            return
        except Exception:
            first = None
        offered = first.get("token") if isinstance(first, dict) else None
        if isinstance(first, dict) and first.get("type") == "AUTH" and isinstance(offered, str):
            user_id = await _user_id_for_token(offered)
        if user_id is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        await sync_manager.register(user_id, websocket)

    try:
        # Initial greeting with server time & connection confirmation
        await websocket.send_json({
            "type": "CONNECTED",
            "data": {
                "user_id": str(user_id),
                "server_time": datetime.now(UTC).isoformat(),
            },
        })
        while True:
            data = await websocket.receive_json()
            if isinstance(data, dict) and data.get("type") == "PING":
                await websocket.send_json({
                    "type": "PONG",
                    "data": {"timestamp": datetime.now(UTC).isoformat()},
                })
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        log.warning("WebSocket error for user %s: %s", user_id, exc)
    finally:
        await sync_manager.disconnect(user_id, websocket)
