"""Publication figures for the Aegis paper (white background, print-safe)."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = Path(__file__).parent / "figs"
OUT.mkdir(exist_ok=True)
ROOT = Path(r"D:\IDS-Project")
plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"],
                     "font.size": 9, "axes.spines.top": False, "axes.spines.right": False})


def box(ax, x, y, w, h, text, fc="#ffffff", ec="#333333", lw=1.0, fs=7.2, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.008,rounding_size=0.012",
                                fc=fc, ec=ec, lw=lw))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal", wrap=True)


def arrow(ax, x1, y1, x2, y2, text=None, dashed=False):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", lw=0.9, color="#333333",
                                linestyle="--" if dashed else "-", shrinkA=0, shrinkB=0))
    if text:
        ax.text((x1 + x2) / 2 + 0.008, (y1 + y2) / 2, text, fontsize=7, va="center", style="italic")


# ---------------------------------------------------------------- Fig. 1 architecture
def fig_architecture():
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    g1, g2, g3 = "#eef3f8", "#f6f1e8", "#eef6ef"
    box(ax, 0.02, 0.86, 0.96, 0.10, "Flow source: CICFlowMeter CSV upload · optional PCAP → flows (fail-closed) · replay of held-out flows",
        fc="#f2f2f2")
    box(ax, 0.02, 0.70, 0.96, 0.10, "FastAPI service layer: HMAC/API-key auth · RBAC · rate & size limits · CORS · structured logs · /api/ready",
        fc="#f2f2f2")
    # detection lane
    box(ax, 0.02, 0.43, 0.30, 0.21, "Closed-set detector (frozen v1.1)\nDT binary @ τ=0.85\n→ RF family (6 classes)\n40+40 SelectKBest features",
        fc=g1)
    box(ax, 0.35, 0.43, 0.30, 0.21, "Aegis-OSR Zero-Day Gate (advisory)\nXGB evidence + kNN benign novelty\nFisher fusion → conformal p-value\nMondrian family attribution",
        fc=g1)
    box(ax, 0.68, 0.43, 0.30, 0.21, "Triage\nSHAP (TreeExplainer) · LIME\ncounterfactual hints\nrisk score & severity band",
        fc=g2)
    # response lane
    box(ax, 0.02, 0.17, 0.30, 0.20, "Incidents\n5-min de-duplication\n30-min campaign linking\nappend-only audit (SQLite/Alembic)",
        fc=g2)
    box(ax, 0.35, 0.17, 0.30, 0.20, "Human-gated response\npropose → dry-run → approve\n→ execute → verify → rollback\nDRY_RUN · CONTROLLED (LIVE forbidden)",
        fc=g3)
    box(ax, 0.68, 0.17, 0.30, 0.20, "Trace-driven cyber range\n(replayed flows, measured)\nStoryboard (illustrative)\nControlled lab plane",
        fc=g3)
    box(ax, 0.02, 0.02, 0.96, 0.09, "React SOC console: dashboard · live traffic monitor · zero-day lab · research lab · response queue · system health",
        fc="#f2f2f2")
    for x in (0.17, 0.50, 0.83):
        arrow(ax, x, 0.86, x, 0.80)
        arrow(ax, x, 0.70, x, 0.64)
    arrow(ax, 0.32, 0.535, 0.35, 0.535)
    arrow(ax, 0.65, 0.535, 0.68, 0.535)
    arrow(ax, 0.17, 0.43, 0.17, 0.37)
    arrow(ax, 0.32, 0.27, 0.35, 0.27)
    arrow(ax, 0.65, 0.27, 0.68, 0.27, dashed=True)
    arrow(ax, 0.83, 0.43, 0.83, 0.37, dashed=True)
    for x in (0.17, 0.50, 0.83):
        arrow(ax, x, 0.17, x, 0.11)
    fig.savefig(OUT / "fig1_architecture.png", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------- Fig. 2 Aegis-OSR pipeline
def fig_osr():
    fig, ax = plt.subplots(figsize=(8.2, 3.6))
    ax.set_xlim(-0.02, 1.02); ax.set_ylim(0, 1); ax.axis("off")
    box(ax, 0.00, 0.40, 0.13, 0.20, "flow x\n(77 features)\nsigned-log,\nstandardize,\nclip ±8", fs=7.5)
    box(ax, 0.17, 0.62, 0.17, 0.22, "XGBoost, K+1 classes\n√-balanced weights\ns_sup = 1 − P(benign|x)", fs=7.5, fc="#eef3f8")
    box(ax, 0.17, 0.16, 0.17, 0.22, "kNN (k=5) to benign\nreference set R\ns_nov = mean distance", fs=7.5, fc="#eef3f8")
    box(ax, 0.38, 0.62, 0.15, 0.22, "benign surprisal\nt_sup (split C₁)\n+ exponential tail", fs=7.5)
    box(ax, 0.38, 0.16, 0.15, 0.22, "benign surprisal\nt_nov (split C₁)\n+ exponential tail", fs=7.5)
    box(ax, 0.57, 0.40, 0.12, 0.20, "Fisher sum\nf = t_sup + t_nov", fs=7.5, fc="#f6f1e8")
    box(ax, 0.73, 0.40, 0.12, 0.20, "conformal\np-value on\nsplit C₂\nalert: p ≤ α", fs=7.5, fc="#f6f1e8")
    box(ax, 0.885, 0.74, 0.115, 0.16, "BENIGN", fs=7.5, fc="#eef6ef")
    box(ax, 0.885, 0.52, 0.115, 0.16, "known family", fs=7.5, fc="#eef6ef")
    box(ax, 0.885, 0.30, 0.115, 0.16, "UNKNOWN-\nATTACK", fs=7.5, fc="#fbeaea")
    box(ax, 0.885, 0.08, 0.115, 0.16, "ZERO-DAY-\nANOMALY", fs=7.5, fc="#fbeaea")
    arrow(ax, 0.13, 0.55, 0.17, 0.70); arrow(ax, 0.13, 0.45, 0.17, 0.30)
    arrow(ax, 0.34, 0.73, 0.38, 0.73); arrow(ax, 0.34, 0.27, 0.38, 0.27)
    arrow(ax, 0.53, 0.70, 0.57, 0.55); arrow(ax, 0.53, 0.30, 0.57, 0.45)
    arrow(ax, 0.69, 0.50, 0.73, 0.50)
    arrow(ax, 0.85, 0.56, 0.885, 0.82); ax.text(0.80, 0.70, "p > α", fontsize=7, style="italic")
    arrow(ax, 0.85, 0.52, 0.885, 0.60)
    arrow(ax, 0.85, 0.48, 0.885, 0.38)
    arrow(ax, 0.85, 0.44, 0.885, 0.16)
    ax.text(0.50, 0.965, "p ≤ α and s_sup ≥ 0.5: Mondrian p_fam > α_fam → known family, otherwise UNKNOWN-ATTACK;"
            "  p ≤ α and s_sup < 0.5 → ZERO-DAY-ANOMALY", ha="center", fontsize=7.2)
    fig.savefig(OUT / "fig2_aegis_osr.png", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------- Fig. 5 adaptation
def fig_adaptation():
    s = json.loads((ROOT / "research_artifacts/openset_temporal_summary.json").read_text(encoding="utf-8"))
    ad = s["adaptation"]["temporal"]
    base = s["per_fold"]["temporal"]
    folds = ["Mon-Thu→Fri", "Mon-Wed→Thu"]
    fig, axes = plt.subplots(2, 2, figsize=(7.0, 4.4), sharex=True)
    for j, fold in enumerate(folds):
        for variant, mk, ls in (("recal", "o", "-"), ("recal+ref", "s", "--")):
            ws, fpr, zdr = [], [], []
            for W in (500, 2000, 5000):
                m = ad[f"{variant}@{W}"]["per_fold"][fold]["Aegis-OSR"]
                ws.append(W); fpr.append(100 * m["fpr"]["mean"]); zdr.append(m["zero_day_recall"]["mean"])
            axes[0, j].plot(ws, fpr, marker=mk, ls=ls, color="black", lw=1, ms=4, label=variant)
            axes[1, j].plot(ws, zdr, marker=mk, ls=ls, color="black", lw=1, ms=4, label=variant)
        b = base[fold]["Aegis-OSR"]
        axes[0, j].axhline(100 * b["fpr"]["mean"], color="0.45", ls=":", lw=1, label="no adaptation")
        axes[1, j].axhline(b["zero_day_recall"]["mean"], color="0.45", ls=":", lw=1, label="no adaptation")
        axes[0, j].axhline(1.0, color="0.2", ls="-.", lw=0.8, label="α = 1%")
        o = ad["oracle@2000"]["per_fold"][fold]["Aegis-OSR"]
        axes[0, j].plot([2000], [100 * o["fpr"]["mean"]], marker="*", color="0.3", ms=9, ls="none", label="oracle (random benign)")
        axes[1, j].plot([2000], [o["zero_day_recall"]["mean"]], marker="*", color="0.3", ms=9, ls="none")
        axes[0, j].set_title(fold.replace("→", " → "), fontsize=9)
        axes[1, j].set_xscale("log"); axes[1, j].set_xticks([500, 2000, 5000]); axes[1, j].set_xticklabels(["500", "2000", "5000"])
        axes[1, j].set_ylim(0, 1.05)
        axes[1, j].set_xlabel("warm-up window W (benign flows from target day)")
    axes[0, 0].set_ylabel("realized benign FPR (%)")
    axes[1, 0].set_ylabel("zero-day recall")
    axes[0, 0].legend(fontsize=7, frameon=False, loc="upper right")
    fig.tight_layout()
    fig.savefig(OUT / "fig5_adaptation.png", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------- Fig. 6 gate operating points
def fig_gate():
    g = json.loads((ROOT / "research_artifacts/zero_day_gate_report.json").read_text(encoding="utf-8"))["evaluation"]
    ops = g["operating_points"]
    a = [100 * o["alpha"] for o in ops]
    fig, ax = plt.subplots(figsize=(4.2, 2.8))
    ax.plot(a, [100 * o["benign_fpr"] for o in ops], marker="o", color="black", lw=1, ms=4, label="benign FPR (%)")
    ax.plot(a, a, color="0.6", ls=":", lw=1, label="nominal α (%)")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("nominal α (%)"); ax.set_ylabel("benign FPR (%)")
    ax2 = ax.twinx()
    ax2.plot(a, [o["known_attack_recall"] for o in ops], marker="s", ls="--", color="0.25", lw=1, ms=4, label="known-attack recall")
    ax2.plot(a, [o["natural_unknown_alert_rate"] for o in ops], marker="^", ls="-.", color="0.5", lw=1, ms=4,
             label="alert rate, never-seen attacks (n=47)")
    ax2.set_ylim(0, 1.05); ax2.set_ylabel("rate"); ax2.spines["right"].set_visible(True)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=6.5, frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(OUT / "fig6_gate.png", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    fig_architecture(); fig_osr(); fig_adaptation(); fig_gate()
    print("ok", sorted(p.name for p in OUT.iterdir()))
