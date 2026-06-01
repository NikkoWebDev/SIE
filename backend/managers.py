from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger("siee.managers")


class EcosystemSocketManager:
    def __init__(self) -> None:
        self.active_connections: dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def register(self, user_id: str, ws: WebSocket) -> None:
        async with self._lock:
            self.active_connections[user_id] = ws
        logger.debug("ws+ %s (total=%d)", user_id, len(self.active_connections))

    async def unregister(self, user_id: str) -> None:
        async with self._lock:
            ws = self.active_connections.pop(user_id, None)
        if ws:
            try:
                await ws.close()
            except Exception as e:
                logger.debug("ws close error for %s: %s", user_id, e)
        logger.debug("ws- %s (total=%d)", user_id, len(self.active_connections))

    async def send(self, user_id: str, payload: dict[str, Any]) -> bool:
        async with self._lock:
            ws = self.active_connections.get(user_id)
        if ws is None:
            return False
        try:
            await ws.send_json(payload)
            return True
        except Exception:
            await self.unregister(user_id)
            return False

    async def broadcast(self, payload: dict[str, Any]) -> int:
        async with self._lock:
            snapshot = list(self.active_connections.items())
        sent = 0
        for uid, ws in snapshot:
            try:
                await ws.send_json(payload)
                sent += 1
            except Exception:
                await self.unregister(uid)
        return sent

    @property
    def count(self) -> int:
        return len(self.active_connections)


ws_manager = EcosystemSocketManager()
