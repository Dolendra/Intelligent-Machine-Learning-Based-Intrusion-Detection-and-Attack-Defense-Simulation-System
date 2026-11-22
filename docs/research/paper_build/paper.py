"""Builds the Aegis research paper (.docx). Every number is taken from the project's result files
(see the provenance notes in the companion checklist).

R1a: the sections touched by the claim audit (significance, gate head-to-head, explanation study,
abstract statistics) now read their numbers from docs/research/paper_numbers.json and the result
JSON files at build time instead of hand-typed strings. Run scripts/59_paper_numbers.py first."""
import json as _json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
import sys as _sys

_sys.path.insert(0, str(_ROOT))
from research import publication as PUB  # noqa: E402  canonical tables + prose facts (R1b)

TABLES = PUB.build_tables()
import subprocess as _sp

_GIT_COMMIT = _sp.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=_ROOT, text=True).strip()
F = {k: v.display for k, v in PUB.facts().items()}
# Order in which tables appear below; Roman numerals for cross-references are derived from it
# and checked against the builder's own numbering at the end of the build.
TABLE_ORDER = ["data", "cand", "v11", "loafo", "significance", "family", "temporal", "adapt", "gate", "v11_2018",
               "cross", "cross_perday", "inversion", "r3", "families", "range_def", "range_det", "xai", "p11", "perf"]
_NUM = _json.loads((_ROOT / "docs" / "research" / "paper_numbers.json").read_text(encoding="utf-8"))
_SUMMARY = _json.loads((_ROOT / "research_artifacts" / "openset_loafo_summary.json").read_text(encoding="utf-8"))
_GATE = _json.loads((_ROOT / "research_artifacts" / "zero_day_gate_report.json").read_text(encoding="utf-8"))["evaluation"]
_XAI = _json.loads((_ROOT / "models" / "trained_models" / "xai_stability_report.json").read_text(encoding="utf-8"))


def N(key: str) -> str:
    """Display string of a paper number, converted from LaTeX to plain text."""
    s = _NUM[key]["display"].replace("\\%", "%")
    if "\\times10^{" in s:
        mant, exp = s.split("\\times10^{")
        s = f"{mant}×10^{{{exp.rstrip('}').replace('-', '−')}}}"
    return s


def _sci(v: float) -> str:
    m, e = f"{v:.1e}".split("e")
    return f"{m}×10^{{{str(int(e)).replace('-', '−')}}}"

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from docbuilder import ROMAN, Paper

HERE = Path(__file__).parent
FIG = HERE / "figs"
OUT = Path(r"D:\IDS-Project\docs\research\Aegis_Research_Paper.docx")

P = Paper()
d = P.doc

TR = {k: ROMAN[i] for i, k in enumerate(TABLE_ORDER)}  # "Table {TR['loafo']}" in prose


def PT(key: str, **override) -> None:
    """Emit a canonical table (research/publication.py) — never hand-typed rows."""
    t = TABLES[key]
    kw = {"widths": t.docx.get("widths"), "label": key, "notes": t.notes or None}
    if t.docx.get("size"):
        kw["size"] = t.docx["size"]
    kw.update(override)
    P.table(t.title, t.header, t.rows, **{k: v for k, v in kw.items() if v is not None})

# =====================================================================================  TITLE
t = d.add_paragraph(); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
t.paragraph_format.space_after = Pt(10)
r = t.add_run("Aegis: Open-Set Network Intrusion Detection with Conformal False-Alarm Control "
              "and a Trace-Driven Cyber Range for Measured, Human-Gated Response")
r.font.size = Pt(17)

a = d.add_paragraph(); a.alignment = WD_ALIGN_PARAGRAPH.CENTER
a.paragraph_format.space_after = Pt(2)
r = a.add_run("Nelluri Dolendra Sai Teja, Edla Harshavardhan, Chittuluri Naveen, and R Rahul")
r.font.size = Pt(11)
af = d.add_paragraph(); af.alignment = WD_ALIGN_PARAGRAPH.CENTER
af.paragraph_format.space_after = Pt(14)
r = af.add_run("Department of Computer Science and Engineering, Rajiv Gandhi University of Knowledge Technologies (RGUKT), Basar, Telangana, India\n"
               "[corresponding-author e-mail]")
r.font.size = Pt(9.5); r.italic = True

# =====================================================================================  ABSTRACT
P.para("**Abstract—**Machine-learning intrusion detectors routinely report F1 scores above 0.99 on public flow "
       "benchmarks, yet they assume a closed world and are rarely tested outside the capture they learned from. We "
       "examine both assumptions and describe Aegis, a detection platform built around the answers. Its frozen "
       f"two-stage detector scores binary F1 {F['v11_f1']} on a stratified CICIDS2017 split, but flags {F['unseen_frozen']} of the "
       f"{F['unseen_total']} naturally occurring unseen attacks in that corpus, and on CSE-CIC-IDS2018 its F1 falls to {F['x_frozen_f1']}. "
       "Aegis-OSR, an open-set gate that runs beside it, adds a classifier's attack evidence to a benign-neighbourhood "
       "distance and calibrates the sum with split-conformal prediction, so that the benign false-alarm rate is "
       "chosen in advance—provided benign test traffic is exchangeable with the calibration traffic. Under "
       f"leave-one-attack-family-out evaluation (six families, {F['loafo_seeds']} seeds) it detected {F['osr_zdr']} (95% CI "
       f"{F['osr_zdr_ci']}) of flows from the withheld family at a realised {F['osr_fpr']} false-alarm rate, against {F['xgb_zdr']} for "
       f"the same classifier alone (difference {N('DeltaXgb')}, 95% CI {N('DeltaXgbLo')} to {N('DeltaXgbHi')}, paired t-test over "
       f"independent seeds p = {N('TpXgb')}, better in {N('PosSeedsXgb')} of {N('LoafoSeeds')} seeds); ten closed-set classifier "
       f"families, including SVMs and MLP, CNN and LSTM networks, caught on average no more than {F['fam_best_heldout']} of a "
       f"withheld family at the same budget. The guarantee does not survive distribution shift: false alarms rose to "
       f"{F['t_fri_osr_fpr']} on a later capture day and to {F['x_osr_fpr']} on the 2018 dataset. Re-calibrating on 2,000 benign "
       f"flows from the new day, without retraining, brought it back under budget ({F['a_fri_recal_2000_osr_fpr']}; "
       f"{F['a_fri_oracle_2000_osr_fpr']} with a random sample), but the effect depended on the window (5,000 early-morning "
       f"flows left it at {F['a_fri_recal_5000_osr_fpr']}). On the 2018 data, re-calibrating separately on each capture day's own "
       f"benign flows brought the average false-alarm rate to {F['pd_recal2000_fpr']}, but the gate then recognised only "
       f"{F['pd_recal2000_known']} of known-family attacks and {F['pd_recal2000_zdr']} of the unseen family, so transfer remains "
       f"unsolved; after that re-calibration the fused score detected fewer known attacks than the classifier alone "
       f"({F['ra_pd_fisher_xgb_conf']}, an exploratory finding), so fusion that helps in-distribution can hurt under shift. To measure what such numbers mean operationally, we built a trace-driven cyber range that replays "
       "recorded flows through the real detectors on a seeded clock and lets a human choose the response. Across "
       f"{F['range_runs']} runs, the frozen detector raised an incident in {F['rz_frozen_detected']} of {F['range_seeds']} zero-day "
       f"runs and the gate in {F['rz_gate_detected']} (mean {F['rz_gate_latency']} s); requiring three alerts within five seconds "
       f"removed false incidents; and isolating the target stopped attacks but blocked {F['r_iso_collateral']} of legitimate "
       "traffic. We report successes and failures side by side and release all code and run records.",
       indent=False, size=9.5)
P.para("**Index Terms—**Network intrusion detection, open-set recognition, zero-day attacks, conformal "
       "prediction, false-alarm control, concept drift, cyber range, explainable AI, MITRE ATT&CK, CICIDS2017, "
       "CSE-CIC-IDS2018.",
       indent=False, size=9.5, space_after=10)

# =====================================================================================  I. INTRODUCTION
P.section("Introduction")
P.para("An intrusion detection system earns its keep in two ways: by catching attacks, and by not burying the "
       "analysts who read its output. The second requirement is easy to underestimate. Benign traffic outnumbers "
       "malicious traffic by orders of magnitude on most networks, so a false-positive rate that looks small on a "
       "benchmark can still produce an unmanageable alert queue [1], [2]. Field studies of security operations "
       "centres (SOCs) describe analysts who disable or ignore detectors precisely because of this [3].")
P.para("Machine-learning detectors trained on labelled flow datasets such as CICIDS2017 [4] address the first "
       "requirement remarkably well when the test traffic resembles the training traffic. Tree ensembles reach "
       "F1 scores above 0.99 on random splits of these datasets, and our own two-stage detector is no exception. "
       "The difficulty is that such numbers say little about the case that matters most operationally: an attack "
       "that the model has never seen. A supervised classifier partitions the entire feature space among the "
       "classes it was trained on [5]. A novel attack therefore lands in one of those regions, and because benign "
       "traffic occupies most of the space, it frequently lands in the benign one. Unsupervised anomaly detectors "
       "avoid that trap but trade it for another: their threshold is usually set by hand or by a contamination "
       "parameter, and the resulting false-alarm rate on real benign traffic is unknown until it is measured.")
P.para("This paper reports on Aegis, an intrusion detection platform built as a final-year project and then "
       "extended into a research study. Aegis began as a decision-support system: a frozen two-stage detector "
       "(a Decision Tree that separates benign from malicious flows, followed by a Random Forest that names the "
       "attack family), with explanations, a risk score, recommendations, and a response workflow that requires "
       "human approval. When we tried to evaluate that detector honestly, two problems surfaced. First, it had no "
       f"notion of an unknown attack; of the {F['unseen_total']} Heartbleed and Infiltration flows that it never saw in "
       f"training, it raised an alert on {F['unseen_frozen']}. Second, our early \"temporal\" evaluation turned out to "
       "score the model on rows it had already been trained on, which inflated the result. Both problems pushed us "
       "towards the question this paper is mainly about: *can a flow-based detector raise alerts on unseen attack "
       "families while keeping its benign false-alarm rate at a level the operator chooses in advance?*")
P.para("Our answer is Aegis-OSR, an open-set gate that combines supervised and unsupervised evidence and wraps "
       "the combination in split-conformal calibration [6], [7]. The calibration step is what makes the "
       "false-alarm rate a design parameter rather than an outcome: provided calibration and test benign flows are "
       "exchangeable, the fraction of benign flows that raise an alert is at most α. Exchangeability is a real "
       "assumption, and we test what happens when it breaks.")
P.para("The contributions of the paper are as follows.", keep=True)
P.numbered([
    "**Aegis-OSR**, an open-set detector that maps a classifier's attack evidence and a k-nearest-neighbour "
    "benign-novelty distance into benign surprisals with an exponential tail, sums them, and calibrates the sum "
    "with split-conformal prediction. A Mondrian conformal test then decides whether an alert matches a known "
    "family or should be reported as unknown (Section VI).",
    "**A controlled comparison** against ten alternatives that all pass through the same conformal calibration, "
    "and a separate comparison of ten classifier families—including kernel SVMs and MLP, CNN and LSTM networks—at "
    "a matched 1% false-alarm budget on seen and unseen families (Sections IX–X).",
    "**A generalisation study that reports its failures**: leave-one-attack-family-out over six families and five "
    "seeds; a five-seed temporal split with label-light re-calibration; CICIDS2017 → CSE-CIC-IDS2018 transfer for "
    "both the frozen detector and the open-set gate, with per-day re-calibration; and the "
    f"{F['unseen_total']} naturally occurring unseen attacks.",
    "**A trace-driven cyber range** in which recorded flows meet the real detectors, a per-source incident rule, "
    "firewall controls and a capacity model of the target service on a seeded clock, so that detection latency, "
    f"service impact, collateral damage and recovery are measured rather than assumed; with a {F['range_runs']}-run experiment "
    "programme over defenses, intensity, attacker count, detector choice, alert threshold and approval delay "
    "(Sections VIII, X-H).",
    "**An integrated, human-gated platform** with SHAP/LIME explanations and an explanation-stability study, "
    "MITRE ATT&CK context for every known-family detection and campaign (unnamed zero-day candidates carry none), an approval-based response workflow, and frozen, "
    "hashed, reproducible artefacts (Sections III, VII, X-I).",
])
P.para("The rest of the paper is organised as follows. Section II reviews related work. Section III describes the "
       "platform, Section IV the data, and Section V the closed-set detector. Section VI presents Aegis-OSR. "
       "Section VII covers explanation, threat intelligence, risk and response, and Section VIII the cyber range. "
       "Section IX sets out the experimental protocol and Section X the results. Section XI discusses them, "
       "Section XII lists threats to validity, and Section XIII concludes.")

