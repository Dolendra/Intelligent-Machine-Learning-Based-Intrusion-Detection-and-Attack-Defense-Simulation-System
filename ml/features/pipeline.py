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
    multiclass_selector: SelectKBest | None = None
    selected_features_multiclass: list[str] = field(default_factory=list)
    # Attack-family encoder (BENIGN excluded). Older artifacts may omit this.
    attack_label_encoder: LabelEncoder | None = None

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

    def _family_encoder(self) -> LabelEncoder:
        if self.attack_label_encoder is not None:
            return self.attack_label_encoder
        return self.label_encoder

    def encode_labels(self, labels: pd.Series | np.ndarray) -> np.ndarray:
        """Encode full Label column (includes BENIGN) via the dataset label encoder."""
        return self.label_encoder.transform(labels)

    def decode_labels(self, encoded: np.ndarray) -> np.ndarray:
        return self.label_encoder.inverse_transform(encoded)

    def encode_attack_labels(self, labels: pd.Series | np.ndarray) -> np.ndarray:
        return self._family_encoder().transform(labels)

    def decode_attack_labels(self, encoded: np.ndarray) -> np.ndarray:
        return self._family_encoder().inverse_transform(encoded)

    def attack_class_names(self) -> list[str]:
        names = [str(c) for c in self._family_encoder().classes_]
        return [n for n in names if n != "BENIGN"]

    def save(self, path: Path | str) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @staticmethod
    def load(path: Path | str) -> "FeatureBundle":
        bundle = joblib.load(path)
        if getattr(bundle, "multiclass_selector", None) is None:
            bundle.multiclass_selector = None
        if not getattr(bundle, "selected_features_multiclass", None):
            bundle.selected_features_multiclass = list(bundle.selected_features)
        if getattr(bundle, "attack_label_encoder", None) is None:
            # Backward compat: derive attack-only encoder from full label_encoder if possible
            full = bundle.label_encoder
            attack_classes = [c for c in full.classes_ if str(c) != "BENIGN"]
            if attack_classes:
                enc = LabelEncoder()
                enc.fit(attack_classes)
                bundle.attack_label_encoder = enc
            else:
                bundle.attack_label_encoder = full
        return bundle


def fit_feature_pipeline(
    train_df: pd.DataFrame,
    max_features: int | None = None,
    *,
    dual_selectors: bool | None = None,
) -> tuple[FeatureBundle, np.ndarray, np.ndarray, np.ndarray]:
    """Fit scaler + SelectKBest on training data only (no leakage).

    Multiclass selector and attack_label_encoder are fit on **attack rows only**.
    Returns binary-selected X_train and binary y for stage-1 training.
    """
    cfg = load_config()
    max_features = max_features or cfg["features"]["max_features"]
    if dual_selectors is None:
        dual_selectors = bool(cfg.get("features", {}).get("dual_selectors", True))

    feature_names = get_feature_columns(train_df)
    X = train_df[feature_names].astype(float).values
    y_binary = train_df["is_attack"].values
    y_multi_all = train_df["Label"].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    k = min(max_features, X_scaled.shape[1])
    selector = SelectKBest(score_func=f_classif, k=k)
    X_selected = selector.fit_transform(X_scaled, y_binary)
    mask = selector.get_support()
    selected_features = [f for f, m in zip(feature_names, mask) if m]

    # Full encoder kept for dataset audits / backward compatibility
    label_encoder = LabelEncoder()
    label_encoder.fit(y_multi_all)

    attack_mask = train_df["is_attack"].to_numpy() == 1
    attack_labels = train_df.loc[attack_mask, "Label"]
    if attack_labels.empty:
        raise ValueError("Training set has no attack rows for multiclass stage")
    attack_label_encoder = LabelEncoder()
    attack_label_encoder.fit(attack_labels)
    y_attack_enc = attack_label_encoder.transform(attack_labels)

    multiclass_selector = None
    selected_features_multiclass = list(selected_features)
    if dual_selectors:
        multiclass_selector = SelectKBest(score_func=f_classif, k=k)
        multiclass_selector.fit(X_scaled[attack_mask], y_attack_enc)
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
        attack_label_encoder=attack_label_encoder,
    )
    # Third return kept for callers; prefer transform_attack_split for multiclass y
    return bundle, X_selected, y_binary, y_attack_enc


def transform_split(
    bundle: FeatureBundle,
    df: pd.DataFrame,
    task: Task = "binary",
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Transform a split. For multiclass task, encodes Label with attack encoder (BENIGN rows will error)."""
    X = bundle.transform(df, task=task)
    y_binary = df["is_attack"].values
    if task == "multiclass":
        y_multi = bundle.encode_attack_labels(df["Label"].values)
    else:
        # Binary path still returns attack-family encodings for attack rows only when possible
        try:
            y_multi = bundle.encode_attack_labels(df["Label"].values)
        except Exception:
            y_multi = bundle.label_encoder.transform(df["Label"].values)
    return X, y_binary, y_multi


def transform_attack_split(
    bundle: FeatureBundle,
    df: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    """Stage-2 transform: attack rows only, attack-family labels."""
    attacks = df[df["is_attack"] == 1].reset_index(drop=True)
    if attacks.empty:
        raise ValueError("No attack rows in split for multiclass transform")
    X = bundle.transform(attacks, task="multiclass")
    y = bundle.encode_attack_labels(attacks["Label"].values)
    return X, y, attacks


def default_bundle_path() -> Path:
    cfg = load_config()
    return resolve_path(cfg["models"]["output_dir"]) / "feature_bundle.joblib"
