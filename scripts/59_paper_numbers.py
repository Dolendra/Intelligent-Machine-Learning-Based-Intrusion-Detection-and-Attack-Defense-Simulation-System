"""Single source of truth for every number quoted in the paper, guide and report (R1a-C).

Reads ONLY result artifacts (never documents) and writes
  docs/research/paper_numbers.json   {key: {value, display, source}}
  docs/research/paper_numbers.tex    \\newcommand{\\Key}{display} for every key (\\input in paper.tex)

``tests/test_paper_claims.py`` recomputes these values and checks that the paper uses them,
so a stale or hand-typed number fails CI. Rerun after any experiment:
    python scripts/59_paper_numbers.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

OUT_JSON = ROOT / "docs" / "research" / "paper_numbers.json"
OUT_TEX = ROOT / "docs" / "research" / "paper_numbers.tex"

LOAFO = "research_artifacts/openset_loafo_summary.json"
TEMPORAL = "research_artifacts/openset_temporal_summary.json"
CROSS = "research_artifacts/openset_cross_summary.json"
GATE = "research_artifacts/zero_day_gate_report.json"
FROZEN18 = "research_artifacts/frozen_v11_on_cic2018.json"
FAMILIES = "research_artifacts/model_family_comparison.json"
XAI = "models/trained_models/xai_stability_report.json"
RANGE = "results/cyber_range/experiments/latest.json"
POOL = "research_artifacts/replay/replay_pool_manifest.json"

OSR, XGB, DT = "Aegis-OSR", "Closed-set XGB", "Closed-set DT (v1.1-style)"
FRI, THU = "Mon-Thu→Fri", "Mon-Wed→Thu"
X18 = "CICIDS2017→CSE-CIC-IDS2018"

_cache: dict[str, Any] = {}


def load(rel: str) -> Any:
    if rel not in _cache:
        _cache[rel] = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    return _cache[rel]


def dig(obj: Any, path: list) -> Any:
    for p in path:
        obj = obj[p]
    return obj


# formatters ------------------------------------------------------------------------------
def f3(v: float) -> str:
    return f"{v:.3f}"


def pct1(v: float) -> str:
    return f"{100 * v:.1f}\\%"


def pct2(v: float) -> str:
    return f"{100 * v:.2f}\\%"


def sci(v: float) -> str:
    m, e = f"{v:.1e}".split("e")
    return f"{m}\\times10^{{{int(e)}}}"


def plain(v: Any) -> str:
    return f"{v:g}" if isinstance(v, float) else str(v)


def sgn3(v: float) -> str:
    return f"{v:+.3f}"


def one(v: float) -> str:
    return f"{v:.1f}"


NUMBERS: dict[str, dict] = {}


def put(key: str, value: Any, fmt: Callable[[Any], str], source: str, path: list | str) -> None:
    assert re.fullmatch(r"[A-Za-z]+", key), f"LaTeX macro names must be letters only: {key}"
    assert key not in NUMBERS, key
    NUMBERS[key] = {"value": value, "display": fmt(value), "source": f"{source}:{path if isinstance(path, str) else '.'.join(map(str, path))}"}


def ci(prefix: str, src: str, path: list, fmt=f3) -> None:
    c = dig(load(src), path)
    put(prefix, c["mean"], fmt, src, path + ["mean"])
    put(prefix + "Lo", c["ci_low"], fmt, src, path + ["ci_low"])
    put(prefix + "Hi", c["ci_high"], fmt, src, path + ["ci_high"])


# ------------------------------------------------------------------------------- LOAFO
def loafo() -> None:
    s = load(LOAFO)
    put("LoafoRecords", s["meta"]["n_records"], plain, LOAFO, "meta.n_records")
    put("LoafoSeeds", len(s["meta"]["seeds"]), plain, LOAFO, "meta.seeds")
    ci("LoafoOsrZdr", LOAFO, ["overall", "loafo", OSR, "zero_day_recall"])
    ci("LoafoOsrAuroc", LOAFO, ["overall", "loafo", OSR, "auroc_unknown"])
    ci("LoafoOsrFpr", LOAFO, ["overall", "loafo", OSR, "fpr"], pct2)
    ci("LoafoXgbZdr", LOAFO, ["overall", "loafo", XGB, "zero_day_recall"])
    ci("LoafoDtZdr", LOAFO, ["overall", "loafo", DT, "zero_day_recall"])
    for fam in ("Bot", "BruteForce", "DDoS", "DoS", "PortScan", "WebAttack"):
        put(f"LoafoOsr{fam}", dig(s, ["per_fold", "loafo", fam, OSR, "zero_day_recall", "mean"]), pct1, LOAFO,
            ["per_fold", "loafo", fam, OSR, "zero_day_recall", "mean"])
        put(f"LoafoXgb{fam}", dig(s, ["per_fold", "loafo", fam, XGB, "zero_day_recall", "mean"]), pct1, LOAFO,
            ["per_fold", "loafo", fam, XGB, "zero_day_recall", "mean"])
    p5 = ["per_fold", "loafo", "PortScan", OSR, "zero_day_recall@0.05", "mean"]
    put("LoafoOsrPortScanAtFive", dig(s, p5), pct1, LOAFO, p5)
    bot = {m: v["zero_day_recall"]["mean"] for m, v in s["per_fold"]["loafo"]["Bot"].items()}
    best = max(bot, key=bot.get)
    put("LoafoBotBestAny", bot[best], pct1, LOAFO, f"per_fold.loafo.Bot.{best}.zero_day_recall.mean (max over methods)")
    sig = ["significance_seed_level", "loafo", "zero_day_recall"]
    for short, m in (("Xgb", XGB), ("Dt", DT), ("Energy", "XGB + Energy"), ("Ae", "Autoencoder"),
                     ("Knn", "kNN distance"), ("AblAe", "Aegis-OSR w/ AE novelty"),
                     ("AblMax", "Aegis-OSR w/ max fusion"), ("AblOmni", "Aegis-OSR w/ omnibus fusion")):
        t = dig(s, sig + [m])
        put(f"Delta{short}", t["mean_diff"], sgn3, LOAFO, sig + [m, "mean_diff"])
        put(f"Delta{short}Lo", t["diff_ci_low"], sgn3, LOAFO, sig + [m, "diff_ci_low"])
        put(f"Delta{short}Hi", t["diff_ci_high"], sgn3, LOAFO, sig + [m, "diff_ci_high"])
        put(f"Tp{short}", t["t_p_value"], sci, LOAFO, sig + [m, "t_p_value"])
        put(f"PosSeeds{short}", t["positive_seeds"], plain, LOAFO, sig + [m, "positive_seeds"])
    pairs = dig(s, ["significance", "loafo", "zero_day_recall", XGB])
    put("PairWinsXgb", pairs["wins"], plain, LOAFO, "significance.loafo.zero_day_recall.Closed-set XGB.wins")
    put("PairsN", pairs["n"], plain, LOAFO, "significance.loafo.zero_day_recall.Closed-set XGB.n")


# ------------------------------------------------------------------------------- temporal / cross
def _ad(src: str, proto: str, key: str, fold: str, m: str, metric: str) -> tuple[float, list]:
    path = ["adaptation", proto, key, "per_fold", fold, m, metric, "mean"]
    return dig(load(src), path), path


def temporal() -> None:
    for tag, fold in (("Fri", FRI), ("Thu", THU)):
        for short, m in (("Osr", OSR), ("Xgb", XGB), ("Knn", "kNN distance")):
            for met, fmt in (("fpr", pct2), ("zero_day_recall", f3)):
                p = ["per_fold", "temporal", fold, m, met, "mean"]
                put(f"Temp{tag}{short}{'Fpr' if met == 'fpr' else 'Zdr'}", dig(load(TEMPORAL), p), fmt, TEMPORAL, p)
        for key, name in (("recal@500", "RecalFiveH"), ("recal@2000", "RecalTwoK"), ("recal@5000", "RecalFiveK"),
                          ("recal+ref@500", "RefFiveH"), ("recal+ref@2000", "RefTwoK"), ("recal+ref@5000", "RefFiveK"),
                          ("oracle@2000", "OracleTwoK")):
            for met, fmt in (("fpr", pct2), ("zero_day_recall", f3)):
                v, p = _ad(TEMPORAL, "temporal", key, fold, OSR, met)
                put(f"Temp{tag}{name}{'Fpr' if met == 'fpr' else 'Zdr'}", v, fmt, TEMPORAL, p)


def cross() -> None:
    for short, m in (("Osr", OSR), ("Xgb", XGB)):
        for met, suf, fmt in (("fpr", "Fpr", pct1), ("zero_day_recall", "Zdr", f3), ("known_recall", "Known", f3)):
            p = ["per_fold", "cross_dataset", X18, m, met, "mean"]
            put(f"Cross{short}{suf}", dig(load(CROSS), p), fmt, CROSS, p)
    for key, name in (("recal@500", "RecalFiveH"), ("recal@2000", "RecalTwoK"), ("recal+ref@2000", "RefTwoK"),
                      ("recal+ref@5000", "RefFiveK")):
        for met, fmt in (("fpr", pct1), ("zero_day_recall", f3)):
            v, p = _ad(CROSS, "cross_dataset", key, X18, OSR, met)
            put(f"Cross{name}{'Fpr' if met == 'fpr' else 'Zdr'}", v, fmt, CROSS, p)
    per = {r["label"]: r for r in load(FROZEN18)["per_label"]}
    for lab, name in (("DoS attacks-Hulk", "Hulk"), ("SSH-Bruteforce", "Ssh"), ("DDoS attacks-LOIC-HTTP", "LoicHttp"),
                      ("DoS attacks-Slowloris", "Slowloris")):
        put(f"FrozenEighteen{name}", per[lab]["alert_rate"], pct1, FROZEN18, f"per_label[{lab}].alert_rate")
    b = load(FROZEN18)["binary"]
    for k, n, fmt in (("f1", "FrozenEighteenFone", f3), ("recall", "FrozenEighteenRecall", f3),
                      ("precision", "FrozenEighteenPrecision", f3), ("benign_fpr", "FrozenEighteenFpr", pct2)):
        put(n, b[k], fmt, FROZEN18, ["binary", k])


# ------------------------------------------------------------------------------- gate (clean head-to-head)
def gate() -> None:
    ev = load(GATE)["evaluation"]
    assert ev.get("protocol_version", 1) >= 2, "gate report predates the R1a clean head-to-head"
    g = ev["gate"]
    put("GateFpr", g["benign_fpr"], pct2, GATE, "evaluation.gate.benign_fpr")
    put("GateKnownRecall", g["known_attack_recall"], f3, GATE, "evaluation.gate.known_attack_recall")
    h = ev["head_to_head"]
    put("HthFrozenFpr", h["frozen_v11"]["benign_fpr"], pct2, GATE, "evaluation.head_to_head.frozen_v11.benign_fpr")
    put("HthFrozenKnown", h["frozen_v11"]["known_attack_recall"], f3, GATE, "evaluation.head_to_head.frozen_v11.known_attack_recall")
    for fam in ("WebAttack", "Bot"):
        r = h["per_family_recall"][fam]
        put(f"Hth{fam}Frozen", r["frozen_v11"], pct1, GATE, f"evaluation.head_to_head.per_family_recall.{fam}.frozen_v11")
        put(f"Hth{fam}Gate", r["gate"], pct1, GATE, f"evaluation.head_to_head.per_family_recall.{fam}.gate")
        put(f"Hth{fam}N", r["n"], plain, GATE, f"evaluation.head_to_head.per_family_recall.{fam}.n")
    un = ev["natural_unknowns"]
    total = sum(u["n"] for u in un)
    put("UnseenTotal", total, plain, GATE, "evaluation.natural_unknowns[*].n")
    put("UnseenGateCaught", round(sum(u["gate_alert_rate"] * u["n"] for u in un)), plain, GATE,
        "evaluation.natural_unknowns[*].gate_alert_rate*n")
    put("UnseenFrozenCaught", round(sum(u["frozen_v11_attack_rate"] * u["n"] for u in un)), plain, GATE,
        "evaluation.natural_unknowns[*].frozen_v11_attack_rate*n")
    m = load(POOL)
    put("PoolRows", m["rows"], plain, POOL, "rows")


# ------------------------------------------------------------------------------- model families, XAI
def families_xai() -> None:
    r = load(FAMILIES)["results"]
    best = max(r, key=lambda k: r[k]["heldout_mean"]["zero_day_recall"])
    put("FamBestHeldout", r[best]["heldout_mean"]["zero_day_recall"], pct1, FAMILIES, f"results.{best}.heldout_mean.zero_day_recall")
    put("FamCount", len(r), plain, FAMILIES, "results")
    x = load(XAI)
    put("XaiShapLime", x["overall"]["shap_lime_jaccard_top5"]["mean"], f3, XAI, "overall.shap_lime_jaccard_top5.mean")
    for fam in ("Bot", "WebAttack"):
        put(f"XaiRobust{fam}", x["per_family"][fam]["robustness_jaccard_top5"]["mean"], f3, XAI,
            f"per_family.{fam}.robustness_jaccard_top5.mean")


# ------------------------------------------------------------------------------- cyber range
def _cells(suite: str) -> list[dict]:
    return load(RANGE)["suites"][suite]["cells"]


def _cell(suite: str, **dims) -> dict:
    hits = [c for c in _cells(suite) if all(c["cell"].get(k) == v for k, v in dims.items())]
    assert len(hits) == 1, (suite, dims, len(hits))
    return hits[0]["summary"]


def cyber_range() -> None:
    d = load(RANGE)
    n_seeds = len(d["seeds"])
    total = sum(len(s["cells"]) for s in d["suites"].values()) * n_seeds
    put("RangeRuns", total, plain, RANGE, "sum(len(suites.*.cells)) * len(seeds)")
    put("RangeSeeds", n_seeds, plain, RANGE, "seeds")
    for det, name in (("frozen", "Frozen"), ("gate", "Gate")):
        s = _cell("detector", scenario="zero_day", detector=det)
        put(f"RangeZeroDay{name}Detected", s["detected"]["mean"], pct1, RANGE,
            f"suites.detector[zero_day,{det}].summary.detected.mean")
    s = _cell("detector", scenario="zero_day", detector="gate")
    put("RangeZeroDayGateLatency", s["detection_latency_s"]["mean"], one, RANGE,
        "suites.detector[zero_day,gate].summary.detection_latency_s.mean")
    thr = {}
    for k in (1, 3):
        vals = [c["summary"]["false_incidents"]["mean"] for c in _cells("threshold") if c["cell"]["alert_threshold"] == k]
        thr[k] = sum(vals) / len(vals)
        put(f"RangeFalseIncidents{'One' if k == 1 else 'Three'}", thr[k], one, RANGE,
            f"mean over scenarios of suites.threshold[alert_threshold={k}].false_incidents")
    iso = [c["summary"] for c in _cells("defense") if c["cell"]["defense"] == "isolate_host"]
    put("RangeIsolateCollateral", sum(s["collateral_rate"]["mean"] for s in iso) / len(iso), pct1, RANGE,
        "mean over scenarios of suites.defense[isolate_host].collateral_rate")
    blk = [c["summary"] for c in _cells("defense") if c["cell"]["defense"] == "block_source"]
    put("RangeBlockCollateral", sum(s["collateral_rate"]["mean"] for s in blk) / len(blk), pct1, RANGE,
        "mean over scenarios of suites.defense[block_source].collateral_rate")
    for delay, name in ((0, "Zero"), (30, "Thirty")):
        s = _cell("delay", scenario="ddos", approval_delay_s=delay)
        put(f"RangeDdosAvail{name}", s["availability_mean_during_attack"]["mean"], pct1, RANGE,
            f"suites.delay[ddos,{delay}].availability_mean_during_attack.mean")


METHOD_ORDER = [
    (OSR, "Proposed"), ("Aegis-OSR w/ omnibus fusion", "Ablation"), ("Aegis-OSR w/ AE novelty", "Ablation"),
    ("Aegis-OSR w/ max fusion", "Ablation"), ("Aegis-OSR w/ IForest novelty", "Ablation"), (XGB, "Baseline"),
    ("XGB + Energy", "Baseline"), ("kNN distance", "Baseline"), (DT, "Baseline"), ("Autoencoder", "Baseline"),
    ("Isolation Forest", "Baseline"),
]
TEX_NAME = {OSR: r"\textbf{Aegis-OSR (proposed)}", "kNN distance": "$k$-NN distance", DT: "Closed-set DT (v1.1-style)"}
ROW_END = " " + "\\" * 2


def _cis(c: dict, fmt) -> str:
    return f"{fmt(c['mean'])} [{fmt(c['ci_low'])}, {fmt(c['ci_high'])}]"


def loafo_tables() -> tuple[str, str]:
    """Table bodies for paper.tex, generated so no table value is ever typed by hand."""
    s = load(LOAFO)
    o = s["overall"]["loafo"]
    rows = []
    for m, kind in METHOD_ORDER:
        r = o[m]
        rows.append(f"{TEX_NAME.get(m, m)} & {kind} & {_cis(r['zero_day_recall'], f3)} & "
                    f"{_cis(r['auroc_unknown'], f3)} & {_cis(r['known_recall'], f3)} & "
                    f"{_cis(r['fpr'], pct2)}{ROW_END}")
    header = f"% AUTO-GENERATED by scripts/59_paper_numbers.py from {LOAFO}\n"
    sig = s["significance_seed_level"]["loafo"]["zero_day_recall"]
    pairs = s["significance"]["loafo"]["zero_day_recall"]
    srows = []
    for m, _ in METHOD_ORDER[1:]:
        t, pr = sig[m], pairs[m]
        srows.append(f"vs. {TEX_NAME.get(m, m)} & {sgn3(t['mean_diff'])} [{sgn3(t['diff_ci_low'])}, "
                     f"{sgn3(t['diff_ci_high'])}] & {t['positive_seeds']}/{t['n_seeds']} & "
                     f"${sci(t['t_p_value'])}$ & {pr['wins']}/{pr['n']}{ROW_END}")
    return header + "\n".join(rows) + "\n", header + "\n".join(srows) + "\n"


def build() -> dict[str, dict]:
    NUMBERS.clear()
    _cache.clear()
    for fn in (loafo, temporal, cross, gate, families_xai, cyber_range):
        fn()
    return dict(NUMBERS)


def main() -> None:
    nums = build()
    OUT_JSON.write_text(json.dumps(nums, indent=1, ensure_ascii=False), encoding="utf-8")
    lines = ["% AUTO-GENERATED by scripts/59_paper_numbers.py from result artifacts. Do not edit.",
             "% Every macro's source file and JSON path is listed in paper_numbers.json."]
    lines += [f"\\newcommand{{\\{k}}}{{{v['display']}}}" for k, v in sorted(nums.items())]
    OUT_TEX.write_text("\n".join(lines) + "\n", encoding="utf-8")
    main_t, sig_t = loafo_tables()
    (OUT_TEX.parent / "paper_table_loafo.tex").write_text(main_t, encoding="utf-8")
    (OUT_TEX.parent / "paper_table_significance.tex").write_text(sig_t, encoding="utf-8")
    print(f"wrote {len(nums)} numbers → {OUT_JSON.relative_to(ROOT)}, {OUT_TEX.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
