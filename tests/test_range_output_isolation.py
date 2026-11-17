"""R1b: Cyber Range runs created by the test suite must never write into committed evidence."""
from __future__ import annotations

import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_range_runs_dir_is_temporary_during_tests():
    from cyberrange import engine

    runs = Path(engine.RUNS_DIR).resolve()
    committed = (ROOT / "results" / "cyber_range" / "runs").resolve()
    assert runs != committed, "tests would write Cyber Range runs into results/ (committed evidence)"
    assert Path(tempfile.gettempdir()).resolve() in runs.parents, f"RUNS_DIR is not under the temp dir: {runs}"


def test_completed_range_run_lands_in_temp_dir():
    from cyberrange import engine

    committed = ROOT / "results" / "cyber_range" / "runs"
    before = {p.name for p in committed.glob("*.json")}
    try:
        run = engine.RangeRun(engine.RangeConfig(scenario="port_scan", seed=11).validate())
    except FileNotFoundError:  # models/pool unavailable in a minimal CI checkout
        return
    run.step(seconds=run.duration + 5)
    after = {p.name for p in committed.glob("*.json")}
    assert after == before, "a test run was written to results/cyber_range/runs"
    assert (Path(engine.RUNS_DIR) / f"{run.id}.json").exists(), "run record not written to the temp RUNS_DIR"
