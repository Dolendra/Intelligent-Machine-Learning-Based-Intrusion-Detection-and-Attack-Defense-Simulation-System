"""Builds the Aegis research paper (.docx). Every number is taken from the project's result files
(see the provenance notes in the companion checklist)."""
from pathlib import Path

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from docbuilder import Paper

HERE = Path(__file__).parent
FIG = HERE / "figs"
OUT = Path(r"D:\IDS-Project\docs\research\Aegis_Research_Paper.docx")

P = Paper()
d = P.doc

# =====================================================================================  TITLE
t = d.add_paragraph(); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
t.paragraph_format.space_after = Pt(10)
r = t.add_run("Aegis: Open-Set Network Intrusion Detection with Conformal False-Alarm Control, "
              "Explainable Triage, and Human-Gated Response")
r.font.size = Pt(17)

a = d.add_paragraph(); a.alignment = WD_ALIGN_PARAGRAPH.CENTER
a.paragraph_format.space_after = Pt(2)
r = a.add_run("Nelluri Dolendra Sai Teja, Edla Harshavardhan, Chittuluri Naveen, and R Rahul")
r.font.size = Pt(11)
af = d.add_paragraph(); af.alignment = WD_ALIGN_PARAGRAPH.CENTER
af.paragraph_format.space_after = Pt(14)
r = af.add_run("Department of Computer Science and Engineering, [Institution Name], [City], India\n"
               "[corresponding-author e-mail]")
r.font.size = Pt(9.5); r.italic = True

# =====================================================================================  ABSTRACT
P.para("**Abstract—**Machine-learning intrusion detectors trained on public flow benchmarks routinely report "
       "F1 scores above 0.99, yet almost all of them make a closed-world assumption: a flow is either benign or "
       "one of the attack families seen during training. A family that was never seen has nowhere to go, and "
       "it is usually waved through as benign. We describe Aegis, an intrusion detection platform that runs a "
       "conventional two-stage detector alongside an open-set gate, Aegis-OSR, whose benign false-alarm rate is "
       "chosen in advance by the operator. Aegis-OSR turns two complementary signals—the benign posterior of a "
       "gradient-boosted classifier and the distance from a flow to its nearest benign neighbours—into benign "
       "surprisals, adds them, and calibrates the sum with split-conformal prediction, so that the probability "
       "of alerting on an exchangeable benign flow is at most α. Each alert is then either attributed to a known "
       "family or marked as unknown by a class-conditional (Mondrian) conformal test. On CICIDS2017, under a "
       "leave-one-attack-family-out protocol (six families, five seeds), Aegis-OSR detected 70.6% "
       "(95% CI 68.9–72.3%) of flows from the withheld family at a realized benign false-positive rate of 1.00%, "
       "compared with 49.0% for a closed-set XGBoost classifier passed through the same calibration "
       "(30 of 30 paired wins; Wilcoxon p = 1.9×10^{−9}). The gain is largest for brute-force attacks "
       "(92.3% vs. 31.0%), while botnet traffic remains almost invisible as a novelty (2.3%). Across capture days "
       "the exchangeability assumption fails and the false-alarm rate on Friday rises to 7.7%; re-calibrating on "
       "500–2,000 benign flows from the new day brings it back to 0.2–0.8% without retraining, at some cost in "
       "recall. The frozen production detector (binary F1 0.990, multiclass macro-F1 0.998 on a stratified split) "
       "flags none of the 47 naturally occurring unseen attacks in the corpus; the gate running beside it flags 29. "
       "Around the detectors, Aegis adds SHAP and LIME explanations, a transparent risk score, and an approval-gated "
       "response workflow whose effect is measured on a controlled test plane rather than assumed.",
       indent=False, size=9.5)
P.para("**Index Terms—**Network intrusion detection, open-set recognition, zero-day attacks, conformal "
       "prediction, false-alarm control, concept drift, explainable AI, CICIDS2017, security operations.",
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
       "notion of an unknown attack; on the 47 Heartbleed and Infiltration flows that it never saw in training, it "
       "raised no alert at all. Second, our early \"temporal\" evaluation turned out to score the model on rows it "
       "had already been trained on, which inflated the result. Both problems pushed us towards the question this "
       "paper is mainly about: *can a flow-based detector raise alerts on unseen attack families while keeping "
       "its benign false-alarm rate at a level the operator chooses in advance?*")
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
    "**A controlled comparison** against ten alternatives—closed-set XGBoost and Decision Tree classifiers, an "
    "energy-based out-of-distribution score, k-NN distance, an autoencoder, Isolation Forest, and four ablations "
    "that each change one design choice. Every method goes through the same conformal calibration, so "
    "differences come from the evidence and the fusion rule, not from threshold tuning (Sections VIII–IX).",
    "**An evaluation that separates its claims**: leave-one-attack-family-out (LOAFO) over six families and five "
    "seeds with paired significance tests; a temporal split by capture day that deliberately violates "
    "exchangeability; label-light re-calibration under that shift; and the 47 naturally occurring unseen "
    "attacks in CICIDS2017.",
    "**An integrated, human-gated platform** in which the open-set gate runs beside a frozen production "
    "detector without altering its decisions, and is surrounded by explanations, a transparent risk score, "
    "incident correlation, and an approval-based response workflow whose mitigation effect we measure on a "
    "controlled test plane and report next to—not in place of—the simulation's assumed values (Sections III, VII).",
    "**A reproducible artefact**: frozen model hashes, fixed seeds, per-run JSON records, and scripts that "
    "regenerate every table in this paper.",
])
P.para("The rest of the paper is organised as follows. Section II reviews related work. Section III describes the "
       "platform, Section IV the data, and Section V the closed-set detector. Section VI presents Aegis-OSR. "
       "Section VII covers explanation, risk, and response. Section VIII sets out the experimental protocol and "
       "Section IX the results. Section X discusses what the results mean, Section XI lists threats to validity, "
       "and Section XII concludes.")

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
         "response workflow consume both. Solid arrows carry data; dashed arrows lead to the isolated simulation and "
         "the controlled lab plane.", 1.0)
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
       "refused. A React console exposes a dashboard, a live traffic monitor that replays held-out flows through "
       "both detectors, a zero-day laboratory for exploring the α trade-off, a research view of all experimental "
       "results, the response queue, and system health.")
