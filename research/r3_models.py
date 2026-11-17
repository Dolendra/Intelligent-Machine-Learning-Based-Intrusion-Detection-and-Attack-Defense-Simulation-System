"""R3 supervised evidence models (R3_PROTOCOL.md §1, §7).

Each entry builds a (K+1)-class classifier with ``fit(X, y, sample_weight)`` and ``predict_proba(X)``,
so it can be used standalone or as Aegis-OSR's supervised evidence (``AegisOSR(clf_factory=...)``).

* ``xgb_ref`` is the exact v3 configuration (``research.openset.build_classifier``) and must reproduce
  the committed results; every other model is new.
* Models with early stopping carve their own stratified early-stop split (10 %) out of the *training*
  data they are given, so C1/C2 calibration and test data are never seen by model selection.
* LightGBM and CatBoost are imported lazily: they are installed only in the isolated ``.venvs/r3-*``
  environments, never in the main project environment.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier

from research.openset import build_classifier

ES_FRACTION = 0.10
ES_ROUNDS = 50
MAX_ROUNDS = 2000


def _es_split(X, y, w, seed):
    idx = np.arange(len(y))
    tr, es = train_test_split(idx, test_size=ES_FRACTION, random_state=seed, stratify=y)
    return (X[tr], y[tr], None if w is None else w[tr]), (X[es], y[es])


class _EarlyStopped:
    """Common wrapper: fit on 90 % of the training data, stop on the held-out 10 % (multi-logloss)."""

    def __init__(self, kind: str, n_classes: int, seed: int, params: dict) -> None:
        self.kind, self.n_classes, self.seed, self.params = kind, n_classes, seed, dict(params)
        self.best_iteration_: int | None = None

    def fit(self, X, y, sample_weight=None):
        (Xt, yt, wt), (Xe, ye) = _es_split(np.asarray(X), np.asarray(y), sample_weight, self.seed)
        if self.kind == "xgb":
            from xgboost import XGBClassifier
            self.m_ = XGBClassifier(n_estimators=MAX_ROUNDS, early_stopping_rounds=ES_ROUNDS, tree_method="hist",
                                    objective="multi:softprob", num_class=self.n_classes, eval_metric="mlogloss",
                                    n_jobs=-1, random_state=self.seed, **self.params)
            self.m_.fit(Xt, yt, sample_weight=wt, eval_set=[(Xe, ye)], verbose=False)
            self.best_iteration_ = int(self.m_.best_iteration)
        elif self.kind == "lgbm":
            import lightgbm as lgb
            self.m_ = lgb.LGBMClassifier(objective="multiclass", num_class=self.n_classes, n_estimators=MAX_ROUNDS,
                                         random_state=self.seed, deterministic=True, force_row_wise=True, n_jobs=-1,
                                         verbose=-1, **self.params)
            self.m_.fit(Xt, yt, sample_weight=wt, eval_set=[(Xe, ye)], eval_metric="multi_logloss",
                        callbacks=[lgb.early_stopping(ES_ROUNDS, verbose=False)])
            self.best_iteration_ = int(self.m_.best_iteration_)
        elif self.kind == "catboost":
            from catboost import CatBoostClassifier
            self.m_ = CatBoostClassifier(iterations=MAX_ROUNDS, loss_function="MultiClass", random_seed=self.seed,
                                         od_type="Iter", od_wait=ES_ROUNDS, verbose=False, thread_count=-1,
                                         allow_writing_files=False, **self.params)
            self.m_.fit(Xt, yt, sample_weight=wt, eval_set=(Xe, ye), use_best_model=True)
            self.best_iteration_ = int(self.m_.get_best_iteration())
        else:
            raise ValueError(self.kind)
        return self

    def predict_proba(self, X):
        return np.asarray(self.m_.predict_proba(X), dtype=np.float64)


@dataclass(frozen=True)
class ModelSpec:
    name: str
    build: Callable[[int, int, dict], Any]       # (n_classes, seed, params) -> classifier
    defaults: dict = field(default_factory=dict)  # library-defaults arm (plus fixed protocol settings)
    space: Callable[[Any], dict] | None = None    # optuna trial -> params (R3_PROTOCOL §7); None = not tuned
    needs: tuple[str, ...] = ()                   # optional packages


def _space_tree(t):
    return {"max_depth": t.suggest_categorical("max_depth", [4, 8, 12, 16, 20, 30, 40, None]),
            "min_samples_leaf": t.suggest_int("min_samples_leaf", 1, 200, log=True),
            "criterion": t.suggest_categorical("criterion", ["gini", "entropy"])}


def _space_forest(t):
    return {"max_features": t.suggest_categorical("max_features", ["sqrt", 0.3, 0.5]),
            "min_samples_leaf": t.suggest_int("min_samples_leaf", 1, 50, log=True),
            "max_depth": t.suggest_categorical("max_depth", [None, 20, 40])}


def _space_xgb(t):
    return {"learning_rate": t.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "max_depth": t.suggest_int("max_depth", 3, 12),
            "min_child_weight": t.suggest_float("min_child_weight", 1, 20, log=True),
            "subsample": t.suggest_float("subsample", 0.5, 1.0),
            "colsample_bytree": t.suggest_float("colsample_bytree", 0.5, 1.0),
            "reg_lambda": t.suggest_float("reg_lambda", 1e-3, 10, log=True)}


def _space_lgbm(t):
    return {"learning_rate": t.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "num_leaves": t.suggest_int("num_leaves", 15, 255, log=True),
            "min_child_samples": t.suggest_int("min_child_samples", 5, 200, log=True),
            "colsample_bytree": t.suggest_float("colsample_bytree", 0.5, 1.0),
            "subsample": t.suggest_float("subsample", 0.5, 1.0), "subsample_freq": 1,
            "reg_lambda": t.suggest_float("reg_lambda", 1e-3, 10, log=True)}


def _space_cat(t):
    return {"learning_rate": t.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "depth": t.suggest_int("depth", 4, 10),
            "l2_leaf_reg": t.suggest_float("l2_leaf_reg", 1, 10, log=True)}


MODELS: dict[str, ModelSpec] = {
    "xgb_ref": ModelSpec("xgb_ref", lambda k, s, p: build_classifier(k, s)),
    "dt": ModelSpec("dt", lambda k, s, p: DecisionTreeClassifier(random_state=s, **p), {}, _space_tree),
    "rf": ModelSpec("rf", lambda k, s, p: RandomForestClassifier(n_estimators=300, n_jobs=-1, random_state=s, **p),
                    {}, _space_forest),
    "et": ModelSpec("et", lambda k, s, p: ExtraTreesClassifier(n_estimators=300, n_jobs=-1, random_state=s, **p),
                    {}, _space_forest),
    "xgb": ModelSpec("xgb", lambda k, s, p: _EarlyStopped("xgb", k, s, p), {}, _space_xgb),
    "lgbm": ModelSpec("lgbm", lambda k, s, p: _EarlyStopped("lgbm", k, s, p), {}, _space_lgbm, ("lightgbm",)),
    "catboost": ModelSpec("catboost", lambda k, s, p: _EarlyStopped("catboost", k, s, p), {}, _space_cat, ("catboost",)),
}


def factory(name: str, params: dict | None = None) -> Callable[[int, int], Any]:
    spec = MODELS[name]
    merged = {**spec.defaults, **(params or {})}
    return lambda n_classes, seed: spec.build(n_classes, seed, merged)