# =====================================================================================  II. RELATED WORK
P.section("Related Work")
P.subsection("Machine Learning for Flow-Based Intrusion Detection")
P.para("Surveys of machine-learning intrusion detection [8], [9] document a long line of classifiers trained on "
       "labelled corpora, from KDD'99 and UNSW-NB15 [10] to CICIDS2017 and CSE-CIC-IDS2018 [4]. Ring et al. [11] "
       "catalogue these datasets and their limitations. CICIDS2017 in particular has been audited: Engelen et al. "
       "[12] and Lanvin et al. [13] found flow-construction artefacts and labelling errors that change measured "
       "performance. Sommer and Paxson [5] argued more than a decade ago that intrusion detection differs from other "
       "machine-learning tasks because the cost of errors is asymmetric, the data is non-stationary, and the "
       "important events are, by definition, the ones absent from training. Arp et al. [14] turned this into a "
       "checklist of pitfalls, including sampling bias from random splits, data snooping, and reporting metrics that "
       "ignore the base rate. Apruzzese et al. [15] make a similar argument from the operator's point of view. "
       "We treat these papers as design constraints: our evaluation uses held-out families, disjoint calibration "
       "data, fixed false-alarm budgets, and an explicit temporal split.")
P.subsection("Open-Set Recognition and Out-of-Distribution Detection")
P.para("Scheirer et al. [16] formalised open-set recognition, in which a classifier must also reject inputs from "
       "classes not seen in training. OpenMax [17] extended the idea to deep networks with extreme-value modelling "
       "of activations. In the out-of-distribution (OOD) literature, the maximum softmax probability [18], the "
       "Mahalanobis distance [19], the energy score [20], and deep k-nearest-neighbour distances [21] are standard "
       "detectors; Pang et al. [22] review the broader anomaly-detection field, including autoencoders and "
       "Isolation Forest [23]. In network security, Kitsune [24] uses an ensemble of autoencoders for online "
       "anomaly detection. These methods produce *scores*; turning a score into an alert still requires a "
       "threshold, and a threshold chosen on one day's traffic carries no guarantee about the next. That gap is "
       "the one Aegis-OSR is designed to close.")
P.subsection("Conformal Prediction and Drift in Security")
P.para("Conformal prediction [6] produces predictions with finite-sample error guarantees under the sole "
       "assumption of exchangeability. Bates et al. [7] showed how conformal p-values can be used to test for "
       "outliers with controlled error, and Angelopoulos and Bates [25] give an accessible treatment of the "
       "split-conformal recipe we use. In security, Transcend [26] and its successor [27] use conformal evaluation "
       "to detect when a malware classifier's predictions can no longer be trusted because of concept drift, and "
       "TESSERACT [28] shows how temporal bias inflates reported malware-detection results. Concept drift more "
       "generally is surveyed in [29], [30]. Our work differs from Transcend in what is being calibrated: we "
       "calibrate a fused statistic built from a supervised and an unsupervised detector, and we use the "
       "calibration both to raise alerts at a fixed benign false-alarm rate and to attribute them.")
P.subsection("Closest Prior Work")
P.para("Several recent papers are close to ours, and we state the differences explicitly. CLOSR [44] learns a "
       "benign-anchored contrastive representation for zero-day and open-set intrusion detection and reports "
       "threshold-free metrics on a single dataset; it does not set an operating point with a false-alarm bound, "
       "and we have not compared against it inside our calibrated pipeline, so we make no claim of better zero-day "
       "detection than CLOSR. FIRCE [45] uses Transcend-style conformal evaluation as a drift signal for a binary "
       "IoT intrusion classifier and retrains with labels when drift is flagged; Aegis-OSR instead calibrates one "
       "open-set alert threshold on disjoint benign data and adapts without labels or retraining. Arepalli et al. "
       "[46] use conformal prediction for intrusion triage and compare probability-space and k-nearest-neighbour "
       "feature-space novelty scores under leave-one-attack-family-out evaluation; their k-NN score has the same "
       "form as ours, but they do not test cross-network shift. Mchina et al. [47] cascade a CNN classifier with an "
       "autoencoder-based zero-day detector on CSE-CIC-IDS2018 and adapt thresholds and fusion parameters at "
       "deployment time without retraining; their fusion is tuned to a false-positive budget rather than calibrated "
       "conformally, and no model is transferred between datasets. Outside intrusion detection, MaSF [48] combines "
       "per-layer empirical p-values with Fisher and Simes rules under Type-I error control; Aegis-OSR sums "
       "surprisals and re-calibrates the sum on a disjoint split, so its validity comes from that final calibration "
       "rather than from a p-value combination theorem. Finally, Ahmed et al. [49] audit label-free monitoring, "
       "including conformal abstention, and test-time adaptation on the same CIC-IDS2017 to CSE-CIC-IDS2018 shift. "
       "That such tools degrade under this transfer is therefore not new; what we add is a matched-false-alarm "
       "measurement of what recalibration restores for fused versus single-stream evidence, across several "
       "evidence models.")
P.subsection("Explainability and Decision Support")
P.para("SHAP [31], [32] and LIME [33] are widely used to explain individual predictions. In intrusion detection "
       "they help an analyst decide whether an alert is plausible, though they do not establish causality. "
       "Security orchestration platforms map alerts to playbooks; Aegis follows that pattern at prototype scale "
       "but keeps every response behind an explicit human approval and never touches a live network.")

# =====================================================================================  III. SYSTEM OVERVIEW
P.section("System Overview")
P.para("Fig. 1 shows the platform. Flows enter as CICFlowMeter records, either uploaded as CSV, extracted from a "
       "PCAP file when the optional extractor is installed (the path fails closed otherwise), or replayed from the "
       "held-out test pool for demonstration. A FastAPI service handles authentication, role-based access control, "
       "rate and size limits, and structured logging. Every flow is scored by two detectors in parallel.")
P.figure(FIG / "fig1_architecture.png",
         "Aegis architecture. The frozen closed-set detector makes the decision of record; the Aegis-OSR gate runs "
         "beside it and adds an advisory zero-day verdict. Explanations, risk, incidents, and the human-gated "
         "response workflow consume both. Solid arrows carry data; dashed arrows lead to the trace-driven cyber range "
         "and the controlled lab plane.", 1.0)
P.para("The **closed-set detector** (version 1.1) was frozen early in the project and its artefacts are pinned by "
       "SHA-256 hash. It produces the decision of record: benign or attack, and if attack, which of six families. "
       "The **Aegis-OSR gate** runs alongside it and attaches a zero-day verdict to every prediction "
       "(BENIGN, a known family, UNKNOWN-ATTACK, or ZERO-DAY-ANOMALY) together with its conformal p-value. The gate is "
       "advisory by design: it never overrides the frozen decision. This separation lets us add open-set "
       "capability without retraining or re-validating the detector already in service, and it keeps the two "
       "sets of numbers in this paper from contaminating each other.")
P.para("Downstream, the platform explains each decision with SHAP or LIME, computes a risk score, opens or updates "
       "an incident, and proposes defensive actions. Proposed actions follow a fixed lifecycle "
       "(propose → dry-run → approve → execute → verify, with rollback on failed verification) and can only be "
       "executed against an in-memory test adapter; a LIVE mode exists in the type system only so that it can be "
       "refused. A React console exposes a dashboard, a detection bench, the cyber range, a live traffic monitor "
       "that replays held-out flows through both detectors, a zero-day laboratory for exploring the α trade-off, a "
       "research view of all experimental results, incident and campaign workspaces, and system health.")
P.para("Throughout the project we kept four kinds of numbers apart, and we keep them apart here: **research "
       "measurements** on dataset splits (Sections V and X-A to X-G); **range measurements**, which are measured "
       "inside the cyber range but depend on its modelled traffic rates and capacities (Sections VIII and X-H); "
       "**storyboard assumptions**, configuration values used only to animate an illustrative attack walkthrough; "
       "and **controlled-lab measurements** from an in-process test plane (Section X-J). Conflating them is a common "
       "way for project reports to overstate what they have shown.")

# =====================================================================================  IV. DATA
P.section("Data and Preprocessing")
P.subsection("Dataset")
P.para("We use the MachineLearningCVE export of CICIDS2017 [4]: five days of traffic (Monday 3 July to Friday "
       "7 July 2017) from a testbed network, converted to bidirectional flows by CICFlowMeter. Monday contains only "
       "benign traffic. Attacks appear on the remaining days: brute-force FTP and SSH on Tuesday; four DoS tools "
       "and Heartbleed on Wednesday; web attacks and Infiltration on Thursday; and a botnet, a port scan, and DDoS "
       "on Friday. We map the fine-grained labels to families—for example, DoS Hulk, GoldenEye, Slowloris, and "
       "Slowhttptest all become DoS—and keep Infiltration and Heartbleed as separate rare families.")
P.para("Cleaning follows the same rules in both pipelines described below: identifier columns (flow ID, source "
       "and destination address, source port, timestamp) are dropped to avoid leaking the testbed's topology, "
       "values are coerced to numbers, rows with infinite or missing values are removed, and exact duplicates are "
       f"dropped. This leaves {F['corpus_rows']} unique flows described by {F['n_features']} numeric features "
       f"(Table {TR['data']}). The removal of duplicates matters more than it appears: CICIDS2017 contains many "
       "repeated flows, and a random split that keeps them can place identical rows in training and test.")
PT("data")
P.subsection("Two Preprocessing Pipelines")
P.para("The frozen closed-set detector and the research study use different preprocessing because they answer "
       "different questions.")
P.runin("Closed-set pipeline (v1.1)",
        f"Families with fewer than 50 flows (Infiltration, Heartbleed) are removed, and the remaining {F['v11_rows']} flows "
        "are split 70/10/20 into training, validation, and test sets, stratified by label, with random state 42 "
        f"({F['v11_train_rows']} / {F['v11_val_rows']} / {F['v11_test_rows']} rows). Features are standardised and reduced "
        "with SelectKBest (ANOVA F-test), fitted on the training split only. We fit two selectors—40 features for the "
        "binary stage and 40 for the multiclass stage—because the features that separate benign from malicious "
        "traffic are not the ones that separate one attack family from another; "
        f"{F['feature_overlap']} features are shared.")
P.runin("Research pipeline (Aegis-OSR)",
        "Flow features span roughly ten orders of magnitude (bytes per second against flag counts). Distances in "
        "such a space are dominated by a handful of features, so for the k-NN and autoencoder detectors we apply a "
        "signed logarithm, standardise with training statistics, and clip:")
P.equation(r"z_i=\mathrm{clip}\left(\frac{\mathrm{sign}(x_i)\ln(1+|x_i|)-\mu_i}{\sigma_i},-8,8\right)", "eq_scale")
P.para("where μ_i and σ_i are the mean and standard deviation of the transformed feature over the training split "
       "(columns with σ_i < 10^{−6} pass through as zero). The transform is monotone per feature, so it does not "
       "change what a tree learns, but it makes Euclidean neighbourhoods meaningful. Each research split is drawn "
       "per seed (60/10/30, stratified), and families are capped so that a run fits in memory: at most 300,000 "
       "benign and 60,000 per attack family in training, 60,000 and 10,000 in validation, and 150,000 and 25,000 "
       "in test.", indent=False)

# =====================================================================================  V. CLOSED-SET DETECTOR
P.section("Closed-Set Detection Stage")
P.subsection("Binary Stage")
P.para("We trained logistic regression, a Decision Tree, a Random Forest [34], and XGBoost [35] on the same "
       "features and compared them on the validation split. Rather than pick the highest F1, we ranked candidates "
       "with a weighted score that reflects what a SOC cares about:")
P.equation(r"S=0.30\,\mathrm{Rec}+0.25\,F_1+0.20\,\mathrm{PR\text{-}AUC}+0.15\,(1-\mathrm{FPR})+0.10\,\max\left(0,1-\frac{t_{\mathrm{inf}}}{2\,\mathrm{s}}\right)")
P.para("where t_inf is the inference time over the validation split. The weights are a project convention, and we "
       f"report the raw metrics so that a reader can apply different ones. Table {TR['cand']} shows that XGBoost has the "
       "best F1 and the lowest false-positive rate, while the Decision Tree has the best recall and the best score. We "
       f"selected the Decision Tree, accepting roughly {F['dt_xgb_fpr_ratio']} times the false-positive rate of XGBoost in "
       f"exchange for about {F['dt_xgb_recall_gap_pp']} percentage points of recall. In hindsight this choice deserves "
       "scrutiny, and we return to it in the Discussion.", indent=False)
PT("cand")
P.para(f"The operating threshold τ = 0.85 was chosen on {F['thr_val_rows']} validation rows as the value that maximises "
       "F1 among thresholds with recall of at least 0.95. Scores between 0.10 and 0.95 are labelled as an uncertainty "
       "band in the console, so that an analyst can see when the model is close to its decision boundary. We also "
       f"tested isotonic calibration of the tree's scores on a {F['calib_rows']}-row sample; it reduced recall "
       f"({F['calib_recall_before']} → {F['calib_recall_after']})"
       + (f" and worsened the Brier score ({F['calib_brier_before']} → {F['calib_brier_after']})" if 'calib_brier_after' in F else "")
       + ", so calibration was left disabled.")
P.subsection("Multiclass Stage")
P.para("Flows that the binary stage calls malicious are passed to an attack-only multiclass model with six "
       "classes (Bot, BruteForce, DDoS, DoS, PortScan, WebAttack). Training it without a benign class means it never "
       "has to repeat the binary decision. Random Forest and XGBoost were compared using 0.7·macro-F1 + "
       f"0.3·weighted-F1; the Random Forest scored {F['mc_score_random_forest']} on validation against "
       f"{F['mc_score_xgboost']} for XGBoost and was selected.")