P.para("Throughout the project we kept three kinds of numbers apart, and we keep them apart here: **research "
       "measurements** on CICIDS2017 splits (Sections V and IX-A to IX-D); **simulation assumptions**, which are "
       "configuration values used to animate the attack–defence lifecycle; and **controlled-lab measurements** "
       "from the isolated test plane (Section IX-F). Conflating them is a common way for project reports to "
       "overstate what they have shown.")

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
       "dropped. This leaves 2,520,798 unique flows described by 77 numeric features (Table I). The removal of "
       "duplicates matters more than it appears: CICIDS2017 contains many repeated flows, and a random split that "
       "keeps them can place identical rows in training and test.")
P.table("Composition of the Cleaned CICIDS2017 Corpus",
        ["Family", "Flows", "Capture day(s)", "Role in this study"],
        [["BENIGN", "2,095,057", "Mon–Fri", "negative class; calibration"],
         ["DoS", "193,745", "Wed", "known / held out in LOAFO"],
         ["DDoS", "128,014", "Fri", "known / held out in LOAFO"],
         ["PortScan", "90,694", "Fri", "known / held out in LOAFO"],
         ["BruteForce", "9,150", "Tue", "known / held out in LOAFO"],
         ["WebAttack", "2,143", "Thu", "known / held out in LOAFO"],
         ["Bot", "1,948", "Fri", "known / held out in LOAFO"],
         ["Infiltration", "36", "Thu", "natural unknown (never trained on)"],
         ["Heartbleed", "11", "Wed", "natural unknown (never trained on)"],
         ["Total", "2,520,798", "", "77 features after cleaning"]],
        widths=[1.2, 1.0, 1.0, 2.2], label="data", bold_rows=(9,))
P.subsection("Two Preprocessing Pipelines")
P.para("The frozen closed-set detector and the research study use different preprocessing because they answer "
       "different questions.")
P.runin("Closed-set pipeline (v1.1)",
        "Families with fewer than 50 flows (Infiltration, Heartbleed) are removed, and the remaining 2,520,751 flows "
        "are split 70/10/20 into training, validation, and test sets, stratified by label, with random state 42 "
        "(1,764,525 / 252,075 / 504,151 rows). Features are standardised and reduced with SelectKBest (ANOVA F-test), "
        "fitted on the training split only. We fit two selectors—40 features for the binary stage and 40 for the "
        "multiclass stage—because the features that separate benign from malicious traffic are not the ones that "
        "separate one attack family from another; 27 features are shared.")
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
       "report the raw metrics so that a reader can apply different ones. Table II shows that XGBoost has the best "
       "F1 and the lowest false-positive rate, while the Decision Tree has the best recall and the best score. We "
       "selected the Decision Tree, accepting roughly four times the false-positive rate of XGBoost in exchange for "
       "about 0.7 percentage points of recall. In hindsight this choice deserves scrutiny, and we return to it in "
       "Section X.", indent=False)
P.table("Binary Candidates on the Validation Split (252,075 Flows)",
        ["Model", "Precision", "Recall", "F1", "FPR", "PR-AUC", "MCC", "Score S"],
        [["Logistic regression", "0.7206", "0.9706", "0.8272", "0.0765", "0.9405", "0.7991", "0.9239"],
         ["**Decision Tree (selected)**", "0.9845", "**0.9966**", "0.9905", "0.0032", "0.9972", "0.9886", "**0.9940**"],
         ["Random Forest", "0.9864", "0.9961", "0.9912", "0.0028", "0.9997", "0.9894", "0.9877"],
         ["XGBoost", "**0.9962**", "0.9899", "**0.9930**", "**0.0008**", "0.9997", "**0.9916**", "0.9918"]],
        widths=[2.0, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8], label="cand")
P.para("The operating threshold τ = 0.85 was chosen on 150,000 validation rows as the value that maximises F1 among "
       "thresholds with recall of at least 0.95. Scores between 0.10 and 0.95 are labelled as an uncertainty band in "
       "the console, so that an analyst can see when the model is close to its decision boundary. We also tested "
       "isotonic calibration of the tree's scores on a 60,000-row sample; it reduced recall (0.986 → 0.982) and "
       "worsened the Brier score (0.0028 → 0.0037), so calibration was left disabled.")
P.subsection("Multiclass Stage")
P.para("Flows that the binary stage calls malicious are passed to an attack-only multiclass model with six "
       "classes (Bot, BruteForce, DDoS, DoS, PortScan, WebAttack). Training it without a benign class means it never "
       "has to repeat the binary decision. Random Forest and XGBoost were compared using 0.7·macro-F1 + "
       "0.3·weighted-F1; the Random Forest scored 0.99877 on validation against 0.99806 for XGBoost and was "
       "selected.")
P.subsection("Test Results")
P.para("Table III gives the frozen detector's scores on the 504,151-row stratified test split. Of 85,139 attacks in "
       "the multiclass test set, 18 were assigned to the wrong family; the largest group was six PortScan flows "
       "labelled DoS. These are excellent numbers, and they are also the numbers that the rest of this paper "
       "warns against reading too much into: they come from a random split of a single capture, and every family "
       "in the test set was present in training.")
