"""P11 empirical mitigation experiment runner (CONTROLLED adapter only)."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from empirical.controlled_plane import ControlledTestPlane
from empirical.detection import DetectionMode, FrozenDetector, run_detection
from empirical.metrics import mitigation_effectiveness, summarize
from security.response.adapters import reset_test_adapter
from security.response.service import approve_action, propose_action, rollback_action, run_dry_run
from security.response.store import response_store
from security.response.types import ActionStatus

Condition = Literal["no_defense", "recommendation_only", "controlled_response"]


@dataclass
class Timeline:
    """Wall/perf timeline slots. Only populate what is actually measured."""

    t0_traffic_start: float | None = None
    t1_attack_detectable: float | None = None
    t2_aegis_detect: float | None = None
    t3_recommendation: float | None = None
    t4_action_proposed: float | None = None
    t5_approval: float | None = None
    t6_response_executed: float | None = None
    t7_response_verified: float | None = None
    t8_traffic_recovered: float | None = None

    def latencies_s(self) -> dict[str, float | None]:
        def d(a: float | None, b: float | None) -> float | None:
            if a is None or b is None:
                return None
            return round(a - b, 6)

        return {
            "detection_latency_s": d(self.t2_aegis_detect, self.t0_traffic_start),
            "decision_latency_s": d(self.t4_action_proposed, self.t2_aegis_detect),
            "approval_latency_s": d(self.t5_approval, self.t4_action_proposed),
            "response_latency_s": d(self.t6_response_executed, self.t5_approval),
            "verify_latency_s": d(self.t7_response_verified, self.t6_response_executed),
            "mitigation_latency_s": d(self.t6_response_executed, self.t0_traffic_start),
            "recovery_latency_s": d(self.t8_traffic_recovered, self.t6_response_executed),
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "marks_perf_counter": {
                "t0_traffic_start": self.t0_traffic_start,
                "t1_attack_detectable": self.t1_attack_detectable,
                "t2_aegis_detect": self.t2_aegis_detect,
                "t3_recommendation": self.t3_recommendation,
                "t4_action_proposed": self.t4_action_proposed,
                "t5_approval": self.t5_approval,
                "t6_response_executed": self.t6_response_executed,
                "t7_response_verified": self.t7_response_verified,
                "t8_traffic_recovered": self.t8_traffic_recovered,
            },
            "derived_latencies_s": self.latencies_s(),
        }


@dataclass
class ScenarioSpec:
    name: str
    attack_type: str
    experiment_id: str
    pre_attack: int = 40
    pre_benign: int = 10
    post_attack: int = 40
    post_benign: int = 10
    risk_score: float = 92.0
    severity: str = "CRITICAL"


SCENARIOS: list[ScenarioSpec] = [
    ScenarioSpec(name="ddos_block_source", attack_type="DDoS", experiment_id="EXP-018"),
    ScenarioSpec(name="dos_rate_limit", attack_type="DoS", experiment_id="EXP-019", risk_score=78.0, severity="HIGH"),
]


@dataclass
class TrialResult:
    trial: int
    condition: Condition
    scenario: str
    attack_type: str
    timeline: Timeline
    detection: dict[str, Any]
    pre: dict[str, Any]
    post: dict[str, Any]
    action: dict[str, Any] | None
    measured_mitigation_effectiveness: float | None
    simulation_assumption: float | None
    adapter_snapshot: dict[str, Any]
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "trial": self.trial,
            "condition": self.condition,
            "scenario": self.scenario,
            "attack_type": self.attack_type,
            "timeline": self.timeline.as_dict(),
            "detection": self.detection,
            "pre_window": self.pre,
            "post_window": self.post,
            "action": self.action,
            "measured_mitigation_effectiveness": self.measured_mitigation_effectiveness,
            "simulation_assumption": self.simulation_assumption,
            "adapter_snapshot": self.adapter_snapshot,
            "notes": self.notes,
        }


def _sim_assumption(attack_type: str) -> float | None:
    try:
        from ids_config import load_config

        cfg = load_config()
        return float((cfg.get("simulation") or {}).get("defense_effectiveness", {}).get(attack_type))
    except Exception:
        return None


def run_trial(
    *,
    scenario: ScenarioSpec,
    condition: Condition,
    trial: int,
    plane: ControlledTestPlane,
    detection_mode: DetectionMode,
    model_dir: Path | None,
    detector: FrozenDetector | None = None,
) -> TrialResult:
    response_store.clear()
    reset_test_adapter()
    plane.reset_counters()

    tl = Timeline()
    notes: list[str] = []
    action_info: dict[str, Any] | None = None

    tl.t0_traffic_start = time.perf_counter()
    pre_stats, _ = plane.run_window(n_attack=scenario.pre_attack, n_benign=scenario.pre_benign)
    tl.t1_attack_detectable = time.perf_counter()

    det = run_detection(
        attack_type=scenario.attack_type,
        mode=detection_mode,
        model_dir=model_dir,
        detector=detector,
    )
    tl.t2_aegis_detect = time.perf_counter()
    if not det.detected:
        notes.append("Detection did not fire; post-window still measured for honesty.")

    # Recommendation generation (planner via propose fields — timestamp only)
    tl.t3_recommendation = time.perf_counter()

    if condition == "no_defense":
        notes.append("No response proposed or executed.")
    elif condition == "recommendation_only":
        prop = propose_action(
            attack_type=scenario.attack_type,
            severity=scenario.severity,
            risk_score=scenario.risk_score,
            source_ip=plane.attacker_ip,
            mode="CONTROLLED",
            actor="p11_analyst",
            source="empirical_p11",
        )
        tl.t4_action_proposed = time.perf_counter()
        dry = run_dry_run(prop["action_id"], actor="p11_analyst")
        action_info = {"proposed": prop, "dry_run": dry["dry_run"], "approved": False}
        notes.append("Recommendation + dry-run only; CONTROLLED state not applied.")
    else:  # controlled_response
        prop = propose_action(
            attack_type=scenario.attack_type,
            severity=scenario.severity,
            risk_score=scenario.risk_score,
            source_ip=plane.attacker_ip,
            mode="CONTROLLED",
            actor="p11_analyst",
            source="empirical_p11",
        )
        tl.t4_action_proposed = time.perf_counter()
        run_dry_run(prop["action_id"], actor="p11_analyst")
        out = approve_action(prop["action_id"], actor="p11_responder")
        tl.t5_approval = time.perf_counter()
        # approve_action executes immediately
        tl.t6_response_executed = tl.t5_approval
        status = out["action"]["status"]
        if status in {ActionStatus.ACTIVE.value, ActionStatus.VERIFIED.value}:
            tl.t7_response_verified = time.perf_counter()
        action_info = {
            "proposed": {k: prop[k] for k in ("action_id", "action_type", "target", "mode", "adapter")},
            "execution": out.get("execution"),
            "status": status,
            "approved": True,
        }
        notes.append("Approved CONTROLLED response applied via TestNetworkAdapter.")

    post_stats, _ = plane.run_window(n_attack=scenario.post_attack, n_benign=scenario.post_benign)

    # Recovery: rollback when we applied a reversible control
    if condition == "controlled_response" and action_info and action_info.get("approved"):
        aid = action_info["proposed"]["action_id"]
        try:
            rb = rollback_action(aid, actor="p11_responder")
            action_info["rollback"] = {"status": rb["action"]["status"]}
            # Measure availability after rollback
            recover_stats, _ = plane.run_window(n_attack=10, n_benign=5)
            tl.t8_traffic_recovered = time.perf_counter()
            action_info["post_rollback_window"] = recover_stats.as_dict()
        except Exception as exc:  # noqa: BLE001
            notes.append(f"Rollback skipped/failed: {exc}")

    eff = mitigation_effectiveness(
        baseline_attack_accepted_rate=pre_stats.as_dict()["attack_accepted_rate"],
        defended_attack_accepted_rate=post_stats.as_dict()["attack_accepted_rate"],
    )

    return TrialResult(
        trial=trial,
        condition=condition,
        scenario=scenario.name,
        attack_type=scenario.attack_type,
        timeline=tl,
        detection={
            "detected": det.detected,
            "mode": det.mode,
            "confidence": det.confidence,
            "latency_s": round(det.latency_s, 6),
            "n_flows_scored": det.n_flows_scored,
            "detail": det.detail,
        },
        pre=pre_stats.as_dict(),
        post=post_stats.as_dict(),
        action=action_info,
        measured_mitigation_effectiveness=eff,
        simulation_assumption=_sim_assumption(scenario.attack_type),
        adapter_snapshot=plane.adapter.snapshot(),
        notes=notes,
    )


def run_experiment(
    *,
    scenarios: list[ScenarioSpec] | None = None,
    conditions: list[Condition] | None = None,
    repetitions: int = 10,
    detection_mode: DetectionMode = "frozen_ml",
    model_dir: Path | None = None,
) -> dict[str, Any]:
    scenarios = scenarios or SCENARIOS
    conditions = conditions or ["no_defense", "recommendation_only", "controlled_response"]
    plane = ControlledTestPlane()
    detector = FrozenDetector(model_dir=model_dir) if model_dir and detection_mode == "frozen_ml" else None
    if detector is not None:
        detector.load()
    raw: list[dict[str, Any]] = []

    for scenario in scenarios:
        for condition in conditions:
            for trial in range(1, repetitions + 1):
                result = run_trial(
                    scenario=scenario,
                    condition=condition,
                    trial=trial,
                    plane=plane,
                    detection_mode=detection_mode,
                    model_dir=model_dir,
                    detector=detector,
                )
                raw.append(result.as_dict())

    # Aggregate by scenario × condition
    aggregates: dict[str, Any] = {}
    for scenario in scenarios:
        aggregates[scenario.name] = {}
        for condition in conditions:
            subset = [r for r in raw if r["scenario"] == scenario.name and r["condition"] == condition]
            aggregates[scenario.name][condition] = {
                "n_trials": len(subset),
                "measured_mitigation_effectiveness": summarize(
                    [r["measured_mitigation_effectiveness"] for r in subset]
                ),
                "post_attack_blocked_rate": summarize(
                    [r["post_window"]["attack_blocked_rate"] for r in subset]
                ),
                "post_service_availability": summarize(
                    [r["post_window"]["service_availability"] for r in subset]
                ),
                "post_cpu_proxy_load": summarize([r["post_window"]["cpu_proxy_load"] for r in subset]),
                "detection_latency_s": summarize(
                    [r["timeline"]["derived_latencies_s"]["detection_latency_s"] for r in subset]
                ),
                "decision_latency_s": summarize(
                    [r["timeline"]["derived_latencies_s"]["decision_latency_s"] for r in subset]
                ),
                "response_latency_s": summarize(
                    [r["timeline"]["derived_latencies_s"]["response_latency_s"] for r in subset]
                ),
                "mitigation_latency_s": summarize(
                    [r["timeline"]["derived_latencies_s"]["mitigation_latency_s"] for r in subset]
                ),
                "simulation_assumption": subset[0]["simulation_assumption"] if subset else None,
            }

    comparisons: dict[str, Any] = {}
    for scenario in scenarios:
        nd = aggregates[scenario.name].get("no_defense", {})
        cr = aggregates[scenario.name].get("controlled_response", {})
        ro = aggregates[scenario.name].get("recommendation_only", {})
        comparisons[scenario.name] = {
            "attack_type": scenario.attack_type,
            "experiment_id": scenario.experiment_id,
            "no_defense_post_attack_blocked_rate_mean": (nd.get("post_attack_blocked_rate") or {}).get("mean"),
            "recommendation_only_post_attack_blocked_rate_mean": (ro.get("post_attack_blocked_rate") or {}).get(
                "mean"
            ),
            "controlled_response_post_attack_blocked_rate_mean": (cr.get("post_attack_blocked_rate") or {}).get(
                "mean"
            ),
            "controlled_measured_effectiveness_mean": (cr.get("measured_mitigation_effectiveness") or {}).get(
                "mean"
            ),
            "simulation_assumption": cr.get("simulation_assumption"),
            "delta_measured_minus_simulation": (
                None
                if cr.get("simulation_assumption") is None
                or (cr.get("measured_mitigation_effectiveness") or {}).get("mean") is None
                else round(
                    float((cr.get("measured_mitigation_effectiveness") or {})["mean"])
                    - float(cr["simulation_assumption"]),
                    6,
                )
            ),
        }

    return {
        "raw_trials": raw,
        "aggregates": aggregates,
        "comparisons": comparisons,
        "repetitions": repetitions,
        "conditions": list(conditions),
        "scenarios": [s.name for s in scenarios],
    }