P.subsection("Test Results")
P.para(f"Table {TR['v11']} gives the frozen detector's scores on the {F['v11_test_rows']}-row stratified test split at both "
       "the argmax threshold 0.5 and the deployed threshold 0.85. Earlier versions of this report labelled the 0.5 "
       f"figures as 0.85; at 0.85 the binary F1 is {F['v11_f1']} (recall {F['v11_recall_085']}, false-positive rate "
       f"{F['v11_fpr_085']}). The aggregate hides a minority-family failure: at 0.85 the two-stage system detects only "
       f"{F['v11_bot_det_085']} of botnet flows (n = {F['v11_bot_n']}) and {F['v11_web_det_085']} of web-attack flows "
       f"(n = {F['v11_web_n']}), and its end-to-end seven-class macro-F1 is {F['v11_e2e_macro_f1']}. The threshold rule maximised "
       "overall F1, which DoS and DDoS dominate. Of "
       f"{F['mc_test_attacks']} attacks in the multiclass test set, {F['mc_misattributed']} were assigned to the wrong family "
       f"when the family model is applied to every true attack, i.e. assuming a perfect first stage; the largest group was "
       f"{F['mc_worst_cell']}. These numbers come from a random split of a single capture, and every family in the test set "
       "was present in training.")
PT("v11")

# =====================================================================================  VI. AEGIS-OSR
P.section("Aegis-OSR: Conformal Evidence Fusion")
P.para("Let z ∈ ℝ^{77} be a preprocessed flow, let class 0 denote BENIGN, and let 1, …, K denote the K attack "
       "families available for training. At test time a flow may also come from a family outside this set. "
       "Aegis-OSR must decide whether to raise an alert and, if it does, whether the alert belongs to a known "
       "family. Fig. 2 summarises the procedure.")
P.figure(FIG / "fig2_aegis_osr.png",
         "The Aegis-OSR gate. Two evidence scores are mapped to benign surprisals on calibration split C₁, summed, and "
         "converted to a conformal p-value on the disjoint split C₂. Alerts are attributed by a class-conditional "
         "conformal test.", 1.0)
P.subsection("Two Sources of Evidence")
P.para("**Supervised evidence.** An XGBoost classifier with K + 1 classes (250 trees, depth 8, learning rate 0.1, "
       "row and column subsampling 0.8) is trained on benign flows and the known families. Because benign flows "
       "outnumber the smallest family by more than a hundred to one, each class c is weighted by")
P.equation(r"w_c=\left(\frac{n_{\max}}{n_c}\right)^{1/2}", "eq_w")
P.para("where n_c is the number of training flows in class c and n_max that of the largest class. Full inverse-"
       "frequency weighting over-corrected in pilot runs and cost benign precision; the square root is a compromise. "
       "The attack evidence is the probability mass the classifier puts outside the benign class,", indent=False)
P.equation(r"s_{\mathrm{sup}}(z)=1-\hat{P}(y=0\mid z).", "eq_sup")
P.para("**Novelty evidence.** A classifier can be confidently wrong about a flow that lies far from anything it has "
       "seen, because its decision regions extend to infinity. To catch such flows we keep a reference set R of "
       "benign training flows (40,000 in the experiments, 20,000 in the deployed gate) and measure the mean "
       "Euclidean distance to the k = 5 nearest of them:", indent=False)
P.equation(r"s_{\mathrm{nov}}(z)=\frac{1}{k}\sum_{j=1}^{k}\left\|z-\mathrm{NN}_j(z;R)\right\|_2.", "eq_nov")
P.para("The two scores are deliberately different in kind. The first knows what attacks look like; the second "
       "knows only what benign traffic looks like. A novel attack that resembles a known family raises the first; "
       "one that resembles nothing at all raises the second.", indent=False)
P.subsection("Benign Surprisal with an Exponential Tail")
P.para("The two scores live on different scales, so they cannot be added directly. We split the benign "
       "validation flows at random into two halves, C₁ and C₂ (30,000 each in the experiments). On C₁ each score is "
       "converted into a *benign surprisal*: the negative log of the fraction of benign flows that score at "
       "least as high. Within the range of C₁ this is an empirical tail probability; beyond the largest benign "
       "score s_j^{max} it would saturate, so we extend it linearly in log space,")
P.equation(r"t_j(z)=-\ln\frac{1+\left|\{u\in C_1:s_j(u)\ge s_j(z)\}\right|}{1+|C_1|}+\frac{\max\left(0,\,s_j(z)-s_j^{\max}\right)}{\tau_j},", "eq_t")
P.para("where τ_j is the mean excess of the top 1% of benign scores over their 99th percentile. This amounts to an "
       "exponential model of the far tail, in the peaks-over-threshold spirit [36], [37]; we do not fit a full "
       "generalised Pareto distribution. The extension costs nothing at the decision threshold, which lies well "
       "inside the empirical range, but it keeps flows far outside the benign range ordered by how far out they "
       "are. That ordering matters for AUROC and for re-calibration with small windows, where s_j^{max} is "
       "reached quickly.", indent=False)
P.subsection("Fisher Fusion")
P.para("The fused statistic is the sum of the two surprisals,")
P.equation(r"f(z)=t_{\mathrm{sup}}(z)+t_{\mathrm{nov}}(z),", "eq_f")
P.para("which is Fisher's method for combining p-values [38], up to a factor of two. Its practical property is that "
       "evidence accumulates: a flow that is moderately unusual to both detectors outranks a flow that is "
       "mildly unusual to one and ordinary to the other. Two alternatives are evaluated as ablations: the "
       "maximum of the two surprisals, and an omnibus rule max(t_sup, t_nov, T(t_sup + t_nov)), where T is the benign "
       "surprisal of the sum estimated on C₁, which fires when either detector alone *or* their joint evidence is "
       "extreme. We stress that the two surprisals are not independent, so the sum does not follow the χ² "
       "distribution that Fisher's method assumes. This does not matter here, because the threshold comes from "
       "conformal calibration, not from the χ² table.", indent=False)
P.subsection("Conformal Calibration and the False-Alarm Guarantee")
P.para("The fused statistic is calibrated on C₂, which played no part in training or in building the surprisal "
       "maps. The conformal p-value of a test flow is")
P.equation(r"p(z)=\frac{1+\left|\{v\in C_2:f(v)\ge f(z)\}\right|}{1+|C_2|},", "eq_p")
P.para("and an alert is raised when p(z) ≤ α. The following is a standard property of split-conformal p-values "
       "[6], [7], [25]; we restate it because the whole design rests on it.", indent=False)
P.para("*Proposition 1.* If the flows in C₂ and a benign test flow z are exchangeable, then for every α ∈ (0, 1), "
       "P(p(z) ≤ α) ≤ α.", indent=False)
P.para("*Proof sketch.* Because f is fixed before C₂ is seen, the |C₂| + 1 values f(v), v ∈ C₂, and f(z) are "
       "exchangeable, so the rank of f(z) among them is uniform (ties broken conservatively). The event "
       "p(z) ≤ α requires f(z) to be among the ⌊α(|C₂| + 1)⌋ largest, which has probability at most α. ∎",
       indent=False)
P.para("Two remarks keep this result in proportion. First, the guarantee is marginal over the draw of C₂. For a "
       "single, fixed calibration set of size n, the realised false-positive rate on future benign flows is "
       "approximately distributed as", indent=False)
P.equation(r"\mathrm{FPR}\mid C_2\sim\mathrm{Beta}\left(\ell,\,n+1-\ell\right),\qquad \ell=\lfloor\alpha(n+1)\rfloor,", "eq_beta")
P.para("whose standard deviation is about √ℓ/(n + 1). With n = 30,000 and α = 0.01 this is "
       f"{100 * (0.01 * 30001) ** 0.5 / 30001:.2f} percentage points; with n = 1,000 it is "
       f"{100 * (0.01 * 1001) ** 0.5 / 1001:.2f}. We use this to read the re-calibration results. Second, the "
       "guarantee says nothing about attacks. Detection power depends entirely on how well f separates attacks "
       "from benign traffic, which is what the experiments measure.", indent=False)
P.subsection("Attribution: Known Family or Unknown?")
P.para("An alert alone does not tell the analyst what to do. Aegis-OSR assigns each flow one of four labels. If "
       "p(z) > α the flow is BENIGN. If the flow alerts but the classifier itself considers it benign "
       "(s_sup < 0.5), the alert came mainly from the novelty channel and the flow is labelled ZERO-DAY-ANOMALY. "
       "Otherwise the classifier's most likely attack family k̂ is tested with a Mondrian (class-conditional) "
       "conformal test [6]. Its non-conformity score is")
P.equation(r"a(z)=1-q(\hat{k}\mid z),\qquad q(k\mid z)=\frac{P(y=k\mid z)}{\sum_{c=1}^{K}P(y=c\mid z)},", "eq_mond")
P.para("where P denotes the classifier's estimated probabilities, so q(k | z) is the probability of family k "
       "renormalised over the attack classes. The score is calibrated separately for each family on validation flows of that family (families with fewer than 20 "
       "validation flows are not tested). If the family-specific p-value exceeds α_fam = 0.01 the alert is "
       "attributed to k̂; otherwise it is labelled UNKNOWN-ATTACK—an attack that looks malicious to the "
       "classifier but does not look like any family it knows.", indent=False)
P.subsection("Label-Light Adaptation")
P.para("When benign traffic shifts, exchangeability fails and Proposition 1 no longer applies. Retraining the "
       "classifier needs labelled attacks from the new environment, which are exactly what an operator does not "
       "have. Aegis-OSR offers a cheaper repair. Given a window of W flows from the new environment that are "
       "believed to be benign—for instance, the first minutes of a new day after analyst review—the method "
       "re-estimates both C₁ and C₂ from the window, leaving the classifier untouched (*recal@W*). A second variant, "
       "*recal+ref@W*, first moves one third of the window into the k-NN reference set, so that the novelty "
       "detector itself learns the new benign modes, and calibrates on the remaining two thirds. Either variant "
       "takes seconds, because it involves only scoring, sorting, and rebuilding a nearest-neighbour index.")
P.subsection("Serving")
P.para("The deployed gate is exported without any deep-learning dependency: the XGBoost model in its native format, "
       "the scaler, the reference set, quantile sketches of the surprisal maps and calibration scores, and the "
       f"Mondrian calibrators. It was trained on {F['gate_train_rows']} flows, calibrated on two benign splits of "
       f"{F['gate_cal_rows']}, and scores a flow in about {F['gate_latency_ms']} ms in batch mode on a 20-thread desktop "
       f"processor. Its outputs agree with the research implementation on {F['gate_parity']} of test flows; the small "
       "difference comes from the quantile sketches.")

# =====================================================================================  VII. TRIAGE & RESPONSE
P.section("Explanation, Risk, and Response")
P.subsection("Explanations")
P.para("For each prediction the analyst can request a local explanation. SHAP values are computed with the exact "
       "TreeExplainer [32] for the tree models, falling back to KernelExplainer over a stored background sample when "
       "a model is not tree-based; LIME [33] is offered as a second opinion. The console shows the top ten "
       "contributing features and a short narrative. A counterfactual helper moves the strongest positive drivers "
       "towards the background median and re-scores the flow, which answers the question \"what would have to change "
       "for this flow to be called benign?\". Globally, the binary tree's own feature importances are highest for "
       f"{F['global_top']}. We present explanations as decision support, not as proof of how an attack works.")
P.subsection("Risk Score")
P.para("Each detection receives a score between 0 and 100,")
P.equation(r"R=w_bB_k+100\left(w_c\,c+w_i\,\iota+w_a\,a\right),", "eq_risk")
P.para("where B_k is a configurable base severity of the family (for example 90 for DDoS, 75 for WebAttack, 45 for "
       "PortScan), c is the model's confidence, ι ∈ [0, 1] is traffic intensity—the larger of the percentile ranks "
       "of the flow's packets per second and bytes per second against training-set percentiles—and a ∈ [0, 1] is the "
       "criticality of the targeted asset. The default weights are (w_b, w_c, w_i, w_a) = (0.50, 0.25, 0.15, 0.10), "
       "and scores are banded into LOW (< 31), MEDIUM (< 61), HIGH (< 81), and CRITICAL. Every response includes the "
       "four additive contributions, so the analyst can see why a score is high. These weights are conventions, not "
       "measured quantities. We checked their sensitivity on four reference cases under three weightings "
       f"(severity-heavy, balanced, operations-heavy): a case's score varied by at most {F['risk_max_move']} points and "
       f"{F['risk_band_changes']} cases changed band.", indent=False)
P.subsection("Incidents and Recommendations")
P.para("Detections of the same family from the same source within five minutes update a single incident rather "
       "than opening new ones, and related detections within thirty minutes share a campaign identifier. Each family "
       "maps to a ranked list of advisory actions with a rationale and an expected effect—for example, rate "
       "limiting and signature filtering for DoS, upstream filtering for DDoS, account lockout and authentication "
       "rate limits for brute force, and tightened web-application firewall rules for web attacks.")
P.subsection("Human-Gated Response")
P.para("A recommendation becomes an action only through an explicit lifecycle: an analyst proposes it, the "
       "platform shows a dry-run preview, a responder or administrator approves it, the controlled adapter executes "
       "it, and a verification step checks the effect. If verification fails, the action is rolled back and cannot "
       "reach a verified state. Approval is an atomic claim: in a test with eight concurrent approvers, exactly one "
       "succeeded. After a crash, in-flight actions are reclaimed and marked failed; they are never replayed "
       "automatically. Roles are bound on the server through signed bearer tokens or a configured API key, so a "
       "client cannot raise its own privileges by editing a request field. Viewers can only read; analysts can "
       "propose and dry-run; responders and administrators can also approve and roll back.")
