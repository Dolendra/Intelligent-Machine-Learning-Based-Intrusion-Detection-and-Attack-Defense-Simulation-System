"""Standardized API error responses with request IDs."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID") or "-"


def _envelope(code: str, message: str, request_id: str, extra: dict | None = None) -> dict:
    body = {"code": code, "message": message, "request_id": request_id}
    if extra:
        body.update(extra)
    return {"detail": body}


def attach_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exc_handler(request: Request, exc: HTTPException):
        rid = _request_id(request)
        detail = exc.detail
        if isinstance(detail, dict) and "code" in detail:
            payload = {"detail": {**detail, "request_id": detail.get("request_id") or rid}}
        elif isinstance(detail, dict):
            payload = _envelope(
                str(detail.get("code") or "HTTP_ERROR"),
                str(detail.get("message") or detail),
                rid,
                {k: v for k, v in detail.items() if k not in {"code", "message"}},
            )
        else:
            payload = _envelope("HTTP_ERROR", str(detail), rid)
        return JSONResponse(status_code=exc.status_code, content=payload, headers={"X-Request-ID": rid})

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        rid = _request_id(request)
        return JSONResponse(
            status_code=422,
            content=_envelope("VALIDATION_ERROR", "Request validation failed", rid, {"errors": exc.errors()}),
            headers={"X-Request-ID": rid},
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception):
        rid = _request_id(request)
        return JSONResponse(
            status_code=500,
            content=_envelope("INTERNAL_ERROR", "Unexpected server error", rid),
            headers={"X-Request-ID": rid},
        )
