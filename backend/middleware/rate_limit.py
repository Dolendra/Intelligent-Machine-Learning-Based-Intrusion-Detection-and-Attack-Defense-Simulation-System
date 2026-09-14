"""Simple in-process rate limiting for selected API routes (demo-safe)."""
from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ids_config import load_config


class SimpleRateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window limiter keyed by client host. Disabled when enabled=false."""

    def __init__(self, app, *, enabled: bool, limit: int, window_seconds: int, paths: list[str]):
        super().__init__(app)
        self.enabled = enabled
        self.limit = max(1, limit)
        self.window = max(1, window_seconds)
        self.paths = tuple(paths)
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _match(self, path: str) -> bool:
        return any(path.startswith(p) for p in self.paths)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.enabled or request.method == "OPTIONS" or not self._match(request.url.path):
            return await call_next(request)

        # Allow CI/demo bypass
        if os.getenv("DISABLE_RATE_LIMIT", "").lower() in {"1", "true", "yes"}:
            return await call_next(request)

        client = request.client.host if request.client else "unknown"
        key = f"{client}:{request.url.path}"
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > self.window:
                q.popleft()
            if len(q) >= self.limit:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": {
                            "code": "RATE_LIMITED",
                            "message": f"Too many requests (limit {self.limit}/{self.window}s)",
                        }
                    },
                )
            q.append(now)
        return await call_next(request)


def attach_rate_limit(app) -> None:
    cfg = load_config().get("api", {}).get("rate_limit", {})
    enabled = bool(cfg.get("enabled", False))
    app.add_middleware(
        SimpleRateLimitMiddleware,
        enabled=enabled,
        limit=int(cfg.get("requests_per_window", 100)),
        window_seconds=int(cfg.get("window_seconds", 60)),
        paths=list(
            cfg.get(
                "paths",
                [
                    "/api/predict",
                    "/api/ingest",
                    "/api/explain",
                    "/api/recommendation",
                    "/api/response",
                    "/api/simulation",
                ],
            )
        ),
    )
