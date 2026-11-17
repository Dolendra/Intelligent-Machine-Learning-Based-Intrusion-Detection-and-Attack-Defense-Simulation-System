"""Paper revision part 2: results from the temporal study onward, discussion, threats, conclusion, references."""
from pathlib import Path

P = Path(__file__).with_name("paper.py")
s = P.read_text(encoding="utf-8")
if "##RESULTS_V2##" in s:
    raise SystemExit("already patched")


def between(text, start, end, new):
    i = text.index(start)
    j = text.index(end, i)
    return text[:i] + new + text[j:]


RESULTS = r'''P.subsection("Temporal Shift")  # ##RESULTS_V2##
P.para("Table VII reports the temporal split, where calibration and test benign traffic come from different days. "
       "Here the guarantee visibly breaks. Training on Monday–Thursday and testing on Friday, Aegis-OSR realised a "
       "benign false-positive rate of 7.09% against a nominal 1%, and the k-NN distance alone 8.82%; closed-set "
       "XGBoost stayed close to budget (1.27%). The benign *neighbourhood* moves from day to day much more than the "
       "classifier's benign posterior does, so the channel that gives Aegis-OSR its zero-day recall also makes it the "
       "more sensitive to benign drift. On Thursday the k-NN distance alone drifted even further (11.0%), yet "
       "Aegis-OSR stayed at 1.72%, because the classifier's evidence kept the fused score of most benign flows low.")
P.table("Temporal Split by Capture Day, No Adaptation (α = 1%, Mean over Five Seeds)",
        ["Method", "Mon–Wed → Thu recall", "FPR (%)", "Mon–Thu → Fri recall", "FPR (%)"],
        [["Aegis-OSR", "0.992", "1.72", "0.495", "7.09"],
         ["Aegis-OSR w/ AE novelty", "0.986", "1.66", "0.490", "5.94"],
         ["Closed-set XGB", "0.982", "1.25", "0.471", "1.27"],
         ["XGB + Energy", "0.983", "1.27", "0.447", "1.28"],
         ["k-NN distance", "0.055", "11.01", "0.423", "8.82"],
         ["Autoencoder", "0.015", "9.65", "0.264", "8.14"],
         ["Closed-set DT (v1.1-style)", "0.857", "0.10", "0.127", "0.16"]],
        widths=[2.0, 1.3, 0.8, 1.3, 0.8], label="temporal",
        notes="Unknown families: Thursday—WebAttack (Aegis-OSR recall 0.998), Infiltration (0.650; closed-set XGB 0.000); "
              "Friday—DDoS (0.992), PortScan (0.036), Bot (0.009). Recall values are not comparable across rows when the "
              "realised FPR differs from the budget.")
P.para("Per family, the temporal results repeat the LOAFO picture. On Friday, DDoS was caught (99.2%) while PortScan "
       "(3.6%) and Bot (0.9%) were not; Friday's overall recall of about 49% is essentially the DDoS share of the "
       "unknown flows. On Thursday, web attacks were caught and so were 65% of the Infiltration flows, against none "
       "for closed-set XGBoost. With an inflated false-positive rate, however, the recall figures in Table VII cannot "
       "be compared across methods; re-calibration is needed first.")
P.subsection("Label-Light Re-Calibration")
P.para("Table VIII and Fig. 5 show what re-calibration buys, averaged over five seeds. On Friday, re-calibrating on "
       "the first 2,000 benign flows of the day reduced Aegis-OSR's false-positive rate from 7.09% to 0.82%, and to "
       "0.36% with 500 flows, at the cost of recall (0.495 → 0.43 and 0.35); part of the unadapted recall had come from "
       "the inflated alarm rate. Re-calibrating on a *random* sample of 2,000 benign flows from the whole day (the "
       "oracle) gave 0.97% [0.64, 1.30]—exactly the behaviour Proposition 1 predicts once calibration and test traffic "
       "are exchangeable again. Larger arrival-order windows did worse, not better: with 5,000 flows the rate rose to "
       "2.6–2.8%, two to three times the spread that (9) allows, which indicates that the first minutes of a day are "
       "not exchangeable with the rest of it. A deployment should therefore re-calibrate on a sample spread over "
       "time rather than on the first N flows. Once every method is re-calibrated, the open-set advantage on Friday "
       "shrinks to a few points (0.429 against 0.367 for closed-set XGBoost at W = 2,000) and disappears under the "
       "oracle (0.390 against 0.397); on Thursday closed-set XGBoost is slightly ahead. Under temporal shift, in "
       "other words, most of the value of Aegis-OSR lies in the calibrated alarm rate rather than in extra recall.")
P.table("Re-Calibration on Benign Flows from the Target Day (Zero-Day Recall / Benign FPR, Mean over Five Seeds)",
        ["Fold", "Variant", "W", "Aegis-OSR", "Closed-set XGB", "XGB + Energy"],
        [["Mon–Thu → Fri", "none", "0", "0.495 / 7.09%", "0.471 / 1.27%", "0.447 / 1.28%"],
         ["", "recal", "500", "0.345 / 0.36%", "0.366 / 0.61%", "0.341 / 0.59%"],
         ["", "recal", "2,000", "**0.429 / 0.82%**", "0.367 / 0.68%", "0.344 / 0.54%"],
         ["", "recal", "5,000", "0.441 / 2.57%", "—", "—"],
         ["", "recal+ref", "2,000", "0.383 / 0.63%", "0.368 / 0.63%*", "0.354 / 0.57%*"],
         ["", "recal+ref", "5,000", "0.444 / 2.84%", "—", "—"],
         ["", "oracle", "2,000", "0.390 / 0.97%", "0.397 / 0.81%", "0.392 / 0.84%"],
         ["Mon–Wed → Thu", "none", "0", "0.992 / 1.72%", "0.982 / 1.25%", "0.983 / 1.27%"],
         ["", "recal", "500", "0.938 / 0.27%", "0.951 / 0.43%", "0.974 / 0.91%"],
         ["", "recal", "2,000", "0.951 / 0.49%", "0.980 / 0.97%", "0.982 / 0.95%"],
         ["", "recal+ref", "2,000", "0.954 / 0.49%", "0.960 / 0.79%*", "0.978 / 0.94%*"],
         ["", "oracle", "2,000", "0.981 / 0.92%", "0.970 / 0.85%", "0.979 / 0.89%"]],
        widths=[1.3, 0.9, 0.6, 1.4, 1.4, 1.4], label="adapt", size=8,
        notes="Warm-up windows are the earliest W benign flows of the target day; the oracle samples 2,000 benign flows at "
              "random from the whole day. *Baselines without a k-NN component are unaffected by the reference update; "
              "differences from the *recal* row come from the smaller calibration split.")
P.figure(FIG / "fig5_adaptation.png",
         "Label-light re-calibration of Aegis-OSR under temporal shift (mean over five seeds). Top: realised benign "
         "false-positive rate; bottom: zero-day recall. Dotted lines show the unadapted model; the star is the oracle "
         "that re-calibrates on a random benign sample of the target day.", 0.95)
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
P.para("The frozen detector flagged none of the 47 flows. At its deployed setting of α = 1%, the gate flagged all 11 "
       "Heartbleed flows and half of the Infiltration flows, and labelled every one of them ZERO-DAY-ANOMALY rather "
       "than forcing it into a known family. With only 47 flows these rates carry wide intervals and we regard them "
       "as illustrative. Table IX also exposes something the aggregate scores in Table III hide: on this split the "
       "frozen detector's binary stage caught only 42.0% of web-attack flows and 61.7% of botnet flows, while its "
       "overall recall was 0.993; these two families make up about 1% of the attacks, so an aggregate F1 of 0.99 is "
       "compatible with missing most of them. We measured this on the gate's split rather than the frozen detector's "
       "own test split, so we treat it as a reason to report per-family recall, not as a definitive score for v1.1.")
P.subsection("Transfer to Another Network: CSE-CIC-IDS2018")
P.para("Table X scores the *unchanged* frozen detector on CSE-CIC-IDS2018. Its benign false-positive rate stayed "
       "low (0.08%) and its precision high (0.992), but its recall collapsed to 0.102 and its F1 from 0.990 to "
       "0.185. The per-label rows show that the failure is not confined to unfamiliar labels: 2018's DDoS (HOIC, "
       "LOIC-HTTP, LOIC-UDP), botnet and SSH brute-force traffic—families the detector was trained on—were detected "
       "almost never, while Slowloris (95.6%) and the small FTP brute-force sample (68.6%) carried over. The same "
       "attack *names* evidently produce different flow statistics on a different network and toolchain.")
P.table("Frozen v1.1 Detector Scored Unchanged on CSE-CIC-IDS2018",
        ["2018 label", "Family", "n", "Alert rate", "Correct family"],
        [["Benign", "BENIGN", "143,116", "0.08%", "—"],
         ["DoS-Slowloris", "DoS", "9,908", "95.6%", "95.6%"],
         ["DoS-SlowHTTPTest", "DoS", "55", "70.9%", "0.0%"],
         ["FTP-BruteForce", "BruteForce", "51", "68.6%", "68.6%"],
         ["DoS-GoldenEye", "DoS", "20,000", "27.4%", "27.4%"],
         ["Brute Force-XSS / -Web / SQL inj.", "WebAttack", "867", "2.4–11.0%", "≤ 0.9%"],
         ["Infiltration", "Infiltration", "20,000", "1.4%", "—"],
         ["DoS-Hulk", "DoS", "20,000", "0.8%", "0.7%"],
         ["DDoS-HOIC / LOIC-HTTP / LOIC-UDP", "DDoS", "41,730", "≤ 0.1%", "0.0%"],
         ["Bot", "Bot", "20,000", "0.0%", "0.0%"],
         ["SSH-Bruteforce", "BruteForce", "20,000", "0.0%", "0.0%"],
         ["**All attacks**", "", "152,611", "**recall 0.102**", "precision 0.992, **F1 0.185**"]],
        widths=[2.2, 1.0, 0.9, 1.1, 1.6], label="v11_2018", size=8,
        notes="Up to 20,000 flows per attack label; labels mapped to CICIDS2017 families; features mapped to the 2017 schema. "
              "Nothing was retrained or re-thresholded.")
P.para("Table XI reports the open-set protocol across datasets, with Infiltration—never in training—as the unknown "
       "family. It is a negative result. Every method's ability to separate the unknown family from benign traffic "
       "was close to chance (AUROC_u 0.44–0.60), the conformal guarantee failed badly (Aegis-OSR realised 35.2% "
       "benign false positives at α = 1%), and even the classifier's known families transferred poorly: the gate "
       "attributed only 7.5% of known 2018 attacks to their correct family. Re-calibration on 500 benign 2018 flows "
       "restored the alarm rate (0.83%) but left 4.3% recall; larger windows did not converge to the budget. Two "
       "explanations are compatible with the data and we cannot yet separate them: the CICIDS2017 benign "
       "neighbourhood is simply the wrong reference for a different network, and CSE-CIC-IDS2018's Infiltration "
       "label is known to contain many flows that are indistinguishable from benign traffic [40].")
P.table("Open-Set Detection Trained on CICIDS2017, Tested on CSE-CIC-IDS2018 (α = 1%, Mean over Five Seeds)",
        ["Method", "Zero-day recall", "AUROC_u", "Known recall", "Benign FPR (%)"],
        [["Aegis-OSR", "0.438", "0.576", "0.864", "35.2"],
         ["Aegis-OSR w/ AE novelty", "0.433", "0.563", "0.926", "23.7"],
         ["Aegis-OSR w/ IForest novelty", "0.150", "0.487", "0.757", "3.4"],
         ["k-NN distance", "0.714", "0.559", "0.519", "59.3"],
         ["Autoencoder", "0.304", "0.550", "0.514", "27.4"],
         ["Closed-set XGB", "0.166", "0.490", "0.842", "4.1"],
         ["XGB + Energy", "0.155", "0.495", "0.799", "3.8"],
         ["Closed-set DT (v1.1-style)", "0.085", "0.453", "0.331", "14.0"],
         ["Isolation Forest", "0.037", "0.438", "0.007", "1.5"],
         ["Aegis-OSR, recal on 500 / 2,000 2018 flows", "0.043 / 0.152", "—", "—", "0.83 / 2.36"]],
        widths=[2.6, 1.2, 0.9, 1.0, 1.1], label="cross", size=8,
        notes="Unknown family: Infiltration (never in CICIDS2017 training). No CSE-CIC-IDS2018 data was used for training.")
##MF_SECTION##
P.subsection("The Cyber Range: From Detection Scores to Outcomes")
P.para("Tables XIII and XIV and Fig. 7 summarise the 1,190 range runs. Because the replayed families come from the "
       "same capture as the detectors' training data, per-flow recall is near-perfect for every in-distribution "
       "scenario and incidents are raised within 0–3.4 s of the attack starting. The range is therefore most "
       "informative about what happens *after* detection, and about the one scenario the detectors were not built "
       "for.")
P.para("**Zero-day scenario.** With the frozen detector as the incident source, the zero-day intrusion was never "
       "detected in ten runs; its per-flow recall on that traffic was 0.000. With the gate, an incident was raised in "
       "all ten runs after 4.3 s on average [2.6, 6.0], with a per-flow recall of 0.645. On beacon traffic the gate "
       "also shortened detection (2.4 s against 3.4 s) and raised per-flow recall from 0.714 to 0.945.")
P.para("**Alert aggregation is the operational partner of calibration.** The gate's per-flow false-positive rate in "
       "the range was about 0.85%, roughly ten times the frozen detector's 0.07%, yet neither produced a single false "
       "incident at the default k = 3 alerts in 5 s. At k = 1, every scenario produced 17–19 false incidents per run "
       "(normal users flagged as attackers); at k = 2, fewer than one; at k ≥ 3, none. The price is latency: from k = 1 "
       "to k = 8 the time to detect a slow beacon grew from 1.2 s to 7.1 s and a slow host discovery from 1.2 s to "
       "6.8 s, while a DoS flood stayed under one second. Conformal calibration fixes the per-flow rate; "
       "per-source aggregation turns that rate into an acceptable number of incidents.")
P.table("Cyber Range: Defense Comparison (Mean over Nine Scenarios, Ten Seeds Each, Automatic Response after 3 s)",
        ["Defense", "Attack success after defense", "Availability during attack (mean / min)", "Legitimate traffic blocked", "Recovery after defense (s)"],
        [["Block source", "0.0%", "99.8% / 96.4%", "0.0%", "2.6"],
         ["Rate limit", "19.7%", "99.6% / 96.2%", "0.0%", "3.6"],
         ["Isolate target", "0.0%", "10.8% / 0.0%", "27.4%", "52.4"],
         ["Monitor only", "—", "89.7% / 84.7%", "0.0%", "—"],
         ["Increase inspection", "100%", "89.7% / 84.7%", "0.0%", "—†"]],
        widths=[1.5, 1.3, 1.9, 1.3, 1.2], label="range_def",
        notes="Means over scenarios hide that most scenarios are cheap for the server; in DoS and DDoS runs without a "
              "blocking defense, availability fell to 27–31%. †Recovery only after the attack ends.")
P.figure(FIG / "fig7_range_tradeoff.png",
         "Defense trade-off in the cyber range: each point is one scenario (mean of ten seeds). Blocking and rate "
         "limiting keep the service available without touching legitimate users; isolating the target also stops the "
         "attack but cuts off about a quarter of legitimate traffic.", 0.7)
P.para("**Choosing the defense matters more than detecting faster.** Blocking the detected source stopped every "
       "attack with no collateral; rate limiting left about 20% of attack traffic through, as designed, but kept the "
       "service available; isolating the target stopped the attack too, but blocked 27.4% of legitimate traffic and "
       "took about 52 s to recover, because isolation can only be lifted once the attacker falls quiet. In a DDoS, "
       "*block source* acts per detected source, so each new source leaks a little traffic until it, too, is "
       "detected: with eight sources, availability dipped to 36.5% before the block took hold, against 95.2% with two.")
P.para("**The analyst's decision time is the dominant cost for floods.** With the response applied immediately, "
       "availability during a DDoS averaged 99.5%; with a 3 s approval it was 98.0%, with 10 s 89.9%, and with 30 s "
       "62.0%. Detection latency was effectively zero in all four cases. In the DoS scenario the attacker was usually "
       "caught during its reconnaissance stage and blocked before the flood began, so availability stayed at or "
       "above 99.8% for delays up to 10 s and fell to 85.3% only at 30 s—an argument for responding to "
       "reconnaissance, not only to impact.")
P.table("Cyber Range: Which Detector Raises the Incident (Ten Seeds per Cell)",
        ["Scenario", "Detector", "Runs detected", "Detection latency (s)", "Attack-flow recall", "Benign flow FPR"],
        [["Zero-day intrusion", "Frozen v1.1", "0 / 10", "—", "0.000", "0.06%"],
         ["", "Zero-Day Gate", "10 / 10", "4.3 [2.6, 6.0]", "0.645", "0.85%"],
         ["Beacon-style bot", "Frozen v1.1", "10 / 10", "3.4 [1.7, 5.1]", "0.714", "0.07%"],
         ["", "Zero-Day Gate", "10 / 10", "2.4 [0.9, 3.9]", "0.945", "0.86%"],
         ["Web request burst", "Frozen v1.1", "10 / 10", "2.6 [0.6, 4.6]", "0.866", "0.10%"],
         ["", "Zero-Day Gate", "10 / 10", "2.6 [0.6, 4.6]", "1.000", "0.88%"],
         ["Slow host discovery", "Frozen v1.1", "10 / 10", "2.4 [0.9, 3.9]", "1.000", "0.07%"],
         ["", "Zero-Day Gate", "10 / 10", "2.4 [0.9, 3.9]", "1.000", "0.83%"]],
        widths=[1.6, 1.2, 1.0, 1.4, 1.2, 1.1], label="range_det", size=8,
        notes="False incidents were zero for every detector at the default threshold (3 alerts within 5 s). The remaining five "
              "scenarios were detected by both detectors in every run within 0.0–0.8 s.")
P.subsection("Do the Explanations Hold Up?")
P.para("Table XV reports the explanation-stability study. SHAP attributions were robust to ±1% feature noise for "
       "most classes—the top-five overlap was 0.90–1.00 for benign, brute-force, DoS, DDoS and port-scan flows—but not "
       "for botnet (0.51) and web-attack flows (0.66), whose rank correlations under noise fell to 0.34 and 0.51. These "
       "are the same two families on which the frozen detector is weakest (Table IX), which suggests that unstable "
       "explanations are a symptom of a fragile decision boundary and could serve as a warning signal. Within a "
       "family, port-scan flows always received the same explanation (1.00) and DDoS flows nearly so (0.85), while "
       "DoS, web-attack and botnet explanations were flow-specific (0.45–0.54). SHAP and LIME agreed poorly overall "
       "(0.26), and for web attacks hardly at all (0.06). Different explainers can point at different features for "
       "the same decision, which supports presenting explanations as decision support rather than as evidence.")
P.table("Explanation Stability of the Frozen Detector (20 Held-Out Flows per Class)",
        ["Class", "Consistency within family", "Robustness to ±1% noise", "Rank stability (Spearman)", "SHAP–LIME agreement"],
        [["Benign", "0.54", "0.98", "0.98", "0.14"],
         ["Bot", "0.45", "**0.51**", "**0.34**", "0.44"],
         ["BruteForce", "0.74", "0.92", "0.99", "0.20"],
         ["DDoS", "0.85", "0.90", "0.91", "0.38"],
         ["DoS", "0.53", "0.90", "0.95", "0.38"],
         ["PortScan", "1.00", "1.00", "1.00", "0.24"],
         ["WebAttack", "0.54", "**0.66**", "**0.51**", "**0.06**"]],
        widths=[1.2, 1.4, 1.4, 1.4, 1.3], label="xai",
        notes="Consistency, robustness and agreement are mean Jaccard overlaps of top-five SHAP features (1 = identical). "
              "Rank stability is the Spearman correlation of the top-ten attribution magnitudes with and without noise.")
P.subsection("Mitigation on the Controlled Test Plane")
P.para("Before the range existed, the controlled test plane measured the response chain directly (Table XVI). "
       "Without defence and with a proposed-but-unapproved recommendation, the target accepted every attack attempt; "
       "with an approved response, the source block denied all subsequent DDoS attempts and the rate limit 80% of DoS "
       "attempts—close to what the controlled adapter is built to do. The experiment validates the chain detection → "
       "approval → enforcement → verification → rollback more than it estimates what a real firewall would achieve. "
       "The storyboard's assumed values are reported beside the measurements and were not adjusted to match them.")
P.table("Mitigation Measured on the Controlled Test Plane (10 Repetitions, Frozen-ML Detection)",
        ["Scenario", "No defence", "Recommendation only", "Approved response", "Storyboard prior", "Δ"],
        [["DDoS, BLOCK_SOURCE", "0.00", "0.00", "**1.00 ± 0.00**", "0.82", "+0.18"],
         ["DoS, RATE_LIMIT", "0.00", "0.00", "**0.80 ± 0.00**", "0.78", "+0.02"]],
        widths=[1.6, 0.9, 1.3, 1.3, 1.1, 0.6], label="p11",
        notes="Values are measured effectiveness E from (12). Δ = measured − assumed.")
P.subsection("Engineering Performance and Security Validation")
P.para("Table XVII lists the measured operating envelope on the development machine. The vectorised models score "
       "15,000–22,000 flows per second, yet the full pipeline handles about 125 flows per second in batches of 500: "
       "per-flow enrichment and persistence, not inference, are the bottleneck. A cyber-range run of about 90 "
       "simulated seconds and 4,000–9,000 flows completes in 0.03–0.2 s once the pool is scored. These are measured "
       "points on one machine, not capacity claims.")
P.table("Measured Operating Envelope (Single Windows Desktop, 20 Threads)",
        ["Workload", "Measured value"],
        [["Single-flow prediction, no explanation", "≈ 68 flows/s; p50 ≈ 15 ms, p95 ≈ 16 ms; 0% errors"],
         ["Pipeline batch, 100 / 500 flows", "≈ 113 / ≈ 125 flows/s (wall clock)"],
         ["Vectorised DT/RF inference, 1,000–5,000 flows", "≈ 15,000–22,000 flows/s"],
         ["Zero-Day Gate, batch scoring", "≈ 0.06 ms per flow (5,000-flow batches)"],
         ["Cyber-range run (~90 simulated s)", "0.03–0.2 s; 1,190 runs in ≈ 2 min"],
         ["SHAP TreeExplainer on frozen DT", "same order as prediction (p50 ratio ≈ 0.7)"],
         ["Concurrent approval of one action", "1 of 8 concurrent approvers succeeds"]],
        widths=[2.4, 3.0], label="perf")
P.para("A final validation pass checked ten categories with automated tests: authentication and RBAC, response "
       "safety (no live mode, approval mandatory, rollback on failed verification, no automatic replay after "
       "recovery), API and input security (size limits, PCAP validation, path-traversal and filename sanitisation, "
       "rate limits, CORS allow-list, security headers), persistence and recovery, model-serving safety, simulation "
       "isolation, auditability of the mitigation experiments, audit-log integrity, documented production boundaries, "
       "and integrity of the frozen baseline. All passed; the test suite now holds 256 backend and 49 interface tests. "
       "This shows that the prototype enforces the boundaries it claims; it is not a penetration test.")

'''

