"""In-process pub/sub hub for dashboard WebSocket refresh."""
from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import WebSocket


class EventHub:
    def __init__(self) -> None:
        self._clients: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._clients.append(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            if ws in self._clients:
                self._clients.remove(ws)

    async def broadcast(self, event: dict[str, Any]) -> None:
        payload = json.dumps(event)
        async with self._lock:
            clients = list(self._clients)
        dead: list[WebSocket] = []
        for ws in clients:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws)


event_hub = EventHub()


def notify_sync(event: dict[str, Any]) -> None:
    """Best-effort notify from sync request handlers."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(event_hub.broadcast(event))
        else:
            loop.run_until_complete(event_hub.broadcast(event))
    except Exception:
        pass
