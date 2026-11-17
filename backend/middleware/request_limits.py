"""Request body size limits (P5 DoS / memory protection)."""
from __future__ import annotations

from security.auth.posture import kill_switch_allowed
import os

from fastapi import HTTPException
from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

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


class BodyTooLarge(HTTPException):
    """Raised from the wrapped ``receive`` once the streamed body exceeds its limit.

    It subclasses HTTPException on purpose: FastAPI re-raises HTTPException from body/form
    parsing unchanged (other errors become a generic 400), so the client gets a 413.
    """

    def __init__(self, limit: int) -> None:
        super().__init__(
            status_code=413,
            detail={
                "code": "REQUEST_TOO_LARGE",
                "message": f"Request body exceeds limit ({limit} bytes)",
                "limit_bytes": limit,
            },
        )
        self.limit = limit


def _client(scope: Scope) -> str | None:
    client = scope.get("client")
    return client[0] if client else None


def _too_large_event(scope: Scope, limit: int, size: int | None, *, streamed: bool) -> None:
    security_event(
        "request_too_large",
        path=scope.get("path"),
        method=scope.get("method"),
        code="REQUEST_TOO_LARGE",
        client=_client(scope),
        detail={"size": size, "limit": limit, "streamed": streamed},
    )


class RequestSizeLimitMiddleware:
    """Enforce body-size limits on the bytes actually received (R-07, SEC-4).

    * A declared ``Content-Length`` above the limit is rejected before the handler runs.
    * Every body, with or without Content-Length (e.g. ``Transfer-Encoding: chunked``), is
      counted as it streams in; the request fails with 413 as soon as the limit is crossed,
      so at most ``limit`` bytes plus one chunk are ever buffered.
    """

    def __init__(self, app: ASGIApp, *, enabled: bool = True) -> None:
        self.app = app
        self.enabled = enabled

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http"
            or not self.enabled
            or scope.get("method") in {"GET", "HEAD", "OPTIONS"}
            or kill_switch_allowed("DISABLE_REQUEST_LIMITS")
        ):
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        path = scope.get("path", "")
        limit = limit_for_path(path, headers.get("content-type"))

        cl = headers.get("content-length")
        if cl is not None:
            try:
                declared = int(cl)
                if declared < 0:
                    raise ValueError(cl)
            except ValueError:
                security_event("invalid_content_length", path=path, method=scope.get("method"),
                               code="BAD_CONTENT_LENGTH", client=_client(scope))
                await JSONResponse(
                    status_code=400,
                    content={"detail": {"code": "BAD_CONTENT_LENGTH", "message": "Invalid Content-Length"}},
                )(scope, receive, send)
                return
            if declared > limit:
                _too_large_event(scope, limit, declared, streamed=False)
                await JSONResponse(status_code=413, content={"detail": BodyTooLarge(limit).detail})(
                    scope, receive, send)
                return

        received = 0

        async def counted_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    _too_large_event(scope, limit, received, streamed=True)
                    raise BodyTooLarge(limit)
            return message

        await self.app(scope, counted_receive, send)


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
            "Streamed/chunked bodies are counted as received and cut off at the limit (R-07).",
            "PCAP also validated by magic/extension/size in ingestion.pcap_validation.",
        ],
    }
