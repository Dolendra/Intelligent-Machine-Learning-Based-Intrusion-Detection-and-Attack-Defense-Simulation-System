"""Tests for decision trace + Alembic migration presence."""
from __future__ import annotations

from pathlib import Path

from backend.services.decision_trace import build_trace_from_prediction
from ids_config import ROOT


def test_decision_trace_steps():
    payload = {
        "is_attack": True,
        "attack_type": "DDoS",
        "confidence": 0.97,
        "binary_proba_attack": 0.97,
        "certainty": "likely_attack",
        "threshold": 0.5,
        "risk_score": 91,
        "severity": "CRITICAL",
        "recommendation": {"primary": "Rate limit + upstream filter", "rule_hits": [{"id": "r1"}]},
        "incident_id": "INC-TEST01",
        "campaign_id": "CMP-TEST",
        "risk_factors": {"intensity": 0.9},
    }
    trace = build_trace_from_prediction(
        payload,
        explain={
            "actual_method": "shap",
            "fallback_used": False,
            "top_features": [
                {"feature": "Flow Packets/s", "contribution": 0.4},
                {"feature": "Flow Bytes/s", "contribution": 0.2},
            ],
        },
    )
    stages = [s["stage"] for s in trace["steps"]]
    assert stages[0] == "traffic"
    assert "ml" in stages and "xai" in stages and "risk" in stages
    assert "recommendation" in stages and "incident" in stages


def test_alembic_files_present():
    assert (ROOT / "alembic.ini").exists()
    assert (ROOT / "alembic" / "env.py").exists()
    versions = list((ROOT / "alembic" / "versions").glob("*.py"))
    assert any("001_initial" in p.name for p in versions)
