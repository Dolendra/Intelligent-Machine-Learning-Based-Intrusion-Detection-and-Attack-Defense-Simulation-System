"""Module registry: name -> factory, per module kind. Factories are lazy, so listing modules loads no model."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from framework.interfaces import KINDS, PROTOCOLS


class UnknownModuleError(KeyError):
    pass


@dataclass(frozen=True)
class Entry:
    kind: str
    name: str
    factory: Callable[..., Any]
    description: str
    status: str            # IMPLEMENTED AND VERIFIED / IMPLEMENTED BUT NOT FULLY VERIFIED / EXPERIMENTAL


class Registry:
    def __init__(self) -> None:
        self._entries: dict[tuple[str, str], Entry] = {}

    def register(self, kind: str, name: str, factory: Callable[..., Any], *, description: str = "",
                 status: str = "IMPLEMENTED AND VERIFIED") -> None:
        if kind not in KINDS:
            raise ValueError(f"unknown module kind {kind!r}; expected one of {KINDS}")
        if (kind, name) in self._entries:
            raise ValueError(f"{kind} module {name!r} is already registered")
        self._entries[(kind, name)] = Entry(kind, name, factory, description, status)

    def create(self, kind: str, name: str, **kwargs: Any) -> Any:
        try:
            entry = self._entries[(kind, name)]
        except KeyError:
            raise UnknownModuleError(f"no {kind} module named {name!r}; available: {self.names(kind)}") from None
        module = entry.factory(**kwargs)
        if not isinstance(module, PROTOCOLS[kind]):
            raise TypeError(f"{kind} module {name!r} does not implement the {PROTOCOLS[kind].__name__} interface")
        return module

    def names(self, kind: str) -> list[str]:
        return sorted(n for k, n in self._entries if k == kind)

    def describe(self) -> dict[str, list[dict[str, str]]]:
        return {k: [{"name": e.name, "description": e.description, "status": e.status}
                    for (kk, _), e in sorted(self._entries.items()) if kk == k] for k in KINDS}


registry = Registry()
