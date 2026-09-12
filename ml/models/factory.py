"""Model factory and persistence for binary + multiclass IDS classifiers."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.tree import DecisionTreeClassifier

try:
    from xgboost import XGBClassifier

    HAS_XGB = True
except ImportError:  # pragma: no cover
    HAS_XGB = False


def build_model(name: str, random_state: int = 42) -> Any:
    name = name.lower().strip()
    if name in ("logistic_regression", "lr"):
        return LogisticRegression(max_iter=1000, class_weight="balanced", random_state=random_state)
    if name in ("decision_tree", "dt"):
        return DecisionTreeClassifier(max_depth=20, class_weight="balanced", random_state=random_state)
    if name in ("random_forest", "rf"):
        return RandomForestClassifier(
            n_estimators=80,
            max_depth=20,
            n_jobs=-1,
            class_weight="balanced_subsample",
            random_state=random_state,
        )
    if name in ("xgboost", "xgb", "gradient_boosting", "gb"):
        if HAS_XGB and name in ("xgboost", "xgb"):
            return XGBClassifier(
                n_estimators=120,
                max_depth=8,
                learning_rate=0.08,
                subsample=0.8,
                colsample_bytree=0.8,
                eval_metric="mlogloss",
                tree_method="hist",
                random_state=random_state,
                n_jobs=-1,
            )
        return GradientBoostingClassifier(random_state=random_state)
    if name in ("mlp", "neural_network"):
        return MLPClassifier(hidden_layer_sizes=(128, 64), max_iter=40, random_state=random_state)
    raise ValueError(f"Unknown model: {name}")


def save_model(model: Any, path: Path | str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)


def load_model(path: Path | str) -> Any:
    return joblib.load(path)
