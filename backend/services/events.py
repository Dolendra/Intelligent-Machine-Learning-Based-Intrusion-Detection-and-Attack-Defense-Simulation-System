"""In-process pub/sub hub for dashboard WebSocket refresh."""
from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import WebSocket


class EventHub:
    def __init__(self) -> None:
        self._clients: list[WebSocket] = []
        self._lock: asyncio.Lock | None = None
        # Event loop that serves the WebSockets; sync handlers run in worker threads and must
        # hand broadcasts to this loop (they have no running loop of their own).
        self.loop: asyncio.AbstractEventLoop | None = None

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def connect(self, ws: WebSocket) -> None:
        self.loop = asyncio.get_running_loop()
        await ws.accept()
        async with self._get_lock():
            self._clients.append(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._get_lock():
            if ws in self._clients:
                self._clients.remove(ws)

    async def broadcast(self, event: dict[str, Any]) -> None:
        if not self._clients:
            return
        payload = json.dumps(event)
        async with self._get_lock():
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
    if not event_hub._clients:
        return
    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is not None:  # called from async code on the server loop
            loop.create_task(event_hub.broadcast(event))
            return
        # Called from a sync handler (FastAPI worker thread): schedule on the WebSocket loop.
        if event_hub.loop is not None and event_hub.loop.is_running():
            asyncio.run_coroutine_threadsafe(event_hub.broadcast(event), event_hub.loop)
    except Exception:
        pass
