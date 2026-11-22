# Research integrity report — Phase 2 (research integrity and publication closure)

**Date:** 2026-11-18
**Branch:** `research/phase2-integrity`, local and not pushed. Based on `remediation/phase1-application-ml` @ `3148969`.

**Untouched:**
* the frozen v1.1 models and the 16 frozen files;
* the 25 manifest-protected research artifacts;
* `main` and `v3-openset-research`.

**No retraining and no threshold selection.** Two new evaluations were run, each writing new, versioned artifacts:
* the frozen v1.1 detector scored once on its existing test split at fixed thresholds;
* a re-analysis of per-flow scores that already existed.

The per-claim classification is in `CLAIM_AUDIT.md` §11.

---

## 1. New evaluations (E-01 to E-05; all actually run)

### Scripts and outputs

| Script | Output (new, versioned; the script refuses to overwrite) | Reproduction anchor |
|---|---|---|
| `scripts/71_v11_reeval.py` (E-01, E-02, E-03) | `research_artifacts/v11_reeval/` with `MANIFEST.json` (SHA-256 of inputs and outputs, code commit) | The recomputed 0.5 metrics equal `model_metadata.json:test_metrics_binary` to within 1e-9. DT `predict()` equals `proba ≥ 0.5` on every test row. |
| `scripts/72_matched_fpr_reanalysis.py` (E-04, E-05) | `research_artifacts/reanalysis/` with `MANIFEST.json` | Conformal metrics recomputed from the per-flow dumps equal the committed records: 3,160 values, maximum difference 5e-7 (the records are rounded to 6 decimals). |

### Rules that applied to every evaluation

* Thresholds were fixed in advance: 0.5 is the historical argmax, and 0.85 was chosen on the validation split.
* The test split selected nothing.
* "Matched-FPR" numbers set the threshold on the evaluated benign flows. They are **oracle ranking comparisons**, labelled as such, and are never presented as operating points.

## 2. Corrected metrics

### 2.1 Frozen v1.1 binary detector on its test split (ML-1)

504,151 rows: 419,012 benign and 85,139 attack.

| Metric | @ 0.5 (historical figure, labelled "@ 0.85") | @ 0.85 (deployed) |
|---|---|---|
| Precision | 0.98404 | 0.99549 |
| Recall | 0.99700 | 0.99217 [0.99155, 0.99274] |
| F1 | 0.99048 | **0.99382** |
| FPR | 0.00329 | **0.00091** [0.00083, 0.00101] |
| TP / FN / FP | 84,884 / 255 / 1,377 | 84,472 / 667 / 383 |

ROC-AUC 0.99916 and PR-AUC 0.99744 do not depend on the threshold. Intervals are Wilson 95 %.

**Caveat (ML-20).** This is a random IID split of session-correlated flows. It is optimistic for unseen traffic and is not a temporal estimate.

### 2.2 End-to-end per family (ML-2)

| Family | n | Detected @ 0.5 | Detected @ 0.85 | Detected and correctly named @ 0.85 |
|---|---|---|---|---|
| Bot | 389 | 80.5 % | **57.1 %** | 57.1 % |
| WebAttack | 429 | 97.7 % | **37.3 %** | 36.8 % |
| BruteForce | 1,830 | 99.7 % | 99.7 % | 99.7 % |
| DoS | 38,749 | 99.6 % | 99.4 % | 99.4 % |
| PortScan | 18,139 | 99.98 % | 99.97 % | 99.9 % |
| DDoS | 25,603 | 99.99 % | 99.99 % | 99.99 % |

* Stage-2 macro-F1 is **0.99813**. That figure applies the family model to every true attack, so it assumes a perfect first stage.
* End-to-end 7-class macro-F1 is **0.890 @ 0.5** and **0.881 @ 0.85**.
* The low macro-F1 is driven by Bot and WebAttack: at 0.85, recall is 0.571 and 0.368 and precision 0.813 and 0.840.

**The deployed detector misses most web attacks and about 43 % of botnet flows.** The threshold rule maximised overall F1, which DoS and DDoS dominate. Fixing this needs a **new** model version with per-family recall floors chosen on validation data (PR-11). That is not part of Phase 2; the frozen model is unchanged.

### 2.3 Benign incident rate per policy (ML-4)