P.subsection("Threat-Intelligence Context")
P.para("Every detection, recommendation, campaign and range incident carries the MITRE ATT&CK Enterprise tactic and "
       "technique that best describe the family's behaviour: PortScan → Reconnaissance, T1595 Active Scanning; "
       "BruteForce → Credential Access, T1110; WebAttack and Heartbleed → Initial Access, T1190 Exploit Public-Facing "
       "Application; Infiltration → Lateral Movement, T1021; Bot → Command and Control, T1071; DoS → Impact, T1499; "
       "DDoS → Impact, T1498. A campaign's family sequence is summarised as ordered tactics, which tells the analyst "
       "how far along the kill chain an actor has come. The mapping is a documented analyst judgement, not a learned "
       "model; its value is that it lets an alert be read in the vocabulary that threat reports and mitigation "
       "guidance already use.")
P.subsection("Storyboard and Controlled Test Plane")
P.para("For teaching, an *attack storyboard* animates the lifecycle normal → attack → impact → detected → "
       "recommended → defended → recovered on a small topology. The defense effectiveness it displays (for example "
       f"{F['p11_ddos_prior']} for DDoS) is a configuration value and is labelled as such. Before the cyber range existed, "
       "we measured the response path on an in-process test plane: a test client generates attacker and benign "
       "connection attempts, Aegis detects the attack with the frozen models, and an approved action is applied "
       "through the controlled adapter. Its mitigation effectiveness is")
P.equation(r"E=\frac{a_{\mathrm{pre}}-a_{\mathrm{post}}}{a_{\mathrm{pre}}},", "eq_E")
P.para("where a_pre and a_post are the accepted fractions of attack attempts before and after the response, under "
       "three conditions: no defence, recommendation only, and approved controlled response.", indent=False)

# =====================================================================================  VIII. CYBER RANGE  (TRACE-DRIVEN-CYBER-RANGE)
P.section("A Trace-Driven Cyber Range")
P.para("The project's design required that the simulator be a laboratory rather than an animation: every state the "
       "interface shows must come from simulated traffic, real detector output and measured outcomes. Packet-level "
       "emulators such as Mininet need a Linux host; we wanted a range that runs anywhere and whose traffic is "
       "realistic by construction. The Aegis range therefore *replays recorded flows* on a seeded, discrete "
       "simulation clock, and pushes each one through the same components a deployment would use.")
P.subsection("Traffic")
P.para(f"The range draws from a pool of {F['pool_rows']} CICIDS2017 flows that neither detector trained or was "
       f"validated on: {F['pool_benign']} benign flows, {F['pool_attack_range']} per known attack family (as many as are "
       "eligible), and all Infiltration and Heartbleed flows. A flow is eligible only if it lies in both the frozen "
       "detector's and the gate's test splits and in neither model's training or validation data. Each simulated "
       "second, benign arrivals follow a Poisson law with mean 30 from 40 client addresses, half of them addressed to "
       "the target service. Each attacker emits Poisson(ρ·r·I) flows, where ρ is the scenario's base rate, r the "
       "stage's rate multiplier and I a user-chosen intensity; families are drawn from the stage's mixture. A "
       "scenario is a sequence of ground-truth stages—NORMAL (12 s), PREPARATION (3 s), RECONNAISSANCE (8 s at "
       "r = 0.25), ATTACK_INITIATED (6 s at r = 0.4) and ATTACK_ACTIVE (40 s at r = 1)—followed by a 25 s tail. Nine "
       "scenarios cover port scanning, slow host discovery, brute force, DoS, a four-source DDoS, web-attack bursts, "
       "bot beaconing from an infected internal host, a zero-day intrusion built only from Infiltration and "
       "Heartbleed flows, and a multi-stage campaign (scan → brute force → web exploitation → bot command and "
       "control).")
P.subsection("Detection, Incidents and Service")
P.para("A flow first meets the firewall, which applies whichever controls are active. If it passes, it is scored by "
       "the frozen v1.1 detector and the Aegis-OSR gate; because both are deterministic, each pool flow is scored "
       "once and its verdict reused, which makes long experiments cheap without changing any result. An incident is "
       "raised for a source after k alerts within W seconds (k = 3, W = 5 by default), using either detector or "
       "their union. Flows that reach the target consume service capacity: a benign flow costs one unit, DoS and "
       "DDoS flows four, brute-force and web-attack flows 1.5, scans and bot beacons 0.5. With L units arriving in a "
       "second and capacity C = 60 units per second, the target serves a fraction")
P.equation(r"\sigma=\min\left(1,\frac{C}{L}\right)", "eq_serve")
P.para("of what reaches it, and service availability is the share of legitimate target requests served. The "
       "detection side follows the locked state machine NORMAL → SUSPICIOUS (first alert on an attacking source) → "
       "DETECTED → EXPLAINED (SHAP on the triggering flow) → RESPONSE_OPTIONS → MITIGATING → CONTAINED (attack "
       "traffic reaching the target cut by at least 75% over three seconds) → RECOVERY (availability ≥ 98% for three "
       "seconds) → COMPLETED.", indent=False)
P.subsection("Responses")
P.para("Five responses are available: *block source* drops every flow from each detected source, and keeps doing so "
       "for sources detected later; *rate limit* lets 20% of a detected source's flows through; *isolate target* drops "
       "every flow to the target until the attacker has been quiet for five seconds; *monitor only* changes nothing; "
       "and *increase inspection* switches to the union of both detectors with k = 1. The response is either chosen "
       "by the user when the incident is raised (the clock waits) or applied automatically after an approval delay "
       "that stands in for the analyst's decision time. The recommended response follows the family that was "
       "actually detected, so a scanner caught during reconnaissance is blocked before its main attack begins.")
P.subsection("Measurements and Reproducibility")
P.para("Each run records detection latency (attack start → incident), time to mitigate, containment and recovery "
       "times, attack success before and after the response, mean and minimum availability during the attack, the "
       "share of legitimate flows blocked (collateral), per-flow false-positive rates and false incidents (benign "
       "sources that became incidents), and per-detector attack-flow recall. Every state change is an event with a "
       "run identifier, sequence number and simulated time; the configuration, seed, events and per-second "
       "telemetry are saved for each run. A test verifies that the same configuration and seed reproduce identical "
       "metrics. What is *modelled* is stated in the interface and in every result file: arrival rates, per-family "
       "service cost, the 20% pass-through of a rate limit and the target capacity. What is *measured* within that "
       "model is everything the detectors and the firewall do.")

# =====================================================================================  VIII. PROTOCOL
P.section("Experimental Protocol")
P.subsection("Leave-One-Attack-Family-Out (LOAFO)")
P.para("For each of the six trainable families, we remove that family from training and validation and present "
       "it only at test time, as a simulated zero-day. The model is trained on benign flows and the other five "
       "families. The test set contains held-out benign flows, test flows of the five known families, up to 25,000 "
       "flows of the held-out family drawn from *all* of its rows (none of which the model has seen), and the "
       f"{F['unseen_total']} Infiltration and Heartbleed flows, which are unknown in every fold. Depending on the fold, "
       f"the unknown group holds between {F['loafo_unknown_min']} and {F['loafo_unknown_max']} flows; every fold has "
       f"{F['loafo_benign_test']} benign test flows. We repeat this for seeds 1 to 5, with a fresh split per seed, "
       f"giving {F['loafo_runs']} runs. Seed 0 was used to choose the design—Fisher fusion with k-NN novelty—and is "
       "excluded from every number reported here. The six held-out families are the same ones used for that choice, "
       "so a mild selection effect cannot be excluded.")
P.subsection("Temporal Split")
P.para("To test what happens when exchangeability is violated, we train on earlier days and test on a later one: "
       "Monday–Wednesday → Thursday, where web attacks and Infiltration are unknown, and Monday–Thursday → Friday, "
       "where Bot, PortScan, and DDoS are unknown. Unlike LOAFO, the benign test traffic now comes from a different "
       "day than the calibration traffic. The earliest 5,000 benign flows of the target day, in arrival order, are "
       "set aside as the warm-up pool for adaptation and are never tested on. As an upper reference, an *oracle* "
       "re-calibrates on 2,000 benign flows sampled at random from the whole target day. This protocol replaced an "
       "earlier \"Friday holdout\" in our project that scored the frozen models on Friday rows, some of which had "
       "been in their training split; we report no results from that earlier evaluation. The temporal protocol was "
       "run with five seeds (1–5).")
P.subsection("Cross-Dataset Transfer")
P.para("CSE-CIC-IDS2018 was captured a year later on a different, much larger network with different tooling. We "
       f"mapped its labels to the CICIDS2017 families and its columns to the same {F['n_features']}-feature schema, and drew "
       f"a sample of {F['x_sample_rows']} flows ({F['x_sample_benign']} benign, from all {F['x_sample_days']} capture days; DDoS, "
       "DoS, brute force, bot, web attacks and Infiltration, but no port scans): a uniform 5% of each day's benign "
       "flows and, per day and label, a random sample of at most 100,000 attack flows. An earlier version of this "
       f"sample capped each label globally and therefore kept benign flows from only {F['x_v1_benign_days']} of the "
       f"{F['x_sample_days']} days; all 2018 results below use the corrected sample. Three experiments use it. First, the "
       f"*frozen* v1.1 artefacts are scored unchanged on up to {F['x_frozen_per_label_cap']} flows per attack label "
       f"({F['x_frozen_n_total']} flows in total); nothing is retrained. Second, Aegis-OSR and every baseline are trained and "
       "calibrated on CICIDS2017 and tested on the 2018 sample, where Infiltration—never in training—is the unknown "
       "family. Third, the same models are re-calibrated *per capture day*: for each day independently, the earliest "
       "500, 2,000 or 5,000 benign flows of that day form the warm-up window, and evaluation uses only the rest of "
       "that day, so calibration and evaluation flows never overlap. Both open-set protocols were run with five seeds.")
P.subsection("Baselines and Ablations")
P.para("Every method below produces a score per flow, and every score is passed through the same benign-surprisal "
       "map (on C₁) and conformal calibration (on C₂). All methods therefore operate at the same nominal "
       "false-alarm rate, and differences in recall reflect the quality of the evidence rather than a better-tuned "
       "threshold.", keep=True)
P.bullets([
    "*Closed-set XGB*: the Aegis-OSR classifier's s_sup alone.",
    "*Closed-set DT (v1.1-style)*: a balanced Decision Tree of depth 20 trained for benign versus attack, "
    "approximating the production detector.",
    "*XGB + Energy*: the classifier's evidence combined (by maximum) with the energy score −log Σ_c exp(g_c(z)) "
    "of its logits [20].",
    "*k-NN distance*: s_nov alone [21].",
    "*Autoencoder*: an under-complete network (64–32–12 hidden units, LeakyReLU) trained on benign flows with "
    "AdamW and early stopping, scored by variance-weighted reconstruction error.",
    "*Isolation Forest* [23]: 200 trees, 512 samples per tree, trained on benign flows.",
    "*Ablations*: Aegis-OSR with max fusion; with omnibus fusion; with the autoencoder in place of k-NN; and with "
    "Isolation Forest in place of k-NN.",
])
P.subsection("Model Families")
P.para("To ask whether a different or deeper classifier would solve the zero-day problem on its own, we trained ten "
       "binary classifiers on the same research split (seed 1; up to 150,000 benign and 25,000 flows per family): "
       "logistic regression, a decision tree, a random forest, XGBoost, histogram gradient boosting (scikit-learn's "
       "LightGBM-style implementation), a linear SVM, an RBF-kernel SVM approximated with 400 Nyström features, and "
       "three PyTorch networks—an MLP (128–64 units), a one-dimensional CNN and an LSTM that read the 77 features as "
       "a sequence, as is common in the literature. Every model's threshold is set on validation benign flows for a "
       "1% false-alarm rate. Each is evaluated on a stratified test split with all families seen, and on six "
       "leave-one-family-out folds in which the test set holds benign flows and the withheld family only.")
P.subsection("Cyber-Range Experiments")
P.para("The range experiments run each configuration with ten seeds: every scenario × every response (E8, automatic "
       "response after 3 s); intensity 0.5×, 1× and 2× (E6); one, two, four and eight DDoS sources (E7); frozen, "
       "gate or union as the incident source; alert thresholds k ∈ {1, 2, 3, 5, 8} (E3); and approval delays of 0, 3, "
       f"10 and 30 s—{F['range_runs']} runs in all, which took {F['range_runtime_min']} minutes.")
P.subsection("Explanation Stability")
P.para("For twenty held-out replay flows of each class we compute SHAP attributions and measure three things: "
       "consistency (mean pairwise Jaccard overlap of the top-five features among flows of one family), robustness "
       "(Jaccard overlap between a flow's top five and those of the same flow with independent ±1% multiplicative "
       "noise on every feature, plus the Spearman correlation of the top-ten magnitudes), and agreement (Jaccard "
       "overlap of the top five features from SHAP and from LIME).")
