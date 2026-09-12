"""Shared simulation graph types."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SimNode:
    id: str
    label: str
    kind: str
    status: str = "ok"


@dataclass
class SimEdge:
    id: str
    source: str
    target: str
    traffic: str = "normal"
    intensity: float = 0.2
