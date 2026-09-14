"""Backward-compatible dry-run exports (P2 → P3 adapters)."""
from __future__ import annotations

from security.response.adapters.dry_run import DryRunAdapter
from security.response.adapters.live_forbidden import LiveAdapterForbiddenError
from security.response.adapters.live_forbidden import _LegacyLive as LiveNetworkAdapter

DryRunExecutor = DryRunAdapter

__all__ = [
    "DryRunAdapter",
    "DryRunExecutor",
    "LiveAdapterForbiddenError",
    "LiveNetworkAdapter",
]
