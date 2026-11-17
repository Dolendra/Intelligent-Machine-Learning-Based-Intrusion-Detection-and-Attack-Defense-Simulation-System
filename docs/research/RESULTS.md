# Aegis-OSR — results (auto-generated)

_Generated 2026-11-17T11:04:21+00:00 by `scripts/55_research_figures.py`. Do not edit by hand — rerun the script._

Design selected on pilot seed 0; all numbers below use fresh seeds (see `meta`). α = 1% benign false-alarm budget unless stated; brackets are 95% t-intervals over seeds.

## Leave-one-attack-family-out (CICIDS2017)

Seeds: [1, 2, 3, 4, 5] · records: 30 · commit `775e9a9`

![loafo methods](../../research_artifacts/figures/loafo_methods.png)

| Method | Group | Zero-day recall @1% | AUROC (unknown) | Known recall | Realized FPR |
|---|---|---|---|---|---|
| **Aegis-OSR** | proposed | 0.706 [0.689, 0.723] | 0.946 [0.943, 0.950] | 1.000 [0.999, 1.000] | 1.00% [0.92, 1.07] |
| Aegis-OSR w/ omnibus fusion | ablation | 0.614 [0.587, 0.642] | 0.946 [0.941, 0.951] | 1.000 [1.000, 1.000] | 0.99% [0.92, 1.06] |
| Aegis-OSR w/ AE novelty | ablation | 0.562 [0.527, 0.597] | 0.955 [0.952, 0.957] | 1.000 [1.000, 1.000] | 0.97% [0.88, 1.05] |
| Aegis-OSR w/ max fusion | ablation | 0.531 [0.500, 0.563] | 0.944 [0.939, 0.948] | 1.000 [1.000, 1.000] | 0.99% [0.95, 1.04] |
| Aegis-OSR w/ IForest novelty | ablation | 0.478 [0.438, 0.518] | 0.929 [0.924, 0.934] | 1.000 [1.000, 1.000] | 0.99% [0.96, 1.02] |
| Closed-set XGB | baseline | 0.490 [0.447, 0.533] | 0.938 [0.932, 0.945] | 1.000 [1.000, 1.000] | 1.00% [0.97, 1.02] |
| XGB + Energy | baseline | 0.457 [0.430, 0.484] | 0.947 [0.943, 0.952] | 1.000 [1.000, 1.000] | 1.00% [0.95, 1.04] |
| kNN distance | baseline | 0.379 [0.358, 0.401] | 0.866 [0.861, 0.871] | 0.546 [0.534, 0.559] | 1.01% [0.92, 1.11] |
| Closed-set DT (v1.1-style) | baseline | 0.241 [0.177, 0.305] | 0.606 [0.571, 0.640] | 0.999 [0.999, 0.999] | 0.31% [0.21, 0.42] |
| Autoencoder | baseline | 0.231 [0.197, 0.265] | 0.883 [0.870, 0.897] | 0.430 [0.397, 0.463] | 1.00% [0.86, 1.13] |
| Isolation Forest | baseline | 0.012 [0.011, 0.012] | 0.840 [0.829, 0.851] | 0.008 [0.007, 0.008] | 0.99% [0.92, 1.06] |

**Seed-level paired comparison (folds averaged within each seed; fold W/L/T descriptive only)**