DISCUSSION = r'''P.section("Discussion")
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
       "factor of seven across days and by a factor of thirty-five across datasets. A deployment should therefore "
       "monitor the realised alert rate on traffic believed to be benign and re-calibrate when it drifts, sampling "
       "the calibration flows across time. That procedure needs no labelled attacks. The range adds a second, "
       "complementary control: per-source aggregation converts a per-flow false-alarm rate into a number of incidents "
       "an analyst actually sees, and k = 3 was enough to remove false incidents entirely at a cost of at most a few "
       "seconds of latency.")
P.subsection("From Scores to Outcomes")
P.para("The range shows that once detection is fast, operational outcomes are decided by the response: which "
       "defense, how quickly it is approved, and how much collateral it causes. Isolation is the bluntest "
       "instrument—effective, but with a quarter of legitimate traffic lost and a minute of downtime in our model—while "
       "blocking or rate-limiting detected sources achieved the same containment with no collateral. A thirty-second "
       "approval delay cost more availability during a DDoS than any detector difference we measured. Responding to "
       "reconnaissance, when it is detected, prevented later stages altogether. These conclusions depend on the "
       "range's modelled capacities and costs, but their direction does not.")
P.subsection("Lessons from Building the Platform")
P.para("Four lessons seem worth passing on. Aggregate metrics conceal weak families: an F1 of 0.990 coexisted with "
       "detecting fewer than half of the web attacks on a different split, and with an F1 of 0.185 on a different "
       "network. Our own early temporal evaluation was leaky, and we found the problem only because we re-derived "
       "every split for the research study; evaluation code deserves the same review as model code. The choice of "
       "the Decision Tree for production, made on a weighted score that favoured recall, gave a model with four "
       "times the false-positive rate of XGBoost and far poorer behaviour on unseen families; with conformal "
       "calibration, a model can be chosen for its ranking quality and its operating point set separately. Finally, "
       "a simulator that only animates assumed numbers invites them to be quoted as results; replacing it with a "
       "range that measures—however simple its traffic model—changed what we could honestly claim.")

'''

