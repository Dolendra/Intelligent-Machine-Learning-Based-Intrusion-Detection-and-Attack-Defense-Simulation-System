"""Threshold sweep experiment for binary IDS operating point + uncertainty bands."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np

from ids_config import load_config, resolve_path
from ml.evaluation.metrics import evaluate_binary
from ml.features.pipeline import FeatureBundle, transform_split
from ml.models.factory import load_model
from ml.preprocessing.dataset import load_processed


def _derive_uncertainty_bands(rows: list[dict], best_thr: float) -> tuple[float, float, str]:
    """Derive uncertainty lower/upper from validation sweep evidence."""
    high_recall = [r for r in rows if r["recall"] >= 0.98]
    high_prec = [r for r in rows if r["precision"] >= 0.95]
    if high_recall:
        lower = float(min(r["threshold"] for r in high_recall))
    else:
        lower = max(0.10, best_thr - 0.20)
    if high_prec:
        upper = float(min(r["threshold"] for r in high_prec))
    else:
        upper = min(0.90, best_thr + 0.20)
    if lower >= best_thr:
        lower = max(0.10, round(best_thr - 0.15, 2))
    if upper <= best_thr:
        upper = min(0.95, round(best_thr + 0.15, 2))
    if lower >= upper:
        lower, upper = 0.30, 0.70
    reason = (
        f"lower≈thr where recall stays ≥0.98 ({lower}); "
        f"upper≈lowest thr with precision≥0.95 ({upper}); "
        f"operating={best_thr}"
    )
    return lower, upper, reason


def main() -> None:
    cfg = load_config()
    out_dir = resolve_path(cfg["models"]["output_dir"])
    bundle = FeatureBundle.load(out_dir / "feature_bundle.joblib")
    model = load_model(out_dir / "binary_best.joblib")
    val = load_processed("val")
    if len(val) > 150000:
        val = val.sample(n=150000, random_state=cfg["data"]["random_state"])
    X, y, _ = transform_split(bundle, val, task="binary")
    if not hasattr(model, "predict_proba"):
        raise SystemExit("Binary model lacks predict_proba")
    proba = model.predict_proba(X)
    classes = list(getattr(model, "classes_", [0, 1]))
    idx = classes.index(1) if 1 in classes else 1
    p = proba[:, idx]

    rows = []
    for thr in [round(x, 2) for x in np.arange(0.10, 0.95, 0.05)]:
        pred = (p >= thr).astype(int)
        m = evaluate_binary(y, pred, p)
        rows.append(
            {
                "threshold": thr,
                "precision": m["precision"],
                "recall": m["recall"],
                "f1": m["f1"],
                "fpr": m["fpr"],
                "fnr": m["fnr"],
                "pr_auc": m.get("pr_auc"),
            }
        )

    eligible = [r for r in rows if r["recall"] >= 0.95] or rows
    best = max(eligible, key=lambda r: (r["f1"], -r["fpr"]))
    lower, upper, band_reason = _derive_uncertainty_bands(rows, float(best["threshold"]))

    operating = {
        "operating_threshold": best["threshold"],
        "uncertainty_lower": lower,
        "uncertainty_upper": upper,
        "selection_method": "max_f1_among_recall_ge_0.95_else_max_f1",
        "validation_split": "val",
        "val_rows": int(len(val)),
        "band_derivation": band_reason,
    }
    report = {
        "experiment": "binary_threshold_sweep",
        "val_rows": int(len(val)),
        "suggested_threshold": best["threshold"],
        "suggested_reason": "Max F1 among thresholds with recall>=0.95 when available; else max F1",
        "current_config_threshold": cfg.get("models", {}).get("binary_threshold", 0.5),
        "certainty_bands": {
            "likely_benign_lt": lower,
            "likely_attack_gt": upper,
            "derivation": band_reason,
        },
        "operating_point": operating,
        "sweep": rows,
        "note": (
            "Writes threshold_operating_point.json for the predictor. "
            "Optionally mirror values into config.yaml models.binary_threshold / uncertainty_*."
        ),
    }
    path = out_dir / "threshold_sweep.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    (out_dir / "threshold_operating_point.json").write_text(json.dumps(operating, indent=2), encoding="utf-8")
    print(f"Wrote {path}")
    print(f"Wrote {out_dir / 'threshold_operating_point.json'}")
    print(
        f"Suggested threshold={best['threshold']} "
        f"uncertainty=[{lower}, {upper}] F1={best['f1']:.4f} Recall={best['recall']:.4f}"
    )


if __name__ == "__main__":
    main()
