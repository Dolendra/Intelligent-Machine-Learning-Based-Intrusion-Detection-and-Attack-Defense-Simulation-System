"""Live / future vendor adapters — intentionally forbidden until a later phase."""
from __future__ import annotations

from typing import Any

from security.response.adapters.base import AdapterError, ResponseAdapter
from security.response.types import ResponseAction


class LiveAdapterForbiddenError(AdapterError):
    def __init__(self, message: str | None = None) -> None:
        super().__init__(
            "LIVE_ADAPTER_FORBIDDEN",
            message
            or (
                "Live network adapters are disabled. "
                "Use DRY_RUN or CONTROLLED (test_network) mode only."
            ),
        )


class LiveNetworkAdapter(ResponseAdapter):
    """Stub for future Firewall/EDR — must not execute in P3."""

    name = "live_forbidden"
    touches_real_network = True

    def validate(self, action: ResponseAction) -> dict[str, Any]:
        raise LiveAdapterForbiddenError()

    def preview(self, action: ResponseAction) -> dict[str, Any]:
        raise LiveAdapterForbiddenError()

    def execute(self, action: ResponseAction) -> dict[str, Any]:
        raise LiveAdapterForbiddenError()

    def verify(self, action: ResponseAction) -> dict[str, Any]:
        raise LiveAdapterForbiddenError()

    def rollback(self, action: ResponseAction) -> dict[str, Any]:
        raise LiveAdapterForbiddenError()


# Back-compat aliases used by P2 imports
class _LegacyLive:
    def apply(self, action: ResponseAction) -> dict[str, Any]:
        raise LiveAdapterForbiddenError(
            "Live network adapters are disabled in productionization P3. Use DRY_RUN or CONTROLLED."
        )

    def rollback(self, action: ResponseAction) -> dict[str, Any]:
        raise LiveAdapterForbiddenError("Live rollback adapters are disabled in P3.")
