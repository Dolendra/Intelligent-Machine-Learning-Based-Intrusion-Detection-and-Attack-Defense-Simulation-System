"""Vendor-neutral response adapter contract (productionization P3)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from security.response.types import ResponseAction


class AdapterError(RuntimeError):
    """Adapter-level failure (validate/execute/verify/rollback)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ResponseAdapter(ABC):
    """Neutral contract — DryRun, TestNetwork, future Firewall/EDR."""

    name: str = "base"
    touches_real_network: bool = False

    @abstractmethod
    def validate(self, action: ResponseAction) -> dict[str, Any]:
        ...

    @abstractmethod
    def preview(self, action: ResponseAction) -> dict[str, Any]:
        ...

    @abstractmethod
    def execute(self, action: ResponseAction) -> dict[str, Any]:
        ...

    @abstractmethod
    def verify(self, action: ResponseAction) -> dict[str, Any]:
        ...

    @abstractmethod
    def rollback(self, action: ResponseAction) -> dict[str, Any]:
        ...

    def capabilities(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "touches_real_network": self.touches_real_network,
            "supports_rollback": True,
            "supports_verify": True,
        }