**Data:** 82,111 benign flows held out from **both** the frozen model and the Zero-Day Gate (the full eligible set of `scripts/52`, not only the 8,000-flow replay sample).

**Benign incident rate:**

| Policy | Rate | Wilson 95 % |
|---|---|---|
| `frozen` (default since P0) | **0.077 %** | [0.060, 0.098] % |
| `gate` | **0.896 %** | — |
| `union` | **0.934 %** | [0.871, 1.002] % |

**Detection by policy** (gate α = 1 %), on the same doubly held-out set:

| Family | n | frozen | gate | union |
|---|---|---|---|---|
| WebAttack | 77 | 41.6 % | 100 % | 100 % |
| Bot | 82 | 58.5 % | 92.7 % | 93.9 % |
| Heartbleed (never trained on) | 11 | 0 % | 100 % | 100 % |
| Infiltration (never trained on) | 36 | 0 % | 50 % | 50 % |

**Product implication (a decision for the user, not taken here).** Under the default `frozen` policy:
* the gate-only WebAttack, Bot and natural-unknown detections are recorded as Zero-Day Candidates, with no incident;
* switching to `union` would raise them to incidents, at about 12× the benign incident rate.

The Bot and WebAttack samples are small. They are the same flows as in the replay pool.

### 2.4 Re-analysis at matched false-alarm rates (RES-2, RES-3, RES-4, RES-7, RES-22)

The table reports differences in recall. The hierarchical bootstrap resamples families or days, then seeds within each.

| Comparison | Mean | Hierarchical 95 % CI | Seeds | Groups | Seed-level p |
|---|---|---|---|---|---|
| LOAFO: Aegis-OSR − XGB, zero-day recall, conformal | +0.216 | [+0.082, +0.395] | 5/5 | 6/6 families | — |
| LOAFO: Aegis-OSR − XGB, matched 1 % FPR | **+0.218** | [+0.079, +0.396] | 5/5 | 6/6 families | 0.00015 |
| LOAFO: Aegis-OSR − DT, matched 1 % FPR | +0.461 | [+0.222, +0.704] | 5/5 | 6/6 families | — |
| 2018 per-day, recal@2000: Fisher − XGB, known recall, conformal | **−0.237** | [−0.504, −0.012] | 0/5 | 4 of 8 days | 0.0014 (day-level Wilcoxon 0.31) |
| Same, matched 1 % FPR | −0.202 | [−0.435, −0.010] | 0/5 | 3 of 8 days | — |
| 2018 per-day, recal@2000: max fusion − XGB, matched 1 % FPR | −0.043 | [−0.152, +0.033] | 0/5 | 3 of 8 days | — |

**What this establishes:**

1. **The LOAFO headline survives** three checks: matched FPR, family-level uncertainty, and the DT tie artefact. The family-level interval [+0.079, +0.396] is about four times wider than the seed-level one ([+0.180, +0.252]), so seed-level CIs understate the uncertainty. The decision tree realises 0.31 % FPR at α = 1 % because of tied scores (RES-2). At matched FPR it is still far behind, so the paper's DT comparison keeps its direction.
2. **The fusion inversion after recalibration is real but day-dependent.** On the four days where XGB still separates attacks (02-14, 02-15, 02-16, 02-20), Fisher fusion loses heavily. On the other four, every method detects under 5 %. Max fusion almost matches XGB. So the loss is specific to sum-type fusion.
3. **This is the classical Fisher vs min-p trade-off** (Birnbaum 1954; Heard & Rubin-Delanchy 2018). It is now observed directly in the per-flow scores: kNN AUROC is 0.407 on 02-14 and 0.046 on 02-16. It is cited, not claimed as new (RES-16).
4. **Temporal shift is neutral at matched FPR (RES-4).** At oracle@2000, Friday is −0.008 (2/5 seeds) and Thursday +0.012 (4/5). "Inversion specific to cross-network shift" is withdrawn.
5. **The 2018 recalibration results are validated:** the committed per-day records were reproduced exactly from the per-flow dumps. Realised FPR after recal@2000 still ranges from 0.00 % to 8.84 % across days (seed means). Max fusion realised 2.5 % on 02-15.

## 3. Claims removed or qualified

The full classification table is in `CLAIM_AUDIT.md` §11. In summary:

