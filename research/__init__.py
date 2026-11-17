"""Aegis v3 research track: open-set (zero-day) intrusion detection.

This package is deliberately separate from the frozen v1.1 pipeline (``ml/``):
nothing here reads or overwrites ``binary_best.joblib`` / ``multiclass_best.joblib``.

Modules
-------
data       CICIDS2017 (with capture day + fine labels) and CSE-CIC-IDS2018 loaders
features   signed-log + standard scaling shared by all research models
novelty    unsupervised novelty detectors (autoencoder, isolation forest)
conformal  conformal p-values with a finite-sample benign false-positive bound
openset    Aegis-OSR hybrid detector and the baseline scorers it is compared to
metrics    open-set metrics, confidence intervals, significance tests
protocols  leave-one-family-out, true temporal, and cross-dataset experiments
"""
