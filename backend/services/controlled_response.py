"""Controlled response planning — advisory + optional simulation preview (not live mitigation)."""
from __future__ import annotations

from typing import Any

from security.recommendations.engine import recommend
from security.risk.engine import compute_risk


def build_response_plan(
    *,
    attack_type: str,
    severity: str | None = None,
    confidence: float | None = None,
    traffic_intensity: float | None = None,
    certainty: str | None = None,
    is_attack: bool | None = None,
    asset_criticality: float | None = None,
    risk_score: float | None = None,
    start_simulation: bool = False,
    incident_id: str | None = None,
) -> dict[str, Any]:
    """Compose recommendation + optional sim preview. Never executes network controls."""
    attack_flag = True if is_attack is None else bool(is_attack)
    if attack_type == "BENIGN":
        attack_flag = False

    conf = 0.9 if confidence is None else float(confidence)
    intensity = 0.5 if traffic_intensity is None else float(traffic_intensity)

    recommendation = recommend(
        attack_type,
        severity,
        confidence=conf,
        traffic_intensity=intensity,
        certainty=certainty,
        is_attack=attack_flag,
    )
    risk = compute_risk(
        attack_type,
        conf,
        attack_flag,
        intensity,
        asset_criticality=asset_criticality,
    )
    if risk_score is not None:
        risk = {**risk, "risk_score": float(risk_score), "risk_score_override": True}

    simulation = None
    if start_simulation and attack_flag:
        from simulation.engine.core import simulation_engine

        simulation = simulation_engine.start(
            attack_type,
            conf,
            incident_id=incident_id,
            risk_score=float(risk.get("risk_score", risk_score or 50.0)),
            severity=recommendation.get("severity") or severity,
            traffic_intensity=intensity,
            asset_criticality=asset_criticality,
        )

    from security.response.planner import plan_action_type

    suggested = plan_action_type(
        attack_type,
        rule_actions=list(recommendation.get("rule_actions") or []),
        severity=recommendation.get("severity") or severity,
    )

    return {
        "mode": "dry_run_approval",
        "live_mitigation": False,
        "advisory_only": True,
        "phase": "P3",
        "attack_type": attack_type,
        "recommendation": recommendation,
        "risk": risk,
        "simulation": simulation,
        "suggested_action_type": suggested.value,
        "next_steps": [
            "Review recommendation with an analyst (decision support).",
            "Propose via POST /api/response/actions/propose (DRY_RUN default, or CONTROLLED test adapter).",
            "Dry-run → APPROVE/REJECT → adapter execute → verify → optional rollback/expire.",
            "LIVE firewall/EDR adapters remain disabled in P3.",
        ],
        "disclaimer": (
            "P3 controlled response uses dry-run / simulated test adapters with human approval. "
            "Aegis IDS does not automatically apply real firewall, WAF, or host isolation actions."
        ),
    }