| Claim | Status | Changed in |
|---|---|---|
| "Binary test results (DT @ 0.85)" F1 0.99048 / recall 0.99700 | **Corrected**: @ 0.5; 0.85 figures added | PROJECT_REPORT, VIVA_QA, PRESENTATION, DEMO, GENERALIZATION, `publication.py` v11 table, README note, ModelsPage label |
| Macro-F1 0.998 as system performance | **Corrected**: conditional on stage 1; end-to-end per-family added | same |
| P10 Friday "temporal generalization" F1 0.99770 | **Unsupported** (scored training rows) → marked superseded | GENERALIZATION (banner), PROJECT_REPORT, VIVA_QA, IMPLEMENTATION_STATUS, docs index |
| Benign false-alarm rate ~0.09 % as the system rate | **Corrected**: per-policy rates | README, `config.yaml` comment |
| P11 "measured" mitigation 1.00 / 0.80 | **Corrected**: harness validation, by construction | PROJECT_REPORT, VIVA_QA, PRESENTATION, DEMO, EMPIRICAL_MITIGATION, `publication.py` p11 table, DOCX |
| "Ports dropped" | **Corrected**: Destination Port is a feature | PROJECT_REPORT, VIVA_QA |
| "Guaranteed benign false-alarm rate" | **Corrected**: conditional on exchangeability | README |
| "Recalibration restores false-alarm control" | **Corrected**: re-targets the threshold; 0–8.84 % per day | README, AEGIS_OSR, gap analysis, both papers |
| "A classifier retrained on CICIDS2017" | **Corrected**: the same 2017 classifier, not retrained | both papers |
| "The shift moves scores rather than removing the signal" | **Corrected**: true on 2 days, not on 4 of 8 | both papers |
| "Evidence points to an extractor confound" | **Unsupported**: now hypothesis wording; needs new data | both papers |
| "It cannot create separation the evidence lacks" (decision E, remaining sentence) | **Corrected** to "cannot restore separation that the fused score has lost" | both papers |
| "Inversion specific to the cross-network setting" | **Unsupported**: withdrawn | PRIOR_WORK_COMPARISON §3 |
| "Anomaly detectors offer no control over their false-alarm rate" | **Corrected** (contradicted by cited and closest work) | paper.tex abstract |
| "Recalibration restores FPR, not detection" as a novel gap | **Unsupported as novelty**: Şahin & Mert 2026 report the analogous result | papers' related work; RESEARCH_ALIGNMENT_REVIEW §2 |

Old figures are kept where they appear, relabelled or inside a marked correction. Forbidden-phrase tests stop the old wording from reappearing (`tests/test_phase2_research_integrity.py`).

## 4. Publication closure (R1b) — **not complete**

| Check | Result |
|---|---|
| Tables derive from canonical result files | PASS: `scripts/62` regenerated them. New `inversion` table; `v11` and `p11` corrected. `tests/test_publication_tables.py` and `test_paper_claims.py` pass, except the LaTeX staleness check (below). |
| Number macros | PASS: `scripts/59` regenerated them. 40 new `ra_*`, `v11_*` and `policy_*` facts, each with its artifact path. `v11_f1` now uses the like-for-like 0.85 figure (0.994) beside the 2018 F1; the argmax figure is kept as `v11_f1_argmax`. |
| DOCX ↔ LaTeX values | DOCX rebuilt (19 tables) and exported to PDF with Word. Spot check: the new facts (−0.237, 0.994, 57.1 %, 36.8 %) appear in the DOCX PDF. **LaTeX cross-check pending** (needs the compiled PDF). |
| References valid | PASS for existence: 40/40 DOCX references exist (38 fully verified; 2 partial: Liu 2020 pages, Fisher 4th-edition year). Three references added and verified on Crossref: Birnbaum 1954, Heard & Rubin-Delanchy 2018, Şahin & Mert 2026. |
| **paper.tex compiles; PDF validated** | **NOT DONE.** Tectonic 0.17.0 was re-downloaded and its SHA-256 matches the recorded release digest, but running it was blocked by the session's permission policy. `tests/test_publication_tables.py::test_compiled_latex_paper_is_validated_and_current` fails as designed, because the sources changed after the last validation. |

**To close R1b:**
1. Run `cd docs/research && <tectonic.exe> --keep-logs --outdir <out> paper.tex`.
2. Run `python scripts/63_validate_latex_pdf.py --pdf <out>/paper.pdf --log <out>/paper.log`.
3. Commit `Aegis_OSR_paper_ieee.pdf` and `latex_validation.json`.

