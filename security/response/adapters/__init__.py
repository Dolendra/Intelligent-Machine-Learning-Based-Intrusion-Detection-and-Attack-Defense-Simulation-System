"""Adapter registry — select dry_run / test_network; never live in P3."""
from __future__ import annotations

from typing import Any

from security.response.adapters.base import ResponseAdapter
from security.response.adapters.dry_run import DryRunAdapter
from security.response.adapters.live_forbidden import LiveNetworkAdapter
from security.response.adapters.test_network import TestNetworkAdapter, test_network_adapter
from security.response.types import ExecutionMode

_dry_run = DryRunAdapter()
_live = LiveNetworkAdapter()


def get_adapter(name: str | None = None, *, mode: str | None = None) -> ResponseAdapter:
    """Resolve adapter from explicit name or execution mode."""
    if name:
        key = name.strip().lower()
        if key in {"dry_run", "dry-run"}:
            return _dry_run
        if key in {"test_network", "test", "controlled"}:
            return test_network_adapter
        if key in {"live", "firewall", "edr", "live_forbidden"}:
            return _live
        raise KeyError(f"Unknown adapter '{name}'")

    m = (mode or ExecutionMode.DRY_RUN.value).upper()
    if m == ExecutionMode.DRY_RUN.value:
        return _dry_run
    if m == ExecutionMode.CONTROLLED.value:
        return test_network_adapter
    if m == ExecutionMode.LIVE.value:
        return _live
    raise KeyError(f"Unknown mode '{mode}'")


def list_adapters() -> list[dict[str, Any]]:
    return [
        _dry_run.capabilities(),
        test_network_adapter.capabilities(),
        {
            **_live.capabilities(),
            "enabled": False,
            "notes": "Reserved for future Firewall/EDR — forbidden in P3.",
        },
    ]


def reset_test_adapter() -> None:
    test_network_adapter.reset()


__all__ = [
    "DryRunAdapter",
    "TestNetworkAdapter",
    "LiveNetworkAdapter",
    "get_adapter",
    "list_adapters",
    "reset_test_adapter",
    "test_network_adapter",
]
