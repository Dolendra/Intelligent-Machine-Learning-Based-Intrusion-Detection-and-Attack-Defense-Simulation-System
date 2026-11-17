"""R3 runner (Stage 0: readiness only — full campaign NOT approved).

Modes
  --plan            print the run matrix and the cost estimate (no computation)
  --smoke           tiny caps, pilot seed 0, 2 LOAFO folds + 2 per-day days, every requested model
  --pilot-timing    one full-size LOAFO fold (DoS held out), pilot seed 0: fit/score time and peak RSS per model
  --campaign        the confirmatory runs (seeds 101-110). Refuses to start unless --i-have-approval is given.

Every run, in every mode:
  * models from research/r3_models.py, each evaluated standalone ("Closed-set (sup only)", arm B) and inside
    Aegis-OSR (Fisher / max / omnibus, arm C); arm A (native argmax) is recoverable from the score dumps;
    ``xgb_ref`` uses the full v3 method set and is the regression-gated reference;
  * leakage checks on every split (row hashes over features + fine label; held-out families absent from
    training-side splits; warm-up ∩ evaluation = ∅) — a failure raises and the record is not written;
  * per-flow score dumps for every record and adaptation variant;
  * outputs only under research_artifacts/r3/runs/<run-name>/ (protected paths are refused).

Use the isolated environment (LightGBM/CatBoost are not installed in the main one):
    .venvs/r3-cpu/Scripts/python.exe scripts/67_r3_run.py --smoke --models xgb_ref dt rf et xgb lgbm catboost
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import subprocess
import sys
import threading
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
from research.artifact_guard import R3_DIR, assert_writable  # noqa: E402
from research.data import dedup_float32, feature_columns, load_cic2017, load_cic2018  # noqa: E402
from research.openset import METHODS, PROPOSED, MethodSpec  # noqa: E402
from research.r3_models import MODELS, factory  # noqa: E402
from research.scoredump import ScoreDump  # noqa: E402

CONFIRMATORY_SEEDS = list(range(101, 111))
PILOT_SEED = 0
R3_METHODS = {
    "Closed-set (sup only)": MethodSpec(("sup",)),
    PROPOSED: MethodSpec(("sup", "knn"), "fisher", "proposed"),
    "Aegis-OSR w/ max fusion": MethodSpec(("sup", "knn"), "max", "ablation"),
    "Aegis-OSR w/ omnibus fusion": MethodSpec(("sup", "knn"), "omnibus", "ablation"),
    "kNN distance": MethodSpec(("knn",)),
}


class LeakageError(RuntimeError):
    pass


def _row_hash(df: pd.DataFrame, feats: list[str]) -> set:
    cols = feats + (["fine_label"] if "fine_label" in df.columns else [])
    return set(pd.util.hash_pandas_object(df[cols].astype({c: "float32" for c in feats}), index=False).to_numpy())


class LeakageChecker:
    def __init__(self) -> None:
        self.log: list[dict] = []

    def __call__(self, key: dict, splits: dict) -> None:
        frames = {k: v for k, v in splits.items() if v is not None and len(v)}
        feats = feature_columns(frames["train"])
        hashes = {k: _row_hash(v, feats) for k, v in frames.items()}
        res = {"key": key, "sizes": {k: int(len(v)) for k, v in frames.items()}, "overlaps": {}, "unknown_in_training": {}}
        names = list(frames)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                if {a, b} == {"warmup", "warmup_oracle"}:
                    continue
                res["overlaps"][f"{a}&{b}"] = len(hashes[a] & hashes[b])
        for side in [x for x in ("train", "val") if x in frames]:
            fam = frames[side]["family"].astype(str)
            res["unknown_in_training"][side] = int(fam.isin(key.get("unknown", [])).sum())
        # cross-network: a 2018 flow may equal a 2017 training flow feature-for-feature (different captures);
        # that is recorded, not leakage. Within one dataset every overlap is fatal.
        cross = key.get("protocol") == "cross_perday"
        informational = {f"{a}&{b}" for a in ("train", "val") for b in ("test", "warmup")} if cross else set()
        res["informational_overlaps"] = sorted(informational & set(res["overlaps"]))
        bad = ({k: v for k, v in res["overlaps"].items() if v and k not in informational}
               | {k: v for k, v in res["unknown_in_training"].items() if v})
        res["pass"] = not bad
        self.log.append(res)
        if bad:
            raise LeakageError(f"{key}: {bad}")


class PeakRSS:
    def __init__(self) -> None:
        import psutil
        self.p, self.peak, self._stop = psutil.Process(), 0, threading.Event()

    def __enter__(self):
        def run():
            while not self._stop.is_set():
                self.peak = max(self.peak, self.p.memory_info().rss)
                time.sleep(0.1)
        self.t = threading.Thread(target=run, daemon=True)
        self.t.start()
        return self

    def __exit__(self, *a):
        self._stop.set()
        self.t.join()


def _exp():
    spec = importlib.util.spec_from_file_location("exp50", ROOT / "scripts" / "50_openset_experiments.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _versions() -> dict:
    out = {"python": platform.python_version(), "executable": sys.executable}
    for m in ("numpy", "pandas", "sklearn", "xgboost", "lightgbm", "catboost", "torch", "optuna"):
        try:
            out[m] = __import__(m).__version__
        except ImportError:
            out[m] = None
    return out


def model_kwargs(name: str) -> dict:
    if name == "xgb_ref":
        return {"methods": METHODS}  # exactly the v3 configuration (regression-gated)
    return {"clf_factory": factory(name), "methods": R3_METHODS}


def run(mode: str, models: list[str], protocols: list[str], seeds: list[int], out: Path,
        loafo_folds: list[str] | None = None, perday_days: list[str] | None = None) -> dict:
    exp = _exp()
    out.mkdir(parents=True, exist_ok=True)
    # R3 protocol change (Stage 0 finding): de-duplicate at float32 precision before any split
    df17, removed17 = dedup_float32(load_cic2017())
    df18, removed18 = (dedup_float32(load_cic2018(feature_columns(df17), version=2)) if "cross_perday" in protocols
                       else (None, 0))
    if df18 is not None and perday_days:
        df18 = df18[df18["day"].astype(str).isin(perday_days)]
    print(f"float32 de-duplication removed {removed17:,} CICIDS2017 and {removed18:,} CSE-CIC-IDS2018 rows", flush=True)
    leak = LeakageChecker()
    summary: dict = {"mode": mode, "models": {}, "started": datetime.now(timezone.utc).isoformat(),
                     "dedup_float32_removed": {"cic2017": removed17, "cic2018": removed18}}
    for name in models:
        for proto in protocols:
            dump = ScoreDump(out / "scores" / name)
            recs: list[dict] = []
            t0 = time.time()
            with PeakRSS() as mem:
                for seed in seeds:
                    kw = dict(seeds=[seed], alpha=0.01, ae_kwargs={"epochs": 25}, log=lambda m: print("   ", m, flush=True),
                              dump=dump, model_kwargs=model_kwargs(name), on_split=leak)
                    got = (P.loafo(df17, families=loafo_folds or P.LOAFO_FAMILIES, **kw) if proto == "loafo"
                           else P.cross_dataset_perday(df17, df18, **kw))
                    for r in got:
                        r["evidence_model"] = name
                    recs += got
                    path = out / f"{proto}__{name}_records.json"
                    assert_writable(path)
                    exp._write(path, {"meta": {"mode": mode, "versions": _versions()}, "records": recs})
            summary["models"].setdefault(name, {})[proto] = {
                "records": len(recs), "wall_seconds": round(time.time() - t0, 1),
                "fit_seconds": [r.get("fit_seconds") for r in recs], "peak_rss_gb": round(mem.peak / 2**30, 2),
                "score_ms_per_1k_flows": [r.get("score_ms_per_1k_flows") for r in recs],
            }
            print(f"== {name}/{proto}: {len(recs)} records, {time.time() - t0:.0f}s, peak RSS {mem.peak / 2**30:.1f} GB",
                  flush=True)
    summary["leakage"] = {"checked_splits": len(leak.log), "all_pass": all(x["pass"] for x in leak.log),
                          "max_overlap": max((v for x in leak.log for v in x["overlaps"].values()), default=0)}
    summary["versions"] = _versions()
    summary["git_commit"] = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    (out / "leakage_report.json").write_text(json.dumps(leak.log, indent=1, default=str), encoding="utf-8")
    (out / "run_summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    return summary


def plan(models: list[str], timing: Path) -> None:
    t = json.loads(timing.read_text(encoding="utf-8")) if timing.exists() else None
    n = {"loafo": 6, "cross_perday": 1}  # fits per seed (per-day trains once per seed)
    print("R3 confirmatory matrix (seeds 101-110):")
    tot = 0.0
    for m in models:
        for proto, fits in n.items():
            s = None
            if t and m in t["models"] and "loafo" in t["models"][m]:
                s = float(np.mean(t["models"][m]["loafo"]["fit_seconds"]))
            hrs = None if s is None else s * fits * 10 / 3600
            tot += hrs or 0
            print(f"  {m:9s} {proto:12s} {fits * 10:3d} fits  " + (f"≈ {hrs:5.1f} CPU-h (fit only)" if hrs else "cost: run --pilot-timing"))
    print(f"total ≈ {tot:.1f} CPU-h for measured models (evaluation and per-day adaptation add ~40-60 s per record)")


def main() -> None:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--plan", action="store_true")
    g.add_argument("--smoke", action="store_true")
    g.add_argument("--pilot-timing", action="store_true")
    g.add_argument("--campaign", action="store_true")
    ap.add_argument("--i-have-approval", action="store_true", help="required for --campaign")
    ap.add_argument("--models", nargs="+", default=list(MODELS), choices=list(MODELS))
    ap.add_argument("--protocols", nargs="+", default=["loafo", "cross_perday"], choices=["loafo", "cross_perday"])
    ap.add_argument("--name", default=None)
    a = ap.parse_args()
    timing = R3_DIR / "pilots" / "model_timing" / "run_summary.json"
    if a.plan:
        plan(a.models, timing)
        return
    if a.campaign and not a.i_have_approval:
        sys.exit("R3 campaign not approved: refusing to start (R3_PROTOCOL.md §13).")
    if a.smoke:
        P.TRAIN_CAPS = {"BENIGN": 20_000, "_attack": 3_000}
        P.VAL_CAPS = {"BENIGN": 6_000, "_attack": 800}
        P.TEST_CAPS = {"BENIGN": 10_000, "_attack": 2_000}
        P.PERDAY_TEST_CAPS = {"BENIGN": 3_000, "_attack": 1_000}
        s = run("smoke", a.models, a.protocols, [PILOT_SEED], R3_DIR / "runs" / (a.name or "smoke"),
                loafo_folds=["DoS", "Bot"], perday_days=["2018-02-14", "2018-02-16"])
    elif a.pilot_timing:
        s = run("pilot-timing", a.models, ["loafo"], [PILOT_SEED], R3_DIR / "pilots" / (a.name or "model_timing"),
                loafo_folds=["DoS"])
    else:
        s = run("campaign", a.models, a.protocols, CONFIRMATORY_SEEDS, R3_DIR / "runs" / (a.name or "campaign"))
    print(json.dumps({"leakage": s["leakage"], "models": {m: {p: {k: v[k] for k in ("records", "wall_seconds", "peak_rss_gb")}
                                                             for p, v in d.items()} for m, d in s["models"].items()}}, indent=1))


if __name__ == "__main__":
    main()
