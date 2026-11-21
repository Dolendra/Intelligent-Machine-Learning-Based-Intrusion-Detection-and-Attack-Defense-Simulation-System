"""Built-in framework modules: thin adapters over the existing, already-tested components.

Nothing here re-implements detection logic. Every module delegates to the code the service already uses:
* the frozen v1.1 predictor (``backend.services.pipeline.get_predictor``);
* the Zero-Day Gate (``zero_day_assessment_with_status``, including its fault isolation);
* the SHAP and LIME engines;
* the shared incident policy (``security.detection_policy.decide``).

The default pipeline is therefore behaviour-identical to ``run_prediction``, which
``tests/test_framework.py`` checks.

The one new capability is ``conformal_recalibration``. It re-targets the gate's calibration to a benign
window from a new environment, as R1b's ``recal@W`` does (benign surprisal maps on one half of the window,
conformal calibration on the other half). It never retrains and never touches the shared gate: it works on
the open-set module's own copy. Under the R3 findings this re-targets the alert threshold; it does not
restore detection under shift (Şahin & Mert 2026; RESEARCH_INTEGRITY_REPORT).
"""
from __future__ import annotations

import copy
from typing import Any, Sequence

import numpy as np
import pandas as pd

from framework.interfaces import AdaptationReport, Decision, DetectionOutput, OpenSetOutput, Row
from framework.registry import registry


# ----------------------------------------------------------------------------- detector
class FrozenV11Detector:
    """The frozen v1.1 two-stage detector (DT binary at the configured operating threshold + RF family)."""

    name = "frozen_v11"

    def __init__(self, allow_missing_features: bool = False) -> None:
        self.allow_missing_features = allow_missing_features

    def _predictor(self):
        from backend.services.pipeline import get_predictor

        p = get_predictor()
        if p is None:
            raise RuntimeError("frozen v1.1 models are not available")
        return p

    def detect(self, rows: Sequence[Row]) -> list[DetectionOutput]:
        pred = self._predictor()
        out = []
        for row in rows:
            r = pred.predict_row(row, allow_missing=self.allow_missing_features)
            out.append(DetectionOutput(is_attack=bool(r.is_attack), family=str(r.attack_type),
                                       score=float(r.binary_proba_attack), threshold=float(r.threshold),
                                       details={"multiclass_confidence": float(r.multiclass_confidence),
                                                "missing_features": list(r.missing_features)}))
        return out


# ----------------------------------------------------------------------------- open set
class AegisOSRGateModule:
    """Aegis-OSR Zero-Day Gate: conformal p-value of fused supervised + kNN evidence."""

    name = "aegis_osr_gate"

    def __init__(self, gate: Any | None = None, explain_top: int = 5) -> None:
        self.gate = gate              # None -> the shared, fault-isolated service gate
        self.explain_top = explain_top

    def assess(self, rows: Sequence[Row]) -> list[OpenSetOutput]:
        rows = list(rows)
        if self.gate is None:
            from backend.services.pipeline import zero_day_assessment_with_status

            results, status = zero_day_assessment_with_status(rows, explain_top=self.explain_top)
        else:
            results, status = self.gate.assess(rows, explain_top=self.explain_top), ["ok"] * len(rows)
        out = []
        for res, st in zip(results, status):
            if res is None:
                out.append(OpenSetOutput(alert=False, label=None, p_value=None, status=st))
            else:
                out.append(OpenSetOutput(alert=bool(res.get("alert")), label=res.get("label"),
                                         p_value=float(res["p_value"]) if res.get("p_value") is not None else None,
                                         status=st, details=res))
        return out

    def raw_scores(self, rows: Sequence[Row]) -> dict[str, np.ndarray]:
        """Raw evidence streams of the gate (needs a concrete gate)."""
        gate = self._concrete_gate()
        Z = gate._frame(list(rows))
        proba = gate.clf.predict_proba(Z)
        return {"sup": 1.0 - proba[:, 0], "knn": gate.knn.kneighbors(Z)[0].mean(axis=1)}

    def _concrete_gate(self):
        if self.gate is None:
            from research.serving import get_gate

            g = get_gate()
            if g is None:
                raise RuntimeError("Zero-Day Gate artifacts are not available")
            self.gate = g
        return self.gate


class NoOpenSet:
    """Disables open-set assessment (closed-set operation)."""

    name = "none"

    def assess(self, rows: Sequence[Row]) -> list[OpenSetOutput]:
        return [OpenSetOutput(alert=False, label=None, p_value=None, status="disabled") for _ in rows]


