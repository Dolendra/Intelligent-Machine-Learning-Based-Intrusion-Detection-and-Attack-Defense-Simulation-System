"""Phase 9: modular framework. Interfaces, registry, behaviour parity with the service, and the adapter."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from framework import AegisPipeline, UnknownModuleError, registry
from framework.interfaces import (KINDS, PROTOCOLS, Decision, DetectionOutput, Detector, OpenSetOutput)
from framework.registry import Registry


def test_every_builtin_module_is_registered_and_implements_its_interface():
    names = {k: registry.names(k) for k in KINDS}
    assert names["detector"] == ["frozen_v11"]
    assert names["open_set"] == ["aegis_osr_gate", "none"]
    assert names["policy"] == ["frozen", "gate", "union"]
    assert set(names["explainer"]) == {"shap", "lime"} and names["adapter"] == ["conformal_recalibration"]
    for kind in ("detector", "open_set", "explainer", "policy"):
        for n in names[kind]:
            assert isinstance(registry.create(kind, n), PROTOCOLS[kind])
    desc = registry.describe()
    assert all(e["status"] for k in KINDS for e in desc[k])


def test_registry_rejects_unknown_duplicate_and_nonconforming_modules():
    with pytest.raises(UnknownModuleError):
        registry.create("detector", "nope")
    r = Registry()
    with pytest.raises(ValueError):
        r.register("bogus_kind", "x", object)
    r.register("detector", "bad", lambda: object())
    with pytest.raises(ValueError):
        r.register("detector", "bad", lambda: object())
    with pytest.raises(TypeError):
        r.create("detector", "bad")


class _StubDetector:
    name = "stub"

    def __init__(self, verdicts):
        self.verdicts = verdicts

    def detect(self, rows):
        return [DetectionOutput(v, "DoS" if v else "BENIGN", float(v), 0.85) for v in self.verdicts]


class _StubOpenSet:
    name = "stub_osr"

    def __init__(self, alerts):
        self.alerts = alerts

    def assess(self, rows):
        return [OpenSetOutput(a, "ZERO-DAY-ANOMALY" if a else "BENIGN", 0.001 if a else 0.5, "ok") for a in self.alerts]


def test_modules_are_interchangeable_without_framework_inheritance():
    assert isinstance(_StubDetector([]), Detector)
    verdicts, alerts = [True, False, False], [False, True, False]
    for policy, expect in (("frozen", [True, False, False]), ("gate", [False, True, False]),
                           ("union", [True, True, False])):
        pipe = AegisPipeline(_StubDetector(verdicts), _StubOpenSet(alerts), registry.create("policy", policy))
        res = pipe.process([{}, {}, {}])
        assert [r.decision.raises_incident for r in res] == expect
        assert all(isinstance(r.decision, Decision) for r in res)
    gate_only = AegisPipeline(_StubDetector([False]), _StubOpenSet([True]), registry.create("policy", "union"))
    d = gate_only.process([{}])[0].decision
    assert d.incident_label == "Zero-Day Candidate" and d.known_family is None   # gate never names a family


def test_pipeline_without_explainer_or_adapter_says_so():
    pipe = AegisPipeline(_StubDetector([False]), _StubOpenSet([False]), registry.create("policy", "frozen"))
    with pytest.raises(RuntimeError):
        pipe.explain({})
    with pytest.raises(RuntimeError):
        pipe.adapt([])


# ----------------------------------------------------------------------------- real models
def _ready() -> bool:
    try:
        from backend.services import pipeline as svc
        from research.serving import GATE_DIR
        return svc.models_ready() and (GATE_DIR / "aegis_osr_bundle.joblib").exists()
    except Exception:  # noqa: BLE001
        return False


needs_models = pytest.mark.skipif(not _ready(), reason="frozen models + gate artifacts required")


def _replay(per_family: int = 4) -> tuple[list[dict], list[str]]:
    from ids_config import ROOT

    pool = pd.read_parquet(ROOT / "research_artifacts" / "replay" / "replay_pool.parquet")
    pick = pool.groupby("family", observed=True).head(per_family)
    drop = {"family", "fine_label", "day", "dataset"}
    rows = [{k: float(v) for k, v in r.items() if k not in drop} for _, r in pick.iterrows()]
    return rows, pick["family"].astype(str).tolist()


@needs_models
@pytest.mark.parametrize("policy", ["frozen", "union"])
def test_default_pipeline_reproduces_the_service_decision_exactly(policy, monkeypatch):
    import security.detection_policy as dp
    from backend.services import pipeline as svc

    monkeypatch.setattr(dp, "configured_policy", lambda: policy)
    rows, _ = _replay()
    pipe = AegisPipeline.from_config()
    assert pipe.describe()["policy"] == policy and pipe.describe()["open_set"] == "aegis_osr_gate"
    got = pipe.process(rows)
    for row, res in zip(rows, got):
        ref = svc.run_prediction(row, db=None, persist=False)
        assert res.detection.is_attack == ref["is_attack"] and res.detection.family == ref["attack_type"]
        assert res.detection.score == pytest.approx(ref["binary_proba_attack"], abs=1e-12)
        dd = ref["detection_decision"]
        assert res.decision.to_dict() == {**{k: dd[k] for k in ("raises_incident", "source", "incident_label",
                                                                "known_family", "gate_hint")}, "policy": policy}
        assert res.open_set.status == ref["zero_day_status"]


@needs_models
def test_closed_set_pipeline_never_raises_gate_incidents():
    rows, _ = _replay(2)
    res = AegisPipeline.build(open_set="none", policy="union", explainer=None).process(rows)
    assert all(r.open_set.status == "disabled" for r in res)
    assert all(r.decision.raises_incident == r.detection.is_attack for r in res)


@needs_models
def test_recalibration_adapter_targets_alpha_on_exchangeable_benign_and_leaves_shared_gate_untouched():
    from ids_config import ROOT
    from research.serving import get_gate

    shared = get_gate()
    shared_cal = shared.cal
    pool = pd.read_parquet(ROOT / "research_artifacts" / "replay" / "replay_pool.parquet")
    benign = pool[pool["family"] == "BENIGN"].sample(frac=1.0, random_state=0)
    drop = {"family", "fine_label", "day", "dataset"}
    rows = [{k: float(v) for k, v in r.items() if k not in drop} for _, r in benign.iterrows()]
    window, held = rows[:4000], rows[4000:]
    pipe = AegisPipeline.build(policy="gate", explainer=None, adapter="conformal_recalibration")
    rep = pipe.adapt(window)
    assert rep.window == 4000 and rep.details["calibration_flows"] == 2000
    assert get_gate().cal is shared_cal                       # the service gate is unchanged
    assert pipe.open_set.gate is not shared and "+recal@4000" in pipe.open_set.gate.version
    fpr = np.mean([r.alert for r in pipe.open_set.assess(held)])
    assert fpr <= 0.025                                         # alpha = 1 %; n = 4,000 held-out benign flows
    with pytest.raises(ValueError):
        pipe.adapt(window[:10])
