# R2 literature closure — reference and prior-work verification (Phase 2, 2026-11-18)

> **Provenance.** Compiled by a literature sub-agent from publisher pages, Crossref, arXiv and open-access PDFs (no paywalled
> content). Independently re-checked in the main session against Crossref: Şahin & Mert, *Electronics* 15(18):4084 (title, authors,
> venue and abstract); Heard & Rubin-Delanchy, *Biometrika* 105(1):239–246; Birnbaum, *JASA* 49(267):559–574. **Not**
> independently re-checked: F4 (Arepalli et al.) full-text statements (publisher login wall), and the Şahin & Mert full-text
> details beyond the abstract (the "valid and useless" wording and per-tool recalls). Treat those as reported, pending a
> manual read. "Not found" means not found in the 15 papers checked; it is not evidence that a gap exists.


**Date:** 2026-11-18. **Mode:** read-only on the repository. Nothing under the project tree was changed.

**How the checks were done.**
* **Bibliographic records:** Crossref REST API (`api.crossref.org/works`); OpenAlex and Semantic Scholar APIs as fallbacks; official proceedings pages (usenix.org, proceedings.mlr.press, proceedings.neurips.cc metadata JSON, iclr.cc, icml.cc); arXiv abstract pages.
* **Full texts read:** F4 (Springer OA PDF), F6 (MDPI OA PDF), the Dual-Threshold Conformal Deferral paper (MDPI OA PDF), MaSF (arXiv PDF) and Heard & Rubin-Delanchy (arXiv PDF). Text was extracted with pypdf.
* **Blocked:** DBLP (bot wall), ScienceDirect (403) and the Springer landing page (login redirect). The Springer PDF itself was open.
* **Scope:** 15 closest-prior-work papers checked. "Not found" below means *not found in these 15 papers*. It is not evidence that the gap exists.

---

## 1. Reference validity

The DOCX list (`paper_build/paper.py`, `REFS`) has 40 entries. All 11 `\bibitem`s in `paper.tex` are a subset of it (column "tex key").

Legend:
* **OK**: authors, title, venue and year match the primary record.
* **OK+**: correct as cited, but a page range or DOI is missing and should be added.
* **PARTIAL**: one field could not be confirmed from a primary source.

