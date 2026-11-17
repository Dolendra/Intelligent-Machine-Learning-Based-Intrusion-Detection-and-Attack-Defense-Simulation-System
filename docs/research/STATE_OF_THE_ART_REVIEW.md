# Aegis IDS — State-of-the-Art Review (R2)

**Date:** 2026-11-17 · **Branch:** `v3-openset-research` · **Scope:** 2023–2026 literature (older works only where foundational, and marked as such)
**Companion document:** [`RESEARCH_GAP_ANALYSIS.md`](RESEARCH_GAP_ANALYSIS.md)
**Aegis numbers** are quoted from [`RESULTS.md`](RESULTS.md), [`CLAIM_AUDIT.md`](CLAIM_AUDIT.md), [`AEGIS_OSR.md`](AEGIS_OSR.md) and [`XAI_STABILITY.md`](XAI_STABILITY.md). This review does not restate them from memory.

---

## 1. Purpose and method

### 1.1 Purpose

This review places Aegis-OSR in the current literature before the R3 benchmark and the paper. Aegis-OSR is our conformal fusion of XGBoost attack evidence and benign kNN distance for zero-day NIDS. The review answers three questions:

1. Which current methods are credible alternatives or components for the evidence models (tabular ML, Family A)?
2. What has already been done on open-set and zero-day NIDS, on conformal or calibrated false-alarm control, and on cross-dataset generalisation (Families B and C)?
3. Which behavioural or temporal approaches could close the Bot and PortScan gap (Family D)?

### 1.2 Search terms

Searches ran on 2026-11-17 using web search, arXiv, publisher and proceedings pages, and the Crossref REST API for DOI metadata. The main queries were:

* **Tabular ML:** TabR, TabM, TabICL, TabICLv2, TabPFN Nature, FT-Transformer, "why do tree-based models still outperform", "when do neural nets outperform boosted trees", "TabPFN TabICL intrusion detection", "tabular representation learning network intrusion detection".
* **Open-set and conformal:** "open set recognition network intrusion detection", "zero-day network intrusion detection held-out attack", "conformal prediction intrusion detection false alarm", Transcend, "Transcending Transcend", CADE, "conformal p-values outliers", "conformal prediction beyond exchangeability", "adaptive conformal inference", energy-based OOD, deep nearest neighbours OOD, Deep SVDD, OpenMax, "extreme value theory streams".
* **Cross-dataset:** NetFlow standard feature set, NF-v3 temporal NetFlow, cross-evaluation NIDS, cross-dataset generalisation CIC-IDS2017 CSE-CIC-IDS2018, LycoS-IDS2017, "error prevalence NIDS datasets", "troubleshooting CICIDS2017", "errors in the CICIDS2017 dataset", "bad design smells NIDS datasets", "flow exporter impact", "CICFlowMeter version", "feature harmonization intrusion detection", "domain generalization intrusion detection".
* **Temporal and behavioural:** E-GraphSAGE, Anomal-E, XG-BoT, Euler lateral movement, Kitsune, FlowTransformer, "sequential machine learning NIDS evaluation", "LSTM / TCN / transformer flow sequence CIC-IDS2017".
* **Evaluation methodology:** "Dos and Don'ts of machine learning in computer security", "SoK pragmatic assessment NIDS", "evaluating explanation methods deep learning security", "stream assembly intrusion detection benchmark".
* **Leads from the chatbot conversation:** each lead was searched by its stated name, venue and year (Section 6).

### 1.3 Inclusion and exclusion

* **Included:** work that proposes or evaluates (a) tabular learners usable as Aegis evidence models, (b) open-set, zero-day, OOD or conformal methods applicable to flow-level NIDS, (c) cross-dataset or measurement-tool effects on NIDS datasets, (d) temporal, host-level or graph NIDS relevant to Bot and PortScan, or (e) NIDS evaluation methodology.
* **Excluded:** papers whose venue or authorship could not be confirmed on an official or bibliographic source (they are listed in Section 6). Also excluded: packet-payload and LLM-based NIDS, which are out of Aegis's scope. Also excluded: generic surveys without a protocol contribution. Ahmad et al. (2023) is the one survey kept, because it frames the zero-day problem.

### 1.4 Verification rule

Every entry below was checked against at least one of the following sources:

* the publisher or proceedings page (USENIX, PMLR, NeurIPS, ICLR, CVF, IEEE, Project Euclid);
* DOI metadata from the Crossref REST API (`api.crossref.org/works/<DOI>`), which returns the registered title, authors, venue, volume and pages;
* the arXiv abstract page, including the author-supplied comments, journal-ref and related-DOI fields.

Other rules:

* Metrics are reported **only** when read in an abstract or official page, and always with their dataset and protocol.
* Fields marked "not verified" were not visible in the sources read. Most entries were verified at **abstract and metadata level**: experimental details beyond the abstract (preprocessing, splits) are marked "not stated in abstract" rather than guessed.
* Code links are given only when the paper's own page, the arXiv page or the authors' project page names them, or when the repository name matches the official project and was confirmed by a search result. Bare existence of a GitHub repository is labelled as such.
* **Type codes:** **PR** = peer-reviewed (journal, conference or workshop proceedings, confirmed via DOI metadata or official proceedings page). **PR\*** = peer-reviewed according to the authors' arXiv comment only; the proceedings entry was not independently seen. **Preprint** = arXiv or Preprints.org only.
* **Hardware assumptions for the reproducibility notes:** Windows workstation, 20 CPU threads, 24 GB RAM, RTX 4060 8 GB. The installed PyTorch is `2.12.0+cpu` (CUDA unavailable). XGBoost 3.2.0 and scikit-learn 1.9.0 are installed. LightGBM and CatBoost are **not** installed. These versions were checked locally on 2026-11-17.

---

## 2. Summary matrix

Relevance to Aegis runs from 1 (background) to 5 (directly shapes R3 or the paper). "Code" means official code verified (Y), not found (N), or partial/unverified status (?).

| # | Paper (short) | Year | Venue | Type | Fam. | Code | Rel. |
|---|---|---|---|---|---|---|---|
| A1 | Gorishniy et al., FT-Transformer / "Revisiting DL for tabular data" | 2021 (found.) | NeurIPS | PR | A | Y | 3 |
| A2 | Grinsztajn et al., "Why do tree-based models still outperform…" | 2022 | NeurIPS D&B | PR | A | N | 4 |
| A3 | McElfresh et al., "When do neural nets outperform boosted trees…" | 2023 | NeurIPS D&B | PR | A | ? | 4 |
| A4 | Gorishniy et al., TabR | 2024 | ICLR | PR | A | Y | 3 |
| A5 | Gorishniy et al., TabM | 2025 | ICLR | PR | A | Y | 4 |
| A6 | Hollmann et al., TabPFN (v2) | 2025 | Nature | PR | A | Y | 3 |
| A7 | Qu et al., TabICL | 2025 | ICML (PMLR 267) | PR | A | Y | 4 |
| A8 | Qu et al., TabICLv2 | 2026 | ICML 2026 (per arXiv comment) | PR\* | A | Y | 3 |
| A9 | García et al., TabPFN/TabICL for tabular IDS | 2025 | Electronics (MDPI) | PR | A | ? | 4 |
| A10 | Butt et al., Tabular representation learning for NIDS | 2026 | IEEE CSR 2026 (per arXiv comment) | PR\* | A/C | N | 4 |
| B1 | Sommer & Paxson, "Outside the Closed World" | 2010 (found.) | IEEE S&P | PR | B | — | 4 |
| B2 | Bendale & Boult, OpenMax | 2016 (found.) | CVPR | PR | B | Y | 3 |
| B3 | Jordaney et al., Transcend | 2017 (found.) | USENIX Security | PR | B | ? | 5 |
| B4 | Siffer et al., SPOT/DSPOT (EVT for streams) | 2017 (found.) | KDD | PR | B | ? | 3 |
| B5 | Ruff et al., Deep SVDD | 2018 (found.) | ICML | PR | B | N | 2 |
| B6 | Liu et al., Energy-based OOD | 2020 (found.) | NeurIPS | PR | B | ? | 3 |
| B7 | Gibbs & Candès, Adaptive conformal inference | 2021 | NeurIPS | PR | B | N | 5 |
| B8 | Yang et al., CADE | 2021 | USENIX Security | PR | B | Y | 4 |
| B9 | Sun et al., Deep kNN OOD | 2022 | ICML | PR | B | Y | 5 |
| B10 | Barbero et al., Transcending Transcend | 2022 | IEEE S&P | PR | B | ? | 5 |
| B11 | Bates et al., Conformal p-values for outliers | 2023 | Ann. Statist. | PR | B | N | 5 |
| B12 | Barber et al., Conformal prediction beyond exchangeability | 2023 | Ann. Statist. | PR | B | N | 5 |
| B13 | Verkerken et al., Multi-stage hierarchical NIDS (zero-day) | 2023 | IEEE TNSM | PR | B | N | 5 |
| B14 | Ahmad et al., Zero-day attack detection SLR | 2023 | Artif. Intell. Rev. | PR | B | — | 2 |
| B15 | Souza et al., Open-set Energy-based Flow Classifier | 2025 | Computers & Security | PR | B | N | 4 |
| B16 | Wilkie et al., Contrastive loss for zero-day NIDS (CLOSR) | 2026 | IEEE TNSM | PR | B | Y | 5 |
| B17 | Rheey & Park, Conformal false-alarm control for O-RAN IDS | 2026 | ICML 2026 workshop (AI4NextG) | PR (workshop) | B | N | 5 |
| B18 | Nayak, ThreatFormer-IDS | 2026 | AICCONF 2026 (IEEE) | PR | B/D | N | 3 |
| B19 | Fuhrman et al., CND-IDS | 2025 | arXiv | Preprint | B | N | 3 |
| B20 | Qiu et al., VAEMax | 2024 | arXiv (ICTC 2024 claimed) | Preprint | B | N | 2 |
| B21 | Alzubi & Stahl, UNAD+ | 2026 | arXiv | Preprint | B | N | 2 |
| C1 | Pontes et al., Energy-based Flow Classifier (inverse Potts) | 2021 | IEEE TNSM | PR | B/C | N | 3 |
| C2 | Engelen et al., Troubleshooting CICIDS2017 | 2021 | IEEE SPW (WTMC) | PR | C | Y | 5 |
| C3 | Rosay et al., LYCOS-IDS2017 | 2021 | WI-IAT | PR | C | ? | 4 |
| C4 | Verkerken et al., Inter-dataset unsupervised NIDS | 2022 | J. Netw. Syst. Manage. | PR | C | N | 4 |
| C5 | Sarhan et al., Standard NetFlow feature set (NF-v2) | 2022 | Mobile Netw. Appl. | PR | C | ? | 5 |
| C6 | Sarhan et al., Standard feature sets: generalisability & explainability | 2022 | Big Data Research | PR | C | N | 4 |
| C7 | Apruzzese et al., Cross-evaluation of ML-NIDS (XeNIDS) | 2022 | IEEE TNSM | PR | C | N | 4 |
| C8 | Liu et al., Error prevalence in CIC-IDS-2017 / CSE-CIC-IDS-2018 | 2022 | IEEE CNS | PR | C | Y | 5 |
| C9 | Lanvin et al., Errors in CICIDS2017 | 2022/2023 | CRiSIS (LNCS 13857) | PR | C | ? | 4 |
| C10 | Layeghy & Portmann, Explainable cross-domain evaluation | 2023 | Comput. Electr. Eng. | PR | C | N | 4 |
| C11 | Flood et al., Bad design smells in NIDS datasets | 2024 | IEEE EuroS&P | PR | C | N | 4 |
| C12 | Cantone et al., Cross-dataset generalisation (LycoS-Unicas-IDS2018) | 2024 | IEEE Access | PR | C | N | 5 |
| C13 | Jiang et al., Open DGML | 2024 | Applied Sciences | PR | C | N | 2 |
| C14 | Wang et al., Learn-IDS | 2024 | Electronics (MDPI) | PR | C | Y | 3 |
| C15 | Pinto et al., Flow exporter impact (HERA) | 2025 | ICISSP 2025 (per arXiv comment) | PR\* | C | N | 5 |
| C16 | Verkerken et al., ConCap | 2026 | IEEE SaTML | PR | C | ? | 4 |
| C17 | Luay et al., Temporal NetFlow features (NF-v3) | 2026 | IEEE Access | PR | C/D | ? | 4 |
| C18 | Mishra et al., Cross-dataset harmonised IDS framework | 2026 | PLOS ONE | PR | C | N | 2 |
| D1 | Mirsky et al., Kitsune | 2018 (found.) | NDSS | PR | D | ? | 4 |
| D2 | Corsini et al., Sequential ML for NIDS evaluation | 2021 | ARES | PR | D | N | 4 |
| D3 | Lo et al., E-GraphSAGE | 2022 | IEEE/IFIP NOMS | PR | D | ? | 4 |
| D4 | King & Huang, Euler | 2022 | NDSS | PR | D | ? | 3 |
| D5 | Caville et al., Anomal-E | 2022 | Knowledge-Based Systems | PR | D | N | 4 |
| D6 | Lo et al., XG-BoT | 2023 | Internet of Things | PR | D | N | 4 |
| D7 | Manocchio et al., FlowTransformer | 2024 | Expert Syst. Appl. | PR | D | Y | 3 |
| D8 | Moczkodan & Ragab, "Do Transformers actually help…" | 2026 | arXiv | Preprint | D | Y | 4 |
| E1 | Warnecke et al., Evaluating explanation methods in security | 2020 | IEEE EuroS&P | PR | E | ? | 3 |
| E2 | Arp et al., Dos and Don'ts of ML in security | 2022 | USENIX Security | PR | E | — | 5 |
| E3 | Apruzzese et al., SoK: Pragmatic assessment of ML-NIDS | 2023 | IEEE EuroS&P | PR | E | ? | 4 |
| E4 | Youssef, Stream assembly as uncontrolled treatment | 2026 | arXiv | Preprint | E | ? | 3 |

