"""Simple in-process rate limiting for security-sensitive API routes (P5 default-on)."""
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
from security.security_events import security_event

# Sensitive prefixes — rate-limited by matched prefix (not full path) to reduce bypasses
DEFAULT_PATHS = [
    "/api/auth/login",
    "/api/predict",
    "/api/ingest",
    "/api/explain",
    "/api/recommendation",
    "/api/response",
    "/api/simulation",
]


class SimpleRateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window limiter keyed by client + matched path prefix."""

    def __init__(
        self,
        app,
        *,
        enabled: bool,
        limit: int,
        window_seconds: int,
        paths: list[str],
        path_limits: dict[str, dict] | None = None,
    ):
        super().__init__(app)
        self.enabled = enabled
        self.limit = max(1, limit)
        self.window = max(1, window_seconds)
        # Longest prefix first for stable matching
        self.paths = tuple(sorted(paths, key=len, reverse=True))
        self.path_limits = path_limits or {}
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _match_prefix(self, path: str) -> str | None:
        for p in self.paths:
            if path.startswith(p):
                return p
        return None

    def _limit_for(self, prefix: str) -> tuple[int, int]:
        override = self.path_limits.get(prefix) or {}
        limit = int(override.get("requests_per_window", self.limit))
        window = int(override.get("window_seconds", self.window))
        return max(1, limit), max(1, window)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.enabled or request.method == "OPTIONS":
            return await call_next(request)

        if os.getenv("DISABLE_RATE_LIMIT", "").lower() in {"1", "true", "yes"}:
            return await call_next(request)

        prefix = self._match_prefix(request.url.path)
        if prefix is None:
            return await call_next(request)

        limit, window = self._limit_for(prefix)
        client = request.client.host if request.client else "unknown"
        # Key by prefix (not full path) so /api/predict vs /api/predict/batch share a bucket
        key = f"{client}:{prefix}"
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > window:
                q.popleft()
            if len(q) >= limit:
                rid = getattr(request.state, "request_id", None)
                security_event(
                    "rate_limited",
                    request_id=rid,
                    path=request.url.path,
                    method=request.method,
                    code="RATE_LIMITED",
                    client=client,
                    detail={"prefix": prefix, "limit": limit, "window": window},
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": {
                            "code": "RATE_LIMITED",
                            "message": f"Too many requests (limit {limit}/{window}s)",
                            "prefix": prefix,
                        }
                    },
                    headers={"Retry-After": str(window)},
                )
            q.append(now)
        return await call_next(request)


def attach_rate_limit(app) -> None:
    cfg = load_config().get("api", {}).get("rate_limit", {}) or {}
    enabled_env = os.getenv("AEGIS_RATE_LIMIT_ENABLED")
    if enabled_env is not None:
        enabled = enabled_env.lower() in {"1", "true", "yes"}
    else:
        # P5: default ON for security-sensitive paths
        enabled = bool(cfg.get("enabled", True))
    path_limits = cfg.get("path_limits") if isinstance(cfg.get("path_limits"), dict) else {}
    app.add_middleware(
        SimpleRateLimitMiddleware,
        enabled=enabled,
        limit=int(cfg.get("requests_per_window", 120)),
        window_seconds=int(cfg.get("window_seconds", 60)),
        paths=list(cfg.get("paths") or DEFAULT_PATHS),
        path_limits=path_limits,
    )
