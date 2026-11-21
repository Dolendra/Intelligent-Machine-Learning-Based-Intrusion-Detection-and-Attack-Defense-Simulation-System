"""Typed module interfaces of the AEGIS framework (roadmap Phase 9).

Five interchangeable module kinds. Each is a ``typing.Protocol``, so any object with the right methods
qualifies: no inheritance from framework classes is needed, and existing components are wrapped, not
rewritten.

| kind       | question it answers                                       | built-in implementations            |
|------------|-----------------------------------------------------------|-------------------------------------|
| detector   | is this flow an attack, and which known family?           | ``frozen_v11``                      |
| open_set   | is this flow unlike calibrated benign traffic?            | ``aegis_osr_gate``, ``none``        |
| adapter    | re-target calibration to a new environment (benign only)  | ``conformal_recalibration``         |
| explainer  | which features drove the detector's verdict?              | ``shap``, ``lime``                  |
| policy     | does this flow raise an incident, and what is it called?  | ``frozen``, ``gate``, ``union``     |

The outputs are plain dataclasses, so modules can be compared and swapped in experiments as well as in
the service.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Protocol, Sequence, runtime_checkable

Row = dict[str, float]

KINDS = ("detector", "open_set", "adapter", "explainer", "policy")


@dataclass(frozen=True)
class DetectionOutput:
    is_attack: bool
    family: str                 # "BENIGN" when not an attack
    score: float                # P(attack) or an equivalent monotone score
    threshold: float
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OpenSetOutput:
    alert: bool
    label: str | None           # BENIGN / known family / UNKNOWN-ATTACK / ZERO-DAY-ANOMALY
    p_value: float | None
    status: str                 # "ok", "unavailable", "error", "disabled"
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Decision:
    raises_incident: bool
    source: str | None          # which detector(s) alerted: frozen / zero_day_gate / both
    incident_label: str | None
    known_family: str | None
    gate_hint: str | None
    policy: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AdaptationReport:
    window: int
    target_alpha: float
    details: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class Detector(Protocol):
    name: str

    def detect(self, rows: Sequence[Row]) -> list[DetectionOutput]: ...


@runtime_checkable
class OpenSetModule(Protocol):
    name: str

    def assess(self, rows: Sequence[Row]) -> list[OpenSetOutput]: ...


@runtime_checkable
class Adapter(Protocol):
    name: str

    def adapt(self, benign_rows: Sequence[Row]) -> AdaptationReport: ...


@runtime_checkable
class Explainer(Protocol):
    name: str

    def explain(self, row: Row, top_k: int = 10) -> dict[str, Any]: ...


@runtime_checkable
class DecisionPolicy(Protocol):
    name: str

    def decide(self, detection: DetectionOutput, open_set: OpenSetOutput | None) -> Decision: ...


PROTOCOLS = {"detector": Detector, "open_set": OpenSetModule, "adapter": Adapter, "explainer": Explainer,
             "policy": DecisionPolicy}