# ----------------------------------------------------------------------------- adapter
class ConformalRecalibrationAdapter:
    """Benign-window recalibration of an ``AegisOSRGateModule`` (R1b recal@W). It never retrains.

    The window is split at random (fixed seed) into two halves: C1 re-estimates the per-stream benign
    surprisal maps, and C2 re-fits the conformal calibrator on the Fisher-fused score. The module gets a
    private copy of the gate, so the shared service gate is unchanged.
    """

    name = "conformal_recalibration"

    def __init__(self, open_set: AegisOSRGateModule, seed: int = 7919, min_window: int = 200) -> None:
        self.open_set = open_set
        self.seed = seed
        self.min_window = min_window

    def adapt(self, benign_rows: Sequence[Row]) -> AdaptationReport:
        from research.conformal import ConformalCalibrator
        from research.openset import BenignCDF, fuse

        rows = list(benign_rows)
        if len(rows) < self.min_window:
            raise ValueError(f"recalibration needs at least {self.min_window} benign flows, got {len(rows)}")
        base = self.open_set._concrete_gate()
        raw = self.open_set.raw_scores(rows)
        idx = np.random.default_rng(self.seed).permutation(len(rows))
        c1, c2 = idx[: len(idx) // 2], idx[len(idx) // 2:]
        new = copy.copy(base)
        new.cdf = {k: BenignCDF(v[c1]) for k, v in raw.items()}
        fused = fuse([new.cdf["sup"](raw["sup"][c2]), new.cdf["knn"](raw["knn"][c2])], "fisher")
        new.cal = ConformalCalibrator().fit(fused)
        new.version = f"{base.version}+recal@{len(rows)}"
        self.open_set.gate = new
        return AdaptationReport(window=len(rows), target_alpha=float(base.alpha),
                                details={"calibration_flows": int(len(c2)), "map_flows": int(len(c1)),
                                         "gate_version": new.version,
                                         "note": "re-targets the threshold; does not restore detection under shift"})


# ----------------------------------------------------------------------------- explainers
class _EngineExplainer:
    name = ""

    def __init__(self, allow_missing_features: bool = False) -> None:
        self.allow_missing_features = allow_missing_features

    def explain(self, row: Row, top_k: int = 10) -> dict[str, Any]:
        from backend.services.pipeline import run_explain

        return run_explain(row, top_k=top_k, method=self.name, allow_missing_features=self.allow_missing_features)


class ShapExplainer(_EngineExplainer):
    name = "shap"


class LimeExplainer(_EngineExplainer):
    name = "lime"


# ----------------------------------------------------------------------------- policies
class IncidentPolicy:
    """The shared incident policy (``security.detection_policy``): frozen, gate or union."""

    def __init__(self, name: str) -> None:
        from security.detection_policy import POLICIES

        if name not in POLICIES:
            raise ValueError(f"policy must be one of {POLICIES}, got {name!r}")
        self.name = name

    def decide(self, detection: DetectionOutput, open_set: OpenSetOutput | None) -> Decision:
        from security.detection_policy import decide

        d = decide(detection.is_attack, detection.family, bool(open_set and open_set.alert),
                   open_set.label if open_set else None, self.name)
        return Decision(raises_incident=d.raises_incident, source=d.source, incident_label=d.incident_label,
                        known_family=d.known_family, gate_hint=d.gate_hint, policy=self.name)


# ----------------------------------------------------------------------------- registration
def _register() -> None:
    if registry.names("detector"):
        return
    registry.register("detector", "frozen_v11", FrozenV11Detector,
                      description="Frozen v1.1 Decision Tree (binary, operating threshold) + Random Forest (family)")
    registry.register("open_set", "aegis_osr_gate", AegisOSRGateModule,
                      description="Aegis-OSR: split-conformal p-value of Fisher-fused XGB + kNN evidence")
    registry.register("open_set", "none", NoOpenSet, description="Closed-set operation (no open-set module)")
    registry.register("adapter", "conformal_recalibration", ConformalRecalibrationAdapter,
                      description="Benign-window recalibration of the gate (recal@W); never retrains",
                      status="IMPLEMENTED BUT NOT FULLY VERIFIED")
    registry.register("explainer", "shap", ShapExplainer, description="SHAP attributions of the frozen detector")
    registry.register("explainer", "lime", LimeExplainer, description="LIME attributions of the frozen detector")
    for p in ("frozen", "gate", "union"):
        registry.register("policy", p, lambda p=p: IncidentPolicy(p),
                          description={"frozen": "Only the frozen detector raises incidents (default)",
                                       "gate": "Only the Zero-Day Gate raises incidents",
                                       "union": "Either detector raises incidents"}[p])


_register()
