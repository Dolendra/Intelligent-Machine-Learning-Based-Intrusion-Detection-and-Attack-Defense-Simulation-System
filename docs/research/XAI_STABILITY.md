# E9 — Explanation stability (auto-generated)

_Generated 2026-11-10T11:19:10Z by `scripts/57_xai_stability.py`; 20 held-out replay flows per family; seed 7._

| Family | Flows | Consistency (Jaccard top-5, within family) | Robustness to ±1% noise (Jaccard top-5) | Rank stability (Spearman top-10) | SHAP–LIME agreement (Jaccard top-5) |
|---|---|---|---|---|---|
| BENIGN | 20 | 0.54 ± 0.19 | 0.98 ± 0.07 | 0.98 ± 0.09 | 0.14 ± 0.09 |
| Bot | 20 | 0.45 ± 0.33 | 0.51 ± 0.25 | 0.34 ± 0.45 | 0.44 ± 0.24 |
| BruteForce | 20 | 0.74 ± 0.21 | 0.92 ± 0.15 | 0.99 ± 0.01 | 0.20 ± 0.16 |
| DDoS | 20 | 0.85 ± 0.17 | 0.90 ± 0.20 | 0.91 ± 0.25 | 0.38 ± 0.08 |
| DoS | 20 | 0.53 ± 0.25 | 0.90 ± 0.16 | 0.95 ± 0.04 | 0.38 ± 0.13 |
| PortScan | 20 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.01 | 0.24 ± 0.04 |
| WebAttack | 20 | 0.54 ± 0.30 | 0.66 ± 0.28 | 0.51 ± 0.41 | 0.06 ± 0.07 |

Overall: robustness Jaccard 0.8372, rank stability 0.8109, SHAP–LIME agreement 0.2619.

Most frequent top-5 features per family:

* **BENIGN** — Init_Win_bytes_backward (20/20), Average Packet Size (20/20), Bwd Packet Length Std (18/20), Packet Length Variance (9/20), Destination Port (9/20)
* **Bot** — Destination Port (18/20), Init_Win_bytes_backward (18/20), Fwd Packet Length Max (13/20), min_seg_size_forward (11/20), Fwd Packet Length Mean (10/20)
* **BruteForce** — Destination Port (20/20), min_seg_size_forward (20/20), Fwd Packet Length Max (20/20), Bwd Header Length (17/20), Packet Length Mean (11/20)
* **DDoS** — Destination Port (20/20), Init_Win_bytes_backward (20/20), Fwd Packet Length Max (20/20), Fwd Packet Length Mean (20/20), min_seg_size_forward (14/20)
* **DoS** — Destination Port (20/20), Fwd Packet Length Max (17/20), Init_Win_bytes_backward (17/20), Idle Mean (11/20), Packet Length Mean (10/20)
* **PortScan** — Fwd Packet Length Max (20/20), Packet Length Mean (20/20), Avg Fwd Segment Size (20/20), Fwd Packet Length Mean (20/20), Average Packet Size (20/20)
* **WebAttack** — Average Packet Size (18/20), Max Packet Length (18/20), Destination Port (16/20), Avg Fwd Segment Size (15/20), Bwd Packet Length Mean (8/20)
