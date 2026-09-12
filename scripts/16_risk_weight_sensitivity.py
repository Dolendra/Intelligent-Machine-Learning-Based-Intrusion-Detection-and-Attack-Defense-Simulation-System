"""Risk weight sensitivity analysis (project conventions — not a universal standard)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from security.risk.engine import compute_risk


CONFIGS = {
    "A_severity_heavy": {"attack_base": 0.55, "confidence": 0.25, "intensity": 0.10, "asset_criticality": 0.10},
    "B_balanced": {"attack_base": 0.50, "confidence": 0.25, "intensity": 0.15, "asset_criticality": 0.10},
    "C_ops_heavy": {"attack_base": 0.35, "confidence": 0.20, "intensity": 0.25, "asset_criticality": 0.20},
}

CASES = [
    {"name": "ddos_high", "attack_type": "DDoS", "confidence": 0.97, "intensity": 0.9, "asset": 5},
    {"name": "portscan_med", "attack_type": "PortScan", "confidence": 0.8, "intensity": 0.4, "asset": 3},
    {"name": "bruteforce_unc", "attack_type": "BruteForce", "confidence": 0.55, "intensity": 0.5, "asset": 4},
    {"name": "web_low_asset", "attack_type": "WebAttack", "confidence": 0.9, "intensity": 0.6, "asset": 2},
]


def main() -> None:
    from ids_config import load_config, resolve_path
    import yaml

    cfg_path = ROOT / "config.yaml"
    base_cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    out = {"experiment": "risk_weight_sensitivity", "configs": CONFIGS, "results": {}}

    for cfg_name, weights in CONFIGS.items():
        # Temporarily mutate in-memory config used by compute_risk via load_config cache?
        # compute_risk calls load_config() each time — patch file is heavy; monkeypatch weights arg instead.
        rows = []
        for case in CASES:
            # Inline score with custom weights (mirror engine formula)
            from security.risk.engine import severity_label
            from ids_config import load_config as _lc

            attack_type = case["attack_type"]
            conf = case["confidence"]
            intensity = case["intensity"]
            asset_01 = case["asset"] / 5.0
            base_map = _lc()["risk"]["attack_base"]
            base = float(base_map.get(attack_type, 50))
            w_base, w_conf, w_int, w_asset = (
                weights["attack_base"],
                weights["confidence"],
                weights["intensity"],
                weights["asset_criticality"],
            )
            tw = w_base + w_conf + w_int + w_asset
            w_base, w_conf, w_int, w_asset = (x / tw for x in (w_base, w_conf, w_int, w_asset))
            score = round(
                w_base * base + w_conf * conf * 100 + w_int * intensity * 100 + w_asset * asset_01 * 100,
                1,
            )
            rows.append(
                {
                    "case": case["name"],
                    "risk_score": score,
                    "severity": severity_label(score),
                    "default_engine": compute_risk(
                        attack_type, conf, True, intensity, asset_criticality=case["asset"]
                    )["risk_score"],
                }
            )
        out["results"][cfg_name] = rows

    out["note"] = (
        "Weight choices are project conventions. Compare A/B/C sensitivity; justify final weights in the report."
    )
    path = resolve_path(load_config()["models"]["output_dir"]) / "risk_weight_sensitivity.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {path}")
    for name, rows in out["results"].items():
        print(name, {r["case"]: r["risk_score"] for r in rows})


if __name__ == "__main__":
    main()
