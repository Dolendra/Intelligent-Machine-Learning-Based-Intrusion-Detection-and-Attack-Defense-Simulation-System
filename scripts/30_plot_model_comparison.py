"""Plot model-selection / comparison figures from training_report.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ids_config import load_config, resolve_path


def plot_binary_selection(val: dict, best: str, out: Path) -> None:
    names = list(val.keys())
    scores = [float(val[n]["selection_score"]) for n in names]
    colors = ["#2a9d8f" if n == best else "#1f4e79" for n in names]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.barh(names[::-1], scores[::-1], color=colors[::-1])
    ax.set_xlabel("Multi-objective selection_score (validation)")
    ax.set_xlim(0.90, 1.0)
    ax.set_title(f"Binary model selection — selected: {best}")
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out / "model_binary_selection_scores.png", dpi=160)
    plt.close(fig)


def plot_f1_recall(val: dict, best: str, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 5))
    for name, m in val.items():
        x = float(m["recall"])
        y = float(m["f1"])
        ax.scatter(x, y, s=120 if name == best else 80, zorder=3)
        ax.annotate(name, (x, y), textcoords="offset points", xytext=(6, 4), fontsize=8)
    ax.set_xlabel("Recall (validation)")
    ax.set_ylabel("F1 (validation)")
    ax.set_title("Binary trade-off: XGBoost higher F1, Decision Tree higher recall → selected")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out / "model_binary_f1_vs_recall.png", dpi=160)
    plt.close(fig)


def plot_binary_metric_bars(val: dict, best: str, out: Path) -> None:
    metrics = ["recall", "f1", "pr_auc", "fpr"]
    names = list(val.keys())
    x = np.arange(len(metrics))
    w = 0.18
    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    for i, name in enumerate(names):
        vals = []
        for m in metrics:
            v = float(val[name][m])
            vals.append(1.0 - v if m == "fpr" else v)
        ax.bar(x + (i - 1.5) * w, vals, w, label=name + (" ★" if name == best else ""))
    ax.set_xticks(x)
    ax.set_xticklabels(["Recall", "F1", "PR-AUC", "1−FPR"])
    ax.set_ylim(0.9, 1.005)
    ax.set_title("Binary validation metrics (1−FPR shown so higher is better)")
    ax.legend(fontsize=8, ncol=2)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out / "model_binary_metric_bars.png", dpi=160)
    plt.close(fig)


def plot_multiclass_selection(val: dict, best: str, out: Path) -> None:
    names = list(val.keys())
    macro = [float(val[n]["f1_macro"]) for n in names]
    weighted = [float(val[n]["f1_weighted"]) for n in names]
    sel = [float(val[n]["selection_score"]) for n in names]
    x = np.arange(len(names))
    w = 0.25
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.bar(x - w, macro, w, label="macro-F1", color="#1f4e79")
    ax.bar(x, weighted, w, label="weighted-F1", color="#2a9d8f")
    ax.bar(x + w, sel, w, label="selection_score", color="#e9c46a")
    ax.set_xticks(x)
    ax.set_xticklabels([n + (" ★" if n == best else "") for n in names])
    ax.set_ylim(0.995, 1.001)
    ax.set_title(f"Multiclass validation — selected: {best}")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out / "model_multiclass_selection.png", dpi=160)
    plt.close(fig)


def plot_summary(report: dict, out: Path) -> None:
    b = report["binary"]
    m = report["multiclass"]
    fig, ax = plt.subplots(figsize=(8.8, 5.0))
    ax.axis("off")
    lines = [
        "Model comparison / selection summary (frozen v1.1)",
        "",
        "Binary candidates: LR, Decision Tree, Random Forest, XGBoost",
        "Selection weights: recall 0.30 · F1 0.25 · PR-AUC 0.20 · FPR 0.15 · latency 0.10",
        "",
        f"Selected binary: {b['best']}  (val selection_score={b['validation'][b['best']]['selection_score']})",
        f"  DT recall={b['validation']['decision_tree']['recall']:.4f}  F1={b['validation']['decision_tree']['f1']:.4f}",
        f"  XGB recall={b['validation']['xgboost']['recall']:.4f}  F1={b['validation']['xgboost']['f1']:.4f}  <- higher F1, lower recall",
        f"  RF  F1={b['validation']['random_forest']['f1']:.4f} but slower val infer ({b['validation']['random_forest']['infer_seconds_val']}s)",
        "",
        f"Selected multiclass: {m['best']}  (attack-only; selection~0.7*macro+0.3*weighted)",
        f"  RF  macro-F1={m['validation']['random_forest']['f1_macro']:.4f}",
        f"  XGB macro-F1={m['validation']['xgboost']['f1_macro']:.4f}",
        "",
        "Not claiming XGBoost is inferior in general — only under this IDS selection policy.",
    ]
    ax.text(0.02, 0.98, "\n".join(lines), va="top", ha="left", family="monospace", fontsize=8.5)
    fig.tight_layout()
    fig.savefig(out / "model_selection_summary.png", dpi=160)
    plt.close(fig)


def write_experiment_md(report: dict, path: Path) -> None:
    b, m = report["binary"], report["multiclass"]
    lines = [
        "# Model comparison & selection",
        "",
        "Scripts: `scripts/04_export_comparison.py`, `scripts/30_plot_model_comparison.py`",
        "Source: `models/trained_models/training_report.json`",
        "Figures: `model_binary_*.png`, `model_multiclass_selection.png`, `model_selection_summary.png`",
        "",
        "## Binary selection policy",
        "",
        "Multi-objective score (project-justified weights in `config.yaml`):",
        "",
        "- recall **0.30**",
        "- F1 **0.25**",
        "- PR-AUC **0.20**",
        "- FPR penalty **0.15**",
        "- latency **0.10**",
        "",
        f"**Selected:** `{b['best']}`",
        "",
        "| Model | Recall | F1 | PR-AUC | FPR | Infer(s) | selection_score |",
        "|-------|-------:|---:|-------:|----:|---------:|----------------:|",
    ]
    for name, met in b["validation"].items():
        star = "**" if name == b["best"] else ""
        lines.append(
            f"| {star}{name}{star} | {met['recall']:.4f} | {met['f1']:.4f} | {met['pr_auc']:.4f} | "
            f"{met['fpr']:.4f} | {met.get('infer_seconds_val')} | {met['selection_score']:.6f} |"
        )
    lines += [
        "",
        "### Why not XGBoost?",
        "",
        "XGBoost has the highest validation F1, but **lower recall** than Decision Tree. "
        "Under an IDS-oriented policy that weights recall first, Decision Tree wins the selection score.",
        "",
        "## Multiclass selection",
        "",
        "Score ≈ `0.7·macro-F1 + 0.3·weighted-F1` on attack-only classes.",
        "",
        f"**Selected:** `{m['best']}`",
        "",
        "| Model | macro-F1 | weighted-F1 | selection_score |",
        "|-------|---------:|------------:|----------------:|",
    ]
    for name, met in m["validation"].items():
        star = "**" if name == m["best"] else ""
        lines.append(
            f"| {star}{name}{star} | {met['f1_macro']:.4f} | {met['f1_weighted']:.4f} | {met['selection_score']:.6f} |"
        )
    lines += [
        "",
        "## Claims",
        "",
        "- Comparison is an **algorithm ablation under a fixed feature pipeline**, not an architecture search.",
        "- Selection is policy-dependent; different weights could prefer XGBoost.",
        "- Final test metrics for selected models are reported in `PROJECT_REPORT.md` §7.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_model_comparison_md(report: dict, path: Path) -> None:
    bval = report["binary"]["validation"]
    mval = report["multiclass"]["validation"]
    lines = [
        "# Model comparison (from training_report.json)",
        "",
        f"**Frozen selection (v1.1):** binary = `{report['binary']['best']}` · multiclass = `{report['multiclass']['best']}`",
        "Binary selection is **multi-objective** (recall / F1 / PR-AUC / FPR / latency).",
        "",
        "## Binary validation",
        "",
        "| Model | Precision | Recall | F1 | ROC-AUC | selection_score |",
        "|-------|----------:|-------:|---:|--------:|----------------:|",
    ]
    for name, m in bval.items():
        star = "**" if name == report["binary"]["best"] else ""
        lines.append(
            f"| {star}{name}{star} | {m['precision']:.4f} | {m['recall']:.4f} | {m['f1']:.4f} | "
            f"{m['roc_auc']:.4f} | {m['selection_score']:.6f} |"
        )
    bt = report["binary"]["test"]
    lines += [
        "",
        f"**Best binary:** `{report['binary']['best']}`",
        f"**Test:** precision={bt['precision']:.5f}, recall={bt['recall']:.5f}, F1={bt['f1']:.5f}, "
        f"ROC-AUC={bt['roc_auc']:.5f}, PR-AUC={bt['pr_auc']:.5f}",
        "",
        "## Multiclass validation (attack-only)",
        "",
        "| Model | macro-F1 | weighted-F1 | accuracy | selection_score |",
        "|-------|---------:|------------:|---------:|----------------:|",
    ]
    for name, m in mval.items():
        star = "**" if name == report["multiclass"]["best"] else ""
        lines.append(
            f"| {star}{name}{star} | {m['f1_macro']:.4f} | {m['f1_weighted']:.4f} | "
            f"{m['accuracy']:.4f} | {m['selection_score']:.6f} |"
        )
    mt = report["multiclass"]["test"]
    lines += [
        "",
        f"**Best multiclass:** `{report['multiclass']['best']}`",
        f"**Test:** accuracy={mt['accuracy']:.5f}, macro-F1={mt['f1_macro']:.5f}, weighted-F1={mt['f1_weighted']:.5f}",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    cfg = load_config()
    model_dir = resolve_path(cfg["models"]["output_dir"])
    report = json.loads((model_dir / "training_report.json").read_text(encoding="utf-8"))
    out = model_dir / "figures"
    out.mkdir(parents=True, exist_ok=True)

    bval = report["binary"]["validation"]
    mval = report["multiclass"]["validation"]
    plot_binary_selection(bval, report["binary"]["best"], out)
    plot_f1_recall(bval, report["binary"]["best"], out)
    plot_binary_metric_bars(bval, report["binary"]["best"], out)
    plot_multiclass_selection(mval, report["multiclass"]["best"], out)
    plot_summary(report, out)
    write_experiment_md(report, ROOT / "docs" / "experiments" / "MODEL_COMPARISON.md")
    write_model_comparison_md(report, model_dir / "model_comparison.md")
    print(
        json.dumps(
            {
                "ok": True,
                "best_binary": report["binary"]["best"],
                "best_multi": report["multiclass"]["best"],
                "figures": [
                    "model_binary_selection_scores.png",
                    "model_binary_f1_vs_recall.png",
                    "model_binary_metric_bars.png",
                    "model_multiclass_selection.png",
                    "model_selection_summary.png",
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