| Aegis-OSR vs | Mean Δ zero-day recall [95% CI] | Seeds better | Paired t p (seeds) | Fold W / L / T (descriptive) |
|---|---|---|---|---|
| Isolation Forest | +0.694 [+0.677, +0.712] | 5 / 5 | 3.76e-08 | 27 / 2 / 1 |
| kNN distance | +0.327 [+0.304, +0.350] | 5 / 5 | 2.39e-06 | 25 / 5 / 0 |
| XGB + Energy | +0.249 [+0.231, +0.267] | 5 / 5 | 2.63e-06 | 30 / 0 / 0 |
| Autoencoder | +0.475 [+0.435, +0.514] | 5 / 5 | 4.72e-06 | 27 / 3 / 0 |
| Aegis-OSR w/ max fusion | +0.175 [+0.152, +0.197] | 5 / 5 | 2.59e-05 | 24 / 6 / 0 |
| Closed-set DT (v1.1-style) | +0.465 [+0.402, +0.528] | 5 / 5 | 3.27e-05 | 30 / 0 / 0 |
| Aegis-OSR w/ IForest novelty | +0.228 [+0.194, +0.262] | 5 / 5 | 4.79e-05 | 30 / 0 / 0 |
| Aegis-OSR w/ omnibus fusion | +0.092 [+0.078, +0.106] | 5 / 5 | 5.24e-05 | 24 / 6 / 0 |
| Closed-set XGB | +0.216 [+0.180, +0.252] | 5 / 5 | 7.59e-05 | 30 / 0 / 0 |
| Aegis-OSR w/ AE novelty | +0.144 [+0.119, +0.169] | 5 / 5 | 8.67e-05 | 25 / 5 / 0 |

![per family](../../research_artifacts/figures/loafo_by_family.png)

![operating curve](../../research_artifacts/figures/loafo_operating_curve.png)

**Per fold (zero-day recall, realized FPR)**

| Fold | Aegis-OSR | Closed-set XGB | Aegis-OSR w/ AE novelty | Closed-set DT (v1.1-style) |
|---|---|---|---|---|
| Bot | 0.023 [0.019, 0.028]<br/>FPR 1.00% [0.94, 1.06] | 0.004 [-0.001, 0.009]<br/>FPR 0.98% [0.95, 1.02] | 0.012 [0.010, 0.015]<br/>FPR 0.96% [0.84, 1.08] | 0.000 [-0.000, 0.001]<br/>FPR 0.40% [0.05, 0.75] |
| BruteForce | 0.923 [0.869, 0.977]<br/>FPR 1.00% [0.91, 1.08] | 0.310 [0.123, 0.497]<br/>FPR 1.00% [0.93, 1.07] | 0.316 [0.126, 0.505]<br/>FPR 0.96% [0.88, 1.04] | 0.001 [0.000, 0.001]<br/>FPR 0.40% [0.13, 0.68] |
| DDoS | 0.965 [0.928, 1.002]<br/>FPR 0.99% [0.90, 1.09] | 0.742 [0.616, 0.867]<br/>FPR 1.00% [0.94, 1.07] | 0.920 [0.854, 0.985]<br/>FPR 0.97% [0.87, 1.08] | 0.499 [0.423, 0.576]<br/>FPR 0.54% [0.51, 0.57] |
| DoS | 0.977 [0.974, 0.980]<br/>FPR 1.00% [0.92, 1.08] | 0.824 [0.726, 0.923]<br/>FPR 1.00% [0.93, 1.07] | 0.987 [0.983, 0.991]<br/>FPR 0.94% [0.86, 1.03] | 0.246 [0.062, 0.430]<br/>FPR 0.12% [0.10, 0.15] |
| PortScan | 0.357 [0.257, 0.457]<br/>FPR 0.99% [0.92, 1.06] | 0.112 [0.020, 0.204]<br/>FPR 1.00% [0.98, 1.03] | 0.177 [0.016, 0.337]<br/>FPR 0.99% [0.90, 1.08] | 0.011 [0.007, 0.015]<br/>FPR 0.09% [0.08, 0.09] |
| WebAttack | 0.991 [0.989, 0.993]<br/>FPR 1.00% [0.90, 1.09] | 0.946 [0.930, 0.962]<br/>FPR 0.99% [0.93, 1.05] | 0.960 [0.951, 0.969]<br/>FPR 0.97% [0.91, 1.04] | 0.688 [0.256, 1.121]<br/>FPR 0.31% [0.14, 0.49] |

## True temporal holdout (CICIDS2017 capture days)

Seeds: [1, 2, 3, 4, 5] · records: 10 · commit `775e9a9`

![temporal methods](../../research_artifacts/figures/temporal_methods.png)