THREATS = r'''P.section("Threats to Validity")
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
    "capacity are chosen parameters; flows are resampled from a finite pool of 11,665 held-out flows; and because those "
    "flows come from the detectors' own capture, detection latencies for known families are optimistic. The range "
    "measures what the detectors and controls do within this model, not on a real network.",
    "*Sampling caps and seeds.* Training, validation and test sets were capped per family. The model-family comparison "
    "used one seed. Results on uncapped data could differ, particularly for the largest families.",
    "*Design selection.* The fusion rule and novelty detector were chosen on a pilot seed excluded from reporting; "
    "hyper-parameters such as k = 5 were not tuned further.",
    "*Controlled plane.* The mitigation experiment runs in process on synthetic connection attempts, with an adapter "
    "whose behaviour partly determines the result; it says nothing about a real firewall or endpoint agent.",
])

'''

CONCLUSION = r'''P.section("Conclusion and Future Work")
P.para("We set out to give a flow-based intrusion detector a way to say \"this is an attack I do not recognise\" while "
       "keeping its false alarms at a level chosen in advance, and to measure what that changes operationally. "
       "Aegis-OSR adds a classifier's attack evidence to a benign-neighbourhood distance and calibrates the sum "
       "conformally. On CICIDS2017 it detected 70.6% of flows from withheld families at a realised 1.00% false-alarm "
       "rate, against 49.0% for the same classifier alone, labelled those alerts as unknown rather than forcing them "
       "into a known family, and flagged 29 of 47 naturally unseen attacks that the frozen detector missed entirely. "
       "The guarantee held exactly when its assumption held and failed when traffic changed: across days, "
       "re-calibration on a few thousand benign flows restored it without retraining; across networks, neither the "
       "frozen detector (F1 0.990 → 0.185) nor the gate transferred. In the trace-driven cyber range, the gate turned an "
       "undetectable zero-day scenario into one detected in about four seconds, alert aggregation removed false "
       "incidents, and the choice and timing of the human-approved response—not detection speed—decided the service "
       "outcome.")
P.para("The most pressing next steps follow from the failures: building the benign reference and calibration from "
       "the target network itself, with analyst confirmation, and testing whether that rescues cross-network "
       "detection; monitoring the realised alert rate online and re-calibrating automatically on time-spread samples; "
       "aggregating flows per host over time so that low-and-slow threats such as botnets become visible; repeating "
       "the study on UNSW-NB15, NSL-KDD, TON_IoT and re-labelled CICIDS data; replacing the replayed traffic with a "
       "packet-level range in an isolated Linux network; and a study with analysts to test whether explanations and "
       "ATT&CK context actually improve triage.")

'''

