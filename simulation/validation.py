"""Cyber-range simulation validation (controlled visualization — not a live range).

Validates that configured attack-family scenarios complete the advisory lifecycle
with deterministic shape. Defense effectiveness values are config assumptions,
not measured real-world mitigation rates.
"""
from __future__ import annotations

from typing import Any

from ids_config import load_config
from simulation.engine.core import SimulationEngine

DEFAULT_FAMILIES = ("DDoS", "DoS", "PortScan", "BruteForce", "WebAttack", "Bot")

REQUIRED_KEYS = (
    "id",
    "attack_type",
    "state",
    "advisory_only",
    "disclaimer",
    "latencies",
    "series",
    "comparison",
    "metrics",
    "phase_guide",
)


def configured_efficacy_table() -> dict[str, float]:
    cfg = load_config().get("simulation", {}).get("defense_effectiveness", {}) or {}
    return {str(k): float(v) for k, v in cfg.items()}


def run_family_to_recovered(
    attack_type: str,
    *,
    confidence: float = 0.92,
    traffic_intensity: float = 0.65,
    engine: SimulationEngine | None = None,
) -> dict[str, Any]:
    eng = engine or SimulationEngine()
    session = eng.start(attack_type, confidence, traffic_intensity=traffic_intensity)
    sid = session["id"]
    states = [session["state"]]
    for _ in range(12):
        if session["state"] == "recovered":
            break
        session = eng.advance(sid)
        states.append(session["state"])
    return {"final": session, "states": states}


def validate_session(session: dict[str, Any], *, attack_type: str) -> list[str]:
    """Return list of validation error strings (empty = pass)."""
    errors: list[str] = []
    for key in REQUIRED_KEYS:
        if key not in session:
            errors.append(f"missing_key:{key}")
    if session.get("attack_type") != attack_type:
        errors.append(f"attack_type_mismatch:{session.get('attack_type')}")
    if session.get("advisory_only") is not True:
        errors.append("advisory_only_false")
    disc = str(session.get("disclaimer") or "")
    if "assumption" not in disc.lower() and "visualization" not in disc.lower():
        errors.append("disclaimer_weak")
    if session.get("state") != "recovered":
        errors.append(f"not_recovered:{session.get('state')}")
    metrics = session.get("metrics") or {}
    if "defense_effectiveness" not in metrics:
        errors.append("missing_defense_effectiveness")
    else:
        eff = float(metrics["defense_effectiveness"])
        if not (0.45 <= eff <= 0.97):
            errors.append(f"efficacy_out_of_range:{eff}")
    lat = session.get("latencies") or {}
    for lk in ("detection_s", "defense_s", "recovery_s", "attack_to_recover_s"):
        if lat.get(lk) is None:
            errors.append(f"missing_latency:{lk}")
    cmp_ = session.get("comparison") or {}
    if "with_defense" not in cmp_ or "without_defense" not in cmp_:
        errors.append("missing_comparison")
    rec = session.get("recommendation") or {}
    if rec.get("advisory_only") is not True:
        errors.append("recommendation_not_advisory")
    return errors


def validate_families(
    families: tuple[str, ...] | list[str] = DEFAULT_FAMILIES,
    *,
    check_determinism: bool = True,
) -> dict[str, Any]:
    """Run simulated cyber-range validation across attack families."""
    efficacy_cfg = configured_efficacy_table()
    results: list[dict[str, Any]] = []
    all_ok = True

    for family in families:
        eng = SimulationEngine()
        run = run_family_to_recovered(family, engine=eng)
        final = run["final"]
        errors = validate_session(final, attack_type=family)
        if "detected" not in run["states"]:
            errors.append("missing_detected_state")

        det_ok = True
        if check_determinism:
            eng2 = SimulationEngine()
            run2 = run_family_to_recovered(family, engine=eng2)
            a = final.get("latencies") or {}
            b = (run2["final"].get("latencies") or {})
            if a != b:
                errors.append("non_deterministic_latencies")
                det_ok = False
            if run["states"] != run2["states"]:
                errors.append("non_deterministic_states")
                det_ok = False

        ok = len(errors) == 0
        all_ok = all_ok and ok
        results.append(
            {
                "attack_type": family,
                "ok": ok,
                "errors": errors,
                "final_state": final.get("state"),
                "states": run["states"],
                "assumed_efficacy_config": efficacy_cfg.get(family),
                "simulated_defense_effectiveness": (final.get("metrics") or {}).get(
                    "defense_effectiveness"
                ),
                "latencies": final.get("latencies"),
                "deterministic": det_ok if check_determinism else None,
                "advisory_only": final.get("advisory_only"),
            }
        )

    return {
        "tool": "cyber_range_sim_validate",
        "mode": "controlled_visualization",
        "live_cyber_range": False,
        "live_mitigation": False,
        "efficacy_are_assumptions": True,
        "families": list(families),
        "assumed_efficacy_table": efficacy_cfg,
        "all_ok": all_ok,
        "results": results,
        "notes": [
            "This validates the in-process simulation state machine and advisory framing.",
            "It is not evidence of real-world mitigation performance or a physical cyber range.",
            "defense_effectiveness comes from config.yaml assumptions adjusted by sim heuristics.",
        ],
    }