P.subsection("Metrics and Statistics")
P.para("The primary metric is *zero-day recall*: the fraction of unknown-group flows that raise an alert at "
       "α = 0.01. We also report the realised benign false-positive rate, the recall on known families, and the "
       "area under the ROC curve for separating unknown from benign flows (AUROC_u), which does not depend on a "
       "threshold. For attribution we report the share of unknown flows labelled UNKNOWN-ATTACK or "
       "ZERO-DAY-ANOMALY, the share wrongly attributed to a known family, and the accuracy of family labels on "
       "known attacks. Each LOAFO metric is averaged over the six folds within a seed, and we give the mean and a "
       "95% Student-t interval over the five seeds. Folds within a seed share one data split and are not "
       "independent, so methods are compared with a paired t-test over the five seed-level means (a Wilcoxon "
       "signed-rank test [39] on five seeds cannot fall below p = 0.0625); fold-level win counts are descriptive only. All experiments ran on a single Windows desktop "
       "(Intel, 20 threads) with Python 3.11.9, scikit-learn 1.9.0, XGBoost 3.2.0, and SHAP 0.51.0; a LOAFO run "
       f"took {F['loafo_fit_s']} s to fit on average and scored about {F['loafo_score_ms']} ms per 1,000 flows with all "
       "eleven methods enabled.")

# =====================================================================================  IX. RESULTS
P.section("Results")
P.subsection("Detection of Withheld Families (LOAFO)")
P.para(f"Table {TR['loafo']} summarises the {F['loafo_runs']} LOAFO runs. Every conformally calibrated method realised a "
       f"benign false-positive rate between {F['fpr_range_calibrated']} against a nominal 1%, and the 95% interval for "
       f"Aegis-OSR ({F['osr_fpr_ci']}) is consistent with the spread that (9) predicts for |C₂| = 30,000. The calibration "
       "therefore behaves as the theory says it should when its assumption holds. The only method that did not realise "
       "≈1% is the Decision Tree, whose scores take very few distinct values, so its conformal threshold cannot be "
       "placed exactly at α.")
PT("loafo")
P.para(f"Aegis-OSR detected {F['osr_zdr']} of withheld-family flows, {F['osr_minus_xgb_pp']} points more than the "
       f"closed-set XGBoost classifier it is built on and {F['osr_minus_dt_pp']} points more than the Decision Tree that "
       f"approximates the production detector. Its recall on known families stayed at {F['osr_known']}. The unsupervised "
       f"detectors are a different story. At a 1% budget, Isolation Forest caught {F['if_zdr']} of unknown flows and "
       f"{F['if_known']} of known ones, and the autoencoder and k-NN distance each missed roughly half of the *known* "
       "attacks. On their own, these detectors would be unusable at this alarm budget; inside Aegis-OSR, the k-NN "
       "distance supplies exactly the signal the classifier lacks.")
P.para("The ablations isolate the two design choices. Holding the novelty detector fixed, Fisher fusion beat "
       f"omnibus fusion by {F['abl_omni_pp']} points and max fusion by {F['abl_max_pp']}. Holding Fisher fusion fixed, k-NN "
       f"novelty beat the autoencoder by {F['abl_ae_pp']} points and Isolation Forest by {F['abl_if_pp']}. One result runs "
       f"the other way: the autoencoder variant has the higher AUROC_u ({F['ae_auroc']} against {F['osr_auroc']}). AUROC "
       "averages over all thresholds, including the high false-alarm regions no SOC would operate in; at the 1% "
       "operating point that we actually use, k-NN is clearly better. This is a concrete instance of the point made "
       "in [14] about choosing metrics that match the deployment.")
_SEED = _SUMMARY["significance_seed_level"]["loafo"]["zero_day_recall"]
_PAIRS = _SUMMARY["significance"]["loafo"]["zero_day_recall"]
_SIG_ROWS = sorted(_SEED, key=lambda m: -_SEED[m]["mean_diff"])
P.para(f"Table {TR['significance']} gives the paired tests over independent seeds. Aegis-OSR improved zero-day recall "
       f"over every baseline and every single-change ablation in all {N('LoafoSeeds')} seeds; against closed-set XGBoost "
       f"the difference was {N('DeltaXgb')} (95% CI {N('DeltaXgbLo')} to {N('DeltaXgbHi')}, p = {N('TpXgb')}) and against "
       f"the strongest ablation (omnibus fusion) {N('DeltaAblOmni')} (p = {N('TpAblOmni')}). Fold-level win counts are "
       "shown for completeness only, because the six folds of a seed are not independent observations.")
PT("significance")
P.subsection("Which Families Can Be Caught, and How They Are Labelled")
P.para(f"The average hides large differences between families (Fig. 3, Table {TR['family']}). DoS, DDoS, and web "
       f"attacks are caught almost completely when withheld ({F['fam_flood_web_range']}). Brute force shows the clearest "
       f"benefit of fusion: the classifier alone caught {F['fam_BruteForce_xgb']} and the autoencoder variant "
       f"{F['fam_BruteForce_ae']}, but Aegis-OSR caught {F['fam_BruteForce']}. A plausible explanation, which we did not "
       "test directly, is that individual password attempts look like ordinary short TCP sessions to a classifier "
       "trained on other attacks yet sit in a sparse part of the benign neighbourhood, which the k-NN term picks up. "
       f"PortScan is only partly caught ({F['fam_PortScan']}), and the botnet is effectively missed ({F['fam_Bot']}).")
P.figure(FIG / "fig3_loafo_by_family.png",
         "Zero-day recall at α = 1% for each withheld family (mean and 95% CI over five seeds).", 0.92)
PT("family")
P.para(f"The attribution columns of Table {TR['family']} show the second half of the design at work. When Aegis-OSR "
       "raised an alert on a withheld family, it almost never claimed the flow belonged to a family it knew: at most "
       f"{F['mis_max']} of unknown flows were misattributed (in the {F['mis_max_fold']} fold), and in {F['mis_small_folds']} "
       "folds the figure was 0.2% or less. At the same time, attacks from known families were labelled correctly in at "
       f"least {F['known_acc_min']} of cases in every fold. In practice, an alert reaches the analyst with an honest "
       "label: *this is a DDoS*, or *this is malicious but unlike anything I was trained on*. Missed unknowns were "
       "missed by being called benign, not by being forced into the wrong family.")
P.para(f"Fig. 4 shows how the operating point moves with α. At α = 0.1% Aegis-OSR caught {F['osr_zdr_a001']} of "
       f"unknown flows (realised FPR {F['osr_fpr_a001']}), against {F['xgb_zdr_a001']} for closed-set XGBoost; at α = 5% "
       f"it caught {F['osr_zdr_a05']} (FPR {F['osr_fpr_a05']}) against {F['xgb_zdr_a05']}. The advantage is largest in "
       "relative terms at the strictest budgets, which are the ones a busy SOC is most likely to choose.")
P.figure(FIG / "fig4_operating_curve.png",
         "Zero-day recall against the nominal benign false-alarm budget α (LOAFO, mean over five seeds). Realised "
         "false-positive rates matched α at every point.", 0.62)
P.subsection("Temporal Shift")  # ##RESULTS_V2##
P.para(f"Table {TR['temporal']} reports the temporal split, where calibration and test benign traffic come from "
       "different days. Here the guarantee visibly breaks. Training on Monday–Thursday and testing on Friday, "
       f"Aegis-OSR realised a benign false-positive rate of {F['t_fri_osr_fpr']} against a nominal 1%, and the k-NN "
       f"distance alone {F['t_fri_knn_fpr']}; closed-set XGBoost stayed closer to budget ({F['t_fri_xgb_fpr']}). The benign "
       "*neighbourhood* moves from day to day much more than the classifier's benign posterior does, so the channel "
       "that gives Aegis-OSR its zero-day recall also makes it the more sensitive to benign drift. On Thursday the "
       f"k-NN distance alone drifted even further ({F['t_thu_knn_fpr']}), while Aegis-OSR stayed at {F['t_thu_osr_fpr']}, "
       "because the classifier's evidence kept the fused score of most benign flows low.")
PT("temporal")
P.para("Per family, the temporal results repeat the LOAFO picture. On Friday, DDoS was caught "
       f"({F['t_fam_DDoS']}) while PortScan ({F['t_fam_PortScan']}) and Bot ({F['t_fam_Bot']}) were not; Friday's overall "
       f"recall of {F['t_fri_osr_zdr']} reflects mostly the DDoS share of the unknown flows. On Thursday, web attacks were "
       f"caught ({F['t_fam_WebAttack']}) and so were {F['t_fam_Infiltration']} of the Infiltration flows, against "
       f"{F['t_fam_Infiltration_xgb']} for closed-set XGBoost. With an inflated false-positive rate, however, the recall "
       f"figures in Table {TR['temporal']} cannot be compared across methods; re-calibration is needed first.")
P.subsection("Label-Light Re-Calibration")
P.para(f"Table {TR['adapt']} and Fig. 5 show what re-calibration buys, averaged over five seeds. On Friday, "
       "re-calibrating on the first 2,000 benign flows of the day reduced Aegis-OSR's false-positive rate from "
       f"{F['t_fri_osr_fpr']} to {F['a_fri_recal_2000_osr_fpr']}, and to {F['a_fri_recal_500_osr_fpr']} with 500 flows, at the "
       f"cost of recall ({F['t_fri_osr_zdr']} → {F['a_fri_recal_2000_osr_zdr']} and {F['a_fri_recal_500_osr_zdr']}); part of the "
       "unadapted recall had come from the inflated alarm rate. Re-calibrating on a *random* sample of 2,000 benign "
       f"flows from the whole day (the oracle) gave {F['a_fri_oracle_2000_osr_fpr']} {F['a_fri_oracle_fpr_ci']}—the behaviour "
       "Proposition 1 predicts once calibration and test traffic are exchangeable again. Larger arrival-order windows "
       f"did worse, not better: with 5,000 flows the rate rose to {F['a_fri_recal_5000_osr_fpr']} "
       f"(recal+ref: {F['a_fri_recalref_5000_osr_fpr']}), which indicates that the first minutes of a day are not "
       "exchangeable with the rest of it. A deployment should therefore re-calibrate on a sample spread over time rather "
       "than on the first N flows. Once every method is re-calibrated, the open-set advantage on Friday shrinks to a few "
       f"points ({F['a_fri_recal_2000_osr_zdr']} against {F['a_fri_recal_2000_xgb_zdr']} for closed-set XGBoost at W = 2,000) "
       f"and is not present under the oracle ({F['a_fri_oracle_2000_osr_zdr']} against {F['a_fri_oracle_2000_xgb_zdr']}). Under "
       "temporal shift, in other words, most of the value of Aegis-OSR lies in the calibrated alarm rate rather than "
       "in extra recall.")
PT("adapt")
P.figure(FIG / "fig5_adaptation.png",
         "Label-light re-calibration of Aegis-OSR under temporal shift (mean over five seeds). Top: realised benign "
         "false-positive rate; bottom: zero-day recall. Dotted lines show the unadapted model; the star is the oracle "
         "that re-calibrates on a random benign sample of the target day.", 0.95)
P.subsection("Naturally Unseen Attacks and the Deployed Gate")
_H = _GATE["head_to_head"]
_HN = _H["n"]
_UN = sum(u["n"] for u in _GATE["natural_unknowns"])
_PF = _H["per_family_recall"]
P.para(f"CICIDS2017 contains two attack types that are too rare to train on: {F['n_Infiltration']} Infiltration flows "
       f"and {F['n_Heartbleed']} Heartbleed flows. Neither the frozen detector nor the deployed gate saw them. Table "
       f"{TR['gate']} compares the gate with the frozen detector on the *same* flows: those in both models' test splits "
       "and in neither model's training or validation data "
       f"({_HN['benign']:,} benign flows, {_HN['known_attacks']:,} known attacks, and the {_UN} never-seen flows). "
       "Restricting the comparison this way matters: an earlier version of this table scored the frozen detector on "
       f"the gate's test split, {F['legacy_overlap']} of which lay in the frozen detector's training or validation splits.")
PT("gate")
P.figure(FIG / "fig6_gate.png",
         "Operating points of the deployed gate. The realised benign false-positive rate (solid) tracks the nominal α "
         "(dotted) across two orders of magnitude.", 0.6)
P.para(f"The frozen detector flagged {F['unseen_frozen']} of the {F['unseen_total']} flows. At its deployed setting of "
       f"α = 1%, the gate flagged {F['unseen_gate']} of them, labelling each as an unknown attack rather than forcing it "
       f"into a known family. With only {F['unseen_total']} flows these rates carry wide intervals and we regard them as "
       f"illustrative. Table {TR['gate']} also exposes something the aggregate scores in Table {TR['v11']} hide: on flows it "
       f"never trained on, the frozen detector's binary stage caught only {N('HthWebAttackFrozen')} of web-attack flows "
       f"(n = {N('HthWebAttackN')}) and {N('HthBotFrozen')} of botnet flows (n = {N('HthBotN')}), while its overall "
       f"known-attack recall was {N('HthFrozenKnown')}; these two families are about 1% of the attacks, so an aggregate "
       "F1 near 0.99 is compatible with missing most of them. The samples are small, so we treat this as a reason to "
       "report per-family recall rather than as a definitive score for v1.1.")
