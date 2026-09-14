"""P8 performance harness — reproducible JSON result records (not an SLA claim)."""
from __future__ import annotations

import json
import math
import os
import platform
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from ids_config import ROOT

RESULTS_DIR = ROOT / "results" / "performance"


def percentile(samples: list[float], p: float) -> float | None:
    if not samples:
        return None
    ordered = sorted(samples)
    if len(ordered) == 1:
        return round(ordered[0], 4)
    rank = (len(ordered) - 1) * p
    lo = math.floor(rank)
    hi = math.ceil(rank)
    if lo == hi:
        return round(ordered[lo], 4)
    w = rank - lo
    return round(ordered[lo] * (1 - w) + ordered[hi] * w, 4)


def latency_summary(samples_ms: list[float]) -> dict[str, Any]:
    if not samples_ms:
        return {
            "count": 0,
            "mean_ms": None,
            "p50_ms": None,
            "p95_ms": None,
            "p99_ms": None,
            "min_ms": None,
            "max_ms": None,
        }
    return {
        "count": len(samples_ms),
        "mean_ms": round(sum(samples_ms) / len(samples_ms), 4),
        "p50_ms": percentile(samples_ms, 0.50),
        "p95_ms": percentile(samples_ms, 0.95),
        "p99_ms": percentile(samples_ms, 0.99),
        "min_ms": round(min(samples_ms), 4),
        "max_ms": round(max(samples_ms), 4),
    }


def git_commit() -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(ROOT),
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip() or None
    except Exception:  # noqa: BLE001
        return None


def environment_snapshot_safe() -> dict[str, Any]:
    """Environment snapshot without optional dependencies."""
    snap: dict[str, Any] = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "aegis_env": os.getenv("AEGIS_ENV", "development"),
    }
    try:
        import psutil

        snap["cpu_percent_sample"] = psutil.cpu_percent(interval=0.05)
        vm = psutil.virtual_memory()
        snap["memory"] = {
            "total_mb": round(vm.total / (1024 * 1024), 1),
            "available_mb": round(vm.available / (1024 * 1024), 1),
            "percent": vm.percent,
        }
    except Exception:  # noqa: BLE001
        snap["cpu_percent_sample"] = None
        snap["memory"] = {"note": "psutil optional — not required for P8"}
    return snap


def new_result(
    *,
    workload: str,
    scenario: str,
    configuration: dict[str, Any] | None = None,
    metrics: dict[str, Any] | None = None,
    stages: dict[str, Any] | None = None,
    notes: list[str] | None = None,
    error_rate: float | None = None,
    throughput: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "p8.1",
        "experiment_id": f"perf-{uuid.uuid4().hex[:10]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "commit": git_commit(),
        "phase": "P8",
        "workload": workload,
        "scenario": scenario,  # normal | high | saturation | component
        "configuration": configuration or {},
        "environment": environment_snapshot_safe(),
        "metrics": metrics or {},
        "throughput": throughput or {},
        "stages_ms": stages or {},
        "error_rate": error_rate,
        "prototype_only": True,
        "not_a_capacity_claim": True,
        "ml_baseline_untouched": True,
        "notes": notes
        or [
            "Measured operating point on this host — not an SLA or multi-node capacity claim.",
            "Research DT/RF artifacts were not modified for P8.",
        ],
    }


def write_result(result: dict[str, Any], *, name: str | None = None) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    workload = result.get("workload", "bench")
    fname = name or f"{workload}_{stamp}_{result.get('experiment_id', 'x')}.json"
    path = RESULTS_DIR / fname
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return path


def time_calls(fn, n: int, *, warmup: int = 2) -> tuple[list[float], int]:
    """Return per-call latencies in ms and error count."""
    for _ in range(max(0, warmup)):
        try:
            fn()
        except Exception:  # noqa: BLE001
            pass
    samples: list[float] = []
    errors = 0
    for _ in range(max(1, n)):
        t0 = time.perf_counter()
        try:
            fn()
            samples.append((time.perf_counter() - t0) * 1000.0)
        except Exception:  # noqa: BLE001
            errors += 1
            samples.append((time.perf_counter() - t0) * 1000.0)
    return samples, errors


def flows_per_sec(n_flows: int, elapsed_s: float) -> float | None:
    if elapsed_s <= 0:
        return None
    return round(n_flows / elapsed_s, 3)
