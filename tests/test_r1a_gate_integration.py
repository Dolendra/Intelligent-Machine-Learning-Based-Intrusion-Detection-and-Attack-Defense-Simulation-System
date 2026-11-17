"""R1a acceptance: Zero-Day Gate alerts are persisted and share incident semantics with the range."""
from __future__ import annotations

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services import pipeline as svc
from research.serving import GATE_DIR
from security.detection_policy import GATE_ONLY_LABEL, decide

client = TestClient(app)
ready = svc.models_ready() and (GATE_DIR / "aegis_osr_bundle.joblib").exists()
needs_models = pytest.mark.skipif(not ready, reason="frozen models + gate artifacts required")


# ----------------------------------------------------------------------------- policy (pure)
def test_gate_only_alert_is_never_a_known_family():
    d = decide(False, "BENIGN", True, "DDoS", "union")  # gate even *names* a family
    assert d.raises_incident and d.source == "zero_day_gate"
    assert d.incident_label == GATE_ONLY_LABEL and d.known_family is None
    assert d.gate_hint == "DDoS"  # kept as advisory evidence only


def test_frozen_alert_keeps_frozen_family_under_every_policy():
    for policy in ("frozen", "union", "gate"):
        d = decide(True, "PortScan", True, "ZERO-DAY-ANOMALY", policy)
        assert d.raises_incident and d.incident_label == "PortScan" and d.source == "both"


def test_policies_gate_which_detector_raises_incidents():
    assert not decide(False, "BENIGN", True, "ZERO-DAY-ANOMALY", "frozen").raises_incident
    assert not decide(True, "DoS", False, None, "gate").raises_incident
    assert not decide(False, "BENIGN", False, None, "union").raises_incident
    with pytest.raises(ValueError):
        decide(True, "DoS", False, None, "bogus")


# ----------------------------------------------------------------------------- API persistence
def _heartbleed_features() -> dict:
    from ids_config import ROOT

    pool = pd.read_parquet(ROOT / "research_artifacts" / "replay" / "replay_pool.parquet")
    row = pool[pool["family"] == "Heartbleed"].iloc[0]
    drop = {"family", "fine_label", "day", "dataset"}
    return {k: float(v) for k, v in row.items() if k not in drop}


@needs_models
def test_gate_only_detection_creates_auditable_zero_day_incident(monkeypatch):
    import security.detection_policy as dp
    from database.db import SessionLocal, ZeroDayAlert

    # "union" is now an explicitly selected experimental policy (default is "frozen").
    monkeypatch.setattr(dp, "configured_policy", lambda: "union")

    body = client.post("/api/predict", json={"features": _heartbleed_features(), "persist": True,
                                             "source_ref": "r1a-heartbleed"}).json()
    assert body["is_attack"] is False                      # frozen verdict unchanged
    assert body["zero_day"]["alert"] is True
    dd = body["detection_decision"]
    assert dd["source"] == "zero_day_gate" and dd["incident_label"] == GATE_ONLY_LABEL
    inc_id = body["incident_id"]
    assert inc_id
    inc = client.get(f"/api/incidents/{inc_id}").json()
    assert inc["attack_type"] == GATE_ONLY_LABEL and inc["detector_source"] == "zero_day_gate"
    assert inc["zero_day_label"] in ("ZERO-DAY-ANOMALY", "UNKNOWN-ATTACK")
    assert any(s["stage"] == "zero_day_gate" for s in body["decision_trace"]["steps"])
    db = SessionLocal()
    try:
        # repeat detections dedup onto one incident but each gate alert gets its own audit row
        row = (db.query(ZeroDayAlert).filter(ZeroDayAlert.incident_code == inc_id)
               .order_by(ZeroDayAlert.id.desc()).first())
        assert row is not None
        assert row.raised_incident == 1 and row.frozen_is_attack == 0
        assert row.gate_model_version.startswith("aegis-osr@") and 0 < row.p_value <= row.alpha
        assert row.created_at is not None
    finally:
        db.close()


@needs_models
def test_frozen_policy_records_gate_alert_without_incident(monkeypatch):
    import security.detection_policy as dp
    from database.db import SessionLocal, ZeroDayAlert

    monkeypatch.setattr(dp, "configured_policy", lambda: "frozen")
    body = client.post("/api/predict", json={"features": _heartbleed_features(), "persist": True,
                                             "source_ref": "r1a-frozen-policy"}).json()
    assert body["incident_id"] is None and body["zero_day"]["alert"] is True
    db = SessionLocal()
    try:
        row = (db.query(ZeroDayAlert).filter(ZeroDayAlert.source_ref == "r1a-frozen-policy")
               .order_by(ZeroDayAlert.id.desc()).first())
        assert row is not None and row.raised_incident == 0 and row.policy == "frozen"
    finally:
        db.close()


# ----------------------------------------------------------------------------- range semantics
@needs_models
def test_range_zero_day_incident_uses_shared_label_and_no_ground_truth_attack_tag():
    from cyberrange.engine import RangeConfig, RangeRun

    gate_only_runs = 0
    for seed in (1, 2, 3):
        run = RangeRun(RangeConfig(scenario="zero_day", seed=seed, detector="gate").validate())
        run.step(seconds=run.duration + 5)
        view = run.view()
        if view["detected_family"] is None:
            continue
        # detector="gate": frozen never names these unseen families → shared gate-only label
        assert view["detected_family"] == GATE_ONLY_LABEL
        assert view["mitre_attack"] is None, "range must not show the scenario's ground-truth technique"
        assert view["recommended"] == "block_source"
        gate_only_runs += 1
    assert gate_only_runs >= 1


def test_range_refuses_to_run_without_detectors(monkeypatch):
    import cyberrange.engine as eng
    import research.serving as serving

    eng.scored_pool.cache_clear()
    monkeypatch.setattr(serving, "get_gate", lambda: None)
    try:
        with pytest.raises(eng.ModelsUnavailable):
            eng.scored_pool()
    finally:
        eng.scored_pool.cache_clear()
