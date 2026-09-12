"""Tests for severity escalation, campaigns, rate-limit config."""
from __future__ import annotations

from security.correlation import escalate_severity, severity_rank


def test_severity_escalation_with_hits():
    assert escalate_severity("LOW", "LOW", hit_count=1) == "LOW"
    assert escalate_severity("LOW", "LOW", hit_count=2) == "MEDIUM"
    assert escalate_severity("MEDIUM", "MEDIUM", hit_count=4) == "HIGH"
    assert escalate_severity("HIGH", "HIGH", hit_count=8) == "CRITICAL"
    # Never downgrade below current when target is lower
    assert severity_rank(escalate_severity("CRITICAL", "LOW", hit_count=1)) == severity_rank("CRITICAL")


def test_campaign_chain_adjacency():
    from security.correlation import CHAIN_NEXT

    assert "BruteForce" in CHAIN_NEXT["PortScan"]
    assert "WebAttack" in CHAIN_NEXT["BruteForce"]
