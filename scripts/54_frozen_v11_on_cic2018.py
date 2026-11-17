"""EXP-009 (completed): score the FROZEN v1.1 models on CSE-CIC-IDS2018 — no retraining.

Report limitation #3 ("external-dataset validation skipped") and Future Work #1 ("compatible
cross-dataset evaluation under frozen preprocessing — no retrain-and-claim") are addressed
here: the frozen feature bundle, Decision Tree @0.85 and attack-only Random Forest are applied
unchanged to 2018 flows mapped onto the 2017 MachineLearningCVE schema.

Outputs:
  research_artifacts/frozen_v11_on_cic2018.json
  models/trained_models/cross_dataset_status.json   (replaces the old "skipped" status)
"""
from __future__ import annotations

import json
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")
warnings.filterwarnings("ignore")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import f1_score, precision_score, recall_score  # noqa: E402

from ml.prediction.predictor import IDSPredictor  # noqa: E402
from research.data import ARTIFACT_DIR, feature_columns, load_cic2017, load_cic2018  # noqa: E402

SEED = 42
PER_LABEL = 20_000
BENIGN_N = 200_000


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--cic2018-version", type=int, default=2, choices=[1, 2])
    version = ap.parse_args().cic2018_version
    feats = feature_columns(load_cic2017().head(1))
    d18 = load_cic2018(feats, version=version)
    parts = []
    for lab, g in d18.groupby("fine_label", observed=True):
        n = BENIGN_N if (g["family"] == "BENIGN").all() else PER_LABEL
        parts.append(g.sample(n=min(n, len(g)), random_state=SEED))
    test = pd.concat(parts, ignore_index=True)
    frame = test[feats].copy()
    frame["Fwd Header Length.1"] = frame["Fwd Header Length"]

    pred = IDSPredictor.from_artifacts()
    out = pred.predict_many_vectorized(frame)
    is_attack = np.array([p.is_attack for p in out])
    p_attack = np.array([p.binary_proba_attack for p in out])
    a_type = np.array([p.attack_type for p in out], dtype=object)
    fam = test["family"].astype(str).to_numpy()
    fine = test["fine_label"].astype(str).to_numpy()
    y = (fam != "BENIGN").astype(int)

    known = {"Bot", "BruteForce", "DDoS", "DoS", "PortScan", "WebAttack"}
    per_label = []
    for lab in sorted(set(fine)):
        m = fine == lab
        f = fam[m][0]
        row = {"label": lab, "family": f, "n": int(m.sum()),
               "family_known_to_v11": f in known or f == "BENIGN",
               "alert_rate": float(is_attack[m].mean()),
               "median_p_attack": float(np.median(p_attack[m]))}
        if f != "BENIGN":
            row["family_match_rate"] = float((a_type[m] == f).mean())
            row["predicted_types"] = pd.Series(np.where(is_attack[m], a_type[m], "BENIGN")).value_counts().head(4).to_dict()
        per_label.append(row)

    ref = json.loads((ROOT / "models/trained_models/training_report.json").read_text(encoding="utf-8"))
    iid_f1 = ref["binary"]["test"]["f1"]  # frozen v1.1 IID test F1 (training_report.json → binary.test.f1)

    result = {
        "experiment": "cross_dataset_validation",
        "status": "completed",
        "train_dataset": "CICIDS2017 (frozen v1.1 artifacts, unchanged)",
        "external_dataset": "CSE-CIC-IDS2018 (Processed Traffic Data for ML Algorithms, mapped to 2017 schema)",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sampling": {"benign": BENIGN_N, "per_attack_label": PER_LABEL, "seed": SEED,
                     "cic2018_sample_version": version,
                     "benign_days": sorted(test.loc[test["family"] == "BENIGN", "day"].astype(str).unique().tolist())},
        "n": {"benign": int((y == 0).sum()), "attack": int(y.sum())},
        "binary": {
            "precision": float(precision_score(y, is_attack, zero_division=0)),
            "recall": float(recall_score(y, is_attack, zero_division=0)),
            "f1": float(f1_score(y, is_attack, zero_division=0)),
            "benign_fpr": float(is_attack[y == 0].mean()),
            "iid_cicids2017_f1_reference": iid_f1,
        },
        "per_label": per_label,
        "interpretation": (
            "Frozen CICIDS2017 models transferred to a different network, year and CICFlowMeter version. "
            "Performance under this shift is the honest external-validity number; it is NOT comparable to "
            "the IID score and no retraining or threshold tuning was done on 2018 data."
        ),
    }
    name = "frozen_v11_on_cic2018.json" if version == 1 else f"frozen_v11_on_cic2018_v{version}.json"
    (ARTIFACT_DIR / name).write_text(json.dumps(result, indent=2), encoding="utf-8")
    if version != 1:  # keep the EXP-009 status file pointing at its original evidence
        print(json.dumps(result["binary"], indent=1))
        return
    status_path = ROOT / "models/trained_models/cross_dataset_status.json"
    status_path.write_text(json.dumps({
        "experiment": "cross_dataset_validation", "train_dataset": "CICIDS2017",
        "external_dataset_dir": "CSE-CIC-IDS2018", "status": "completed",
        "binary": result["binary"], "n": result["n"],
        "details": "research_artifacts/frozen_v11_on_cic2018.json",
        "note": "Frozen v1.1 models scored without retraining (scripts/54_frozen_v11_on_cic2018.py).",
    }, indent=2), encoding="utf-8")
    print(json.dumps(result["binary"], indent=1))
    for r in per_label:
        print(f"{r['label']:28s} {r['family']:12s} n={r['n']:6d} alert={r['alert_rate']:.3f} "
              f"match={r.get('family_match_rate', float('nan')):.3f}")


if __name__ == "__main__":
    main()
