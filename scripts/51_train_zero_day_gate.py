"""Train and export the production Aegis-OSR Zero-Day Gate.

* Fits the locked Aegis-OSR design (XGB K+1 classifier + kNN benign novelty, Fisher fusion,
  split-conformal calibration, Mondrian family conformity) on the CICIDS2017 IID split.
* Exports torch-free artifacts to models/trained_models/aegis_osr/.
* Evaluates on held-out test flows, including the two *natural* unknown families that the
  frozen v1.1 pipeline never saw (Infiltration, Heartbleed), and compares against the frozen
  v1.1 detector on exactly the same flows.

The frozen v1.1 models are only *read* here (for the comparison); nothing is retrained.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")
warnings.filterwarnings("ignore", category=UserWarning)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from research.data import ARTIFACT_DIR, cap_per_family, feature_columns, load_cic2017, stratified_split  # noqa: E402
from research.features import SignedLogScaler  # noqa: E402
from research.openset import BENIGN, PROPOSED, AegisOSR  # noqa: E402
from research.serving import GATE_DIR, ZeroDayGate, export_gate  # noqa: E402

SEED = 42
NATURAL_UNKNOWN = ["Infiltration", "Heartbleed"]


def _frozen_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Re-create the 78-column v1.1 schema (adds the duplicate header column)."""
    out = df.copy()
    out["Fwd Header Length.1"] = out["Fwd Header Length"]
    return out


