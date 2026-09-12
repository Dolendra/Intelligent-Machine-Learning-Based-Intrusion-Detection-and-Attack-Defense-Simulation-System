"""Build global + attack-specific importance artifacts for the Model Lab."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.services import pipeline as svc
from explainability.global_importance import attack_specific_from_explanations, global_model_importance
from ids_config import load_config, resolve_path


def main() -> None:
    cfg = load_config()
    out_dir = resolve_path(cfg["models"]["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    predictor = svc.get_predictor()
    if predictor is None:
        raise SystemExit("Models not ready — train first.")

    global_imp = global_model_importance(predictor, top_k=15)

    explanations = []
    try:
        demo = svc.load_demo_flows(n=24)
        items = demo.get("items") or []
    except Exception:
        items = []
    for item in items:
        feats = item.get("features") or {}
        try:
            exp = svc.run_explain(feats, method="shap", top_k=10, allow_missing_features=True)
            explanations.append(exp)
        except Exception:
            continue

    attack_imp = attack_specific_from_explanations(explanations, top_k=8)
    report = {
        "experiment": "global_and_attack_shap",
        "status": "ok",
        "global": global_imp,
        "attack_specific": attack_imp,
        "samples_explained": len(explanations),
    }
    path = out_dir / "global_shap_summary.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"wrote": str(path), "samples": len(explanations)}, indent=2))


if __name__ == "__main__":
    main()
