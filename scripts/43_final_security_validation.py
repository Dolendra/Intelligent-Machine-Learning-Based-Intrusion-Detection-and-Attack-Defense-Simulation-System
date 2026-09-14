"""P12 — Final security validation runner (script 43; 42 is empirical mitigation).

Writes:
  reports/final_security_validation_report.json
  models/trained_models/final_security_validation_report.json (mirror)

Exit code 0 on overall PASS, 1 on FAIL.
"""
from __future__ import annotations

import json
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from security.validation.p12_checks import run_all_p12_checks


def _git_commit() -> str | None:
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL)
            .decode()
            .strip()
        )
    except Exception:
        return None


def _print_board(report: dict) -> None:
    print("P12 FINAL SECURITY VALIDATION")
    print("-" * 32)
    cats = report.get("categories") or {}
    width = max((len(k) for k in cats), default=20)
    for name, cat in cats.items():
        status = cat.get("status", "?")
        print(f"{name:<{width}}  {status}")
    print()
    print(f"Overall: {report.get('overall')}")


def main() -> int:
    report = run_all_p12_checks()
    report["git_commit"] = _git_commit()
    report["environment"] = {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
    }
    report["honesty"] = {
        "live_firewall_edr": False,
        "not_production_soc_claim": True,
        "empirical_script": "scripts/42_empirical_mitigation_experiment.py",
        "validation_script": "scripts/43_final_security_validation.py",
        "new_features_in_p12": False,
    }
    # Flatten artifact verification from model category if present
    model_checks = (report.get("categories") or {}).get("Model-serving safety", {}).get("checks") or []
    hash_check = next((c for c in model_checks if c.get("id") == "artifact_hashes"), None)
    report["artifact_hash_verification"] = {
        "status": (hash_check or {}).get("status", "UNKNOWN"),
        "detail": (hash_check or {}).get("detail"),
    }

    reports_dir = ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    out = reports_dir / "final_security_validation_report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    mirror_dir = ROOT / "models" / "trained_models"
    mirror_dir.mkdir(parents=True, exist_ok=True)
    mirror = mirror_dir / "final_security_validation_report.json"
    mirror.write_text(json.dumps(report, indent=2), encoding="utf-8")

    _print_board(report)
    print(json.dumps({"wrote": str(out), "mirror": str(mirror)}, indent=2))

    # Refresh docs status board snippet if FINAL doc exists (optional light touch)
    return 0 if report.get("overall") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
