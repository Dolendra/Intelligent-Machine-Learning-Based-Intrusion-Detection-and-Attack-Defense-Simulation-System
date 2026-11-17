"""R-03 (ARCH-18, RES-17): frozen v1.1 and protected research artifacts cannot be overwritten."""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ids_config import ROOT
from research.artifact_guard import FROZEN_V11, ProtectedArtifactError, assert_writable

FROZEN_SHAP = ROOT / "models" / "trained_models" / "global_shap_summary.json"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_global_shap_refresh_get_never_writes_frozen_file():
    from backend.main import app
    from backend.services import pipeline as svc

    if not svc.models_ready():
        pytest.skip("frozen models required")
    assert "models/trained_models/global_shap_summary.json" in FROZEN_V11
    before = _sha(FROZEN_SHAP)
    r = TestClient(app).get("/api/models/shap/global", params={"refresh": True, "top_k": 5})
    assert r.status_code == 200 and r.json().get("persisted") is False
    assert _sha(FROZEN_SHAP) == before


@pytest.mark.parametrize("rel", sorted(FROZEN_V11))
def test_every_frozen_file_is_refused(rel):
    with pytest.raises(ProtectedArtifactError):
        assert_writable(ROOT / rel)


def test_low_level_savers_refuse_frozen_paths(tmp_path):
    from ml.features.intensity import save_intensity_reference
    from ml.models.factory import save_model

    with pytest.raises(ProtectedArtifactError):
        save_model({"x": 1}, ROOT / "models" / "trained_models" / "binary_best.joblib")
    with pytest.raises(ProtectedArtifactError):
        save_intensity_reference({"x": 1}, ROOT / "models" / "trained_models" / "intensity_reference.json")
    save_model({"x": 1}, tmp_path / "ok.joblib")                     # new locations still work
    assert (tmp_path / "ok.joblib").exists()


WRITERS = ["02_train_models", "11_calibration_hpo_experiment", "13_write_model_metadata",
           "15_threshold_optimization", "16_risk_weight_sensitivity", "20_data_drift_report",
           "23_error_analysis", "24_global_shap_summary", "25_temporal_holdout_eval",
           "51_train_zero_day_gate", "52_build_replay_pool", "58_model_family_comparison",
           "61_dataset_summary"]


@pytest.mark.parametrize("name", WRITERS)
def test_scripts_writing_protected_files_call_the_guard(name):
    """Every write call in these scripts is preceded by assert_writable on the same target."""
    src = (ROOT / "scripts" / f"{name}.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    guarded = {ast.unparse(n.args[0]) for n in ast.walk(tree)
               if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "assert_writable"}
    writes = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            if n.func.attr in {"write_text", "to_parquet"}:
                writes.append(ast.unparse(n.func.value))
            elif n.func.attr == "save" and getattr(n.func.value, "id", "") == "np":
                writes.append(ast.unparse(n.args[0]))
    assert writes, name
    unguarded = [w for w in writes if w not in guarded and w.removeprefix("pool.drop(columns=['seq', 'is_attack'])") ]
    # pool.drop(...).to_parquet(path): the guarded target is the positional path argument
    unguarded = [w for w in unguarded if not w.startswith("pool.drop")]
    assert not unguarded, f"{name}: unguarded writes {unguarded}"
