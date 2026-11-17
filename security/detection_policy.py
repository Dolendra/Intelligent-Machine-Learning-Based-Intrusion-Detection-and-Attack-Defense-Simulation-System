"""Shared incident semantics for the frozen v1.1 detector and the advisory Zero-Day Gate.

Both the operational API (``backend/services/pipeline.py``) and the Cyber Range
(``cyberrange/engine.py``) call :func:`decide`, so "which detector raised this incident, and what
is it called" means exactly the same thing everywhere.

Policies (``config.yaml → zero_day_gate.incident_policy``):

* ``frozen`` — only the frozen v1.1 model raises incidents (gate alerts are still recorded).
* ``gate``   — only the Zero-Day Gate raises incidents.
* ``union``  — either detector raises an incident (default).

Labelling rule — a gate alert never becomes a known-family classification by itself:

* frozen alert (with or without the gate)  → the frozen model's family (e.g. ``DDoS``)
* gate-only alert                          → ``Zero-Day Candidate``; the gate's own label
  (which may name a family, ``UNKNOWN-ATTACK`` or ``ZERO-DAY-ANOMALY``) is kept separately as
  advisory evidence and is **not** used for ATT&CK mapping, playbooks or campaign typing.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ids_config import load_config

Policy = Literal["frozen", "gate", "union"]
POLICIES: tuple[str, ...] = ("frozen", "gate", "union")
GATE_ONLY_LABEL = "Zero-Day Candidate"

DetectorSource = Literal["frozen", "zero_day_gate", "both"]


@dataclass(frozen=True)
class DetectionDecision:
    raises_incident: bool
    source: DetectorSource | None      # which detector(s) alerted, regardless of policy
    incident_label: str | None         # label an incident carries (None when no incident)
    known_family: str | None           # only ever set from the frozen model
    gate_hint: str | None              # gate's own label for gate alerts (advisory evidence)


def configured_policy() -> str:
    cfg = load_config().get("zero_day_gate", {}) or {}
    policy = str(cfg.get("incident_policy", "union")).lower()
    if policy not in POLICIES:
        raise ValueError(f"zero_day_gate.incident_policy must be one of {POLICIES}, got {policy!r}")
    return policy


def decide(
    frozen_alert: bool,
    frozen_family: str | None,
    gate_alert: bool,
    gate_label: str | None,
    policy: str | None = None,
) -> DetectionDecision:
    policy = policy or configured_policy()
    if policy not in POLICIES:
        raise ValueError(f"policy must be one of {POLICIES}, got {policy!r}")
    frozen_alert, gate_alert = bool(frozen_alert), bool(gate_alert)
    source: DetectorSource | None = (
        "both" if frozen_alert and gate_alert else "frozen" if frozen_alert else "zero_day_gate" if gate_alert else None
    )
    counts = {"frozen": frozen_alert, "gate": gate_alert, "union": frozen_alert or gate_alert}[policy]
    known = frozen_family if frozen_alert else None
    hint = gate_label if gate_alert else None
    if not counts:
        return DetectionDecision(False, source, None, known, hint)
    # Whenever the frozen model alerted, it is the one that named the family (also under "gate").
    label = frozen_family if frozen_alert else GATE_ONLY_LABEL
    return DetectionDecision(True, source, label, known, hint)