P.table("Frozen Closed-Set Detector (v1.1) on the Stratified Test Split",
        ["Stage", "Metric", "Value", "Metric", "Value"],
        [["Binary (DT, τ = 0.85)", "Precision", "0.98404", "F1", "**0.99048**"],
         ["", "Recall", "0.99700", "ROC-AUC", "0.99916"],
         ["", "FPR", "0.00329", "PR-AUC", "0.99744"],
         ["", "TP / FN", "84,884 / 255", "TN / FP", "417,635 / 1,377"],
         ["", "Brier", "0.00229", "ECE", "0.00242"],
         ["Multiclass (RF, attack-only)", "Accuracy", "0.99979", "Macro-F1", "**0.99813**"],
         ["", "Macro precision", "0.99762", "Macro recall", "0.99864"],
         ["", "Weighted F1", "0.99979", "Misattributed", "18 / 85,139"]],
        widths=[1.8, 1.1, 1.0, 1.1, 1.0], label="v11")

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
P.para("whose standard deviation is about √ℓ/(n + 1). With n = 30,000 and α = 0.01 this is 0.06 percentage points; "
       "with n = 1,000 it is 0.32. We use this to read the re-calibration results in Section IX-D. Second, the "
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
       "Mondrian calibrators. It was trained on 662,365 flows, calibrated on two benign splits of 40,000, and "
       "scores a flow in about 0.06 ms in batch mode on a 20-thread desktop processor. Its outputs agree with the "
       "research implementation on 99.996% of test flows; the small difference comes from the quantile "
       "sketches.")

# =====================================================================================  VII. TRIAGE & RESPONSE
P.section("Explanation, Risk, and Response")
P.subsection("Explanations")
P.para("For each prediction the analyst can request a local explanation. SHAP values are computed with the exact "
       "TreeExplainer [32] for the tree models, falling back to KernelExplainer over a stored background sample when "
       "a model is not tree-based; LIME [33] is offered as a second opinion. The console shows the top ten "
       "contributing features and a short narrative. A counterfactual helper moves the strongest positive drivers "
       "towards the background median and re-scores the flow, which answers the question \"what would have to change "
       "for this flow to be called benign?\". Globally, the binary tree relies most on the standard deviation of "
       "backward packet length (importance 0.40), average packet size (0.28), maximum packet length (0.10), "
       "destination port (0.08), and the initial backward TCP window (0.06). We present explanations as decision "
       "support, not as proof of how an attack works.")
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
       "(severity-heavy, balanced, operations-heavy): scores moved by at most 6.6 points and no case changed band.", indent=False)
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
P.subsection("Simulation and the Controlled Test Plane")
P.para("For teaching and demonstration, a simulator animates an attack on a small enterprise topology through the "
       "states idle, normal, attack start, impact, detected, recommended, defended, and recovered. The defence "
       "effectiveness it displays (for example 0.82 for DDoS and 0.78 for DoS) is a configuration value, and the "
       "interface says so. To obtain measured values we built a separate in-process test plane: a test client "
       "generates attacker and benign connection attempts against a target with finite capacity, Aegis detects the "
       "attack using the frozen models, and the approved action is applied through the controlled adapter. "
       "Mitigation effectiveness is")
P.equation(r"E=\frac{a_{\mathrm{pre}}-a_{\mathrm{post}}}{a_{\mathrm{pre}}},", "eq_E")
P.para("where a_pre and a_post are the accepted fractions of attack attempts before and after the response. Three "
       "conditions are compared under identical traffic: no defence, recommendation only (proposed and dry-run but "
       "not approved), and approved controlled response.", indent=False)

# =====================================================================================  VIII. PROTOCOL
P.section("Experimental Protocol")
P.subsection("Leave-One-Attack-Family-Out (LOAFO)")
P.para("For each of the six trainable families, we remove that family from training and validation and present "
       "it only at test time, as a simulated zero-day. The model is trained on benign flows and the other five "
       "families. The test set contains held-out benign flows, test flows of the five known families, up to 25,000 "
       "flows of the held-out family drawn from *all* of its rows (none of which the model has seen), and the 47 "
       "Infiltration and Heartbleed flows, which are unknown in every fold. Depending on the fold, the unknown group "
       "holds between 1,995 flows (Bot) and 25,047 (DDoS, DoS, PortScan); every fold has 150,000 benign test flows. "
       "We repeat this for seeds 1 to 5, with a fresh split per seed, giving 30 runs. Seed 0 was used to choose "
       "the design—Fisher fusion with k-NN novelty—and is excluded from every number reported here.")
P.subsection("Temporal Split")
P.para("To test what happens when exchangeability is violated, we train on earlier days and test on a later one: "
       "Monday–Wednesday → Thursday, where web attacks and Infiltration are unknown, and Monday–Thursday → Friday, "
       "where Bot, PortScan, and DDoS are unknown. Unlike LOAFO, the benign test traffic now comes from a different "
       "day than the calibration traffic. The earliest 5,000 benign flows of the target day, in arrival order, are "
       "set aside as the warm-up pool for adaptation and are never tested on. As an upper reference, an *oracle* "
       "re-calibrates on 2,000 benign flows sampled at random from the whole target day. This protocol replaced an "
       "earlier \"Friday holdout\" in our project that scored the frozen models on Friday rows, some of which had "
       "been in their training split; we report no results from that earlier evaluation. The temporal protocol was "
       "run with one seed.")
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
P.subsection("Metrics and Statistics")
P.para("The primary metric is *zero-day recall*: the fraction of unknown-group flows that raise an alert at "
       "α = 0.01. We also report the realised benign false-positive rate, the recall on known families, and the "
       "area under the ROC curve for separating unknown from benign flows (AUROC_u), which does not depend on a "
       "threshold. For attribution we report the share of unknown flows labelled UNKNOWN-ATTACK or "
       "ZERO-DAY-ANOMALY, the share wrongly attributed to a known family, and the accuracy of family labels on "
       "known attacks. Each LOAFO metric is averaged over the six folds within a seed, and we give the mean and a "
       "95% Student-t interval over the five seeds. Methods are compared with the two-sided Wilcoxon signed-rank "
       "test [39] over the 30 paired (fold, seed) runs. All experiments ran on a single Windows desktop "
       "(Intel, 20 threads) with Python 3.11.9, scikit-learn 1.9.0, XGBoost 3.2.0, and SHAP 0.51.0; a LOAFO run "
       "took 84 s to fit on average and scored about 68 ms per 1,000 flows with all eleven methods enabled.")