P.subsection("Transfer to Another Network: CSE-CIC-IDS2018")
P.para(f"Table {TR['v11_2018']} scores the *unchanged* frozen detector on CSE-CIC-IDS2018. Its benign false-positive "
       f"rate stayed low ({F['x_frozen_fpr']}) and its precision high ({F['x_frozen_precision']}), but its recall collapsed "
       f"to {F['x_frozen_recall']} and its F1 from {F['v11_f1']} to {F['x_frozen_f1']}. (F1 depends on the benign-to-attack mix of "
       "the sample; the earlier sample, whose benign flows came from four days only, gave a lower F1 for the same "
       "detector.) The per-label rows show that the failure is not confined to unfamiliar labels: DoS-Hulk "
       f"({F['x_frozen_hulk']}) and SSH brute force ({F['x_frozen_ssh']}), tools that also appear in CICIDS2017, were barely "
       f"detected by the frozen detector at its fixed operating thresholds, while LOIC-HTTP ({F['x_frozen_loichttp']}) transferred partly and Slowloris ({F['x_frozen_slowloris']}) "
       "carried over. Per-label rates also depend on how the sample is drawn: the earlier sample, which kept each label's "
       "first flows in file order, showed LOIC-HTTP as undetected. This does not make those attacks undetectable. In an "
       "exploratory, post-hoc analysis of the per-day records, the closed-set XGBoost classifier trained on CICIDS2017 "
       "(not retrained on 2018 data) and re-calibrated on "
       "2,000 benign flows of the same day detected the 2018-02-14 brute-force attacks (recall "
       f"{F['rd_xgb_bf_known']} at {F['rd_xgb_bf_fpr']} false alarms) and the 2018-02-16 DoS attacks "
       f"({F['rd_xgb_dos_known']} at {F['rd_xgb_dos_fpr']}): on these two days the shift moved scores relative to the frozen "
       f"thresholds rather than removing the signal. It does not hold on every day: on {F['ra_xgb_low_days']} of the "
       f"{F['ra_known_days']} days with known-family attacks the re-calibrated classifier detected under 5% of them "
       f"(Table {TR['inversion']}). Differences between the flow extractors used for the two releases may "
       "contribute and are confounded with the change of network; this is a hypothesis we have not tested, and "
       "separating the two requires data produced by a single extractor.")
PT("v11_2018")
P.para(f"Table {TR['cross']} reports the open-set protocol across datasets, with Infiltration—never in training—as "
       "the unknown family. It is a negative result. Every method's ability to separate the unknown family from benign "
       f"traffic was poor (AUROC_u {F['x_auroc_range']}); the conformal guarantee failed badly (Aegis-OSR realised "
       f"{F['x_osr_fpr']} benign false positives at α = 1%); and the classifier's known families transferred poorly—the "
       f"gate attributed only {F['x_family_acc']} of known 2018 attacks to their correct family. Table {TR['cross_perday']} "
       "repeats the experiment with re-calibration on each capture day's own earliest benign flows. Averaged over "
       f"days and seeds, re-calibration on 2,000 flows brought the false-alarm rate to {F['pd_recal2000_fpr']} "
       f"({F['pd_days_within']} of {F['pd_days']} days within 1.5%; per-day range {F['pd_recal2000_fpr_range']}), but recall "
       f"fell to {F['pd_recal2000_known']} on known families and {F['pd_recal2000_zdr']} on the unseen family. Calibrating on "
       "the target day therefore controls false alarms where the day's early traffic resembles the rest of it, but it "
       "cannot restore separation that the fused score has lost. On "
       f"{F['pd_anomaly_day']} the flows labelled benign differ sharply from benign traffic on every other day (median "
       f"{F['pd_anomaly_bytes']} against {F['pd_other_bytes_median']} bytes/s) and every one of them alerted before "
       f"re-calibration, consistent with documented labelling problems in this release; we keep the day, and excluding it "
       f"changes the W = 2,000 average false-alarm rate to {F['pd_recal2000_fpr_excl']}. Two explanations remain compatible with the data: "
       "the CICIDS2017 benign neighbourhood and attack signatures do not describe a network measured with a different "
       "extractor, and CSE-CIC-IDS2018's Infiltration label is known to contain many flows that are indistinguishable "
       "from benign traffic [40].")
PT("cross")
PT("cross_perday")
P.para(f"Table {TR['inversion']} compares, for every 2018 day with known-family attacks, the classifier alone, max fusion "
       "and Fisher fusion (Aegis-OSR) after the same re-calibration. This is an exploratory, post-hoc re-analysis of the "
       "stored per-flow scores. Averaged over days, Fisher fusion detected fewer known-family attacks than the classifier "
       f"alone ({F['ra_pd_fisher_xgb_conf']}; hierarchical bootstrap over days and seeds {F['ra_pd_fisher_xgb_conf_ci']}; "
       f"{F['ra_pd_fisher_xgb_conf_seeds']} seeds favour fusion). The loss comes from the four days on which the classifier still "
       "separates attacks; on the other four every method detects under 5%. At an exactly matched 1% false-alarm rate "
       f"(an oracle threshold, used only to compare rankings) the difference is {F['ra_pd_fisher_xgb_matched']} "
       f"{F['ra_pd_fisher_xgb_matched_ci']}, while max fusion stays close to the classifier ({F['ra_pd_max_xgb_matched']} "
       f"{F['ra_pd_max_xgb_matched_ci']}). A sum of surprisals loses power when one stream carries no signal or an "
       "inverted one—the classical observation that no p-value combiner is most powerful against every alternative, "
       "with Fisher's sum favouring evidence spread across tests and the minimum-p rule evidence concentrated in one "
       "[41], [42]—and on several of these days the k-NN stream ranks attacks below benign flows. Şahin and Mert [43] "
       "report, for conformal alert triage across a cross-dataset shift, that after re-calibration on labelled target data "
       "degradation appears as reduced automation rather than silent errors; our finding that re-calibration restores "
       "the false-alarm budget but not detection is consistent with theirs and is not claimed as new. In-distribution the "
       f"same fusion helps (LOAFO, matched 1% false-alarm rate: {F['ra_loafo_xgb_matched']} over the classifier, "
       f"{F['ra_loafo_xgb_matched_ci']} over families and seeds), so the sign of the fusion effect depends on the setting. "
       "Day, attack family, extractor and label quality are confounded in this comparison.")
PT("inversion")
P.subsection("A Pre-Registered Multi-Model Campaign")
P.para("The results above use one evidence model (XGBoost) and seeds that also informed the design. To test whether they "
       "depend on that choice, we committed hypotheses, decision rules and frozen configurations before running a reduced "
       f"campaign: {F['r3_models']} tree-based evidence models (the v3 XGBoost configuration, a decision tree, a random forest, "
       "extra trees, and XGBoost and LightGBM with library defaults), five new seeds, and four protocols. The protocols are "
       "LOAFO, the day-ordered split, per-day 2018 re-calibration, and a cross-dataset LOAFO in which a family present in both "
       "datasets is removed from training and evaluated on the 2018 days that contain it. Each model is used alone and fused "
       "with the same k-NN stream, with identical calibration. Conformal p-values use randomised tie-breaking, which makes the "
       "false-alarm rate exact for tree models with tied scores. The primary metric is the detection rate at an exactly "
       "matched 1% false-alarm rate. The seed is the statistical unit (paired t-test, Holm correction across models), and a "
       "hypothesis counts as supported only if at least five of the six models meet its rule.")
P.para(f"Table {TR['r3']} gives the verdicts. The validity check passed: all {F['r3_a4_cells']} model-arm combinations realised "
       f"{F['r3_a4_min']}–{F['r3_a4_max']} false alarms at α = 1% under LOAFO. Fisher fusion improved zero-day detection for "
       f"{F['r3_a1_n']} evidence models ({F['r3_a1_min']} to {F['r3_a1_max']}), and the v3 XGBoost gain on the new seeds "
       f"({F['r3_a1_xgbref']} {F['r3_a1_xgbref_ci']}) matches the earlier estimate ({F['ra_loafo_xgb_matched']}). With a "
       f"decision tree as evidence the fused detector found {F['r3_a2_dt']} less than with XGBoost. On the 2018 data after "
       f"per-day re-calibration, Fisher fusion detected fewer known-family attacks than its own evidence model for "
       f"{F['r3_a5_n']} models ({F['r3_a5_min']} to {F['r3_a5_max']}), so the inversion is not specific to XGBoost. Max fusion "
       f"is not a safe fixed alternative: it was non-inferior to the evidence model alone (margin {F['r3_ni_margin']}) for {F['r3_a7_n']} "
       f"models. In the cross-dataset LOAFO the in-distribution gain did not transfer ({F['r3_a6_min']} to {F['r3_a6_max']}). "
       "Dropping any single family or day leaves these verdicts unchanged, except that the max-fusion verdict becomes "
       "inconclusive when one 2018 day is dropped.")
P.para("We also pre-registered a label-free reliability screen: the share of a day's first 500 benign flows that each "
       "stream, under its source calibration, already calls anomalous at α₀ = 5%. It did not predict the stream's AUROC "
       f"(Spearman ρ = {F['r3_rs1_rho']}, day-cluster 95% interval {F['r3_rs1_ci']}) or the fusion loss (ρ = {F['r3_rs2_rho']}, "
       f"{F['r3_rs2_ci']}). The k-NN screen saturates, flagging {F['r3_screen_min']}–{F['r3_screen_max']} of benign warm-up "
       "flows on every 2018 day, so it cannot rank days. By the pre-registered rule, no gated fusion method was built. In "
       "an exploratory analysis, refreshing the k-NN reference set with the warm-up flows largely removed the inversion; "
       "this needs its own confirmatory test.")
PT("r3")
P.subsection("Would a Different Classifier Solve It?")
P.para(f"Table {TR['families']} compares ten classifier families at the same 1% benign false-alarm budget. With "
       f"every family seen in training they are hard to tell apart: binary F1 ranged from {F['fam_iid_f1_range']}, and "
       f"{F['fam_above_098']} of the ten scored above 0.98. With one family withheld, the picture changes. Averaged over "
       f"the six folds, the best model ({F['fam_best_name']}) caught {F['fam_best_heldout']} of the withheld family; the "
       f"{F['fam_n_trees']} tree-based models averaged {F['fam_tree_mean']} and the {F['fam_n_nns']} neural networks "
       f"{F['fam_nn_mean']}. No model detected more than {F['fam_bot_max']} of the withheld botnet, and none caught more than "
       "a small share of withheld port scans. Deeper or differently shaped classifiers are therefore not a substitute "
       f"for open-set detection: under the same budget and a comparable protocol, Aegis-OSR's {F['osr_zdr']} "
       f"(Table {TR['loafo']}) is well above every closed-set classifier here. (The protocols differ in detail—this "
       "comparison uses one seed and a binary task—so we compare levels rather than exact values.)")
PT("families")

P.subsection("The Cyber Range: From Detection Scores to Outcomes")
P.para(f"Tables {TR['range_def']} and {TR['range_det']} and Fig. 7 summarise the {F['range_runs']} range runs. The replayed "
       "flows were never used to train or validate either detector, but they come from the same capture, so per-flow "
       "recall is high for every in-distribution scenario and incidents are raised within "
       f"{F['r_known_latency_max']} s of the attack starting at most. The range is therefore most informative about what "
       "happens *after* detection, and about the one scenario the detectors were not built for.")
P.para("**Zero-day scenario.** With the frozen detector as the incident source, the zero-day intrusion was "
       f"detected in {F['rz_frozen_detected']} of {F['range_seeds']} runs; its per-flow recall on that traffic was "
       f"{F['rz_frozen_recall']}. With the gate, an incident was raised in {F['rz_gate_detected']} runs after "
       f"{F['rz_gate_latency']} s on average {F['rz_gate_latency_ci']}, with a per-flow recall of {F['rz_gate_recall']}. These "
       f"runs redraw the same {F['unseen_total']} never-seen flows, so they are not independent zero-days. On beacon traffic "
       f"the gate also shortened detection ({F['rb_gate_latency']} s against {F['rb_frozen_latency']} s) and raised per-flow "
       f"recall from {F['rb_frozen_recall']} to {F['rb_gate_recall']}.")
P.para("**Alert aggregation is the operational partner of calibration.** The gate's per-flow false-positive rate "
       f"in the range was about {F['r_gate_fpr']}, about {F['r_fpr_ratio']} times the frozen detector's {F['r_frozen_fpr']}, yet at the "
       "default k = 3 alerts in 5 s false incidents were essentially absent "
       f"(at most {F['r_fi_k3plus_max']} per run for k ≥ 3). At k = 1, every scenario produced {F['r_fi_k1']} false incidents "
       f"per run (normal users flagged as attackers); at k = 2, {F['r_fi_k2']} on average. The price is latency: from k = 1 "
       f"to k = {F['r_kmax']} the time to detect a slow beacon grew from {F['r_lat_beacon_k1']} s to {F['r_lat_beacon_kmax']} s "
       f"and a slow host discovery from {F['r_lat_hostdisc_k1']} s to {F['r_lat_hostdisc_kmax']} s, while a DoS flood stayed "
       f"at {F['r_lat_dos_kmax']} s. Conformal calibration fixes the per-flow rate; per-source aggregation turns that rate "
       "into an acceptable number of incidents.")
PT("range_def")
P.figure(FIG / "fig7_range_tradeoff.png",
         "Defense trade-off in the cyber range: each point is one scenario (mean of ten seeds). Blocking and rate "
         "limiting keep the service available without touching legitimate users; isolating the target also stops the "
         "attack but cuts off about a quarter of legitimate traffic.", 0.7)
