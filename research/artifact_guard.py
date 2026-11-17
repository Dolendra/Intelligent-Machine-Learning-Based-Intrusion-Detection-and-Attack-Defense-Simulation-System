"""Protection of historical research artifacts and the frozen v1.1 baseline (R3 Stage 0).

Two layers:

1. **Prevention.** Experiment writers call :func:`assert_writable` before writing. It refuses any
   path listed in the protected manifest, so a re-run can never overwrite a historical result —
   re-runs must use a new name (``--tag``) or the ``research_artifacts/r3/`` tree.
2. **Detection.** ``research_artifacts/PROTECTED_MANIFEST.json`` stores the SHA-256 of every
   committed research artifact; ``tests/test_artifact_integrity.py`` fails if any of them changes.
   The frozen v1.1 files are additionally compared with the git tag ``v1.1-research``.

Build or extend the manifest (never silently): ``python -m research.artifact_guard --build``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "research_artifacts" / "PROTECTED_MANIFEST.json"
FROZEN_TAG = "v1.1-research"
# v1.1 model, preprocessing, threshold and report files that must stay byte-identical to the tag.
# (cross_dataset_status.json, experiment_index.json and model_comparison.md are status documents
#  that were updated in the v3 work and are intentionally not part of the frozen set.)
FROZEN_V11 = [
    "models/trained_models/binary_best.joblib",
    "models/trained_models/multiclass_best.joblib",
    "models/trained_models/feature_bundle.joblib",
    "models/trained_models/model_metadata.json",
    "models/trained_models/training_report.json",
    "models/trained_models/threshold_operating_point.json",
    "models/trained_models/threshold_sweep.json",
    "models/trained_models/calibration_hpo_experiment.json",
    "models/trained_models/intensity_reference.json",
    "models/trained_models/shap_background.npy",
    "models/trained_models/global_shap_summary.json",
    "models/trained_models/demo_flows.json",
    "models/trained_models/drift_report.json",
    "models/trained_models/error_analysis_report.json",
    "models/trained_models/risk_weight_sensitivity.json",
    "models/trained_models/temporal_holdout_report.json",
]
R3_DIR = ROOT / "research_artifacts" / "r3"


class ProtectedArtifactError(RuntimeError):
    pass


def _rel(path: Path) -> str:
    return Path(path).resolve().relative_to(ROOT).as_posix()


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_manifest() -> dict:
    if not MANIFEST.exists():
        return {"files": {}}
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def protected_paths() -> set[str]:
    return set(load_manifest()["files"]) | set(FROZEN_V11)


def assert_writable(path: Path) -> None:
    """Raise if ``path`` is a protected historical artifact or frozen v1.1 file."""
    try:
        rel = _rel(path)
    except ValueError:  # outside the repository (e.g. a temp dir) — not ours to protect
        return
    if rel in protected_paths():
        raise ProtectedArtifactError(
            f"refusing to overwrite protected artifact {rel}; write re-runs under a new name "
            f"(--tag) or under research_artifacts/r3/")


def verify_manifest() -> dict[str, str]:
    """Return {path: problem} for every protected artifact that is missing or changed."""
    bad = {}
    for rel, meta in load_manifest()["files"].items():
        p = ROOT / rel
        if not p.exists():
            bad[rel] = "missing"
        elif sha256(p) != meta["sha256"]:
            bad[rel] = "changed"
    return bad


def frozen_v11_diff() -> list[str]:
    """Frozen v1.1 files that differ from the git tag (empty list = unchanged)."""
    out = []
    for rel in FROZEN_V11:
        r = subprocess.run(["git", "diff", "--quiet", FROZEN_TAG, "--", rel], cwd=ROOT)
        if r.returncode != 0:
            out.append(rel)
    return out


def _committed_artifacts() -> list[str]:
    files = subprocess.check_output(["git", "ls-files", "research_artifacts"], cwd=ROOT, text=True).split()
    return sorted(f for f in files if not f.startswith("research_artifacts/r3/")
                  and f != _rel(MANIFEST) and not f.startswith("research_artifacts/figures/"))


def build(reason: str) -> dict:
    """Add every committed research artifact to the manifest. Existing entries are never changed."""
    man = load_manifest()
    files = man.setdefault("files", {})
    added = []
    for rel in _committed_artifacts():
        if rel not in files:
            files[rel] = {"sha256": sha256(ROOT / rel), "added": datetime.now(timezone.utc).date().isoformat()}
            added.append(rel)
    man.setdefault("history", []).append({"at": datetime.now(timezone.utc).isoformat(), "reason": reason,
                                          "added": added})
    man["note"] = ("Historical research artifacts. Never overwrite; re-runs use new names or research_artifacts/r3/. "
                   "Entries are only ever added (python -m research.artifact_guard --build --reason ...).")
    MANIFEST.write_text(json.dumps(man, indent=1), encoding="utf-8")
    return man


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--reason", default="")
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    if a.build:
        if not a.reason:
            ap.error("--build needs --reason")
        m = build(a.reason)
        print(f"manifest: {len(m['files'])} protected files; added {len(m['history'][-1]['added'])}")
    if a.verify or not a.build:
        print("changed/missing:", verify_manifest() or "none")
        print("frozen v1.1 differing from tag:", frozen_v11_diff() or "none")
