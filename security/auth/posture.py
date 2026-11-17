"""Security posture checks applied at startup (fail-closed).

Remediation R-05/R-06 (SEC-1, SEC-2, SEC-3, SEC-16, SEC-28).

The deployment environment comes from the ``AEGIS_ENV`` environment variable only.
``config.yaml`` ``observability.environment`` is a logging label and is deliberately
*not* trusted here. If ``AEGIS_ENV`` is unset the environment is treated as
``production``, so a forgotten setting fails closed rather than open.

Outside ``development`` / ``test`` the API refuses to start when:
* authentication is disabled; or
* any security kill switch (``DISABLE_API_AUTH``, ``DISABLE_RATE_LIMIT``,
  ``DISABLE_REQUEST_LIMITS``, ``AEGIS_EXPOSE_ERRORS``, ``AEGIS_ALLOW_ROLE_HEADER``) is on.

Whenever authentication is enabled (any environment), a strong token secret is required
(see :func:`token_secret_problem`).
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

from ids_config import load_config

DEV_ENVIRONMENTS = frozenset({"development", "test"})
KILL_SWITCHES = (
    "DISABLE_API_AUTH",
    "DISABLE_RATE_LIMIT",
    "DISABLE_REQUEST_LIMITS",
    "AEGIS_EXPOSE_ERRORS",
    "AEGIS_ALLOW_ROLE_HEADER",
)
MIN_SECRET_LENGTH = 32

log = logging.getLogger("aegis.security")


class InsecureConfigurationError(RuntimeError):
    """Raised at startup when the configuration would run the API insecurely."""


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def deployment_environment() -> str:
    """``AEGIS_ENV`` (lower-cased); ``production`` when unset."""
    return (os.getenv("AEGIS_ENV") or "production").strip().lower()


def is_dev_environment() -> bool:
    return deployment_environment() in DEV_ENVIRONMENTS


def auth_enabled() -> bool:
    """Effective auth flag: ``AEGIS_AUTH_ENABLED`` overrides ``config.yaml api.auth.enabled``."""
    env = os.getenv("AEGIS_AUTH_ENABLED")
    if env is not None:
        return _truthy(env)
    cfg = load_config().get("api", {}).get("auth", {}) or {}
    return bool(cfg.get("enabled", False))


def active_kill_switches() -> list[str]:
    return [name for name in KILL_SWITCHES if _truthy(os.getenv(name))]


def kill_switch_allowed(name: str) -> bool:
    """A kill switch takes effect only when it is set *and* the environment is dev/test."""
    return _truthy(os.getenv(name)) and is_dev_environment()


def token_secret_problem() -> str | None:
    """Return why the token secret is unacceptable, or None if it is acceptable."""
    secret = os.getenv("AEGIS_AUTH_SECRET") or ""
    if not secret:
        return "AEGIS_AUTH_SECRET is not set"
    if len(secret) < MIN_SECRET_LENGTH:
        return f"AEGIS_AUTH_SECRET is shorter than {MIN_SECRET_LENGTH} characters"
    api_key = os.getenv("AEGIS_API_KEY") or ""
    if api_key and secret == api_key:
        return "AEGIS_AUTH_SECRET must differ from AEGIS_API_KEY"
    return None


@dataclass
class Posture:
    environment: str
    dev_environment: bool
    auth_enabled: bool
    kill_switches_set: list[str] = field(default_factory=list)
    kill_switches_effective: list[str] = field(default_factory=list)
    token_secret_ok: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "environment": self.environment,
            "dev_environment": self.dev_environment,
            "auth_enabled": self.auth_enabled,
            "kill_switches_set": list(self.kill_switches_set),
            "kill_switches_effective": list(self.kill_switches_effective),
            "token_secret_ok": self.token_secret_ok,
        }


def current_posture() -> Posture:
    dev = is_dev_environment()
    switches = active_kill_switches()
    return Posture(
        environment=deployment_environment(),
        dev_environment=dev,
        auth_enabled=auth_enabled(),
        kill_switches_set=switches,
        kill_switches_effective=switches if dev else [],
        token_secret_ok=token_secret_problem() is None,
    )


def enforce_startup_posture() -> Posture:
    """Raise :class:`InsecureConfigurationError` if the API must not start; else return the posture."""
    posture = current_posture()
    problems: list[str] = []
    if not posture.dev_environment:
        if not posture.auth_enabled:
            problems.append(
                f"authentication is disabled in environment '{posture.environment}'. "
                "Set AEGIS_AUTH_ENABLED=true, or AEGIS_ENV=development for a local demo"
            )
        if posture.kill_switches_set:
            problems.append(
                f"security kill switches {posture.kill_switches_set} are set in environment "
                f"'{posture.environment}'; they are only allowed in development/test"
            )
    if posture.auth_enabled:
        secret_problem = token_secret_problem()
        if secret_problem:
            problems.append(f"authentication is enabled but {secret_problem}")
    if problems:
        raise InsecureConfigurationError("Refusing to start: " + "; ".join(problems))
    if posture.kill_switches_effective:
        log.warning("security kill switches active (development only): %s", posture.kill_switches_effective)
    if not posture.auth_enabled:
        log.warning("authentication is DISABLED (environment '%s'); for local development only",
                    posture.environment)
    return posture