# =====================================================================================  IX. RESULTS
P.section("Results")
P.subsection("Detection of Withheld Families (LOAFO)")
P.para("Table IV summarises the 30 LOAFO runs. Every conformally calibrated method realised a benign "
       "false-positive rate between 0.97% and 1.01% against a nominal 1%, and the 95% interval for Aegis-OSR "
       "(0.92–1.07%) matches the spread that (9) predicts for |C₂| = 30,000. The calibration therefore behaves "
       "as the theory says it should when its assumption holds. The only method that did not realise ≈1% is the "
       "Decision Tree, whose scores take very few distinct values, so its conformal threshold cannot be placed "
       "exactly at α.")
P.table("Leave-One-Attack-Family-Out on CICIDS2017 at α = 1% (Mean and 95% CI over Five Seeds)",
        ["Method", "Group", "Zero-day recall", "AUROC_u", "Known recall", "Benign FPR (%)"],
        [["**Aegis-OSR**", "proposed", "**0.706** [0.689, 0.723]", "0.946 [0.943, 0.950]", "1.000 [0.999, 1.000]", "1.00 [0.92, 1.07]"],
         ["  w/ omnibus fusion", "ablation", "0.614 [0.587, 0.642]", "0.946 [0.941, 0.951]", "1.000", "0.99 [0.92, 1.06]"],
         ["  w/ AE novelty", "ablation", "0.562 [0.527, 0.597]", "**0.955** [0.952, 0.957]", "1.000", "0.97 [0.88, 1.05]"],
         ["  w/ max fusion", "ablation", "0.531 [0.500, 0.563]", "0.944 [0.939, 0.948]", "1.000", "0.99 [0.95, 1.04]"],
         ["  w/ IForest novelty", "ablation", "0.478 [0.438, 0.518]", "0.929 [0.924, 0.934]", "1.000", "0.99 [0.96, 1.02]"],
         ["Closed-set XGB", "baseline", "0.490 [0.447, 0.533]", "0.938 [0.932, 0.945]", "1.000", "1.00 [0.97, 1.02]"],
         ["XGB + Energy", "baseline", "0.457 [0.430, 0.484]", "0.947 [0.943, 0.952]", "1.000", "1.00 [0.95, 1.04]"],
         ["k-NN distance", "baseline", "0.379 [0.358, 0.401]", "0.866 [0.861, 0.871]", "0.546 [0.534, 0.559]", "1.01 [0.92, 1.11]"],
         ["Closed-set DT (v1.1-style)", "baseline", "0.241 [0.177, 0.305]", "0.606 [0.571, 0.640]", "0.999", "0.31 [0.21, 0.42]"],
         ["Autoencoder", "baseline", "0.231 [0.197, 0.265]", "0.883 [0.870, 0.897]", "0.430 [0.397, 0.463]", "1.00 [0.86, 1.13]"],
         ["Isolation Forest", "baseline", "0.012 [0.011, 0.012]", "0.840 [0.829, 0.851]", "0.008 [0.007, 0.008]", "0.99 [0.92, 1.06]"]],
        widths=[1.75, 0.7, 1.45, 1.4, 1.55, 1.25], label="loafo", size=7.5,
        notes="Known recall is shown without an interval where its interval rounds to [1.000, 1.000] or [0.999, 0.999]. "
              "AUROC_u: area under the ROC curve for unknown versus benign flows.")
P.para("Aegis-OSR detected 70.6% of withheld-family flows, 21.6 points more than the closed-set XGBoost classifier it "
       "is built on and 46.5 points more than the Decision Tree that approximates the production detector. It did so "
       "without losing anything on known families, whose recall stayed at 1.000. The unsupervised detectors are a "
       "different story. At a 1% budget, Isolation Forest caught 1.2% of unknown flows and 0.8% of known ones, and the "
       "autoencoder and k-NN distance each missed roughly half of the *known* attacks. On their own, these detectors "
       "would be unusable at this alarm budget; inside Aegis-OSR, the k-NN distance supplies exactly the signal the "
       "classifier lacks.")
P.para("The ablations isolate the two design choices. Holding the novelty detector fixed, Fisher fusion beat "
       "omnibus fusion by 9.2 points and max fusion by 17.5. Holding Fisher fusion fixed, k-NN novelty beat "
       "the autoencoder by 14.4 points and Isolation Forest by 22.8. One result runs the other way: the autoencoder "
       "variant has the highest AUROC_u (0.955 against 0.946). AUROC averages over all thresholds, including the "
       "high false-alarm regions no SOC would operate in; at the 1% operating point that we actually use, k-NN is "
       "clearly better. This is a concrete instance of the point made in [14] about choosing metrics that match the "
       "deployment.")
P.para("Table V gives the paired tests. Aegis-OSR beat closed-set XGBoost, the Decision Tree, the energy baseline, "
       "and the Isolation Forest ablation in all 30 pairs. For 30 pairs with no ties, a clean sweep gives the smallest "
       "attainable two-sided Wilcoxon p-value, 2/2^{30} ≈ 1.9×10^{−9}. Against the strongest ablation (omnibus fusion), "
       "Aegis-OSR won 24 pairs and lost 6, and the difference is still significant (p = 1.1×10^{−4}).")
P.table("Paired Two-Sided Wilcoxon Signed-Rank Tests on Zero-Day Recall (30 Fold × Seed Pairs)",
        ["Aegis-OSR vs.", "Mean Δ recall", "Wins / losses / ties", "p-value"],
        [["Closed-set XGB", "+0.216", "30 / 0 / 0", "1.86×10^{−9}"],
         ["Closed-set DT (v1.1-style)", "+0.465", "30 / 0 / 0", "1.86×10^{−9}"],
         ["XGB + Energy", "+0.249", "30 / 0 / 0", "1.73×10^{−6}"],
         ["Aegis-OSR w/ IForest novelty", "+0.228", "30 / 0 / 0", "1.73×10^{−6}"],
         ["Isolation Forest", "+0.694", "27 / 2 / 1", "3.69×10^{−6}"],
         ["Autoencoder", "+0.475", "27 / 3 / 0", "4.73×10^{−6}"],
         ["Aegis-OSR w/ max fusion", "+0.175", "24 / 6 / 0", "6.92×10^{−6}"],
         ["Aegis-OSR w/ AE novelty", "+0.144", "25 / 5 / 0", "6.92×10^{−6}"],
         ["k-NN distance", "+0.327", "25 / 5 / 0", "7.68×10^{−6}"],
         ["Aegis-OSR w/ omnibus fusion", "+0.092", "24 / 6 / 0", "1.11×10^{−4}"]],
        widths=[2.4, 1.2, 1.5, 1.2], label="wilcoxon")
