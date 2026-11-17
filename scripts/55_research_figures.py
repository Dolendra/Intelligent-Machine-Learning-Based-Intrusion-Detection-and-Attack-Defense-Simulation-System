"""Paper-ready figures + results tables for the v3 open-set study.

Reads research_artifacts/openset_*_summary.json, zero_day_gate_report.json and
frozen_v11_on_cic2018.json; writes
  research_artifacts/figures/*.png   (300 dpi, colour-blind-safe palette)
  docs/research/RESULTS.md           (auto-generated tables; do not edit by hand)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from research.data import ARTIFACT_DIR  # noqa: E402
from research.digest import build_overview  # noqa: E402
from research.openset import PROPOSED  # noqa: E402

FIG = ARTIFACT_DIR / "figures"
DOC = ROOT / "docs" / "research" / "RESULTS.md"
BASE = "Closed-set XGB"
# Okabe–Ito palette (colour-blind safe)
C = {"proposed": "#D55E00", "ablation": "#E69F00", "baseline": "#0072B2", "grey": "#999999",
     "recal": "#009E73", "recal+ref": "#CC79A7", "oracle": "#56B4E9", "none": "#000000"}
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.dpi": 110, "savefig.dpi": 300, "savefig.bbox": "tight"})


def _m(ci):
    return np.nan if not ci else ci["mean"]


def _err(ci):
    if not ci or ci.get("low") is None:
        return (0.0, 0.0)
    return (ci["mean"] - ci["low"], ci["high"] - ci["mean"])


def fig_methods(block: dict, proto: str, title: str) -> str:
    rows = [r for r in block["methods"] if r["zero_day_recall"]]
    names = [r["method"] for r in rows]
    vals = [_m(r["zero_day_recall"]) for r in rows]
    errs = np.array([_err(r["zero_day_recall"]) for r in rows]).T
    colors = [C[r["group"]] for r in rows]
    fig, ax = plt.subplots(figsize=(6.4, 0.32 * len(rows) + 1))
    y = np.arange(len(rows))[::-1]
    ax.barh(y, vals, xerr=errs, color=colors, height=0.65, capsize=2, error_kw={"lw": 0.8})
    ax.set_yticks(y, names)
    ax.set_xlim(0, 1)
    ax.set_xlabel("Zero-day recall at benign FPR budget α = 1%  (mean ± 95% CI over seeds)")
    ax.set_title(title, loc="left", fontsize=10)
    for yi, v in zip(y, vals):
        ax.text(min(v + 0.01, 0.93), yi, f"{v:.3f}", va="center", fontsize=7.5)
    path = FIG / f"{proto}_methods.png"
    fig.savefig(path)
    plt.close(fig)
    return path.name


def fig_loafo_by_family(block: dict) -> str:
    fams = [f["fold"] for f in block["folds"]]
    show = [PROPOSED, "Aegis-OSR w/ AE novelty", BASE, "Closed-set DT (v1.1-style)", "kNN distance"]
    show = [m for m in show if m in block["folds"][0]["methods"]]
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    w = 0.8 / len(show)
    palette = [C["proposed"], C["ablation"], C["baseline"], C["grey"], "#009E73"]
    for i, m in enumerate(show):
        v = [_m(f["methods"][m]["zero_day_recall"]) for f in block["folds"]]
        e = np.array([_err(f["methods"][m]["zero_day_recall"]) for f in block["folds"]]).T
        ax.bar(np.arange(len(fams)) + i * w - 0.4 + w / 2, v, w, yerr=e, label=m, color=palette[i], capsize=1.5,
               error_kw={"lw": 0.6})
    ax.set_xticks(np.arange(len(fams)), [f"{f}\n(held out)" for f in fams])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Zero-day recall @ α=1%")
    ax.legend(fontsize=7, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.22), frameon=False)
    path = FIG / "loafo_by_family.png"
    fig.savefig(path)
    plt.close(fig)
    return path.name


def fig_operating(block: dict, proto: str) -> str:
    alphas = [0.001, 0.01, 0.05]
    keys = {0.001: "zero_day_recall_at_0_001", 0.01: "zero_day_recall", 0.05: "zero_day_recall_at_0_05"}
    fig, ax = plt.subplots(figsize=(4.2, 3.0))
    for r in block["methods"]:
        if r["method"] not in (PROPOSED, BASE, "Aegis-OSR w/ AE novelty", "XGB + Energy", "kNN distance"):
            continue
        v = [_m(r[keys[a]]) for a in alphas]
        ax.plot(alphas, v, marker="o", ms=3.5, label=r["method"], color=C.get(r["group"]) if r["group"] != "baseline" or r["method"] == BASE else None,
                lw=2.2 if r["group"] == "proposed" else 1.2)
    ax.set_xscale("log")
    ax.set_xlabel("Benign false-alarm budget α (conformal)")
    ax.set_ylabel("Zero-day recall")
    ax.set_ylim(0, 1)
    ax.legend(fontsize=7, frameon=False)
    path = FIG / f"{proto}_operating_curve.png"
    fig.savefig(path)
    plt.close(fig)
    return path.name


def fig_adaptation(block: dict, proto: str) -> str | None:
    ad = [a for a in block["adaptation"] if a["method"] == PROPOSED]
    if not ad:
        return None
    folds = sorted({a["fold"] for a in ad})
    fig, axes = plt.subplots(2, len(folds), figsize=(3.4 * len(folds), 4.6), squeeze=False)
    for j, fold in enumerate(folds):
        base = next(f for f in block["folds"] if f["fold"] == fold)["methods"][PROPOSED]
        for i, metric in enumerate(("fpr", "zero_day_recall")):
            ax = axes[i, j]
            ax.axhline(_m(base[metric]), color=C["none"], ls=":", lw=1, label="no adaptation")
            for variant in ("recal", "recal+ref"):
                pts = sorted((a["window"], a[metric]) for a in ad if a["fold"] == fold and a["variant"] == variant)
                if pts:
                    xs = [p[0] for p in pts]
                    ax.errorbar(xs, [_m(p[1]) for p in pts], yerr=np.array([_err(p[1]) for p in pts]).T,
                                marker="o", ms=3.5, capsize=2, color=C[variant], label=variant)
            orc = [a for a in ad if a["fold"] == fold and a["variant"] == "oracle"]
            if orc:
                ax.scatter([orc[0]["window"]], [_m(orc[0][metric])], marker="*", s=70, color=C["oracle"],
                           label="oracle (random benign)", zorder=5)
            if metric == "fpr":
                ax.axhline(0.01, color=C["proposed"], lw=0.8, ls="--", label="α = 1%")
                ax.set_ylabel("Realized benign FPR")
            else:
                ax.set_ylabel("Zero-day recall")
                ax.set_ylim(0, 1)
                ax.set_xlabel("Warm-up window (benign flows from target)")
            ax.set_xscale("log")
            ax.set_title(fold if i == 0 else "", fontsize=9)
    axes[0, 0].legend(fontsize=6.5, frameon=False)
    path = FIG / f"{proto}_adaptation.png"
    fig.savefig(path)
    plt.close(fig)
    return path.name


def fig_gate(gate: dict) -> str | None:
    ev = (gate or {}).get("evaluation")
    if not ev:
        return None
    ops = ev["operating_points"]
    a = [o["alpha"] for o in ops]
    fig, ax = plt.subplots(figsize=(4.6, 3.0))
    ax.plot(a, [o["known_attack_recall"] for o in ops], marker="o", label="known-attack recall", color=C["baseline"])
    ax.plot(a, [o["natural_unknown_alert_rate"] for o in ops], marker="s", label="never-seen attack alert rate",
            color=C["proposed"])
    ax.plot(a, [o["benign_fpr"] for o in ops], marker="^", label="benign FPR (realized)", color=C["grey"])
    ax.plot(a, a, ls=":", color="black", lw=0.8, label="α (guaranteed bound)")
    f = ev["frozen_v11"]
    ax.scatter([max(f["benign_fpr"], 1e-4)], [f["known_attack_recall"]], marker="*", s=80, color="black",
               label="frozen v1.1 (known recall)", zorder=5)
    ax.set_xscale("log")
    ax.set_xlabel("Gate α")
    ax.set_ylim(0, 1.02)
    ax.legend(fontsize=6.5, frameon=False)
    path = FIG / "gate_operating_points.png"
    fig.savefig(path)
    plt.close(fig)
    return path.name


def _fmt(ci, pct=False):
    if not ci or ci.get("mean") is None:
        return "—"
    k = 100 if pct else 1
    if ci.get("low") is None or ci.get("n", 0) < 2:
        return f"{ci['mean'] * k:.3f}" if not pct else f"{ci['mean'] * k:.2f}%"
    if pct:
        return f"{ci['mean'] * k:.2f}% [{ci['low'] * k:.2f}, {ci['high'] * k:.2f}]"
    return f"{ci['mean']:.3f} [{ci['low']:.3f}, {ci['high']:.3f}]"


def table_methods(block: dict) -> str:
    lines = ["| Method | Group | Zero-day recall @1% | AUROC (unknown) | Known recall | Realized FPR |",
             "|---|---|---|---|---|---|"]
    for r in block["methods"]:
        name = f"**{r['method']}**" if r["group"] == "proposed" else r["method"]
        lines.append(f"| {name} | {r['group']} | {_fmt(r['zero_day_recall'])} | {_fmt(r['auroc_unknown'])} | "
                     f"{_fmt(r['known_recall'])} | {_fmt(r['fpr'], pct=True)} |")
    return "\n".join(lines)


def table_sig(block: dict) -> str:
    rows = [s for s in block["significance"] if s["metric"] == "zero_day_recall"]
    if not rows:
        return "_No significance tests yet._"
    lines = ["| Aegis-OSR vs | Mean Δ zero-day recall [95% CI] | Seeds better | Paired t p (seeds) | Fold W / L / T (descriptive) |",
             "|---|---|---|---|---|"]
    for s in sorted(rows, key=lambda s: s.get("p_value") if s.get("p_value") is not None else 1):
        p = s.get("p_value")
        ci = (f" [{s['diff_ci_low']:+.3f}, {s['diff_ci_high']:+.3f}]"
              if s.get("diff_ci_low") is not None and s.get("diff_ci_high") is not None else "")
        seeds = f"{s['positive_seeds']} / {s['n_seeds']}" if s.get("n_seeds") else "—"
        lines.append(f"| {s['versus']} | {s['mean_diff']:+.3f}{ci} | {seeds} | {'—' if p is None else f'{p:.2e}'} | "
                     f"{s['wins']} / {s['losses']} / {s['ties']} |")
    return "\n".join(lines)


def table_folds(block: dict) -> str:
    methods = [PROPOSED, BASE, "Aegis-OSR w/ AE novelty", "Closed-set DT (v1.1-style)"]
    lines = ["| Fold | " + " | ".join(methods) + " |", "|---|" + "---|" * len(methods)]
    for f in block["folds"]:
        cells = []
        for m in methods:
            v = f["methods"].get(m, {})
            cells.append(f"{_fmt(v.get('zero_day_recall'))}<br/>FPR {_fmt(v.get('fpr'), pct=True)}")
        lines.append(f"| {f['fold']} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def table_adapt(block: dict) -> str:
    ad = [a for a in block["adaptation"] if a["method"] == PROPOSED]
    if not ad:
        return "_No adaptation results._"
    lines = ["| Fold | Variant | Window | Zero-day recall | Realized FPR |", "|---|---|---|---|---|"]
    for a in sorted(ad, key=lambda a: (a["fold"], a["variant"], a["window"])):
        lines.append(f"| {a['fold']} | {a['variant']} | {a['window']} | {_fmt(a['zero_day_recall'])} | {_fmt(a['fpr'], pct=True)} |")
    return "\n".join(lines)


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    DOC.parent.mkdir(parents=True, exist_ok=True)
    ov = build_overview(ARTIFACT_DIR)
    md = ["# Aegis-OSR — results (auto-generated)", "",
          f"_Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} by "
          "`scripts/55_research_figures.py`. Do not edit by hand — rerun the script._", "",
          "Design selected on pilot seed 0; all numbers below use fresh seeds (see `meta`). "
          "α = 1% benign false-alarm budget unless stated; brackets are 95% t-intervals over seeds.", ""]
    titles = {"loafo": "Leave-one-attack-family-out (CICIDS2017)",
              "temporal": "True temporal holdout (CICIDS2017 capture days)",
              "cross": "Cross-dataset: CICIDS2017 → CSE-CIC-IDS2018"}
    for proto in ("loafo", "temporal", "cross"):
        block = ov.get(proto)
        md += [f"## {titles[proto]}", ""]
        if not block:
            md += [f"_Not generated yet: `python scripts/50_openset_experiments.py --protocol {proto}`._", ""]
            continue
        meta = block["meta"] or {}
        md += [f"Seeds: {meta.get('seeds')} · records: {meta.get('n_records')} · commit `{meta.get('git_commit')}`", ""]
        md += [f"![{proto} methods](../../research_artifacts/figures/{fig_methods(block, proto, titles[proto])})", ""]
        md += [table_methods(block), "", "**Seed-level paired comparison (folds averaged within each seed; fold W/L/T descriptive only)**", "", table_sig(block), ""]
        if proto == "loafo":
            md += [f"![per family](../../research_artifacts/figures/{fig_loafo_by_family(block)})", "",
                   f"![operating curve](../../research_artifacts/figures/{fig_operating(block, proto)})", ""]
        md += ["**Per fold (zero-day recall, realized FPR)**", "", table_folds(block), ""]
        if block["adaptation"]:
            name = fig_adaptation(block, proto)
            md += ["**Label-light adaptation (no retraining)**", "", f"![adaptation](../../research_artifacts/figures/{name})",
                   "", table_adapt(block), ""]
    gate = ov.get("gate")
    if gate:
        g = fig_gate(gate)
        ev = gate["evaluation"]
        md += ["## Production Zero-Day Gate", "", f"![gate](../../research_artifacts/figures/{g})", "",
               "| α | Benign FPR | Known-attack recall | Never-seen alert rate |", "|---|---|---|---|"]
        for o in ev["operating_points"]:
            md.append(f"| {o['alpha']} | {o['benign_fpr'] * 100:.3f}% | {o['known_attack_recall']:.4f} | {o['natural_unknown_alert_rate']:.3f} |")
        f = ev["frozen_v11"]
        md += ["", f"Frozen v1.1 reference: benign FPR {f['benign_fpr'] * 100:.3f}%, known recall "
               f"{f['known_attack_recall']:.4f}, never-seen attack rate {f['natural_unknown_attack_rate']:.3f}.", "",
               f"> {ev.get('note', '')}", ""]
    fz = ov.get("frozen_v11_on_cic2018")
    if fz:
        b = fz["binary"]
        md += ["## Frozen v1.1 on CSE-CIC-IDS2018 (EXP-009, no retraining)", "",
               f"Precision {b['precision']:.3f} · recall {b['recall']:.3f} · F1 {b['f1']:.3f} · benign FPR "
               f"{b['benign_fpr'] * 100:.2f}% (IID CICIDS2017 F1 reference: {b.get('iid_cicids2017_f1_reference')})", "",
               "| 2018 label | Family | n | Alert rate | Family match |", "|---|---|---|---|---|"]
        for r in fz["per_label"]:
            fm = r.get("family_match_rate")
            md.append(f"| {r['label']} | {r['family']} | {r['n']} | {r['alert_rate']:.3f} | {'—' if fm is None else f'{fm:.3f}'} |")
        md += ["", f"> {fz['interpretation']}", ""]
    DOC.write_text("\n".join(md), encoding="utf-8")
    print(f"wrote {DOC.relative_to(ROOT)} and {len(list(FIG.glob('*.png')))} figures")


if __name__ == "__main__":
    main()
