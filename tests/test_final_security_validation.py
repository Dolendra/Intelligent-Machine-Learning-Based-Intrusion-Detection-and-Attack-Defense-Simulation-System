"""P12 — Final security validation umbrella tests."""
from __future__ import annotations

import json
from pathlib import Path

from security.validation.p12_checks import run_all_p12_checks

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "final_security_validation_report.json"
DOCS = [
    ROOT / "docs" / "FINAL_SECURITY_VALIDATION.md",
    ROOT / "docs" / "SECURITY_MODEL.md",
    ROOT / "docs" / "PRODUCTION_READINESS.md",
]


def test_p12_docs_exist() -> None:
    for path in DOCS:
        assert path.is_file(), f"missing {path}"


def test_p12_all_categories_pass() -> None:
    report = run_all_p12_checks()
    failed = {
        name: [
            c
            for c in (cat.get("checks") or [])
            if c.get("status") != "PASS"
        ]
        for name, cat in (report.get("categories") or {}).items()
        if cat.get("status") != "PASS"
    }
    assert report["overall"] == "PASS", f"P12 FAIL: {json.dumps(failed, indent=2)}"


def test_p12_report_file_if_present() -> None:
    if not REPORT.is_file():
        return
    data = json.loads(REPORT.read_text(encoding="utf-8"))
    assert data.get("phase") == "P12"
    assert data.get("honesty", {}).get("live_firewall_edr") is False
