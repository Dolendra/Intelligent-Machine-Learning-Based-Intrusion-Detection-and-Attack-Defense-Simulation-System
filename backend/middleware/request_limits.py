"""Request body size limits (P5 DoS / memory protection)."""
from __future__ import annotations

import os
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ids_config import load_config
from security.security_events import security_event


def _limits_from_config() -> dict[str, int]:
    cfg = load_config().get("api", {}).get("request_limits", {}) or {}
    return {
        "default": int(cfg.get("max_body_bytes", 2 * 1024 * 1024)),
        "json": int(cfg.get("max_json_bytes", 1 * 1024 * 1024)),
        "csv": int(cfg.get("max_csv_bytes", 10 * 1024 * 1024)),
        "pcap": int(os.getenv("IDS_PCAP_MAX_BYTES", str(cfg.get("max_pcap_bytes", 25 * 1024 * 1024)))),
        "multipart": int(cfg.get("max_multipart_bytes", 30 * 1024 * 1024)),
    }


def limit_for_path(path: str, content_type: str | None) -> int:
    limits = _limits_from_config()
    ct = (content_type or "").lower()
    # Multipart Content-Length includes framing — never apply the raw PCAP byte cap here.
    # Accurate PCAP size is enforced after read in validate_pcap_upload.
    if "multipart/form-data" in ct or path.startswith("/api/ingest") or "csv" in path or path.endswith("/batch/csv"):
        if path.startswith("/api/ingest/pcap") or path.startswith("/api/ingest/queue/submit-pcap"):
            return limits["multipart"]
        if "csv" in path or path.endswith("/batch/csv"):
            return max(limits["csv"], limits["multipart"])
        return limits["multipart"]
    if "application/json" in ct or path.startswith("/api/"):
        return limits["json"] if "json" in ct or not ct else limits["default"]
    return limits["default"]


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject oversized requests early via Content-Length (when present)."""

    def __init__(self, app, *, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.enabled or request.method in {"GET", "HEAD", "OPTIONS"}:
            return await call_next(request)
        if os.getenv("DISABLE_REQUEST_LIMITS", "").lower() in {"1", "true", "yes"}:
            return await call_next(request)

        cl = request.headers.get("content-length")
        if cl is None:
            return await call_next(request)
        try:
            size = int(cl)
        except ValueError:
            security_event(
                "invalid_content_length",
                path=request.url.path,
                method=request.method,
                code="BAD_CONTENT_LENGTH",
                client=request.client.host if request.client else None,
            )
            return JSONResponse(
                status_code=400,
                content={"detail": {"code": "BAD_CONTENT_LENGTH", "message": "Invalid Content-Length"}},
            )

        limit = limit_for_path(request.url.path, request.headers.get("content-type"))
        if size > limit:
            rid = getattr(request.state, "request_id", None)
            security_event(
                "request_too_large",
                request_id=rid,
                path=request.url.path,
                method=request.method,
                code="REQUEST_TOO_LARGE",
                client=request.client.host if request.client else None,
                detail={"size": size, "limit": limit},
            )
            return JSONResponse(
                status_code=413,
                content={
                    "detail": {
                        "code": "REQUEST_TOO_LARGE",
                        "message": f"Request body exceeds limit ({limit} bytes)",
                        "limit_bytes": limit,
                    }
                },
            )
        return await call_next(request)


def attach_request_limits(app) -> None:
    cfg = load_config().get("api", {}).get("request_limits", {}) or {}
    enabled_env = os.getenv("AEGIS_REQUEST_LIMITS")
    if enabled_env is not None:
        enabled = enabled_env.lower() in {"1", "true", "yes"}
    else:
        enabled = bool(cfg.get("enabled", True))
    app.add_middleware(RequestSizeLimitMiddleware, enabled=enabled)


def request_limits_summary() -> dict:
    limits = _limits_from_config()
    cfg = load_config().get("api", {}).get("request_limits", {}) or {}
    return {
        "enabled": bool(cfg.get("enabled", True)),
        "limits_bytes": limits,
        "notes": [
            "Content-Length checked before handlers when present.",
            "PCAP also validated by magic/extension/size in ingestion.pcap_validation.",
        ],
    }
