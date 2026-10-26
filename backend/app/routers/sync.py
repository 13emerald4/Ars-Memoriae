"""Real-time synchronization router.

Provides:
- Authenticated WebSocket endpoint (`/api/ws/sync`) for instant desktop <-> mobile state updates.
- Server pairing & network discovery endpoint (`/api/sync/status`).
- Offline batch review ingestion (`/api/sync/batch`).
"""

from __future__ import annotations

import logging
import socket
import uuid
from datetime import UTC, datetime

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decode_access_token
from app.db import get_db
from app.models import Card, Deck, ReviewLog, User
from app.routers.deps import current_user, parse_uuid
from app.schemas.review import Grade
from app.services.fsrs_service import GRADE_TO_RATING, FSRSService
from app.services.sync_service import sync_manager

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sync", tags=["sync"])


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
    confidence: int | None = None
    is_blitz: bool = False
    reviewed_at: datetime | None = None


class BatchSyncRequest(BaseModel):
    reviews: list[BatchReviewItem] = Field(default_factory=list)


class BatchSyncResponse(BaseModel):
    synced_count: int
    failed_items: list[dict[str, str]]


@router.get("/status", response_model=SyncStatusResponse)
async def sync_status(user: User = Depends(current_user)) -> SyncStatusResponse:
    """Returns local network details for 1-click mobile companion pairing."""
    lan_ip = get_lan_ip()
    port = getattr(settings, "port", 8000)
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
    """Ingests reviews recorded while the mobile app was offline."""
    synced_count = 0
    failed_items: list[dict[str, str]] = []

    for item in body.reviews:
        try:
            cid = parse_uuid(item.card_id)
            card = await db.get(Card, cid)
            if not card:
                failed_items.append({"card_id": item.card_id, "error": "card not found"})
                continue
            deck = await db.get(Deck, card.deck_id)
            if not deck or deck.user_id != user.id:
                failed_items.append({"card_id": item.card_id, "error": "card not owned"})
                continue

            review_time = item.reviewed_at or datetime.now(UTC)
            if not review_time.tzinfo:
                review_time = review_time.replace(tzinfo=UTC)

            # Idempotency check: avoid double-logging identical reviews
            existing_log = await db.execute(
                select(ReviewLog.id)
                .where(ReviewLog.card_id == card.id)
                .where(ReviewLog.reviewed_at == review_time)
            )
            if existing_log.scalar_one_or_none():
                continue

            state_before = card.state
            last_review = card.last_review
            elapsed_days = None
            if last_review:
                lr = last_review if last_review.tzinfo else last_review.replace(tzinfo=UTC)
                elapsed_days = (review_time - lr).total_seconds() / 86400.0

            retention = deck.desired_retention_override or user.desired_retention
            fsrs = FSRSService(weights=user.fsrs_parameters, desired_retention=retention)
            fsrs_card = FSRSService.to_fsrs_card(
                state=card.state,
                stability=card.stability,
                difficulty=card.difficulty,
                step=card.step,
                due=card.due,
                last_review=card.last_review,
            )
            _, new_state = fsrs.schedule(
                fsrs_card, GRADE_TO_RATING[item.final_grade.value], review_time
            )

            if item.final_grade == Grade.again and state_before == "review":
                card.lapse_count += 1

            for key, val in new_state.items():
                setattr(card, key, val)

            db.add(
                ReviewLog(
                    card_id=card.id,
                    reviewed_at=review_time,
                    typed_answer=item.typed_answer,
                    latency_ms=item.latency_ms,
                    final_grade=item.final_grade.value,
                    overridden=False,
                    state_before=state_before,
                    elapsed_days=elapsed_days,
                    graduated_to_review=state_before != "review" and new_state.get("state") == "review",
                    user_confidence=item.confidence,
                    is_blitz=item.is_blitz,
                )
            )
            synced_count += 1
        except Exception as exc:
            failed_items.append({"card_id": item.card_id, "error": str(exc)})

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


@router.websocket("/ws")
async def websocket_sync_endpoint(
    websocket: WebSocket,
    token: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Authenticated WebSocket endpoint for real-time mobile <-> desktop synchronization."""
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id_str = decode_access_token(token)
    if not user_id_str:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        user_uuid = uuid.UUID(user_id_str)
        user = await db.get(User, user_uuid)
    except Exception:
        user = None

    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await sync_manager.connect(user.id, websocket)
    try:
        # Initial greeting with server time & connection confirmation
        await websocket.send_json({
            "type": "CONNECTED",
            "data": {
                "user_id": str(user.id),
                "server_time": datetime.now(UTC).isoformat(),
            },
        })
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            if msg_type == "PING":
                await websocket.send_json({
                    "type": "PONG",
                    "data": {"timestamp": datetime.now(UTC).isoformat()},
                })
    except WebSocketDisconnect:
        await sync_manager.disconnect(user.id, websocket)
    except Exception as exc:
        log.warning("WebSocket error for user %s: %s", user.id, exc)
        await sync_manager.disconnect(user.id, websocket)