R1b is **not** declared complete until then.

## 5. R2 literature closure

Full detail: `R2_LITERATURE_VERIFICATION.md`. 15 closest papers were checked.

**Already published (do not claim):**
* conformal FPR control for intrusion detection (O-RAN workshop paper, HADAR-UAV, Şahin & Mert);
* supervised + anomaly fusion at a fixed FPR budget, with adaptive per-signal weighting (Mchina et al., *Network* 6(2):23 — formerly "F6");
* Fisher combination with Type-I control (MaSF);
* LOAFO on CIC-IDS2017 with the same kNN mean-distance score (Arepalli et al., *Discover Informatics* 1:33 — formerly "F4");
* conformal failure on 2017→2018, and **"recalibration keeps the error certificate while detection collapses"** (Şahin & Mert, *Electronics* 15(18):4084, 2026).

The last one removes the gap that the previous novelty notes relied on.

**Narrowly distinguishable** (not found in the 15 papers checked):
* the stream-level decomposition under 2017→2018 with benign-only, time-disjoint recalibration: the supervised stream keeps its ranking, the kNN stream goes stale, and Fisher fusion falls below its own classifier;
* conformally calibrated supervised + kNN surprisal fusion under LOAFO.

The first is an empirical observation with a classical mechanism. The second is an engineering combination, and it must be reconciled with Arepalli et al.'s report that a naive summed fusion hurts on 10 of 15 families. That statement has not been independently re-read: the publisher's page is behind a login.

**Still unread:**
* ConFID's abstract;
* ZeroDefense and the Ren & Bao preprint (titles only);
* VAEMax and DOC++;
* FADES full text;
* Verkerken 2023 (not re-checked; the closest architectural prior, and uncited in the papers).

~~**Citation gap remaining.** Neither paper yet discusses CLOSR, FIRCE, MaSF, Arepalli et al. or Mchina et al.~~ **Closed 2026-11-22.** Both papers now have a "Closest Prior Work" subsection citing CLOSR, FIRCE, Arepalli et al., Mchina et al., MaSF and Ahmed et al. (refs 44–49 in the DOCX). Bibliographic records were re-checked against Crossref on 2026-11-22; Mchina et al. and Ahmed et al. design statements against their Crossref abstracts. **Still not independently re-checked:** the Arepalli et al. full text (Springer login wall); the papers state only its design (conformal triage, probability- vs k-NN novelty, leave-one-family-out) and that it has no cross-network test, as read in the R2 pass, and quote none of its numbers. CLOSR is described as not compared, and no advantage over it is claimed.

## 6. Readiness for R3 — **not ready**

| Blocker | Status |
|---|---|
| PR-01 randomised conformal p-values; amend H4 (RES-2) | Open. The matched-FPR analysis confirms that the tie artefact is real (DT realises 0.31 % at α = 1 %). |
| PR-02 tuning with an equal budget, frozen configs; temporal protocol (RES-10) | Open |
| PR-03 equal data volume, unified names, feature-only leakage hash (RES-18) | Open |
| PR-04 design-free confirmation flows (RES-6) | Open |
| H1c bar | Must change to **superiority over the best fixed alternative**. Max fusion is within −0.043 of XGB at matched FPR, so beating Fisher is not a meaningful bar. |
| Novelty framing | The R3 question must be re-scoped in light of Şahin & Mert (2026) and Mchina et al. (2026). Benign-only reliability signals already fail the pre-registered H1b on the discovery data (ρ = −0.41). |
| R1b LaTeX compile | Pending (§4) |

**Recommendation.** A reduced R3 run is defensible only after PR-01 to PR-03 are implemented and approved. It should be scoped as **"when does fixed fusion help or hurt, at matched FPR, with family- and day-level uncertainty"**, and should not claim a new detector.

## 7. Not done in Phase 2

* **Docker runtime verification:** the Docker Desktop daemon is still not running.
* **Infrastructure workstream:** not started, for the same reason.
* **Protected manifest:** the new versioned artifacts are not added to `PROTECTED_MANIFEST.json`. The scripts refuse to overwrite them, and the tests check their manifest hashes. Adding them to the manifest is optional.
* **Old PPTX / Word drafts outside `docs/`:** not edited. `PROJECT_REPORT.md` names the authoritative sources.
