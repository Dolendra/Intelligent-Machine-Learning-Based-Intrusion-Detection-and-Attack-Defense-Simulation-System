"""Tests for rule engine, context risk, and recommendations."""
from security.risk.engine import compute_risk
from security.recommendations.engine import recommend
from security.rules import evaluate_rules, rule_actions
from backend.services.pipeline import INCIDENT_TRANSITIONS


def test_rules_ddos_high_intensity():
    hits = evaluate_rules(
        attack_type="DDoS",
        severity="CRITICAL",
        is_attack=True,
        traffic_intensity=0.9,
    )
    actions = rule_actions(hits)
    assert "UPSTREAM_FILTER" in actions
    assert "RATE_LIMIT" in actions
    assert "ESCALATE_ANALYST" in actions


def test_rules_uncertain_review():
    hits = evaluate_rules(
        attack_type="PortScan",
        severity="MEDIUM",
        is_attack=True,
        certainty="uncertain",
    )
    assert any(h.action == "ANALYST_REVIEW" for h in hits)


def test_risk_asset_criticality_raises_score():
    low = compute_risk("DDoS", 0.9, True, traffic_intensity=0.5, asset_criticality=1)
    high = compute_risk("DDoS", 0.9, True, traffic_intensity=0.5, asset_criticality=5)
    assert high["risk_score"] >= low["risk_score"]
    assert "asset_criticality" in high["factors"]
    assert "weights" in high


def test_recommend_includes_rule_hits():
    rec = recommend("DDoS", "CRITICAL", confidence=0.95, traffic_intensity=0.85)
    assert rec["advisory_only"] is True
    assert rec["rule_hits"]
    assert rec["rule_actions"]


def test_incident_transitions_cover_lifecycle():
    assert "Triaged" in INCIDENT_TRANSITIONS["Detected"]
    assert "Resolved" in INCIDENT_TRANSITIONS["Monitoring"]
    assert INCIDENT_TRANSITIONS["Resolved"] == set()