def main() -> None:
    t0 = time.time()
    df = load_cic2017()
    feats = feature_columns(df)
    base = df[~df["family"].isin(NATURAL_UNKNOWN)]
    tr, va, te = stratified_split(base, (0.7, 0.1, 0.2), SEED)
    fams = sorted(set(base["family"].astype(str)))
    train = cap_per_family(tr, {f: (400_000 if f == BENIGN else 100_000) for f in fams}, SEED)
    val = cap_per_family(va, {f: (80_000 if f == BENIGN else 20_000) for f in fams}, SEED)
    test = pd.concat([
        cap_per_family(te, {f: (200_000 if f == BENIGN else 30_000) for f in fams}, SEED),
        df[df["family"].isin(NATURAL_UNKNOWN)],
    ], ignore_index=True)
    print(f"train={len(train):,} val={len(val):,} test={len(test):,}", flush=True)

    scaler = SignedLogScaler().fit(train[feats].to_numpy())
    model = AegisOSR(seed=SEED, alpha=0.01, with_baselines=False, knn_ref=20_000)
    model.fit(scaler.transform(train[feats].to_numpy()), train["family"].to_numpy(),
              scaler.transform(val[feats].to_numpy()), val["family"].to_numpy(), log=print)
    print(f"fit done in {time.time() - t0:.0f}s", flush=True)

    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:  # pragma: no cover
        commit = "unknown"
    metadata = {
        "name": "Aegis-OSR Zero-Day Gate",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": commit,
        "method": {
            "classifier": "XGBoost (K+1 classes: BENIGN + known families), sqrt-balanced weights",
            "novelty": "mean distance to k=5 nearest benign training flows (signed-log standardized space)",
            "fusion": "Fisher: sum of benign surprisals with exponential tail extrapolation",
            "calibration": "split-conformal on held-out benign flows → P_benign(p<=alpha) <= alpha",
            "attribution": "Mondrian (class-conditional) conformal family conformity",
        },
        "training": {
            "dataset": "CICIDS2017 MachineLearningCVE (research cache, IID stratified split seed 42)",
            "n_train": int(len(train)), "n_val": int(len(val)), "calibration_split": list(model.n_cal_),
            "known_classes": model.classes_, "knn_reference": int(len(model.knn_ref_X_)),
        },
        "advisory_only": True,
    }

    sizes = export_gate(model, scaler, feats, GATE_DIR, metadata)
    print("exported:", {k: f"{v / 1e6:.1f} MB" for k, v in sizes.items()}, flush=True)

    # ---------------------------------------------------------------- evaluation via the *served* gate
    gate = ZeroDayGate(GATE_DIR)
    t1 = time.time()
    res = gate.assess(test, explain_top=0)
    per_flow_ms = 1000 * (time.time() - t1) / len(test)
    labels = np.array([r["label"] for r in res], dtype=object)
    alerts = np.array([r["alert"] for r in res])
    fam = test["family"].astype(str).to_numpy()
    b, u = fam == BENIGN, np.isin(fam, NATURAL_UNKNOWN)
    k = ~b & ~u

    # parity check: served gate == research model on the same flows
    sc = model.score(scaler.transform(test[feats].to_numpy()))
    parity = float(np.mean((sc.pvalue[PROPOSED] <= 0.01) == alerts))

    # frozen v1.1 on the same flows
    from ml.prediction.predictor import IDSPredictor

    pred = IDSPredictor.from_artifacts()
    frozen = pred.predict_many_vectorized(_frozen_frame(test))
    f_attack = np.array([p.is_attack for p in frozen])
    f_type = np.array([p.attack_type for p in frozen], dtype=object)

    unknown_rows = []
    for name in NATURAL_UNKNOWN:
        m = fam == name
        unknown_rows.append({
            "family": name, "n": int(m.sum()),
            "gate_alert_rate": float(alerts[m].mean()),
            "gate_flagged_novel_rate": float(np.isin(labels[m], ["UNKNOWN-ATTACK", "ZERO-DAY-ANOMALY"]).mean()),
            "gate_labels": pd.Series(labels[m]).value_counts().to_dict(),
            "frozen_v11_attack_rate": float(f_attack[m].mean()),
            "frozen_v11_labels": pd.Series(np.where(f_attack[m], f_type[m], "BENIGN")).value_counts().to_dict(),
        })

    # operating points: same scores, different conformal alpha (benign FPR budget)
    pvals = np.array([r["p_value"] for r in res])
    operating_points = []
    for a in (0.0005, 0.001, 0.005, 0.01, 0.05):
        al = pvals <= a
        operating_points.append({
            "alpha": a, "benign_fpr": float(al[b].mean()), "known_attack_recall": float(al[k].mean()),
            "natural_unknown_alert_rate": float(al[u].mean()),
            "per_family_recall": {f: float(al[fam == f].mean()) for f in sorted(set(fam[k]))},
        })

    evaluation = {
        "operating_points": operating_points,
        "frozen_v11_operating_point": {"threshold": float(pred.binary_threshold), "benign_fpr": float(f_attack[b].mean())},
        "test_sizes": {"benign": int(b.sum()), "known_attacks": int(k.sum()), "natural_unknown": int(u.sum())},
        "gate": {
            "benign_fpr": float(alerts[b].mean()),
            "benign_fpr_nominal_alpha": 0.01,
            "known_attack_recall": float(alerts[k].mean()),
            "known_family_accuracy": float((labels[k] == fam[k]).mean()),
            "natural_unknown_alert_rate": float(alerts[u].mean()),
            "latency_ms_per_flow_batch": round(per_flow_ms, 4),
            "served_vs_research_parity": parity,
        },
        "frozen_v11": {
            "benign_fpr": float(f_attack[b].mean()),
            "known_attack_recall": float(f_attack[k].mean()),
            "natural_unknown_attack_rate": float(f_attack[u].mean()),
        },
        "natural_unknowns": unknown_rows,
        "per_family_recall": {f: {"gate": float(alerts[fam == f].mean()), "frozen_v11": float(f_attack[fam == f].mean())}
                              for f in sorted(set(fam[k]))},
        "note": "Natural unknowns (Infiltration n=36, Heartbleed n=11) are tiny; treat rates as illustrative, "
                "the LOAFO / temporal / cross-dataset protocols are the statistical evidence.",
    }
    metadata["evaluation"] = evaluation
    (GATE_DIR / "aegis_osr_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (ARTIFACT_DIR / "zero_day_gate_report.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(evaluation, indent=1))
    print(f"total {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
