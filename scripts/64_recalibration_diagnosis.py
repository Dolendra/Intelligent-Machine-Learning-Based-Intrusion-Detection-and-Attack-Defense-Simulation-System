"""Exploratory diagnosis: why per-day re-calibration on CSE-CIC-IDS2018 restores the false-alarm rate but not detection.

POST-HOC ANALYSIS of committed records only (no training, no new data):
    research_artifacts/openset_cross_perday_records.json   (cross_perday protocol, seeds 1-5, sample v2)
    research_artifacts/openset_loafo_summary.json          (in-distribution reference, if present)

It was designed AFTER seeing the per-day results, so it generates hypotheses; it does not confirm them.
Any method motivated by it must be validated on data and protocols not used here (see R3_PROTOCOL.md).

Writes research_artifacts/recalibration_diagnosis.json.

    python scripts/64_recalibration_diagnosis.py
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, stdev

from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
ART = ROOT / "research_artifacts"
SRC = ART / "openset_cross_perday_records.json"
OUT = ART / "recalibration_diagnosis.json"

METHODS = ["Aegis-OSR", "Aegis-OSR w/ max fusion", "Aegis-OSR w/ omnibus fusion", "Closed-set XGB", "XGB + Energy",
           "kNN distance"]
VARIANTS = ["none", "recal@500", "recal@2000", "recal@5000", "recal+ref@500", "recal+ref@2000", "recal+ref@5000"]
METRICS = ["fpr", "known_recall", "zero_day_recall", "auroc_all"]
REFERENCE = "Aegis-OSR"


def _m(xs):
    xs = [x for x in xs if x is not None and not (isinstance(x, float) and math.isnan(x))]
    return mean(xs) if xs else None


def _get(rec: dict, variant: str, method: str) -> dict | None:
    if variant == "none":
        return rec["methods"].get(method)
    return rec["adaptation"][variant]["methods"].get(method)


def seed_level(records: list[dict], variant: str, method: str, metric: str) -> list[float]:
    """One value per seed: the metric averaged over the 2018 days of that seed (days share a trained model)."""
    out = []
    for s in sorted({r["seed"] for r in records}):
        v = _m((_get(r, variant, method) or {}).get(metric) for r in records if r["seed"] == s)
        if v is not None:
            out.append(v)
    return out


def paired(records, variant, method, metric="known_recall") -> dict:
    a = seed_level(records, variant, method, metric)
    b = seed_level(records, variant, REFERENCE, metric)
    d = [x - y for x, y in zip(a, b)]
    t = stats.ttest_1samp(d, 0.0)
    half = stats.t.ppf(0.975, len(d) - 1) * stdev(d) / math.sqrt(len(d))
    return {"method_minus_aegis_osr": mean(d), "ci95": [mean(d) - half, mean(d) + half], "seeds_better": sum(x > 0 for x in d),
            "n_seeds": len(d), "paired_t_p": float(t.pvalue)}


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=OUT, help="output path (the committed file is protected)")
    out = ap.parse_args().out
    sys.path.insert(0, str(ROOT))
    from research.artifact_guard import assert_writable
    assert_writable(out)
    data = json.loads(SRC.read_text(encoding="utf-8"))
    recs = data["records"]
    days = sorted({r["fold"] for r in recs})

    overall = {v: {m: {k: _m((_get(r, v, m) or {}).get(k) for r in recs) for k in METRICS} for m in METHODS}
               for v in VARIANTS}
    per_day = {}
    for d in days:
        rs = [r for r in recs if r["fold"] == d]
        per_day[d] = {"attack_families": {k: v for k, v in rs[0]["test_families"].items() if k != "BENIGN"},
                      "variants": {v: {m: {k: _m((_get(r, v, m) or {}).get(k) for r in rs) for k in METRICS}
                                       for m in METHODS} for v in VARIANTS}}
    comparisons = {v: {m: paired(recs, v, m) for m in METHODS if m != REFERENCE}
                   for v in ["recal@2000", "recal@5000", "recal+ref@2000", "recal+ref@5000"]}

    loafo = None
    lsum = ART / "openset_loafo_summary.json"
    if lsum.exists():
        ls = json.loads(lsum.read_text(encoding="utf-8"))
        loafo = {"source": "research_artifacts/openset_loafo_summary.json", "note": "in-distribution reference; "
                 "read the zero-day recall of each fusion rule from the summary (Table I of the paper)"}
        meth = ls["overall"]["loafo"]
        loafo["zero_day_recall_mean"] = {m: meth[m]["zero_day_recall"]["mean"] for m in METHODS if m in meth}

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "exploratory / post-hoc — hypothesis-generating, not confirmatory",
        "source": str(SRC.relative_to(ROOT).as_posix()),
        "source_meta": data["meta"],
        "statistics": "seed-level: metric averaged over days within each seed (days share the trained model), "
                      "then a paired t-test over 5 independent seeds; days are not independent samples",
        "overall_mean_over_days_and_seeds": overall,
        "per_day_mean_over_seeds": per_day,
        "seed_level_known_recall_vs_aegis_osr": comparisons,
        "in_distribution_reference": loafo,
    }
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")

    print(f"wrote {out}")
    for v in ["none", "recal@2000", "recal+ref@2000", "recal+ref@5000"]:
        print(f"\n{v}:  FPR / known recall / AUROC(benign vs attacks)")
        for m in METHODS:
            o = overall[v][m]
            print(f"  {m:28s} {o['fpr']:.4f} / {o['known_recall']:.3f} / {o['auroc_all']:.3f}")
    print("\nseed-level known recall, method − Aegis-OSR, recal@2000:")
    for m, c in comparisons["recal@2000"].items():
        print(f"  {m:28s} {c['method_minus_aegis_osr']:+.3f} [{c['ci95'][0]:+.3f}, {c['ci95'][1]:+.3f}] "
              f"{c['seeds_better']}/{c['n_seeds']} p={c['paired_t_p']:.2g}")
    if loafo:
        print("\nLOAFO zero-day recall (in-distribution):", {k: round(v, 3) for k, v in loafo["zero_day_recall_mean"].items()})


if __name__ == "__main__":
    main()
