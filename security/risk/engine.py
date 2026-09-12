"""Risk / severity scoring for detected attacks."""
from __future__ import annotations

from typing import Any

from ids_config import load_config


def severity_label(score: float) -> str:
    """Map score to severity using lower-bound cuts (handles fractional scores).

    Config bands like low:[0,30], medium:[31,60] become:
    score < 31 → LOW, < 61 → MEDIUM, < 81 → HIGH, else CRITICAL.
    """
    cfg = load_config()
    bands = cfg["risk"]["bands"]
    score = max(0.0, min(100.0, float(score)))
    ordered: list[tuple[str, float]] = []
    for name in ("low", "medium", "high", "critical"):
        if name in bands:
            ordered.append((name, float(bands[name][0])))
    if not ordered:
        ordered = [("low", 0.0), ("medium", 31.0), ("high", 61.0), ("critical", 81.0)]
    ordered.sort(key=lambda x: x[1])
    label = ordered[0][0]
    for name, lo in ordered:
        if score >= lo:
            label = name
    return label.upper()


def compute_risk(
    attack_type: str,
    confidence: float,
    is_attack: bool,
    traffic_intensity: float | None = None,
    asset_criticality: float | None = None,
) -> dict[str, Any]:
    """
    Combine attack-family base severity + model confidence + intensity + asset criticality.

    Returns a score in 0–100 and a severity band. Weights and thresholds are
    configurable project conventions in config.yaml — not universal standards.
    """
    cfg = load_config()
    weights = cfg.get("risk", {}).get("weights", {})
    w_base = float(weights.get("attack_base", 0.50))
    w_conf = float(weights.get("confidence", 0.25))
    w_int = float(weights.get("intensity", 0.15))
    w_asset = float(weights.get("asset_criticality", 0.10))
    total_w = w_base + w_conf + w_int + w_asset
    if total_w <= 0:
        w_base, w_conf, w_int, w_asset, total_w = 0.50, 0.25, 0.15, 0.10, 1.0
    w_base, w_conf, w_int, w_asset = (w / total_w for w in (w_base, w_conf, w_int, w_asset))

    if not is_attack or attack_type == "BENIGN":
        return {
            "risk_score": 0,
            "severity": "LOW",
            "factors": {
                "attack_base": 0,
                "confidence": float(confidence),
                "intensity": 0.0,
                "asset_criticality": float(asset_criticality or 0.5),
            },
            "weights": {
                "attack_base": w_base,
                "confidence": w_conf,
                "intensity": w_int,
                "asset_criticality": w_asset,
            },
        }

    base_map = cfg["risk"]["attack_base"]
    base = float(base_map.get(attack_type, base_map.get("Other", 50)))
    conf = max(0.0, min(1.0, float(confidence)))
    intensity = 0.5 if traffic_intensity is None else max(0.0, min(1.0, float(traffic_intensity)))
    # Asset criticality: accept 1–5 scale or 0–1; default mid-tier (3/5).
    if asset_criticality is None:
        asset_01 = 0.6
    else:
        ac = float(asset_criticality)
        asset_01 = max(0.0, min(1.0, ac / 5.0 if ac > 1.0 else ac))

    score = (
        w_base * base
        + w_conf * (conf * 100.0)
        + w_int * (intensity * 100.0)
        + w_asset * (asset_01 * 100.0)
    )
    score = round(max(0.0, min(100.0, score)), 1)

    return {
        "risk_score": score,
        "severity": severity_label(score),
        "factors": {
            "attack_base": base,
            "confidence": conf,
            "intensity": intensity,
            "asset_criticality": asset_01,
        },
        "weights": {
            "attack_base": w_base,
            "confidence": w_conf,
            "intensity": w_int,
            "asset_criticality": w_asset,
        },
    }