P.subsection("Which Families Can Be Caught, and How They Are Labelled")
P.para("The average hides large differences between families (Fig. 3, Table VI). DoS, DDoS, and web attacks are "
       "caught almost completely when withheld (96.5–99.1%). Brute force shows the clearest benefit of fusion: the "
       "classifier alone caught 31.0% and the autoencoder variant 31.6%, but Aegis-OSR caught 92.3%. Individual "
       "password attempts look like ordinary short TCP sessions to a classifier trained on other attacks, yet they "
       "sit in a sparse part of the benign neighbourhood, and the k-NN term picks that up. PortScan is only partly "
       "caught (35.7%), and the botnet is effectively missed (2.3%).")
P.figure(FIG / "fig3_loafo_by_family.png",
         "Zero-day recall at α = 1% for each withheld family (mean and 95% CI over five seeds).", 0.92)
P.table("Per-Family Zero-Day Recall and Aegis-OSR Attribution (LOAFO, α = 1%, Mean over Five Seeds)",
        ["Held-out family", "Aegis-OSR", "Closed-set XGB", "w/ AE novelty", "DT (v1.1-style)",
         "Flagged unknown", "Mis-attributed", "Known-family acc."],
        [["WebAttack", "**0.991**", "0.946", "0.960", "0.688", "0.990", "0.001", "0.990"],
         ["DoS", "0.977", "0.824", "**0.987**", "0.246", "0.968", "0.009", "0.989"],
         ["DDoS", "**0.965**", "0.742", "0.920", "0.499", "0.963", "0.002", "0.989"],
         ["BruteForce", "**0.923**", "0.310", "0.316", "0.001", "0.923", "0.001", "0.990"],
         ["PortScan", "**0.357**", "0.112", "0.177", "0.011", "0.355", "0.002", "0.990"],
         ["Bot", "**0.023**", "0.004", "0.012", "0.000", "0.023", "0.000", "0.990"]],
        widths=[1.35, 0.95, 1.0, 1.0, 1.05, 1.0, 1.05, 1.1], label="family", size=7.5,
        notes="The last three columns refer to Aegis-OSR. *Flagged unknown*: share of the withheld family labelled "
              "UNKNOWN-ATTACK or ZERO-DAY-ANOMALY. *Misattributed*: share wrongly given a known-family label. "
              "*Known-family acc.*: accuracy of family labels on attacks from the five known families.")
P.para("The attribution columns of Table VI show the second half of the design at work. When Aegis-OSR raised an "
       "alert on a withheld family, it almost never claimed the flow belonged to a family it knew: at most 0.9% of "
       "unknown flows were misattributed (in the DoS fold), and in five of six folds the figure "
       "was 0.2% or less. At the same time, attacks from known families were labelled correctly about 99% of the "
       "time. In practice, an alert reaches the analyst with an honest label: *this is a DDoS*, or *this is "
       "malicious but unlike anything I was trained on*. Missed unknowns were missed by being called benign, not by "
       "being forced into the wrong family.")
P.para("Fig. 4 shows how the operating point moves with α. At α = 0.1% Aegis-OSR caught 28.2% of unknown flows "
       "(realised FPR 0.10%), against 11.2% for closed-set XGBoost; at α = 5% it caught 81.2% (FPR 5.00%) against 73.2%. "
       "The advantage is largest in relative terms at the strictest budgets, which are the ones a busy SOC is most "
       "likely to choose.")
P.figure(FIG / "fig4_operating_curve.png",
         "Zero-day recall against the nominal benign false-alarm budget α (LOAFO, mean over five seeds). Realised "
         "false-positive rates matched α at every point.", 0.62)
P.subsection("Temporal Shift")
P.para("Table VII reports the temporal split, where calibration and test benign traffic come from different days. "
       "Here the guarantee visibly breaks. Training on Monday–Thursday and testing on Friday, Aegis-OSR realised a "
       "benign false-positive rate of 7.68% against a nominal 1%, and the k-NN distance alone reached 8.94%. "
       "Closed-set XGBoost stayed close to budget (1.27%). The pattern is informative: the benign *neighbourhood* "
       "moves from day to day much more than the classifier's benign posterior does, so the same channel that "
       "gives Aegis-OSR its zero-day recall also makes it the more sensitive to benign drift. On Thursday the "
       "k-NN distance alone drifted even further (11.21%), yet Aegis-OSR stayed at 1.55%: there the classifier's "
       "evidence was confident enough to keep the fused score of most benign flows low.")
P.table("Temporal Split by Capture Day, No Adaptation (α = 1%, Seed 1)",
        ["Method", "Mon–Wed → Thu recall", "FPR (%)", "Mon–Thu → Fri recall", "FPR (%)"],
        [["Aegis-OSR", "0.992", "1.55", "0.492", "7.68"],
         ["Aegis-OSR w/ AE novelty", "0.979", "1.41", "0.484", "6.39"],
         ["Closed-set XGB", "0.983", "1.21", "0.479", "1.27"],
         ["k-NN distance", "0.055", "11.21", "0.422", "8.94"],
         ["Autoencoder", "0.014", "10.28", "0.289", "7.48"],
         ["Closed-set DT (v1.1-style)", "0.870", "0.06", "0.007", "0.04"]],
        widths=[2.0, 1.3, 0.8, 1.3, 1.3], label="temporal",
        notes="Unknown families: Thursday—WebAttack (Aegis-OSR recall 0.999), Infiltration (0.556); "
              "Friday—DDoS (0.989), PortScan (0.033), Bot (0.008). Recall values are not comparable across rows "
              "when the realised FPR differs from the budget.")
