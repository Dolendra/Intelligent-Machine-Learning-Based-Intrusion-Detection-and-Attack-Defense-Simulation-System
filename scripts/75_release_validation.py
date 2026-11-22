"""Phase 11 release validation: one versioned report that gathers every release gate.

    python scripts/75_release_validation.py [--tag rc1]

Gates:
  1. security checks (the same ``run_all_p12_checks`` as scripts/43, written to a NEW file; the historical
     reports/final_security_validation_report.json is not overwritten);
  2. research integrity: protected-artifact manifest unchanged, frozen v1.1 files identical to the tag;
  3. framework parity: the default framework pipeline equals the service decision on replay flows;
  4. R3 analysis present and its pre-registered validity check (A4) recorded.

Output: reports/release/release_validation_<date>[_<tag>].json (refuses to overwrite).
Exit code 0 when every gate passes.
"""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")


def isolate_environment() -> str:
    """Run every in-process check like the test suite does: AEGIS_ENV=test, a throwaway SQLite database and the
    test-only seed passwords, so the release check never starts the app against the developer database."""
    import os
    import tempfile

    db = Path(tempfile.mkdtemp(prefix="aegis_release_")) / "aegis_release.db"
    os.environ["AEGIS_ENV"] = "test"
    os.environ["DISABLE_RATE_LIMIT"] = "true"
    os.environ["IDS_DB_PATH"] = str(db)
    os.environ["IDS_DB_URL"] = "sqlite:///" + db.as_posix()
    os.environ["AEGIS_RANGE_RUNS_DIR"] = str(db.parent / "range_runs")
    from tests._seed_passwords import SEED_PASSWORDS

    for user, pw in SEED_PASSWORDS.items():
        os.environ[f"AEGIS_SEED_PASSWORD_{user.upper()}"] = pw
    from database.db import init_db

    init_db()
    return str(db)


def gate_security() -> dict:
    from security.validation.p12_checks import run_all_p12_checks

    rep = run_all_p12_checks()
    return {"status": rep["overall"], "categories": {k: v["status"] for k, v in rep["categories"].items()},
            "failed_checks": [{"category": k, "id": c.get("id"), "detail": c.get("detail")}
                              for k, v in rep["categories"].items() for c in v.get("checks", [])
                              if c.get("status") not in ("PASS", "SKIP", "INFO")]}


def gate_integrity() -> dict:
    from research.artifact_guard import frozen_v11_diff, load_manifest, verify_manifest

    bad, diff = verify_manifest(), frozen_v11_diff()
    return {"status": "PASS" if not bad and not diff else "FAIL", "protected_files": len(load_manifest()["files"]),
            "changed_or_missing": bad, "frozen_v11_differs_from_tag": diff}


def gate_framework_parity(n_per_family: int = 2) -> dict:
    import pandas as pd

    from backend.services import pipeline as svc
    from framework import AegisPipeline

    pool = pd.read_parquet(ROOT / "research_artifacts" / "replay" / "replay_pool.parquet")
    pick = pool.groupby("family", observed=True).head(n_per_family)
    drop = {"family", "fine_label", "day", "dataset"}
    rows = [{k: float(v) for k, v in r.items() if k not in drop} for _, r in pick.iterrows()]
    pipe = AegisPipeline.from_config(explainer=None)
    mismatches = 0
    for row, res in zip(rows, pipe.process(rows)):
        ref = svc.run_prediction(row, db=None, persist=False)
        dd = ref["detection_decision"]
        same = (res.detection.is_attack == ref["is_attack"] and res.detection.family == ref["attack_type"]
                and all(getattr(res.decision, k) == dd[k] for k in ("raises_incident", "source", "incident_label")))
        mismatches += not same
    return {"status": "PASS" if mismatches == 0 else "FAIL", "flows": len(rows), "mismatches": mismatches,
            "pipeline": pipe.describe()}


def gate_r3() -> dict:
    base = ROOT / "research_artifacts" / "r3" / "analysis"
    runs = sorted((p for p in base.glob("*") if (p / "hypotheses.json").exists()),
                  key=lambda p: p.stat().st_mtime) if base.exists() else []
    if not runs:
        return {"status": "FAIL", "reason": "no R3 analysis"}
    hyp = json.loads((runs[-1] / "hypotheses.json").read_text(encoding="utf-8"))
    return {"status": "PASS" if not hyp["A4"]["xgb_ref_failed"] else "FAIL", "analysis": runs[-1].name,
            "verdicts": {h: hyp[h]["verdict"] for h in ("A1", "A2", "A4", "A5", "A6", "A7")},
            "note": "PASS means the analysis exists and the reference model passed the validity check (A4); "
                    "verdicts are reported as they are, supported or not"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default=None)
    a = ap.parse_args()
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    out = ROOT / "reports" / "release" / f"release_validation_{day}{'_' + a.tag if a.tag else ''}.json"
    if out.exists():
        raise SystemExit(f"{out.relative_to(ROOT)} exists; release reports are never overwritten (use --tag)")
    isolated_db = isolate_environment()
    gates = {}
    for name, fn in (("security", gate_security), ("integrity", gate_integrity),
                     ("framework_parity", gate_framework_parity), ("r3_analysis", gate_r3)):
        try:
            gates[name] = fn()
        except Exception as exc:  # noqa: BLE001 — a crashing gate is a failing gate
            gates[name] = {"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}
        print(f"{name:18s} {gates[name]['status']}")
    report = {"generated_at": datetime.now(timezone.utc).isoformat(),
              "git_commit": subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip(),
              "python": platform.python_version(), "platform": platform.platform(),
              "environment": {"AEGIS_ENV": "test", "database": "throwaway SQLite (" + isolated_db + ")",
                              "note": "in-process checks run in the test configuration; production-mode startup "
                                      "with authentication is verified separately in Docker"},
              "overall": "PASS" if all(g["status"] == "PASS" for g in gates.values()) else "FAIL", "gates": gates}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print("overall:", report["overall"], "->", out.relative_to(ROOT))
    return 0 if report["overall"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
