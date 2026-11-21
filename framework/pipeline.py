"""Composable AEGIS pipeline: detector -> open-set module -> incident policy (-> explainer on demand).

    from framework import AegisPipeline
    pipe = AegisPipeline.from_config()                                  # the service's configuration
    pipe = AegisPipeline.build(open_set="none", policy="frozen")        # closed-set variant
    results = pipe.process([flow_features, ...])

``from_config`` reads ``config.yaml -> framework`` (falling back to ``zero_day_gate.incident_policy``), so the
default pipeline is the one the API serves.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import framework.builtin  # noqa: F401  (registers the built-in modules)
from framework.interfaces import Decision, DetectionOutput, OpenSetOutput, Row
from framework.registry import registry


@dataclass(frozen=True)
class PipelineResult:
    detection: DetectionOutput
    open_set: OpenSetOutput | None
    decision: Decision

    def to_dict(self) -> dict[str, Any]:
        return {"detection": self.detection.to_dict(),
                "open_set": None if self.open_set is None else self.open_set.to_dict(),
                "decision": self.decision.to_dict()}


class AegisPipeline:
    def __init__(self, detector, open_set, policy, explainer=None, adapter=None) -> None:
        self.detector, self.open_set, self.policy = detector, open_set, policy
        self.explainer, self.adapter = explainer, adapter

    @classmethod
    def build(cls, detector: str = "frozen_v11", open_set: str = "aegis_osr_gate", policy: str = "frozen",
              explainer: str | None = "shap", adapter: str | None = None,
              detector_kwargs: dict | None = None) -> "AegisPipeline":
        det = registry.create("detector", detector, **(detector_kwargs or {}))
        osr = registry.create("open_set", open_set)
        pol = registry.create("policy", policy)
        exp = registry.create("explainer", explainer) if explainer else None
        ada = registry.create("adapter", adapter, open_set=osr) if adapter else None
        return cls(det, osr, pol, exp, ada)

    @classmethod
    def from_config(cls, cfg: dict | None = None, **overrides: Any) -> "AegisPipeline":
        if cfg is None:
            from ids_config import load_config

            cfg = load_config()
        from security.detection_policy import configured_policy

        fw = dict(cfg.get("framework") or {})
        spec = {"detector": fw.get("detector", "frozen_v11"),
                "open_set": fw.get("open_set", "aegis_osr_gate"),
                "policy": fw.get("policy") or configured_policy(),
                "explainer": fw.get("explainer", "shap"),
                "adapter": fw.get("adapter")}
        spec.update(overrides)
        return cls.build(**spec)

    def describe(self) -> dict[str, Any]:
        return {"detector": self.detector.name, "open_set": self.open_set.name, "policy": self.policy.name,
                "explainer": None if self.explainer is None else self.explainer.name,
                "adapter": None if self.adapter is None else self.adapter.name}

    def process(self, rows: Sequence[Row]) -> list[PipelineResult]:
        rows = list(rows)
        dets = self.detector.detect(rows)
        osrs = self.open_set.assess(rows)
        return [PipelineResult(d, o, self.policy.decide(d, o)) for d, o in zip(dets, osrs)]

    def explain(self, row: Row, top_k: int = 10) -> dict[str, Any]:
        if self.explainer is None:
            raise RuntimeError("this pipeline has no explainer module")
        return self.explainer.explain(row, top_k=top_k)

    def adapt(self, benign_rows: Sequence[Row]):
        if self.adapter is None:
            raise RuntimeError("this pipeline has no adapter module")
        return self.adapter.adapt(benign_rows)
