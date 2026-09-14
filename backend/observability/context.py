"""Correlation context via contextvars (request/job/incident/action)."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator

_request_id: ContextVar[str | None] = ContextVar("aegis_request_id", default=None)
_job_id: ContextVar[str | None] = ContextVar("aegis_job_id", default=None)
_incident_id: ContextVar[str | None] = ContextVar("aegis_incident_id", default=None)
_action_id: ContextVar[str | None] = ContextVar("aegis_action_id", default=None)
_user: ContextVar[str | None] = ContextVar("aegis_user", default=None)


def get_correlation() -> dict[str, str | None]:
    return {
        "request_id": _request_id.get(),
        "job_id": _job_id.get(),
        "incident_id": _incident_id.get(),
        "action_id": _action_id.get(),
        "user": _user.get(),
    }


def set_request_id(value: str | None) -> None:
    _request_id.set(value)


def set_user(value: str | None) -> None:
    _user.set(value)


@contextmanager
def bind_correlation(**kwargs: Any) -> Iterator[None]:
    tokens = []
    mapping = {
        "request_id": _request_id,
        "job_id": _job_id,
        "incident_id": _incident_id,
        "action_id": _action_id,
        "user": _user,
    }
    try:
        for key, var in mapping.items():
            if key in kwargs and kwargs[key] is not None:
                tokens.append((var, var.set(str(kwargs[key]))))
        yield
    finally:
        for var, token in reversed(tokens):
            var.reset(token)