P.para("Per family, the temporal results repeat the LOAFO picture. On Friday, DDoS was caught (98.9%) while "
       "PortScan (3.3%) and Bot (0.8%) were not; Friday's overall recall of 49.2% is essentially the DDoS share of "
       "the unknown flows. On Thursday, web attacks were caught (99.9%) and so were 55.6% of the Infiltration "
       "flows, against none for closed-set XGBoost. With an inflated false-positive rate, however, the recall "
       "figures in Table VII cannot be compared across methods; adaptation is needed first.")
P.subsection("Label-Light Re-Calibration")
P.para("Table VIII and Fig. 5 show what re-calibration buys. On Friday, re-calibrating on the first 2,000 benign "
       "flows of the day reduced Aegis-OSR's false-positive rate from 7.68% to 0.25%, and the variant that also "
       "extends the k-NN reference set reached 0.79%. Recall fell from 0.492 to 0.41–0.43, so part of the "
       "unadapted \"recall\" had come from the inflated alarm rate. Once every method is re-calibrated on the same "
       "window, Aegis-OSR still leads on Friday (0.412 at 0.25% FPR against 0.338 at 0.56% for closed-set XGBoost). "
       "On Thursday the methods are roughly level: XGBoost has slightly higher recall (0.983 against 0.971) at twice "
       "the false-positive rate (1.07% against 0.52%).")
P.table("Re-Calibration on Warm-Up Windows from the Target Day (Zero-Day Recall / Benign FPR, Seed 1)",
        ["Fold", "Variant", "W", "Aegis-OSR", "Closed-set XGB", "XGB + Energy"],
        [["Mon–Thu → Fri", "none", "0", "0.492 / 7.68%", "0.479 / 1.27%", "—"],
         ["", "recal", "500", "0.355 / 0.54%", "0.357 / 0.66%", "0.334 / 0.52%"],
         ["", "recal", "2,000", "**0.412 / 0.25%**", "0.338 / 0.56%", "0.322 / 0.30%"],
         ["", "recal", "5,000", "0.435 / 1.48%", "—", "—"],
         ["", "recal+ref", "500", "0.318 / 0.18%", "—", "—"],
         ["", "recal+ref", "2,000", "0.426 / 0.79%", "0.357 / 0.65%*", "0.322 / 0.46%*"],
         ["", "recal+ref", "5,000", "0.457 / 1.66%", "—", "—"],
         ["", "oracle", "2,000", "0.484 / 1.31%", "0.472 / 1.10%", "0.472 / 1.21%"],
         ["Mon–Wed → Thu", "none", "0", "0.992 / 1.55%", "0.983 / 1.21%", "—"],
         ["", "recal", "500", "0.959 / 0.23%", "0.970 / 0.37%", "0.983 / 0.86%"],
         ["", "recal", "2,000", "0.971 / 0.52%", "0.983 / 1.07%", "0.983 / 1.14%"],
         ["", "recal+ref", "2,000", "0.968 / 0.56%", "0.983 / 1.14%*", "0.983 / 1.03%*"],
         ["", "oracle", "2,000", "0.982 / 0.69%", "0.972 / 0.42%", "0.983 / 0.45%"]],
        widths=[1.3, 0.9, 0.6, 1.4, 1.4, 1.4], label="adapt", size=8,
        notes="*Baselines without a k-NN component are unaffected by the reference update; differences from the "
              "*recal* row come from the smaller calibration split. Dashes: not evaluated for that variant.")
P.figure(FIG / "fig5_adaptation.png",
         "Label-light re-calibration of Aegis-OSR under temporal shift. Top: realised benign false-positive rate; "
         "bottom: zero-day recall. Dotted lines show the unadapted model; the star is the oracle that re-calibrates on "
         "a random benign sample of the target day.", 0.95)
P.para("Two details deserve a careful reading. First, larger windows are not uniformly better. With W = 5,000 the "
       "false-positive rate rose again to 1.48–1.66%. With n = 2,500 calibration flows, (9) predicts a spread of about "
       "0.2 points around 1%, so these values lie two to three standard deviations above budget—more than chance "
       "alone would explain. The likeliest reason is that the first 5,000 flows of a day are early-morning traffic and "
       "are not exchangeable with the rest of the day. Second, even the oracle, which samples benign flows from the whole "
       "day, realised 1.31% on Friday; with n = 1,000 calibration flows the predicted spread is 0.32 points, so this "
       "one is within the variation expected from a single calibration draw. We ran the temporal protocol with one "
       "seed only, so these observations should be confirmed with more seeds before anyone relies on them.")
P.subsection("Naturally Unseen Attacks and the Deployed Gate")
P.para("CICIDS2017 contains two attack types that are too rare to train on: 36 Infiltration flows and 11 Heartbleed "
       "flows. Neither the frozen detector nor the deployed gate saw them. Table IX and Fig. 6 report the gate's "
       "operating points on a held-out split of 200,000 benign flows, 76,390 known attacks, and these 47 flows.")
P.table("Deployed Zero-Day Gate on Held-Out Flows, with the Frozen v1.1 Detector for Reference",
        ["Operating point", "Benign FPR (%)", "Known-attack recall", "Never-seen attacks flagged"],
        [["Gate, α = 0.05%", "0.032", "0.865", "3 / 47 (6.4%)"],
         ["Gate, α = 0.1%", "0.073", "0.893", "14 / 47 (29.8%)"],
         ["Gate, α = 0.5%", "0.467", "0.994", "25 / 47 (53.2%)"],
         ["**Gate, α = 1% (deployed)**", "**0.921**", "**0.999**", "**29 / 47 (61.7%)**"],
         ["Gate, α = 5%", "4.943", "1.000", "46 / 47 (97.9%)"],
         ["Frozen v1.1 detector (τ = 0.85)", "0.064", "0.993", "0 / 47 (0%)"]],
        widths=[2.2, 1.2, 1.4, 1.8], label="gate",
        notes="At α = 1%: Heartbleed 11/11 flagged (all ZERO-DAY-ANOMALY); Infiltration 18/36 flagged (all ZERO-DAY-ANOMALY), "
              "the rest labelled BENIGN. Per-family recall of known attacks, gate vs. v1.1: Bot 0.879 vs. 0.617; "
              "WebAttack 1.000 vs. 0.420; BruteForce, DDoS, DoS, PortScan ≥ 0.995 for both.")
