"""Phase 2 re-evaluation of the FROZEN v1.1 detector (E-01, E-02, E-03). No training, no threshold selection.

    python scripts/71_v11_reeval.py

Why this exists (docs/research/ML_PIPELINE_AUDIT.md):
  * ML-1: the published "Decision Tree @ 0.85" binary test metrics were computed at 0.5 (argmax).
  * ML-2: family metrics were computed on oracle attack rows (stage 2 after a perfect stage 1).
  * ML-4: the system-level benign incident rate depends on the incident policy (frozen / gate / union).

What it does (all thresholds are FIXED in advance; the test data selects nothing):
  E-01  Score data/processed/test.parquet once with the frozen DT. Report binary metrics at 0.5 (the historical
        argmax figure, used as a reproduction anchor) and at 0.85 (the deployed operating point, chosen on the
        validation split by scripts/15 -> threshold_operating_point.json).
  E-02  End-to-end per-family detection on the same split: stage-1 detection at each threshold, stage-2 family
        accuracy on oracle attack rows (the historical quantity), and end-to-end "detected AND correct family".
  E-03  Policy-level alert rates on rows held out from BOTH the frozen model and the Zero-Day Gate (the full
        eligible set of scripts/52, not only the 8,000-row replay sample): benign incident rate and per-family
        detection for incident_policy = frozen / gate / union.

Outputs (new, versioned; the script refuses to overwrite them):
  research_artifacts/v11_reeval/v11_test_metrics_by_threshold.json   (E-01)
  research_artifacts/v11_reeval/v11_family_end_to_end.json           (E-02)
  research_artifacts/v11_reeval/v11_policy_alert_rates.json          (E-03)
  research_artifacts/v11_reeval/MANIFEST.json                        (input/output SHA-256, code commit)
"""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import f1_score  # noqa: E402

from ml.evaluation.metrics import evaluate_binary  # noqa: E402
from ml.prediction.predictor import IDSPredictor  # noqa: E402
from research.artifact_guard import assert_writable  # noqa: E402

OUT = ROOT / "research_artifacts" / "v11_reeval"
MODEL_DIR = ROOT / "models" / "trained_models"
PROCESSED = ROOT / "data" / "processed"
THRESHOLDS = (0.5, 0.85)
DEPLOYED = 0.85
SEED = 42  # scripts/52 split seed (gate split); reproduced, not chosen here
NATURAL_UNKNOWN = ["Infiltration", "Heartbleed"]
ANCHOR_TOL = 1e-9


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wilson(k: int, n: int, z: float = 1.959964) -> list[float] | None:
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, c - h), 6), round(min(1.0, c + h), 6)]


def rate(k: int, n: int) -> dict:
    return {"k": int(k), "n": int(n), "rate": (k / n) if n else None, "wilson95": wilson(int(k), int(n))}


def git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:  # pragma: no cover
        return "unknown"


