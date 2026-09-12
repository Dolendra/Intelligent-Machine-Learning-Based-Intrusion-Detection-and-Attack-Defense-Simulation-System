"""Request ID + structured request logging."""
from __future__ import annotations

import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("aegis.api")


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.perf_counter()
        response: Response | None = None
        err: str | None = None
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as exc:  # noqa: BLE001
            err = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            ms = (time.perf_counter() - start) * 1000
            status = response.status_code if response is not None else 500
            logger.info(
                "request_id=%s method=%s path=%s status=%s duration_ms=%.1f client=%s err=%s",
                request_id,
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
