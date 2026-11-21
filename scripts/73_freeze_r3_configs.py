"""Freeze the R3 model configurations and the reduced campaign design (R3 amendment PR-02).

The campaign runner (``scripts/67_r3_run.py --campaign``) refuses to start without this file.

Decision recorded here (docs/research/R3_AMENDMENT.md §2):
  * every model runs its **library-defaults arm** (R3_PROTOCOL §7 already requires that arm);
  * ``xgb_ref`` runs the exact v3 configuration (``research.openset.build_classifier``);
  * the tuned arm (30 Optuna trials per model and fold) is **not run**: equal budget of 0 trials for
    every model. Reason: 25-60 CPU-h estimated, outside the remaining schedule. This is a deviation
    and is reported as such; no hyper-parameter is ever chosen on unknown-family, target or test data.

Refuses to overwrite an existing frozen file (re-freezing would make earlier runs untraceable).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research.artifact_guard import R3_DIR, assert_writable  # noqa: E402

OUT = R3_DIR / "configs" / "frozen_configs.json"

DESIGN = {
    "seeds": [101, 102, 103, 104, 105],
    "protocols": ["loafo", "temporal", "cross_perday", "cross_loafo"],
    "windows": [2000],
    "pvalue_mode": "smoothed",
    "alpha": 0.01,
    "primary_metric": "TPR at matched 1 % benign FPR (threshold set on test benign; label 'oracle-matched')",
    "secondary_metric": "conformal recall at alpha = 1 % with smoothed p-values, realised FPR shown",
}

MODELS = {
    "xgb_ref": {"params": {}, "arm": "v3 reference configuration (research.openset.build_classifier)"},
    "dt": {"params": {}, "arm": "library defaults"},
    "rf": {"params": {}, "arm": "library defaults (n_estimators=300 fixed by protocol)"},
    "et": {"params": {}, "arm": "library defaults (n_estimators=300 fixed by protocol)"},
    "xgb": {"params": {}, "arm": "library defaults + early stopping on its own 10 % split"},
    "lgbm": {"params": {}, "arm": "library defaults + early stopping on its own 10 % split"},
    "catboost": {"params": {}, "arm": "library defaults + early stopping on its own 10 % split"},
}


def main() -> None:
    if OUT.exists():
        sys.exit(f"{OUT.relative_to(ROOT)} already exists; frozen configurations are never overwritten")
    assert_writable(OUT)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    body = {
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip(),
        "amendment": "docs/research/R3_AMENDMENT.md",
        "tuning": {"trials_per_model": 0, "deviation_from": "R3_PROTOCOL.md §7 (30 Optuna trials)",
                   "reason": "budget: 25-60 CPU-h estimated, outside the remaining schedule"},
        "design": DESIGN,
        "models": MODELS,
    }
    text = json.dumps(body, indent=1)
    OUT.write_text(text, encoding="utf-8")
    print(f"froze {len(MODELS)} configurations -> {OUT.relative_to(ROOT)} "
          f"(sha256 {hashlib.sha256(text.encode()).hexdigest()[:16]})")


if __name__ == "__main__":
    main()
