"""Plot IID drift + residual error-analysis figures from frozen JSON artifacts."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ids_config import load_config, resolve_path

ATTACK_CLASSES = ["Bot", "BruteForce", "DDoS", "DoS", "PortScan", "WebAttack"]


def enrich_error_report(err: dict, training: dict) -> dict:
    btest = (training.get("binary") or {}).get("test") or {}
    mtest = (training.get("multiclass") or {}).get("test") or {}
    cm = mtest.get("confusion_matrix") or []
    offs = []
    for i, row in enumerate(cm):
        for j, v in enumerate(row):
            if i != j and v:
                offs.append(
                    {
                        "count": int(v),
                        "true": ATTACK_CLASSES[i] if i < len(ATTACK_CLASSES) else str(i),
                        "pred": ATTACK_CLASSES[j] if j < len(ATTACK_CLASSES) else str(j),
                    }
                )
    offs.sort(key=lambda r: r["count"], reverse=True)
    err["summary"] = {
        "binary_best": (training.get("binary") or {}).get("best"),
        "multiclass_best": (training.get("multiclass") or {}).get("best"),
        "binary_test_errors": {
            "false_positives": btest.get("false_positives"),
            "false_negatives": btest.get("false_negatives"),
            "true_positives": btest.get("true_positives"),
            "true_negatives": btest.get("true_negatives"),
            "fpr": btest.get("fpr"),
            "fnr": btest.get("fnr"),
            "f1": btest.get("f1"),
        },
        "multiclass_off_diagonal": offs,
        "multiclass_off_diagonal_total": int(sum(o["count"] for o in offs)),
        "multiclass_n_attacks": int(sum(sum(r) for r in cm)) if cm else None,
        "notes": [
            "Error counts come from the frozen IID test split in training_report.json.",
            "Dominant residual family confusions involve PortScan / DoS / WebAttack.",
            "This is residual-error characterization, not a claim of zero operational risk.",
        ],
    }
    return err


def enrich_drift_report(drift: dict) -> dict:
    fd = drift.get("feature_drift") or {}
    ld = drift.get("label_drift") or {}
    top = fd.get("top_psi") or []
    by_z = sorted(top, key=lambda r: abs(float(r.get("mean_shift_z") or 0)), reverse=True)
    drift["summary"] = {
        "protocol": f"{drift.get('ref')} → {drift.get('current')} (IID stratified processed splits)",
        "features_compared": fd.get("features_compared"),
        "flagged_psi_ge_0.2_count": len(fd.get("flagged_psi_ge_0.2") or []),
        "max_psi": max((float(r.get("psi") or 0) for r in top), default=0.0),
        "largest_abs_mean_shift_z": by_z[0] if by_z else None,
        "label_max_abs_delta_pp": max(
            (abs(float(r.get("delta_pp") or 0)) for r in (ld.get("by_label") or [])),
            default=0.0,
        ),
        "retrain_recommendation": drift.get("retrain_recommendation"),
        "academic_caveats": [
            "IID train→test PSI near zero is expected under stratified sampling from one corpus.",
            "This does not measure temporal day-shift, live capture drift, or cross-dataset shift.",
            "Temporal holdout (§8) is the complementary within-CICIDS generalization check.",
            "External-dataset validation remains future work.",
        ],
    }
    return drift


def plot_psi(drift: dict, out: Path) -> None:
    top = (drift.get("feature_drift") or {}).get("top_psi") or []
    names = [r["feature"][:28] for r in top[:12]]
    psi = [float(r.get("psi") or 0) for r in top[:12]]
    z = [abs(float(r.get("mean_shift_z") or 0)) for r in top[:12]]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    axes[0].barh(names[::-1], psi[::-1], color="#1f4e79")
    axes[0].axvline(0.2, color="#e76f51", ls="--", label="PSI=0.2 heuristic")
    axes[0].set_xlabel("PSI")
    axes[0].set_title("Feature PSI (train→test IID) — freeze snapshot")
    axes[0].legend(fontsize=8)
    axes[1].barh(names[::-1], z[::-1], color="#2a9d8f")
    axes[1].set_xlabel("|mean_shift_z|")
    axes[1].set_title("Largest |mean shift| (still tiny under IID)")
    fig.tight_layout()
    fig.savefig(out / "drift_psi_train_vs_test.png", dpi=160)
    plt.close(fig)


def plot_label_drift(drift: dict, out: Path) -> None:
    rows = ((drift.get("label_drift") or {}).get("by_label") or [])
    if not rows:
        return
    labels = [r["label"] for r in rows]
    ref = [float(r["ref_pct"]) for r in rows]
    cur = [float(r["cur_pct"]) for r in rows]
    x = np.arange(len(labels))
    w = 0.38
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(x - w / 2, ref, w, label="Train (ref) %", color="#1f4e79")
    ax.bar(x + w / 2, cur, w, label="Test (cur) %", color="#2a9d8f")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=25, ha="right")
    ax.set_ylabel("Percent of flows")
    ax.set_title("Label distribution: train vs test (IID) — deltas ≈ 0 pp")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out / "drift_label_distribution.png", dpi=160)
    plt.close(fig)


def plot_binary_errors(err: dict, out: Path) -> None:
    s = (err.get("summary") or {}).get("binary_test_errors") or {}
    if not s:
        return
    labels = ["TN", "FP", "FN", "TP"]
    vals = [
        float(s.get("true_negatives") or 0),
        float(s.get("false_positives") or 0),
        float(s.get("false_negatives") or 0),
        float(s.get("true_positives") or 0),
    ]
    colors = ["#457b9d", "#e9c46a", "#e76f51", "#2a9d8f"]
    fig, ax = plt.subplots(figsize=(7, 4.2))
    bars = ax.bar(labels, vals, color=colors)
    ax.set_ylabel("Count (IID test)")
    ax.set_title(
        f"Binary residual errors (Decision Tree) — FP={int(vals[1])} FN={int(vals[2])}"
    )
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v, f"{int(v):,}", ha="center", va="bottom", fontsize=8)
    ax.set_yscale("log")
    fig.tight_layout()
    fig.savefig(out / "error_binary_fp_fn_counts.png", dpi=160)
    plt.close(fig)


def plot_multiclass_confusions(err: dict, out: Path) -> None:
    offs = (err.get("summary") or {}).get("multiclass_off_diagonal") or []
    if not offs:
        return
    top = offs[:8]
    names = [f"{r['true']}→{r['pred']}" for r in top]
    counts = [r["count"] for r in top]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.barh(names[::-1], counts[::-1], color="#e76f51")
    ax.set_xlabel("Misclassification count (IID test)")
    total = (err.get("summary") or {}).get("multiclass_off_diagonal_total")
    n = (err.get("summary") or {}).get("multiclass_n_attacks")
    ax.set_title(f"Top multiclass residual confusions — {total} errors / {n} attacks")
    fig.tight_layout()
    fig.savefig(out / "error_multiclass_top_confusions.png", dpi=160)
    plt.close(fig)


def plot_research_summary(drift: dict, err: dict, out: Path) -> None:
    ds = drift.get("summary") or {}
    es = err.get("summary") or {}
    be = es.get("binary_test_errors") or {}
    fig, ax = plt.subplots(figsize=(8.8, 5.0))
    ax.axis("off")
    lines = [
        "IID drift + residual error summary (frozen v1.1)",
        "",
        f"Drift protocol: {ds.get('protocol')}",
        f"Features compared: {ds.get('features_compared')}  |  PSI≥0.2 flagged: {ds.get('flagged_psi_ge_0.2_count')}",
        f"Max PSI: {ds.get('max_psi')}  |  Max |label Δ pp|: {ds.get('label_max_abs_delta_pp')}",
        f"Retrain action: {(ds.get('retrain_recommendation') or {}).get('action')} (promote=false)",
        "",
        f"Binary FP={be.get('false_positives')}  FN={be.get('false_negatives')}  FPR={be.get('fpr'):.5f}  FNR={be.get('fnr'):.5f}",
        f"Multiclass off-diagonal total: {es.get('multiclass_off_diagonal_total')} / {es.get('multiclass_n_attacks')} attacks",
        "Dominant confusions: PortScan↔DoS and DoS/PortScan/WebAttack triangle",
        "",
        "IID PSI≈0 ≠ live/temporal drift absence. External-dataset = future work.",
    ]
    # fix f-string if fpr None
    if be.get("fpr") is None:
        lines[7] = f"Binary FP={be.get('false_positives')}  FN={be.get('false_negatives')}"
    ax.text(0.02, 0.98, "\n".join(lines), va="top", ha="left", family="monospace", fontsize=9)
    fig.tight_layout()
    fig.savefig(out / "drift_error_research_summary.png", dpi=160)
    plt.close(fig)


def main() -> None:
    cfg = load_config()
    model_dir = resolve_path(cfg["models"]["output_dir"])
    drift_path = model_dir / "drift_report.json"
    err_path = model_dir / "error_analysis_report.json"
    tr_path = model_dir / "training_report.json"
    if not drift_path.exists() or not err_path.exists() or not tr_path.exists():
        raise SystemExit("Need drift_report.json, error_analysis_report.json, training_report.json")

    drift = enrich_drift_report(json.loads(drift_path.read_text(encoding="utf-8")))
    training = json.loads(tr_path.read_text(encoding="utf-8"))
    err = enrich_error_report(json.loads(err_path.read_text(encoding="utf-8")), training)

    drift_path.write_text(json.dumps(drift, indent=2), encoding="utf-8")
    err_path.write_text(json.dumps(err, indent=2), encoding="utf-8")

    out = model_dir / "figures"
    out.mkdir(parents=True, exist_ok=True)
    plot_psi(drift, out)
    plot_label_drift(drift, out)
    plot_binary_errors(err, out)
    plot_multiclass_confusions(err, out)
    plot_research_summary(drift, err, out)
    print(
        json.dumps(
            {
                "figures": [
                    "drift_psi_train_vs_test.png",
                    "drift_label_distribution.png",
                    "error_binary_fp_fn_counts.png",
                    "error_multiclass_top_confusions.png",
                    "drift_error_research_summary.png",
                ]
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
