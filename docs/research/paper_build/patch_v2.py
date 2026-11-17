"""Second revision of the paper: cyber range, 5-seed temporal study, cross-dataset transfer, model families,
explanation stability and ATT&CK context. Applies block replacements to paper.py (idempotent guard)."""
from pathlib import Path

P = Path(__file__).with_name("paper.py")
s = P.read_text(encoding="utf-8")
if "TRACE-DRIVEN-CYBER-RANGE" in s:
    raise SystemExit("already patched")


def between(text: str, start: str, end: str, new: str) -> str:
    i = text.index(start)
    j = text.index(end, i)
    return text[:i] + new + text[j:]


def swap(text: str, old: str, new: str) -> str:
    assert old in text, old[:80]
    return text.replace(old, new, 1)


# ------------------------------------------------------------------ title
s = swap(s, '''r = t.add_run("Aegis: Open-Set Network Intrusion Detection with Conformal False-Alarm Control, "
              "Explainable Triage, and Human-Gated Response")''',
         '''r = t.add_run("Aegis: Open-Set Network Intrusion Detection with Conformal False-Alarm Control "
              "and a Trace-Driven Cyber Range for Measured, Human-Gated Response")''')

# ------------------------------------------------------------------ abstract
s = between(s, 'P.para("**Abstract—**', 'P.para("**Index Terms—**', '''P.para("**Abstract—**Machine-learning intrusion detectors routinely report F1 scores above 0.99 on public flow "
       "benchmarks, yet they assume a closed world and are rarely tested outside the capture they learned from. We "
       "examine both assumptions and describe Aegis, a detection platform built around the answers. Its frozen "
       "two-stage detector scores binary F1 0.990 on a stratified CICIDS2017 split, but flags none of the 47 "
       "naturally occurring unseen attacks in that corpus, and on CSE-CIC-IDS2018 its F1 falls to 0.185. Aegis-OSR, "
       "an open-set gate that runs beside it, adds a classifier's attack evidence to a benign-neighbourhood "
       "distance and calibrates the sum with split-conformal prediction, so that the benign false-alarm rate is "
       "chosen in advance. Under leave-one-attack-family-out evaluation (six families, five seeds) it detected 70.6% "
       "(95% CI 68.9–72.3%) of flows from the withheld family at a realised 1.00% false-alarm rate, against 49.0% for "
       "the same classifier alone (30 of 30 paired wins, p = 1.9×10^{−9}); ##MF_ABSTRACT## The guarantee does not "
       "survive distribution shift: false alarms rose to 7.1% on a later capture day and to 35% on the 2018 dataset. "
       "Re-calibrating on 2,000 benign flows from the new day, without retraining, restored the rate (0.82%; 0.97% "
       "with a random sample), but not the cross-dataset case, where the unseen family was barely separable from "
       "benign traffic (AUROC 0.58). To measure what such numbers mean operationally, we built a trace-driven cyber "
       "range that replays recorded flows through the real detectors on a seeded clock and lets a human choose the "
       "response. Across 1,190 runs, the frozen detector never raised an incident in a zero-day scenario while the "
       "gate did in every run (mean 4.3 s); requiring three alerts within five seconds removed all false incidents; "
       "and isolating the target stopped attacks but blocked 27% of legitimate traffic. We report successes and "
       "failures side by side and release all code and run records.",
       indent=False, size=9.5)
''')
s = swap(s, '"prediction, false-alarm control, concept drift, explainable AI, CICIDS2017, security operations."',
         '"prediction, false-alarm control, concept drift, cyber range, explainable AI, MITRE ATT&CK, CICIDS2017, "\n       "CSE-CIC-IDS2018."')

# ------------------------------------------------------------------ contributions + roadmap
s = between(s, 'P.numbered([\n    "**Aegis-OSR**', 'P.para("The rest of the paper is organised as follows.', '''P.numbered([
    "**Aegis-OSR**, an open-set detector that maps a classifier's attack evidence and a k-nearest-neighbour "
    "benign-novelty distance into benign surprisals with an exponential tail, sums them, and calibrates the sum "
    "with split-conformal prediction. A Mondrian conformal test then decides whether an alert matches a known "
    "family or should be reported as unknown (Section VI).",
    "**A controlled comparison** against ten alternatives that all pass through the same conformal calibration, "
    "and a separate comparison of ten classifier families—including kernel SVMs and MLP, CNN and LSTM networks—at "
    "a matched 1% false-alarm budget on seen and unseen families (Sections IX–X).",
    "**A generalisation study that reports its failures**: leave-one-attack-family-out over six families and five "
    "seeds; a five-seed temporal split with label-light re-calibration; CICIDS2017 → CSE-CIC-IDS2018 transfer for "
    "both the frozen detector and the open-set gate; and the 47 naturally occurring unseen attacks.",
    "**A trace-driven cyber range** in which recorded flows meet the real detectors, a per-source incident rule, "
    "firewall controls and a capacity model of the target service on a seeded clock, so that detection latency, "
    "service impact, collateral damage and recovery are measured rather than assumed; with a 1,190-run experiment "
    "programme over defenses, intensity, attacker count, detector choice, alert threshold and approval delay "
    "(Sections VIII, X-H).",
    "**An integrated, human-gated platform** with SHAP/LIME explanations and an explanation-stability study, "
    "MITRE ATT&CK context for every detection and campaign, an approval-based response workflow, and frozen, "
    "hashed, reproducible artefacts (Sections III, VII, X-I).",
])
''')
s = between(s, 'P.para("The rest of the paper is organised as follows.', '\n# ====', '''P.para("The rest of the paper is organised as follows. Section II reviews related work. Section III describes the "
       "platform, Section IV the data, and Section V the closed-set detector. Section VI presents Aegis-OSR. "
       "Section VII covers explanation, threat intelligence, risk and response, and Section VIII the cyber range. "
       "Section IX sets out the experimental protocol and Section X the results. Section XI discusses them, "
       "Section XII lists threats to validity, and Section XIII concludes.")
''')

