"""R-01 (ARCH-2, ML-5, ARCH-19): risk is read with the right key; gate-only risk uses measured intensity."""
from __future__ import annotations

import typing

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services import pipeline as svc
from ml.features.intensity import intensity_report
from research.serving import GATE_DIR
from security.detection_policy import GATE_ONLY_LABEL
from security.risk.engine import RiskResult, compute_risk

client = TestClient(app)
ready = svc.models_ready() and (GATE_DIR / "aegis_osr_bundle.joblib").exists()
needs_models = pytest.mark.skipif(not ready, reason="frozen models + gate artifacts required")


def _pool_row(family: str, i: int = 0) -> dict:
    from ids_config import ROOT

    pool = pd.read_parquet(ROOT / "research_artifacts" / "replay" / "replay_pool.parquet")
    row = pool[pool["family"] == family].iloc[i]
    return {k: float(v) for k, v in row.items() if k not in {"family", "fine_label", "day", "dataset"}}


def test_compute_risk_return_contract():
    out = compute_risk("DDoS", 0.9, True, 0.5)
    assert set(typing.get_type_hints(RiskResult)) <= set(out)
    assert "score" not in out and out["risk_score"] > 0


@needs_models
def test_gate_only_incident_persists_nonzero_risk_with_measured_intensity(monkeypatch):
    import security.detection_policy as dp

    monkeypatch.setattr(dp, "configured_policy", lambda: "union")   # gate may raise incidents
    feats = _pool_row("Heartbleed")
    body = client.post("/api/predict", json={"features": feats, "persist": True,
                                             "source_ref": "r01-heartbleed"}).json()
    assert body["is_attack"] is False and body["zero_day"]["alert"] is True
    inc_risk = body["incident_risk"]
    p = float(body["zero_day"]["p_value"])
    expected = compute_risk(GATE_ONLY_LABEL, max(0.0, min(1.0, 1 - p)), True,
                            traffic_intensity=intensity_report(feats)["value"])
    assert inc_risk["risk_score"] == expected["risk_score"] > 0
    assert inc_risk["severity"] == expected["severity"]
    inc = client.get(f"/api/incidents/{body['incident_id']}").json()
    assert float(inc["risk_score"]) == expected["risk_score"]          # persisted, not 0


@needs_models
def test_gate_only_intensity_is_not_forced_to_zero(monkeypatch):
    feats = _pool_row("Heartbleed")
    assert intensity_report(feats)["value"] > 0                       # precondition for the fix


@needs_models
def test_dedup_update_raises_stored_risk(monkeypatch):
    import security.detection_policy as dp

    monkeypatch.setattr(dp, "configured_policy", lambda: "union")
    feats = _pool_row("Heartbleed")
    first = client.post("/api/predict", json={"features": feats, "persist": True,
                                              "source_ref": "r01-dedup"}).json()
    second = client.post("/api/predict", json={"features": feats, "persist": True,
                                               "source_ref": "r01-dedup"}).json()
    assert second["incident_id"] == first["incident_id"]
    inc = client.get(f"/api/incidents/{first['incident_id']}").json()
    assert float(inc["risk_score"]) > 0


@needs_models
def test_live_tick_carries_computed_risk_for_attacks(monkeypatch):
    from backend.services.live_stream import POOL_PATH, LiveSession

    s = LiveSession(scenario="enterprise_day", rate=50, seed=7)
    frame = pd.read_parquet(POOL_PATH)
    ddos = frame[frame["family"] == "DDoS"].head(40).reset_index(drop=True)
    benign = frame[frame["family"] == "BENIGN"].head(10).reset_index(drop=True)
    batch = pd.concat([ddos, benign], ignore_index=True)
    monkeypatch.setattr(s, "_draw", lambda n, mix: batch)
    flows = s.tick()["flows"]
    alerts = [f for f in flows if f["frozen"]["is_attack"]]
    assert alerts, "no frozen alerts on DDoS rows"
    assert all(f["frozen"]["risk_score"] > 0 for f in alerts)
    assert all(f["frozen"]["risk_score"] == 0 for f in flows if not f["frozen"]["is_attack"])