i = s.index('P.subsection("Temporal Shift")')
j = s.index('# =====================================================================================  X. DISCUSSION')
s = s[:i] + RESULTS + s[j:]
s = between(s, 'P.section("Discussion")', '# =====================================================================================  XI. THREATS', DISCUSSION)
s = between(s, 'P.section("Threats to Validity")', '# =====================================================================================  XII. CONCLUSION', THREATS)
s = between(s, 'P.section("Conclusion and Future Work")', '# =====================================================================================  BACK MATTER', CONCLUSION)
# reference [40]
s = s.replace('''    "F. Wilcoxon, \\"Individual comparisons by ranking methods,\\" *Biometrics Bull.*, vol. 1, no. 6, pp. 80–83, 1945.",
]''', '''    "F. Wilcoxon, \\"Individual comparisons by ranking methods,\\" *Biometrics Bull.*, vol. 1, no. 6, pp. 80–83, 1945.",
    "L. Liu, G. Engelen, T. Lynar, D. Essam, and W. Joosen, \\"Error prevalence in NIDS datasets: A case study on CIC-IDS-2017 and CSE-CIC-IDS-2018,\\" in *Proc. IEEE Conf. Commun. Netw. Security (CNS)*, 2022.",
]''')
assert "CNS)*, 2022" in s, "reference 40 not added"
P.write_text(s, encoding="utf-8")
print("patched part 2")
