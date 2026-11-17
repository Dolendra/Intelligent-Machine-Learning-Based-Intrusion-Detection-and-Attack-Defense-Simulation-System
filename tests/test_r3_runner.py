"""R3 Stage 0 runner safeguards (scripts/67_r3_run.py, research/r3_models.py, research/data.dedup_float32)."""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]


def _runner():
    spec = importlib.util.spec_from_file_location("r3run", ROOT / "scripts" / "67_r3_run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _frame(values, labels):
    df = pd.DataFrame(np.asarray(values, dtype=np.float32), columns=["a", "b"])
    df["family"] = labels
    df["fine_label"] = labels
    return df


def test_leakage_checker_rejects_shared_rows_and_unknown_in_training():
    R = _runner()
    chk = R.LeakageChecker()
    tr = _frame([[1, 2], [3, 4]], ["BENIGN", "DoS"])
    te = _frame([[5, 6], [1, 2]], ["BENIGN", "BENIGN"])   # [1, 2] BENIGN also in train
    with pytest.raises(R.LeakageError):
        chk({"protocol": "loafo", "fold": "x", "seed": 0, "unknown": []}, {"train": tr, "val": None, "test": te})
    tr2 = _frame([[1, 2], [3, 4]], ["BENIGN", "Bot"])
    with pytest.raises(R.LeakageError):
        chk({"protocol": "loafo", "fold": "Bot", "seed": 0, "unknown": ["Bot"]},
            {"train": tr2, "val": None, "test": _frame([[9, 9]], ["Bot"])})


def test_leakage_checker_cross_dataset_overlap_is_informational_but_warmup_overlap_is_fatal():
    R = _runner()
    chk = R.LeakageChecker()
    tr = _frame([[1, 2], [3, 4]], ["BENIGN", "DoS"])
    te = _frame([[1, 2], [7, 8]], ["BENIGN", "BENIGN"])
    chk({"protocol": "cross_perday", "fold": "d", "seed": 0, "unknown": []}, {"train": tr, "val": None, "test": te})
    assert chk.log[-1]["pass"] and chk.log[-1]["overlaps"]["train&test"] == 1
    with pytest.raises(R.LeakageError):
        chk({"protocol": "cross_perday", "fold": "d", "seed": 0, "unknown": []},
            {"train": tr, "val": None, "test": te, "warmup": _frame([[7, 8]], ["BENIGN"])})


def test_dedup_float32_removes_rows_identical_after_cast():
    from research.data import dedup_float32
    df = pd.DataFrame({"a": np.array([1.0, 1.0 + 1e-12, 2.0], dtype=np.float32), "fine_label": ["BENIGN"] * 3,
                       "family": ["BENIGN"] * 3})
    out, removed = dedup_float32(df)
    assert removed == 1 and len(out) == 2


def test_reference_model_is_the_v3_configuration():
    R = _runner()
    from research.openset import METHODS
    kw = R.model_kwargs("xgb_ref")
    assert kw == {"methods": METHODS}  # no custom classifier factory → research.openset.build_classifier


def test_campaign_refuses_without_approval():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "67_r3_run.py"), "--campaign"], capture_output=True, text=True,
                       cwd=ROOT)
    assert r.returncode != 0 and "not approved" in (r.stderr + r.stdout)


def test_our_evaluation_never_selects_auroc_direction_from_labels():
    """CLOSR's mean_auroc returns max(roc, 1 - roc); our metrics must use a fixed, pre-declared direction."""
    import re
    for path in [*(ROOT / "research").glob("*.py"), *(ROOT / "scripts").glob("6*.py")]:
        src = path.read_text(encoding="utf-8")
        assert not re.search(r"max\(\s*\w*roc\w*\s*,\s*1\s*-\s*\w*roc", src), f"label-chosen AUROC direction in {path.name}"
