"""Request ID + JSON structured request logging (P7)."""
from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from backend.observability.context import set_request_id, set_user
from backend.observability.events import log_event
from backend.observability.registry import domain_metrics
from ids_config import load_config

logger = logging.getLogger("aegis.api")


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"
        request.state.request_id = request_id
        set_request_id(request_id)
        user = getattr(request.state, "username", None) or getattr(request.state, "user", None)
        if user:
            set_user(str(user))
        start = time.perf_counter()
        response: Response | None = None
        err: str | None = None
        error_code: str | None = None
        try:
            response = await call_next(request)
            # Auth middleware may set identity after dispatch starts; re-read
            user = getattr(request.state, "username", None) or getattr(request.state, "role", None)
            if user:
                set_user(str(user))
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as exc:  # noqa: BLE001
            err = type(exc).__name__
            error_code = getattr(exc, "code", None) or type(exc).__name__
            raise
        finally:
            ms = (time.perf_counter() - start) * 1000
            status = response.status_code if response is not None else 500
            domain_metrics.incr("api.requests_total")
            if status >= 400:
                domain_metrics.incr("api.request_errors_total")
            log_event(
                "http_request",
                level="error" if status >= 500 else "info",
                endpoint=request.url.path,
                method=request.method,
                status=status,
                duration_ms=ms,
                error_code=error_code,
                client=request.client.host if request.client else None,
                exception=err,
            )


def attach_request_logging(app) -> None:
    cfg = load_config().get("observability") or {}
    level_name = str(os.getenv("AEGIS_LOG_LEVEL") or cfg.get("log_level") or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        force=True,
    )
    app.add_middleware(StructuredLoggingMiddleware)