P.figure(FIG / "fig6_gate.png",
         "Operating points of the deployed gate. The realised benign false-positive rate (solid) tracks the nominal α "
         "(dotted) across two orders of magnitude.", 0.6)
P.para("The frozen detector flagged none of the 47 flows; it classified every one of them as benign. At its "
       "deployed setting of α = 1%, the gate flagged all 11 Heartbleed flows and half of the Infiltration flows, "
       "and labelled every one of them ZERO-DAY-ANOMALY rather than forcing it into a known family. That is the "
       "behaviour the design intends. With only 47 flows, though, these rates carry wide confidence intervals, and "
       "we regard them as illustrative; the statistical evidence is the LOAFO study.")
P.para("Table IX also exposes something the aggregate scores in Table III hide. On this split, the frozen "
       "detector's binary stage detected only 42.0% of web-attack flows and 61.7% of botnet flows, while its overall "
       "recall was 0.993. These two families together make up about 1% of the attacks, so an aggregate F1 of 0.99 "
       "is compatible with missing most of them. The gate, whose classifier is trained with class weighting, "
       "detected 87.9% of the botnet flows and all of the web-attack flows. We measured this on the gate's split, not on the frozen detector's own "
       "test split, so we report it as an observation that motivates per-family reporting rather than as a "
       "definitive per-family score for v1.1.")
P.subsection("Mitigation on the Controlled Test Plane")
P.para("Table X reports ten repetitions of two scenarios on the controlled test plane. Without defence, and with a "
       "recommendation that was proposed but not approved, the target kept accepting every attack attempt—a "
       "recommendation on its own changes nothing, which is the point of measuring it as a separate condition. "
       "With an approved response, the source block denied all subsequent DDoS attempts and the rate limit denied "
       "80% of DoS attempts. Both results are close to what the controlled adapter is built to do: a hard block "
       "denies everything, and the rate limiter is configured to let 20% through. The experiment therefore "
       "validates the measurement chain—detection, approval, enforcement, verification, rollback—more than it "
       "estimates what a real firewall would achieve. We report the simulation's assumed values beside the "
       "measurements and did not adjust either to match the other.")
P.table("Mitigation Measured on the Controlled Test Plane (10 Repetitions, Frozen-ML Detection)",
        ["Scenario", "No defence", "Recommendation only", "Approved response", "Simulation prior", "Δ"],
        [["DDoS, BLOCK_SOURCE", "0.00", "0.00", "**1.00 ± 0.00**", "0.82", "+0.18"],
         ["DoS, RATE_LIMIT", "0.00", "0.00", "**0.80 ± 0.00**", "0.78", "+0.02"]],
        widths=[1.6, 0.9, 1.3, 1.3, 1.1, 0.6], label="p11",
        notes="Values are measured effectiveness E from (12). Δ = measured − assumed.")
P.subsection("Engineering Performance and Security Validation")
P.para("Table XI lists the measured operating envelope of the platform on the development machine. The vectorised "
       "models score 15,000–22,000 flows per second, yet the full pipeline handles about 125 flows per second in "
       "batches of 500. The gap shows that per-flow enrichment and persistence (risk, incident correlation, database "
       "writes), not model inference, are the bottleneck. These are measured points on one machine, not capacity "
       "claims.")
P.table("Measured Operating Envelope (Single Windows Desktop, 20 Threads)",
        ["Workload", "Measured value"],
        [["Single-flow prediction, no explanation", "≈ 68 flows/s; p50 ≈ 15 ms, p95 ≈ 16 ms; 0% errors"],
         ["Pipeline batch, 100 / 500 flows", "≈ 113 / ≈ 125 flows/s (wall clock)"],
         ["Vectorised DT/RF inference, 1,000–5,000 flows", "≈ 15,000–22,000 flows/s"],
         ["Zero-Day Gate, batch scoring", "≈ 0.06 ms per flow"],
         ["SHAP TreeExplainer on frozen DT", "same order as prediction (p50 ratio ≈ 0.7)"],
         ["Concurrent approval of one action", "1 of 8 concurrent approvers succeeds"],
         ["Ingest queue at capacity", "explicit rejection; no silent drop"]],
        widths=[2.4, 3.0], label="perf")
P.para("A final validation pass checked ten categories with automated tests: authentication and RBAC (viewers "
       "cannot propose, analysts cannot approve, forged or expired tokens are rejected), response safety (no live "
       "mode, approval mandatory, rollback on failed verification, no automatic replay after recovery), API and "
       "input security (size limits, PCAP validation, path-traversal and filename sanitisation, rate limits, CORS "
       "allow-list, security headers), persistence and recovery, model-serving safety (batch cap of 500, artefact "
       "hashes), simulation isolation, auditability of the mitigation experiments, audit-log integrity, documented "
       "production boundaries, and integrity of the frozen research baseline. All ten passed. This shows that the "
       "prototype enforces the boundaries it claims; it is not a penetration test.")

# =====================================================================================  X. DISCUSSION
P.section("Discussion")
P.subsection("Why Fusion Works, and When It Does Not")
P.para("The two evidence channels fail in different places. The classifier recognises attacks that share "
       "structure with a known family—a withheld DDoS still looks a lot like DoS—but has no reason to object to a "
       "flow that simply lies far from its training data. The k-NN distance objects to anything unusual but cannot "
       "tell an unusual attack from an unusual benign flow, which is why on its own it loses half of the known "
       "attacks at a 1% budget. Summing surprisals lets a flow that is somewhat suspicious to both channels cross "
       "the threshold even when neither channel alone would raise it. The brute-force fold is the clearest case, "
       "and the ablations confirm that both the choice of fusion rule and the choice of novelty detector matter.")