**Totals:** 61 verified papers. 56 are peer-reviewed: 53 confirmed via DOI metadata or official proceedings (PR, including one workshop paper, B17) and 3 per author comment only (PR\*: A8, A10, C15). 5 are preprint-only (B19, B20, B21, D8, E4). 8 are marked foundational (pre-2023 and outside the date window). Family E (evaluation methodology) is cross-cutting.

The GBDT and forest baselines (Breiman 2001; Geurts et al. 2006; Chen & Guestrin 2016; Ke et al. 2017; Prokhorenkova et al. 2018) were verified for the reference list only. They are not counted above.

---

## 3. Per-paper entries

Field legend:

* **Venue/type** — venue and type code.
* **ID** — DOI and official URL.
* **Method** — architecture or method.
* **Data** — datasets and preprocessing.
* **Protocol** — experimental protocol. *Unseen-family*, *cross-dataset* and *temporal* are flagged explicitly.
* **Metrics** — reported metrics, with dataset context.
* **+ / −** — strengths and limitations.
* **Code** — code availability.
* **Repro** — reproducibility on our hardware.
* **Rel.** — relevance to Aegis.

### A. Advanced tabular machine learning

**A1. Revisiting Deep Learning Models for Tabular Data (FT-Transformer)** — *foundational*
* **Authors:** Y. Gorishniy, I. Rubachev, V. Khrulkov, A. Babenko.
* **Venue/type:** NeurIPS 2021, PR.
* **ID:** no DOI. arXiv [2106.11959](https://arxiv.org/abs/2106.11959) (camera-ready per arXiv comment).
* **Method:** a ResNet-like MLP baseline and FT-Transformer, which tokenises each feature and applies a Transformer.
* **Data:** a range of public tabular benchmarks (not NIDS); details are not stated in the abstract.
* **Protocol:** same training and tuning protocol for all models, including GBDT. No unseen-class, cross-dataset or temporal evaluation.
* **Metrics:** qualitative only in the abstract: FT-Transformer beats other DL models on most tasks, and "there is still no universally superior solution" compared with GBDT.
* **+ / −:**
  * \+ Strong, widely used DL baseline.
  * − Attention over features costs O(d²) per layer. At 77 features and about 0.5 M rows, CPU training is slow.
* **Code:** Y, [yandex-research/tabular-dl-revisiting-models](https://github.com/yandex-research/tabular-dl-revisiting-models) (listed on arXiv).
* **Repro:** CPU possible but slow at our scale (estimate, not measured). GPU would require a CUDA PyTorch build.
* **Rel.:** 3. Historical DL baseline. Superseded for R3 by TabM (A5).

**A2. Why do tree-based models still outperform deep learning on typical tabular data?**
* **Authors:** L. Grinsztajn, E. Oyallon, G. Varoquaux.
* **Venue/type:** NeurIPS 2022 Datasets & Benchmarks, PR.
* **ID:** no DOI (arXiv DOI 10.48550/arXiv.2207.08815). [NeurIPS PDF](https://papers.nips.cc/paper_files/paper/2022/file/0378c7692da36807bdec87ab043cdadc-Paper-Datasets_and_Benchmarks.pdf), [arXiv](https://arxiv.org/abs/2207.08815).
* **Method:** benchmark of tree ensembles (XGBoost, RF) against DL, with an analysis of inductive biases.
* **Data:** 45 tabular datasets of about 10k samples. Not NIDS.
* **Protocol:** accounts for the cost of hyperparameter search (about 20,000 compute-hours per learner, per abstract). IID only.
* **Metrics:** qualitative: trees remain state of the art on medium-sized data. NNs struggle with uninformative features, irregular functions and non-rotation-invariant data.
* **+ / −:**
  * \+ Explains *why* trees suit CICFlowMeter-like features, which are heavy-tailed, irregular and partly redundant.
  * − The medium-size regime is smaller than our ~10⁵–10⁶ flows.
* **Code:** benchmark released; repository URL not seen on the pages read (N).
* **Repro:** N/A (benchmark).
* **Rel.:** 4. Justifies tree-based evidence models in R3.

**A3. When Do Neural Nets Outperform Boosted Trees on Tabular Data?**
* **Authors:** D. McElfresh, S. Khandagale, J. Valverde, V. Prasad C, B. Feuer, C. Hegde, G. Ramakrishnan, M. Goldblum, C. White.
* **Venue/type:** NeurIPS 2023 Datasets & Benchmarks, PR.
* **ID:** no DOI. [arXiv 2305.02997](https://arxiv.org/abs/2305.02997), [NeurIPS page](https://neurips.cc/virtual/2023/poster/73658).
* **Method:** 19 algorithms on 176 datasets.
* **Data:** public tabular datasets (not NIDS).
* **Protocol:** IID.
* **Metrics:** qualitative. The NN-versus-GBDT gap is often negligible, and light tuning of GBDT matters more. GBDTs handle skewed and heavy-tailed features better. TabPFN was strongest on average when training sets were subsampled to 3,000 rows. These are as summarised on the official pages and the search abstract.
* **+ / −:**
  * \+ The heavy-tail finding matches flow statistics.
  * − IID only.
* **Code:** TabZilla suite released; the official URL was not confirmed (?).
* **Repro:** N/A.
* **Rel.:** 4. Supports GBDT-first and lightly tuned baselines.

**A4. TabR: Tabular Deep Learning Meets Nearest Neighbors**
* **Authors:** Y. Gorishniy, I. Rubachev, N. Kartashev, D. Shlenskii, A. Kotelnikov, A. Babenko.
* **Venue/type:** ICLR 2024, PR.
* **ID:** no DOI. [ICLR proceedings](https://proceedings.iclr.cc/paper_files/paper/2024/hash/4ef594af0d9a519db8fb292452c461fa-Abstract-Conference.html), [arXiv 2307.14338](https://arxiv.org/abs/2307.14338).
* **Method:** feed-forward network with an attention-like kNN retrieval module that uses neighbours' features **and labels**.
* **Data:** public benchmarks up to several million objects (not NIDS).
* **Protocol:** IID.
* **Metrics:** qualitative: best average among tabular DL models, and it beats GBDT on the "GBDT-friendly" benchmark.
* **+ / −:**
  * \+ Retrieval is conceptually close to Aegis's kNN novelty evidence.
  * − Retrieval over the training set at inference time. Not designed for OOD or open-set use.
* **Code:** Y, [yandex-research/tabular-dl-tabr](https://github.com/yandex-research/tabular-dl-tabr).
* **Repro:** GPU-oriented. CPU feasible only on subsamples (estimate).
* **Rel.:** 3. Interesting as a learned-retrieval alternative to raw kNN distance. Not prioritised for R3.

**A5. TabM: Advancing Tabular Deep Learning with Parameter-Efficient Ensembling**
* **Authors:** Y. Gorishniy, A. Kotelnikov, A. Babenko.
* **Venue/type:** ICLR 2025, PR.
* **ID:** no DOI. [ICLR proceedings](https://proceedings.iclr.cc/paper_files/paper/2025/hash/c1ba41c694834aeef91ae161711d4939-Abstract-Conference.html), [arXiv 2410.24210](https://arxiv.org/abs/2410.24210).
* **Method:** an MLP that imitates an ensemble of MLPs (BatchEnsemble-style shared weights) and emits multiple predictions per object.
* **Data:** large public tabular benchmark (not NIDS).
* **Protocol:** IID.
* **Metrics:** qualitative: best among tabular DL models. MLP-based models (including TabM) outperform attention- and retrieval-based ones in performance and practicality.
* **+ / −:**
  * \+ Simple MLP, so CPU-trainable.
  * \+ Its multiple predictions give a natural disagreement or uncertainty signal that could serve as extra conformal evidence (our hypothesis, not tested by the authors).
  * − No OOD evaluation.
* **Code:** Y, [yandex-research/tabm](https://github.com/yandex-research/tabm).
* **Repro:** **CPU feasible** at our scale (MLP; estimate hours, not measured).
* **Rel.:** 4. Best-supported DL candidate for R3.

**A6. Accurate predictions on small data with a tabular foundation model (TabPFN v2)**
* **Authors:** N. Hollmann, S. Müller, L. Purucker, A. Krishnakumar, M. Körfer, S. B. Hoo, R. T. Schirrmeister, F. Hutter.
* **Venue/type:** Nature 637:319–326, 2025, PR.
* **ID:** DOI [10.1038/s41586-024-08328-6](https://doi.org/10.1038/s41586-024-08328-6).
* **Method:** Transformer pretrained on millions of synthetic datasets that performs in-context learning.
* **Data:** not NIDS.
* **Protocol:** IID.
* **Metrics:** per abstract, outperforms previous methods on datasets with **up to 10,000 samples** by a wide margin, with less training time.
* **+ / −:**
  * \+ No tuning needed.
  * \+ Supports density estimation and embeddings (per abstract).
  * − The claimed regime (≤ 10k samples) is far below our training sizes, so subsampling is required.
* **Code:** Y, [PriorLabs/TabPFN](https://github.com/PriorLabs/TabPFN), weights on Hugging Face. The licence terms were not verified.
* **Repro:** CPU inference possible on small contexts. GPU strongly preferred (not measured).
* **Rel.:** 3. Superseded for our data size by TabICL (A7). Excluded from the R3 core.

**A7. TabICL: A Tabular Foundation Model for In-Context Learning on Large Data**
* **Authors:** J. Qu, D. Holzmüller, G. Varoquaux, M. Le Morvan.
* **Venue/type:** ICML 2025 (PMLR 267:50817–50847), PR.
* **ID:** no DOI. [PMLR](https://proceedings.mlr.press/v267/qu25d.html), [arXiv 2502.05564](https://arxiv.org/abs/2502.05564).
* **Method:** column-then-row attention builds row embeddings, then a Transformer performs in-context learning. Pretrained on synthetic data of up to 60k samples.
* **Data:** TALENT benchmark, 200 classification datasets.
* **Protocol:** IID.
* **Metrics** (abstract):
  * on par with TabPFNv2 on the 200 TALENT datasets, and up to 10× faster;
  * on the 53 datasets with more than 10k samples, surpasses both TabPFNv2 and CatBoost;
  * handles 500k samples "on affordable resources" (hardware unspecified).
* **+ / −:**
  * \+ The scale is closest to ours among foundation models.
  * \+ No hyperparameter tuning.
  * − Hardware requirements unspecified.
  * − Context-size limits imply subsampling of our training set.
* **Code:** Y, [soda-inria/tabicl](https://github.com/soda-inria/tabicl) (pretrained models released).
* **Repro:** CPU inference feasibility **unverified**. A pilot on a 10k–50k context is required. GPU would need a CUDA PyTorch build.
* **Rel.:** 4. Candidate "advanced" method for R3 if a CPU pilot succeeds.

**A8. TabICLv2: A better, faster, scalable, and open tabular foundation model**
* **Authors:** J. Qu, D. Holzmüller, G. Varoquaux, M. Le Morvan.
* **Venue/type:** ICML 2026 per arXiv comment ("Published at ICML 2026"). Proceedings page not seen, so PR\*.
* **ID:** [arXiv 2602.11139](https://arxiv.org/abs/2602.11139).
* **Method:** new synthetic-data engine, scalable softmax attention, Muon optimiser.
* **Data/protocol:** TabArena and TALENT, IID.
* **Metrics** (abstract): without tuning, outperforms RealTabPFN-2.5 on TabArena and TALENT. Million-scale datasets fit in under 50 GB of GPU memory.
* **+ / −:**
  * \+ Fully open: inference, pretraining and data-generation code.
  * − The stated memory scale exceeds our 8 GB GPU.
* **Code:** Y, [soda-inria/tabicl](https://github.com/soda-inria/tabicl).
* **Repro:** large-data mode is not feasible on our GPU. Small-context CPU inference is unknown.
* **Rel.:** 3. Probably the "TabICL (2026)" lead (Section 6).

**A9. Foundation Models for Cybersecurity: A Comprehensive Multi-Modal Evaluation of TabPFN and TabICL for Tabular Intrusion Detection**
* **Authors:** P. García, J. de Curtò, I. de Zarzà, J. C. Cano, C. T. Calafate.
* **Venue/type:** Electronics 14(19):3792, 2025, PR.
* **ID:** DOI [10.3390/electronics14193792](https://doi.org/10.3390/electronics14193792). Abstract read via Crossref; the MDPI page returned 403.
* **Method:** compares TabPFN, TabICL, LLMs and traditional ML.
* **Data:** CIC-IDS2017, N-BaIoT, CIC-UNSW. Preprocessing not stated in the abstract.
* **Protocol:** "model-appropriate evaluation protocols". Foundation models use "fractions of the available training data". A "cross-dataset validation" is mentioned but not described. **No unseen-family protocol is stated.**
* **Metrics** (abstract): TabICL 99.59% accuracy on CIC-IDS2017. The foundation models achieve non-zero recall on all classes, including Heartbleed and Infiltration, whereas the ensembles "completely fail on several minority classes".
* **+ / −:**
  * \+ The only verified IDS-specific TabPFN/TabICL study.
  * \+ The rare-class finding is relevant to Aegis's Bot and WebAttack weakness.
  * − Accuracy on IID CIC-IDS2017 is not comparable with Aegis's LOAFO recall at a fixed FPR.
  * − Closed-set.
* **Code:** not stated in the abstract (?).
* **Repro:** as A6/A7.
* **Rel.:** 4. Direct motivation for including TabICL in R3 under *our* protocol.

**A10. Evaluating Tabular Representation Learning for Network Intrusion Detection**
* **Authors:** M. U. Butt, A. Hotho, D. Schlör.
* **Venue/type:** IEEE International Conference on Cyber Security and Resilience (CSR) 2026, per arXiv comment, so PR\*.
* **ID:** [arXiv 2605.02519](https://arxiv.org/abs/2605.02519).
* **Method:** TabICL embeddings, autoencoders and end-to-end Transformers, each feeding supervised classifiers or unsupervised anomaly detectors.
* **Data:** NetFlow benchmark datasets. Only CIDDS is named in the abstract.
* **Protocol:** within-dataset, plus **cross-dataset** transfer. Unseen-family protocol not mentioned.
* **Metrics** (abstract, qualitative):
  * TabICL is best on CIDDS;
  * autoencoders tie with end-to-end Transformers for best average rank;
  * supervised methods substantially outperform unsupervised detectors;
  * cross-dataset transfer "varies widely across source-target pairs".
* **+ / −:**
  * \+ Recent, NetFlow-based, includes cross-dataset results.
  * − No calibrated-FPR or open-set evaluation.
* **Code:** not listed (N).
* **Repro:** depends on TabICL (A7).
* **Rel.:** 4. Matches the "2026 tabular representation learning study for IDS" lead (Section 6).

### B. Open-set, zero-day and calibrated detection

**B1. Outside the Closed World: On Using Machine Learning for Network Intrusion Detection** — *foundational*
* **Authors:** R. Sommer, V. Paxson.
* **Venue/type:** IEEE S&P 2010, pp. 305–316, PR.
* **ID:** DOI 10.1109/SP.2010.25. [ICSI PDF](https://www1.icsi.berkeley.edu/pubs/networking/outsidethe10.pdf).
* **Method:** position paper on why ML-based IDS is harder than other ML applications.
* **Data/protocol/metrics:** N/A.
* **+ / −:**
  * \+ Defines the closed-world problem Aegis-OSR addresses.
  * − No experiments.
* **Code:** —.
* **Rel.:** 4. Motivation.

**B2. Towards Open Set Deep Networks (OpenMax)** — *foundational*
* **Authors:** A. Bendale, T. Boult.
* **Venue/type:** CVPR 2016, pp. 1563–1572, PR.
* **ID:** DOI 10.1109/CVPR.2016.173 (Crossref-checked). [CVF](https://openaccess.thecvf.com/content_cvpr_2016/html/Bendale_Towards_Open_Set_CVPR_2016_paper.html).
* **Method:** an OpenMax layer that estimates the probability of an unknown class by applying meta-recognition to penultimate-layer activations. The abstract claims bounded open-space risk. EVT calibration is discussed in the supplementary material, per the search result; the exact EVT form was not read.
* **Data:** ImageNet 2012 plus fooling and open-set images.
* **Protocol:** open-set (vision).
* **Metrics:** not read.
* **+ / −:**
  * \+ Canonical EVT open-set method; basis of VAEMax (B20).
  * − Designed for deep features, not tabular flows.
* **Code:** Y, [abhijitbendale/OSDN](https://github.com/abhijitbendale/OSDN) (described as the paper's code).
* **Repro:** CPU feasible on top of any classifier's scores.
* **Rel.:** 3. An EVT baseline that Aegis lacks (Aegis uses exponential tail extrapolation, not a fitted EVT; see CLAIM_AUDIT §2).

**B3. Transcend: Detecting Concept Drift in Malware Classification Models** — *foundational*
* **Authors:** R. Jordaney, K. Sharad, S. K. Dash, Z. Wang, D. Papini, I. Nouretdinov, L. Cavallaro.
* **Venue/type:** USENIX Security 2017, pp. 625–642, PR.
* **ID:** no DOI. [USENIX](https://www.usenix.org/conference/usenixsecurity17/technical-sessions/presentation/jordaney).
* **Method:** statistical comparison of deployment samples with training data (conformal evaluation, per the follow-up B10). Per-class rejection thresholds are found by an optimisation that trades performance against the number of rejected samples (per the official page summary).
* **Data:** Android and Windows malware.
* **Protocol:** **temporal drift**.
* **Metrics:** not read.
* **+ / −:**
  * \+ Closest prior use of conformal p-values in security. Aegis's Mondrian attribution is in the same spirit.
  * − Malware, not NIDS. Thresholds are tuned, not a finite-sample FPR guarantee.
* **Code:** see B10.
* **Rel.:** 5.

**B4. Anomaly Detection in Streams with Extreme Value Theory (SPOT/DSPOT)** — *foundational*
* **Authors:** A. Siffer, P.-A. Fouque, A. Termier, C. Largouët.
* **Venue/type:** KDD 2017, pp. 1067–1075, PR.
* **ID:** DOI [10.1145/3097983.3098144](https://doi.org/10.1145/3097983.3098144).
* **Method:** EVT-based streaming anomaly thresholds. Only the title and metadata were read; method details (e.g., the tail model and drift variant) are **not verified** here.
* **Data/protocol/metrics:** not read beyond metadata.
* **+ / −:**
  * \+ A principled version of Aegis's exponential-tail extrapolation.
  * \+ Streaming threshold adaptation is relevant to R4.
* **Code:** a `libspot` project page exists ([asiffer.github.io/libspot](https://asiffer.github.io/libspot/about)); official status not confirmed (?).
* **Repro:** CPU, trivial.
* **Rel.:** 3.

**B5. Deep One-Class Classification (Deep SVDD)** — *foundational*
* **Authors:** L. Ruff, R. Vandermeulen, N. Görnitz, L. Deecke, S. A. Siddiqui, A. Binder, E. Müller, M. Kloft.
* **Venue/type:** ICML 2018 (PMLR 80:4393–4402), PR.
* **ID:** [PMLR](https://proceedings.mlr.press/v80/ruff18a.html).
* **Method:** learns a hypersphere enclosing normal data.
* **Data:** MNIST, CIFAR-10, GTSRB adversarial examples.
* **Protocol:** one-class (vision).
* **Metrics:** not read.
* **+ / −:**
  * \+ Canonical deep one-class baseline.
  * − Aegis's autoencoder novelty ablation already underperforms kNN in LOAFO (RESULTS.md: AE-novelty 0.562 vs kNN-novelty Aegis-OSR 0.706). Deep SVDD is not expected to change the picture, but this is untested.
* **Code:** not linked from PMLR (N).
* **Repro:** CPU feasible.
* **Rel.:** 2.

**B6. Energy-based Out-of-distribution Detection** — *foundational*
* **Authors:** W. Liu, X. Wang, J. Owens, Y. Li.
* **Venue/type:** NeurIPS 2020, PR.
* **ID:** no DOI. [NeurIPS](https://neurips.cc/virtual/2020/poster/17313), [arXiv 2010.03759](https://arxiv.org/abs/2010.03759).
* **Method:** OOD score = negative free energy (logsumexp of logits).
* **Data:** vision benchmarks.
* **Protocol:** OOD.
* **Metrics:** not read.
* **+ / −:** \+ Already an Aegis baseline ("XGB + Energy", RESULTS.md LOAFO 0.457 vs Aegis-OSR 0.706 at α = 1%).
* **Code:** a repository `wetliu/energy_ood` exists under the first author's handle; not confirmed from the paper page (?).
* **Repro:** CPU, trivial.
* **Rel.:** 3.

**B7. Adaptive Conformal Inference Under Distribution Shift**
* **Authors:** I. Gibbs, E. Candès.
* **Venue/type:** NeurIPS 2021 (oral), PR.
* **ID:** no DOI. [NeurIPS proceedings](https://proceedings.neurips.cc/paper/2021/hash/0d441de75945e5acbc865406fc9a2559-Abstract.html), [arXiv 2106.00170](https://arxiv.org/abs/2106.00170).
* **Method:** online update of the miscoverage level, which gives **long-run** coverage without exchangeability.
* **Data:** two real-world datasets (not security).
* **Protocol:** sequential.
* **Metrics:** qualitative (robust under visible shifts).
* **+ / −:**
  * \+ The exact tool for Aegis's R4 "online FPR monitor". Gives a long-run frequency guarantee, not a per-batch one.
  * − Needs feedback (here: confirmed-benign labels) to update.
* **Code:** not found (N).
* **Repro:** CPU, trivial.
* **Rel.:** 5. Already-published methodology for what Aegis's adaptation would need; reduces our novelty claim there.

**B8. CADE: Detecting and Explaining Concept Drift Samples for Security Applications**
* **Authors:** L. Yang, W. Guo, Q. Hao, A. Ciptadi, A. Ahmadzadeh, X. Xing, G. Wang.
* **Venue/type:** USENIX Security 2021, pp. 2327–2344, PR.
* **ID:** no DOI. [USENIX](https://www.usenix.org/conference/usenixsecurity21/presentation/yang).
* **Method:** maps samples to a low-dimensional space with a distance function learned by contrastive learning on existing training labels. Detects individual drifting samples, with a distance-based explanation method (abstract).
* **Data:** Android malware and **network intrusion** (supplementary material includes a CSE-CIC-IDS2018 case study).
* **Protocol:** **unseen-family drift** (previously unseen families held out).
* **Metrics:** not stated on the official page; full paper not read.
* **+ / −:**
  * \+ Closest prior on "detect *and explain* novel-family samples" in NIDS.
  * − No calibrated FPR. Explanation is per sample, not shift-versus-novelty.
* **Code:** Y, [whyisyoung/CADE](https://www.github.com/whyisyoung/CADE) (academic-only licence per search result).
* **Repro:** CPU feasible (small AE).
* **Rel.:** 4. A must-cite comparator, and a possible R3 baseline.

**B9. Out-of-Distribution Detection with Deep Nearest Neighbors**
* **Authors:** Y. Sun, Y. Ming, X. Zhu, Y. Li.
* **Venue/type:** ICML 2022 (PMLR 162:20827–20840), PR.
* **ID:** [PMLR](https://proceedings.mlr.press/v162/sun22d.html).
* **Method:** non-parametric k-th nearest-neighbour distance in (normalised) feature space, with no distributional assumption.
* **Data:** vision.
* **Metrics** (abstract): with the same ImageNet-1k model, reduces FPR@TPR95 by 24.77% compared with SSD+ (parametric Mahalanobis).
* **+ / −:**
  * \+ This is Aegis's novelty evidence.
  * − Raw-feature kNN in Aegis is not the learned-embedding kNN of the paper.
* **Code:** Y, [deeplearning-wisc/knn-ood](https://github.com/deeplearning-wisc/knn-ood).
* **Repro:** CPU (FAISS or sklearn).
* **Rel.:** 5.

**B10. Transcending Transcend: Revisiting Malware Classification in the Presence of Concept Drift**
* **Authors:** F. Barbero, F. Pendlebury, F. Pierazzi, L. Cavallaro.
* **Venue/type:** IEEE S&P 2022, pp. 805–823 per Crossref (the Royal Holloway record lists 1165–1183; not reconciled), PR.
* **ID:** DOI 10.1109/SP46214.2022.9833659. [IEEE Xplore](https://ieeexplore.ieee.org/document/9833659), [arXiv 2010.03856](https://arxiv.org/abs/2010.03856).
* **Method:** classification with rejection built on conformal prediction theory. Develops "two additional conformal evaluators" that match or surpass Transcend with much lower computational overhead (abstract; the evaluators are not named in the abstract). Released as TRANSCENDENT.
* **Data:** Android malware over time.
* **Protocol:** **temporal**.
* **Metrics:** not read.
* **Notes:** the UCL S2Lab project page lists an **erratum (December 2023)**; check it before citing numbers.
* **+ / −:**
  * \+ Methodological template for conformal rejection under drift.
  * − Malware domain. Rejection, not FPR control on benign traffic.
* **Code:** TRANSCENDENT released per the authors. The exact repository URL was not verified (`github.com/s2labres/transcendent` returned 404).
* **Repro:** CPU.
* **Rel.:** 5.

**B11. Testing for Outliers with Conformal p-values**
* **Authors:** S. Bates, E. Candès, L. Lei, Y. Romano, M. Sesia.
* **Venue/type:** Annals of Statistics 51(1):149–178, 2023, PR.
* **ID:** DOI [10.1214/22-AOS2244](https://doi.org/10.1214/22-AOS2244).
* **Method** (abstract): standard conformal p-values are marginally valid but mutually dependent. The authors prove positive dependence, enabling exact FDR control in a weak marginal sense. They introduce **calibration-conditional** p-values that are valid conditionally on the calibration data. They also derive a **uniform confidence bound on the false-positive rate of any outlier detector as a function of its threshold**.
* **Data:** real and simulated (not named in the abstract).
* **Protocol:** statistical theory plus experiments.
* **Metrics:** not read.
* **+ / −:**
  * \+ Theoretical basis of Aegis's FPR guarantee.
  * \+ The calibration-conditional p-values and the uniform FPR bound address the caveat that Aegis's guarantee holds only on average over calibration draws. Aegis does not yet state this caveat.
* **Code:** a related repository (`msesia/conditional-conformal-pvalues`) appears in search results; not confirmed official (N).
* **Repro:** CPU.
* **Rel.:** 5.

**B12. Conformal Prediction Beyond Exchangeability**
* **Authors:** R. F. Barber, E. Candès, A. Ramdas, R. J. Tibshirani.
* **Venue/type:** Annals of Statistics 51(2):816–845, 2023, PR.
* **ID:** DOI [10.1214/23-AOS2276](https://doi.org/10.1214/23-AOS2276).
* **Method** (abstract): weighted quantiles for robustness to distribution drift, plus a randomisation technique for non-symmetric fitting algorithms (e.g., weighting recent data). Provably robust: loses less coverage when exchangeability fails, and keeps standard coverage when it holds. The precise form of the coverage-gap bound was not read.
* **+ / −:**
  * \+ Weighting recent calibration data is a direct candidate remedy for the Friday drift.
  * − Robustness depends on how far the data are from exchangeable, which is unknown in deployment.
* **Code:** N.
* **Repro:** CPU.
* **Rel.:** 5.

**B13. A Novel Multi-Stage Approach for Hierarchical Intrusion Detection**
* **Authors:** M. Verkerken, L. D'hooge, D. Sudyana, Y.-D. Lin, T. Wauters, B. Volckaert, F. De Turck.
* **Venue/type:** IEEE TNSM 20:3915–3929, 2023, PR.
* **ID:** DOI 10.1109/TNSM.2023.3259474. Accepted version at [imec](https://imec-publications.be/handle/20.500.12860/43401).
* **Method:** multi-stage hierarchical intrusion detection, designed to scale and to detect unknown (zero-day) attacks. Stage details beyond the abstract (e.g., which stage is a benign-only anomaly detector) were **not verified**. The abstract refers to sets of thresholds.
* **Data:** CIC-IDS-2017 and CSE-CIC-IDS-2018.
* **Protocol:** includes **zero-day attacks**.
* **Metrics** (abstract):
  * up to 96% balanced accuracy;
  * best models with balanced thresholds correctly classified **41 of 47 zero-day attacks (87%)**;
  * up to 69% bandwidth reduction.
* **Note:** the 47 count coincides with Aegis's 47 natural unknowns (Infiltration 36 + Heartbleed 11, RESULTS.md gate section). It may be the same set, but this was **not verified**. Thresholds and protocols differ, so 41/47 is **not comparable** with the Aegis gate's 29/47 at α = 1%.
* **+ / −:**
  * \+ The **closest architectural prior** to Aegis's "known-family classifier + benign-novelty" design.
  * − No finite-sample FPR guarantee. Thresholds are tuned.
* **Code:** not found (N).
* **Repro:** CPU (classical ML).
* **Rel.:** 5. Must be cited and, ideally, re-implemented as an R3 baseline.

**B14. Zero-day attack detection: a systematic literature review**
* **Authors:** R. Ahmad, I. Alsmadi, W. Alhamdani, L. Tawalbeh.
* **Venue/type:** Artificial Intelligence Review 56:10733–10811, 2023, PR.
* **ID:** DOI 10.1007/s10462-023-10437-z.
* **Content:** survey. Notes that many solutions ignore zero-day attacks during development and testing.
* **Rel.:** 2. Background only.

**B15. A novel open set Energy-based Flow Classifier for Network Intrusion Detection**
* **Authors:** M. M. C. Souza, C. T. Pontes, J. J. C. Gondim, L. P. F. Garcia, L. DaSilva, E. F. M. Cavalcante, M. A. Marotta.
* **Venue/type:** Computers & Security 157:104569, 2025, PR.
* **ID:** DOI 10.1016/j.cose.2025.104569. [arXiv 2109.11224](https://arxiv.org/abs/2109.11224).
* **Method:** multi-class extension of EFC (C1). Potts-model energies per class; unknowns are flagged by energy.
* **Data:** not named in the abstract.
* **Protocol:** open-set (details not in the abstract).
* **Metrics:** "accuracy similar to state of the art" (abstract, qualitative).
* **+ / −:**
  * \+ Single-layer, low complexity, explicitly open-set NIDS.
  * − No FPR guarantee stated.
* **Code:** not listed (N).
* **Repro:** CPU.
* **Rel.:** 4.

**B16. A Novel Contrastive Loss for Zero-Day Network Intrusion Detection (CLOSR)**
* **Authors:** J. Wilkie, H. Hindy, C. Michie, C. Tachtatzis, J. Irvine, R. Atkinson.
* **Venue/type:** IEEE TNSM 23:2064–2076, 2026, PR.
* **ID:** DOI 10.1109/TNSM.2026.3652529. [Strathprints](https://strathprints.strath.ac.uk/95296/), [arXiv 2601.09902](https://arxiv.org/abs/2601.09902).
* **Method:** contrastive loss that learns the benign distribution from benign samples **plus known malign classes**, excluding the zero-day class. Extended to open-set recognition.
* **Data:** **LycoS-IDS2017** (corrected CICIDS2017).
* **Protocol:** **zero-day class held out** (leave-one-attack-out style) and open-set recognition.
* **Metrics** (abstract, LycoS-IDS2017; improvements over unnamed prior models):
  * known-attack AUROC +0.000065;
  * zero-day AUROC +0.060883;
  * open-set OpenAUC +0.170883.
* **+ / −:**
  * \+ The **closest 2026 peer-reviewed prior** to Aegis's LOAFO zero-day study.
  * \+ Uses corrected data, which Aegis does not.
  * − Threshold-free metrics only (AUROC/OpenAUC). No calibrated operating point.
* **Code:** Y, [jackwilkie/CLOSR](https://github.com/jackwilkie/CLOSR).
* **Repro:** PyTorch. CPU training feasibility not verified; small contrastive MLPs are probably CPU-feasible.
* **Rel.:** 5. Strongest R3 open-set comparator with official code.

**B17. Toward Reliable Intrusion Monitoring for O-RAN Based Networks with Conformal False Alarm Control**
* **Authors:** J. Rheey, H. Park. *(Spot-check 2026-11-17: the paper and ICML listing exist, but the author names could not be confirmed without OpenReview sign-in — confirm before citing.)*
* **Venue/type:** ICML 2026 Workshop AI4NextG (poster). PR (workshop), not main conference.
* **ID:** [ICML page](https://icml.cc/virtual/2026/78428), OpenReview `zMogeI2Sbk` (forum not readable without sign-in).
* **Method:** autoencoder with a Mahalanobis distance in reconstruction-error space as non-conformity score. Split-conformal threshold controls the **false-alarm rate under exchangeability**. Per-feature decomposition supports triage.
* **Data:** "5G traffic" (dataset not named).
* **Protocol:** not stated.
* **Metrics:** qualitative: higher detection than a conformal baseline at the same target FAR; microsecond-scale latency.
* **+ / −:**
  * \+ **Direct prior for "conformal FAR control in intrusion detection"**: Aegis cannot claim that idea as new.
  * − Unsupervised only (no known-attack evidence). Wireless domain. No shift analysis on the page.
* **Code:** N.
* **Rel.:** 5. Narrows the Aegis novelty claim (see the gap analysis).

**B18. ThreatFormer-IDS: Robust Transformer Intrusion Detection with Zero-Day Generalization and Explainable Attribution**
* **Authors:** S. Nayak.
* **Venue/type:** 2026 4th Cognitive Models and AI Conference (AICCONF), pp. 1–8, PR.
* **ID:** DOI 10.1109/AICCONF69182.2026.11600642. [arXiv 2603.00185](https://arxiv.org/abs/2603.00185).
* **Method:** Transformer over time-ordered flow windows, combining weighted supervised loss, masked self-supervised learning, PGD adversarial training and Integrated Gradients attribution.
* **Data:** ToN-IoT.
* **Protocol:** **chronological** split, **zero-day held-out families**, adversarial budget sweep.
* **Metrics** (abstract, ToN-IoT):
  * chronological: AUC-PR 0.956, Recall@1%FPR 0.910;
  * zero-day: AUC-PR 0.721, Recall@1%FPR 0.783.
* **+ / −:**
  * \+ Reports a fixed-FPR recall like Aegis.
  * − Single author, 7 pages, baselines unnamed in the abstract, no variance reported. The 1% FPR is set empirically, not guaranteed.
  * − Different dataset, so not comparable with Aegis's 0.706.
* **Code:** N.
* **Repro:** CPU training of a Transformer is slow.
* **Rel.:** 3.

**B19. CND-IDS: Continual Novelty Detection for Intrusion Detection Systems**
* **Authors:** S. Fuhrman, O. Gungor, T. Rosing.
* **Venue/type:** arXiv 2502.14094 (2025), preprint; no venue found.
* **ID:** [arXiv](https://arxiv.org/abs/2502.14094).
* **Method:** continually updated feature extractor plus PCA-reconstruction novelty detector. No attack labels.
* **Data:** not verified.
* **Protocol:** continual / open-world.
* **Metrics** (abstract): up to 6.1× F-score and 6.5× forward-transfer improvement over the best unsupervised continual-learning baseline.
* **+ / −:**
  * \+ Continual setting.
  * − Preprint. Code "upon acceptance" (not found).
* **Rel.:** 3.

**B20. VAEMax: Open-Set Intrusion Detection based on OpenMax and Variational Autoencoder**
* **Authors:** Z. Qiu, D. Zhou, Y. Zhai, B. Liu, L. He, J. Cao.
* **Venue/type:** arXiv 2403.04193 (2024). The comment cites "2024 5th ICTC", but the proceedings were not verified, so treated as a preprint.
* **ID:** [arXiv](https://arxiv.org/abs/2403.04193).
* **Method:** 1D-CNN on payload, OpenMax, then a per-class VAE.
* **Data:** CIC-IDS2017 and CSE-CIC-IDS2018.
* **Protocol and metrics:** not stated in the abstract.
* **Rel.:** 2. Payload-based, which is out of Aegis's flow-feature scope.

**B21. UNAD+: An Explainable Hybrid Framework for Unknown Network Attack Detection**
* **Authors:** S. Alzubi, F. Stahl.
* **Venue/type:** arXiv 2605.22621 (2026), preprint.
* **ID:** [arXiv](https://arxiv.org/abs/2605.22621).
* **Method:** benign-only unsupervised ensemble, supervised refinement on pseudo-labels, then post-hoc XAI.
* **Data:** CICIDS2017 and NSL-KDD.
* **Protocol:** unseen-attack intent; the split is not described.
* **Metrics:** F1 > 98% (abstract).
* **Rel.:** 2. The architecture resembles Aegis's evidence fusion, but evidence is too thin for comparison.

### C. Cross-dataset generalisation, measurement tools and dataset quality

**C1. A New Method for Flow-Based Network Intrusion Detection Using the Inverse Potts Model (EFC)**
* **Authors:** C. F. T. Pontes, M. M. C. de Souza, J. J. C. Gondim, M. Bishop, M. A. Marotta.
* **Venue/type:** IEEE TNSM 18:1125–1136, 2021, PR.
* **ID:** DOI 10.1109/TNSM.2021.3075503. [arXiv 1910.07266](https://arxiv.org/abs/1910.07266).
* **Method:** one-class statistical model of benign flows (Potts energy).
* **Data:** CIDDS-001, CICIDS17, CICDDoS19.
* **Protocol:** includes evaluation on different distributions.
* **Metrics:** qualitative: "more adaptable to different data distributions than classical ML" (as summarised in search results).
* **+ / −:** \+ Interpretable benign model. − Binary only.
* **Code:** N.
* **Rel.:** 3.

**C2. Troubleshooting an Intrusion Detection Dataset: the CICIDS2017 Case Study**
* **Authors:** G. Engelen, V. Rimmer, W. Joosen.
* **Venue/type:** 2021 IEEE Security and Privacy Workshops (WTMC), pp. 7–12, PR.
* **ID:** DOI 10.1109/SPW53761.2021.00009. [KU Leuven Lirias](https://lirias.kuleuven.be/retrieve/713070).
* **Method:** audit of traffic generation, **CICFlowMeter flow construction** and labelling. Regenerated data with a modified CICFlowMeter, in which TCP flows end only after mutual FIN and RST also terminates a flow.
* **Data:** CICIDS2017 PCAPs.
* **Metrics:** "more than 20 percent of original traffic traces are reconstructed or relabelled" (search-result summary of the paper).
* **+ / −:**
  * \+ Documents the very extractor bugs suspected in Aegis's 2017→2018 collapse.
* **Code:** Y, [GintsEngelen/WTMC2021-Code](https://github.com/GintsEngelen/WTMC2021-Code).
* **Repro:** re-extraction from PCAP is CPU-bound and disk-heavy (PCAP size not verified).
* **Rel.:** 5.

**C3. From CIC-IDS2017 to LYCOS-IDS2017: A corrected dataset for better performance**
* **Authors:** A. Rosay, F. Carlier, E. Cheval, P. Leroux.
* **Venue/type:** IEEE/WIC/ACM WI-IAT 2021, pp. 570–575, PR.
* **ID:** DOI 10.1145/3486622.3493973. [HAL](https://hal.archives-ouvertes.fr/hal-03508406).
* **Method:** new extractor (LycoSTand) used to regenerate CICIDS2017.
* **Metrics:** "significant performance increases for all evaluated ML algorithms" (abstract).
* **+ / −:** \+ A corrected 2017 dataset used by B16 and C12.
* **Code/data:** project site [lycos-ids.univ-lemans.fr](http://lycos-ids.univ-lemans.fr/) (not opened; ?).
* **Rel.:** 4.

**C4. Towards Model Generalization for Intrusion Detection: Unsupervised Machine Learning Techniques**
* **Authors:** M. Verkerken, L. D'hooge, T. Wauters, B. Volckaert, F. De Turck.
* **Venue/type:** J. Network and Systems Management 30, art. 12, 2022 (online 2021), PR.
* **ID:** DOI 10.1007/s10922-021-09615-7.
* **Method:** autoencoder, one-class SVM, isolation forest and PCA.
* **Data:** CIC-IDS-2017 and CSE-CIC-IDS2018 with compatible features.
* **Protocol:** **inter-dataset** (train on one, test on the other).
* **Metrics:** an NDSS 2023 poster by the authors reports an average accuracy decrease of 25%, with OC-SVM best at a 26% decrease (poster, not the journal abstract).
* **+ / −:** \+ Same dataset pair as Aegis. − Unsupervised only.
* **Code:** N.
* **Rel.:** 4.

**C5. Towards a Standard Feature Set for Network Intrusion Detection System Datasets**
* **Authors:** M. Sarhan, S. Layeghy, M. Portmann.
* **Venue/type:** Mobile Networks and Applications 27(1):357–370, 2022, PR.
* **ID:** DOI 10.1007/s11036-021-01843-0. [arXiv 2101.11315](https://arxiv.org/abs/2101.11315).
* **Method:** NetFlow-based standard feature set (43 features in the extended version); four datasets converted (NF-*-v2).
* **Protocol:** Extra Trees classifier per dataset.
* **+ / −:**
  * \+ **One NetFlow feature extractor for several datasets.** This is the cleanest available way to hold the extractor constant across networks.
  * − NetFlow features differ from Aegis's 77 CICFlowMeter features.
* **Data:** [UQ NIDS datasets page](https://staff.itee.uq.edu.au/marius/NIDS_datasets/).
* **Rel.:** 5.

**C6. Evaluating Standard Feature Sets Towards Increased Generalisability and Explainability of ML-based Network Intrusion Detection**
* **Authors:** M. Sarhan, S. Layeghy, M. Portmann.
* **Venue/type:** Big Data Research 30:100359, 2022, PR.
* **ID:** DOI 10.1016/j.bdr.2022.100359. [arXiv 2104.07183](https://arxiv.org/abs/2104.07183).
* **Method:** compares NetFlow and CICFlowMeter feature sets, with SHAP.
* **Data:** CSE-CIC-IDS2018, BoT-IoT, ToN-IoT.
* **Metrics:** NetFlow features improved detection for various attacks compared with CICFlowMeter features (abstract, qualitative).
* **+ / −:** \+ Direct evidence that the *feature extractor* changes detection and explanations.
* **Code:** N.
* **Rel.:** 4.

**C7. The Cross-Evaluation of Machine Learning-Based Network Intrusion Detection Systems (XeNIDS)**
* **Authors:** G. Apruzzese, L. Pajola, M. Conti.
* **Venue/type:** IEEE TNSM 19(4):5152–5169, 2022, PR.
* **ID:** DOI 10.1109/TNSM.2022.3157344. [arXiv 2203.04686](https://arxiv.org/abs/2203.04686).
* **Method:** framework for reliable cross-evaluation of NetFlow-based ML-NIDS.
* **Data:** six datasets.
* **Protocol:** **cross-dataset**.
* **Metrics:** not read.
* **+ / −:** \+ Methodology for when cross-evaluation is meaningful.
* **Code:** N.
* **Rel.:** 4.

**C8. Error Prevalence in NIDS datasets: A Case Study on CIC-IDS-2017 and CSE-CIC-IDS-2018**
* **Authors:** L. Liu, G. Engelen, T. Lynar, D. Essam, W. Joosen.
* **Venue/type:** IEEE CNS 2022, pp. 254–262, PR.
* **ID:** DOI 10.1109/CNS56114.2022.9947235.
* **Method:** audit of attack orchestration, feature generation, documentation and labelling in **both** CIC datasets. Publishes recreated datasets with corrected labelling logic.
* **+ / −:**
  * \+ The **only verified source of corrected re-extractions of both** CICIDS2017 and CSE-CIC-IDS2018 with one fixed tool chain. This is the key enabler for separating extractor shift from network shift.
* **Code:** Y, [GintsEngelen/CNS2022_Code](https://github.com/GintsEngelen/CNS2022_Code) (research code).
* **Rel.:** 5.

**C9. Errors in the CICIDS2017 Dataset and the Significant Differences in Detection Performances It Makes**
* **Authors:** M. Lanvin, P.-F. Gimenez, Y. Han, F. Majorczyk, L. Mé, É. Totel.
* **Venue/type:** CRiSIS 2022, LNCS 13857, pp. 18–33 (Springer 2023), PR.
* **ID:** DOI 10.1007/978-3-031-31108-6_2. [HAL](https://hal.archives-ouvertes.fr/hal-03775466).
* **Method:** documents packet misordering, duplication and mislabelled attacks; measures the effect on supervised IDS evaluation.
* **Code:** a related labelling-fix pull request exists on the CNS2022 repository (?).
* **Rel.:** 4. Already cited as a threat to validity in AEGIS_OSR.md §5.

**C10. Explainable Cross-domain Evaluation of ML-based Network Intrusion Detection Systems**
* **Authors:** S. Layeghy, M. Portmann.
* **Venue/type:** Computers and Electrical Engineering 108:108692, 2023, PR.
* **ID:** DOI 10.1016/j.compeleceng.2023.108692.
* **Method:** cross-domain evaluation with SHAP.
* **Data and metrics:** full text not read. Secondary sources state 7 models × 4 datasets, with no model generalising and strongly asymmetric transfer; not verified first-hand.
* **Rel.:** 4. Closest prior on "explanations under cross-dataset shift".

**C11. Bad Design Smells in Benchmark NIDS Datasets**
* **Authors:** R. Flood, G. Engelen, D. Aspinall, L. Desmet.
* **Venue/type:** IEEE EuroS&P 2024, pp. 658–675, PR.
* **ID:** DOI 10.1109/EuroSP60621.2024.00042. [Author PDF](https://detlearsom.github.io/pubs/BadSmells-EuroSP24-finaldraft.pdf).
* **Method:** manual analysis of 7 datasets, giving six "data design smells" (e.g., leaked labels via features, near-duplicate flows, attacks against closed ports) and heuristics to measure them.
* **Note:** the chatbot attributed this paper to "Flood et al. 2024 on NIDS ML evaluation". The verified author list includes Desmet, not Joosen.
* **Rel.:** 4. Aegis's CLAIM_AUDIT §5 found 2018 FTP-BruteForce collapsing to 51 unique flows, which is exactly the "near-duplicate" smell.

**C12. Machine Learning in Network Intrusion Detection: A Cross-Dataset Generalization Study**
* **Authors:** M. Cantone, C. Marrocco, A. Bria.
* **Venue/type:** IEEE Access 12:144489–144508, 2024, PR.
* **Title note:** the arXiv title is "On the Cross-Dataset Generalization of Machine Learning for Network Intrusion Detection".
* **ID:** DOI 10.1109/ACCESS.2024.3472907. [arXiv 2402.10974](https://arxiv.org/abs/2402.10974).
* **Method:** four classifiers; introduces **LycoS-Unicas-IDS2018**, which applies LycoS-style corrections to CSE-CIC-IDS2018.
* **Data:** CIC-IDS2017, CSE-CIC-IDS2018, LycoS-IDS2017, LycoS-Unicas-IDS2018.
* **Protocol:** **cross-dataset**.
* **Metrics** (abstract): near-perfect within-dataset. Cross-dataset accuracy is "largely commensurate with random chance", except for a few attack and dataset combinations.
* **+ / −:**
  * \+ Provides a **same-extractor 2017/2018 pair**. It already suggests that correcting the extractor alone does *not* restore closed-set transfer.
  * − Closed-set classifiers only. No calibrated FPR.
* **Code/data:** not listed (N).
* **Rel.:** 5. Must be replicated with Aegis-OSR before any extractor-shift claim.

**C13. Open DGML: Intrusion Detection Based on Open-Domain Generation Meta-Learning**
* **Authors:** K. Jiang, F. Zou, H. Huang, L. Zheng, H. Zhai.
* **Venue/type:** Applied Sciences 14:5426, 2024, PR.
* **ID:** DOI 10.3390/app14135426.
* **Method:** flow imaging, augmentation and open-domain generalisation meta-learning.
* **Data:** ISCX2012, NDSec-1, CICIDS2017, CICIDS2018.
* **Protocol:** closed-domain versus open-domain.
* **Metrics** (abstract): closed-domain average accuracy 96.52%; open-domain 68.73% accuracy and 61.49% detection rate.
* **Rel.:** 2. Shows the size of the domain gap. Image-based method.

**C14. Learn-IDS: Bridging Gaps between Datasets and Learning-Based Network Intrusion Detection**
* **Authors:** M. Wang, N. Yang, Y. Guo, N. Weng.
* **Venue/type:** Electronics 13(6):1072, 2024, PR.
* **ID:** DOI 10.3390/electronics13061072.
* **Method:** raw-PCAP processing framework for uniform cross-dataset sampling and formatting.
* **Metrics** (abstract): labels raw data with about 90% accuracy across three datasets; +30.3% average OOD accuracy in a cross-dataset sampling case study; +4.1% from temporal information.
* **Code:** Y, [wangminxiao/Learn_IDS](https://github.com/wangminxiao/Learn_IDS) (per search result; not opened).
* **Rel.:** 3. Lead verified (Section 6).

**C15. Flow Exporter Impact on Intelligent Intrusion Detection Systems**
* **Authors:** D. Pinto, J. Vitorino, E. Maia, I. Amorim, I. Praça.
* **Venue/type:** ICISSP 2025 per arXiv comment, PR\*.
* **ID:** [arXiv 2412.14021](https://arxiv.org/abs/2412.14021).
* **Method:** re-exports UNSW-NB15 and CIC-IDS2017 PCAPs with the HERA exporter; trains RF, XGBoost, LightGBM and EBM.
* **Protocol:** original versus HERA-generated datasets.
* **Metrics:** qualitative: HERA-trained models "consistently outperformed" the originals and generalised better.
* **+ / −:** \+ Direct evidence that the exporter changes results. − No numbers in the abstract.
* **Code:** N.
* **Rel.:** 5.

**C16. ConCap: Practical Network Traffic Generation for (ML- and) Flow-based Intrusion Detection Systems**
* **Authors:** M. Verkerken, L. D'hooge, B. Volckaert, F. De Turck, G. Apruzzese.
* **Venue/type:** IEEE SaTML 2026, pp. 806–828, PR.
* **ID:** DOI 10.1109/SaTML68715.2026.00051. [arXiv 2509.16038](https://arxiv.org/abs/2509.16038).
* **Method:** isolated, reproducible generation of labelled packets and NetFlows from a configuration file.
* **Metrics:** qualitative (generated data "functionally equivalent" to other environments).
* **+ / −:**
  * \+ A route to *controlled* attack/benign generation, so tool and network can be varied independently.
  * \+ A search summary attributes to a recent paper (probably this one; **not confirmed**) the observation that CICFlowMeter received more than 30 feature-changing commits after the corrected CIC datasets were released in October 2022.
* **Code:** open-source per abstract; URL not given (?).
* **Rel.:** 4. Relevant to R5 (packet-level testbed).

**C17. Time Matters: Temporal NetFlow Features for ML-Based Network Intrusion Detection (NF-v3)**
* **Authors:** M. Luay, S. Layeghy, N. Noorbin, M. Sarhan, G. Kulatilleke, N. Moustafa, M. Portmann.
* **Venue/type:** IEEE Access 14:66899–66913, 2026, PR.
* **Title note:** the arXiv title is "Temporal Analysis of NetFlow Datasets for NIDS".
* **ID:** DOI 10.1109/ACCESS.2026.3688204. [arXiv 2503.04404](https://arxiv.org/abs/2503.04404).
* **Method:** releases NetFlow datasets with temporal features (inter-packet arrival, duration) and time-frequency analysis.
* **Data:** NF-UNSW-NB15-v3, NF-ToN-IoT-v3, NF-CSE-CIC-IDS2018-v3 (53 features per the UQ page).
* **+ / −:** \+ Same exporter across networks, plus temporal features. A candidate R2 target.
* **Rel.:** 4.

**C18. A cross-dataset harmonized intrusion detection framework with statistically validated multi-model learning**
* **Authors:** S. Mishra, N. S. Alshammari, H. Hussain, R. A. Alfahidah.
* **Venue/type:** PLOS ONE 21, 2026, PR.
* **ID:** DOI 10.1371/journal.pone.0346982.
* **Method:** manual feature harmonisation of NSL-KDD and CICIDS2017; statistical tests (Wilcoxon, McNemar, DeLong).
* **Metrics** (abstract): RF 98.0% accuracy and 97.0% F1 on the harmonised set. The authors note that manual alignment may not work on heterogeneous data.
* **Rel.:** 2. Matches the "2026 cross-dataset harmonization study" lead. Harmonises *pooled* data and does not test transfer between CIC-2017 and 2018.

### D. Temporal, behavioural and host/graph-level detection

**D1. Kitsune: An Ensemble of Autoencoders for Online Network Intrusion Detection** — *foundational*
* **Authors:** Y. Mirsky, T. Doitshman, Y. Elovici, A. Shabtai.
* **Venue/type:** NDSS 2018, PR.
* **ID:** DOI 10.14722/ndss.2018.23204. [arXiv 1802.09089](https://arxiv.org/abs/1802.09089).
* **Method:** a feature-extraction layer that tracks statistical patterns per network channel online, feeding an ensemble of autoencoders (KitNET). Window details were not read.
* **Protocol:** online, unsupervised.
* **Metrics:** comparable to offline detectors; runs on a Raspberry Pi (abstract).
* **+ / −:** \+ The canonical **channel-level incremental feature extractor**. Exactly the kind of evidence Aegis lacks for Bot and PortScan.
* **Code:** repository [ymirsky/Kitsune-py](https://github.com/ymirsky/Kitsune-py) exists under the first author's handle (?).
* **Repro:** CPU. Needs packets or timestamps plus IPs (see the gap analysis).
* **Rel.:** 4.

**D2. On the Evaluation of Sequential Machine Learning for Network Intrusion Detection**
* **Authors:** A. Corsini, S. J. Yang, G. Apruzzese.
* **Venue/type:** ARES 2021, PR.
* **ID:** DOI 10.1145/3465481.3470065. [arXiv 2106.07961](https://arxiv.org/abs/2106.07961).
* **Method:** methodology for extracting NetFlow sequences; LSTM compared with a static FNN.
* **Data:** CICIDS2017 and CTU13.
* **Metrics** (abstract):
  * CICIDS2017: LSTM ≈ FNN, both above 99.5% F1;
  * CTU13: LSTM 95.7% versus FNN 91.5% F1.
* **+ / −:** \+ Sequences help on botnet data (CTU13) but not on CICIDS2017 in their setup.
* **Code:** N.
* **Rel.:** 4.

**D3. E-GraphSAGE: A Graph Neural Network based Intrusion Detection System for IoT**
* **Authors:** W. W. Lo, S. Layeghy, M. Sarhan, M. Gallagher, M. Portmann.
* **Venue/type:** IEEE/IFIP NOMS 2022, pp. 1–9, PR.
* **ID:** DOI 10.1109/NOMS54207.2022.9789878. [arXiv 2103.16329](https://arxiv.org/abs/2103.16329).
* **Method:** flows as edges between hosts; edge-feature GraphSAGE.
* **Data:** four NIDS datasets (the final arXiv version).
* **Metrics:** "outperforms the state of the art" (qualitative).
* **Code:** repository `waimorris/E-GraphSAGE` exists; official status not confirmed (?).
* **Repro:** needs source and destination IPs (available in Aegis's `TrafficLabelling/` 2017 CSVs).
* **Rel.:** 4.

**D4. Euler: Detecting Network Lateral Movement via Scalable Temporal Graph Link Prediction**
* **Authors:** I. J. King, H. H. Huang.
* **Venue/type:** NDSS 2022, PR. Journal version: ACM TOPS 26(3), 2023, DOI 10.1145/3588771.
* **ID:** DOI 10.14722/ndss.2022.24107.
* **Method:** GNN stacked on a sequence encoder over discrete-time host graphs; anomalous edges are candidate lateral movement.
* **Metrics:** not read first-hand.
* **Code:** repository [iHeartGraph/Euler](https://github.com/iHeartGraph/Euler) exists (?).
* **Rel.:** 3. Host-level temporal model, mainly for lateral movement.

**D5. Anomal-E: A self-supervised network intrusion detection system based on graph neural networks**
* **Authors:** E. Caville, W. W. Lo, S. Layeghy, M. Portmann.
* **Venue/type:** Knowledge-Based Systems 258:110030, 2022, PR.
* **ID:** DOI 10.1016/j.knosys.2022.110030. [arXiv 2207.06819](https://arxiv.org/abs/2207.06819).
* **Method:** self-supervised edge embeddings (no labels), then anomaly detectors.
* **Data:** two NIDS datasets (unnamed in the abstract).
* **Metrics:** embeddings improve on raw features (qualitative).
* **Code:** N.
* **Rel.:** 4. A label-free host-graph evidence source.

**D6. XG-BoT: An explainable deep graph neural network for botnet detection and forensics**
* **Authors:** W. W. Lo, G. Kulatilleke, M. Sarhan, S. Layeghy, M. Portmann.
* **Venue/type:** Internet of Things 22:100747, 2023, PR.
* **ID:** DOI 10.1016/j.iot.2023.100747. [arXiv 2207.09088](https://arxiv.org/abs/2207.09088).
* **Method:** GIN-based node classification on botnet communication graphs, with GNNExplainer and saliency.
* **Data:** large-scale botnet graph datasets.
* **Code:** N (the guessed repository path returned 404).
* **Rel.:** 4. Bot detection is inherently host/graph-level.

**D7. FlowTransformer: A transformer framework for flow-based network intrusion detection systems**
* **Authors:** L. D. Manocchio, S. Layeghy, W. W. Lo, G. K. Kulatilleke, M. Sarhan, M. Portmann.
* **Venue/type:** Expert Systems with Applications 241:122564, 2024, PR.
* **ID:** DOI 10.1016/j.eswa.2023.122564. [arXiv 2304.14746](https://arxiv.org/abs/2304.14746).
* **Method:** modular Transformer over flow sequences.
* **Data:** three NIDS datasets.
* **Metrics** (abstract): the classification head matters most; global average pooling performs poorly; model size can be cut by more than 50% without accuracy loss.
* **Code:** Y, [liamdm/FlowTransformer](https://github.com/liamdm/FlowTransformer).
* **Repro:** TensorFlow/Keras (not verified), CPU slow.
* **Rel.:** 3.

**D8. Do Transformers Actually Help Intrusion Detection? A Temporal Sequence Evaluation on CIC-IDS2017**
* **Authors:** Z. Moczkodan, H. Ragab.
* **Venue/type:** arXiv 2606.11098 (2026), preprint.
* **ID:** [arXiv](https://arxiv.org/abs/2606.11098).
* **Method:** ordered conversation sequences; nine models.
* **Protocol:** a random split plus two **leakage-free** splits; padding ablation.
* **Metrics** (abstract, CIC-IDS2017):
  * Transformer macro-F1 0.89 on non-padded windows, but it degrades under zero-pad+mask;
  * class-balanced RF is the most robust overall;
  * repeat-last padding hid a 67× rise in the Transformer's false-alarm rate.
* **Code:** Y, [zachmocz/temporal-ids-bench](https://github.com/zachmocz/temporal-ids-bench).
* **Rel.:** 4. A cautionary prior for any Aegis sequence model.

### E. Evaluation methodology (cross-cutting)

**E1. Evaluating Explanation Methods for Deep Learning in Security**
* **Authors:** A. Warnecke, D. Arp, C. Wressnegger, K. Rieck.
* **Venue/type:** IEEE EuroS&P 2020, pp. 158–174, PR.
* **ID:** DOI 10.1109/EuroSP48549.2020.00018. [arXiv 1906.02108](https://arxiv.org/abs/1906.02108).
* **Method:** six explanation methods evaluated with security-specific criteria.
* **Data:** malware and vulnerability discovery.
* **Rel.:** 3. Criteria to extend Aegis's XAI_STABILITY.md.

**E2. Dos and Don'ts of Machine Learning in Computer Security**
* **Authors:** D. Arp, E. Quiring, F. Pendlebury, A. Warnecke, F. Pierazzi, C. Wressnegger, L. Cavallaro, K. Rieck.
* **Venue/type:** USENIX Security 2022, pp. 3971–3988, PR.
* **ID:** no DOI. [USENIX](https://usenix.org/conference/usenixsecurity22/presentation/arp).
* **Content:** 10 pitfalls (e.g., sampling bias, data snooping), each with a recommendation, found in a review of 30 papers.
* **Rel.:** 5. Aegis's seed-0 design selection on the same families (CLAIM_AUDIT §2) is a mild data-snooping instance.

**E3. SoK: Pragmatic Assessment of Machine Learning for Network Intrusion Detection**
* **Authors:** G. Apruzzese, P. Laskov, J. Schneider.
* **Venue/type:** IEEE EuroS&P 2023, pp. 592–614, PR.
* **ID:** DOI 10.1109/EuroSP57164.2023.00042. [arXiv 2305.00550](https://arxiv.org/abs/2305.00550).
* **Content:** "pragmatic assessment" covering configurations, adversarial settings and four hardware platforms, with a practitioner user study.
* **Rel.:** 4. Supports reporting cost and latency next to accuracy in R3.

**E4. Stream Assembly Is an Uncontrolled Treatment in Streaming Intrusion-Detection Benchmarks**
* **Authors:** M. A. Youssef.
* **Venue/type:** arXiv 2605.24696 (v3, 2026), preprint.
* **Title note:** formerly titled "CALIBURN: …Conformal Risk Control"; v3 is a self-declared "substantial correction".
* **ID:** [arXiv](https://arxiv.org/abs/2605.24696).
* **Content:** reordering CICIDS2017 records under a fixed 70/15/15 positional split yields held-out sets sharing only 32.5% of records, with prevalence differing by about 43 percentage points, which reverses detector rankings (abstract).
* **Code/data:** Zenodo [10.5281/zenodo.22673735](https://doi.org/10.5281/zenodo.22673735) (?).
* **Rel.:** 3. Supports Aegis's fixed-seed, stratified splits, and warns against positional temporal splits without reporting prevalence.

---

## 4. Comparison with Aegis-OSR

All Aegis numbers are from RESULTS.md unless marked otherwise. Literature metrics are **not** comparable with Aegis numbers unless dataset, protocol and operating point match. None of the verified papers matches all three.

### 4.1 What the literature does that Aegis does not

| Line of work | Evidence | What Aegis lacks |
|---|---|---|
| **Corrected or re-extracted data** | B16 uses LycoS-IDS2017. C2, C3, C8, C9 and C12 document and fix CICFlowMeter and labelling errors. C12 provides LycoS-Unicas-IDS2018. | Aegis uses the original MachineLearningCVE export "as-is" (AEGIS_OSR.md §5). Every Aegis number may carry dataset artefacts. |
| **Same-extractor cross-network evaluation** | C5 and C17 (NF-v2/v3, one NetFlow exporter); C12 (LycoS pair); C15 (HERA re-export) | Aegis's 2017→2018 transfer mixes tool versions (AEGIS_OSR.md §5; CLAIM_AUDIT §5), so it cannot attribute its 35.20% FPR. |
| **Host / graph / sequence evidence** | D1 Kitsune (per-channel incremental statistics); D3, D5, D6 (host graphs); D2 (sequences help on CTU13 botnets); B18 (time windows) | Aegis is per-flow only. Bot LOAFO recall is 0.023 and PortScan 0.357 at α = 1%. |
| **Fitted EVT tails** | B2 OpenMax (meta-recognition/EVT); B4 SPOT (EVT for streams) | Aegis uses an exponential tail extrapolation without a fitted EVT distribution (CLAIM_AUDIT §2). |
| **Shift-robust conformal theory** | B7 (adaptive α, long-run guarantee); B12 (weighted conformal, drift-robust coverage); B11 (calibration-conditional p-values, uniform FPR bound, FDR) | Aegis's guarantee is marginal and exchangeability-only. Recalibration is window-dependent: Friday W=5000 gives 2.57%; 2018 recal+ref@2000 gives 50.96%. |
| **Contrastive or learned representations for zero-day** | B8 CADE; B16 CLOSR; A10 TabICL embeddings | Aegis's kNN runs on signed-log standardised raw features, not on a learned metric. |
| **Tabular foundation and modern DL models** | A5 TabM, A7 TabICL, A9 (TabICL keeps non-zero recall on Heartbleed and Infiltration, closed-set) | Aegis's DL comparison is limited to single-seed families (CLAIM_AUDIT §1: "NNs 5–35%" held-out); TabM and TabICL were not tested. |
| **Leakage-aware sequence evaluation** | D8 (padding and split leakage); E4 (stream assembly) | Not yet relevant: Aegis has no sequence model. Must be respected in R3. |

### 4.2 What Aegis does that the verified literature does not (evidence-based, not a novelty claim)

| Aegis property | Aegis evidence | Closest verified prior and the difference |
|---|---|---|
| **Finite-sample benign-FPR control for a *supervised + novelty* open-set NIDS** | Realized FPR 1.00% [0.92, 1.07] at α = 1% under IID LOAFO | **B17** controls FAR with split conformal for an *unsupervised* AE detector (O-RAN, workshop, no dataset named). **B11** is the general theory. **B13** and **B16** report tuned thresholds or threshold-free AUROC. We found no verified NIDS paper that fuses known-attack and novelty evidence under one conformal FPR guarantee. This is a hypothesis of novelty, pending a broader search (e.g., p-value combination in conformal anomaly detection, which was **not reviewed** here). |
| **Same calibration pipeline for every compared method** | AEGIS_OSR.md §2: all methods use surprisal → fusion → conformal | Most NIDS papers compare at default or tuned thresholds (B13, B18) or with AUROC (B16), which confounds evidence quality with threshold choice. |
| **LOAFO with seed-level statistics at a fixed α** | 0.706 [0.689, 0.723] vs closed-set XGB 0.490 [0.447, 0.533]; Δ +0.216 [0.180, 0.252], paired t p = 7.59×10⁻⁵, 5/5 seeds | B16 holds out one class (AUROC only); B18 uses held-out families on ToN-IoT (Recall@1%FPR 0.783, no variance reported). No verified paper reports seed-level paired tests at a calibrated α on CICIDS2017. |
| **Reporting where the guarantee breaks** | Friday FPR 7.09% [6.66, 7.52]; 2018 FPR 36.73% [34.72, 38.73] (v2 sample, `openset_cross_summary_v2.json`; v1: 35.20%); per-day recalibration table | B17, B11 and B12 discuss exchangeability theoretically. We found no NIDS paper that measures conformal FPR violation under temporal and cross-dataset shift. |
| **Per-tool transfer diagnosis** | The frozen v1.1 detector misses the same tools in 2018 (v2 sample): DoS-Hulk 1.1%, SSH-Bruteforce 0.0%, LOIC-HTTP 45.0%, Slowloris 95.6% (EXP-009). A retrained, recalibrated XGB detects the brute-force and DoS days at ≤ 1% FPR (PRIOR_WORK_COMPARISON §3) | C12 reports near-random cross-dataset accuracy, but not per-tool detection with an extractor hypothesis. C2 and C8 document the bugs but do not measure their effect on open-set FPR. |
| **Honest attribution (Mondrian)** | Unknowns are rarely mislabelled as a known family (≤ 0.9%, CLAIM_AUDIT §1) | B3 and B10 do per-class conformal rejection for malware. B16 does open-set recognition (OpenAUC). Attribution with an explicit UNKNOWN-ATTACK versus ZERO-DAY-ANOMALY split is uncommon in the verified NIDS papers. |

### 4.3 Where Aegis is weaker than the state of the art

* **Bot:** Aegis LOAFO recall is 0.023 [0.019, 0.028]. Graph and host-level methods (D3, D6) and sequences (D2 on CTU13) are designed for exactly this case.
* **Cross-network:** Aegis AUROC (unknown) is 0.568 on 2018 and realized FPR is 36.73% (v2 sample; v1: 0.576 and 35.20%). The literature (C4, C12, C13, A10) agrees that cross-dataset transfer is poor in general, so Aegis is *not* uniquely bad, but it is not solved either.
* **Data hygiene:** published 2026 zero-day work (B16) uses corrected data. Reviewers will expect Aegis to do so too, or to justify why not.

---

## 5. Reproducibility on our hardware (summary)

| Method | Official code | CPU-only feasible? | GPU (RTX 4060 8 GB) | Note |
|---|---|---|---|---|
| DT, RF, Extra Trees | scikit-learn | Yes | n/a | Installed |
| XGBoost | `xgboost` 3.2.0 | Yes | Optional | Installed |
| LightGBM, CatBoost | PyPI packages | Yes | Optional | **Not installed**: `pip install` needed |
| kNN-OOD (B9) | knn-ood / sklearn / FAISS | Yes | Optional | Already in Aegis |
| Energy (B6) | trivial | Yes | — | Already in Aegis |
| CADE (B8) | Y | Likely (small AE) | Optional | Academic-only licence |
| CLOSR (B16) | Y | Likely, not verified | Helpful | PyTorch CPU build present |
| TabM (A5) | Y | Yes (MLP), hours (estimate) | Helpful | — |
| TabICL (A7) | Y | **Unverified**; pilot needed | Needs CUDA build of PyTorch | Context subsampling required |
| TabPFN v2 (A6) | Y | Small contexts only | Needs CUDA build | ≤ 10k-sample regime per abstract |
| TabR (A4), FT-Transformer (A1) | Y | Slow | Needs CUDA build | Deferred |
| E-GraphSAGE / Anomal-E (D3, D5) | ? / N | Feasible on 2017 with IPs | Helpful | 2018 processed CSVs lack Src IP in 9 of 10 files (checked locally) |
| Kitsune (D1) | ? | Yes | — | Needs per-packet or timestamped flow streams |

---

## 6. Leads that could not be verified

Each lead was searched by name, venue and year on 2026-11-17.

| Lead (as given) | Outcome |
|---|---|
| **"TabR (2026, Wiley)"** | **Not found.** TabR is Gorishniy et al., ICLR 2024 (A4). No Wiley TabR intrusion-detection paper surfaced. The closest Wiley hit was a TabTransformer-based IDS in *Trans. Emerging Telecommunications Technologies* (DOI 10.1002/ett.70483, seen only as a search snippet; not reviewed). |
| **"TabICL (2026)"** | **Resolved, with a different identity.** The original TabICL is ICML 2025 (A7). The 2026 item is most likely **TabICLv2** (arXiv 2602.11139, "Published at ICML 2026" per arXiv comment; A8). The IDS-specific TabICL study is García et al., *Electronics* **2025** (A9), not 2026. |
| **"Protocol State-Masked Transformer (Scientific Reports 2026)"** | **Not found** under this or similar wording. Related but different works: ThreatFormer-IDS (B18, masked self-supervised flow Transformer, AICCONF 2026) and PLM-NIDS (arXiv 2606.00155, state-space model; not reviewed). |
| **"OpenPN (2026, SAGE)"** | **Not found.** No method named OpenPN surfaced. "SAGE" matched an unrelated adversarial-defence engine (Sample-Aware Guarding Engine), not a SAGE Publishing journal. The closest open-set prototype work was a 2024 *Int. J. Inf. Security* paper (not verified, not reviewed). |
| **"Learn-IDS (MDPI)"** | **Verified:** Wang et al., *Electronics* 13(6):1072, 2024 (C14). |
| **"2026 tabular representation learning study for IDS"** | **Verified** as Butt, Hotho & Schlör, arXiv 2605.02519, IEEE CSR 2026 per comment (A10). |
| **"2026 cross-dataset harmonization study"** | **Probably** Mishra et al., *PLOS ONE* 2026 (C18), which harmonises NSL-KDD and CICIDS2017. Other 2026 candidates were found only on Preprints.org (a NetFlow-v3 cross-domain study, manuscript 202610.1041, page returned 403) or as search snippets (Kılıç & Şengül, *IEEE Access* 2026, DOI 10.1109/ACCESS.2026.3703481: title and authors confirmed via Crossref, abstract not read). Treat the lead as ambiguous. |
| "Flood et al. 2024 on NIDS ML evaluation" | **Verified with a correction:** Flood, Engelen, Aspinall, **Desmet**, EuroS&P 2024 (C11). |
| "CALIBURN" (surfaced during search) | Now retitled; v3 retracts the earlier conformal-risk-control claims (E4). Do not cite v1/v2. |
| Schleicher et al. 2026 (open-set active learning; surfaced in search) | Venue (KuVS workshop) and details **not verified**. Not reviewed. |
| Kılıç & Şengül 2026 (SHAP-guided cross-dataset feature selection, CICIDS2017→CSE-CIC-IDS2018) | Title, authors and venue verified via Crossref (IEEE Access 14:90926–90936). **Abstract not read**, so not included as a reviewed paper. High priority to read for R2. |

---

## 7. Reference list

Grouped as in Section 3. "found." marks a foundational (pre-2023) work. DOIs were checked via Crossref or publisher pages unless noted.

**A. Tabular ML**
1. Y. Gorishniy, I. Rubachev, V. Khrulkov, A. Babenko. Revisiting Deep Learning Models for Tabular Data. NeurIPS 2021. https://arxiv.org/abs/2106.11959 (found.)
2. L. Grinsztajn, E. Oyallon, G. Varoquaux. Why do tree-based models still outperform deep learning on typical tabular data? NeurIPS 2022 Datasets & Benchmarks. https://papers.nips.cc/paper_files/paper/2022/file/0378c7692da36807bdec87ab043cdadc-Paper-Datasets_and_Benchmarks.pdf
3. D. McElfresh et al. When Do Neural Nets Outperform Boosted Trees on Tabular Data? NeurIPS 2023 Datasets & Benchmarks. https://arxiv.org/abs/2305.02997
4. Y. Gorishniy, I. Rubachev, N. Kartashev, D. Shlenskii, A. Kotelnikov, A. Babenko. TabR: Tabular Deep Learning Meets Nearest Neighbors. ICLR 2024. https://proceedings.iclr.cc/paper_files/paper/2024/hash/4ef594af0d9a519db8fb292452c461fa-Abstract-Conference.html
5. Y. Gorishniy, A. Kotelnikov, A. Babenko. TabM: Advancing Tabular Deep Learning with Parameter-Efficient Ensembling. ICLR 2025. https://proceedings.iclr.cc/paper_files/paper/2025/hash/c1ba41c694834aeef91ae161711d4939-Abstract-Conference.html
6. N. Hollmann, S. Müller, L. Purucker, A. Krishnakumar, M. Körfer, S. B. Hoo, R. T. Schirrmeister, F. Hutter. Accurate predictions on small data with a tabular foundation model. Nature 637:319–326, 2025. doi:10.1038/s41586-024-08328-6
7. J. Qu, D. Holzmüller, G. Varoquaux, M. Le Morvan. TabICL: A Tabular Foundation Model for In-Context Learning on Large Data. ICML 2025, PMLR 267:50817–50847. https://proceedings.mlr.press/v267/qu25d.html
8. J. Qu, D. Holzmüller, G. Varoquaux, M. Le Morvan. TabICLv2: A better, faster, scalable, and open tabular foundation model. arXiv:2602.11139 (ICML 2026 per authors). https://arxiv.org/abs/2602.11139
9. P. García, J. de Curtò, I. de Zarzà, J. C. Cano, C. T. Calafate. Foundation Models for Cybersecurity: A Comprehensive Multi-Modal Evaluation of TabPFN and TabICL for Tabular Intrusion Detection. Electronics 14(19):3792, 2025. doi:10.3390/electronics14193792
10. M. U. Butt, A. Hotho, D. Schlör. Evaluating Tabular Representation Learning for Network Intrusion Detection. IEEE CSR 2026 (per authors). arXiv:2605.02519. https://arxiv.org/abs/2605.02519

**Baselines (verified, reference only)**
11. L. Breiman. Random Forests. Machine Learning 45:5–32, 2001. doi:10.1023/A:1010933404324 (found.)
12. P. Geurts, D. Ernst, L. Wehenkel. Extremely randomized trees. Machine Learning 63:3–42, 2006. doi:10.1007/s10994-006-6226-1 (found.)
13. T. Chen, C. Guestrin. XGBoost: A Scalable Tree Boosting System. KDD 2016, pp. 785–794. doi:10.1145/2939672.2939785 (found.)
14. G. Ke et al. LightGBM: A Highly Efficient Gradient Boosting Decision Tree. NeurIPS 2017. https://proceedings.neurips.cc/paper/2017/file/6449f44a102fde848669bdd9eb6b76fa-Paper.pdf (found.)
15. L. Prokhorenkova, G. Gusev, A. Vorobev, A. V. Dorogush, A. Gulin. CatBoost: unbiased boosting with categorical features. NeurIPS 2018. https://proceedings.neurips.cc/paper/2018/hash/14491b756b3a51daac41c24863285549-Abstract.html (found.)

**B. Open-set / zero-day / conformal**
16. R. Sommer, V. Paxson. Outside the Closed World: On Using Machine Learning for Network Intrusion Detection. IEEE S&P 2010, pp. 305–316. doi:10.1109/SP.2010.25 (found.)
17. A. Bendale, T. Boult. Towards Open Set Deep Networks. CVPR 2016, pp. 1563–1572. https://openaccess.thecvf.com/content_cvpr_2016/html/Bendale_Towards_Open_Set_CVPR_2016_paper.html (found.) doi:10.1109/CVPR.2016.173
18. R. Jordaney, K. Sharad, S. K. Dash, Z. Wang, D. Papini, I. Nouretdinov, L. Cavallaro. Transcend: Detecting Concept Drift in Malware Classification Models. USENIX Security 2017, pp. 625–642. https://www.usenix.org/conference/usenixsecurity17/technical-sessions/presentation/jordaney (found.)
19. A. Siffer, P.-A. Fouque, A. Termier, C. Largouët. Anomaly Detection in Streams with Extreme Value Theory. KDD 2017, pp. 1067–1075. doi:10.1145/3097983.3098144 (found.)
20. L. Ruff et al. Deep One-Class Classification. ICML 2018, PMLR 80:4393–4402. https://proceedings.mlr.press/v80/ruff18a.html (found.)
21. W. Liu, X. Wang, J. Owens, Y. Li. Energy-based Out-of-distribution Detection. NeurIPS 2020. https://arxiv.org/abs/2010.03759 (found.)
22. I. Gibbs, E. Candès. Adaptive Conformal Inference Under Distribution Shift. NeurIPS 2021. https://proceedings.neurips.cc/paper/2021/hash/0d441de75945e5acbc865406fc9a2559-Abstract.html
23. L. Yang, W. Guo, Q. Hao, A. Ciptadi, A. Ahmadzadeh, X. Xing, G. Wang. CADE: Detecting and Explaining Concept Drift Samples for Security Applications. USENIX Security 2021, pp. 2327–2344. https://www.usenix.org/conference/usenixsecurity21/presentation/yang
24. Y. Sun, Y. Ming, X. Zhu, Y. Li. Out-of-Distribution Detection with Deep Nearest Neighbors. ICML 2022, PMLR 162:20827–20840. https://proceedings.mlr.press/v162/sun22d.html
25. F. Barbero, F. Pendlebury, F. Pierazzi, L. Cavallaro. Transcending Transcend: Revisiting Malware Classification in the Presence of Concept Drift. IEEE S&P 2022, pp. 805–823. doi:10.1109/SP46214.2022.9833659 (erratum Dec 2023 per authors' project page)
26. S. Bates, E. Candès, L. Lei, Y. Romano, M. Sesia. Testing for outliers with conformal p-values. Annals of Statistics 51(1):149–178, 2023. doi:10.1214/22-AOS2244
27. R. F. Barber, E. J. Candès, A. Ramdas, R. J. Tibshirani. Conformal prediction beyond exchangeability. Annals of Statistics 51(2):816–845, 2023. doi:10.1214/23-AOS2276
28. M. Verkerken, L. D'hooge, D. Sudyana, Y.-D. Lin, T. Wauters, B. Volckaert, F. De Turck. A Novel Multi-Stage Approach for Hierarchical Intrusion Detection. IEEE TNSM 20:3915–3929, 2023. doi:10.1109/TNSM.2023.3259474
29. R. Ahmad, I. Alsmadi, W. Alhamdani, L. Tawalbeh. Zero-day attack detection: a systematic literature review. Artificial Intelligence Review 56:10733–10811, 2023. doi:10.1007/s10462-023-10437-z
30. M. M. C. Souza, C. T. Pontes, J. J. C. Gondim, L. P. F. Garcia, L. DaSilva, E. F. M. Cavalcante, M. A. Marotta. A novel open set Energy-based Flow Classifier for Network Intrusion Detection. Computers & Security 157:104569, 2025. doi:10.1016/j.cose.2025.104569
31. J. Wilkie, H. Hindy, C. Michie, C. Tachtatzis, J. Irvine, R. Atkinson. A Novel Contrastive Loss for Zero-Day Network Intrusion Detection. IEEE TNSM 23:2064–2076, 2026. doi:10.1109/TNSM.2026.3652529
32. J. Rheey, H. Park. Toward Reliable Intrusion Monitoring for O-RAN Based Networks with Conformal False Alarm Control. ICML 2026 Workshop AI4NextG. https://icml.cc/virtual/2026/78428
33. S. Nayak. ThreatFormer-IDS: Robust Transformer Intrusion Detection with Zero-Day Generalization and Explainable Attribution. AICCONF 2026, pp. 1–8. doi:10.1109/AICCONF69182.2026.11600642
34. S. Fuhrman, O. Gungor, T. Rosing. CND-IDS: Continual Novelty Detection for Intrusion Detection Systems. arXiv:2502.14094, 2025 (preprint).
35. Z. Qiu, D. Zhou, Y. Zhai, B. Liu, L. He, J. Cao. VAEMax: Open-Set Intrusion Detection based on OpenMax and Variational Autoencoder. arXiv:2403.04193, 2024 (preprint; ICTC 2024 claimed).
36. S. Alzubi, F. Stahl. UNAD+: An Explainable Hybrid Framework for Unknown Network Attack Detection. arXiv:2605.22621, 2026 (preprint).

**C. Cross-dataset / tools / dataset quality**
37. C. F. T. Pontes, M. M. C. de Souza, J. J. C. Gondim, M. Bishop, M. A. Marotta. A New Method for Flow-Based Network Intrusion Detection Using the Inverse Potts Model. IEEE TNSM 18:1125–1136, 2021. doi:10.1109/TNSM.2021.3075503
38. G. Engelen, V. Rimmer, W. Joosen. Troubleshooting an Intrusion Detection Dataset: the CICIDS2017 Case Study. IEEE SPW 2021, pp. 7–12. doi:10.1109/SPW53761.2021.00009
39. A. Rosay, F. Carlier, E. Cheval, P. Leroux. From CIC-IDS2017 to LYCOS-IDS2017: A corrected dataset for better performance. WI-IAT 2021, pp. 570–575. doi:10.1145/3486622.3493973
40. M. Verkerken, L. D'hooge, T. Wauters, B. Volckaert, F. De Turck. Towards Model Generalization for Intrusion Detection: Unsupervised Machine Learning Techniques. J. Netw. Syst. Manage. 30:12, 2022. doi:10.1007/s10922-021-09615-7
41. M. Sarhan, S. Layeghy, M. Portmann. Towards a Standard Feature Set for Network Intrusion Detection System Datasets. Mobile Netw. Appl. 27(1):357–370, 2022. doi:10.1007/s11036-021-01843-0
42. M. Sarhan, S. Layeghy, M. Portmann. Evaluating Standard Feature Sets Towards Increased Generalisability and Explainability of ML-Based Network Intrusion Detection. Big Data Research 30:100359, 2022. doi:10.1016/j.bdr.2022.100359
43. G. Apruzzese, L. Pajola, M. Conti. The Cross-Evaluation of Machine Learning-Based Network Intrusion Detection Systems. IEEE TNSM 19(4):5152–5169, 2022. doi:10.1109/TNSM.2022.3157344
44. L. Liu, G. Engelen, T. Lynar, D. Essam, W. Joosen. Error Prevalence in NIDS datasets: A Case Study on CIC-IDS-2017 and CSE-CIC-IDS-2018. IEEE CNS 2022, pp. 254–262. doi:10.1109/CNS56114.2022.9947235
45. M. Lanvin, P.-F. Gimenez, Y. Han, F. Majorczyk, L. Mé, É. Totel. Errors in the CICIDS2017 Dataset and the Significant Differences in Detection Performances It Makes. CRiSIS 2022, LNCS 13857:18–33, 2023. doi:10.1007/978-3-031-31108-6_2
46. S. Layeghy, M. Portmann. Explainable Cross-domain Evaluation of ML-based Network Intrusion Detection Systems. Computers and Electrical Engineering 108:108692, 2023. doi:10.1016/j.compeleceng.2023.108692
47. R. Flood, G. Engelen, D. Aspinall, L. Desmet. Bad Design Smells in Benchmark NIDS Datasets. IEEE EuroS&P 2024, pp. 658–675. doi:10.1109/EuroSP60621.2024.00042
48. M. Cantone, C. Marrocco, A. Bria. Machine Learning in Network Intrusion Detection: A Cross-Dataset Generalization Study. IEEE Access 12:144489–144508, 2024. doi:10.1109/ACCESS.2024.3472907
49. K. Jiang, F. Zou, H. Huang, L. Zheng, H. Zhai. Open DGML: Intrusion Detection Based on Open-Domain Generation Meta-Learning. Applied Sciences 14:5426, 2024. doi:10.3390/app14135426
50. M. Wang, N. Yang, Y. Guo, N. Weng. Learn-IDS: Bridging Gaps between Datasets and Learning-Based Network Intrusion Detection. Electronics 13(6):1072, 2024. doi:10.3390/electronics13061072
51. D. Pinto, J. Vitorino, E. Maia, I. Amorim, I. Praça. Flow Exporter Impact on Intelligent Intrusion Detection Systems. ICISSP 2025 (per authors). arXiv:2412.14021
52. M. Verkerken, L. D'hooge, B. Volckaert, F. De Turck, G. Apruzzese. ConCap: Practical Network Traffic Generation for (ML- and) Flow-based Intrusion Detection Systems. IEEE SaTML 2026, pp. 806–828. doi:10.1109/SaTML68715.2026.00051
53. M. Luay, S. Layeghy, N. Noorbin, M. Sarhan, G. Kulatilleke, N. Moustafa, M. Portmann. Time Matters: Temporal NetFlow Features for ML-Based Network Intrusion Detection. IEEE Access 14:66899–66913, 2026. doi:10.1109/ACCESS.2026.3688204
54. S. Mishra, N. S. Alshammari, H. Hussain, R. A. Alfahidah. A cross-dataset harmonized intrusion detection framework with statistically validated multi-model learning. PLOS ONE 21, 2026. doi:10.1371/journal.pone.0346982

**D. Temporal / behavioural**
55. Y. Mirsky, T. Doitshman, Y. Elovici, A. Shabtai. Kitsune: An Ensemble of Autoencoders for Online Network Intrusion Detection. NDSS 2018. doi:10.14722/ndss.2018.23204 (found.)
56. A. Corsini, S. J. Yang, G. Apruzzese. On the Evaluation of Sequential Machine Learning for Network Intrusion Detection. ARES 2021. doi:10.1145/3465481.3470065
57. W. W. Lo, S. Layeghy, M. Sarhan, M. Gallagher, M. Portmann. E-GraphSAGE: A Graph Neural Network based Intrusion Detection System for IoT. NOMS 2022. doi:10.1109/NOMS54207.2022.9789878
58. I. J. King, H. H. Huang. Euler: Detecting Network Lateral Movement via Scalable Temporal Graph Link Prediction. NDSS 2022. doi:10.14722/ndss.2022.24107 (journal version ACM TOPS 2023, doi:10.1145/3588771)
59. E. Caville, W. W. Lo, S. Layeghy, M. Portmann. Anomal-E: A self-supervised network intrusion detection system based on graph neural networks. Knowledge-Based Systems 258:110030, 2022. doi:10.1016/j.knosys.2022.110030
60. W. W. Lo, G. Kulatilleke, M. Sarhan, S. Layeghy, M. Portmann. XG-BoT: An explainable deep graph neural network for botnet detection and forensics. Internet of Things 22:100747, 2023. doi:10.1016/j.iot.2023.100747
61. L. D. Manocchio, S. Layeghy, W. W. Lo, G. K. Kulatilleke, M. Sarhan, M. Portmann. FlowTransformer: A transformer framework for flow-based network intrusion detection systems. Expert Systems with Applications 241:122564, 2024. doi:10.1016/j.eswa.2023.122564
62. Z. Moczkodan, H. Ragab. Do Transformers Actually Help Intrusion Detection? A Temporal Sequence Evaluation on CIC-IDS2017. arXiv:2606.11098, 2026 (preprint).

**E. Evaluation methodology**
63. A. Warnecke, D. Arp, C. Wressnegger, K. Rieck. Evaluating Explanation Methods for Deep Learning in Security. IEEE EuroS&P 2020, pp. 158–174. doi:10.1109/EuroSP48549.2020.00018
64. D. Arp, E. Quiring, F. Pendlebury, A. Warnecke, F. Pierazzi, C. Wressnegger, L. Cavallaro, K. Rieck. Dos and Don'ts of Machine Learning in Computer Security. USENIX Security 2022, pp. 3971–3988. https://usenix.org/conference/usenixsecurity22/presentation/arp
65. G. Apruzzese, P. Laskov, J. Schneider. SoK: Pragmatic Assessment of Machine Learning for Network Intrusion Detection. IEEE EuroS&P 2023, pp. 592–614. doi:10.1109/EuroSP57164.2023.00042
66. M. A. Youssef. Stream Assembly Is an Uncontrolled Treatment in Streaming Intrusion-Detection Benchmarks. arXiv:2605.24696 v3, 2026 (preprint).

*Cited in AEGIS_OSR.md but not re-verified in this pass:* V. Vovk, A. Gammerman, G. Shafer, *Algorithmic Learning in a Random World* (Springer, 2005), and I. Sharafaldin et al., ICISSP 2018 (the CICIDS2017 dataset paper). Verify both before submission.

---

## Audit notes (independent spot-check, 2026-11-17)

* **B17 (O-RAN conformal false-alarm control):** existence and ICML 2026 listing confirmed
  (https://icml.cc/virtual/2026/78428); author names **not** confirmed — verify on OpenReview before citing.
* **Wilkie et al., TNSM 2026:** confirmed — IEEE Trans. Netw. Service Manag., vol. 23, pp. 2064–2076,
  DOI 10.1109/TNSM.2026.3652529; arXiv 2601.09902; official code https://github.com/jackwilkie/CLOSR.
* **Missing lead to review before any novelty claim:** S. Barrett, L. Li, G. Dorai, S. Rajaganapathy, *FIRCE: A
  Framework for Intrusion Response and Conformal Evaluation*, arXiv 2605.01962 (May 2026) — conformal evaluation
  for concept drift in supervised IDS classifiers. Not yet read; it may overlap with the shift-aware false-alarm
  control contribution (Gap analysis, contribution 2).

---

## Addendum (2026-11-17): close prior work found after the 61-paper review

These papers were found in a targeted novelty re-check (PRIOR_WORK_COMPARISON.md §5). They are **not** counted in the 61
verified papers. "Read" means the full text or the official abstract page was opened; "snippet only" means the full
text was behind a login or bot wall and **must be read before it is cited or used to judge novelty**.

| ID | Paper | Status | Code | What it does | Overlap with Aegis-OSR | Checked |
|---|---|---|---|---|---|---|
| F1 | S. Barrett, L. Li, G. Dorai, S. Rajaganapathy, *FIRCE: A Framework for Intrusion Response and Conformal Evaluation*, arXiv 2605.01962 | Preprint (v1, 3 May 2026); "accepted by IEEE SmartNets26" per arXiv comment only | github.com/DFAIR-LAB-Augusta/XSecIoT (branch `FIRCE_bkp`) | Transcend-style conformal evaluation (class-conditional) rejects low-confidence predictions of a binary IoT classifier as a drift signal; labelled retraining | Keyword-high, substance-low; calibration is in-sample (invalid p-values) | read (paper + code) |
| F2 | W. Ahmed, M. A. Rahaman, P. Roy, P. Alam, *The dashboard says "perfect"…* (label-free monitoring), Frontiers in AI 9, 2026, doi:10.3389/frai.2026.1928858 | Peer-reviewed | Zenodo 10.5281/zenodo.22654220 | CIC-IDS2017 ↔ CSE-CIC-IDS2018, HGB/MLP, 16 test-time-adaptation and label-shift variants (none beats the unadapted model in both directions); Mondrian conformal coverage at α = 0.1 collapses (0.016–0.263); abstention rate proposed as a drift alarm; 3 seeds | **Direct** on "conformal validity breaks under 2017→2018 and adaptation does not fix it". Not covered: FPR at fixed α, threshold recalibration on target benign, novelty or fusion evidence, unseen families, per-day analysis | read |
| F3 | M. Haroush, T. Frostig, R. Heller, D. Soudry, *A statistical framework for efficient out of distribution detection in deep neural networks* (MaSF), arXiv 2102.12967 (ICLR 2022 per our recollection — verify) | Peer-reviewed (to verify) | — | Combines p-values from many network components (Max/Simes/Fisher) into one OOD test with a Type-I-error guarantee | **Direct at method level** for conformal evidence combination (vision, not NIDS) | abstract read; combination details from memory |
| F4 | *Conformal prediction for network intrusion triage and analysis of unseen attack families*, Springer, 2026, doi:10.1007/s44564-026-00033-y | Peer-reviewed (journal name and authors unverified) | unknown | Per snippets: class-conditional conformal triage, 15 leave-one-family-out runs on UNSW-NB15 and CIC-IDS2017, probability-space vs feature-space novelty scores are family-dependent | **Possibly direct** (Mondrian + leave-one-family-out + supervised vs feature novelty) | snippet only |
| F5 | *ConFID: a conformal one-class framework for unsupervised zero-day intrusion detection in IoT networks*, Internet of Things (Elsevier), 2026 | Peer-reviewed (authors unverified) | unknown | Per snippets: one-class detector with a conformal finite-sample FPR bound, leave-one-attack-out | **Direct** on a conformal FPR bound for zero-day NIDS | snippet only |
| F6 | *Adaptive Decision-Level Intrusion Detection for Known and Zero-Day Attacks*, MDPI Network 6(2):23, 2026 | Peer-reviewed (authors unverified) | unknown | Per snippets: supervised + anomaly evidence fused with weights calibrated on validation data under a fixed FPR budget; CSE-CIC-IDS2018 | **Partial/direct** on hybrid fusion at a fixed FPR (apparently without conformal validity) | snippet only |
| F7 | Ş. Şahin et al., HADAR-UAV, Computers, Materials & Continua 89(1), 2026, doi:10.32604/cmc.2026.080874 | Peer-reviewed | "upon acceptance" | LSTM masked AE + Deep SVDD combined score with a split-conformal threshold; leave-two-families-out (UAVIDS-2025) | Partial (conformal FAR on a combined unsupervised score) | read (agent) |
| F8 | arXiv 2409.00667, conformal prediction integrated into a botnet NIDS (Information Fusion, per search snippet) | to verify | unknown | Conformal NIDS with adversarial examples | to assess | snippet only |
| F9 | Li, *Robust Conformal Intrusion Detection via Traffic-Aware Calibration and Attack-Orbit Invariance*, arXiv 2609.19241 | Preprint | none | Conformal calibration for LLM-based NIDS breaks under adversarial perturbation; weighted split conformal does not fix it | Partial (shift breaks the guarantee; adversarial, not natural shift) | abstract read (agent) |

**Corrections to entries above.**
* **B17** authors: Joohong Rheey, Hyunggon Park (ICML 2026 listing; OpenReview not accessible). The detector uses a
  Mahalanobis score on autoencoder reconstruction errors; no dataset is named; no shift test in the abstract.
* **C12** never crosses extractors (e.g. CIC17 → LycoS18), so it does not isolate the extractor effect.
* **E4** (Youssef, arXiv 2605.24696): v1/v2 were a different paper (CALIBURN, conformal risk control) whose numbers v3
  states were unsupported; cite only v3, as a critique of stream assembly.
