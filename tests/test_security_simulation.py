"""Unit tests for security + simulation (no trained models required)."""
from security.risk.engine import compute_risk, severity_label
from security.recommendations.engine import recommend
from simulation.engine.core import SimulationEngine
from ml.preprocessing.dataset import normalize_labels
import pandas as pd


def test_normalize_labels_families():
    s = pd.Series(["BENIGN", "DoS Hulk", "DDoS", "FTP-Patator", "PortScan"])
    out = normalize_labels(s).tolist()
    assert out == ["BENIGN", "DoS", "DDoS", "BruteForce", "PortScan"]


def test_risk_benign_is_low():
    r = compute_risk("BENIGN", 0.99, is_attack=False)
    assert r["risk_score"] == 0
    assert r["severity"] == "LOW"


def test_risk_ddos_high():
    r = compute_risk("DDoS", 0.95, is_attack=True, traffic_intensity=0.9)
    assert r["risk_score"] >= 70
    assert r["severity"] in {"HIGH", "CRITICAL"}


def test_severity_bands():
    assert severity_label(10) == "LOW"
    assert severity_label(50) == "MEDIUM"
    assert severity_label(70) == "HIGH"
    assert severity_label(90) == "CRITICAL"


def test_recommend_ddos():
    rec = recommend("DDoS", "CRITICAL")
    assert rec["advisory_only"] is True
    assert "filter" in rec["primary"].lower() or "limiting" in rec["primary"].lower()


def test_simulation_lifecycle():
    eng = SimulationEngine()
    s = eng.start("DDoS", 0.96)
    sid = s["id"]
    states = [s["state"]]
    for _ in range(7):
        s = eng.advance(sid)
        states.append(s["state"])
    assert "detected" in states
    assert states[-1] == "recovered"
    assert s["severity"] == "LOW"