def frozen_scores(pred: IDSPredictor, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """P(attack) from the frozen DT and the stage-2 family argmax for every row (same path as predict_many)."""
    work = df[list(pred.bundle.feature_names)]
    X_bin = pred.bundle.transform(work, task="binary")
    p_attack = pred._proba_attack(pred.binary_model, X_bin)
    X_multi = pred.bundle.transform(work, task="multiclass")
    if X_multi.shape[1] != getattr(pred.multiclass_model, "n_features_in_", X_multi.shape[1]):
        X_multi = X_bin
    mp = pred.multiclass_model.predict_proba(X_multi)
    classes = pred._decode_family_classes(list(pred.multiclass_model.classes_))
    keep = [i for i, c in enumerate(classes) if c != "BENIGN"]
    fam = np.asarray([classes[i] for i in keep])[mp[:, keep].argmax(axis=1)]
    return p_attack, fam


# ------------------------------------------------------------------ E-01 / E-02 on the frozen test split
def e01_e02(pred: IDSPredictor) -> tuple[dict, dict]:
    test = pd.read_parquet(PROCESSED / "test.parquet")
    y = test["is_attack"].to_numpy().astype(int)
    label = test["Label"].astype(str).to_numpy()
    p_attack, fam = frozen_scores(pred, test)

    meta = json.loads((MODEL_DIR / "model_metadata.json").read_text(encoding="utf-8"))
    hist = meta["test_metrics_binary"]

    by_thr = {}
    for t in THRESHOLDS:
        y_hat = (p_attack >= t).astype(int)
        m = evaluate_binary(y, y_hat, p_attack)
        tn = int(((y == 0) & (y_hat == 0)).sum())
        fp = int(((y == 0) & (y_hat == 1)).sum())
        fn = int(((y == 1) & (y_hat == 0)).sum())
        tp = int(((y == 1) & (y_hat == 1)).sum())
        m["confusion"] = {"tn": tn, "fp": fp, "fn": fn, "tp": tp}
        m["fpr_wilson95"] = wilson(fp, fp + tn)
        m["recall_wilson95"] = wilson(tp, tp + fn)
        by_thr[str(t)] = m

    # Reproduction anchor: the historical "test_metrics_binary" must equal the 0.5 row (ML-1), not the 0.85 row.
    argmax_pred = pred.binary_model.predict(pred.bundle.transform(test[list(pred.bundle.feature_names)], task="binary"))
    argmax_equals_05 = bool((argmax_pred.astype(int) == (p_attack >= 0.5).astype(int)).all())
    diffs = {k: abs(by_thr["0.5"][k] - hist[k]) for k in ("f1", "recall", "precision", "fpr")}
    anchor = {
        "historical_source": "models/trained_models/model_metadata.json:test_metrics_binary (labelled next to binary_threshold 0.85)",
        "historical": {k: hist[k] for k in ("f1", "recall", "precision", "fpr")},
        "abs_diff_vs_recomputed_at_0.5": diffs,
        "abs_diff_vs_recomputed_at_0.85": {k: abs(by_thr["0.85"][k] - hist[k]) for k in diffs},
        "reproduced_at_0.5": all(v <= ANCHOR_TOL for v in diffs.values()),
        "dt_predict_equals_proba_ge_0.5": argmax_equals_05,
    }
    if not anchor["reproduced_at_0.5"]:
        raise SystemExit(f"anchor failed: recomputed 0.5 metrics do not reproduce model_metadata: {diffs}")

    e01 = {
        "experiment": "E-01 frozen v1.1 binary detector on the frozen test split at fixed thresholds",
        "split": "data/processed/test.parquet (frozen v1.1 random IID split; held out from training and threshold selection)",
        "rows": int(len(y)), "attack_rows": int(y.sum()), "benign_rows": int((y == 0).sum()),
        "model": "models/trained_models/binary_best.joblib (Decision Tree, frozen)",
        "thresholds": {"0.5": "argmax; the threshold the historical test figures were computed at",
                       "0.85": "deployed operating point, chosen on validation (threshold_operating_point.json)"},
        "test_data_used_for_selection": False,
        "metrics": by_thr,
        "reproduction_anchor": anchor,
        "caveat": "IID random split of session-correlated flows (ML-20): optimistic for unseen traffic; not a temporal estimate.",
    }

    fams = sorted(set(label) - {"BENIGN"})
    per_family = {}
    for f in fams:
        mask = label == f
        n = int(mask.sum())
        fam_ok = fam[mask] == f
        row = {"n": n, "stage2_family_accuracy_on_oracle_attack_rows": rate(int(fam_ok.sum()), n)}
        for t in THRESHOLDS:
            det = p_attack[mask] >= t
            row[f"detected@{t}"] = rate(int(det.sum()), n)
            row[f"end_to_end_correct@{t}"] = rate(int((det & fam_ok).sum()), n)
        per_family[f] = row
    benign = label == "BENIGN"
    for t in THRESHOLDS:
        per_family.setdefault("BENIGN", {"n": int(benign.sum())})[f"false_alarm@{t}"] = rate(
            int((p_attack[benign] >= t).sum()), int(benign.sum()))

    # Macro-F1: historical (stage 2 on oracle attack rows) vs end-to-end 7-class system output.
    att = label != "BENIGN"
    cond_macro = f1_score(label[att], fam[att], average="macro", labels=fams)
    e2e = {}
    for t in THRESHOLDS:
        sys_out = np.where(p_attack >= t, fam, "BENIGN")
        e2e[str(t)] = {
            "macro_f1_7class": float(f1_score(label, sys_out, average="macro", labels=["BENIGN", *fams])),
            "macro_recall_attack_families": float(np.mean([(sys_out[label == f] == f).mean() for f in fams])),
        }
    e02 = {
        "experiment": "E-02 end-to-end per-family detection of the frozen two-stage detector",
        "split": e01["split"],
        "per_family": per_family,
        "macro_f1_stage2_conditional_on_oracle_stage1": float(cond_macro),
        "end_to_end_system": e2e,
        "definitions": {
            "detected@t": "stage-1 P(attack) >= t",
            "end_to_end_correct@t": "detected@t AND stage-2 family == true family",
            "stage2_family_accuracy_on_oracle_attack_rows": "historical quantity: family model applied to every true attack row",
        },
    }
    return e01, e02


# ------------------------------------------------------------------ E-03 policy-level rates on doubly held-out rows
def eligible_rows() -> tuple[pd.DataFrame, dict]:
    """Re-derive the scripts/52 eligible set (frozen test ∩ gate test, minus anything either model saw)."""
    from research.data import feature_columns, load_cic2017, stratified_split

    def row_keys(df: pd.DataFrame, feats: list[str]) -> np.ndarray:
        X = df[feats].to_numpy(dtype=np.float32) + np.float32(0.0)
        return pd.util.hash_pandas_object(pd.DataFrame(X), index=False).to_numpy()

    df = load_cic2017()
    feats = feature_columns(df)
    base = df[~df["family"].isin(NATURAL_UNKNOWN)]
    g_tr, g_va, g_te = stratified_split(base, (0.7, 0.1, 0.2), SEED)
    frozen = {s: pd.read_parquet(PROCESSED / f"{s}.parquet", columns=feats) for s in ("train", "val", "test")}
    fk = {s: set(row_keys(d, feats)) for s, d in frozen.items()}
    gate_seen = set(row_keys(g_tr, feats)) | set(row_keys(g_va, feats))
    te = row_keys(g_te, feats)
    mask = np.isin(te, list(fk["test"])) & ~np.isin(te, list(fk["train"] | fk["val"])) & ~np.isin(te, list(gate_seen))
    elig = g_te[mask]
    unseen = df[df["family"].isin(NATURAL_UNKNOWN)]
    rows = pd.concat([elig, unseen], ignore_index=True)
    k = row_keys(rows, feats)
    overlap = {"frozen_train_or_val": int(np.isin(k, list(fk["train"] | fk["val"])).sum()),
               "gate_train_or_val": int(np.isin(k, list(gate_seen)).sum())}
    assert all(v == 0 for v in overlap.values()), overlap
    rows["Fwd Header Length.1"] = rows["Fwd Header Length"]
    return rows, {"eligible_rows": int(mask.sum()), "natural_unknown_rows": int(len(unseen)), "overlap_check": overlap}


def e03(pred: IDSPredictor) -> dict:
    from research.serving import get_gate

    rows, info = eligible_rows()
    gate = get_gate()
    if gate is None:
        raise SystemExit("Zero-Day Gate could not be loaded")
    p_attack, _ = frozen_scores(pred, rows)
    frozen_alert = p_attack >= DEPLOYED
    gate_alert = np.zeros(len(rows), dtype=bool)
    step = 20000
    for i in range(0, len(rows), step):
        res = gate.assess(rows.iloc[i:i + step], explain_top=0)
        gate_alert[i:i + step] = [r["alert"] for r in res]
    union = frozen_alert | gate_alert
    gate_only = gate_alert & ~frozen_alert

    fam = rows["family"].astype(str).to_numpy()
    out = {}
    for f in sorted(set(fam)):
        m = fam == f
        n = int(m.sum())
        out[f] = {
            "n": n,
            "frozen": rate(int(frozen_alert[m].sum()), n),
            "gate": rate(int(gate_alert[m].sum()), n),
            "union": rate(int(union[m].sum()), n),
            "gate_only": rate(int(gate_only[m].sum()), n),
        }
    return {
        "experiment": "E-03 alert / incident rates per incident policy on rows held out from BOTH models",
        "rows": "scripts/52 eligibility rule re-derived in full (not the 8,000-benign replay sample) "
                "+ all Infiltration/Heartbleed (never trained on by either model)",
        **info,
        "frozen_threshold": DEPLOYED,
        "gate_alpha": float(gate.alpha),
        "policies": {
            "frozen": "incident iff frozen P(attack) >= 0.85 (current default since P0)",
            "gate": "incident iff gate conformal p <= alpha",
            "union": "incident iff either detector alerts",
        },
        "per_family": out,
        "note": "BENIGN rows give the system-level benign incident rate per policy; attack rows give detection per policy. "
                "Under the default 'frozen' policy, gate-only alerts are recorded as Zero-Day Candidates and raise no incident.",
    }


def write(path: Path, obj: dict) -> None:
    assert_writable(path)
    if path.exists():
        raise SystemExit(f"refusing to overwrite existing result {path.relative_to(ROOT)}; bump the version instead")
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    targets = {n: OUT / n for n in ("v11_test_metrics_by_threshold.json", "v11_family_end_to_end.json",
                                    "v11_policy_alert_rates.json", "MANIFEST.json")}
    for p in targets.values():
        assert_writable(p)
        if p.exists():
            raise SystemExit(f"refusing to overwrite existing result {p.relative_to(ROOT)}")

    pred = IDSPredictor.from_artifacts(MODEL_DIR)
    if abs(pred.binary_threshold - DEPLOYED) > 1e-12:
        raise SystemExit(f"deployed threshold is {pred.binary_threshold}, expected {DEPLOYED}")
    e1, e2 = e01_e02(pred)
    e3 = e03(pred)
    stamp = {"generated_at": datetime.now(timezone.utc).isoformat(), "code_commit": git_head(), "version": 1}
    for name, obj in (("v11_test_metrics_by_threshold.json", e1), ("v11_family_end_to_end.json", e2),
                      ("v11_policy_alert_rates.json", e3)):
        write(targets[name], {**stamp, **obj})
    inputs = [MODEL_DIR / n for n in ("binary_best.joblib", "multiclass_best.joblib", "feature_bundle.joblib",
                                      "threshold_operating_point.json", "model_metadata.json")]
    inputs += [PROCESSED / "test.parquet", PROCESSED / "train.parquet", PROCESSED / "val.parquet"]
    manifest = {**stamp, "script": "scripts/71_v11_reeval.py",
                "inputs": {p.relative_to(ROOT).as_posix(): sha256(p) for p in inputs},
                "outputs": {targets[n].relative_to(ROOT).as_posix(): sha256(targets[n]) for n in targets if n != "MANIFEST.json"}}
    write(targets["MANIFEST.json"], manifest)

    m = e1["metrics"]
    print(json.dumps({t: {k: round(m[t][k], 5) for k in ("f1", "recall", "precision", "fpr")} for t in m}, indent=1))
    print("anchor:", e1["reproduction_anchor"]["reproduced_at_0.5"])
    for f, r in e2["per_family"].items():
        print(f, {k: (round(v["rate"], 4) if isinstance(v, dict) and v.get("rate") is not None else v) for k, v in r.items()})
    for f, r in e3["per_family"].items():
        print("E03", f, r["n"], {p: round(r[p]["rate"], 5) for p in ("frozen", "gate", "union", "gate_only")})


if __name__ == "__main__":
    main()
