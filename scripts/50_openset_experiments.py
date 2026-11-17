"""Aegis-OSR open-set experiments (v3 research track).

Protocols (see research/protocols.py):
  loafo     leave-one-attack-family-out on CICIDS2017 (6 folds)
  temporal  true day-ordered holdout: Mon–Wed→Thu, Mon–Thu→Fri  (+ warm-up recalibration)
  cross     CICIDS2017 → CSE-CIC-IDS2018                        (+ warm-up recalibration)

Methodology note: the Aegis-OSR design (Fisher fusion, kNN novelty) was selected on a pilot
run with seed 0. Reported results use seeds 1..5 (fresh splits, fresh model initializations).

Outputs (research_artifacts/):
  openset_<protocol>_records.json   raw per-run records (written after every run → resumable)
  openset_<protocol>_summary.json   mean ± 95% CI, Wilcoxon tests, attribution

Usage:
  python scripts/50_openset_experiments.py --protocol loafo temporal --seeds 1 2 3 4 5
  python scripts/50_openset_experiments.py --protocol cross --seeds 1 2 3 4 5
  python scripts/50_openset_experiments.py --protocol loafo --seeds 1 --quick   # smoke test
"""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")  # protocol names contain arrows
warnings.filterwarnings("ignore", category=UserWarning)

import numpy as np  # noqa: E402

import research.protocols as P  # noqa: E402
from research.data import ARTIFACT_DIR, load_cic2017, load_cic2018, feature_columns  # noqa: E402
from research.artifact_guard import assert_writable  # noqa: E402


def _json_default(o):
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def _clean(o):
    """Replace NaN with None recursively so the JSON is standards-compliant."""
    if isinstance(o, float) and np.isnan(o):
        return None
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_clean(v) for v in o]
    return o


def _write(path: Path, payload) -> None:
    assert_writable(path)  # historical results are never overwritten (research/artifact_guard.py)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(_clean(payload), indent=1, default=_json_default), encoding="utf-8")
    tmp.replace(path)


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:  # pragma: no cover
        return "unknown"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--protocol", nargs="+", choices=["loafo", "temporal", "cross", "cross_perday"], default=["loafo", "temporal"])
    ap.add_argument("--seeds", nargs="+", type=int, default=[1, 2, 3, 4, 5])
    ap.add_argument("--alpha", type=float, default=0.01)
    ap.add_argument("--quick", action="store_true", help="small caps for a smoke test (not for reporting)")
    ap.add_argument("--resume", action="store_true", help="skip (fold, seed) pairs already in the records file")
    ap.add_argument("--cic2018-version", type=int, default=2, choices=[1, 2],
                    help="CSE-CIC-IDS2018 sample: 2 = benign for every day (R1b); 1 = pre-R1b sample (benign from 4 days)")
    ap.add_argument("--tag", default="", help="suffix for output files, e.g. 'repro' → openset_loafo_records_repro.json "
                                               "(used to reproduce results without overwriting the originals)")
    args = ap.parse_args()

    if args.quick:
        P.TRAIN_CAPS = {"BENIGN": 40_000, "_attack": 5_000}
        P.VAL_CAPS = {"BENIGN": 10_000, "_attack": 1_500}
        P.TEST_CAPS = {"BENIGN": 20_000, "_attack": 3_000}
    suffix = ("_quick" if args.quick else "") + (f"_{args.tag}" if args.tag else "")
    ae_kwargs = {"epochs": 8} if args.quick else {"epochs": 25}

    print("loading CICIDS2017 research cache ...", flush=True)
    df17 = load_cic2017()
    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),
        "seeds": args.seeds,
        "alpha": args.alpha,
        "caps": {"train": P.TRAIN_CAPS, "val": P.VAL_CAPS, "test": P.TEST_CAPS},
        "warmup_windows": list(P.WARMUP_WINDOWS),
        "python": platform.python_version(),
        "quick": args.quick,
        "pilot_seed_excluded": 0,
        "cic2018_sample_version": args.cic2018_version,
    }

    for proto in args.protocol:
        # never overwrite pre-R1b cross-dataset evidence (built on the v1 2018 sample)
        psuffix = suffix + ("_v2" if proto == "cross" and args.cic2018_version == 2 else "")
        rec_path = ARTIFACT_DIR / f"openset_{proto}_records{psuffix}.json"
        sum_path = ARTIFACT_DIR / f"openset_{proto}_summary{psuffix}.json"
        records: list[dict] = []
        if args.resume and rec_path.exists():
            records = json.loads(rec_path.read_text(encoding="utf-8"))["records"]
        done = {(r["fold"], r["seed"]) for r in records}

        def sink(rec: dict) -> None:
            records.append(rec)
            _write(rec_path, {"meta": meta, "records": records})

        t0 = time.time()
        for seed in args.seeds:
            kw = dict(seeds=[seed], alpha=args.alpha, ae_kwargs=ae_kwargs, log=lambda m: print(m, flush=True))
            if proto == "loafo":
                fams = [f for f in P.LOAFO_FAMILIES if (f, seed) not in done]
                out = P.loafo(df17, families=fams, **kw) if fams else []
            elif proto == "temporal":
                out = [] if all((f, seed) in done for f in P.TEMPORAL_FOLDS) else P.temporal(df17, **kw)
                out = [r for r in out if (r["fold"], seed) not in done]
            elif proto == "cross_perday":
                df18 = load_cic2018(feature_columns(df17), version=args.cic2018_version)
                out = [r for r in P.cross_dataset_perday(df17, df18, **kw) if (r["fold"], seed) not in done]
            else:
                feats = feature_columns(df17)
                df18 = load_cic2018(feats, version=args.cic2018_version)
                out = P.cross_dataset(df17, df18, **kw)
                out = [r for r in out if (r["fold"], seed) not in done]
            for r in out:
                sink(r)
        summary = P.summarize(records)
        summary["meta"] = {**meta, "runtime_seconds": round(time.time() - t0, 1), "n_records": len(records)}
        _write(sum_path, summary)
        print(f"wrote {rec_path.name} and {sum_path.name} ({len(records)} records)", flush=True)


if __name__ == "__main__":
    main()