| Method | Group | Zero-day recall @1% | AUROC (unknown) | Known recall | Realized FPR |
|---|---|---|---|---|---|
| **Aegis-OSR** | proposed | 0.744 [0.742, 0.746] | 0.912 [0.896, 0.928] | — | 4.40% [4.10, 4.71] |
| Aegis-OSR w/ AE novelty | ablation | 0.738 [0.732, 0.744] | 0.933 [0.924, 0.943] | — | 3.80% [3.09, 4.51] |
| Aegis-OSR w/ omnibus fusion | ablation | 0.735 [0.726, 0.744] | 0.910 [0.902, 0.918] | — | 9.21% [8.71, 9.70] |
| Aegis-OSR w/ max fusion | ablation | 0.716 [0.698, 0.733] | 0.906 [0.899, 0.914] | — | 9.62% [9.06, 10.17] |
| Aegis-OSR w/ IForest novelty | ablation | 0.707 [0.692, 0.721] | 0.911 [0.900, 0.922] | — | 2.45% [2.31, 2.59] |
| Closed-set XGB | baseline | 0.727 [0.712, 0.741] | 0.880 [0.843, 0.918] | — | 1.26% [1.19, 1.33] |
| XGB + Energy | baseline | 0.715 [0.690, 0.740] | 0.872 [0.839, 0.905] | — | 1.27% [1.22, 1.33] |
| Closed-set DT (v1.1-style) | baseline | 0.492 [0.392, 0.593] | 0.744 [0.696, 0.793] | — | 0.13% [-0.10, 0.36] |
| kNN distance | baseline | 0.239 [0.238, 0.240] | 0.778 [0.773, 0.783] | — | 9.91% [9.75, 10.08] |
| Autoencoder | baseline | 0.139 [0.097, 0.182] | 0.806 [0.777, 0.835] | — | 8.90% [7.61, 10.19] |
| Isolation Forest | baseline | 0.008 [0.006, 0.009] | 0.794 [0.773, 0.814] | — | 3.44% [3.22, 3.65] |

**Seed-level paired comparison (folds averaged within each seed; fold W/L/T descriptive only)**

| Aegis-OSR vs | Mean Δ zero-day recall [95% CI] | Seeds better | Paired t p (seeds) | Fold W / L / T (descriptive) |
|---|---|---|---|---|
| Isolation Forest | +0.736 [+0.733, +0.739] | 5 / 5 | 2.04e-11 | 10 / 0 / 0 |
| kNN distance | +0.505 [+0.502, +0.508] | 5 / 5 | 9.28e-11 | 10 / 0 / 0 |
| Autoencoder | +0.604 [+0.562, +0.647] | 5 / 5 | 2.40e-06 | 10 / 0 / 0 |
| Aegis-OSR w/ IForest novelty | +0.037 [+0.023, +0.051] | 5 / 5 | 1.66e-03 | 10 / 0 / 0 |
| Closed-set DT (v1.1-style) | +0.252 [+0.152, +0.351] | 5 / 5 | 2.17e-03 | 10 / 0 / 0 |
| Aegis-OSR w/ max fusion | +0.028 [+0.012, +0.044] | 5 / 5 | 7.87e-03 | 6 / 3 / 1 |
| Aegis-OSR w/ AE novelty | +0.006 [+0.002, +0.010] | 5 / 5 | 1.38e-02 | 10 / 0 / 0 |
| Closed-set XGB | +0.017 [+0.004, +0.031] | 5 / 5 | 2.45e-02 | 10 / 0 / 0 |
| XGB + Energy | +0.029 [+0.004, +0.053] | 5 / 5 | 3.03e-02 | 10 / 0 / 0 |
| Aegis-OSR w/ omnibus fusion | +0.009 [+0.000, +0.017] | 5 / 5 | 4.55e-02 | 7 / 3 / 0 |

**Per fold (zero-day recall, realized FPR)**