P.para("**Choosing the defense matters more than detecting faster.** Blocking the detected source stopped every "
       f"attack with no collateral; rate limiting left about {F['r_rl_success']} of attack traffic through, as designed, "
       f"but kept the service available; isolating the target stopped the attack too, but blocked {F['r_iso_collateral']} "
       f"of legitimate flows and needed about {F['r_iso_recovery']} s to recover. That recovery time is a property of the "
       "range's rule (isolation is lifted 5 s after the attacker falls quiet), so it mostly reflects scenario length "
       "rather than a measured recovery behaviour. In a DDoS, *block source* acts per detected source, so each new "
       "source leaks a little traffic until it, too, is detected: with eight sources, availability dipped to "
       f"{F['r_ddos_8src_min_avail']} before the block took hold, against {F['r_ddos_2src_min_avail']} with two.")
P.para("**The analyst's decision time is the dominant cost for floods.** With the response applied immediately, "
       f"availability during a DDoS averaged {F['r_avail_ddos_0']}; with a 3 s approval it was {F['r_avail_ddos_3']}, with "
       f"10 s {F['r_avail_ddos_10']}, and with 30 s {F['r_avail_ddos_30']}. In the DoS scenario the attacker was usually "
       "caught during its reconnaissance stage and blocked before the flood began, so availability stayed at "
       f"{F['r_avail_dos_0']}–{F['r_avail_dos_10']} for delays up to 10 s and fell to {F['r_avail_dos_30']} only at 30 s—an "
       "argument for responding to reconnaissance, not only to impact. Availability is modelled from capacity and load, "
       "so these values show direction and scale, not service measurements.")
PT("range_det")
P.subsection("Do the Explanations Hold Up?")
_XF = _XAI["per_family"]
_rob = {f: v["robustness_jaccard_top5"]["mean"] for f, v in _XF.items()}
_weak = sorted((f for f in _rob if _rob[f] < 0.9), key=_rob.get)
_strong = sorted(f for f in _rob if _rob[f] >= 0.9)
P.para(f"Table {TR['xai']} reports the explanation-stability study on replay flows that neither model trained on. SHAP "
       "attributions were robust to ±1% feature noise (top-five overlap ≥ 0.90) for "
       + ", ".join(_strong) + ", but not for " + ", ".join(f"{f} ({_rob[f]:.2f})" for f in _weak)
       + f". Bot and WebAttack are also the families on which the frozen detector is weakest (Table {TR['gate']}), which is "
       "consistent with, but does not establish, a link between unstable explanations and a fragile decision "
       f"boundary. SHAP and LIME agreed poorly overall ({N('XaiShapLime')} top-five overlap). The LIME runs were not "
       "seeded and used discretized features, which may account for part of the disagreement. Different explainers "
       "can point at different features for the same decision, so explanations are presented as decision support, "
       "not as evidence of causation.")
PT("xai")
P.subsection("Mitigation on the Controlled Test Plane")
P.para(f"Before the range existed, the controlled test plane exercised the response chain directly (Table {TR['p11']}). "
       "These values are harness validation and hold by construction of the test adapter; they are not "
       "mitigation-effectiveness measurements. "
       "Without defence and with a proposed-but-unapproved recommendation, the target accepted every attack attempt; "
       "with an approved response, the source block denied all subsequent DDoS attempts and the rate limit "
       f"{F['p11_dos_eff']} of DoS attempts—close to what the controlled adapter is built to do. The experiment validates "
       "the chain detection → approval → enforcement → verification → rollback more than it estimates what a real "
       "firewall would achieve. The storyboard's assumed values are reported beside them and were not adjusted; the "
       "difference between the two is not meaningful.")
PT("p11")
P.subsection("Engineering Performance and Security Validation")
P.para(f"Table {TR['perf']} lists the measured operating envelope on the development machine. The vectorised models "
       f"score {F['perf_vec_range']} flows per second, yet the full pipeline handles about {F['perf_batch500']} flows per "
       "second in batches of 500: per-flow enrichment and persistence, not inference, are the bottleneck. A cyber-range "
       f"run of {F['r_flows_range']} flows completes in {F['r_wall_range']} s once the pool is scored. These are measured "
       "points on one machine, not capacity claims.")
PT("perf")
P.para(f"A final validation pass checked {F['p12_categories']} categories with automated tests: authentication and "
       "RBAC, response safety (no live mode, approval mandatory, rollback on failed verification, no automatic replay "
       "after recovery), API and input security (size limits, PCAP validation, path-traversal and filename "
       "sanitisation, rate limits, CORS allow-list, security headers), persistence and recovery, model-serving safety, "
       "simulation isolation, auditability of the mitigation experiments, audit-log integrity, documented production "
       f"boundaries, and integrity of the frozen baseline. The overall result was {F['p12_overall']}. This shows that "
       "the prototype enforces the boundaries it claims; it is not a penetration test.")

# =====================================================================================  X. DISCUSSION
P.section("Discussion")
P.subsection("What the Results Say Together")
P.para("Read together, the experiments separate three things that headline F1 scores blur. *Recognition*: on the "
       "capture they were trained on, every classifier we tried detects known families almost perfectly. *Novelty*: "
       "when a family is withheld, closed-set classifiers of every kind miss much of it, and combining a classifier "
       "with a benign-neighbourhood distance recovers a large part of the gap at the same alarm budget. *Transfer*: "
       "on a different network the frozen detector loses most of its recall on families it knows, and the open-set "
       "gate's alarm guarantee fails until it is re-calibrated—and even then the unseen family is not separable. The "
       "first property is what most published results measure; the second and third are what decide whether a "
       "detector is useful in a new place.")
P.subsection("Why Fusion Works, and When It Does Not")
P.para("The two evidence channels fail in different places. The classifier recognises attacks that share structure "
       "with a known family but has no reason to object to a flow that simply lies far from its training data. The "
       "k-NN distance objects to anything unusual but cannot tell an unusual attack from an unusual benign flow, "
       "which is why on its own it loses half of the known attacks at a 1% budget. Summing surprisals lets a flow "
       "that is somewhat suspicious to both channels cross the threshold even when neither alone would. The method "
       "fails where an attack is indistinguishable from benign traffic at the flow level: the CICIDS2017 botnet's "
       "small, regular HTTP exchanges and port scans' short, failed-connection-like flows. The same benign-"
       "neighbourhood channel that provides the extra recall is also the one that drifts most from day to day and "
       "from network to network.")
P.subsection("What the Guarantee Buys")
P.para("Conformal calibration does not make a detector better at ranking; it makes its alarm rate predictable, "
       "turns that rate into a setting a SOC can choose to fit its staffing, and makes comparisons fair. Its "
       "assumption is visible in our results: the realised rate matched the budget whenever calibration and test "
       "traffic were exchangeable—including after re-calibration on a random sample of a new day—and missed it by a "
       f"factor of about {F['t_fri_osr_fpr_ratio']} across days and {F['x_osr_fpr_ratio']} across datasets. A deployment should "
       "therefore monitor the realised alert rate on traffic believed to be benign and re-calibrate when it drifts, "
       "sampling the calibration flows across time. That procedure needs no labelled attacks. The range adds a second, "
       "complementary control: per-source aggregation converts a per-flow false-alarm rate into a number of incidents "
       "an analyst actually sees, and k = 3 was enough to make false incidents essentially vanish at a cost of a few "
       "seconds of latency.")
P.subsection("From Scores to Outcomes")
P.para("The range shows that once detection is fast, operational outcomes are decided by the response: which "
       "defense, how quickly it is approved, and how much collateral it causes. Isolation is the bluntest "
       f"instrument—effective, but with {F['r_iso_collateral']} of legitimate traffic lost in our model—while blocking or "
       "rate-limiting detected sources achieved the same containment with no collateral. A thirty-second approval delay "
       "cost more availability during a DDoS than any detector difference we measured. Responding to reconnaissance, "
       "when it is detected, prevented later stages altogether. These conclusions depend on the range's modelled "
       "capacities and costs, but their direction does not.")
P.subsection("Lessons from Building the Platform")
P.para("Four lessons seem worth passing on. Aggregate metrics conceal weak families: an F1 of "
       f"{F['v11_f1']} coexisted with detecting fewer than half of the web attacks on flows the model never trained on, "
       f"and with an F1 of {F['x_frozen_f1']} on a different network. Our own early temporal evaluation was leaky, and a "
       "later replay set for the live demonstrations overlapped the frozen model's training split; we found both only "
       "because we re-derived every split, so evaluation code deserves the same review as model code. The choice of the "
       "Decision Tree for production, made on a weighted score that favoured recall, gave a model with "
       f"{F['dt_xgb_fpr_ratio']} times the false-positive rate of XGBoost and far poorer behaviour on unseen families; "
       "with conformal calibration, a model can be chosen for its ranking quality and its operating point set "
       "separately. Finally, a simulator that only animates assumed numbers invites them to be quoted as results; "
       "replacing it with a range that measures—however simple its traffic model—changed what we could honestly claim.")

# =====================================================================================  XI. THREATS
P.section("Threats to Validity")
P.numbered([
    "*Benchmarks.* All training data come from CICIDS2017, a testbed capture with known labelling and flow-"
    "construction problems [12], [13]; CSE-CIC-IDS2018 has similar issues, notably in its Infiltration label [40]. We "
    "used the public exports for comparability; re-extracted or re-labelled flows might change individual numbers.",
    "*Simulated zero-days.* LOAFO withholds families that are still present in the same capture, network and tooling. "
    "The cross-dataset results show how much harder a genuinely new environment is, and the 47 natural unknowns are "
    "too few for statistical conclusions.",
    "*Exchangeability.* Proposition 1 holds only if calibration and test benign traffic are exchangeable; our temporal "
    "and cross-dataset results show this is not automatic.",
    "*The range is a model.* Arrival rates, per-family service costs, the rate-limit pass-through and the target "
    f"capacity are chosen parameters; flows are resampled from a finite pool of {F['pool_rows']} flows that neither "
    f"detector trained on (only {F['pool_n_Bot']} Bot and {F['pool_n_WebAttack']} web-attack flows qualify); and "
    "because those flows come from the detectors' own capture, detection latencies for known families are optimistic. The range "
    "measures what the detectors and controls do within this model, not on a real network.",
    "*Sampling caps and seeds.* Training, validation and test sets were capped per family. The model-family comparison "
    "used one seed. Results on uncapped data could differ, particularly for the largest families.",
    "*Design selection.* The fusion rule and novelty detector were chosen on a pilot seed excluded from reporting; "
    "hyper-parameters such as k = 5 were not tuned further.",
    "*Pre-registered campaign scope.* The multi-model campaign covers tree-based evidence models with library defaults "
    "and five seeds (the smallest exact Wilcoxon p is then 0.0625); neural evidence models and GPU-bound open-set "
    "baselines were not run.",
    "*Controlled plane.* The mitigation experiment runs in process on synthetic connection attempts, with an adapter "
    "whose behaviour partly determines the result; it says nothing about a real firewall or endpoint agent.",
])

# =====================================================================================  XII. CONCLUSION
P.section("Conclusion and Future Work")
P.para("We set out to give a flow-based intrusion detector a way to say \"this is an attack I do not recognise\" "
       "while keeping its false alarms at a level chosen in advance, and to measure what that changes operationally. "
       "Aegis-OSR adds a classifier's attack evidence to a benign-neighbourhood distance and calibrates the sum "
       f"conformally. On CICIDS2017 it detected {F['osr_zdr']} of flows from withheld families at a realised {F['osr_fpr']} "
       f"false-alarm rate, against {F['xgb_zdr']} for the same classifier alone, labelled those alerts as unknown rather "
       f"than forcing them into a known family, and flagged {F['unseen_gate']} of {F['unseen_total']} naturally unseen "
       "attacks that the frozen detector missed. The guarantee held when its assumption held and failed when traffic "
       "changed: across days, re-calibration on a few thousand benign flows brought it near the budget for some window "
       "sizes but not others, without retraining; across networks, neither the frozen detector "
       f"(F1 {F['v11_f1']} → {F['x_frozen_f1']}) nor the gate transferred, and per-day re-calibration controlled false "
       "alarms at the cost of most of the recall; after that re-calibration the fixed Fisher fusion detected fewer "
       "known attacks than its own classifier, so a fusion rule that helps in-distribution should not be kept fixed under "
       "shift. A pre-registered campaign over six tree-based evidence models showed that both the in-distribution gain and the "
       "cross-network loss hold across models, and that a simple benign-only screen does not predict when fusion hurts. "
       "In the trace-driven cyber range, the gate turned a zero-day scenario "
       f"that the frozen detector did not detect into one detected in about {F['rz_gate_latency']} seconds, alert aggregation removed false "
       "incidents, and the choice and timing of the human-approved response—not detection speed—decided the modelled "
       "service outcome.")
P.para("The most pressing next steps follow from the failures: building the benign reference and calibration from "
       "the target network itself, with analyst confirmation, and testing whether that rescues cross-network "
       "detection; monitoring the realised alert rate online and re-calibrating automatically on time-spread samples; "
       "aggregating flows per host over time so that low-and-slow threats such as botnets become visible; repeating "
       "the study on UNSW-NB15, NSL-KDD, TON_IoT and re-labelled CICIDS data; replacing the replayed traffic with a "
       "packet-level range in an isolated Linux network; and a study with analysts to test whether explanations and "
       "ATT&CK context actually improve triage.")

