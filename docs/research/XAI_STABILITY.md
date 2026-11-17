# E9 — Explanation stability (auto-generated)

_Generated 2026-11-17T09:36:28Z by `scripts/57_xai_stability.py`; 20 replay flows per family (frozen-test ∩ gate-test, zero train overlap; pool v2); seed 7._

| Family | Flows | Consistency (Jaccard top-5, within family) | Robustness to ±1% noise (Jaccard top-5) | Rank stability (Spearman top-10) | SHAP–LIME agreement (Jaccard top-5) |
|---|---|---|---|---|---|
| BENIGN | 20 | 0.46 ± 0.17 | 1.00 ± 0.00 | 1.00 ± 0.00 | 0.17 ± 0.09 |
| Bot | 20 | 0.47 ± 0.33 | 0.57 ± 0.33 | 0.40 ± 0.48 | 0.48 ± 0.23 |
| BruteForce | 20 | 0.67 ± 0.26 | 0.95 ± 0.12 | 1.00 ± 0.01 | 0.13 ± 0.15 |
| DDoS | 20 | 0.81 ± 0.17 | 0.96 ± 0.17 | 0.92 ± 0.25 | 0.36 ± 0.09 |
| DoS | 20 | 0.62 ± 0.24 | 0.83 ± 0.28 | 0.80 ± 0.41 | 0.40 ± 0.08 |
| PortScan | 20 | 1.00 ± 0.00 | 0.98 ± 0.07 | 0.99 ± 0.02 | 0.26 ± 0.09 |
| WebAttack | 20 | 0.45 ± 0.28 | 0.73 ± 0.31 | 0.58 ± 0.51 | 0.12 ± 0.09 |

Overall: robustness Jaccard 0.8599, rank stability 0.8125, SHAP–LIME agreement 0.2726.

Most frequent top-5 features per family:

* **BENIGN** — Init_Win_bytes_backward (20/20), Average Packet Size (19/20), Bwd Packet Length Std (17/20), Destination Port (9/20), Packet Length Variance (7/20)
* **Bot** — Destination Port (19/20), Init_Win_bytes_backward (18/20), Fwd Packet Length Max (13/20), min_seg_size_forward (11/20), Fwd Packet Length Mean (10/20)
* **BruteForce** — Destination Port (20/20), min_seg_size_forward (19/20), Fwd Packet Length Max (19/20), Packet Length Mean (14/20), Bwd Header Length (13/20)
* **DDoS** — Destination Port (20/20), Init_Win_bytes_backward (20/20), Fwd Packet Length Max (20/20), Fwd Packet Length Mean (20/20), min_seg_size_forward (12/20)
* **DoS** — Destination Port (20/20), Init_Win_bytes_backward (19/20), Fwd Packet Length Max (18/20), Idle Mean (15/20), Packet Length Mean (11/20)
* **PortScan** — Fwd Packet Length Max (20/20), Packet Length Mean (20/20), Avg Fwd Segment Size (20/20), Fwd Packet Length Mean (20/20), Average Packet Size (20/20)
* **WebAttack** — Average Packet Size (18/20), Max Packet Length (17/20), Destination Port (16/20), Packet Length Mean (9/20), Avg Fwd Segment Size (8/20)
