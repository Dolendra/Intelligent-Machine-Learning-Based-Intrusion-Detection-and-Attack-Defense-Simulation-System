"""P8 performance suite — harness shape + light smoke (not heavy benches in CI)."""
from __future__ import annotations

import json
from pathlib import Path

from performance.harness import (
    RESULTS_DIR,
    latency_summary,
    new_result,
    percentile,
    write_result,
)


def test_percentile_and_latency_summary():
    assert percentile([1, 2, 3, 4, 5], 0.5) == 3
    summary = latency_summary([10.0, 20.0, 30.0, 40.0, 100.0])
    assert summary["count"] == 5
    assert summary["p50_ms"] == 30.0
    assert summary["p95_ms"] is not None
    assert summary["max_ms"] == 100.0


def test_result_schema_and_write(tmp_path, monkeypatch):
    monkeypatch.setattr("performance.harness.RESULTS_DIR", tmp_path)
    result = new_result(
        workload="unit_harness",
        scenario="component",
        configuration={"n": 1},
        metrics=latency_summary([1.5, 2.5]),
        throughput={"flows_per_sec": 100.0},
        error_rate=0.0,
    )
    assert result["schema_version"] == "p8.1"
    assert result["phase"] == "P8"
    assert result["prototype_only"] is True
    assert result["ml_baseline_untouched"] is True
    assert result["not_a_capacity_claim"] is True
    path = write_result(result, name="unit_harness.json")
    assert path.exists()
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["workload"] == "unit_harness"
    assert "environment" in loaded
    assert "timestamp" in loaded


def test_results_dir_constant():
    assert RESULTS_DIR.name == "performance"
    assert "results" in str(RESULTS_DIR)


def test_batch_script_exists_and_api_cap_documented():
    root = Path(__file__).resolve().parents[1]
    batch = (root / "scripts" / "31_benchmark_batch.py").read_text(encoding="utf-8")
    assert "api_batch_cap" in batch or "500" in batch
    assert (root / "scripts" / "37_performance_baseline.py").exists()
    assert (root / "scripts" / "30_benchmark_prediction.py").exists()
    assert (root / "scripts" / "32_benchmark_shap.py").exists()
    assert (root / "scripts" / "34_benchmark_queue.py").exists()
    assert (root / "scripts" / "35_benchmark_db.py").exists()
