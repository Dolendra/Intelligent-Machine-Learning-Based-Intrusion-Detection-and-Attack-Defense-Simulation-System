"""MITRE ATT&CK context on recommendations, campaigns and the cyber range."""
from security.recommendations.engine import recommend
from security.threat_intel import ATTACK_MAP, TACTIC_ORDER, attack_context, kill_chain


def test_every_family_maps_to_a_valid_tactic_and_technique():
    for fam, m in ATTACK_MAP.items():
        ctx = attack_context(fam)
        assert ctx["tactic_id"] in TACTIC_ORDER, fam
        assert ctx["technique_id"].startswith("T"), fam
        assert ctx["url"].startswith("https://attack.mitre.org/techniques/T")


def test_benign_and_unknown_have_no_mapping():
    assert attack_context("BENIGN") is None
    assert attack_context("UNKNOWN-ATTACK") is None
    assert recommend("BENIGN", "LOW")["mitre_attack"] is None


def test_recommendation_carries_attack_context():
    rec = recommend("PortScan", "MEDIUM")
    assert rec["mitre_attack"]["tactic"] == "Reconnaissance"
    assert rec["mitre_attack"]["technique_id"] == "T1595"


def test_kill_chain_orders_a_campaign():
    kc = kill_chain(["PortScan", "PortScan", "BruteForce", "WebAttack", "Bot"])
    assert [s["tactic"] for s in kc["steps"]] == ["Reconnaissance", "Credential Access", "Initial Access", "Command and Control"]
    assert kc["multi_stage"] and kc["furthest_tactic"] == "Command and Control"
    assert kill_chain([])["steps"] == []


def test_range_view_exposes_mitre_after_detection():
    from cyberrange import RangeConfig, RangeRun
    from cyberrange.engine import POOL_PATH

    if not POOL_PATH.exists():
        return
    run = RangeRun(RangeConfig(scenario="brute_force", seed=1))
    assert run.view()["mitre_attack"] is None
    v = run.complete()
    assert v["mitre_attack"] is not None and v["mitre_attack"]["framework"] == "MITRE ATT&CK Enterprise"