# =====================================================================================  BACK MATTER
P.section("Data and Code Availability")
P.para("CICIDS2017 is available from the Canadian Institute for Cybersecurity [4]. Source code, configuration, "
       "frozen model hashes, per-run result records, and the scripts that regenerate every table and figure in this "
       "paper are available at https://github.com/Dolendra/Intelligent-Machine-Learning-Based-Intrusion-Detection-"
       f"and-Attack-Defense-Simulation-System. Every experiment record lists the commit it was produced at; this "
       f"manuscript was generated from commit {_GIT_COMMIT}, and every number in it is read from those records at "
       "build time.", indent=False)
P.section("Author Contributions")
P.para("N. Dolendra Sai Teja: data pipeline, model training and evaluation, open-set method and experiments, "
       "repository and release management. E. Harshavardhan: explainability, risk scoring, recommendations, incident "
       "handling, and the response-safety design. C. Naveen: backend API, React console, simulation engine, and "
       "deployment. R. Rahul: supervision, research direction, and critical revision of the manuscript. All authors "
       "read and approved the final manuscript.", indent=False)
P.section("Declaration of Competing Interest")
P.para("The authors declare no competing financial interests or personal relationships that could have influenced "
       "this work.", indent=False)
P.section("Acknowledgment")
P.para("The authors thank the Department of Computer Science and Engineering, RGUKT Basar, for computing "
       "facilities and support, and the Canadian Institute for Cybersecurity for making CICIDS2017 publicly "
       "available.", indent=False)

# =====================================================================================  REFERENCES
P.section("References")
REFS = [
    "S. Axelsson, \"The base-rate fallacy and the difficulty of intrusion detection,\" *ACM Trans. Inf. Syst. Secur.*, vol. 3, no. 3, pp. 186–205, 2000.",
    "W. U. Hassan, S. Guo, D. Li, Z. Chen, K. Jee, Z. Li, and A. Bates, \"NoDoze: Combatting threat alert fatigue with automated provenance triage,\" in *Proc. Netw. Distrib. Syst. Security Symp. (NDSS)*, 2019.",
    "B. A. Alahmadi, L. Axon, and I. Martinovic, \"99% false positives: A qualitative study of SOC analysts' perspectives on security alarms,\" in *Proc. 31st USENIX Security Symp.*, 2022.",
    "I. Sharafaldin, A. H. Lashkari, and A. A. Ghorbani, \"Toward generating a new intrusion detection dataset and intrusion traffic characterization,\" in *Proc. 4th Int. Conf. Inf. Syst. Security Privacy (ICISSP)*, 2018, pp. 108–116.",
    "R. Sommer and V. Paxson, \"Outside the closed world: On using machine learning for network intrusion detection,\" in *Proc. IEEE Symp. Security Privacy*, 2010, pp. 305–316.",
    "V. Vovk, A. Gammerman, and G. Shafer, *Algorithmic Learning in a Random World*. New York, NY, USA: Springer, 2005.",
    "S. Bates, E. Candès, L. Lei, Y. Romano, and M. Sesia, \"Testing for outliers with conformal p-values,\" *Ann. Statist.*, vol. 51, no. 1, pp. 149–178, 2023.",
    "A. L. Buczak and E. Guven, \"A survey of data mining and machine learning methods for cyber security intrusion detection,\" *IEEE Commun. Surveys Tuts.*, vol. 18, no. 2, pp. 1153–1176, 2016.",
    "H.-J. Liao, C.-H. R. Lin, Y.-C. Lin, and K.-Y. Tung, \"Intrusion detection system: A comprehensive review,\" *J. Netw. Comput. Appl.*, vol. 36, no. 1, pp. 16–24, 2013.",
    "N. Moustafa and J. Slay, \"UNSW-NB15: A comprehensive data set for network intrusion detection systems,\" in *Proc. Military Commun. Inf. Syst. Conf. (MilCIS)*, 2015, pp. 1–6.",
    "M. Ring, S. Wunderlich, D. Scheuring, D. Landes, and A. Hotho, \"A survey of network-based intrusion detection data sets,\" *Comput. Secur.*, vol. 86, pp. 147–167, 2019.",
    "G. Engelen, V. Rimmer, and W. Joosen, \"Troubleshooting an intrusion detection dataset: The CICIDS2017 case study,\" in *Proc. IEEE Security Privacy Workshops (SPW)*, 2021, pp. 7–12.",
    "M. Lanvin, P.-F. Gimenez, Y. Han, F. Majorczyk, L. Mé, and E. Totel, \"Errors in the CICIDS2017 dataset and the significant differences in detection performances it makes,\" in *Risks and Security of Internet and Systems (CRiSIS 2022)*, Lecture Notes in Computer Science. Cham, Switzerland: Springer, 2023.",
    "D. Arp *et al.*, \"Dos and don'ts of machine learning in computer security,\" in *Proc. 31st USENIX Security Symp.*, 2022, pp. 3971–3988.",
    "G. Apruzzese, P. Laskov, and J. Schneider, \"SoK: Pragmatic assessment of machine learning for network intrusion detection,\" in *Proc. IEEE Eur. Symp. Security Privacy (EuroS&P)*, 2023.",
    "W. J. Scheirer, A. de Rezende Rocha, A. Sapkota, and T. E. Boult, \"Toward open set recognition,\" *IEEE Trans. Pattern Anal. Mach. Intell.*, vol. 35, no. 7, pp. 1757–1772, 2013.",
    "A. Bendale and T. E. Boult, \"Towards open set deep networks,\" in *Proc. IEEE Conf. Comput. Vis. Pattern Recognit. (CVPR)*, 2016, pp. 1563–1572.",
    "D. Hendrycks and K. Gimpel, \"A baseline for detecting misclassified and out-of-distribution examples in neural networks,\" in *Proc. Int. Conf. Learn. Represent. (ICLR)*, 2017.",
    "K. Lee, K. Lee, H. Lee, and J. Shin, \"A simple unified framework for detecting out-of-distribution samples and adversarial attacks,\" in *Adv. Neural Inf. Process. Syst. (NeurIPS)*, 2018.",
    "W. Liu, X. Wang, J. Owens, and Y. Li, \"Energy-based out-of-distribution detection,\" in *Adv. Neural Inf. Process. Syst. (NeurIPS)*, vol. 33, 2020, pp. 21464–21475.",
    "Y. Sun, Y. Ming, X. Zhu, and Y. Li, \"Out-of-distribution detection with deep nearest neighbors,\" in *Proc. 39th Int. Conf. Mach. Learn. (ICML)*, 2022, pp. 20827–20840.",
    "G. Pang, C. Shen, L. Cao, and A. van den Hengel, \"Deep learning for anomaly detection: A review,\" *ACM Comput. Surv.*, vol. 54, no. 2, pp. 1–38, 2021.",
    "F. T. Liu, K. M. Ting, and Z.-H. Zhou, \"Isolation forest,\" in *Proc. 8th IEEE Int. Conf. Data Mining (ICDM)*, 2008, pp. 413–422.",
    "Y. Mirsky, T. Doitshman, Y. Elovici, and A. Shabtai, \"Kitsune: An ensemble of autoencoders for online network intrusion detection,\" in *Proc. Netw. Distrib. Syst. Security Symp. (NDSS)*, 2018.",
    "A. N. Angelopoulos and S. Bates, \"Conformal prediction: A gentle introduction,\" *Found. Trends Mach. Learn.*, vol. 16, no. 4, pp. 494–591, 2023.",
    "R. Jordaney *et al.*, \"Transcend: Detecting concept drift in malware classification models,\" in *Proc. 26th USENIX Security Symp.*, 2017, pp. 625–642.",
    "F. Barbero, F. Pendlebury, F. Pierazzi, and L. Cavallaro, \"Transcending TRANSCEND: Revisiting malware classification in the presence of concept drift,\" in *Proc. IEEE Symp. Security Privacy*, 2022, pp. 805–823.",
    "F. Pendlebury, F. Pierazzi, R. Jordaney, J. Kinder, and L. Cavallaro, \"TESSERACT: Eliminating experimental bias in malware classification across space and time,\" in *Proc. 28th USENIX Security Symp.*, 2019, pp. 729–746.",
    "J. Gama, I. Žliobaitė, A. Bifet, M. Pechenizkiy, and A. Bouchachia, \"A survey on concept drift adaptation,\" *ACM Comput. Surv.*, vol. 46, no. 4, pp. 1–37, 2014.",
    "J. Lu, A. Liu, F. Dong, F. Gu, J. Gama, and G. Zhang, \"Learning under concept drift: A review,\" *IEEE Trans. Knowl. Data Eng.*, vol. 31, no. 12, pp. 2346–2363, 2019.",
    "S. M. Lundberg and S.-I. Lee, \"A unified approach to interpreting model predictions,\" in *Adv. Neural Inf. Process. Syst. (NeurIPS)*, 2017, pp. 4765–4774.",
    "S. M. Lundberg *et al.*, \"From local explanations to global understanding with explainable AI for trees,\" *Nature Mach. Intell.*, vol. 2, no. 1, pp. 56–67, 2020.",
    "M. T. Ribeiro, S. Singh, and C. Guestrin, \"'Why should I trust you?': Explaining the predictions of any classifier,\" in *Proc. 22nd ACM SIGKDD Int. Conf. Knowl. Discov. Data Mining*, 2016, pp. 1135–1144.",
    "L. Breiman, \"Random forests,\" *Mach. Learn.*, vol. 45, no. 1, pp. 5–32, 2001.",
    "T. Chen and C. Guestrin, \"XGBoost: A scalable tree boosting system,\" in *Proc. 22nd ACM SIGKDD Int. Conf. Knowl. Discov. Data Mining*, 2016, pp. 785–794.",
    "J. Pickands III, \"Statistical inference using extreme order statistics,\" *Ann. Statist.*, vol. 3, no. 1, pp. 119–131, 1975.",
    "A. A. Balkema and L. de Haan, \"Residual life time at great age,\" *Ann. Probab.*, vol. 2, no. 5, pp. 792–804, 1974.",
    "R. A. Fisher, *Statistical Methods for Research Workers*, 4th ed. Edinburgh, U.K.: Oliver and Boyd, 1932.",
    "F. Wilcoxon, \"Individual comparisons by ranking methods,\" *Biometrics Bull.*, vol. 1, no. 6, pp. 80–83, 1945.",
    "L. Liu, G. Engelen, T. Lynar, D. Essam, and W. Joosen, \"Error prevalence in NIDS datasets: A case study on CIC-IDS-2017 and CSE-CIC-IDS-2018,\" in *Proc. IEEE Conf. Commun. Netw. Security (CNS)*, 2022.",
    "A. Birnbaum, \"Combining independent tests of significance,\" *J. Amer. Statist. Assoc.*, vol. 49, no. 267, pp. 559–574, 1954.",
    "N. A. Heard and P. Rubin-Delanchy, \"Choosing between methods of combining p-values,\" *Biometrika*, vol. 105, no. 1, pp. 239–246, 2018.",
    "F. Şahin and N. S. Mert, \"Dual-threshold conformal deferral for trustworthy security alert triage,\" *Electronics*, vol. 15, no. 18, art. 4084, 2026.",
    "J. Wilkie, H. Hindy, C. Michie, C. Tachtatzis, J. Irvine, and R. Atkinson, \"A novel contrastive loss for zero-day network intrusion detection,\" *IEEE Trans. Netw. Service Manag.*, vol. 23, pp. 2064–2076, 2026, doi:10.1109/TNSM.2026.3652529.",
    "S. Barrett, L. Li, G. Dorai, and S. Rajaganapathy, \"FIRCE: A framework for intrusion response and conformal evaluation,\" in *Proc. Int. Conf. Smart Appl., Commun. Netw. (SmartNets)*, 2026, pp. 1–9, doi:10.1109/SmartNets69662.2026.11604738.",
    "S. V. Arepalli, U. S. G. Irrinki, A. Morampudi, and R. K. Surapani, \"Conformal prediction for network intrusion triage and analysis of unseen attack families,\" *Discover Informatics*, vol. 1, art. 33, 2026, doi:10.1007/s44564-026-00033-y.",
    "J. P. Mchina, N. Mduma, and R. S. Sinde, \"Adaptive decision-level intrusion detection for known and zero-day attacks,\" *Network*, vol. 6, no. 2, art. 23, 2026, doi:10.3390/network6020023.",
    "M. Haroush, T. Frostig, R. Heller, and D. Soudry, \"A statistical framework for efficient out of distribution detection in deep neural networks,\" in *Proc. Int. Conf. Learn. Represent. (ICLR)*, 2022.",
    "W. Ahmed, M. A. Rahaman, P. Roy, and P. Alam, \"The dashboard says 'perfect': A systematic audit of label-free model monitoring and test-time adaptation under temporal distribution shift in network intrusion detection,\" *Front. Artif. Intell.*, vol. 9, art. 1928858, 2026, doi:10.3389/frai.2026.1928858.",
]
for i, ref in enumerate(REFS, 1):
    p = d.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.left_indent = __import__("docx.shared", fromlist=["Cm"]).Cm(0.75)
    p.paragraph_format.first_line_indent = __import__("docx.shared", fromlist=["Cm"]).Cm(-0.75)
    p.paragraph_format.space_after = Pt(1.5)
    P._runs(p, f"[{i}]\t" + ref, 8.5)

_built = {k: v for k, v in P.labels.items() if k in TR}
assert _built == TR, f"table references out of sync with emitted tables: {_built} vs {TR}"
P.save(OUT)
print("saved", OUT, "tables", P.tab, "figures", P.fig, "equations", P.eq)
