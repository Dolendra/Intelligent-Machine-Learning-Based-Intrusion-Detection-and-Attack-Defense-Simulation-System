"""Feature selection, scaling, and transformation pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.preprocessing import LabelEncoder, StandardScaler

from ids_config import load_config, resolve_path
from ml.preprocessing.dataset import get_feature_columns

Task = Literal["binary", "multiclass"]


@dataclass
class FeatureBundle:
    feature_names: list[str]
    scaler: StandardScaler
    selector: SelectKBest | None
    selected_features: list[str]
    label_encoder: LabelEncoder
    binary_positive: str = "ATTACK"
    # Optional task-specific selector for attack-family classification.
    # Older artifacts omit this field — joblib load still works; we fall back to `selector`.
    multiclass_selector: SelectKBest | None = None
    selected_features_multiclass: list[str] = field(default_factory=list)

    def _selector_for(self, task: Task) -> SelectKBest | None:
        if task == "multiclass" and self.multiclass_selector is not None:
            return self.multiclass_selector
        return self.selector

    def selected_for(self, task: Task = "binary") -> list[str]:
        if task == "multiclass" and self.selected_features_multiclass:
            return list(self.selected_features_multiclass)
        return list(self.selected_features)

    def transform(self, df: pd.DataFrame, task: Task = "binary") -> np.ndarray:
        X = df[self.feature_names].astype(float).values
        X = self.scaler.transform(X)
        sel = self._selector_for(task)
        if sel is not None:
            X = sel.transform(X)
        return X

    def encode_labels(self, labels: pd.Series | np.ndarray) -> np.ndarray:
        return self.label_encoder.transform(labels)

    def decode_labels(self, encoded: np.ndarray) -> np.ndarray:
        return self.label_encoder.inverse_transform(encoded)

    def save(self, path: Path | str) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @staticmethod
    def load(path: Path | str) -> "FeatureBundle":
        bundle = joblib.load(path)
        # Backward compatibility for artifacts saved before dual selectors
        if getattr(bundle, "multiclass_selector", None) is None:
            bundle.multiclass_selector = None
        if not getattr(bundle, "selected_features_multiclass", None):
            bundle.selected_features_multiclass = list(bundle.selected_features)
        return bundle


def fit_feature_pipeline(
    train_df: pd.DataFrame,
    max_features: int | None = None,
    *,
    dual_selectors: bool | None = None,
) -> tuple[FeatureBundle, np.ndarray, np.ndarray, np.ndarray]:
    """Fit scaler + SelectKBest on training data only (no leakage).

    By default fits:
    - binary selector on is_attack
    - multiclass selector on Label (when dual_selectors enabled in config)
    Returns binary-selected X_train for stage-1 training.
    """
    cfg = load_config()
    max_features = max_features or cfg["features"]["max_features"]
    if dual_selectors is None:
        dual_selectors = bool(cfg.get("features", {}).get("dual_selectors", True))

    feature_names = get_feature_columns(train_df)
    X = train_df[feature_names].astype(float).values
    y_binary = train_df["is_attack"].values
    y_multi = train_df["Label"].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    k = min(max_features, X_scaled.shape[1])
    selector = SelectKBest(score_func=f_classif, k=k)
    X_selected = selector.fit_transform(X_scaled, y_binary)
    mask = selector.get_support()
    selected_features = [f for f, m in zip(feature_names, mask) if m]

    label_encoder = LabelEncoder()
    y_multi_enc = label_encoder.fit_transform(y_multi)

    multiclass_selector = None
    selected_features_multiclass = list(selected_features)
    if dual_selectors:
        multiclass_selector = SelectKBest(score_func=f_classif, k=k)
        multiclass_selector.fit(X_scaled, y_multi_enc)
        mask_m = multiclass_selector.get_support()
        selected_features_multiclass = [f for f, m in zip(feature_names, mask_m) if m]

    bundle = FeatureBundle(
        feature_names=feature_names,
        scaler=scaler,
        selector=selector,
        selected_features=selected_features,
        label_encoder=label_encoder,
        multiclass_selector=multiclass_selector,
        selected_features_multiclass=selected_features_multiclass,
    )
    return bundle, X_selected, y_binary, y_multi_enc


def transform_split(
    bundle: FeatureBundle,
    df: pd.DataFrame,
    task: Task = "binary",
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    X = bundle.transform(df, task=task)
    y_binary = df["is_attack"].values
    y_multi = bundle.encode_labels(df["Label"].values)
    return X, y_binary, y_multi


def default_bundle_path() -> Path:
    cfg = load_config()
    return resolve_path(cfg["models"]["output_dir"]) / "feature_bundle.joblib"
