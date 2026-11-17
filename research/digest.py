"""UI-ready digest of every v3 research artifact (served by GET /api/research/overview)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research.openset import METHODS, PROPOSED

BASELINE = "Closed-set XGB"


def _load(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _ci(d: dict | None) -> dict | None:
    if not d or d.get("mean") is None:
        return None
    return {"mean": d["mean"], "low": d.get("ci_low"), "high": d.get("ci_high"), "n": d.get("n")}


def _method_rows(overall: dict) -> list[dict]:
    rows = []
    for name, m in overall.items():
        spec = METHODS.get(name)
        rows.append({
            "method": name,
            "group": spec.group if spec else "baseline",
            "evidence": list(spec.evidence) if spec else [],
            "fusion": spec.fusion if spec else None,
            "zero_day_recall": _ci(m.get("zero_day_recall")),
            "zero_day_recall_at_0_001": _ci(m.get("zero_day_recall@0.001")),
            "zero_day_recall_at_0_05": _ci(m.get("zero_day_recall@0.05")),
            "auroc_unknown": _ci(m.get("auroc_unknown")),
            "auprc_unknown": _ci(m.get("auprc_unknown")),
            "known_recall": _ci(m.get("known_recall")),
            "fpr": _ci(m.get("fpr")),
        })
    order = {"proposed": 0, "ablation": 1, "baseline": 2}
    return sorted(rows, key=lambda r: (order.get(r["group"], 3), -(r["zero_day_recall"] or {}).get("mean", 0)))


def _protocol(summary: dict, proto: str) -> dict | None:
    if not summary or proto not in summary.get("overall", {}):
        return None
    per_fold = summary["per_fold"][proto]
    folds = []
    for fold, methods in per_fold.items():
        folds.append({
            "fold": fold,
            "methods": {m: {"zero_day_recall": _ci(v.get("zero_day_recall")), "fpr": _ci(v.get("fpr")),
                            "auroc_unknown": _ci(v.get("auroc_unknown"))} for m, v in methods.items()},
        })
    # Primary statistic = seed-level paired test (independent seeds); fold-level W/L/T is descriptive.
    sig = []
    seed_level = (summary.get("significance_seed_level", {}) or {}).get(proto) or {}
    for metric, by_method in (summary.get("significance", {}).get(proto) or {}).items():
        for method, t in by_method.items():
            s = (seed_level.get(metric) or {}).get(method) or {}
            sig.append({
                "metric": metric, "versus": method,
                "n": t.get("n"), "wins": t.get("wins"), "losses": t.get("losses"), "ties": t.get("ties"),
                "mean_diff": s.get("mean_diff", t.get("mean_diff")),
                "diff_ci_low": s.get("diff_ci_low"), "diff_ci_high": s.get("diff_ci_high"),
                "n_seeds": s.get("n_seeds"), "positive_seeds": s.get("positive_seeds"),
                "p_value": s.get("t_p_value"), "test": "paired t over seeds" if s else "wilcoxon over fold×seed pairs",
                "fold_pair_wilcoxon_p": t.get("p_value"),
            })
    adaptation = []
    for key, ad in (summary.get("adaptation", {}).get(proto) or {}).items():
        for fold, methods in ad["per_fold"].items():
            for m in (PROPOSED, BASELINE):
                if m in methods:
                    adaptation.append({
                        "key": key, "variant": ad["variant"], "window": ad["window"], "fold": fold, "method": m,
                        "zero_day_recall": _ci(methods[m].get("zero_day_recall")), "fpr": _ci(methods[m].get("fpr")),
                    })
    per_family = {
        fam: {m: _ci(v) for m, v in d.items()}
        for fam, d in (summary.get("per_family", {}).get(proto) or {}).items()
    }
    attribution = {
        fold: {k: _ci(v) for k, v in d.items()}
        for fold, d in (summary.get("attribution", {}).get(proto) or {}).items()
    }
    meta = summary.get("meta", {})
    return {
        "methods": _method_rows(summary["overall"][proto]),
        "folds": folds,
        "per_family": per_family,
        "significance": sig,
        "adaptation": adaptation,
        "attribution": attribution,
        "meta": {k: meta.get(k) for k in ("generated_at", "git_commit", "seeds", "alpha", "n_records", "runtime_seconds", "caps")},
    }


def build_overview(artifacts: Path) -> dict:
    summaries = {p: _load(artifacts / f"openset_{p}_summary.json") for p in ("loafo", "temporal", "cross")}
    # R1b: prefer results on the corrected CSE-CIC-IDS2018 sample (benign traffic from every capture day)
    summaries["cross"] = _load(artifacts / "openset_cross_summary_v2.json") or summaries["cross"]
    gate = _load(artifacts / "zero_day_gate_report.json")
    frozen_2018 = _load(artifacts / "frozen_v11_on_cic2018_v2.json") or _load(artifacts / "frozen_v11_on_cic2018.json")
    out = {
        "proposed": PROPOSED,
        "baseline": BASELINE,
        "methods_catalog": [
            {"method": n, "group": s.group, "evidence": list(s.evidence), "fusion": s.fusion} for n, s in METHODS.items()
        ],
        "status": {**{p: s is not None for p, s in summaries.items()}, "gate": gate is not None,
                   "frozen_2018": frozen_2018 is not None},
        "loafo": _protocol(summaries["loafo"], "loafo"),
        "temporal": _protocol(summaries["temporal"], "temporal"),
        "cross": _protocol(summaries["cross"], "cross_dataset"),
        "gate": gate,
        "frozen_v11_on_cic2018": frozen_2018,
    }
    headline = {}
    for proto in ("loafo", "temporal", "cross"):
        block = out[proto]
        if not block:
            continue
        by = {r["method"]: r for r in block["methods"]}
        p, b = by.get(PROPOSED), by.get(BASELINE)
        if p and b and p["zero_day_recall"] and b["zero_day_recall"]:
            headline[proto] = {
                "proposed_zero_day_recall": p["zero_day_recall"]["mean"],
                "baseline_zero_day_recall": b["zero_day_recall"]["mean"],
                "proposed_fpr": (p["fpr"] or {}).get("mean"),
                "baseline_fpr": (b["fpr"] or {}).get("mean"),
                "proposed_auroc": (p["auroc_unknown"] or {}).get("mean"),
                "baseline_auroc": (b["auroc_unknown"] or {}).get("mean"),
            }
    out["headline"] = headline
    return out