| Fold | Aegis-OSR | Closed-set XGB | Aegis-OSR w/ AE novelty | Closed-set DT (v1.1-style) |
|---|---|---|---|---|
| Mon-Thu→Fri | 0.495 [0.488, 0.503]<br/>FPR 7.09% [6.66, 7.52] | 0.471 [0.442, 0.499]<br/>FPR 1.27% [1.23, 1.31] | 0.490 [0.484, 0.497]<br/>FPR 5.94% [4.82, 7.07] | 0.127 [-0.078, 0.333]<br/>FPR 0.16% [-0.18, 0.51] |
| Mon-Wed→Thu | 0.992 [0.987, 0.998]<br/>FPR 1.72% [1.15, 2.28] | 0.982 [0.980, 0.985]<br/>FPR 1.25% [1.14, 1.36] | 0.986 [0.979, 0.993]<br/>FPR 1.66% [0.92, 2.40] | 0.857 [0.844, 0.869]<br/>FPR 0.10% [-0.02, 0.21] |

**Label-light adaptation (no retraining)**

![adaptation](../../research_artifacts/figures/temporal_adaptation.png)

| Fold | Variant | Window | Zero-day recall | Realized FPR |
|---|---|---|---|---|
| Mon-Thu→Fri | oracle | 2000 | 0.390 [0.310, 0.469] | 0.97% [0.64, 1.30] |
| Mon-Thu→Fri | recal | 500 | 0.345 [0.299, 0.390] | 0.36% [0.19, 0.52] |
| Mon-Thu→Fri | recal | 2000 | 0.429 [0.402, 0.456] | 0.82% [-0.04, 1.69] |
| Mon-Thu→Fri | recal | 5000 | 0.441 [0.416, 0.467] | 2.57% [1.73, 3.42] |
| Mon-Thu→Fri | recal+ref | 500 | 0.329 [0.313, 0.345] | 0.46% [0.11, 0.80] |
| Mon-Thu→Fri | recal+ref | 2000 | 0.383 [0.316, 0.450] | 0.63% [0.16, 1.10] |
| Mon-Thu→Fri | recal+ref | 5000 | 0.444 [0.420, 0.468] | 2.84% [1.94, 3.73] |
| Mon-Wed→Thu | oracle | 2000 | 0.981 [0.966, 0.997] | 0.92% [0.48, 1.36] |
| Mon-Wed→Thu | recal | 500 | 0.938 [0.913, 0.962] | 0.27% [0.13, 0.42] |
| Mon-Wed→Thu | recal | 2000 | 0.951 [0.918, 0.985] | 0.49% [0.29, 0.69] |
| Mon-Wed→Thu | recal | 5000 | 0.882 [0.667, 1.096] | 0.67% [0.55, 0.78] |
| Mon-Wed→Thu | recal+ref | 500 | 0.926 [0.894, 0.957] | 0.24% [0.08, 0.41] |
| Mon-Wed→Thu | recal+ref | 2000 | 0.954 [0.934, 0.975] | 0.49% [0.27, 0.71] |
| Mon-Wed→Thu | recal+ref | 5000 | 0.961 [0.952, 0.969] | 0.77% [0.62, 0.92] |

## Cross-dataset: CICIDS2017 → CSE-CIC-IDS2018

Seeds: [1, 2, 3, 4, 5] · records: 5 · commit `a20552f`

![cross methods](../../research_artifacts/figures/cross_methods.png)