P.para("The method fails where an attack is statistically indistinguishable from benign traffic at the flow level. "
       "The botnet in CICIDS2017 communicates with its controller through small, regular HTTP exchanges; PortScan "
       "produces very short flows that resemble failed connections. Neither is far from benign traffic in this feature "
       "space, and no rearrangement of the same features is likely to fix that. Detecting them as novelties will need "
       "context beyond a single flow, such as host-level aggregation over time.")
P.subsection("What the Guarantee Buys")
P.para("Conformal calibration does not make a detector better at ranking; it makes its alarm rate predictable. That "
       "is valuable in itself, because it turns the false-alarm rate into a setting that a SOC can choose to fit its "
       "staffing, and because it makes comparisons fair: every method in Table IV spends the same budget. The temporal "
       "results show the other side. When benign traffic shifts, the realised rate can exceed the budget by a factor "
       "of seven, and nothing in the method warns about it. A deployment should therefore monitor the realised alert "
       "rate on traffic believed to be benign and trigger re-calibration when it drifts. That procedure needs no "
       "labelled attacks, which is what makes it practical.")
P.subsection("Lessons from Building the Platform")
P.para("Three lessons from the project seem worth passing on. First, aggregate metrics conceal weak families: an F1 "
       "of 0.990 coexisted with detecting fewer than half of the web attacks on a different split, which argues for "
       "always reporting per-family recall. Second, our own early temporal evaluation was leaky, and we found the "
       "problem only because we re-derived every split from scratch for the research study; evaluation code "
       "deserves the same review as model code. Third, the choice of the Decision Tree for production, made on a "
       "weighted score that favoured recall, gave a model with four times the false-positive rate of XGBoost and, "
       "as Table VI shows, far poorer behaviour on unseen families. With conformal calibration available, a model "
       "can be chosen for its ranking quality and its operating point set separately, which is a cleaner division "
       "of concerns.")

# =====================================================================================  XI. THREATS
P.section("Threats to Validity")
P.numbered([
    "*Single benchmark.* All results come from CICIDS2017, a testbed capture with known labelling and "
    "flow-construction problems [12], [13]. We used the public export so that results are comparable with prior "
    "work; re-extracted flows might change individual numbers. A cross-dataset evaluation on CSE-CIC-IDS2018 is "
    "implemented in our code but was not run for this paper, and we make no claim about it.",
    "*Simulated zero-days.* LOAFO withholds families that are still present in the same capture, on the same network, "
    "produced by the same tools. A genuinely new attack in a different network may be harder to detect. The "
    "47 natural unknowns help, but they are too few for statistical conclusions.",
    "*Exchangeability.* Proposition 1 holds only if calibration and test benign traffic are exchangeable. The "
    "temporal results show this is not automatic, and the re-calibration study used a single seed and two folds.",
    "*Sampling caps.* To keep runs tractable, training, validation, and test sets were capped per family. Results "
    "on uncapped data could differ, particularly for the largest families.",
    "*Design selection.* The fusion rule and novelty detector were chosen on a pilot seed that is excluded from "
    "reporting. Hyper-parameters such as k = 5 and the reference-set size were not tuned further, which may "
    "understate what the method can achieve but avoids optimising on the test seeds.",
    "*Controlled plane.* The mitigation experiment runs in process, on synthetic connection attempts, with an "
    "adapter whose behaviour partly determines the result. It says nothing about the effectiveness of a real "
    "firewall or endpoint agent.",
])

# =====================================================================================  XII. CONCLUSION
P.section("Conclusion and Future Work")
P.para("We set out to give a flow-based intrusion detector a way to say \"this is an attack I do not recognise\" "
       "while keeping its false alarms at a level chosen in advance. Aegis-OSR does this by adding a classifier's "
       "attack evidence to a benign-neighbourhood distance and calibrating the sum conformally. On CICIDS2017 it "
       "detected 70.6% of flows from withheld attack families at a realised 1.00% benign false-alarm rate, against "
       "49.0% for the same classifier alone, and it labelled those alerts as unknown rather than forcing them into a "
       "known family. It caught most volumetric, web, and brute-force attacks it had never seen, and almost none of "
       "the botnet traffic. When the benign traffic changed from one day to the next, its false-alarm guarantee "
       "failed, and re-calibrating on a few thousand benign flows from the new day restored it without retraining.")
P.para("Around this detector, Aegis provides explanations, an itemised risk score, incident correlation, and a "
       "response workflow in which nothing happens without human approval and nothing reaches a live network. We "
       "have tried throughout to report measured values, assumed values, and their limitations side by side.")
P.para("Several directions follow directly from the limitations. The most pressing is to run the cross-dataset "
       "protocol on CSE-CIC-IDS2018 and to repeat the temporal study with more seeds. Beyond that, we plan to "
       "monitor the realised alert rate online and re-calibrate automatically when it drifts; to aggregate flows "
       "per host over time so that low-and-slow threats such as botnets become visible; and to replace the "
       "in-process test plane with a sandboxed network, keeping the same approval, verification, and rollback "
       "model before any real enforcement is considered.")

# =====================================================================================  BACK MATTER
P.section("Data and Code Availability")
P.para("CICIDS2017 is available from the Canadian Institute for Cybersecurity [4]. Source code, configuration, "
       "frozen model hashes, per-run result records, and the scripts that regenerate every table and figure in this "
       "paper are available at https://github.com/Dolendra/Intelligent-Machine-Learning-Based-Intrusion-Detection-"
       "and-Attack-Defense-Simulation-System (research results correspond to commit 775e9a9).", indent=False)
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
P.para("The authors thank the Department of Computer Science and Engineering, [Institution Name], for computing "
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
]
for i, ref in enumerate(REFS, 1):
    p = d.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.left_indent = __import__("docx.shared", fromlist=["Cm"]).Cm(0.75)
    p.paragraph_format.first_line_indent = __import__("docx.shared", fromlist=["Cm"]).Cm(-0.75)
    p.paragraph_format.space_after = Pt(1.5)
    P._runs(p, f"[{i}]\t" + ref, 8.5)

P.save(OUT)
print("saved", OUT, "tables", P.tab, "figures", P.fig, "equations", P.eq)