| # | tex key | As cited (short) | Verified? | Correction needed | Source |
|---|---|---|---|---|---|
| 1 | axelsson2000base | Axelsson, base-rate fallacy, ACM TISSEC 3(3):186–205, 2000 | OK | none (DOI 10.1145/357830.357849) | https://doi.org/10.1145/357830.357849 |
| 2 | – | Hassan et al., NoDoze, NDSS 2019 | OK | add DOI 10.14722/ndss.2019.23349 | https://doi.org/10.14722/ndss.2019.23349 |
| 3 | – | Alahmadi, Axon, Martinovic, "99% false positives", USENIX Sec 2022 | OK+ | add pp. 2783–2800 | https://www.usenix.org/conference/usenixsecurity22/presentation/alahmadi |
| 4 | sharafaldin2018generating | Sharafaldin et al., ICISSP 2018, pp. 108–116 | OK | add DOI 10.5220/0006639801080116 | https://doi.org/10.5220/0006639801080116 |
| 5 | sommer2010outside | Sommer & Paxson, IEEE S&P 2010, 305–316 | OK | DOI 10.1109/SP.2010.25 | https://doi.org/10.1109/SP.2010.25 |
| 6 | vovk2005algorithmic | Vovk, Gammerman, Shafer, Springer 2005 | OK | 1st ed. DOI 10.1007/b106715 (a 2nd ed., 2022, also exists) | https://doi.org/10.1007/b106715 |
| 7 | bates2023testing | Bates et al., Ann. Statist. 51(1):149–178, 2023 | OK | DOI 10.1214/22-AOS2244 | https://doi.org/10.1214/22-AOS2244 |
| 8 | – | Buczak & Guven, IEEE COMST 18(2):1153–1176, 2016 | OK | – | https://doi.org/10.1109/COMST.2015.2494502 |
| 9 | – | Liao et al., JNCA 36(1):16–24, 2013 | OK | – | https://doi.org/10.1016/j.jnca.2012.09.004 |
| 10 | – | Moustafa & Slay, UNSW-NB15, MilCIS 2015, 1–6 | OK | – | https://doi.org/10.1109/MilCIS.2015.7348942 |
| 11 | – | Ring et al., Comput. Secur. 86:147–167, 2019 | OK | – | https://doi.org/10.1016/j.cose.2019.06.005 |
| 12 | – | Engelen, Rimmer, Joosen, SPW 2021, 7–12 | OK | – | https://doi.org/10.1109/SPW53761.2021.00009 |
| 13 | – | Lanvin et al., CRiSIS 2022, LNCS, Springer 2023 | OK+ | add pp. 18–33, DOI 10.1007/978-3-031-31108-6_2 | https://doi.org/10.1007/978-3-031-31108-6_2 |
| 14 | arp2022dos | Arp et al., USENIX Sec 2022, 3971–3988 | OK | – | https://www.usenix.org/conference/usenixsecurity22/presentation/arp |
| 15 | – | Apruzzese, Laskov, Schneider, SoK, EuroS&P 2023 | OK+ | add pp. 592–614, DOI 10.1109/EuroSP57164.2023.00042 | https://doi.org/10.1109/EuroSP57164.2023.00042 |
| 16 | scheirer2012toward | Scheirer et al., TPAMI 35(7):1757–1772, 2013 | OK | key says 2012 (online-first); the cited year 2013 is right | https://doi.org/10.1109/TPAMI.2012.256 |
| 17 | bendale2016towards | Bendale & Boult, CVPR 2016, 1563–1572 | OK | – | https://doi.org/10.1109/CVPR.2016.173 |
| 18 | – | Hendrycks & Gimpel, ICLR 2017 | OK | arXiv 1610.02136; the "ICLR 2017" header is on the OpenReview PDF (id HJ2Pfowdg), seen via search only | https://arxiv.org/abs/1610.02136 |
| 19 | – | Lee, Lee, Lee, Shin, NeurIPS 2018 | OK+ | add pp. 7167–7177 | proceedings.neurips.cc metadata (hash abdeb6f575ac5c6676b747bca8d09cc2) |
| 20 | liu2020energy | Liu, Wang, Owens, Li, NeurIPS 33, 2020, pp. 21464–21475 | PARTIAL | authors and vol. 33 verified; **page range NOT VERIFIED** (no pages on the NeurIPS abstract page; metadata JSON not found) | https://proceedings.neurips.cc/paper/2020/hash/f5496252609c43eb8a3d147ab9b9c006-Abstract.html |
| 21 | sun2022out | Sun, Ming, Zhu, Li, ICML 2022, 20827–20840 | OK | PMLR vol. 162 | https://proceedings.mlr.press/v162/sun22d.html |
| 22 | – | Pang et al., ACM CSUR 54(2):1–38, 2021 | OK | Crossref title: "Deep Learning for Anomaly Detection" (subtitle "A Review") | https://doi.org/10.1145/3439950 |
| 23 | – | Liu, Ting, Zhou, Isolation forest, ICDM 2008, 413–422 | OK | – | https://doi.org/10.1109/ICDM.2008.17 |
| 24 | – | Mirsky et al., Kitsune, NDSS 2018 | OK | add DOI 10.14722/ndss.2018.23204 | https://doi.org/10.14722/ndss.2018.23204 |
| 25 | – | Angelopoulos & Bates, FnTML 16(4):494–591, 2023 | OK | – | https://doi.org/10.1561/2200000101 |
| 26 | jordaney2017transcend | Jordaney et al., USENIX Sec 2017, 625–642 | OK | – | https://www.usenix.org/conference/usenixsecurity17/technical-sessions/presentation/jordaney |
| 27 | – | Barbero et al., IEEE S&P 2022, 805–823 | OK | – | https://doi.org/10.1109/SP46214.2022.9833659 |
| 28 | – | Pendlebury et al., TESSERACT, USENIX Sec 2019, 729–746 | OK | – | https://www.usenix.org/conference/usenixsecurity19/presentation/pendlebury |
| 29 | – | Gama et al., ACM CSUR 46(4):1–37, 2014 | OK | – | https://doi.org/10.1145/2523813 |
| 30 | – | Lu et al., TKDE 31(12):2346–2363, 2019 | OK | vol., pages and year verified (Semantic Scholar journal record); issue 12 not separately confirmed | https://doi.org/10.1109/TKDE.2018.2876857 |
| 31 | – | Lundberg & Lee, NeurIPS 2017, 4765–4774 | OK | – | proceedings.neurips.cc metadata (hash 8a20a8621978632d76c43dfd28b67767) |
| 32 | – | Lundberg et al., Nat. Mach. Intell. 2(1):56–67, 2020 | OK | – | https://doi.org/10.1038/s42256-019-0138-9 |
| 33 | – | Ribeiro, Singh, Guestrin, KDD 2016, 1135–1144 | OK | – | https://doi.org/10.1145/2939672.2939778 |
| 34 | – | Breiman, Mach. Learn. 45(1):5–32, 2001 | OK | – | https://doi.org/10.1023/A:1010933404324 |
| 35 | – | Chen & Guestrin, KDD 2016, 785–794 | OK | – | https://doi.org/10.1145/2939672.2939785 |
| 36 | – | Pickands, Ann. Statist. 3(1):119–131, 1975 | OK | – | https://doi.org/10.1214/aos/1176343003 |
| 37 | – | Balkema & de Haan, Ann. Probab. 2(5):792–804, 1974 | OK | – | https://doi.org/10.1214/aop/1176996548 |
| 38 | – | Fisher, Statistical Methods for Research Workers, 4th ed., Oliver & Boyd, 1932 | PARTIAL | **Conflict.** The book is verified, and a Fisher bibliography (JRSS-A, via search snippet only) gives 4th ed. = 1932. Heard & Rubin-Delanchy (2018) cite the "4th ed." as 1934, and MaSF cites a 1992 reprint. Primary record NOT VERIFIED. | search snippet: https://academic.oup.com/jrsssa/article/126/1/159/7107274 |
| 39 | – | Wilcoxon, Biometrics Bull. 1(6):80–83, 1945 | OK | – | https://doi.org/10.2307/3001968 |
| 40 | – | Liu, Engelen, Lynar, Essam, Joosen, CNS 2022 | OK+ | add pp. 254–262, DOI 10.1109/CNS56114.2022.9947235 | https://doi.org/10.1109/CNS56114.2022.9947235 |

