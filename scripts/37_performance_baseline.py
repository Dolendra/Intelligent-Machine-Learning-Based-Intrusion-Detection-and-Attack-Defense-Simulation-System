#!/usr/bin/env python
"""P8 orchestrator — run offline baselines and write operating-envelope summary.

Does not start uvicorn (API bench is optional via --api).
Does not modify ML artifacts.

Usage:
  python scripts/37_performance_baseline.py
  python scripts/37_performance_baseline.py --quick
  python scripts/37_performance_baseline.py --api --api-base http://127.0.0.1:8000
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from performance.harness import RESULTS_DIR, git_commit, new_result, write_result
from performance.workloads import resource_snapshot


def _parse_json_blob(text: str) -> dict | None:
    text = (text or "").strip()
    if not text:
        return None
    # Prefer outermost object (first '{') — indented dumps break rfind-based parsing
    start = text.find("{")
    if start < 0:
        return None
    try:
        return json.loads(text[start:])
    except json.JSONDecodeError:
        # Fall back: try last complete-looking block
        try:
            return json.loads(text[text.rfind("{\n") :])
        except Exception:  # noqa: BLE001
            return None


def _run(script: str, extra: list[str] | None = None) -> dict:
    cmd = [sys.executable, str(ROOT / "scripts" / script), *(extra or [])]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    out = {
        "script": script,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-1500:],
    }
    out["parsed"] = _parse_json_blob(proc.stdout)
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="P8 baseline suite")
    p.add_argument("--quick", action="store_true", help="Smaller iteration counts")
    p.add_argument("--api", action="store_true", help="Also hit a running API")
    p.add_argument("--api-base", default="http://127.0.0.1:8000")
    args = p.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    quick = args.quick
    runs = []

    pred_n = "20" if quick else "50"
    runs.append(_run("30_benchmark_prediction.py", ["--n", pred_n, "--scenario", "normal"]))
    sizes = "100,500" if quick else "100,500,1000,5000"
    runs.append(_run("31_benchmark_batch.py", ["--sizes", sizes, "--repeats", "2" if quick else "3"]))
    shap_n = "5" if quick else "12"
    runs.append(_run("32_benchmark_shap.py", ["--n", shap_n]))
    runs.append(_run("36_benchmark_stages.py"))
    runs.append(_run("35_benchmark_db.py", ["--n", "15" if quick else "30"]))
    q_jobs = "10" if quick else "25"
    runs.append(_run("34_benchmark_queue.py", ["--jobs", q_jobs, "--flows-per-job", "5"]))
    runs.append(_run("34_benchmark_queue.py", ["--saturate", "--scenario", "saturation"]))

    if args.api:
        runs.append(
            _run(
                "33_benchmark_api.py",
                ["--base", args.api_base, "--requests", "20" if quick else "40", "--workers", "4"],
            )
        )

    # Build envelope summary from parsed outputs
    envelope = {
        "prediction": None,
        "batch": None,
        "shap_ratio": None,
        "queue": None,
        "db_approve_ok": None,
        "stages": None,
    }
    for r in runs:
        parsed = r.get("parsed") or {}
        script = r["script"]
        if script.startswith("30_") and parsed.get("metrics"):
            envelope["prediction"] = {
                "p50_ms": parsed["metrics"].get("p50_ms"),
                "p95_ms": parsed["metrics"].get("p95_ms"),
                "flows_per_sec": (parsed.get("throughput") or {}).get("flows_per_sec"),
                "error_rate": parsed.get("error_rate"),
            }
        if script.startswith("31_") and parsed.get("by_size"):
            envelope["batch"] = parsed["by_size"]
        if script.startswith("32_") and parsed.get("metrics"):
            envelope["shap_ratio"] = parsed["metrics"].get("shap_to_ml_p50_ratio")
        if script.startswith("34_") and parsed.get("throughput"):
            key = "queue_saturation" if "saturate" in str(r.get("stdout_tail") or "") or (
                parsed.get("throughput", {}).get("jobs_submit_errors", 0) or 0
            ) > 0 else "queue"
            # Prefer naming from configuration when present
            envelope[key] = parsed["throughput"]
            if key == "queue_saturation":
                envelope.setdefault("queue", parsed["throughput"])
        if script.startswith("35_") and parsed.get("metrics"):
            envelope["db_approve_ok"] = (parsed["metrics"].get("approve_outcomes") or {}).get("ok")
            # also accept outcomes nested under metrics from print payload
            if envelope["db_approve_ok"] is None and "approve_outcomes" in parsed.get("metrics", {}):
                envelope["db_approve_ok"] = parsed["metrics"]["approve_outcomes"].get("ok")
        if script.startswith("36_") and parsed.get("stages_ms"):
            envelope["stages"] = parsed["stages_ms"]

    summary = new_result(
        workload="operating_envelope",
        scenario="baseline",
        configuration={"quick": quick, "api": args.api, "commit": git_commit()},
        metrics={"envelope": envelope, "run_returncodes": {r["script"]: r["returncode"] for r in runs}},
        notes=[
            "Aggregated measured operating point for this host/config.",
            "Not a production SLA. Saturation behavior recorded separately when queue-full.",
            "DT/RF research baseline untouched.",
        ],
    )
    summary["resources"] = resource_snapshot()
    summary["child_runs"] = [
        {"script": r["script"], "returncode": r["returncode"], "wrote": (r.get("parsed") or {}).get("wrote")}
        for r in runs
    ]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = write_result(summary, name=f"operating_envelope_{stamp}.json")
    # Also write a stable pointer for docs
    latest = RESULTS_DIR / "operating_envelope_latest.json"
    latest.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({"wrote": str(path), "latest": str(latest), "envelope": envelope}, indent=2))
    # Fail only if prediction baseline failed (models missing)
    pred_rc = next((r["returncode"] for r in runs if r["script"].startswith("30_")), 0)
    return 0 if pred_rc == 0 else pred_rc


if __name__ == "__main__":
    raise SystemExit(main())
