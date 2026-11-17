# Aegis-OSR — Conformal Evidence Fusion for Zero-Day Network Intrusion Detection

**Status:** v3 research track (implemented this semester; paper next semester).
**Numbers:** see the auto-generated [`RESULTS.md`](RESULTS.md) — this document holds the
method and protocol, never hand-copied results.

---

## 1. Problem

Supervised NIDS (including Aegis v1.1: Decision Tree → attack-only Random Forest) are
**closed-set**: every flow is forced into *benign* or one of the families seen in training.
A never-seen attack is either silently called benign or mislabelled as a known family —
the classic "outside the closed world" problem (Sommer & Paxson, 2010).

Two practical requirements make this harder:

1. **Bounded false alarms.** A SOC cannot accept an unknown or drifting false-alarm rate.
2. **Distribution shift.** Benign traffic itself changes between days and networks, which
   inflates novelty-based false alarms.

**Research questions**

| ID | Question |
|----|----------|
| RQ-A | Does fusing supervised evidence with benign-novelty evidence detect unseen attack families better than a closed-set classifier at the *same* benign false-alarm rate? |
| RQ-B | Can the benign false-alarm rate be *guaranteed* (not just tuned) in finite samples? |
| RQ-C | What happens to that guarantee under realistic temporal and cross-network shift — and can it be restored without retraining? |
| RQ-D | Can alerts be attributed honestly (known family vs. unknown attack vs. novel anomaly)? |

## 2. Method

Let `x` be a flow (77 CICFlowMeter features, signed-log standardized).

**Evidence.**
* Supervised: `s_sup(x) = 1 − P(BENIGN | x)` from an XGBoost classifier over `K+1` classes
  (benign + K known families, sqrt-inverse-frequency weights).
* Novelty: `s_nov(x)` = mean Euclidean distance to the `k = 5` nearest **benign** training
  flows (a deep-kNN-style OOD score; Sun et al., 2022).

**Benign surprisal (per evidence).** On a benign calibration split `C1`,

```
t_j(x) = −log( (#{z ∈ C1 : s_j(z) ≥ s_j(x)} + 1) / (|C1| + 1) )
```

and beyond the largest benign score the tail is extrapolated exponentially
(peaks-over-threshold): `t_j` keeps increasing by `(s − max)/τ_j`, where `τ_j` is the mean excess
of the top 1 % of benign scores. This keeps flows far outside the benign range ordered.

