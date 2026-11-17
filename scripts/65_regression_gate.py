"""R3 regression gate (Stage 0): nothing may change before any new experiment is trusted.

    python scripts/65_regression_gate.py                       # LOAFO + per-day, seeds 1-5 (~2 h CPU)
    python scripts/65_regression_gate.py --protocols loafo --seeds 1   # partial check

Checks (all must pass; the report says which did not):
  1. historical artifacts — every file in research_artifacts/PROTECTED_MANIFEST.json is unchanged;
  2. frozen v1.1 — the frozen model/threshold/report files are byte-identical to tag v1.1-research,
     and re-scoring the frozen detector on CSE-CIC-IDS2018 (v2) reproduces frozen_v11_on_cic2018_v2.json;
  3. exact reproduction — re-running each protocol (same code path, seeds, caps) **with per-flow score
     dumps enabled** reproduces every value of the committed records (timing fields excluded);
  4. score completeness — every evaluated flow of every record and adaptation variant has a dump row,
     with the evidence streams, surprisals, fused scores and p-values present and finite;
  5. overwrite protection — writing to a protected path is refused.

Outputs (never inside the protected set):
  research_artifacts/r3/regression/<protocol>_records.json   re-run records
  research_artifacts/r3/regression/scores/                   per-flow dumps (git-ignored) + manifest.json
  research_artifacts/r3/regression_gate_report.json          the gate result
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import subprocess
import sys
import tempfile
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

import research.protocols as P  # noqa: E402
from research.artifact_guard import (R3_DIR, ProtectedArtifactError, assert_writable, frozen_v11_diff,  # noqa: E402
                                     verify_manifest)
from research.data import ARTIFACT_DIR, feature_columns, load_cic2017, load_cic2018  # noqa: E402
from research.openset import PROPOSED  # noqa: E402
from research.scoredump import ScoreDump  # noqa: E402

OUT = R3_DIR / "regression"
REPORT = R3_DIR / "regression_gate_report.json"
TIMING_KEYS = {"fit_seconds", "score_ms_per_1k_flows"}
COMMITTED = {"loafo": "openset_loafo_records.json", "temporal": "openset_temporal_records.json",
             "cross": "openset_cross_records_v2.json", "cross_perday": "openset_cross_perday_records.json"}
REQUIRED_STREAM_COLS = ["raw_sup", "raw_knn", "t_sup", "t_knn", f"fused__{PROPOSED}", f"p__{PROPOSED}"]


def _exp_module():
    spec = importlib.util.spec_from_file_location("exp50", ROOT / "scripts" / "50_openset_experiments.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _git_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()


def compare(a, b, path: str = "", out: list | None = None, limit: int = 50) -> list[str]:
    """Exact recursive comparison of two JSON trees; returns mismatch paths (timing keys ignored)."""
    out = [] if out is None else out
    if len(out) >= limit:
        return out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k in TIMING_KEYS:
                continue
            if k not in a or k not in b:
                out.append(f"{path}/{k}: missing in {'original' if k not in a else 'rerun'}")
            else:
                compare(a[k], b[k], f"{path}/{k}", out, limit)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{path}: length {len(a)} vs {len(b)}")
        for i, (x, y) in enumerate(zip(a, b)):
            compare(x, y, f"{path}[{i}]", out, limit)
    else:
        na = a is None or (isinstance(a, float) and math.isnan(a))
        nb = b is None or (isinstance(b, float) and math.isnan(b))
        if not (na and nb) and a != b:
            out.append(f"{path}: {a!r} vs {b!r}")
    return out


def count_leaves(x) -> int:
    if isinstance(x, dict):
        return sum(count_leaves(v) for k, v in x.items() if k not in TIMING_KEYS)
    if isinstance(x, list):
        return sum(count_leaves(v) for v in x)
    return 1


def check_frozen_rescore() -> dict:
    committed = json.loads((ARTIFACT_DIR / "frozen_v11_on_cic2018_v2.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "frozen_rescore.json"
        subprocess.run([sys.executable, str(ROOT / "scripts" / "54_frozen_v11_on_cic2018.py"), "--cic2018-version", "2",
                        "--out", str(tmp)], cwd=ROOT, check=True, capture_output=True, text=True)
        rerun = json.loads(tmp.read_text(encoding="utf-8"))
    keys = ["binary", "per_label", "n", "sampling"]
    diffs = compare({k: committed[k] for k in keys}, {k: rerun[k] for k in keys})
    return {"compared_keys": keys, "mismatches": diffs, "pass": not diffs}


def run_protocol(proto: str, seeds: list[int], df17: pd.DataFrame, dump: ScoreDump, exp) -> list[dict]:
    log_path = OUT / f"{proto}.log"
    logf = log_path.open("a", encoding="utf-8")

    def log(m: str) -> None:
        logf.write(m + "\n")
        logf.flush()

    recs: list[dict] = []
    df18 = None
    for seed in seeds:
        kw = dict(seeds=[seed], alpha=0.01, ae_kwargs={"epochs": 25}, log=log, dump=dump)
        t = time.time()
        if proto == "loafo":
            out = P.loafo(df17, **kw)
        elif proto == "temporal":
            out = P.temporal(df17, **kw)
        else:
            if df18 is None:
                df18 = load_cic2018(feature_columns(df17), version=2)
            out = P.cross_dataset_perday(df17, df18, **kw) if proto == "cross_perday" else P.cross_dataset(df17, df18, **kw)
        recs += out
        print(f"  {proto} seed {seed}: {len(out)} records in {time.time() - t:.0f}s", flush=True)
        path = OUT / f"{proto}_records.json"
        assert_writable(path)
        exp._write(path, {"meta": {"git_commit": _git_commit(), "purpose": "R3 regression gate re-run"},
                          "records": recs})
    logf.close()
    return json.loads((OUT / f"{proto}_records.json").read_text(encoding="utf-8"))["records"]


def check_reproduction(proto: str, rerun: list[dict], seeds: list[int]) -> dict:
    orig_all = json.loads((ARTIFACT_DIR / COMMITTED[proto]).read_text(encoding="utf-8"))["records"]
    orig = {(r["fold"], r["seed"]): r for r in orig_all if r["seed"] in seeds}
    rep = {(r["fold"], r["seed"]): r for r in rerun}
    missing = sorted(set(orig) - set(rep))
    extra = sorted(set(rep) - set(orig))
    mism, leaves = [], 0
    for k in sorted(set(orig) & set(rep)):
        leaves += count_leaves(orig[k])
        mism += [f"{k}: {d}" for d in compare(orig[k], rep[k])]
    return {"records_compared": len(set(orig) & set(rep)), "values_compared": leaves, "mismatches": mism[:50],
            "n_mismatches": len(mism), "missing_in_rerun": [list(m) for m in missing], "extra_in_rerun": [list(e) for e in extra],
            "pass": not mism and not missing}


def check_scores(proto: str, rerun: list[dict], dump_root: Path) -> dict:
    man = json.loads((dump_root / "manifest.json").read_text(encoding="utf-8"))["files"]
    by_key = {(e["protocol"], str(e["fold"]), e["seed"], e["variant"]): (rel, e) for rel, e in man.items()}
    problems, n_checked, n_rows = [], 0, 0
    for r in rerun:
        variants = ["none", *sorted(r.get("adaptation") or {})]
        for v in variants:
            hit = by_key.get((proto, str(r["fold"]), r["seed"], v))
            if hit is None:
                problems.append(f"{r['fold']} s{r['seed']} {v}: no dump")
                continue
            rel, e = hit
            if e["groups"] != r["n_test"]:
                problems.append(f"{rel}: groups {e['groups']} != n_test {r['n_test']}")
            df = pd.read_parquet(dump_root / rel, columns=REQUIRED_STREAM_COLS)
            if len(df) != sum(r["n_test"].values()):
                problems.append(f"{rel}: {len(df)} rows != {sum(r['n_test'].values())} evaluated flows")
            bad = [c for c in REQUIRED_STREAM_COLS if not np.isfinite(df[c].to_numpy()).all()]
            if bad:
                problems.append(f"{rel}: non-finite values in {bad}")
            n_checked += 1
            n_rows += len(df)
    return {"dumps_checked": n_checked, "flows_with_scores": n_rows, "problems": problems[:50], "pass": not problems}


def check_overwrite_protection() -> dict:
    tried = {}
    for rel in ["research_artifacts/openset_loafo_records.json", "models/trained_models/binary_best.joblib"]:
        try:
            assert_writable(ROOT / rel)
            tried[rel] = "ALLOWED (bad)"
        except ProtectedArtifactError:
            tried[rel] = "refused"
    return {"attempts": tried, "pass": all(v == "refused" for v in tried.values())}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--protocols", nargs="+", default=["loafo", "cross_perday"], choices=list(COMMITTED))
    ap.add_argument("--seeds", nargs="+", type=int, default=[1, 2, 3, 4, 5])
    ap.add_argument("--skip-frozen-rescore", action="store_true")
    ap.add_argument("--tag", default="", help="separate output folder/report, e.g. 'r3env' (keeps the full gate report)")
    a = ap.parse_args()
    global OUT, REPORT
    if a.tag:
        OUT = R3_DIR / f"regression_{a.tag}"
        REPORT = R3_DIR / f"regression_gate_report_{a.tag}.json"
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    report: dict = {"generated_at": datetime.now(timezone.utc).isoformat(), "git_commit": _git_commit(),
                    "python": sys.executable,
                    "protocols": a.protocols, "seeds": a.seeds, "checks": {}}

    bad = verify_manifest()
    report["checks"]["historical_artifacts_unchanged"] = {"changed_or_missing": bad, "pass": not bad}
    fz = frozen_v11_diff()
    report["checks"]["frozen_v11_files_equal_tag"] = {"differing": fz, "pass": not fz}
    report["checks"]["overwrite_protection"] = check_overwrite_protection()
    if not a.skip_frozen_rescore:
        print("re-scoring frozen v1.1 on CSE-CIC-IDS2018 v2 ...", flush=True)
        report["checks"]["frozen_v11_rescore"] = check_frozen_rescore()

    exp = _exp_module()
    print("loading CICIDS2017 ...", flush=True)
    df17 = load_cic2017()
    for proto in a.protocols:
        dump_root = OUT / "scores" / proto
        dump = ScoreDump(dump_root)
        print(f"re-running {proto} with score dumps (seeds {a.seeds}) ...", flush=True)
        rerun = run_protocol(proto, a.seeds, df17, dump, exp)
        report["checks"][f"reproduction_{proto}"] = check_reproduction(proto, rerun, a.seeds)
        report["checks"][f"score_completeness_{proto}"] = check_scores(proto, rerun, dump_root)

    report["runtime_seconds"] = round(time.time() - t0, 1)
    report["pass"] = all(c["pass"] for c in report["checks"].values())
    assert_writable(REPORT)
    REPORT.write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v["pass"] for k, v in report["checks"].items()}, indent=1))
    print("GATE:", "PASS" if report["pass"] else "FAIL", f"({report['runtime_seconds']:.0f}s)")
    sys.exit(0 if report["pass"] else 1)


if __name__ == "__main__":
    main()
