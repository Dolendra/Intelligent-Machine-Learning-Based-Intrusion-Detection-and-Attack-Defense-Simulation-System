# Model families on seen vs. unseen attacks (auto-generated)

_Generated 2026-11-10T12:28:22Z by `scripts/58_model_family_comparison.py`; research split seed 1; every model thresholded for a 1% benign false-alarm rate on validation flows._

| Model | IID F1 | IID recall | IID FPR | IID MCC | Fit (s) | µs/flow | Held-out zero-day recall (mean of 6) | Held-out AUROC |
|---|---|---|---|---|---|---|---|---|
| Hist. gradient boosting (LightGBM-style) | 0.9893 | 0.9999 | 1.06% | 0.9841 | 8.3 | 3.67 | 0.483 | 0.937 |
| XGBoost | 0.9893 | 1.0000 | 1.06% | 0.9841 | 6.9 | 1.0 | 0.457 | 0.933 |
| Random forest | 0.9896 | 0.9999 | 1.03% | 0.9845 | 7.8 | 1.38 | 0.455 | 0.839 |
| 1-D CNN (PyTorch) | 0.9894 | 0.9993 | 1.01% | 0.9843 | 47.8 | 10.09 | 0.350 | 0.783 |
| Decision tree | 0.9966 | 0.9980 | 0.23% | 0.9950 | 3.8 | 0.07 | 0.304 | 0.650 |
| MLP / ANN (PyTorch) | 0.9890 | 0.9971 | 0.95% | 0.9836 | 20.6 | 0.38 | 0.249 | 0.745 |
| Kernel SVM (RBF, Nyström) | 0.9861 | 0.9919 | 0.97% | 0.9793 | 15.1 | 5.73 | 0.201 | 0.673 |
| Logistic regression | 0.9357 | 0.8977 | 1.03% | 0.9079 | 5.4 | 0.09 | 0.127 | 0.745 |
| Linear SVM | 0.9506 | 0.9241 | 0.99% | 0.9283 | 15.5 | 0.24 | 0.110 | 0.753 |
| LSTM (PyTorch) | 0.9278 | 0.8836 | 1.03% | 0.8974 | 48.1 | 10.02 | 0.048 | 0.628 |

Per withheld family (zero-day recall at 1% FPR):

| Model | Bot | BruteForce | DDoS | DoS | PortScan | WebAttack |
|---|---|---|---|---|---|---|
| Logistic regression | 0.000 | 0.004 | 0.622 | 0.100 | 0.033 | 0.004 |
| Decision tree | 0.002 | 0.000 | 0.624 | 0.308 | 0.014 | 0.874 |
| Random forest | 0.000 | 0.239 | 0.643 | 0.903 | 0.027 | 0.918 |
| XGBoost | 0.000 | 0.153 | 0.644 | 0.941 | 0.048 | 0.958 |
| Hist. gradient boosting (LightGBM-style) | 0.000 | 0.299 | 0.665 | 0.809 | 0.167 | 0.958 |
| Linear SVM | 0.000 | 0.005 | 0.555 | 0.047 | 0.044 | 0.011 |
| Kernel SVM (RBF, Nyström) | 0.000 | 0.231 | 0.636 | 0.259 | 0.015 | 0.067 |
| MLP / ANN (PyTorch) | 0.000 | 0.240 | 0.638 | 0.538 | 0.010 | 0.067 |
| 1-D CNN (PyTorch) | 0.000 | 0.232 | 0.732 | 0.180 | 0.052 | 0.905 |
| LSTM (PyTorch) | 0.000 | 0.000 | 0.089 | 0.195 | 0.002 | 0.005 |

* Thresholds are set on validation benign flows for a 1% false-alarm budget (same operating point for all).
* Histogram gradient boosting is scikit-learn's LightGBM-style implementation (LightGBM itself not installed).
* CNN/LSTM read the 77 flow features as a 1-D sequence, as is common in the IDS literature; flows have no time axis.
