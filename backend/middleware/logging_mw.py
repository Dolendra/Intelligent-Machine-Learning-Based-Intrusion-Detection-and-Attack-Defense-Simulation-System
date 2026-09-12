"""Lightweight structured request logging."""
from __future__ import annotations

import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("aegis.api")


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        response: Response | None = None
        err: str | None = None
        try:
            response = await call_next(request)
            return response
        except Exception as exc:  # noqa: BLE001
            err = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            ms = (time.perf_counter() - start) * 1000
            status = response.status_code if response is not None else 500
            logger.info(
                "method=%s path=%s status=%s duration_ms=%.1f client=%s err=%s",
                request.method,
                request.url.path,
                status,
                ms,
                request.client.host if request.client else "-",
                err or "-",
            )


def attach_request_logging(app) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    app.add_middleware(StructuredLoggingMiddleware)
