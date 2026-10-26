"""Real-time synchronization service and WebSocket connection hub.

Maintains active client connections per user (desktop web, mobile app) and
broadcasts state changes (reviews, queue invalidation, deck mutations, sessions)
so all client instances stay synchronized in real time.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any

from fastapi import WebSocket

log = logging.getLogger(__name__)


class SyncManager:
    def __init__(self) -> None:
        # Maps user_id -> set of active WebSockets
        self._connections: dict[uuid.UUID, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, user_id: uuid.UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            if user_id not in self._connections:
                self._connections[user_id] = set()
            self._connections[user_id].add(websocket)
        log.info("WebSocket connected for user %s (total: %d)", user_id, len(self._connections[user_id]))

    async def disconnect(self, user_id: uuid.UUID, websocket: WebSocket) -> None:
        async with self._lock:
            user_sockets = self._connections.get(user_id)
            if user_sockets and websocket in user_sockets:
                user_sockets.remove(websocket)
                if not user_sockets:
                    self._connections.pop(user_id, None)
        log.info("WebSocket disconnected for user %s", user_id)

    async def broadcast_to_user(
        self,
        user_id: uuid.UUID,
        event_type: str,
        payload: dict[str, Any],
    ) -> int:
        """Broadcasts an event message to all active sockets belonging to user_id."""
        message_str = json.dumps({
            "type": event_type,
            "data": payload,
        })
        async with self._lock:
            sockets = list(self._connections.get(user_id, set()))

        if not sockets:
            return 0

        stale: list[WebSocket] = []
        sent_count = 0
        for ws in sockets:
            try:
                await ws.send_text(message_str)
                sent_count += 1
            except Exception as exc:
                log.debug("Failed sending WS to user %s: %s", user_id, exc)
                stale.append(ws)

        if stale:
            async with self._lock:
                current_set = self._connections.get(user_id)
                if current_set:
                    for s in stale:
                        current_set.discard(s)

        return sent_count

    def active_connections_count(self, user_id: uuid.UUID | None = None) -> int:
        if user_id is not None:
            return len(self._connections.get(user_id, set()))
        return sum(len(s) for s in self._connections.values())


sync_manager = SyncManager()
