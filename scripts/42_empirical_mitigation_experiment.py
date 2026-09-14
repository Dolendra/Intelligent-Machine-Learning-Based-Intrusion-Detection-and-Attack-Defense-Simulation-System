"""P11 — Run controlled empirical mitigation experiments (CONTROLLED adapter only).

Writes:
  models/trained_models/empirical_mitigation_report.json
  results/empirical/empirical_mitigation_latest.json

Does **not** modify simulation assumptions or frozen ML artifacts.
Does **not** enable LIVE firewall/EDR adapters.
"""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from empirical.experiment import SCENARIOS, run_experiment
from ids_config import load_config, resolve_path


def _git_commit() -> str | None:
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL)
            .decode()
            .strip()
        )
    except Exception:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="P11 empirical mitigation (CONTROLLED lab)")
    parser.add_argument("--repetitions", type=int, default=10)
    parser.add_argument(
        "--detection-mode",
        choices=["frozen_ml", "label_oracle"],
        default="frozen_ml",
        help="frozen_ml scores CICIDS samples; label_oracle is for CI without data",
    )
    parser.add_argument("--quick", action="store_true", help="3 repetitions, oracle detection")
    args = parser.parse_args()

    reps = 3 if args.quick else max(1, args.repetitions)
    detection_mode = "label_oracle" if args.quick else args.detection_mode

    cfg = load_config()
    out_dir = resolve_path(cfg["models"]["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    results_dir = ROOT / "results" / "empirical"
    results_dir.mkdir(parents=True, exist_ok=True)

    meta_path = out_dir / "model_metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}

    print(f"Running empirical mitigation: reps={reps} detection={detection_mode}")
    exp = run_experiment(
        scenarios=SCENARIOS,
        repetitions=reps,
        detection_mode=detection_mode,  # type: ignore[arg-type]
        model_dir=out_dir,
    )

    report = {
        "experiment": "empirical_mitigation_p11",
        "phase": "P11",
        "experiment_ids": [s.experiment_id for s in SCENARIOS],
        "status": "ok",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),
        "model_version": meta.get("model_version") or cfg.get("models", {}).get("model_version"),
        "detection_mode": detection_mode,
        "repetitions": reps,
        "environment": {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "isolation": "in-process controlled test plane (no real network packets)",
        },
        "defense_configuration": {
            "modes_compared": exp["conditions"],
            "adapter": "test_network",
            "execution_mode": "CONTROLLED",
            "live_firewall_edr": False,
            "approval_required": True,
            "verification_required": True,
            "rollback_after_trial": True,
        },
        "honesty": {
            "simulation_preserved": True,
            "simulation_assumptions_path": "config.yaml → simulation.defense_effectiveness",
            "measurement_definition": (
                "mitigation_effectiveness = (pre_attack_accepted_rate - post_attack_accepted_rate) "
                "/ pre_attack_accepted_rate under the controlled test plane"
            ),
            "not_a_claim_of": [
                "production firewall/EDR effectiveness",
                "live-network mitigation rates",
                "zero-day defense",
            ],
        },
        "simulation_vs_measurement": {
            "simulation": "Defense effectiveness = modeled assumption (visualization)",
            "p11_experiment": "Defense effectiveness = measured observation on CONTROLLED test plane",
        },
        "comparisons": exp["comparisons"],
        "aggregates": exp["aggregates"],
        "raw_trials": exp["raw_trials"],
        "limitations": [
            "CONTROLLED TestNetworkAdapter only — no real firewall/EDR enforcement.",
            "Traffic is synthetic connection attempts inside the process, not NIC packets.",
            "Service availability is a benign-probe proxy, not an application SLA.",
            "cpu_proxy_load is an accepted-attack/capacity proxy, not OS CPU.",
            "Frozen-ML detection uses sampled CICIDS flows, not live PCAP from the lab topology.",
            "Simulation assumption values in config.yaml were not modified to match measurements.",
        ],
        "conclusions_template": [
            "Compare no_defense vs recommendation_only vs controlled_response blocked rates.",
            "Report measured_mitigation_effectiveness mean±stdev for controlled_response.",
            "Keep simulation assumptions alongside measurements; explain any delta.",
        ],
    }

    # Human-readable summary conclusions from data
    conclusions = []
    for name, cmp_ in exp["comparisons"].items():
        conclusions.append(
            {
                "scenario": name,
                "statement": (
                    f"Under the controlled lab, {name}: no_defense blocked_rate~="
                    f"{cmp_.get('no_defense_post_attack_blocked_rate_mean')}, "
                    f"recommendation_only~={cmp_.get('recommendation_only_post_attack_blocked_rate_mean')}, "
                    f"controlled_response~={cmp_.get('controlled_response_post_attack_blocked_rate_mean')}; "
                    f"measured effectiveness~={cmp_.get('controlled_measured_effectiveness_mean')} "
                    f"vs simulation assumption {cmp_.get('simulation_assumption')} "
                    f"(delta measured-sim ~={cmp_.get('delta_measured_minus_simulation')})."
                ),
            }
        )
    report["conclusions"] = conclusions

    out_json = out_dir / "empirical_mitigation_report.json"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    latest = results_dir / "empirical_mitigation_latest.json"
    latest.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"wrote": str(out_json), "latest": str(latest), "reps": reps}, indent=2))
    for c in conclusions:
        print(c["statement"])


if __name__ == "__main__":
    main()