# ------------------------------------------------------------------ system overview
s = swap(s, '''"response workflow consume both. Solid arrows carry data; dashed arrows lead to the isolated simulation and "
         "the controlled lab plane.", 1.0)''',
         '''"response workflow consume both. Solid arrows carry data; dashed arrows lead to the trace-driven cyber range "
         "and the controlled lab plane.", 1.0)''')
s = swap(s, '''"refused. A React console exposes a dashboard, a live traffic monitor that replays held-out flows through "
       "both detectors, a zero-day laboratory for exploring the α trade-off, a research view of all experimental "
       "results, the response queue, and system health.")''',
         '''"refused. A React console exposes a dashboard, a detection bench, the cyber range, a live traffic monitor "
       "that replays held-out flows through both detectors, a zero-day laboratory for exploring the α trade-off, a "
       "research view of all experimental results, incident and campaign workspaces, and system health.")''')
s = between(s, 'P.para("Throughout the project we kept three kinds of numbers apart', '\n# ====', '''P.para("Throughout the project we kept four kinds of numbers apart, and we keep them apart here: **research "
       "measurements** on dataset splits (Sections V and X-A to X-G); **range measurements**, which are measured "
       "inside the cyber range but depend on its modelled traffic rates and capacities (Sections VIII and X-H); "
       "**storyboard assumptions**, configuration values used only to animate an illustrative attack walkthrough; "
       "and **controlled-lab measurements** from an in-process test plane (Section X-J). Conflating them is a common "
       "way for project reports to overstate what they have shown.")
''')
s = swap(s, '"Section X.", indent=False)', '"Section XI.", indent=False)')
s = swap(s, 'We use this to read the re-calibration results in Section IX-D.', 'We use this to read the re-calibration results in Section X-D.')

# ------------------------------------------------------------------ VII tail + new VIII (cyber range)
s = between(s, 'P.subsection("Simulation and the Controlled Test Plane")', '\n# =====================================================================================  VIII. PROTOCOL', '''P.subsection("Threat-Intelligence Context")
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
       "0.82 for DDoS) is a configuration value and is labelled as such. Before the cyber range existed, we measured "
       "the response path on an in-process test plane: a test client generates attacker and benign connection "
       "attempts, Aegis detects the attack with the frozen models, and an approved action is applied through the "
       "controlled adapter. Its mitigation effectiveness is")
P.equation(r"E=\\frac{a_{\\mathrm{pre}}-a_{\\mathrm{post}}}{a_{\\mathrm{pre}}},", "eq_E")
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
P.para("The range draws from a pool of 11,665 held-out CICIDS2017 flows (8,000 benign, up to 700 per attack family, "
       "and all 36 Infiltration and 11 Heartbleed flows) taken from the deployed gate's test split. Each simulated "
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
P.equation(r"\\sigma=\\min\\left(1,\\frac{C}{L}\\right)", "eq_serve")
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
''')

# ------------------------------------------------------------------ protocol
s = swap(s, '''"been in their training split; we report no results from that earlier evaluation. The temporal protocol was "
       "run with one seed.")''',
         '''"been in their training split; we report no results from that earlier evaluation. The temporal protocol was "
       "run with five seeds (1–5).")
P.subsection("Cross-Dataset Transfer")
P.para("CSE-CIC-IDS2018 was captured a year later on a different, much larger network with different tooling. We "
       "mapped its labels to the CICIDS2017 families and its columns to the same 77-feature schema, and drew a "
       "sample of 804,192 flows (143,116 benign; DDoS, DoS, brute force, bot, web attacks and Infiltration, but no "
       "port scans). Two experiments use it. First, the *frozen* v1.1 artefacts are scored unchanged on up to 20,000 "
       "flows per attack label (295,727 flows in total); nothing is retrained. Second, Aegis-OSR and every baseline "
       "are trained and calibrated on CICIDS2017 and tested on the 2018 sample, where Infiltration—never in "
       "training—is the unknown family; warm-up flows for re-calibration are the earliest 5,000 benign 2018 flows. "
       "This protocol was run with five seeds.")''')
s = swap(s, 'P.subsection("Metrics and Statistics")', '''P.subsection("Model Families")
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
       "10 and 30 s—1,190 runs in all, which take about two minutes.")
P.subsection("Explanation Stability")
P.para("For twenty held-out replay flows of each class we compute SHAP attributions and measure three things: "
       "consistency (mean pairwise Jaccard overlap of the top-five features among flows of one family), robustness "
       "(Jaccard overlap between a flow's top five and those of the same flow with independent ±1% multiplicative "
       "noise on every feature, plus the Spearman correlation of the top-ten magnitudes), and agreement (Jaccard "
       "overlap of the top five features from SHAP and from LIME).")
P.subsection("Metrics and Statistics")''')

P.write_text(s, encoding="utf-8")
print("patched part 1")