| Method | Group | Zero-day recall @1% | AUROC (unknown) | Known recall | Realized FPR |
|---|---|---|---|---|---|
| **Aegis-OSR** | proposed | 0.438 [0.427, 0.450] | 0.568 [0.562, 0.574] | 0.855 [0.837, 0.873] | 36.73% [34.72, 38.73] |
| Aegis-OSR w/ omnibus fusion | ablation | 0.457 [0.424, 0.490] | 0.580 [0.574, 0.586] | 0.911 [0.906, 0.917] | 37.95% [33.18, 42.72] |
| Aegis-OSR w/ AE novelty | ablation | 0.432 [0.418, 0.447] | 0.546 [0.538, 0.554] | 0.918 [0.915, 0.921] | 29.84% [28.20, 31.48] |
| Aegis-OSR w/ max fusion | ablation | 0.431 [0.388, 0.473] | 0.581 [0.568, 0.593] | 0.890 [0.881, 0.899] | 33.74% [32.93, 34.55] |
| Aegis-OSR w/ IForest novelty | ablation | 0.154 [0.097, 0.210] | 0.511 [0.506, 0.516] | 0.776 [0.700, 0.851] | 3.78% [2.72, 4.84] |
| kNN distance | baseline | 0.715 [0.708, 0.722] | 0.552 [0.547, 0.557] | 0.500 [0.497, 0.502] | 59.79% [59.31, 60.26] |
| Autoencoder | baseline | 0.304 [0.289, 0.318] | 0.533 [0.520, 0.545] | 0.493 [0.491, 0.496] | 29.39% [28.87, 29.91] |
| Closed-set XGB | baseline | 0.168 [0.158, 0.178] | 0.513 [0.508, 0.519] | 0.861 [0.836, 0.886] | 4.62% [2.26, 6.97] |
| XGB + Energy | baseline | 0.157 [0.134, 0.180] | 0.516 [0.509, 0.522] | 0.819 [0.766, 0.873] | 4.23% [3.59, 4.86] |
| Closed-set DT (v1.1-style) | baseline | 0.083 [0.046, 0.121] | 0.455 [0.426, 0.485] | 0.351 [0.297, 0.405] | 14.59% [7.44, 21.74] |
| Isolation Forest | baseline | 0.037 [0.034, 0.040] | 0.467 [0.451, 0.482] | 0.007 [0.007, 0.008] | 1.95% [1.39, 2.51] |

**Seed-level paired comparison (folds averaged within each seed; fold W/L/T descriptive only)**

| Aegis-OSR vs | Mean Δ zero-day recall [95% CI] | Seeds better | Paired t p (seeds) | Fold W / L / T (descriptive) |
|---|---|---|---|---|
| Closed-set XGB | +0.270 [+0.262, +0.279] | 5 / 5 | 1.07e-07 | 5 / 0 / 0 |
| Isolation Forest | +0.401 [+0.388, +0.415] | 5 / 5 | 1.40e-07 | 5 / 0 / 0 |
| kNN distance | -0.276 [-0.292, -0.261] | 0 / 5 | 1.01e-06 | 0 / 5 / 0 |
| Closed-set DT (v1.1-style) | +0.355 [+0.327, +0.383] | 5 / 5 | 3.99e-06 | 5 / 0 / 0 |
| Autoencoder | +0.135 [+0.122, +0.148] | 5 / 5 | 9.29e-06 | 5 / 0 / 0 |
| XGB + Energy | +0.281 [+0.252, +0.310] | 5 / 5 | 1.13e-05 | 5 / 0 / 0 |
| Aegis-OSR w/ IForest novelty | +0.285 [+0.224, +0.345] | 5 / 5 | 1.98e-04 | 5 / 0 / 0 |
| Aegis-OSR w/ omnibus fusion | -0.019 [-0.048, +0.010] | 1 / 5 | 1.42e-01 | 1 / 4 / 0 |
| Aegis-OSR w/ AE novelty | +0.006 [-0.004, +0.016] | 4 / 5 | 1.68e-01 | 4 / 1 / 0 |
| Aegis-OSR w/ max fusion | +0.008 [-0.041, +0.056] | 1 / 5 | 6.80e-01 | 1 / 4 / 0 |

**Per fold (zero-day recall, realized FPR)**

| Fold | Aegis-OSR | Closed-set XGB | Aegis-OSR w/ AE novelty | Closed-set DT (v1.1-style) |
|---|---|---|---|---|
| CICIDS2017→CSE-CIC-IDS2018 | 0.438 [0.427, 0.450]<br/>FPR 36.73% [34.72, 38.73] | 0.168 [0.158, 0.178]<br/>FPR 4.62% [2.26, 6.97] | 0.432 [0.418, 0.447]<br/>FPR 29.84% [28.20, 31.48] | 0.083 [0.046, 0.121]<br/>FPR 14.59% [7.44, 21.74] |

**Label-light adaptation (no retraining)**

![adaptation](../../research_artifacts/figures/cross_adaptation.png)