**Fisher fusion.** `f(x) = Σ_j t_j(x)`: evidence *accumulates*, so a flow that is moderately
unusual to both the classifier and the novelty detector outranks one that is only mildly odd
to either (Fisher's method on benign tail probabilities).

**Split-conformal calibration.** On a disjoint benign split `C2`,

```
p(x) = (1 + #{z ∈ C2 : f(z) ≥ f(x)}) / (|C2| + 1),     alert ⇔ p(x) ≤ α
```

If test benign flows are exchangeable with `C2`, then `P(p ≤ α) ≤ α` for every α — a
**finite-sample guarantee on the benign false-alarm rate** (Vovk et al., 2005; Bates et al., 2023).
Every compared method is calibrated through the *same* surprisal → fusion → conformal steps,
so differences come from the evidence and fusion rule, not from threshold tuning.

**Attribution (Mondrian conformal).** For an alert where the classifier itself says attack
(`P(attack) ≥ 0.5`), the most likely family `k̂` is reported **unless** its class-conditional
conformal p-value (non-conformity `1 − P(k̂ | x, attack)`, calibrated per family on validation
attacks) is `≤ α_fam`, in which case the label is `UNKNOWN-ATTACK`. Alerts raised by novelty
alone are `ZERO-DAY-ANOMALY`.

**Label-light adaptation (no retraining).** Given a small window of *W* confirmed-benign flows
from the new environment:

* `recal@W` — re-estimate `C1`/`C2` on the window (restores exchangeability for calibration);
* `recal+ref@W` — additionally append ⅓ of the window to the kNN benign reference
  (those flows are excluded from calibration to avoid zero self-distances).

The classifier is never retrained.

## 3. Experimental protocol

| Protocol | Train / calibrate | Test | Unknowns |
|----------|------------------|------|----------|
| **LOAFO** | CICIDS2017 minus one family (stratified 60/10/30 split per seed) | test split + *all* rows of the held-out family | held-out family + Infiltration + Heartbleed |
| **Temporal** | earlier capture days | later day (earliest 5 000 benign flows reserved as warm-up) | families absent from the training days |
| **Cross-dataset** | CICIDS2017 | CSE-CIC-IDS2018 mapped to the 2017 schema | 2018 families unseen in 2017 (Infiltration) |

* **Pilot / selection.** The fusion rule (Fisher) and novelty detector (kNN) were chosen on
  seed 0 only (`research_artifacts/pilot_seed0_fusion_selection.csv`). Reported results use
  seeds 1–5 with fresh splits and model initialisations.
* **Caps** (per seed): train 300 k benign + ≤ 60 k per family; validation 60 k benign
  (→ 30 k + 30 k calibration) + ≤ 10 k per family; test 150 k benign + ≤ 25 k per family.
* **Metrics.** Zero-day recall at α ∈ {0.1 %, 1 %, 5 %}; threshold-free AUROC/AUPRC (benign vs.
  unknown); known-attack recall; realized benign FPR vs. nominal α; open-set attribution
  rates; open-set macro-F1.
* **Statistics.** Mean ± 95 % t-interval over seeds (folds averaged within a seed first);
  paired two-sided Wilcoxon signed-rank tests of Aegis-OSR vs. every method over
  fold × seed pairs.
* **Baselines / ablations.** Closed-set XGB; closed-set Decision Tree (Aegis v1.1 style);
  Isolation Forest; autoencoder (benign-only, weighted reconstruction error); kNN distance;
  XGB + energy score (Liu et al., 2020); Aegis-OSR with max fusion, omnibus (min-p) fusion,
  autoencoder novelty, Isolation-Forest novelty.

## 4. Why the old "temporal holdout" was replaced

`scripts/25_temporal_holdout_eval.py` re-scored the **frozen** v1.1 models — trained on a
random split covering all five days — on Friday CSV samples. Friday rows were therefore
partly in the training data, so it was not a temporal test. The v3 temporal protocol
retrains on earlier days only. Because CICIDS2017's Friday families (Bot, PortScan, DDoS)
never occur Monday–Thursday, a true temporal split is also a natural zero-day test.

## 5. Threats to validity (state these in the paper)

* **Dataset artefacts.** CICIDS2017 has documented labelling and flow-construction errors
  (Engelen et al., 2021; Lanvin et al., 2023). We use the public MachineLearningCVE export
  as-is; corrected re-extractions would strengthen the study.
* **Bot and WebAttack resemble benign HTTP.** No method detects held-out Bot reliably; report
  per-family results, not only means.
* **Exchangeability.** The FPR guarantee holds only when calibration and test benign traffic
  are exchangeable. Temporal and cross-dataset protocols are designed to *show* when it breaks.
* **Warm-up labels.** `recal@W` assumes an analyst can confirm W benign flows; the
  earliest-window variant is realistic, the "oracle" random window is an upper bound only.
* **Natural unknowns are tiny** (Infiltration n = 36, Heartbleed n = 11) — illustrative only.
* **Feature mapping 2017→2018** relies on CICFlowMeter column aliases; the tool versions differ.

## 6. Related work to position against (verify each citation before submission)

* R. Sommer, V. Paxson. *Outside the Closed World: On Using Machine Learning for Network
  Intrusion Detection.* IEEE S&P, 2010.
* D. Arp et al. *Dos and Don'ts of Machine Learning in Computer Security.* USENIX Security, 2022.
* R. Jordaney et al. *Transcend: Detecting Concept Drift in Malware Classification Models.*
  USENIX Security, 2017 — conformal evaluation for drift; closest prior use of conformal
  p-values in security (malware, rejection) vs. our NIDS open-set fusion with FPR control.
* V. Vovk, A. Gammerman, G. Shafer. *Algorithmic Learning in a Random World.* Springer, 2005.
* S. Bates, E. Candès, L. Lei, Y. Romano, M. Sesia. *Testing for Outliers with Conformal
  p-values.* Annals of Statistics, 2023.
* A. Bendale, T. Boult. *Towards Open Set Deep Networks* (OpenMax). CVPR, 2016.
* W. Liu, X. Wang, J. Owens, Y. Li. *Energy-based Out-of-distribution Detection.* NeurIPS, 2020.
* Y. Sun, Y. Ming, X. Zhu, Y. Li. *Out-of-Distribution Detection with Deep Nearest Neighbors.* ICML, 2022.
* I. Sharafaldin, A. H. Lashkari, A. A. Ghorbani. *Toward Generating a New Intrusion Detection
  Dataset and Intrusion Traffic Characterization.* ICISSP, 2018.
* G. Engelen, V. Rimmer, W. Joosen. *Troubleshooting an Intrusion Detection Dataset: the
  CICIDS2017 Case Study.* IEEE S&P Workshops, 2021.
* M. Lanvin et al. *Errors in the CICIDS2017 Dataset and the Significant Differences in
  Detection Performances It Makes.* CRiSIS, 2022/2023.

## 7. Reproduce

```bash
python scripts/50_openset_experiments.py --protocol loafo temporal --seeds 1 2 3 4 5
python scripts/50_openset_experiments.py --protocol cross --seeds 1 2 3 4 5   # needs CSE-CIC-IDS2018/
python scripts/53_summarize_research.py
python scripts/51_train_zero_day_gate.py     # production gate (advisory)
python scripts/52_build_replay_pool.py       # live monitor replay data
python scripts/54_frozen_v11_on_cic2018.py   # EXP-009: frozen v1.1 on 2018
python scripts/55_research_figures.py        # figures + RESULTS.md
```

Download CSE-CIC-IDS2018 (public, no sign-in, ~6.5 GB):

```bash
aws s3 sync --no-sign-request --region ca-central-1 \
  "s3://cse-cic-ids2018/Processed Traffic Data for ML Algorithms/" CSE-CIC-IDS2018/
```
