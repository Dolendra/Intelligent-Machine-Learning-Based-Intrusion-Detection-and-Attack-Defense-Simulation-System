"""Evaluate SHAP vs LIME vs model importance agreement (sample-based research)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services import pipeline as svc
from explainability.evaluation import compare_explanations, feature_ranks, spearman_rank_correlation
from ids_config import load_config, resolve_path


def _model_importance(predictor, is_attack: bool, top_k: int = 10) -> list[dict]:
    model = predictor.multiclass_model if is_attack else predictor.binary_model
    task = "multiclass" if is_attack else "binary"
    names = predictor.bundle.selected_for(task)
    if hasattr(model, "feature_importances_"):
        vals = np.asarray(model.feature_importances_, dtype=float)
    elif hasattr(model, "coef_"):
        coef = np.asarray(model.coef_, dtype=float)
        vals = np.abs(coef[0] if coef.ndim > 1 else coef)
    else:
        return []
    n = min(len(names), len(vals))
    pairs = sorted(zip(names[:n], vals[:n]), key=lambda kv: abs(kv[1]), reverse=True)[:top_k]
    return [{"feature": f, "contribution": float(v)} for f, v in pairs]


def main() -> None:
    cfg = load_config()
    predictor = svc.get_predictor()
    if predictor is None:
        raise SystemExit("Models not ready — train first.")

    try:
        demo = svc.load_demo_flows(n=8)
        samples = [d["features"] for d in demo.get("items", [])]
    except Exception:
        samples = []
    if not samples:
        samples = [svc.sample_feature_template()]

    rows = []
    for i, feats in enumerate(samples[:8]):
        shap = svc.run_explain(feats, method="shap", top_k=10, allow_missing_features=True)
        lime = svc.run_explain(feats, method="lime", top_k=10, allow_missing_features=True)
        pred = predictor.predict_row(feats, allow_missing=True)
        importance = _model_importance(predictor, pred.is_attack)
        agreement = compare_explanations(
            shap.get("top_features", []),
            lime.get("top_features", []),
            importance,
            top_k=10,
        )
        # Stability: re-run SHAP and compare ranks
        shap2 = svc.run_explain(feats, method="shap", top_k=10, allow_missing_features=True)
        stability = spearman_rank_correlation(
            feature_ranks(shap.get("top_features", [])),
            feature_ranks(shap2.get("top_features", [])),
        )
        rows.append(
            {
                "index": i,
                "prediction": shap.get("prediction") or pred.attack_type,
                "shap_method": shap.get("actual_method", shap.get("method")),
                "shap_fallback": shap.get("fallback_used", False),
                "agreement": agreement,
                "shap_stability_spearman": stability,
            }
        )

    out_dir = resolve_path(cfg["models"]["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "xai_agreement_report.json"
    report = {
        "n_samples": len(rows),
        "note": "Sample-based XAI agreement; not a claim of ground-truth feature causality.",
        "results": rows,
    }
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    for r in rows:
        a = r["agreement"].get("shap_vs_lime", {})
        print(
            f"[{r['index']}] {r['prediction']}: SHAP↔LIME ρ={a.get('spearman')} "
            f"jaccard5={a.get('top5_jaccard')} stability={r['shap_stability_spearman']}"
        )


if __name__ == "__main__":
    main()
