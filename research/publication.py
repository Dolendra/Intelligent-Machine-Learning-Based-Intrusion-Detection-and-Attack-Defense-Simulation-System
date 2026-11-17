"""Canonical publication tables (R1b).

Every numerical table in the research paper is produced here from committed result artifacts —
never typed by hand. One :class:`Table` per key is rendered three ways from the same object:

* DOCX  — ``docs/research/paper_build/paper.py`` calls :func:`build_tables` and passes rows to its
  table helper;
* LaTeX — ``docs/research/publication/tables/<key>.tex`` (``\\input`` by ``paper.tex``);
* Markdown — ``docs/research/publication/TABLES.md``.

``docs/research/publication/publication_tables.json`` stores every rendered table with the exact
source file and JSON path of its numbers; ``tests/test_publication_tables.py`` rebuilds them from
the artifacts and compares, so any drift or hand edit fails the test suite.

Cells may contain ``**bold**`` (DOCX/Markdown convention); LaTeX rendering converts it.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
RA = "research_artifacts"
LOAFO = f"{RA}/openset_loafo_summary.json"
TEMPORAL = f"{RA}/openset_temporal_summary.json"
CROSS_V2 = f"{RA}/openset_cross_summary_v2.json"
CROSS_V1 = f"{RA}/openset_cross_summary.json"
PERDAY = f"{RA}/openset_cross_perday_summary.json"
PERDAY_REC = f"{RA}/openset_cross_perday_records.json"
FROZEN18_V2 = f"{RA}/frozen_v11_on_cic2018_v2.json"
FROZEN18_V1 = f"{RA}/frozen_v11_on_cic2018.json"
FAMILIES = f"{RA}/model_family_comparison.json"
DATASET = f"{RA}/dataset_summary.json"
TRAINING = "models/trained_models/training_report.json"
P11 = "models/trained_models/empirical_mitigation_report.json"
ENVELOPE = "results/performance/operating_envelope_latest.json"
DBPERF = "results/performance/database_response_20260914T190735Z_perf-dc84a3431e.json"
GATE = f"{RA}/zero_day_gate_report.json"
RANGE = "results/cyber_range/experiments/latest.json"

OSR, XGB, DT = "Aegis-OSR", "Closed-set XGB", "Closed-set DT (v1.1-style)"
FRI, THU = "Mon-Thu→Fri", "Mon-Wed→Thu"
X18 = "CICIDS2017→CSE-CIC-IDS2018"
DASH = "—"


@dataclass
class Table:
    key: str
    title: str
    header: list[str]
    rows: list[list[str]]
    notes: str = ""
    sources: list[str] = field(default_factory=list)
    docx: dict = field(default_factory=dict)  # layout hints for the DOCX builder (widths, size)


_cache: dict[str, Any] = {}


def load(rel: str) -> Any:
    if rel not in _cache:
        _cache[rel] = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    return _cache[rel]


def exists(rel: str) -> bool:
    return (ROOT / rel).exists()


# ------------------------------------------------------------------------------- formatting
def f3(v: float | None) -> str:
    return DASH if v is None else f"{v:.3f}"


def f4(v: float | None) -> str:
    return DASH if v is None else f"{v:.4f}"


def f5(v: float | None) -> str:
    return DASH if v is None else f"{v:.5f}"


def pct(v: float | None, d: int = 1) -> str:
    return DASH if v is None else f"{100 * v:.{d}f}%"


def pnum(v: float | None, d: int = 2) -> str:
    """Percentage number without the sign (for '(%)' columns)."""
    return DASH if v is None else f"{100 * v:.{d}f}"


def n0(v: float | int | None) -> str:
    return DASH if v is None else f"{int(round(v)):,}"


def ci(c: dict | None, fmt: Callable = f3) -> str:
    if not c or c.get("mean") is None:
        return DASH
    if c.get("ci_low") is None or c.get("n", 0) < 2:
        return fmt(c["mean"])
    return f"{fmt(c['mean'])} [{fmt(c['ci_low'])}, {fmt(c['ci_high'])}]"


def m(c: dict | None) -> float | None:
    return None if not c else c.get("mean")


def bold(s: str) -> str:
    return f"**{s}**"


def bold_best_in_row(row: list[str], cols: list[int], values: list[float | None]) -> None:
    """Bold the unique highest value among ``cols`` of one row (ties → no bold)."""
    ok = [v for v in values if v is not None]
    if not ok:
        return
    best = max(ok)
    hits = [c for c, v in zip(cols, values) if v is not None and round(v, 6) == round(best, 6)]
    if len(hits) == 1:
        row[hits[0]] = bold(row[hits[0]])


def bold_best(rows: list[list[str]], cols: list[int], values: list[list[float | None]], lower: set[int] = frozenset()):
    """Bold the unique best value per column across rows (ties → no bold)."""
    for j, c in enumerate(cols):
        vals = [v[j] for v in values]
        ok = [x for x in vals if x is not None]
        if not ok:
            continue
        best = min(ok) if c in lower else max(ok)
        if sum(1 for x in vals if x is not None and round(x, 6) == round(best, 6)) == 1:
            i = next(i for i, x in enumerate(vals) if x is not None and round(x, 6) == round(best, 6))
            rows[i][c] = bold(rows[i][c])


# ------------------------------------------------------------------------------- tables
def t_data() -> Table:
    d = load(DATASET)["cic2017"]
    days = {}
    for day, fams in d["by_day_family"].items():
        for f in fams:
            days.setdefault(f, []).append(day)
    short = {"Monday": "Mon", "Tuesday": "Tue", "Wednesday": "Wed", "Thursday": "Thu", "Friday": "Fri"}
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

    def span(f: str) -> str:
        ds = sorted(days.get(f, []), key=order.index)
        return "Mon–Fri" if len(ds) == 5 else ", ".join(short[x] for x in ds)

    fams = sorted(d["by_family"], key=lambda f: (f != "BENIGN", f in ("Infiltration", "Heartbleed"), -d["by_family"][f]))
    rows = []
    for f in fams:
        role = ("negative class; calibration" if f == "BENIGN" else "natural unknown (never trained on)"
                if f in ("Infiltration", "Heartbleed") else "known / held out in LOAFO")
        rows.append([f, n0(d["by_family"][f]), span(f), role])
    rows.append(["Total", n0(d["rows"]), "", f"{d['n_features']} features after cleaning"])
    return Table("data", "Composition of the Cleaned CICIDS2017 Corpus", ["Family", "Flows", "Capture day(s)", "Role in this study"],
                 rows, sources=[f"{DATASET}:cic2017"], docx={"widths": [1.4, 1.2, 1.3, 2.6]})


def t_cand() -> Table:
    v = load(TRAINING)["binary"]["validation"]
    best = load(TRAINING)["binary"]["best"]
    names = {"logistic_regression": "Logistic regression", "decision_tree": "Decision Tree",
             "random_forest": "Random Forest", "xgboost": "XGBoost"}
    keys = ["precision", "recall", "f1", "fpr", "pr_auc", "mcc", "selection_score"]
    rows, vals = [], []
    for k in names:
        r = v[k]
        label = names[k] + (" (selected)" if k == best else "")
        rows.append([bold(label) if k == best else label] + [f4(r[x]) for x in keys])
        vals.append([r[x] for x in keys])
    bold_best(rows, list(range(1, 8)), vals, lower={4})
    n = sum(v[best]["confusion_matrix"][0]) + sum(v[best]["confusion_matrix"][1])
    return Table("cand", f"Binary Candidates on the Validation Split ({n:,} Flows)",
                 ["Model", "Precision", "Recall", "F1", "FPR", "PR-AUC", "MCC", "Score S"], rows,
                 notes="Score S is the project's weighted selection score (recall, F1, PR-AUC, FPR, latency; config.yaml).",
                 sources=[f"{TRAINING}:binary.validation", f"{TRAINING}:binary.best"],
                 docx={"widths": [1.9, 0.75, 0.75, 0.75, 0.75, 0.75, 0.75, 0.8], "size": 8})


def t_v11() -> Table:
    t = load(TRAINING)
    b, mc = t["binary"]["test"], t["multiclass"]["test"]
    cm = mc["confusion_matrix"]
    total = sum(sum(r) for r in cm)
    wrong = total - sum(cm[i][i] for i in range(len(cm)))
    rows = [
        ["Binary (DT, τ = 0.85)", "Precision", f5(b["precision"]), "F1", bold(f5(b["f1"]))],
        ["", "Recall", f5(b["recall"]), "ROC-AUC", f5(b["roc_auc"])],
        ["", "FPR", f5(b["fpr"]), "PR-AUC", f5(b["pr_auc"])],
        ["", "TP / FN", f"{b['true_positives']:,} / {b['false_negatives']:,}", "TN / FP",
         f"{b['true_negatives']:,} / {b['false_positives']:,}"],
        ["", "Brier", f5(b["brier_score"]), "ECE", f5(b["ece"])],
        ["Multiclass (RF, attack-only)", "Accuracy", f5(mc["accuracy"]), "Macro-F1", bold(f5(mc["f1_macro"]))],
        ["", "Macro precision", f5(mc["precision_macro"]), "Macro recall", f5(mc["recall_macro"])],
        ["", "Weighted F1", f5(mc["f1_weighted"]), "Misattributed", f"{wrong:,} / {total:,}"],
    ]
    return Table("v11", "Frozen Closed-Set Detector (v1.1) on the Stratified Test Split",
                 ["Stage", "Metric", "Value", "Metric", "Value"], rows,
                 sources=[f"{TRAINING}:binary.test", f"{TRAINING}:multiclass.test"], docx={"widths": [1.9, 1.2, 1.1, 1.2, 1.1]})


LOAFO_ORDER = [(OSR, "proposed", "**Aegis-OSR**"), ("Aegis-OSR w/ omnibus fusion", "ablation", "  w/ omnibus fusion"),
               ("Aegis-OSR w/ AE novelty", "ablation", "  w/ AE novelty"), ("Aegis-OSR w/ max fusion", "ablation", "  w/ max fusion"),
               ("Aegis-OSR w/ IForest novelty", "ablation", "  w/ IForest novelty"), (XGB, "baseline", XGB),
               ("XGB + Energy", "baseline", "XGB + Energy"), ("kNN distance", "baseline", "k-NN distance"),
               (DT, "baseline", DT), ("Autoencoder", "baseline", "Autoencoder"), ("Isolation Forest", "baseline", "Isolation Forest")]


def t_loafo() -> Table:
    s = load(LOAFO)
    o = s["overall"]["loafo"]
    rows, vals = [], []
    for key, group, label in LOAFO_ORDER:
        r = o[key]
        rows.append([label, group, ci(r["zero_day_recall"]), ci(r["auroc_unknown"]), ci(r["known_recall"]),
                     ci(r["fpr"], lambda v: f"{100 * v:.2f}")])
        vals.append([m(r["zero_day_recall"]), m(r["auroc_unknown"])])
    bold_best(rows, [2, 3], vals)
    seeds = s["meta"]["seeds"]
    return Table("loafo", f"Leave-One-Attack-Family-Out on CICIDS2017 at α = 1% (Mean and 95% CI over {len(seeds)} Seeds)",
                 ["Method", "Group", "Zero-day recall", "AUROC_u", "Known recall", "Benign FPR (%)"], rows,
                 notes="Folds are averaged within each seed; intervals are 95% Student-t intervals over seeds. "
                       "AUROC_u: area under the ROC curve for unknown versus benign flows.",
                 sources=[f"{LOAFO}:overall.loafo"], docx={"widths": [1.8, 0.8, 1.35, 1.35, 1.1, 1.1], "size": 8})


def t_significance() -> Table:
    s = load(LOAFO)
    sig = s["significance_seed_level"]["loafo"]["zero_day_recall"]
    pairs = s["significance"]["loafo"]["zero_day_recall"]
    rows = []
    for key in sorted(sig, key=lambda k: -sig[k]["mean_diff"]):
        t, p = sig[key], pairs[key]
        mant, exp = f"{t['t_p_value']:.1e}".split("e")
        rows.append([key, f"{t['mean_diff']:+.3f} [{t['diff_ci_low']:+.3f}, {t['diff_ci_high']:+.3f}]",
                     f"{t['positive_seeds']} / {t['n_seeds']}", f"{mant}×10^{{{int(exp)}}}".replace("-", "−"),
                     f"{p['wins']} / {p['n']}"])
    return Table("significance", "Seed-Level Paired Comparison of Zero-Day Recall (Folds Averaged Within Each Seed)",
                 ["Aegis-OSR vs.", "Mean Δ recall [95% CI]", "Seeds better", "Paired t p", "Fold wins (descriptive)"], rows,
                 notes="Paired t-test over independent seeds; the six folds of one seed share a data split, so fold-level "
                       "wins are not independent observations and are shown for context only.",
                 sources=[f"{LOAFO}:significance_seed_level.loafo.zero_day_recall", f"{LOAFO}:significance.loafo.zero_day_recall"],
                 docx={"widths": [2.2, 1.7, 0.9, 1.0, 1.2]})


def t_family() -> Table:
    s = load(LOAFO)
    pf, at = s["per_fold"]["loafo"], s["attribution"]["loafo"]
    fams = sorted(pf, key=lambda f: -m(pf[f][OSR]["zero_day_recall"]))
    rows = []
    for f in fams:
        rec = [m(pf[f][k]["zero_day_recall"]) for k in (OSR, XGB, "Aegis-OSR w/ AE novelty", DT)]
        a = at[f]
        rows.append([f] + [f3(x) for x in rec] + [f3(m(a["unknown_flagged_as_unknown"])),
                                                   f3(m(a["unknown_misattributed_to_known"])),
                                                   f3(m(a["known_family_accuracy"]))])
        bold_best_in_row(rows[-1], [1, 2, 3, 4], rec)
    return Table("family", f"Per-Family Zero-Day Recall and Aegis-OSR Attribution (LOAFO, α = 1%, Mean over {len(s['meta']['seeds'])} Seeds)",
                 ["Held-out family", "Aegis-OSR", "Closed-set XGB", "w/ AE novelty", "DT (v1.1-style)", "Flagged unknown",
                  "Mis-attributed", "Known-family acc."], rows,
                 notes="The last three columns refer to Aegis-OSR. Flagged unknown: share of the withheld family labelled "
                       "UNKNOWN-ATTACK or ZERO-DAY-ANOMALY. Mis-attributed: share wrongly given a known-family label. "
                       "Known-family acc.: accuracy of family labels on attacks from the five known families.",
                 sources=[f"{LOAFO}:per_fold.loafo", f"{LOAFO}:attribution.loafo"],
                 docx={"widths": [1.1, 0.75, 0.85, 0.8, 0.85, 0.85, 0.8, 0.85], "size": 8})


TEMPORAL_METHODS = [OSR, "Aegis-OSR w/ AE novelty", XGB, "XGB + Energy", "kNN distance", "Autoencoder", DT]


def t_temporal() -> Table:
    s = load(TEMPORAL)
    pf = s["per_fold"]["temporal"]
    rows = [[k.replace("kNN distance", "k-NN distance"), f3(m(pf[THU][k]["zero_day_recall"])), pnum(m(pf[THU][k]["fpr"])),
             f3(m(pf[FRI][k]["zero_day_recall"])), pnum(m(pf[FRI][k]["fpr"]))] for k in TEMPORAL_METHODS]
    fam = s["per_family"]["temporal"]
    thu = [f for f in ("WebAttack", "Infiltration") if f in fam]
    fri = [f for f in ("DDoS", "PortScan", "Bot") if f in fam]
    note = ("Unknown-family recall of Aegis-OSR (closed-set XGB in brackets) — Thursday: "
            + ", ".join(f"{f} {f3(m(fam[f][OSR]))} ({f3(m(fam[f][XGB]))})" for f in thu)
            + "; Friday: " + ", ".join(f"{f} {f3(m(fam[f][OSR]))} ({f3(m(fam[f][XGB]))})" for f in fri)
            + ". Recall is not comparable across rows when the realised FPR differs from the budget.")
    return Table("temporal", f"Temporal Split by Capture Day, No Adaptation (α = 1%, Mean over {len(s['meta']['seeds'])} Seeds)",
                 ["Method", "Mon–Wed → Thu recall", "FPR (%)", "Mon–Thu → Fri recall", "FPR (%)"], rows, notes=note,
                 sources=[f"{TEMPORAL}:per_fold.temporal", f"{TEMPORAL}:per_family.temporal"],
                 docx={"widths": [2.2, 1.3, 0.8, 1.3, 0.8]})


ADAPT_ROWS = [("none", 0), ("recal", 500), ("recal", 2000), ("recal", 5000), ("recal+ref", 500), ("recal+ref", 2000),
              ("recal+ref", 5000), ("oracle", 2000)]


def _cell(pair: dict | None) -> str:
    if not pair:
        return DASH
    return f"{f3(m(pair.get('zero_day_recall')))} / {pct(m(pair.get('fpr')), 2)}"


def _adapt_rows(summary: dict, proto: str, folds: list[tuple[str, str]], methods: list[str]) -> list[list[str]]:
    pf, ad = summary["per_fold"][proto], summary.get("adaptation", {}).get(proto, {})
    rows = []
    for fold, label in folds:
        first = True
        for variant, w in ADAPT_ROWS:
            if variant == "none":
                src = pf[fold]
            else:
                key = f"{variant}@{w}"
                if key not in ad or fold not in ad[key]["per_fold"]:
                    continue
                src = ad[key]["per_fold"][fold]
            rows.append([label if first else "", variant, f"{w:,}"] + [_cell(src.get(k)) for k in methods])
            first = False
    return rows


def t_adapt() -> Table:
    s = load(TEMPORAL)
    methods = [OSR, XGB, "XGB + Energy"]
    rows = _adapt_rows(s, "temporal", [(FRI, "Mon–Thu → Fri"), (THU, "Mon–Wed → Thu")], methods)
    return Table("adapt", f"Re-Calibration on Benign Flows from the Target Day (Zero-Day Recall / Benign FPR, Mean over {len(s['meta']['seeds'])} Seeds)",
                 ["Fold", "Variant", "W", OSR, XGB, "XGB + Energy"], rows,
                 notes="Warm-up windows are the earliest W benign flows of the target day and are excluded from evaluation; "
                       "the oracle re-calibrates on 2,000 benign flows sampled at random from the day. recal+ref also adds "
                       "one third of the window to the k-NN reference; methods without a k-NN component change only through "
                       "the smaller calibration split.",
                 sources=[f"{TEMPORAL}:per_fold.temporal", f"{TEMPORAL}:adaptation.temporal"],
                 docx={"widths": [1.1, 0.8, 0.6, 1.4, 1.4, 1.4], "size": 8})


def _frozen18() -> tuple[str, dict]:
    return (FROZEN18_V2, load(FROZEN18_V2)) if exists(FROZEN18_V2) else (FROZEN18_V1, load(FROZEN18_V1))


def t_v11_2018() -> Table:
    src, d = _frozen18()
    rows = []
    labs = sorted(d["per_label"], key=lambda r: (r["family"] != "BENIGN", -r["alert_rate"]))
    for r in labs:
        rows.append([r["label"], r["family"], n0(r["n"]), pct(r["alert_rate"], 2),
                     DASH if r.get("family_match_rate") is None else pct(r["family_match_rate"], 2)])
    b = d["binary"]
    rows.append([bold("All attacks"), "", n0(d["n"]["attack"]), bold(f"recall {b['recall']:.3f}"),
                 f"precision {b['precision']:.3f}, " + bold(f"F1 {b['f1']:.3f}")])
    v = d["sampling"].get("cic2018_sample_version", 1)
    days = d["sampling"].get("benign_days")
    note = (f"CSE-CIC-IDS2018 sample v{v}: up to {d['sampling']['per_attack_label']:,} flows per attack label and "
            f"{d['sampling']['benign']:,} benign flows" + (f" from {len(days)} capture days" if days else "")
            + "; labels mapped to CICIDS2017 families; features mapped to the 2017 schema. Nothing was retrained or "
              f"re-thresholded. IID CICIDS2017 test F1 for reference: {b['iid_cicids2017_f1_reference']:.3f}."
            if b.get("iid_cicids2017_f1_reference") is not None else "")
    return Table("v11_2018", "Frozen v1.1 Detector Scored Unchanged on CSE-CIC-IDS2018", ["2018 label", "Family", "n",
                 "Alert rate", "Correct family"], rows, notes=note, sources=[f"{src}:per_label", f"{src}:binary"],
                 docx={"widths": [2.2, 1.1, 0.9, 1.0, 1.6], "size": 8})


CROSS_METHODS = [OSR, "Aegis-OSR w/ AE novelty", "Aegis-OSR w/ IForest novelty", "kNN distance", "Autoencoder", XGB,
                 "XGB + Energy", DT, "Isolation Forest"]


def t_cross() -> Table:
    src = CROSS_V2 if exists(CROSS_V2) else CROSS_V1
    s = load(src)
    o = s["per_fold"]["cross_dataset"][X18]
    rows = [[k.replace("kNN distance", "k-NN distance"), f3(m(o[k]["zero_day_recall"])), f3(m(o[k]["auroc_unknown"])),
             f3(m(o[k]["known_recall"])), pnum(m(o[k]["fpr"]), 1)] for k in CROSS_METHODS]
    v = s["meta"].get("cic2018_sample_version", 1)
    return Table("cross", f"Open-Set Detection Trained on CICIDS2017, Tested on CSE-CIC-IDS2018 (α = 1%, Mean over {len(s['meta']['seeds'])} Seeds, Sample v{v})",
                 ["Method", "Zero-day recall", "AUROC_u", "Known recall", "Benign FPR (%)"], rows,
                 notes="Unknown family: Infiltration (never in CICIDS2017 training). No CSE-CIC-IDS2018 data was used for "
                       "training; recalibration results per capture day are in the next table.",
                 sources=[f"{src}:per_fold.cross_dataset"], docx={"widths": [2.2, 1.1, 0.9, 1.1, 1.1]})


def _anomaly_note() -> str:
    prof = load(DATASET).get("cic2018_v2", {}).get("benign_median_by_day", {})
    if not prof:
        return ""
    fb = {d_: v["Flow Bytes/s"] for d_, v in prof.items()}
    mid = sorted(fb.values())[len(fb) // 2] or 1
    odd = max(fb, key=lambda d_: fb[d_] / mid)
    others = sorted(v for d_, v in fb.items() if d_ != odd)
    return (f" On {odd} the flows labelled benign have a median of {fb[odd]:,.0f} bytes/s against "
            f"{others[len(others) // 2]:,.0f} on the other days, consistent with documented labelling problems in "
            "CSE-CIC-IDS2018; the day is reported as is.")


def t_cross_perday() -> Table:
    s = load(PERDAY)
    recs = load(PERDAY_REC)["records"]
    pf, ad = s["per_fold"]["cross_perday"], s.get("adaptation", {}).get("cross_perday", {})
    n_by_day: dict[str, dict] = {}
    for r in recs:
        n_by_day.setdefault(r["fold"], r["n_test"])
    rows = []
    for day in sorted(pf):
        base = pf[day][OSR]
        n = n_by_day[day]
        recall_key = "zero_day_recall" if n["unknown"] and not n["known"] else "known_recall"
        cells = [day, n0(n["benign"]), n0(n["known"] + n["unknown"]), pct(m(base["fpr"]), 1), f3(m(base[recall_key]))]
        for w in (500, 2000, 5000):
            a = ad.get(f"recal@{w}", {}).get("per_fold", {}).get(day, {}).get(OSR)
            cells.append(DASH if not a else f"{f3(m(a[recall_key]))} / {pct(m(a['fpr']), 2)}")
        rows.append(cells)
    return Table("cross_perday", "CSE-CIC-IDS2018 per Capture Day: Aegis-OSR before and after Same-Day Re-Calibration (α = 1%)",
                 ["Day", "Benign n", "Attack n", "FPR, none", "Recall, none", "recal 500", "recal 2,000", "recal 5,000"], rows,
                 notes="Trained once on CICIDS2017 per seed. For each 2018 day independently the warm-up window is that day's "
                       "earliest benign flows; evaluation uses only the rest of that day (no overlap). Recall is attack recall "
                       "on the day's attacks (Infiltration days: zero-day recall). Re-calibration cells: recall / benign FPR. "
                       "'—' = no benign flows left for that window size." + _anomaly_note(),
                 sources=[f"{PERDAY}:per_fold.cross_perday", f"{PERDAY}:adaptation.cross_perday", f"{PERDAY_REC}:records[*].n_test"],
                 docx={"widths": [0.9, 0.7, 0.7, 0.75, 0.75, 1.05, 1.05, 1.05], "size": 8})


def t_families() -> Table:
    d = load(FAMILIES)
    r = d["results"]
    names = sorted(r, key=lambda k: -r[k]["heldout_mean"]["zero_day_recall"])
    fams = ["Bot", "BruteForce", "DDoS", "DoS", "PortScan", "WebAttack"]
    rows = [[k, f3(r[k]["iid"]["f1"]), pnum(r[k]["iid"]["fpr"]), f3(r[k]["heldout_mean"]["zero_day_recall"])]
            + [f"{r[k]['heldout'][f]['zero_day_recall']:.2f}" for f in fams] for k in names]
    return Table("families", f"{len(r)} Classifier Families at a 1% Benign False-Alarm Budget: Seen vs. Withheld Families (Seed {d['seed']})",
                 ["Model", "IID F1", "IID FPR (%)", "Withheld: mean recall", "Bot", "Brute", "DDoS", "DoS", "Scan", "Web"], rows,
                 notes="Single seed, no confidence intervals. Thresholds set on validation benign flows for a 1% false-alarm "
                       "rate. 'Hist. gradient boosting' is scikit-learn's LightGBM-style implementation; the CNN and LSTM read "
                       "the 77 features as a 1-D sequence (no time axis).",
                 sources=[f"{FAMILIES}:results"], docx={"widths": [1.6, 0.55, 0.65, 0.85, 0.45, 0.5, 0.5, 0.45, 0.5, 0.45], "size": 8})


DEF_NAMES = {"block_source": "Block source", "rate_limit": "Rate limit", "isolate_host": "Isolate target",
             "monitor_only": "Monitor only", "increase_inspection": "Increase inspection"}


def _range_cells(suite: str) -> list[dict]:
    return load(RANGE)["suites"][suite]["cells"]


def _mean(xs: list[float | None]) -> float | None:
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def t_range_def() -> Table:
    d = load(RANGE)
    cells = _range_cells("defense")
    rows = []
    for key, label in DEF_NAMES.items():
        cs = [c["summary"] for c in cells if c["cell"]["defense"] == key]
        g = lambda k: _mean([m(s.get(k)) for s in cs])  # noqa: E731
        rows.append([label, pct(g("attack_success_after_defense"), 1),
                     f"{pct(g('availability_mean_during_attack'), 1)} / {pct(g('availability_min_during_attack'), 1)}",
                     pct(g("collateral_rate"), 1), one(g("recovery_time_s"))])
    flood = {}
    for sc in ("dos", "ddos"):
        cs = [c["summary"] for c in cells if c["cell"]["defense"] == "monitor_only" and c["cell"]["scenario"] == sc]
        if cs:
            flood[sc] = (m(cs[0]["availability_mean_during_attack"]), m(cs[0]["availability_min_during_attack"]))
    note = (f"Mean over {len({c['cell']['scenario'] for c in cells})} scenarios, {len(d['seeds'])} seeds each, automatic "
            "response. Means hide that most scenarios are cheap for the server; with monitoring only, availability during "
            "the attack averaged " + " and ".join(f"{pct(a, 0)} ({sc.upper()}; worst second {pct(b, 0)})" for sc, (a, b) in flood.items())
            + ". Availability is modelled (capacity / load), not measured on a real service; isolation is lifted 5 s after "
              "the attack stops, so its recovery time reflects scenario length. '—' = not applicable.")
    return Table("range_def", "Cyber Range: Defense Comparison", ["Defense", "Attack success after defense",
                 "Availability during attack (mean / min)", "Legitimate traffic blocked", "Recovery after defense (s)"], rows,
                 notes=note, sources=[f"{RANGE}:suites.defense"], docx={"widths": [1.3, 1.2, 1.5, 1.2, 1.2], "size": 8})


def one(v: float | None) -> str:
    return DASH if v is None else f"{v:.1f}"


SCEN_NAMES = {"zero_day": "Zero-day intrusion", "bot_beacon": "Beacon-style bot", "web_burst": "Web request burst",
              "host_discovery": "Slow host discovery"}


def t_range_det() -> Table:
    d = load(RANGE)
    cells = _range_cells("detector")
    n_seeds = len(d["seeds"])
    scen = sorted({c["cell"]["scenario"] for c in cells}, key=lambda x: (x != "zero_day", x))

    def summ(sc: str, det: str) -> dict:
        return next(c["summary"] for c in cells if c["cell"]["scenario"] == sc and c["cell"]["detector"] == det)

    interesting = [sc for sc in scen if any(m(summ(sc, det)["attack_flow_recall"]) is not None and
                                            (m(summ(sc, det)["attack_flow_recall"]) < 0.99 or m(summ(sc, det)["detected"]) < 1)
                                            for det in ("frozen", "gate"))]
    rows = []
    for sc in interesting:
        for det, label in (("frozen", "Frozen v1.1"), ("gate", "Zero-Day Gate")):
            s = summ(sc, det)
            det_n = round(m(s["detected"]) * n_seeds)
            lat = s["detection_latency_s"] if det_n else None
            rows.append([SCEN_NAMES.get(sc, sc) if det == "frozen" else "", label, f"{det_n} / {n_seeds}",
                         DASH if not lat or lat.get("mean") is None else ci(lat, one), f3(m(s["attack_flow_recall"])),
                         pct(m(s["fpr_flows"]), 2)])
    rest = [sc for sc in scen if sc not in interesting]
    lat_rest = [m(summ(sc, det)["detection_latency_s"]) for sc in rest for det in ("frozen", "gate")]
    fi = [m(summ(sc, det)["false_incidents"]) for sc in scen for det in ("frozen", "gate", "union")]
    note = (f"{n_seeds} seeds per cell; incident rule 3 alerts within 5 s. Shown: scenarios where a detector missed runs or "
            f"had attack-flow recall below 0.99. The other {len(rest)} scenarios were detected by both detectors in every run "
            f"(mean latency {min(lat_rest):.1f}–{max(lat_rest):.1f} s). Mean false incidents per run across all cells: "
            f"{_mean(fi):.2f}. The zero-day scenario redraws the same 47 never-seen flows, so its runs are not independent "
            "zero-days.") if rest else ""
    return Table("range_det", "Cyber Range: Which Detector Raises the Incident", ["Scenario", "Detector", "Runs detected",
                 "Detection latency (s)", "Attack-flow recall", "Benign flow FPR"], rows, notes=note,
                 sources=[f"{RANGE}:suites.detector"], docx={"widths": [1.6, 1.2, 1.0, 1.4, 1.2, 1.1], "size": 8})


def t_p11() -> Table:
    c = load(P11)["comparisons"]
    rows = []
    for key, label in (("ddos_block_source", "DDoS, BLOCK_SOURCE"), ("dos_rate_limit", "DoS, RATE_LIMIT")):
        r = c[key]
        rows.append([label, f"{r['no_defense_post_attack_blocked_rate_mean']:.2f}",
                     f"{r['recommendation_only_post_attack_blocked_rate_mean']:.2f}",
                     bold(f"{r['controlled_measured_effectiveness_mean']:.2f}"), f"{r['simulation_assumption']:.2f}",
                     f"{r['delta_measured_minus_simulation']:+.2f}"])
    reps = load(P11)["repetitions"]
    return Table("p11", f"Mitigation Measured on the Controlled Test Plane ({reps} Repetitions, Frozen-ML Detection)",
                 ["Scenario", "No defence", "Recommendation only", "Approved response", "Storyboard prior", "Δ"], rows,
                 notes="Measured effectiveness on the CONTROLLED test adapter (no live firewall). Δ = measured − assumed "
                       "storyboard prior.", sources=[f"{P11}:comparisons", f"{P11}:repetitions"],
                 docx={"widths": [1.6, 0.9, 1.1, 1.1, 1.0, 0.6]})


def t_perf() -> Table:
    e = load(ENVELOPE)["metrics"]["envelope"]
    g = load(GATE)["evaluation"]["gate"]
    db = load(DBPERF)
    rd = load(RANGE)
    walls = [m(c["summary"]["wall_seconds"]) for s in rd["suites"].values() for c in s["cells"]]
    runtime = sum(s.get("runtime_seconds", 0) for s in rd["suites"].values())
    runs = sum(len(s["cells"]) for s in rd["suites"].values()) * len(rd["seeds"])
    p = e["prediction"]
    outcomes = db["metrics"]["approve_outcomes"]
    rows = [
        ["Single-flow prediction, no explanation", f"{p['flows_per_sec']:.0f} flows/s; p50 {p['p50_ms']:.1f} ms, p95 {p['p95_ms']:.1f} ms; "
                                                   f"{100 * p['error_rate']:.0f}% errors"],
        ["Pipeline batch, 100 / 500 flows", f"{e['batch']['100']['flows_per_sec']:.0f} / {e['batch']['500']['flows_per_sec']:.0f} flows/s (wall clock)"],
        ["Vectorised DT/RF inference, 1,000 / 5,000 flows", f"{e['batch']['1000']['flows_per_sec']:,.0f} / {e['batch']['5000']['flows_per_sec']:,.0f} flows/s"],
        ["Zero-Day Gate, batch scoring", f"{g['latency_ms_per_flow_batch']:.3f} ms per flow"],
        ["Cyber-range run", f"{min(walls):.2f}–{max(walls):.2f} s per run; {runs:,} runs in {runtime / 60:.1f} min"],
        ["SHAP TreeExplainer on frozen DT vs. prediction", f"p50 ratio {e['shap_ratio']:.2f}"],
        ["Concurrent approval of one action", f"{outcomes.get('ok', 0)} of {db['configuration']['concurrent_approves']} "
                                              "concurrent approvers succeeds"],
    ]
    return Table("perf", "Measured Operating Envelope (Single Windows Desktop, 20 Threads)", ["Workload", "Measured value"], rows,
                 notes="Prototype measurements on one workstation; not a capacity claim.",
                 sources=[f"{ENVELOPE}:metrics.envelope", f"{GATE}:evaluation.gate.latency_ms_per_flow_batch", f"{DBPERF}:metrics",
                          f"{RANGE}:suites[*].cells[*].summary.wall_seconds"], docx={"widths": [2.8, 3.4]})


def t_gate() -> Table:
    ev = load(GATE)["evaluation"]
    h = ev["head_to_head"]
    un = sum(u["n"] for u in ev["natural_unknowns"])
    rows = [[(bold("Gate, α = 1% (deployed)") if o["alpha"] == 0.01 else f"Gate, α = {100 * o['alpha']:g}%"),
             f"{100 * o['benign_fpr']:.3f}", f3(o["known_attack_recall"]),
             f"{round(o['natural_unknown_alert_rate'] * un)} / {un} ({100 * o['natural_unknown_alert_rate']:.1f}%)"]
            for o in h["gate_operating_points"]]
    fz = h["frozen_v11"]
    rows.append([f"Frozen v1.1 detector (τ = {fz['threshold']:g})", f"{100 * fz['benign_fpr']:.3f}", f3(fz["known_attack_recall"]),
                 f"{round(fz['natural_unknown_attack_rate'] * un)} / {un}"])
    pf = h["per_family_recall"]
    note = ("Flows in both models' test splits and in neither model's training or validation data "
            f"({h['n']['benign']:,} benign, {h['n']['known_attacks']:,} known attacks, {un} never-seen). Per-family recall at "
            "α = 1%, gate vs. v1.1 (n): " + "; ".join(f"{f} {r['gate']:.3f} vs. {r['frozen_v11']:.3f} (n = {r['n']:,})"
                                                      for f, r in pf.items())
            + ". Bot and WebAttack have fewer than 100 eligible flows; treat their rates as indicative.")
    return Table("gate", "Deployed Zero-Day Gate vs. the Frozen v1.1 Detector on Flows Neither Model Trained On",
                 ["Operating point", "Benign FPR (%)", "Known-attack recall", "Never-seen attacks flagged"], rows, notes=note,
                 sources=[f"{GATE}:evaluation.head_to_head", f"{GATE}:evaluation.natural_unknowns"], docx={"widths": [2.2, 1.2, 1.4, 1.8]})


XAI = "models/trained_models/xai_stability_report.json"


def t_xai() -> Table:
    x = load(XAI)
    rows = []
    for f, v in x["per_family"].items():
        rob = v["robustness_jaccard_top5"]["mean"]
        rows.append([("Benign" if f == "BENIGN" else f), f"{v['consistency_jaccard_top5']['mean']:.2f}",
                     bold(f"{rob:.2f}") if rob < 0.9 else f"{rob:.2f}", f"{v['robustness_spearman_top10']['mean']:.2f}",
                     f"{v['shap_lime_jaccard_top5']['mean']:.2f}"])
    return Table("xai", f"Explanation Stability of the Frozen Detector ({x['per_family_flows']} Flows per Class, Seed {x['seed']})",
                 ["Class", "Consistency within family", "Robustness to ±1% noise", "Rank stability (Spearman)", "SHAP–LIME agreement"],
                 rows, notes="Consistency, robustness and agreement are mean Jaccard overlaps of top-five SHAP features "
                             "(1 = identical); bold marks robustness below 0.90. Rank stability is the Spearman correlation of "
                             "the top-ten attribution magnitudes with and without noise. Flows come from the leakage-free "
                             "replay pool (neither model trained on them).",
                 sources=[f"{XAI}:per_family"], docx={"widths": [1.2, 1.4, 1.4, 1.4, 1.3]})


BUILDERS: dict[str, Callable[[], Table]] = {  # in paper order
    "data": t_data, "cand": t_cand, "v11": t_v11, "loafo": t_loafo, "significance": t_significance, "family": t_family,
    "temporal": t_temporal, "adapt": t_adapt, "gate": t_gate, "v11_2018": t_v11_2018, "cross": t_cross,
    "cross_perday": t_cross_perday, "families": t_families, "range_def": t_range_def, "range_det": t_range_det,
    "xai": t_xai, "p11": t_p11, "perf": t_perf,
}


def build_tables() -> dict[str, Table]:
    _cache.clear()
    return {k: fn() for k, fn in BUILDERS.items()}


# ------------------------------------------------------------------------------- prose facts
@dataclass
class Fact:
    value: Any
    display: str
    source: str


def facts() -> dict[str, Fact]:
    """Every number quoted in the paper's prose, computed from artifacts (with its source)."""
    F: dict[str, Fact] = {}

    def put(key: str, value: Any, display: str, source: str) -> None:
        assert key not in F, key
        F[key] = Fact(value, display, source)

    # --- corpus and frozen detector
    d = load(DATASET)["cic2017"]
    put("corpus_rows", d["rows"], n0(d["rows"]), f"{DATASET}:cic2017.rows")
    put("n_features", d["n_features"], str(d["n_features"]), f"{DATASET}:cic2017.n_features")
    for fam in ("Infiltration", "Heartbleed"):
        put(f"n_{fam}", d["by_family"][fam], str(d["by_family"][fam]), f"{DATASET}:cic2017.by_family.{fam}")
    kept = d["rows"] - d["by_family"]["Infiltration"] - d["by_family"]["Heartbleed"]
    put("v11_rows", kept, n0(kept), f"{DATASET}:cic2017 minus Infiltration/Heartbleed")
    tr = load(TRAINING)
    bt, bv = tr["binary"]["test"], tr["binary"]["validation"]
    n_test = sum(map(sum, bt["confusion_matrix"]))
    n_val = sum(map(sum, bv[tr["binary"]["best"]]["confusion_matrix"]))
    put("v11_test_rows", n_test, n0(n_test), f"{TRAINING}:binary.test.confusion_matrix")
    put("v11_val_rows", n_val, n0(n_val), f"{TRAINING}:binary.validation.<best>.confusion_matrix")
    put("v11_train_rows", kept - n_test - n_val, n0(kept - n_test - n_val), "v11_rows − test − validation")
    put("feature_overlap", len(tr["feature_overlap"]), str(len(tr["feature_overlap"])), f"{TRAINING}:feature_overlap")
    put("v11_f1", bt["f1"], f3(bt["f1"]), f"{TRAINING}:binary.test.f1")
    dt, xg = bv["decision_tree"], bv["xgboost"]
    put("dt_xgb_fpr_ratio", dt["fpr"] / xg["fpr"], f"{dt['fpr'] / xg['fpr']:.0f}", f"{TRAINING}:binary.validation.*.fpr")
    put("dt_xgb_recall_gap_pp", 100 * (dt["recall"] - xg["recall"]), f"{100 * (dt['recall'] - xg['recall']):.1f}",
        f"{TRAINING}:binary.validation.*.recall")
    th = load("models/trained_models/threshold_operating_point.json")
    put("thr_val_rows", th["val_rows"], n0(th["val_rows"]), "models/trained_models/threshold_operating_point.json:val_rows")
    c = load("models/trained_models/calibration_hpo_experiment.json")
    put("calib_rows", c["sample_train_rows"], n0(c["sample_train_rows"]), "models/trained_models/calibration_hpo_experiment.json:sample_train_rows")
    for k, path in (("calib_recall_before", "baseline"), ("calib_recall_after", "isotonic_calibrated")):
        v = c[path]["metrics"]["recall"]
        put(k, v, f3(v), f"models/trained_models/calibration_hpo_experiment.json:{path}.metrics.recall")
    for k, path in (("calib_brier_before", "baseline"), ("calib_brier_after", "isotonic_calibrated")):
        v = c[path]["metrics"].get("brier_score", c[path].get("brier_score"))
        if v is not None:
            put(k, v, f4(v), f"models/trained_models/calibration_hpo_experiment.json:{path}.brier_score")
    mv = tr["multiclass"]["validation"]
    for k in ("random_forest", "xgboost"):
        put(f"mc_score_{k}", mv[k]["selection_score"], f5(mv[k]["selection_score"]), f"{TRAINING}:multiclass.validation.{k}.selection_score")
    cm = tr["multiclass"]["test"]["confusion_matrix"]
    classes = tr["multiclass"]["classes"]
    total = sum(map(sum, cm))
    wrong = total - sum(cm[i][i] for i in range(len(cm)))
    worst = max(((cm[i][j], classes[i], classes[j]) for i in range(len(cm)) for j in range(len(cm)) if i != j))
    put("mc_test_attacks", total, n0(total), f"{TRAINING}:multiclass.test.confusion_matrix")
    put("mc_misattributed", wrong, str(wrong), f"{TRAINING}:multiclass.test.confusion_matrix")
    put("mc_worst_cell", worst, f"{worst[0]} {worst[1]} flows labelled {worst[2]}", f"{TRAINING}:multiclass.test.confusion_matrix")

    # --- LOAFO
    s = load(LOAFO)
    o, pf, at = s["overall"]["loafo"], s["per_fold"]["loafo"], s["attribution"]["loafo"]
    seeds = s["meta"]["seeds"]
    put("loafo_seeds", len(seeds), str(len(seeds)), f"{LOAFO}:meta.seeds")
    put("loafo_runs", s["meta"]["n_records"], str(s["meta"]["n_records"]), f"{LOAFO}:meta.n_records")
    zo = o[OSR]["zero_day_recall"]
    put("osr_zdr", zo["mean"], pct(zo["mean"]), f"{LOAFO}:overall.loafo.{OSR}.zero_day_recall.mean")
    put("osr_zdr_ci", (zo["ci_low"], zo["ci_high"]), f"{100 * zo['ci_low']:.1f}–{pct(zo['ci_high'])}", f"{LOAFO}:overall.loafo.{OSR}.zero_day_recall")
    fo = o[OSR]["fpr"]
    put("osr_fpr", fo["mean"], pct(fo["mean"], 2), f"{LOAFO}:overall.loafo.{OSR}.fpr.mean")
    put("osr_fpr_ci", (fo["ci_low"], fo["ci_high"]), f"{100 * fo['ci_low']:.2f}–{pct(fo['ci_high'], 2)}", f"{LOAFO}:overall.loafo.{OSR}.fpr")
    put("xgb_zdr", m(o[XGB]["zero_day_recall"]), pct(m(o[XGB]["zero_day_recall"])), f"{LOAFO}:overall.loafo.{XGB}.zero_day_recall.mean")
    put("dt_zdr", m(o[DT]["zero_day_recall"]), pct(m(o[DT]["zero_day_recall"])), f"{LOAFO}:overall.loafo.{DT}.zero_day_recall.mean")
    put("osr_minus_xgb_pp", 100 * (zo["mean"] - m(o[XGB]["zero_day_recall"])),
        f"{100 * (zo['mean'] - m(o[XGB]['zero_day_recall'])):.1f}", f"{LOAFO}:overall.loafo")
    put("osr_minus_dt_pp", 100 * (zo["mean"] - m(o[DT]["zero_day_recall"])),
        f"{100 * (zo['mean'] - m(o[DT]['zero_day_recall'])):.1f}", f"{LOAFO}:overall.loafo")
    put("osr_known", m(o[OSR]["known_recall"]), f3(m(o[OSR]["known_recall"])), f"{LOAFO}:overall.loafo.{OSR}.known_recall.mean")
    calibrated = [k for k in o if k != DT]
    fprs = [m(o[k]["fpr"]) for k in calibrated]
    put("fpr_range_calibrated", (min(fprs), max(fprs)), f"{pct(min(fprs), 2)} and {pct(max(fprs), 2)}", f"{LOAFO}:overall.loafo.*.fpr (excl. DT)")
    put("if_zdr", m(o["Isolation Forest"]["zero_day_recall"]), pct(m(o["Isolation Forest"]["zero_day_recall"])), f"{LOAFO}:overall.loafo.Isolation Forest")
    put("if_known", m(o["Isolation Forest"]["known_recall"]), pct(m(o["Isolation Forest"]["known_recall"])), f"{LOAFO}:overall.loafo.Isolation Forest")
    for key, name in (("abl_omni_pp", "Aegis-OSR w/ omnibus fusion"), ("abl_max_pp", "Aegis-OSR w/ max fusion"),
                      ("abl_ae_pp", "Aegis-OSR w/ AE novelty"), ("abl_if_pp", "Aegis-OSR w/ IForest novelty")):
        dlt = 100 * (zo["mean"] - m(o[name]["zero_day_recall"]))
        put(key, dlt, f"{dlt:.1f}", f"{LOAFO}:overall.loafo.{name}.zero_day_recall")
    put("ae_auroc", m(o["Aegis-OSR w/ AE novelty"]["auroc_unknown"]), f3(m(o["Aegis-OSR w/ AE novelty"]["auroc_unknown"])), f"{LOAFO}:overall.loafo")
    put("osr_auroc", m(o[OSR]["auroc_unknown"]), f3(m(o[OSR]["auroc_unknown"])), f"{LOAFO}:overall.loafo")
    fam_r = {f: m(pf[f][OSR]["zero_day_recall"]) for f in pf}
    for f, v in fam_r.items():
        put(f"fam_{f}", v, pct(v), f"{LOAFO}:per_fold.loafo.{f}.{OSR}.zero_day_recall.mean")
    hi = [fam_r[f] for f in ("DoS", "DDoS", "WebAttack")]
    put("fam_flood_web_range", (min(hi), max(hi)), f"{100 * min(hi):.1f}–{pct(max(hi))}", f"{LOAFO}:per_fold.loafo")
    put("fam_BruteForce_xgb", m(pf["BruteForce"][XGB]["zero_day_recall"]), pct(m(pf["BruteForce"][XGB]["zero_day_recall"])), f"{LOAFO}:per_fold.loafo.BruteForce")
    put("fam_BruteForce_ae", m(pf["BruteForce"]["Aegis-OSR w/ AE novelty"]["zero_day_recall"]),
        pct(m(pf["BruteForce"]["Aegis-OSR w/ AE novelty"]["zero_day_recall"])), f"{LOAFO}:per_fold.loafo.BruteForce")
    mis = {f: m(at[f]["unknown_misattributed_to_known"]) for f in at}
    worst_f = max(mis, key=mis.get)
    put("mis_max", mis[worst_f], pct(mis[worst_f]), f"{LOAFO}:attribution.loafo.*.unknown_misattributed_to_known")
    put("mis_max_fold", worst_f, worst_f, f"{LOAFO}:attribution.loafo")
    small = sum(1 for v in mis.values() if v <= 0.002)
    put("mis_small_folds", small, f"{small} of {len(mis)}", f"{LOAFO}:attribution.loafo (≤ 0.2%)")
    accs = [m(at[f]["known_family_accuracy"]) for f in at]
    put("known_acc_min", min(accs), pct(min(accs), 0), f"{LOAFO}:attribution.loafo.*.known_family_accuracy")
    for a, tag in (("0.001", "a001"), ("0.05", "a05")):
        for k, name in ((OSR, "osr"), (XGB, "xgb")):
            v = m(o[k][f"zero_day_recall@{a}"])
            put(f"{name}_zdr_{tag}", v, pct(v), f"{LOAFO}:overall.loafo.{k}.zero_day_recall@{a}")
        v = m(o[OSR][f"fpr@{a}"])
        put(f"osr_fpr_{tag}", v, pct(v, 2), f"{LOAFO}:overall.loafo.{OSR}.fpr@{a}")
    recs = load("research_artifacts/openset_loafo_records.json")["records"]
    unk = [r["n_test"]["unknown"] for r in recs]
    put("loafo_unknown_min", min(unk), n0(min(unk)), "research_artifacts/openset_loafo_records.json:records[*].n_test.unknown")
    put("loafo_unknown_max", max(unk), n0(max(unk)), "research_artifacts/openset_loafo_records.json:records[*].n_test.unknown")
    put("loafo_benign_test", recs[0]["n_test"]["benign"], n0(recs[0]["n_test"]["benign"]), "research_artifacts/openset_loafo_records.json:records[0].n_test.benign")
    fit = sum(r["fit_seconds"] for r in recs) / len(recs)
    sc = sum(r["score_ms_per_1k_flows"] for r in recs) / len(recs)
    put("loafo_fit_s", fit, f"{fit:.0f}", "research_artifacts/openset_loafo_records.json:records[*].fit_seconds")
    put("loafo_score_ms", sc, f"{sc:.0f}", "research_artifacts/openset_loafo_records.json:records[*].score_ms_per_1k_flows")

    # --- temporal
    t = load(TEMPORAL)
    tp, tf, ta = t["per_fold"]["temporal"], t["per_family"]["temporal"], t["adaptation"]["temporal"]
    for fold, tag in ((FRI, "fri"), (THU, "thu")):
        for k, name in ((OSR, "osr"), (XGB, "xgb"), ("kNN distance", "knn")):
            put(f"t_{tag}_{name}_fpr", m(tp[fold][k]["fpr"]), pct(m(tp[fold][k]["fpr"]), 2), f"{TEMPORAL}:per_fold.temporal.{fold}.{k}.fpr")
            put(f"t_{tag}_{name}_zdr", m(tp[fold][k]["zero_day_recall"]), f3(m(tp[fold][k]["zero_day_recall"])),
                f"{TEMPORAL}:per_fold.temporal.{fold}.{k}.zero_day_recall")
    put("t_fri_osr_fpr_ratio", m(tp[FRI][OSR]["fpr"]) / 0.01, f"{m(tp[FRI][OSR]['fpr']) / 0.01:.0f}", f"{TEMPORAL}:per_fold.temporal (÷ α)")
    for f in ("DDoS", "PortScan", "Bot", "WebAttack", "Infiltration"):
        if f in tf:
            put(f"t_fam_{f}", m(tf[f][OSR]), pct(m(tf[f][OSR])), f"{TEMPORAL}:per_family.temporal.{f}.{OSR}")
            put(f"t_fam_{f}_xgb", m(tf[f][XGB]), pct(m(tf[f][XGB])), f"{TEMPORAL}:per_family.temporal.{f}.{XGB}")
    for key in ("recal@500", "recal@2000", "recal@5000", "recal+ref@5000", "oracle@2000"):
        for fold, tag in ((FRI, "fri"), (THU, "thu")):
            cell = ta.get(key, {}).get("per_fold", {}).get(fold)
            if not cell:
                continue
            nm = key.replace("@", "_").replace("+", "")
            for k, name in ((OSR, "osr"), (XGB, "xgb")):
                put(f"a_{tag}_{nm}_{name}_fpr", m(cell[k]["fpr"]), pct(m(cell[k]["fpr"]), 2), f"{TEMPORAL}:adaptation.temporal.{key}.per_fold.{fold}.{k}.fpr")
                put(f"a_{tag}_{nm}_{name}_zdr", m(cell[k]["zero_day_recall"]), f3(m(cell[k]["zero_day_recall"])),
                    f"{TEMPORAL}:adaptation.temporal.{key}.per_fold.{fold}.{k}.zero_day_recall")
    oc = ta["oracle@2000"]["per_fold"][FRI][OSR]["fpr"]
    put("a_fri_oracle_fpr_ci", (oc["ci_low"], oc["ci_high"]), f"[{100 * oc['ci_low']:.2f}, {100 * oc['ci_high']:.2f}]",
        f"{TEMPORAL}:adaptation.temporal.oracle@2000.per_fold.{FRI}.{OSR}.fpr")

    # --- gate
    g = load(GATE)
    ev = g["evaluation"]
    un = ev["natural_unknowns"]
    put("unseen_total", sum(u["n"] for u in un), str(sum(u["n"] for u in un)), f"{GATE}:evaluation.natural_unknowns[*].n")
    gc = round(sum(u["gate_alert_rate"] * u["n"] for u in un))
    put("unseen_gate", gc, str(gc), f"{GATE}:evaluation.natural_unknowns[*].gate_alert_rate")
    fc = round(sum(u["frozen_v11_attack_rate"] * u["n"] for u in un))
    put("unseen_frozen", fc, str(fc), f"{GATE}:evaluation.natural_unknowns[*].frozen_v11_attack_rate")
    put("gate_train_rows", g["training"]["n_train"], n0(g["training"]["n_train"]), f"{GATE}:training.n_train")
    put("gate_cal_rows", g["training"]["calibration_split"][0], n0(g["training"]["calibration_split"][0]), f"{GATE}:training.calibration_split")
    put("gate_latency_ms", ev["gate"]["latency_ms_per_flow_batch"], f"{ev['gate']['latency_ms_per_flow_batch']:.2f}", f"{GATE}:evaluation.gate.latency_ms_per_flow_batch")
    par = ev["gate"]["served_vs_research_parity"]
    put("gate_parity", par, f"{100 * par:.3f}%", f"{GATE}:evaluation.gate.served_vs_research_parity")
    pool = load(f"{RA}/replay/replay_pool_manifest.json")
    put("pool_rows", pool["rows"], n0(pool["rows"]), f"{RA}/replay/replay_pool_manifest.json:rows")
    sp = pool["sampled_per_family"]
    put("pool_benign", sp["BENIGN"], n0(sp["BENIGN"]), f"{RA}/replay/replay_pool_manifest.json:sampled_per_family.BENIGN")
    leak = pool["gate_test_rows_in_frozen_train_or_val"] / pool["gate_test_rows"]
    put("legacy_overlap", leak, pct(leak, 0), f"{RA}/replay/replay_pool_manifest.json:gate_test_rows_in_frozen_train_or_val ÷ gate_test_rows")
    for fam in ("Bot", "WebAttack"):
        put(f"pool_n_{fam}", sp[fam], str(sp[fam]), f"{RA}/replay/replay_pool_manifest.json:sampled_per_family.{fam}")
    att = {k: v for k, v in sp.items() if k not in ("BENIGN", "Infiltration", "Heartbleed")}
    put("pool_attack_range", (min(att.values()), max(att.values())), f"{min(att.values())}–{max(att.values())}",
        f"{RA}/replay/replay_pool_manifest.json:sampled_per_family")

    # --- explainability, risk
    gs = load("models/trained_models/global_shap_summary.json")["global"]["binary_top"]
    put("global_top", [(x["feature"], x["importance"]) for x in gs[:5]],
        ", ".join(f"{x['feature']} ({x['importance']:.2f})" for x in gs[:5]), "models/trained_models/global_shap_summary.json:global.binary_top")
    rs = load("models/trained_models/risk_weight_sensitivity.json")["results"]
    by_case: dict[str, list] = {}
    for cfg in rs.values():
        for c in cfg:
            by_case.setdefault(c["case"], []).append(c)
    # spread of each case's score across the alternative weightings (and the default engine)
    spread = max(max([c["risk_score"] for c in v] + [v[0]["default_engine"]]) -
                 min([c["risk_score"] for c in v] + [v[0]["default_engine"]]) for v in by_case.values())
    put("risk_max_move", spread, f"{spread:.1f}", "models/trained_models/risk_weight_sensitivity.json:results (max per-case spread)")
    band_changes = sum(1 for v in by_case.values() if len({c["severity"] for c in v}) > 1)
    put("risk_band_changes", band_changes, str(band_changes), "models/trained_models/risk_weight_sensitivity.json:results (cases with >1 severity)")

    # --- model families
    fr = load(FAMILIES)["results"]
    iid = [v["iid"]["f1"] for v in fr.values()]
    put("fam_iid_f1_range", (min(iid), max(iid)), f"{min(iid):.3f} to {max(iid):.3f}", f"{FAMILIES}:results.*.iid.f1")
    best = max(fr, key=lambda k: fr[k]["heldout_mean"]["zero_day_recall"])
    put("fam_best_name", best, best, f"{FAMILIES}:results")
    put("fam_best_heldout", fr[best]["heldout_mean"]["zero_day_recall"], pct(fr[best]["heldout_mean"]["zero_day_recall"]), f"{FAMILIES}:results.{best}.heldout_mean")
    trees = [k for k in fr if any(w in k.lower() for w in ("tree", "forest", "boost"))]
    nns = [k for k in fr if any(w in k.lower() for w in ("cnn", "lstm", "mlp"))]
    put("fam_tree_mean", _mean([fr[k]["heldout_mean"]["zero_day_recall"] for k in trees]),
        pct(_mean([fr[k]["heldout_mean"]["zero_day_recall"] for k in trees])), f"{FAMILIES}:results[{', '.join(trees)}]")
    put("fam_nn_mean", _mean([fr[k]["heldout_mean"]["zero_day_recall"] for k in nns]),
        pct(_mean([fr[k]["heldout_mean"]["zero_day_recall"] for k in nns])), f"{FAMILIES}:results[{', '.join(nns)}]")
    put("fam_n_trees", len(trees), str(len(trees)), f"{FAMILIES}:results")
    put("fam_n_nns", len(nns), str(len(nns)), f"{FAMILIES}:results")
    above = [k for k in fr if fr[k]["iid"]["f1"] > 0.98]
    put("fam_above_098", len(above), str(len(above)), f"{FAMILIES}:results.*.iid.f1 > 0.98")
    botmax = max(fr[k]["heldout"]["Bot"]["zero_day_recall"] for k in fr)
    put("fam_bot_max", botmax, pct(botmax, 2), f"{FAMILIES}:results.*.heldout.Bot")

    # --- cyber range
    rd = load(RANGE)
    runs = sum(len(su["cells"]) for su in rd["suites"].values()) * len(rd["seeds"])
    put("range_runs", runs, n0(runs), f"{RANGE}:suites (cells × seeds)")
    put("range_seeds", len(rd["seeds"]), str(len(rd["seeds"])), f"{RANGE}:seeds")
    put("range_scenarios", len(load(RANGE)["scenarios"]), str(len(load(RANGE)["scenarios"])), f"{RANGE}:scenarios")
    runtime = sum(su.get("runtime_seconds", 0) for su in rd["suites"].values())
    put("range_runtime_min", runtime / 60, f"{runtime / 60:.1f}", f"{RANGE}:suites[*].runtime_seconds")
    det = {(c["cell"]["scenario"], c["cell"]["detector"]): c["summary"] for c in rd["suites"]["detector"]["cells"]}
    z_g, z_f = det[("zero_day", "gate")], det[("zero_day", "frozen")]
    put("rz_gate_latency", m(z_g["detection_latency_s"]), one(m(z_g["detection_latency_s"])), f"{RANGE}:suites.detector[zero_day,gate].detection_latency_s")
    put("rz_gate_latency_ci", z_g["detection_latency_s"], f"[{z_g['detection_latency_s']['ci_low']:.1f}, {z_g['detection_latency_s']['ci_high']:.1f}]",
        f"{RANGE}:suites.detector[zero_day,gate].detection_latency_s")
    put("rz_gate_recall", m(z_g["attack_flow_recall"]), f3(m(z_g["attack_flow_recall"])), f"{RANGE}:suites.detector[zero_day,gate].attack_flow_recall")
    put("rz_frozen_recall", m(z_f["attack_flow_recall"]), f3(m(z_f["attack_flow_recall"])), f"{RANGE}:suites.detector[zero_day,frozen].attack_flow_recall")
    put("rz_frozen_detected", round(m(z_f["detected"]) * len(rd["seeds"])), str(round(m(z_f["detected"]) * len(rd["seeds"]))),
        f"{RANGE}:suites.detector[zero_day,frozen].detected")
    put("rz_gate_detected", round(m(z_g["detected"]) * len(rd["seeds"])), str(round(m(z_g["detected"]) * len(rd["seeds"]))),
        f"{RANGE}:suites.detector[zero_day,gate].detected")
    b_g, b_f = det[("bot_beacon", "gate")], det[("bot_beacon", "frozen")]
    for k, s_ in (("rb_gate", b_g), ("rb_frozen", b_f)):
        put(f"{k}_latency", m(s_["detection_latency_s"]), one(m(s_["detection_latency_s"])), f"{RANGE}:suites.detector[bot_beacon].detection_latency_s")
        put(f"{k}_recall", m(s_["attack_flow_recall"]), f3(m(s_["attack_flow_recall"])), f"{RANGE}:suites.detector[bot_beacon].attack_flow_recall")
    gate_fpr = _mean([m(det[(sc, "gate")]["fpr_flows"]) for sc, d_ in det if d_ == "gate"])
    frz_fpr = _mean([m(det[(sc, "frozen")]["fpr_flows"]) for sc, d_ in det if d_ == "frozen"])
    put("r_gate_fpr", gate_fpr, pct(gate_fpr, 2), f"{RANGE}:suites.detector[*,gate].fpr_flows (mean)")
    put("r_frozen_fpr", frz_fpr, pct(frz_fpr, 2), f"{RANGE}:suites.detector[*,frozen].fpr_flows (mean)")
    put("r_fpr_ratio", gate_fpr / frz_fpr, f"{gate_fpr / frz_fpr:.0f}", f"{RANGE}:suites.detector fpr_flows gate ÷ frozen")
    in_dist = [m(det[(sc, dd)]["detection_latency_s"]) for sc, dd in det if sc != "zero_day" and m(det[(sc, dd)]["detected"]) == 1]
    put("r_known_latency_max", max(in_dist), one(max(in_dist)), f"{RANGE}:suites.detector[known scenarios].detection_latency_s")
    thr = {}
    for cell in rd["suites"]["threshold"]["cells"]:
        thr.setdefault(cell["cell"]["alert_threshold"], {})[cell["cell"]["scenario"]] = cell["summary"]
    fi1 = [m(v["false_incidents"]) for v in thr[1].values()]
    put("r_fi_k1", (min(fi1), max(fi1)), f"{min(fi1):.0f}–{max(fi1):.0f}", f"{RANGE}:suites.threshold[k=1].false_incidents")
    fi2 = _mean([m(v["false_incidents"]) for v in thr[2].values()]) if 2 in thr else None
    put("r_fi_k2", fi2, one(fi2), f"{RANGE}:suites.threshold[k=2].false_incidents (mean)")
    fi3 = max(m(v["false_incidents"]) for k_ in thr if k_ >= 3 for v in thr[k_].values())
    put("r_fi_k3plus_max", fi3, one(fi3), f"{RANGE}:suites.threshold[k≥3].false_incidents (max)")
    kmax = max(thr)
    for sc, tag in (("bot_beacon", "beacon"), ("host_discovery", "hostdisc"), ("dos", "dos")):
        if sc in thr[1] and sc in thr[kmax]:
            put(f"r_lat_{tag}_k1", m(thr[1][sc]["detection_latency_s"]), one(m(thr[1][sc]["detection_latency_s"])), f"{RANGE}:suites.threshold[k=1,{sc}]")
            put(f"r_lat_{tag}_kmax", m(thr[kmax][sc]["detection_latency_s"]), one(m(thr[kmax][sc]["detection_latency_s"])), f"{RANGE}:suites.threshold[k={kmax},{sc}]")
    put("r_kmax", kmax, str(kmax), f"{RANGE}:suites.threshold")
    defense = [c for c in rd["suites"]["defense"]["cells"]]
    iso = [c["summary"] for c in defense if c["cell"]["defense"] == "isolate_host"]
    put("r_iso_collateral", _mean([m(s_["collateral_rate"]) for s_ in iso]), pct(_mean([m(s_["collateral_rate"]) for s_ in iso])), f"{RANGE}:suites.defense[isolate_host].collateral_rate")
    put("r_iso_recovery", _mean([m(s_["recovery_time_s"]) for s_ in iso]), f"{_mean([m(s_['recovery_time_s']) for s_ in iso]):.0f}", f"{RANGE}:suites.defense[isolate_host].recovery_time_s")
    rl = [c["summary"] for c in defense if c["cell"]["defense"] == "rate_limit"]
    put("r_rl_success", _mean([m(s_["attack_success_after_defense"]) for s_ in rl]), pct(_mean([m(s_["attack_success_after_defense"]) for s_ in rl]), 0),
        f"{RANGE}:suites.defense[rate_limit].attack_success_after_defense")
    att_cells = {c["cell"]["attackers"]: c["summary"] for c in rd["suites"]["attackers"]["cells"]}
    for n in (2, 8):
        if n in att_cells:
            v = m(att_cells[n]["availability_min_during_attack"])
            put(f"r_ddos_{n}src_min_avail", v, pct(v), f"{RANGE}:suites.attackers[{n}].availability_min_during_attack")
    dl = {(c["cell"]["scenario"], c["cell"]["approval_delay_s"]): c["summary"] for c in rd["suites"]["delay"]["cells"]}
    for (sc, dly), s_ in dl.items():
        put(f"r_avail_{sc}_{dly}", m(s_["availability_mean_during_attack"]), pct(m(s_["availability_mean_during_attack"])),
            f"{RANGE}:suites.delay[{sc},{dly}].availability_mean_during_attack")
    walls = [m(c["summary"]["wall_seconds"]) for su in rd["suites"].values() for c in su["cells"]]
    flows = [m(c["summary"]["flows_total"]) for su in rd["suites"].values() for c in su["cells"]]
    put("r_wall_range", (min(walls), max(walls)), f"{min(walls):.2f}–{max(walls):.2f}", f"{RANGE}:suites[*].cells[*].wall_seconds")
    put("r_flows_range", (min(flows), max(flows)), f"{min(flows):,.0f}–{max(flows):,.0f}", f"{RANGE}:suites[*].cells[*].flows_total")

    # --- XAI, P11, performance, security validation
    x = load(XAI)
    put("xai_shap_lime", x["overall"]["shap_lime_jaccard_top5"]["mean"], f"{x['overall']['shap_lime_jaccard_top5']['mean']:.2f}", f"{XAI}:overall.shap_lime_jaccard_top5")
    p11 = load(P11)["comparisons"]
    put("p11_dos_eff", p11["dos_rate_limit"]["controlled_measured_effectiveness_mean"], pct(p11["dos_rate_limit"]["controlled_measured_effectiveness_mean"], 0),
        f"{P11}:comparisons.dos_rate_limit")
    put("p11_ddos_prior", p11["ddos_block_source"]["simulation_assumption"], f"{p11['ddos_block_source']['simulation_assumption']:.2f}",
        f"{P11}:comparisons.ddos_block_source.simulation_assumption")
    env = load(ENVELOPE)["metrics"]["envelope"]
    put("perf_vec_range", (env["batch"]["1000"]["flows_per_sec"], env["batch"]["5000"]["flows_per_sec"]),
        f"{env['batch']['1000']['flows_per_sec']:,.0f}–{env['batch']['5000']['flows_per_sec']:,.0f}", f"{ENVELOPE}:metrics.envelope.batch")
    put("perf_batch500", env["batch"]["500"]["flows_per_sec"], f"{env['batch']['500']['flows_per_sec']:.0f}", f"{ENVELOPE}:metrics.envelope.batch.500")
    sv = load("reports/final_security_validation_report.json")
    put("p12_categories", len(sv["categories"]), str(len(sv["categories"])), "reports/final_security_validation_report.json:categories")
    put("p12_overall", sv["overall"], str(sv["overall"]), "reports/final_security_validation_report.json:overall")

    # --- CSE-CIC-IDS2018 (sample v2 when available)
    src, fz = _frozen18()
    b = fz["binary"]
    for k, fmt in (("f1", f3), ("recall", f3), ("precision", f3)):
        put(f"x_frozen_{k}", b[k], fmt(b[k]), f"{src}:binary.{k}")
    put("x_frozen_fpr", b["benign_fpr"], pct(b["benign_fpr"], 2), f"{src}:binary.benign_fpr")
    per = {r["label"]: r for r in fz["per_label"]}
    for lab, tag in (("DoS attacks-Slowloris", "slowloris"), ("FTP-BruteForce", "ftp"), ("DoS attacks-Hulk", "hulk"),
                     ("SSH-Bruteforce", "ssh"), ("DDoS attacks-LOIC-HTTP", "loichttp")):
        if lab in per:
            put(f"x_frozen_{tag}", per[lab]["alert_rate"], pct(per[lab]["alert_rate"]), f"{src}:per_label[{lab}].alert_rate")
            put(f"x_frozen_{tag}_n", per[lab]["n"], n0(per[lab]["n"]), f"{src}:per_label[{lab}].n")
    put("x_frozen_n_total", fz["n"]["benign"] + fz["n"]["attack"], n0(fz["n"]["benign"] + fz["n"]["attack"]), f"{src}:n")
    put("x_frozen_n_benign", fz["n"]["benign"], n0(fz["n"]["benign"]), f"{src}:n.benign")
    put("x_frozen_per_label_cap", fz["sampling"]["per_attack_label"], n0(fz["sampling"]["per_attack_label"]), f"{src}:sampling.per_attack_label")
    put("x_sample_version", fz["sampling"].get("cic2018_sample_version", 1), f"v{fz['sampling'].get('cic2018_sample_version', 1)}", f"{src}:sampling")
    ds = load(DATASET)
    key18 = f"cic2018_v{fz['sampling'].get('cic2018_sample_version', 1)}"
    if key18 in ds:
        put("x_sample_rows", ds[key18]["rows"], n0(ds[key18]["rows"]), f"{DATASET}:{key18}.rows")
        put("x_sample_benign", ds[key18]["by_family"]["BENIGN"], n0(ds[key18]["by_family"]["BENIGN"]), f"{DATASET}:{key18}.by_family.BENIGN")
        nb_days = sum(1 for fams in ds[key18]["by_day_family"].values() if fams.get("BENIGN"))
        put("x_sample_benign_days", nb_days, str(nb_days), f"{DATASET}:{key18}.by_day_family")
        put("x_sample_days", len(ds[key18]["by_day_family"]), str(len(ds[key18]["by_day_family"])), f"{DATASET}:{key18}.by_day_family")
    if "cic2018_v1" in ds:
        nb1 = sum(1 for fams in ds["cic2018_v1"]["by_day_family"].values() if fams.get("BENIGN"))
        put("x_v1_benign_days", nb1, str(nb1), f"{DATASET}:cic2018_v1.by_day_family")
    cs_src = CROSS_V2 if exists(CROSS_V2) else CROSS_V1
    cs = load(cs_src)
    co = cs["per_fold"]["cross_dataset"][X18]
    au = [m(co[k]["auroc_unknown"]) for k in co]
    put("x_auroc_range", (min(au), max(au)), f"{min(au):.2f}–{max(au):.2f}", f"{cs_src}:per_fold.cross_dataset.*.auroc_unknown")
    for k, name in ((OSR, "osr"), (XGB, "xgb")):
        put(f"x_{name}_fpr", m(co[k]["fpr"]), pct(m(co[k]["fpr"])), f"{cs_src}:per_fold.cross_dataset.{k}.fpr")
        put(f"x_{name}_auroc", m(co[k]["auroc_unknown"]), f"{m(co[k]['auroc_unknown']):.2f}", f"{cs_src}:per_fold.cross_dataset.{k}.auroc_unknown")
        put(f"x_{name}_known", m(co[k]["known_recall"]), f3(m(co[k]["known_recall"])), f"{cs_src}:per_fold.cross_dataset.{k}.known_recall")
    put("x_osr_fpr_ratio", m(co[OSR]["fpr"]) / 0.01, f"{m(co[OSR]['fpr']) / 0.01:.0f}", f"{cs_src}:per_fold.cross_dataset (÷ α)")
    cat = cs["attribution"]["cross_dataset"][X18]["known_family_accuracy"]
    put("x_family_acc", m(cat), pct(m(cat)), f"{cs_src}:attribution.cross_dataset.known_family_accuracy")
    if exists(PERDAY):
        pdx = load(PERDAY)
        ad = pdx["adaptation"]["cross_perday"]
        po = pdx["overall"]["cross_perday"][OSR]
        put("pd_none_fpr", m(po["fpr"]), pct(m(po["fpr"])), f"{PERDAY}:overall.cross_perday.{OSR}.fpr")
        for w in (500, 2000, 5000):
            ov = ad.get(f"recal@{w}", {}).get("overall", {}).get(OSR)
            if ov:
                put(f"pd_recal{w}_fpr", m(ov["fpr"]), pct(m(ov["fpr"]), 2), f"{PERDAY}:adaptation.cross_perday.recal@{w}.overall.{OSR}.fpr")
                kr = m(ov["known_recall"])
                put(f"pd_recal{w}_known", kr, f3(kr), f"{PERDAY}:adaptation.cross_perday.recal@{w}.overall.{OSR}.known_recall")
                zr = m(ov["zero_day_recall"])
                put(f"pd_recal{w}_zdr", zr, f3(zr), f"{PERDAY}:adaptation.cross_perday.recal@{w}.overall.{OSR}.zero_day_recall")
        days_ok = [d_ for d_, v in ad.get("recal@2000", {}).get("per_fold", {}).items() if m(v[OSR]["fpr"]) is not None]
        put("pd_days", len(days_ok), str(len(days_ok)), f"{PERDAY}:adaptation.cross_perday.recal@2000.per_fold")
        within = [d_ for d_ in days_ok if m(ad["recal@2000"]["per_fold"][d_][OSR]["fpr"]) <= 0.015]
        put("pd_days_within", len(within), str(len(within)), f"{PERDAY}:adaptation.cross_perday.recal@2000.per_fold (FPR ≤ 1.5%)")
        # documented anomaly: the day whose BENIGN flows look least like benign traffic elsewhere
        prof = load(DATASET).get("cic2018_v2", {}).get("benign_median_by_day", {})
        if prof:
            fb = {d_: v["Flow Bytes/s"] for d_, v in prof.items()}
            odd = max(fb, key=lambda d_: fb[d_] / (sorted(fb.values())[len(fb) // 2] or 1))
            others = sorted(v for d_, v in fb.items() if d_ != odd)
            put("pd_anomaly_day", odd, odd, f"{DATASET}:cic2018_v2.benign_median_by_day (max Flow Bytes/s ratio)")
            put("pd_anomaly_bytes", fb[odd], f"{fb[odd]:,.0f}", f"{DATASET}:cic2018_v2.benign_median_by_day.{odd}")
            put("pd_other_bytes_median", others[len(others) // 2], f"{others[len(others) // 2]:,.0f}",
                f"{DATASET}:cic2018_v2.benign_median_by_day (median over other days)")
            put("pd_anomaly_none_fpr", m(pdx["per_fold"]["cross_perday"][odd][OSR]["fpr"]),
                pct(m(pdx["per_fold"]["cross_perday"][odd][OSR]["fpr"])), f"{PERDAY}:per_fold.cross_perday.{odd}.{OSR}.fpr")
            for key, tag in (("recal@2000", "recal2000"),):
                rest = [m(v[OSR]["fpr"]) for d_, v in ad[key]["per_fold"].items() if d_ != odd and m(v[OSR]["fpr"]) is not None]
                put(f"pd_{tag}_fpr_excl", _mean(rest), pct(_mean(rest), 2), f"{PERDAY}:adaptation.cross_perday.{key}.per_fold (day mean excl. {odd})")
        fpr_days = [m(ad["recal@2000"]["per_fold"][d_][OSR]["fpr"]) for d_ in days_ok]
        put("pd_recal2000_fpr_range", (min(fpr_days), max(fpr_days)), f"{pct(min(fpr_days), 2)}–{pct(max(fpr_days), 2)}",
            f"{PERDAY}:adaptation.cross_perday.recal@2000.per_fold.*.{OSR}.fpr")
    return F


_DIGITS = ["Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]


def fact_macro_name(key: str) -> str:
    """'x_osr_fpr' -> 'FactXOsrFpr', 'pd_recal2000_fpr' -> 'FactPdRecalTwoZeroZeroZeroFpr' (letters only)."""
    out = []
    for part in key.split("_"):
        word = "".join(_DIGITS[int(ch)] if ch.isdigit() else ch for ch in part)
        out.append(word[:1].upper() + word[1:])
    return "Fact" + "".join(out)


# ------------------------------------------------------------------------------- renderers
def _md_cell(s: str) -> str:
    return s.replace("|", "\\|")


def to_markdown(t: Table) -> str:
    out = [f"### {t.title}", "", "| " + " | ".join(t.header) + " |", "|" + "---|" * len(t.header)]
    out += ["| " + " | ".join(_md_cell(c.strip()) or " " for c in r) + " |" for r in t.rows]
    if t.notes:
        out += ["", f"_{t.notes}_"]
    out += ["", "Sources: " + "; ".join(f"`{s}`" for s in t.sources), ""]
    return "\n".join(out)


_TEX_ESC = {"%": r"\%", "&": r"\&", "_": r"\_", "#": r"\#", "→": r"$\rightarrow$", "–": "--", "—": "---",
            "≤": r"$\le$", "≥": r"$\ge$", "×": r"$\times$", "−": "-", "Δ": r"$\Delta$", "α": r"$\alpha$",
            "τ": r"$\tau$", "≈": r"$\approx$", "k-NN": r"$k$-NN"}


def tex_escape(s: str) -> str:
    s = re.sub(r"\^\{([^}]*)\}", lambda mm: f"@@SUP{mm.group(1)}@@", s)
    for a, b in _TEX_ESC.items():
        s = s.replace(a, b)
    s = re.sub(r"@@SUP([^@]*)@@", lambda mm: f"$^{{{mm.group(1).replace('$', '')}}}$", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", s)
    return s


def to_latex(t: Table) -> str:
    """A complete table environment; \\input it in paper.tex."""
    cols = "l" + "c" * (len(t.header) - 1)
    # IEEE two-column layout: anything wider than four columns spans the page; every tabular is
    # wrapped in adjustbox{max width} so it can only shrink to fit, never overflow (requires adjustbox).
    env = "table*" if len(t.header) > 4 else "table"
    lines = [f"% AUTO-GENERATED by research/publication.py — sources: {'; '.join(t.sources)}",
             f"\\begin{{{env}}}[t]", "\\centering", "\\footnotesize",
             f"\\caption{{{tex_escape(t.title)}}}", f"\\label{{tab:{t.key}}}",
             "\\begin{adjustbox}{max width=\\linewidth}", f"\\begin{{tabular}}{{{cols}}}", "\\toprule",
             " & ".join(f"\\textbf{{{tex_escape(h)}}}" for h in t.header) + " \\\\", "\\midrule"]
    lines += [" & ".join(tex_escape(c.strip()) for c in r) + " \\\\" for r in t.rows]
    lines += ["\\bottomrule", "\\end{tabular}", "\\end{adjustbox}"]
    if t.notes:
        lines.append(f"\\\\[2pt]\\parbox{{0.95\\linewidth}}{{\\scriptsize {tex_escape(t.notes)}}}")
    lines.append(f"\\end{{{env}}}")
    return "\n".join(lines) + "\n"


def write_all(out_dir: Path | None = None) -> dict[str, Table]:
    out_dir = out_dir or ROOT / "docs" / "research" / "publication"
    tables = build_tables()
    (out_dir / "tables").mkdir(parents=True, exist_ok=True)
    for k, t in tables.items():
        (out_dir / "tables" / f"{k}.tex").write_text(to_latex(t), encoding="utf-8")
    (out_dir / "TABLES.md").write_text(render_markdown(tables), encoding="utf-8")
    (out_dir / "publication_tables.json").write_text(render_json(tables, facts()), encoding="utf-8")
    return tables


def render_json(tables: dict[str, Table], fx: dict[str, Fact]) -> str:
    payload = {"tables": {k: asdict(t) for k, t in tables.items()},
               "facts": {k: {"display": f.display, "source": f.source} for k, f in sorted(fx.items())}}
    return json.dumps(payload, indent=1, ensure_ascii=False, default=str)


def render_markdown(tables: dict[str, Table]) -> str:
    md = ["# Publication tables (auto-generated)", "",
          "_Generated by `python scripts/62_publication_tables.py` from committed result artifacts. Do not edit; "
          "`tests/test_publication_tables.py` fails if these drift from the artifacts._", ""]
    md += [to_markdown(t) for t in tables.values()]
    return "\n".join(md)
