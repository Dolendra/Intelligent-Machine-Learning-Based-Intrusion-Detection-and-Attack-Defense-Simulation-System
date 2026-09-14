"""Standardized API error responses with request IDs (no stack/secret leakage)."""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("aegis.api.errors")


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID") or "-"


def _envelope(code: str, message: str, request_id: str, extra: dict | None = None) -> dict:
    body = {"code": code, "message": message, "request_id": request_id}
    if extra:
        body.update(extra)
    return {"detail": body}


def _sanitize_validation_errors(errors: list) -> list[dict]:
    """Drop raw input values that may contain secrets or huge payloads."""
    safe: list[dict] = []
    for err in errors:
        if not isinstance(err, dict):
            continue
        safe.append(
            {
                "type": err.get("type"),
                "loc": err.get("loc"),
                "msg": err.get("msg"),
            }
        )
    return safe


def attach_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exc_handler(request: Request, exc: HTTPException):
        rid = _request_id(request)
        detail = exc.detail
        if isinstance(detail, dict) and "code" in detail:
            # Never echo nested exception objects / traces
            cleaned = {k: v for k, v in detail.items() if k not in {"exc", "exception", "traceback"}}
            payload = {"detail": {**cleaned, "request_id": cleaned.get("request_id") or rid}}
        elif isinstance(detail, dict):
            payload = _envelope(
                str(detail.get("code") or "HTTP_ERROR"),
                str(detail.get("message") or "Request failed"),
                rid,
                {k: v for k, v in detail.items() if k not in {"code", "message", "exc", "traceback"}},
            )
        else:
            payload = _envelope("HTTP_ERROR", str(detail), rid)
        return JSONResponse(status_code=exc.status_code, content=payload, headers={"X-Request-ID": rid})

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        rid = _request_id(request)
        return JSONResponse(
            status_code=422,
            content=_envelope(
                "VALIDATION_ERROR",
                "Request validation failed",
                rid,
                {"errors": _sanitize_validation_errors(exc.errors())},
            ),
            headers={"X-Request-ID": rid},
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception):
        rid = _request_id(request)
        # Log full detail server-side only
        logger.exception("unhandled request_id=%s path=%s", rid, request.url.path)
        expose = os.getenv("AEGIS_EXPOSE_ERRORS", "").lower() in {"1", "true", "yes"}
        message = f"{type(exc).__name__}: {exc}" if expose else "Unexpected server error"
        return JSONResponse(
            status_code=500,
            content=_envelope("INTERNAL_ERROR", message, rid),
            headers={"X-Request-ID": rid},
        )
