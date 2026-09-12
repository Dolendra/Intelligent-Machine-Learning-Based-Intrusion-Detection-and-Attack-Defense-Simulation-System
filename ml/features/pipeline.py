"""Feature selection, scaling, and transformation pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.preprocessing import LabelEncoder, StandardScaler

from ids_config import load_config, resolve_path
from ml.preprocessing.dataset import get_feature_columns


@dataclass
class FeatureBundle:
    feature_names: list[str]
    scaler: StandardScaler
    selector: SelectKBest | None
    selected_features: list[str]
    label_encoder: LabelEncoder
    binary_positive: str = "ATTACK"

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        X = df[self.feature_names].astype(float).values
        X = self.scaler.transform(X)
        if self.selector is not None:
            X = self.selector.transform(X)
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
        return joblib.load(path)


def fit_feature_pipeline(
    train_df: pd.DataFrame,
    max_features: int | None = None,
) -> tuple[FeatureBundle, np.ndarray, np.ndarray, np.ndarray]:
    """Fit scaler + optional SelectKBest on training data only (no leakage)."""
    cfg = load_config()
    max_features = max_features or cfg["features"]["max_features"]

    feature_names = get_feature_columns(train_df)
    X = train_df[feature_names].astype(float).values
    y_binary = train_df["is_attack"].values
    y_multi = train_df["Label"].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    k = min(max_features, X_scaled.shape[1])
    selector = SelectKBest(score_func=f_classif, k=k)
    # Use binary target for feature relevance to intrusion vs benign
    # Replace any NaN scores from constant columns
    X_selected = selector.fit_transform(X_scaled, y_binary)
    mask = selector.get_support()
    selected_features = [f for f, m in zip(feature_names, mask) if m]

    label_encoder = LabelEncoder()
    label_encoder.fit(y_multi)

    bundle = FeatureBundle(
        feature_names=feature_names,
        scaler=scaler,
        selector=selector,
        selected_features=selected_features,
        label_encoder=label_encoder,
    )
    return bundle, X_selected, y_binary, label_encoder.transform(y_multi)


def transform_split(bundle: FeatureBundle, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    X = bundle.transform(df)
    y_binary = df["is_attack"].values
    y_multi = bundle.encode_labels(df["Label"].values)
    return X, y_binary, y_multi


def default_bundle_path() -> Path:
    cfg = load_config()
    return resolve_path(cfg["models"]["output_dir"]) / "feature_bundle.joblib"