| Fold | Variant | Window | Zero-day recall | Realized FPR |
|---|---|---|---|---|
| CICIDS2017→CSE-CIC-IDS2018 | oracle | 2000 | 0.020 [0.012, 0.028] | 0.92% [0.52, 1.32] |
| CICIDS2017→CSE-CIC-IDS2018 | recal | 500 | 0.073 [0.034, 0.112] | 3.11% [1.22, 5.01] |
| CICIDS2017→CSE-CIC-IDS2018 | recal | 2000 | 0.013 [0.008, 0.018] | 0.93% [0.68, 1.17] |
| CICIDS2017→CSE-CIC-IDS2018 | recal | 5000 | 0.015 [0.011, 0.019] | 0.88% [0.78, 0.98] |
| CICIDS2017→CSE-CIC-IDS2018 | recal+ref | 500 | 0.039 [-0.052, 0.130] | 1.66% [-2.51, 5.83] |
| CICIDS2017→CSE-CIC-IDS2018 | recal+ref | 2000 | 0.126 [0.053, 0.199] | 3.40% [1.82, 4.98] |
| CICIDS2017→CSE-CIC-IDS2018 | recal+ref | 5000 | 0.132 [0.041, 0.223] | 2.95% [1.79, 4.12] |

## Production Zero-Day Gate

![gate](../../research_artifacts/figures/gate_operating_points.png)

| α | Benign FPR | Known-attack recall | Never-seen alert rate |
|---|---|---|---|
| 0.0005 | 0.032% | 0.8650 | 0.064 |
| 0.001 | 0.073% | 0.8925 | 0.298 |
| 0.005 | 0.466% | 0.9935 | 0.532 |
| 0.01 | 0.920% | 0.9988 | 0.617 |
| 0.05 | 4.943% | 1.0000 | 0.979 |

Frozen v1.1 reference: benign FPR 0.079%, known recall 0.9927, never-seen attack rate 0.000.

> Gate metrics use the gate's own test split. Every frozen-vs-gate comparison uses only flows neither model trained on (protocol v2, R1a). Natural unknowns (Infiltration n=36, Heartbleed n=11) are tiny; treat rates as illustrative — LOAFO / temporal / cross-dataset protocols are the statistical evidence.

## Frozen v1.1 on CSE-CIC-IDS2018 (EXP-009, no retraining)

Precision 0.988 · recall 0.162 · F1 0.278 · benign FPR 0.15% (IID CICIDS2017 F1 reference: 0.9904784130688448)

| 2018 label | Family | n | Alert rate | Family match |
|---|---|---|---|---|
| Benign | BENIGN | 200000 | 0.002 | — |
| Bot | Bot | 20000 | 0.000 | 0.000 |
| Brute Force -Web | WebAttack | 555 | 0.031 | 0.000 |
| Brute Force -XSS | WebAttack | 228 | 0.110 | 0.009 |
| DDOS attack-HOIC | DDoS | 20000 | 0.004 | 0.000 |
| DDOS attack-LOIC-UDP | DDoS | 1730 | 0.000 | 0.000 |
| DDoS attacks-LOIC-HTTP | DDoS | 20000 | 0.450 | 0.000 |
| DoS attacks-GoldenEye | DoS | 20000 | 0.274 | 0.274 |
| DoS attacks-Hulk | DoS | 20000 | 0.011 | 0.008 |
| DoS attacks-SlowHTTPTest | DoS | 53 | 0.698 | 0.000 |
| DoS attacks-Slowloris | DoS | 9908 | 0.956 | 0.956 |
| FTP-BruteForce | BruteForce | 51 | 0.686 | 0.686 |
| Infilteration | Infiltration | 20000 | 0.015 | 0.000 |
| SQL Injection | WebAttack | 84 | 0.024 | 0.000 |
| SSH-Bruteforce | BruteForce | 20000 | 0.000 | 0.000 |

> Frozen CICIDS2017 models transferred to a different network, year and CICFlowMeter version. Performance under this shift is the honest external-validity number; it is NOT comparable to the IID score and no retraining or threshold tuning was done on 2018 data.