**Result.**
* No reference is fabricated or misattributed: 38 of 40 fully verified, and 2 are PARTIAL (#20 pages, #38 edition year).
* **More serious problem: the reference lists omit all of the closest prior work.**
  * Neither `paper.tex` nor `paper.py` cites any of them. Grep for Wilkie, CLOSR, FIRCE, Rheey, ConFID, Haroush, MaSF, Arepalli, Mchina, Verkerken, Tippett, Birnbaum, Loughin and Heard returns 0 hits.
  * The `paper.tex` abstract says *"Anomaly detectors can flag novelty but offer no control over their false-alarm rate."* This is contradicted by B17, HADAR-UAV and Bates et al. 2023, which `paper.tex` itself cites. ConFID's title also suggests it, but its abstract was not read.

---

## 2. Closest prior work: exact citations and status

Status key: **R** = full text read this pass; **A** = abstract read from a primary source; **T** = title or metadata only.

| ID | Exact citation (verified) | Read | What it does (from text read) |
|---|---|---|---|
| B16 CLOSR | J. Wilkie, H. Hindy, C. Michie, C. Tachtatzis, J. Irvine, R. Atkinson, "A Novel Contrastive Loss for Zero-Day Network Intrusion Detection," *IEEE TNSM* 23:2064–2076, 2026, doi:10.1109/TNSM.2026.3652529; arXiv 2601.09902 | T (Crossref). Full text read in the earlier R2 pass (PRIOR_WORK_COMPARISON §1) | Benign-anchored contrastive loss plus open-set recognition on LycoS-IDS2017. Two fixed held-out classes; threshold-free metrics only (per earlier read). |
| F1 FIRCE | S. Barrett, L. Li, G. Dorai, S. Rajaganapathy, "FIRCE: A Framework for Intrusion Response and Conformal Evaluation," *2026 Int. Conf. on Smart Applications, Communications and Networking (SmartNets)*, pp. 1–9, 7 Jul 2026, doi:10.1109/SmartNets69662.2026.11604738; arXiv 2605.01962 | T (Crossref). Full text and code read in the earlier R2 pass | Transcend-style class-conditional conformal *evaluation* as a drift signal for a binary IoT IDS, followed by labelled retraining. **Correction to the docs:** there is now an IEEE proceedings DOI, so it is no longer "preprint only". |
| F1b FADES | S. Barrett, G. Dorai, L. Li, S. Rajaganapathy, "FADES: Adaptive Drift Estimation via Conformal Signals for Streaming Intrusion Detection," *Electronics* 15(10):2114, 2026, doi:10.3390/electronics15102114 | A | Journal extension of FIRCE. Adds prediction-space (conformal evaluation) vs representation-space (CADE) drift detectors; 375 simulations; cross-dataset transfer with UNSW-NB15, CICIDS2018 and an IoT testbed. **New lead; not in the docs.** |
| F2 | W. Ahmed, M. A. Rahaman, P. Roy, P. Alam, "The dashboard says 'perfect': a systematic audit of label-free model monitoring and test-time adaptation under temporal distribution shift in network intrusion detection," *Front. Artif. Intell.* 9:1928858, 2026, doi:10.3389/frai.2026.1928858 | A | CIC-IDS2017 ↔ CSE-CIC-IDS2018 in both directions; 7 harmonised classes; 16 adaptation variants, none better than the unadapted model in both directions. Class-conditional conformal coverage falls from 0.90 to as low as 0.016. Conformal abstention rate proposed as a drift alarm. |
| F3 MaSF | M. Haroush, T. Frostig, R. Heller, D. Soudry, "A Statistical Framework for Efficient Out of Distribution Detection in Deep Neural Networks," *ICLR 2022* (poster); arXiv 2102.12967 | R | Per-layer empirical p-values combined by Max, Simes and Fisher into one test with Type-I error control (vision OOD). §3 explicitly discusses the Fisher (dense) vs Simes/min (sparse) power trade-off. **Docs said "ICLR 2022 per recollection": now verified.** |
| F4 | S. V. Arepalli, U. S. G. Irrinki, A. Morampudi, R. K. Surapani, "Conformal prediction for network intrusion triage and analysis of unseen attack families," *Discover Informatics* 1:33, published 2 Nov 2026, doi:10.1007/s44564-026-00033-y (OA, CC BY-NC-ND) | **R** | See §2a. **Docs said journal and authors unverified: now verified.** |
| F5 ConFID | E. Farsimadan, L. Moradi, F. Palmieri, "ConFID: A conformal one-class framework for unsupervised zero-day intrusion detection in IoT networks," *Internet of Things* 40:102078, Nov 2026, doi:10.1016/j.iot.2026.102078 | **T only** | Abstract NOT obtained: ScienceDirect 403, Semantic Scholar has no abstract (closed access), OpenAlex has no abstract. Content claims in the docs (conformal FPR bound, leave-one-attack-out) remain **NOT VERIFIED**. |
| F6 | J. P. Mchina, N. Mduma, R. S. Sinde, "Adaptive Decision-Level Intrusion Detection for Known and Zero-Day Attacks," *Network* (MDPI) 6(2):23, published 9 Apr 2026, doi:10.3390/network6020023 | **R** | See §2a. **Docs said authors unverified: now verified.** |
| F7 HADAR-UAV | C. B. Şahin, S. F. Abdul Razak, A. Ullah, A. F. Gündüz, N. M. Nawi, "HADAR-UAV: Risk-Calibrated One-Class Learning Framework for Zero-Day Intrusion Detection in Unmanned Aerial Vehicle Networks," *CMC* 89(1), 2026, doi:10.32604/cmc.2026.080874 | A | Masked AE + Deep SVDD with a split-conformal false-alarm threshold. Leave-Two-Attack-Families-Out on UAVIDS-2025, 5 seeds × 4 folds, paired t-test; NSL-KDD cross-check. **Docs' "Ş. Şahin" is wrong: the first author is Canan Batur Şahin.** |
| B17 | J. Rheey, H. Park, "Toward Reliable Intrusion Monitoring for O-RAN Based Networks with Conformal False Alarm Control," *2nd Workshop AI4NextG: AI and ML for Next-Generation Wireless*, ICML 2026 | A (icml.cc page) | AE reconstruction-error Mahalanobis score with a split-conformal FAR budget under exchangeability; 5G traffic. Authors now confirmed from the ICML page. |
| F8 | R. Yumlembam, B. Issac, S. M. Jacob, L. Yang, "Comprehensive botnet detection by mitigating adversarial attacks, navigating the subtleties of perturbation distances and fortifying predictions with conformal layers," *Information Fusion*, 2024 (journal-ref and DOI 10.1016/j.inffus.2024.102529 per arXiv 2409.00667) | A | Conformal layer rejects incorrect predictions of botnet detectors under adversarial examples (ISCX, ISOT). Low overlap. |
| F9 | Z. Li, "Robust Conformal Intrusion Detection via Traffic-Aware Calibration and Attack-Orbit Invariance," arXiv 2609.19241 (preprint; submitted to IEEE TDSC) | A | Conformal coverage for LLM-based NIDS breaks under adversarial feature perturbation. **Anomaly:** the arXiv page shows v1 dated 22 Jul 2026, but a 2609 ID implies September 2026. Recheck before citing. |
| **NEW DT** | F. Şahin, N. S. Mert, "Dual-Threshold Conformal Deferral for Trustworthy Security Alert Triage," *Electronics* 15(18):4084, published 9 Sep 2026, doi:10.3390/electronics15184084 (preprint doi:10.20944/preprints202607.1357.v1) | **R** | See §2a. **Not in any R2 doc, and the most damaging find of this pass.** |
| NEW | B. Althani, "Class-Conditional Conformal Prediction for Reliable Anomaly Detection Under Extreme Class Imbalance," *MAKE* 8(7):190, 2026, doi:10.3390/make8070190 | A | Mondrian conformal anomaly detection on time series (not NIDS). Background for the Mondrian claim. |
| B11 | Bates et al. 2023 (verified, ref #7) | A (earlier pass) | Conformal p-values, FPR bound, dependence. |

### 2a. Key facts from the full texts read this pass

**F4 (Arepalli et al., Discover Informatics 2026).**
* **Protocol.** 15 leave-one-attack-family-out runs on UNSW-NB15 and CIC-IDS2017; 3 seeds for leave-one-attack-out, 5 for triage. Heartbleed and Infiltration are dropped.
* **Novelty scores.**
  * Probability-space score: 1 − max softmax.
  * Feature-space score: **mean Euclidean distance to the k nearest standardised training flows**, Eq. 8. This is the same form as the Aegis kNN score; F4's reference set is training flows, Aegis's is benign-only.
  * Results are family-dependent and sometimes inverted. For example, web attacks: 0.966 probability vs 0.298 kNN; port scanning: 0.166 vs 0.812.
* **Fusion.** §5.8: *"A standardized sum is worse than the better individual score on 10 of 15 families"*. The authors add: *"Combining calibrated p-values rather than raw standardized scores is the natural next step and has not been attempted."* The sum is an oracle diagnostic, not a deployable method.
* **Conformal and thresholds.**
  * Marginal, Mondrian and randomized-APS prediction sets are used for analyst triage. Mondrian restores per-class coverage to at least 0.894.
  * Operational check: thresholds at the empirical 99th/95th percentile of *known-class* calibration scores (nominal 1%/5% FPR). Results are in supplementary Table S13, which was not read.
* **Temporal test.** §5.6 fits on Mon–Wed and calibrates and tests on random halves of Thu–Fri. Coverage on retained labels is 0.902. *"No novelty score was evaluated on these temporal flows."*
* **Not covered:** CSE-CIC-IDS2018 and any cross-dataset test.

**F6 (Mchina et al., Network 2026).**
* **Architecture.** A cascade: Gate CNN (binary) → Attack CNN (multiclass); samples predicted Normal go to the zero-day detector, which outputs NOVEL_ATTACK.
* **Fusion.** Zero-day score = convex weighted sum of four normalised signals: gate attack probability (supervised), AE reconstruction error, GMM NLL and energy.
  * *"Fusion weights are initially calibrated on the validation set under a fixed false positive rate (FPR) budget."*
  * Weights are then adapted online. Signals with a higher recent FPR are down-weighted (true labels in "supervised mode", pseudo-FPR proxies in "unsupervised mode").
  * No conformal guarantee.
* **Data and protocol.** CSE-CIC-IDS2018. Zero-day protocol = Web_Attacks and Infiltration excluded from training and validation. Single seed (42). SUNE is trained and evaluated separately, so there is no transfer test.
* **Results.** Zero-day detection 0.8747 at FPR 0.0019; ablation: each added signal helps (in-distribution only). Adaptive-threshold results are reported in supervised (label-using) mode.

**DT (Şahin & Mert, Electronics 2026).**
* **Design.** Split-conformal, class-conditional control of benign auto-escalation (α) and threat auto-close (β), with realized rates reported.
* **Data.** Four classifiers (XGB, RF, MLP, LR) trained on CIC-IDS2017 and tested on CSE-CIC-IDS2018 (57 harmonised features).
* **Detection after shift.**
  * Cross-dataset recall: XGB 0.194, RF 0.010.
  * Per type, XGB: DoS-Hulk 0.000, SSH-Bruteforce 0.000 (all four models), FTP-BruteForce 1.000.
  * *"the in-distribution ranking of the models inverts under shift"*: XGB is strongest in distribution and among the weakest after the shift.
* **Recalibration.** §6.2 recalibrates on **labelled** target data (random 25k-flow split, not per day). *"A single-threshold, false-positive-only escalation gate … satisfies its α budget (realized FPR < 0.006 across all α) while detecting almost nothing … the certificate is valid and useless."*
* **Stale thresholds.** Thresholds left un-recalibrated give error rates "no longer bounded by α".

---

## 3. Overlap with each Aegis-OSR claim

Claims:
* **C1:** conformal benign-FPR control.
* **C2:** supervised + novelty fusion.
* **C3:** Fisher combination.
* **C4:** Mondrian attribution (known / UNKNOWN-ATTACK / ZERO-DAY-ANOMALY).
* **C5:** LOAFO zero-day evaluation on CICIDS2017.
* **C6:** 2017→2018 transfer with recalibration; "recalibration restores FPR, not detection".
* **C7:** fixed fusion helps in-distribution but hurts under cross-network shift even after recalibration.

Values: **PUB** = ALREADY PUBLISHED; **PART** = PARTIAL OVERLAP; **NF** = NOT FOUND IN THIS PAPER; **?** = not verifiable (unread).

| Paper | C1 | C2 | C3 | C4 | C5 | C6 | C7 |
|---|---|---|---|---|---|---|---|
| CLOSR (TNSM 2026) | NF (threshold-free) | PART (benign + known classes in one learned space) | NF | PART (OSR with unknown rejection) | PART (2 fixed held-out classes, LycoS-IDS2017) | NF | NF |
| FIRCE (SmartNets 2026) | PART (class-conditional conformal rejection, not benign FPR) | NF | NF | NF | NF | PART (CICIDS2018→DFAIR with labelled retraining) | NF |
| FADES (Electronics 2026) | PART | NF (detectors compared, not fused) | NF | NF | NF | PART (cross-dataset incl. CICIDS2018; abstract only) | NF |
| F2 Frontiers AI 2026 | PART (coverage, not FPR at α) | NF | NF | PART (class-conditional conformal) | NF | **PUB**: conformal validity collapses on 2017↔2018 and label-free adaptation fails | NF |
| F3 MaSF (ICLR 2022) | PART (Type-I control, vision) | NF | **PUB** (Fisher/Simes combination of p-values with T1E control, vision OOD) | NF | NF | NF | PART (states the Fisher dilution mechanism; no shift) |
| F4 Discover Inform. 2026 | PART (empirical 1%/5% known-class thresholds; conformal coverage) | PART (both score types evaluated; naive sum hurts 10/15) | NF (explicitly "not attempted") | **PUB/PART** (Mondrian conformal triage on CIC-IDS2017 families; no UNKNOWN vs ZERO-DAY split) | **PUB** (leave-one-family-out on CIC-IDS2017 with the same kNN score) | NF (temporal Thu–Fri random-half recalibration only; no 2018) | PART (in-distribution fusion *hurts*, the opposite sign; no shift) |
| F5 ConFID (IoT 2026) | ? (title implies conformal one-class) | ? | ? | ? | ? | ? | ? |
| F6 Network 2026 | PART (fusion weights at a fixed FPR budget, empirical, no conformal) | **PUB** (supervised probability + AE + GMM + energy fusion; cascade) | NF | PART (known class vs NOVEL_ATTACK cascade) | PART (2 held-out classes on CSE-CIC-IDS2018, 1 seed) | NF | NF; adaptive per-signal FPR weighting is **PUB** (relevant to the proposed stream-gated fusion) |
| F7 HADAR-UAV 2026 | **PUB** (split-conformal FAR) | PART (two unsupervised scores combined) | NF | NF | PART (leave-two-families-out, UAV data, 5 seeds × 4 folds) | NF | NF |
| B17 O-RAN (ICML-W 2026) | **PUB** (split-conformal FAR) | NF | NF | NF | NF | NF | NF |
| F8 Inf. Fusion 2024 | PART (conformal rejection) | NF | NF | NF | NF | NF | NF |
| F9 arXiv 2026 | PART (coverage) | NF | NF | NF | NF | PART (adversarial, not natural shift) | NF |
| **DT Electronics 2026** | **PUB** (class-conditional conformal benign-escalation α with realized rates) | NF | NF | NF | NF | **PUB**: 2017→2018; after recalibration the FPR certificate holds while detection collapses; Hulk and SSH missed | PART (in-distribution *model* ranking inverts under shift; no fusion, no novelty stream) |
| Althani MAKE 2026 | PART | NF | NF | PART (Mondrian anomaly detection, not NIDS) | NF | NF | NF |

---

## 4. Targeted 2024–2026 searches (task 3)

Searches run: about 8 web and Crossref queries.

| Query theme | Result that bears on novelty |
|---|---|
| Conformal / open-set NIDS failing on 2017→2018 | **DT (Şahin & Mert 2026)** already reports that, on CIC-IDS2017→CSE-CIC-IDS2018, a recalibrated false-positive-only conformal gate meets α while detection collapses. **F2** reports coverage collapse. No paper found in which a *novelty / open-set* score is evaluated under 2017→2018 at a fixed conformal α. Open-set papers using both datasets (VAEMax, arXiv 2403.04193; DOC++, ScienceDirect S221421262300100X) were **not checked** (titles from search only). |
| Supervised + novelty fusion for zero-day NIDS | **F6** (convex fusion at a fixed FPR budget). **F4** (sum hurts; p-value combination "not attempted"). **ZeroDefense**: A. Wakili, S. Bakkali, *J. Electron. Sci. Technol.* 24(1):100345, 2026, doi:10.1016/j.jnlest.2026.100345, a cascade of an unsupervised-detector fusion and a supervised ensemble; title and search snippet only, **abstract NOT VERIFIED**. **Ren & Bao**, "Adaptive Fusion of Closed-World and Open-Set Detectors for Zero-Day Attack Generalization in Industrial IoT Intrusion Detection," Research Square preprint, doi:10.21203/rs.3.rs-10465303/v1 (Aug 2026); **title only**. |
| Per-stream reliability weighting / adaptive evidence fusion | **F6** down-weights signals with a higher recent FPR, with labels or pseudo-FPR proxies. This directly precedes any "stream-gated / reliability-weighted fusion" method claim, though it has no conformal validity and no shift test. ADAPT-IDS (ResearchGate, unverified) fuses drift signals, not detectors. |

---

## 5. Classical source for the Fisher vs minimum-p (Tippett) power trade-off (RES-16)

| Source | Verified record | What it supports |
|---|---|---|
| A. Birnbaum, "Combining independent tests of significance," *JASA* 49(267):559–574, 1954, doi:10.1080/01621459.1954.10483521 | Crossref | No combiner is uniformly most powerful; each admissible combiner is optimal against some alternative (as summarised in Heard & Rubin-Delanchy's abstract; Birnbaum's own text not read). |
| N. A. Heard, P. Rubin-Delanchy, "Choosing between methods of combining p-values," *Biometrika* 105(1):239–246, 2018, doi:10.1093/biomet/asx076 (arXiv 1707.06897) | Crossref + full text read | Proposition 2: Tippett (minimum p) is optimal when a single test carries the signal. Fisher and Tippett power differ by alternative. |
| M. Haroush et al., ICLR 2022 (MaSF), §3 | Full text read | *"[Fisher] is suitable for detecting dense signals … [Simes/min] is adept for detection of a sparse signal."* Also: *"In the Fisher test, the more test statistics from true null hypotheses are combined, the greater the noise to signal ratio."* This is the Aegis "dilution" mechanism. |
| T. M. Loughin, "A systematic comparison of methods for combining p-values from independent tests," *CSDA* 47(3):467–485, 2004, doi:10.1016/j.csda.2003.11.020 | Crossref and RePEc | Simulation comparison of combiners. **Content NOT VERIFIED** (paywalled; no abstract available); cite only after reading. |
| R. C. Littell, J. L. Folks, "Asymptotic optimality of Fisher's method of combining independent tests," *JASA* 66(336):802–806, 1971, doi:10.1080/01621459.1971.10482347 | Crossref | Fisher's method is Bahadur-optimal (title-level; text not read). |
| L. H. C. Tippett, *The Methods of Statistics*, Williams & Norgate, 1931 | Cited in Heard & Rubin-Delanchy; not independently verified | Origin of the minimum-p combiner. |

**Recommendation.**
* Cite Birnbaum (1954) together with Heard & Rubin-Delanchy (2018) as the classical statement, and MaSF §3 for the dense/sparse and dilution argument.
* Caveat: these results assume independent p-values. Aegis's streams are dependent and their *sum* is calibrated, so the analogy is a mechanism explanation, not a theorem applied directly.

---

## 6. Conclusions (15 closest-prior-work papers checked)

**(a) Already published. Do not claim as new.**
* **C1, conformal FPR control for intrusion detection:** B17, HADAR-UAV and DT, plus the general theory in Bates et al. 2023.
* **C2, fusing supervised and anomaly evidence for zero-day NIDS:** F6, including weights set at a fixed FPR budget and adaptive per-signal FPR weighting.
* **C3, Fisher combination with Type-I control:** MaSF (outside NIDS).
* **C5, leave-one-family-out on CIC-IDS2017:** F4, which uses the same kNN mean-distance score and reports family-dependent, sometimes inverted novelty signals.
* **C4, Mondrian / class-conditional conformal on NIDS families:** F4 (triage) and F2.
* **C6, conformal guarantees failing on 2017→2018:**
  * F2 reports coverage collapse and failed label-free adaptation.
  * DT reports that after recalibration the FPR certificate holds while detection collapses ("valid and useless"), with DoS-Hulk and SSH missed by XGBoost.
  * **This removes the "recalibration restores FPR, not detection" gap recorded in the novelty-position notes.**
* **Model-ranking inversion under 2017→2018 shift** (in-distribution best becomes worst): DT, at the model level.

**(b) Plausibly distinguishable, on narrow grounds only. None of these was found in the 15 papers checked.**
1. **Evidence-stream decomposition under 2017→2018.** Recalibration uses benign flows only, from the earliest window of each capture day, temporally disjoint from evaluation. Under that setup, the supervised stream keeps its within-day ranking while the benign-referenced kNN stream goes stale. As a result the in-distribution-best Fisher fusion falls below its own supervised component (seed-level, 5/5).
   * DT shows the analogous inversion only across *models*, with labelled, random-split recalibration and no novelty stream.
   * F4 shows fusion hurting in-distribution, but with no shift.
   * The mechanism is classical (§5) and must be cited, not claimed.
2. **Conformally calibrated combination of supervised and kNN surprisals for NIDS under LOAFO.**
   * F4 explicitly says p-value combination was "not attempted".
   * F6's fusion has no conformal validity.
   * This is an engineering combination of published parts, not a methodological contribution.
   * Aegis's in-distribution gain from fusion must be reconciled with F4's finding that a naive sum hurts on 10 of 15 families.
3. **The three-way UNKNOWN-ATTACK vs ZERO-DAY-ANOMALY label.** At most a minor detail.

**(c) Remaining unread or unverifiable items.**
* **ConFID:** abstract inaccessible.
* **ZeroDefense, and the Ren & Bao preprint:** titles only.
* **VAEMax and DOC++:** 2017/2018 open-set papers, not checked.
* **FADES:** abstract only.
* **Lower-priority details:**
  * F4 supplementary Table S13 (realized FPR at the 1%/5% thresholds) was not read.
  * Loughin 2004 content not read.
  * Liu 2020 page range not verified.
  * Fisher's 4th-edition year is unresolved (1932 vs 1934).
  * F9's arXiv date and ID are inconsistent.
* **Not re-checked this pass:** B13 Verkerken (TNSM 2023), the closest architectural prior, which the paper also does not cite. CLOSR and FIRCE content assessments rely on the earlier R2 full read; their bibliographic data were re-verified here.

**Required edits flagged, not made:**
* Add the closest-prior-work citations to both paper versions.
* Remove or correct the abstract claim that anomaly detectors "offer no control over their false-alarm rate".
* Update the R2 docs:
  * FIRCE now has an IEEE DOI.
  * F4, F5 and F6 authors and venues, as listed above.
  * HADAR-UAV first author is C. B. Şahin.
  * MaSF is confirmed as ICLR 2022.
  * Add DT and FADES.
