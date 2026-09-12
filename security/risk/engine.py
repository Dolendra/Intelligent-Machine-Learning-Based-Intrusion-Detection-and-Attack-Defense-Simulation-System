"""Risk / severity scoring for detected attacks."""
from __future__ import annotations

from typing import Any

from ids_config import load_config


def severity_label(score: float) -> str:
    cfg = load_config()
    bands = cfg["risk"]["bands"]
    score = max(0.0, min(100.0, float(score)))
    for name, (lo, hi) in bands.items():
        if lo <= score <= hi:
            return name.upper()
    return "MEDIUM"


def compute_risk(
    attack_type: str,
    confidence: float,
    is_attack: bool,
    traffic_intensity: float | None = None,
) -> dict[str, Any]:
    """
    Combine attack-family base severity + model confidence + optional intensity.

    Returns a score in 0–100 and a severity band. Thresholds are configurable
    in config.yaml and are project conventions, not universal standards.
    """
    cfg = load_config()
    if not is_attack or attack_type == "BENIGN":
        return {
            "risk_score": 0,
            "severity": "LOW",
            "factors": {
                "attack_base": 0,
                "confidence": float(confidence),
                "intensity": 0.0,
            },
        }

    base_map = cfg["risk"]["attack_base"]
    base = float(base_map.get(attack_type, base_map.get("Other", 50)))
    conf = max(0.0, min(1.0, float(confidence)))
    intensity = 0.5 if traffic_intensity is None else max(0.0, min(1.0, float(traffic_intensity)))

    # Weighted blend: family severity dominates, then confidence, then intensity
    score = 0.55 * base + 0.30 * (conf * 100.0) + 0.15 * (intensity * 100.0)
    score = round(max(0.0, min(100.0, score)), 1)

    return {
        "risk_score": score,
        "severity": severity_label(score),
        "factors": {
            "attack_base": base,
            "confidence": conf,
            "intensity": intensity,
        },
    }
