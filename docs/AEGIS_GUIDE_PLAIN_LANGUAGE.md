# Aegis IDS — A Plain-Language Guide

*For anyone who wants to understand what this project does, how to use every screen, and what our research found — no technical background needed.*

Team: Nelluri Dolendra Sai Teja · Edla Harshavardhan · Chittuluri Naveen — Guide: R Rahul
Rajiv Gandhi University of Knowledge Technologies, Basar · Department of Computer Science and Engineering

---

## 1. Aegis in one minute

Every computer network carries a constant stream of conversations between machines: a laptop opening a website, a phone checking e-mail, a server answering requests. Most of these are normal. A few are attacks — someone guessing passwords, flooding a website until it crashes, scanning for weak spots, or a hidden program "phoning home" to a criminal's server.

**Aegis is a security guard for that stream.** It watches each conversation, decides whether it looks normal or like an attack, says *which kind* of attack, explains *why* it thinks so, estimates *how dangerous* it is, and suggests *what to do* — but it never acts on a real network without a human approving it.

What makes Aegis different from a typical student intrusion-detection project is three things:

1. **It can say "I don't recognise this attack."** Most detectors only know the attack types they were taught. Shown something new (a "zero-day"), they usually call it normal. Aegis has a second checker — the **Zero-Day Gate** — built to notice traffic that is unlike anything normal, and it does this with a **false-alarm rate you choose in advance**.
2. **It has a real practice range.** The **Cyber Range** replays real recorded network traffic, runs an attack inside a virtual network, lets the real detectors catch it, lets *you* pick the defense, and **measures** what happened — how fast the attack was caught, how much of it got through, how many normal users were hurt.
3. **It is honest about its numbers.** Every result says whether it was *measured*, *assumed* or *modelled*, and the research reports the failures as well as the successes.

---

## 2. Words you will see (glossary)

| Term | What it means in everyday words |
|---|---|
| **Network flow** | One conversation between two machines (for example, one visit to a web page), summarised as ~78 numbers: how long it lasted, how many packets went each way, how big they were, how fast they arrived. Aegis never reads the content of messages — only these measurements. |
| **Benign / normal traffic** | Ordinary, harmless conversations. |
| **Attack family** | A type of attack. Aegis knows six: **DoS** (one machine flooding a server), **DDoS** (many machines flooding at once), **PortScan** (checking which "doors" on a machine are open), **BruteForce** (guessing passwords over and over), **WebAttack** (tricking a website — SQL injection, cross-site scripting), **Bot** (an infected computer taking orders from a criminal). Two more appear only as "never-seen" examples: **Infiltration** and **Heartbleed**. |
| **IDS** | Intrusion Detection System — software that watches network traffic and raises alerts. |
| **Model / machine-learning model** | A program that learned, from millions of labelled examples, how to tell normal flows from attacks. |
| **Frozen model (v1.1)** | Our main detector, "frozen" so its behaviour and published scores never change. It works in two steps: a **Decision Tree** decides *normal or attack*, then a **Random Forest** decides *which attack family*. |
| **Zero-Day Gate (Aegis-OSR)** | Our research contribution: a second detector that can flag attacks it was never trained on. "OSR" stands for *open-set recognition*. It is **advisory** — it adds its opinion but never overrides the frozen model. |
| **Closed-set vs. open-set** | A *closed-set* detector must choose from the classes it knows (like a multiple-choice question with no "none of the above"). An *open-set* detector may answer "none of the above — this is something new". |
| **Zero-day attack** | An attack type the defender has never seen before. |
| **Alert** | The system saying "this flow looks malicious". |
| **False alarm / false positive** | An alert on normal traffic. Too many and analysts stop trusting the system. |
| **Missed attack / false negative** | An attack the system called normal. |
| **Recall (detection rate)** | Of all real attacks, the share that was caught. 90% recall = 9 in 10 attacks caught. |
| **Precision** | Of all alerts, the share that were real attacks. |
| **F1 score** | One number combining precision and recall (1.0 is perfect). |
| **False-positive rate (FPR)** | Of all normal flows, the share wrongly flagged. 1% FPR = 1 false alarm per 100 normal flows. |
| **α (alpha) — false-alarm budget** | The false-alarm rate *you* set for the Zero-Day Gate, e.g. α = 1%. The gate is designed so that, on normal traffic like what it was calibrated on, no more than α of flows raise an alert. |
| **Calibration / conformal prediction** | The statistical method that makes the α promise hold: the gate compares each new flow with a large set of known-normal flows and only alerts if the flow is more unusual than all but α of them. |
| **p-value** | The gate's "how normal is this?" score between 0 and 1. Small = very unusual. Alert when p ≤ α. |
| **SHAP / LIME** | Two methods that explain a single decision by showing which measurements pushed the model towards "attack" and which towards "normal". They explain *the model*, not *the attack*; they are hints, not proof. |
| **Counterfactual ("what-if")** | "If this measurement had been different, would the verdict change?" |
| **Risk score (0–100) and severity** | How urgent an alert is, combining the attack type, the model's confidence, how intense the traffic is and how important the targeted machine is. Bands: Low, Medium, High, Critical. |
| **Incident** | A logged alert that an analyst can investigate, annotate and close. |
| **Campaign** | Several incidents from the same source linked together (for example, a scan followed by password guessing from the same address). |
| **MITRE ATT&CK** | The industry's shared dictionary of attacker behaviour. Each tactic (goal, e.g. "Reconnaissance") and technique (method, e.g. "T1595 Active Scanning") has a code. Aegis tags every detection with one, so analysts can look it up. |
| **Kill chain** | The usual order of an attack: reconnaissance → getting in → stealing credentials → moving around → control → impact. |
| **Cyber range** | A safe practice network where attacks and defenses can be tried and measured. |
| **Seed** | A number that fixes all the randomness of a run. Same seed + same settings = exactly the same run, so results can be checked. |
| **Detection latency** | Time from the start of an attack to the moment an incident is raised. |
| **Availability** | Share of normal users' requests the server could still answer. 100% = nobody noticed the attack. |
| **Collateral damage** | Normal users blocked by a defense. |
| **Block source / Rate limit / Isolate** | Three defenses: drop everything from the attacker; let only 20% of the attacker's traffic through; cut the target server off the network. |
| **CICIDS2017 / CSE-CIC-IDS2018** | Two public, labelled collections of recorded network traffic from the Canadian Institute for Cybersecurity. We train on 2017 and test transfer to 2018. |
| **LOAFO** | "Leave-one-attack-family-out": hide one attack type during training and see whether it is caught later — our main way to simulate zero-days. |
| **Temporal split** | Train on earlier days, test on a later day — checks whether the system copes with change over time. |
| **AUROC** | A 0.5–1.0 score of how well a detector *ranks* attacks above normal traffic regardless of threshold (0.5 = coin flip). |
| **Confidence interval (CI)** | The range the true value probably lies in, e.g. "70.6% [68.9–72.3%]". |
| **Wilcoxon test / p < 0.05** | A statistical test that checks whether one method beats another consistently, not by luck. |

---

## 3. Starting the application

1. Open two terminals in the project folder `D:\IDS-Project`.
2. Terminal A (the brain): `python -m uvicorn backend.main:app --port 8000`
3. Terminal B (the screens): `cd frontend` then `npm run dev`
4. Open **http://127.0.0.1:5173** in a browser. (Or run `powershell -File scripts\start_all.ps1`, which does both.)

If a red **"Backend offline"** banner appears, Terminal A is not running — start it and press **Retry**.

---

## 4. The frame around every page

- **Left sidebar** — the menu, grouped into *Operations*, *Zero-Day Research*, *Investigate* and *Lab*. **Collapse** at the bottom shrinks it to icons. The dot at the bottom says **Models online** when the detectors are loaded.
- **Top bar, left** — where you are ("Operations › Cyber Range").
- **Search… (Ctrl K)** — opens a quick-jump box: type part of a page name ("range", "zero", "reports") and press Enter.
- **Live pill** — green **Live** means the server is pushing new incidents to your screen instantly; otherwise pages refresh every few seconds.
- **Sun/moon button** — light or dark theme.
- **Avatar (DA)** — your account. In demo mode you are "Demo analyst" with full rights; when sign-in is switched on, this is where you sign in or out.
- **Banners** — "Models not loaded" (detectors missing) or "Sign in required" (security switched on).

---

## 5. Every page, explained

### 5.1 Dashboard (Operations → Dashboard)

**What it is:** the control-room overview.

**What you see and what it tells you**
- **Incidents / Critical / High / Medium / Low tiles** — how many incidents exist at each severity, with a tiny trend line. *Click a tile* to filter the tables below to that severity; click again to clear.
- **Zero-Day Gate tile** — whether the gate is running and how many of the never-seen attacks it flags (the frozen model flags none of them). Click to open the Live Monitor.
- **Incident activity** — a chart of detections over time, coloured by severity.
- **Threat level** — a dial showing the average risk of the latest incidents.
- **Severity mix** (donut) and **Attack mix** (bars) — *click a slice or a bar* to filter.
- **Live feed** — the six newest detections, appearing in real time.
- **Recent incidents** table — click an incident ID to open it.

**Buttons:** **Pause live / Resume live** (freeze the screen while you read), **refresh icon**, **Run detection** (go to the Detection page). The bottom tiles are shortcuts to other pages.

### 5.2 Detection (Operations → Detection)

**What it is:** a test bench for the detector — give it one flow (or a file of flows) and see the full decision.

**Single flow — step by step**
1. **Flow family** — choose which kind of example to load (DDoS, DoS, PortScan, BruteForce, WebAttack, Bot, Benign).
2. **Source host (optional)** — type an address (e.g. `203.0.113.24`) if you want repeated detections from the same machine to be linked into a *campaign*. Leave it empty for a one-off test.
3. **Load sample** — fetches a real recorded flow of that type (a different one each time). Its ~78 measurements appear as editable boxes; **Show all** reveals all of them; **Filter** finds one by name. Change any number to experiment; **Reset** undoes your edits.
4. **Detect & classify** — runs the full pipeline. *This logs an incident* (a pop-up shows its ID).

**What appears after detecting**
- **Detection result** — the verdict (attack family or "Benign traffic"), a **risk dial**, severity, confidence, the probability of attack and the decision threshold (0.85). If the model is unsure, it says "analyst review recommended".
- **Zero-Day Gate (advisory)** — the gate's own opinion: *Benign*, a known family, *Unknown attack* or *Zero-day anomaly*, with its p-value on a scale against α. If the gate alerts but the main model said benign, it warns **"Possible zero-day — the frozen model missed it"**. When it alerts, it also shows *which measurements look most unusual* compared with similar normal traffic.
- **Attack-family probabilities** — how sure the model is about each family.
- **Why this risk?** — the risk score broken into its four ingredients.
- **Explainability (SHAP / LIME tabs)** — bars showing which measurements pushed towards the verdict (and which against it), plus a sentence in words.
- **Recommended defense** — the playbook's advice, why, the expected effect, the rules that fired and the MITRE ATT&CK technique. *Advisory only — nothing is changed on any network.*
- **What-if counterfactual** — "if this measurement were closer to normal, would it still be called an attack?"
- **Simulate this incident** — opens the illustrative storyboard for this incident.

**Many flows at once (Bulk & file analysis card)**
- **Score 12 demo flows** — scores twelve examples of the chosen family.
- **CSV flows** tab — drop a CSV file of flows (same columns as CICIDS2017) and choose **Quick score**, **Schema-validated** (checks the columns first) or **Background job** (queues it and shows progress).
- **PCAP capture** tab — drop a packet-capture file; Aegis converts packets to flows (needs the optional `cicflowmeter` tool, otherwise it politely refuses).
- **Batch results** — totals, the riskiest flow, how many flows the gate found novel, how many novel flows the main model *missed*, an attack-share donut and a searchable table. Batch and file scoring is *not* logged as incidents.

### 5.3 Cyber Range (Operations → Cyber Range) — *new*

**What it is:** a safe virtual network where you run a real attack, watch the real detectors, choose the defense, and get measured results.

**How it works, simply:** the range replays recorded network conversations — forty normal users plus one or more attackers — one simulated second at a time. Every conversation passes a firewall (which applies whatever defense is active), then the real detectors (frozen v1.1 and the Zero-Day Gate). If one source triggers enough alerts in a short time (default 3 alerts in 5 seconds), an incident is raised. The target server can only handle so much load, so a flood really does push normal users out. Nothing touches a real network.

**Step 1 — Set up the scenario**
- **Scenario** — nine choices: Port scanning; Host/service discovery (slow, stealthy scan); Controlled brute force; Controlled DoS; Multi-source load (DDoS, four attackers); Suspicious request burst (web attacks); Beacon-style periodic traffic (infected PC calling home); **Zero-day intrusion** (attack types neither model was trained on); Multi-stage campaign (scan → password guessing → web exploitation → botnet).
- **Attack intensity** — Low / Medium / High (half, normal or double attack speed).
- **Detector raising incidents** — *Both* (default), *Frozen v1.1 only* or *Zero-Day Gate only*. Try the zero-day scenario with "Frozen v1.1 only": the attack is never detected.
- **Who responds** — **I decide** (the clock stops when an incident is raised and waits for your choice) or **Automatic playbook** (choose a defense and an *approval delay* in seconds — how long a human takes to approve).
- **Alerts to raise incident** — fewer = faster detection but more false incidents on normal users.
- **Seed** — keep it the same to replay exactly the same run; change it for a different but comparable run.
- **Start run**.

**Step 2 — Watch it unfold**
- **Play / Pause**, **speed (1×, 2×, 4×)**, **+1 s**, **+10 s**, **Run to end**.
- Badges show the **clock**, what the **attacker** is doing right now (the ground truth: normal, preparation, reconnaissance, attack initiated, attack active, attack ended) and the **SOC state**.
- The **state bar** shows the defender's progress: Normal → Suspicious (first alert on an attacker) → Detected (incident raised) → Explained (SHAP ready) → Response options → Mitigating (defense active) → Contained (attack traffic reaching the server cut by at least 75%) → Recovery (service back to normal) → Completed. Hover over a state for its meaning.

**Step 3 — Your decision** (only in "I decide" mode)
A red panel appears with the threat-intelligence tag (MITRE ATT&CK tactic and technique, clickable) and six buttons. The **recommended** one is highlighted:
- **Block source** — drop everything from each detected attacker.
- **Rate limit** — let only 20% of each detected attacker's traffic through.
- **Isolate target** — cut the server off until the attack has been quiet for 5 seconds (stops the attack, but normal users are cut off too).
- **Monitor only** — watch, change nothing.
- **Increase inspection** — use both detectors and alert on a single hit, without blocking.
- **No action** — ignore the alert.

**Reading the results**
- **Tiles:** Detection latency · Time to mitigate · Service availability (now, and the worst moment) · Attack getting through · False alarms (and false incidents on normal users) · Users blocked (collateral damage).
- **Network** — the virtual network: attackers (red when caught, marked *Blocked* when blocked), Internet, Firewall, IDS sensor, core switch, the target server (with live availability) and the 40 clients. Lines show traffic: red = malicious, orange = blocked, green = filtered.
- **Why the incident was raised** — SHAP bars for the flow that triggered the incident, with the real values. For a zero-day incident it explains that the gate (not the frozen model) raised it.
- **Service availability** chart — the share of normal requests answered each second, with markers for *attack*, *detected* and *defense*.
- **Traffic at the firewall** chart — attack traffic sent vs. getting through, normal users blocked, false alerts.
- **Event log** — every change as a numbered, time-stamped event (incident raised, defense applied, attack contained, service recovered…). A **"FALSE ALARM: normal user"** entry means a normal machine was wrongly flagged.
- **Latest flows** — the newest conversations: who sent them, what they really were, whether the firewall passed them, and what each detector said.
- **Result card** (at the end) — the outcome in words, attackers caught, detection rate of each model, availability, recovery time and mitigation effectiveness. The full record is saved in `results/cyber_range/runs/`.

**Experiments tab**
- **Compare defenses** — pick a scenario and press the button: the range runs every defense five times and shows a table of attack getting through, availability, users blocked and recovery time.
- Below it, the saved **full experiment program** (1,190 runs): *Which detector catches what*, *Defense comparison*, *False-alarm control* (alerts needed vs. false incidents) and *Cost of a slow decision* (approval delay vs. availability). To regenerate: `python scripts/56_cyber_range_experiments.py`.

### 5.4 Attack Storyboard (Operations → Attack Storyboard)

**What it is:** an *illustrative* step-by-step animation for teaching (normal → attack → impact → detect → recommend → defend → recover). It does **not** generate traffic, and the defense effectiveness it shows (e.g. 82% for DDoS) is an **assumed** value. For measured results, use the Cyber Range — the page says so at the top.

**Buttons:** choose the attack and intensity, **Run simulation**, **Play/Pause**, speed, **Step**, **Apply defense**, **Reset**; previous sessions can be replayed from the history list.

### 5.5 Live Monitor (Zero-Day Research → Live Monitor)

**What it is:** a never-ending stream of replayed real flows scored by *both* detectors side by side, to show what the Zero-Day Gate adds.

- **Scenario buttons** — Enterprise workday; DDoS wave; **Zero-day intrusion** (never-seen attack types hidden in normal traffic); Multi-stage campaign. Each shows its phases and which one is playing.
- **Replay rate** slider — flows per second (1–200).
- **Pause / Resume / Reset**.
- **Tiles:** throughput, flows scored, frozen-model recall, gate recall, combined recall, zero-day hits (caught only by the gate).
- **Never-seen attack families** — the key comparison: how many Infiltration/Heartbleed flows each detector caught. (Frozen model: essentially none; gate: a large share.)
- **Throughput** chart, **Outcomes** bars (caught by both / frozen only / gate only / missed / false alarms), **Detection rate per family**.
- **Zero-day alerts** list and **Flow feed** table — click any row to open a drawer with both verdicts and the evidence. Filters: All, Any alert, Gate-only, Unseen families; **Hold** freezes the feed.
- Addresses are invented for display; the traffic itself is recorded, not live capture.

### 5.6 Zero-Day Lab (Zero-Day Research → Zero-Day Lab)

**What it is:** a look inside the Zero-Day Gate.

- **How the gate decides** — a picture of the five steps: measure the flow → ask the classifier "how attack-like?" → ask "how far from the nearest normal flows?" → add the two kinds of evidence → compare with known-normal traffic to get a p-value → label it.
- **Tiles:** α budget, real false-alarm rate on normal traffic, recall on known attacks, alert rate on never-seen attacks, family accuracy, speed per flow.
- **Try a flow** — choose a family, press **Load & assess**, and see the frozen verdict beside the gate's verdict with its evidence.
- **False-alarm budget α slider** — move it and watch the same flow get re-judged. Smaller α = fewer false alarms but some attacks slip through.
- **Charts:** *False-alarm guarantee* (the real false-alarm rate stays on or under the promised line), *What α buys* (catch rate vs. α), *Per-family recall*.
- **Never-seen families** table — the 47 Infiltration and Heartbleed flows: the frozen model flagged 0, the gate flagged 29.

### 5.7 Research Lab (Zero-Day Research → Research Lab)

**What it is:** all the research results, with confidence intervals and significance tests.

- **Tabs:** Overview · LOAFO (hide one attack type) · Temporal (train on early days, test on later) · Cross-dataset (2017 → 2018) · Zero-Day Gate.
- Each protocol tab shows: the question being tested; *Zero-day recall by method* with error bars; *All metrics*; heat-maps by attack type; *adaptation* charts (how a quick re-calibration on a few normal flows from the new day brings false alarms back down); *Paired significance* (does Aegis-OSR beat each rival consistently?); *Where do unknowns go?* (flagged as unknown, wrongly given a known label, or missed as normal).

### 5.8 Reports (Investigate → Reports)

**What it is:** the register of all incidents.

- **CSV / JSON / PDF report** buttons download the registry.
- Tiles, an attack-distribution donut and a lifecycle-status chart (*click to filter*), and detections over time.
- **Incident registry** table — search box and filters (severity, attack, status, campaign); click an incident to open it; the **Advance** drop-down moves an incident to its next status (e.g. Detected → Triaged → Investigating → Mitigation recommended → Defense applied → Monitoring → Resolved, or *False positive*).

### 5.9 Incident page (open any incident)

**What it is:** the analyst's workspace for one incident.

- Risk dial, attack type, severity, status, campaign link, confidence, source.
- **Move to:** buttons — change the status (each change is recorded with who and when).
- **Controlled response** — **Propose response** → **Dry run** (preview, changes nothing) → **Approve & execute** (runs it on the *controlled test adapter only*, then verifies it) or **Reject** → **Rollback** (undo). Only roles with permission can approve. An **audit trail** lists every step.
- **Investigation** — write **Analyst notes** and the **Defense action** taken, then **Save investigation** (this now works in every state, including closed incidents).
- **Decision trace** and **Lifecycle events** — the full story of the incident.
- **Simulate** — open it in the storyboard.

### 5.10 Campaigns (Investigate → Campaigns)

**What it is:** incidents linked because they came from the same source.

- Left: a searchable list of campaigns. Right: the selected campaign's incidents, maximum risk, its **attack progression** (e.g. PortScan → BruteForce → WebAttack) with the matching kill-chain stages, a risk chart, and **Simulate progression**.
- Campaigns are created only when a detection carries a source (the *Source host* box on the Detection page), so the list is empty until you use it.

### 5.11 Models (Lab → Models)

**What it is:** the "spec sheet" of the frozen detector.

- **Overview** — which models are deployed, features used, training date and data sizes.
- **Performance** — how the four candidate models (logistic regression, decision tree, random forest, XGBoost) compared, the confusion matrix (right vs. wrong decisions), test scores.
- **Explainability** — which measurements matter most overall and for each attack type.
- **Drift & experiments** — whether the incoming data looks different from the training data (PSI scores; ≥ 0.2 means a notable shift) and the list of experiment files.

### 5.12 Baseline study (Lab → Baseline study v1.1)

The design decisions behind the frozen detector (why a Decision Tree, why threshold 0.85, why calibration is off…), its test metrics and a checklist of experiments with their evidence files.

### 5.13 System (Lab → System)

The health of the platform itself: is the database, model store, job queue and file system ready; request counts and response times; security counters (failed logins, blocked requests, rate-limited requests); response-action counters; and any active operational alerts. Refreshes every 8 seconds.

### 5.14 Login

Only used when security is switched on. Enter username and password; the server — not the screen — decides what each role may do (viewer: look; analyst: propose and dry-run; responder/admin: approve and roll back).

---

## 6. A ten-minute demonstration

1. **Dashboard** — show the overview; point out the Zero-Day Gate tile.
2. **Detection** — load a *DDoS* sample, press *Detect & classify*; show the verdict, the risk breakdown, the SHAP bars, the ATT&CK tag and the advisory recommendation.
3. **Zero-Day Lab** — load a flow and move the α slider; show the false-alarm guarantee chart and the never-seen table (0 of 47 vs. 29 of 47).
4. **Cyber Range** — choose *Multi-source load (DDoS)*, "I decide", Start. Let the attack begin; when the decision panel appears, choose *Block source*; Run to end. Read the tiles: caught in about one second, availability restored, zero users blocked.
5. **Cyber Range again** — choose *Zero-day intrusion* with detector *Frozen v1.1 only*: the attack is never detected. Switch to *Both*: the gate catches it in a few seconds. This is the research in one picture.
6. **Experiments tab** — press *Compare defenses* to show that isolating the server stops the attack but locks out about a quarter of normal users.
7. **Research Lab** — show the LOAFO headline (70.6% vs. 49.0%) and the honest cross-dataset failure.

---

## 7. What our research is — in plain words

### 7.1 The problem

Machine-learning intrusion detectors are usually tested on the same kind of traffic they learned from, and they score superbly (F1 ≈ 0.99). We showed three ways that hides the real picture:

1. **New attack types are invisible.** Our own frozen detector scored F1 0.990 on its test set, yet it flagged **none** of the 47 never-seen attacks in the data. When we hid one attack type at a time during training, we tested ten ordinary detectors — decision trees, random forests, XGBoost, LightGBM-style boosting, SVMs and neural networks (MLP, CNN, LSTM). On familiar attacks they all looked excellent (most scored F1 above 0.98). On the hidden type, the best of them caught only **48%** on average, the neural networks only 5–35%, and **none of the ten caught a single hidden botnet flow**. Some hidden types are "lucky" (a hidden DoS looks a lot like other floods, so tree models still caught 90%+), but you cannot know in advance which kind of new attack you will get.
2. **A different network breaks it.** Tested on the 2018 dataset (different network, different year), the same detector's F1 fell from **0.990 to 0.185** — it caught only about 10% of attacks, missing 2018's DDoS, botnet and SSH password-guessing traffic almost entirely.
3. **Alarm rates are not under control.** Anomaly detectors can catch new things, but nobody can say in advance how many false alarms they will produce.

### 7.2 Our idea — Aegis-OSR (the Zero-Day Gate)

Combine two kinds of evidence and put a statistical guarantee on top:

- *"How attack-like is it?"* — from a classifier that knows the attack types.
- *"How far is it from anything normal?"* — distance to the five most similar normal flows.

Each is turned into a "surprise" score using thousands of known-normal flows; the two surprises are **added** (so being somewhat strange to both counts more than being slightly strange to one), and the total is converted into a p-value by **conformal calibration** — which makes the false-alarm rate equal to the budget α you choose, as long as tomorrow's normal traffic resembles the calibration traffic. A second test then decides whether an alert matches a known attack family or should be reported honestly as **"unknown attack"**.

### 7.3 What we found (the evidence)

| Question | Result |
|---|---|
| Does it catch unseen attack types? (6 types × 5 repeats = 30 tests) | **70.6%** caught vs. **49.0%** for the same classifier alone and **24.1%** for a decision tree like v1.1 — at the same 1% false-alarm rate. It won **30 out of 30** head-to-head comparisons (p = 1.9×10⁻⁹). |
| Is the false-alarm promise kept? | Yes on matching traffic: measured **1.00%** for a promised 1%, for every method. |
| Does it label unknowns honestly? | When it alerted on an unseen type it almost never pretended it was a known one (≤ 0.9% mislabelled). |
| Which unseen types? | Web attacks 99%, DoS 98%, DDoS 97%, brute force **92% (vs. 31% without the gate)**; port scans 36%; botnet only 2% — botnet traffic looks like normal web browsing. |
| Real never-seen attacks (Heartbleed, Infiltration) | Frozen model **0 of 47**; gate **29 of 47** (all 11 Heartbleed). |
| When traffic changes day to day | The promise breaks: Friday's false-alarm rate rises to **~7%**. Re-calibrating on **2,000 normal flows** from the new day — **no retraining** — brings it back near 1% (0.82%; with a random sample of the day, 0.97%). After re-calibration the gate and the plain classifier perform about the same on Friday. |
| On a different network (2018) | **It does not transfer.** False alarms jump to ~35%; re-calibration controls false alarms but then little is caught. We report this openly as the method's main limit. |
| In the Cyber Range (1,190 measured runs) | Zero-day scenario: frozen model **never** raised an incident (0/10 runs); the gate did in **10/10**, after **4.3 s** on average. Requiring 3 alerts in 5 s instead of 1 cut false incidents from **~18 per run to 0**. Blocking the source stopped attacks with no harm to users; isolating the server also stopped them but locked out **27%** of normal users and took **~52 s** to recover. A 30-second approval delay dropped availability during a DDoS from **99.5% to 62%**. |
| Are explanations trustworthy? | SHAP explanations barely change under tiny noise for most attack types — except Bot and WebAttack, exactly the types the detector is weakest on. SHAP and LIME often disagree, so explanations should be treated as hints, not proof. |

### 7.4 Where we improved on typical projects

- **Unknown attacks** — instead of only reporting accuracy on known attacks, we built and statistically tested a detector for unseen ones.
- **Chosen false-alarm rate** — the operator sets the alarm budget; every method is compared at the same budget, so comparisons are fair.
- **A measuring cyber range, not an animation** — detection time, damage and the effect of each defense are measured, with seeds for exact replay.
- **Human in control** — no defense runs on a real network; every response is proposed, previewed, approved, verified and reversible.
- **Honesty** — failures (botnet, cross-network transfer, drift) are reported next to successes; measured, modelled and assumed numbers are labelled separately.
- **Threat-intelligence language** — every detection carries its MITRE ATT&CK tactic and technique; campaigns are summarised as kill-chain stages.

---

## 8. Where the research can go next

These are the most promising directions, in order of expected impact:

1. **Make the gate transfer across networks.** The 2018 result shows the "normal" reference must come from the new network. Next step: build the normal reference and calibration from the first hours of a new network (with analyst confirmation), and test domain-adaptation of the feature scaling.
2. **Watch the false-alarm rate continuously.** Because the promise breaks under drift, add an automatic monitor that re-calibrates whenever the measured alarm rate on confirmed-normal traffic leaves the budget — the experiments already show a random sample of ~2,000 flows is enough.
3. **Look at hosts, not single flows.** Botnet and port-scan traffic look normal one flow at a time. Grouping flows per host over minutes (timing regularity, number of destinations) should expose them; the Cyber Range's beacon and host-discovery scenarios are ready to test this.
4. **A packet-level range.** Replace replayed flows with packets generated in an isolated Linux network (Mininet, as originally planned) so attacks can vary in ways the datasets do not contain.
5. **More datasets.** Repeat the study on UNSW-NB15, NSL-KDD and TON_IoT (listed in our proposal) and on re-labelled versions of CICIDS2017, which fixes known labelling errors.
6. **A human study.** Ask analysts to triage alerts with and without explanations and ATT&CK tags, and measure speed and accuracy — the only real test of whether explanations help.
7. **Safe language-model assistance.** Let a language model write scenario descriptions or post-incident summaries, but only through validated templates — never direct control of a network.

### What was added in this round of work

- The **Cyber Range** (trace-driven, measured, reproducible) with nine scenarios, five defenses, an experiment engine and 1,190 runs of results.
- The **5-seed temporal study** and the **cross-dataset study** on CSE-CIC-IDS2018, plus the frozen detector's 2018 score.
- The **explanation stability study** (E9).
- The **model-family comparison** (SVM, LightGBM-style boosting, MLP, CNN, LSTM vs. the four original models) on seen and unseen attacks.
- **MITRE ATT&CK** tagging of detections and kill-chain summaries of campaigns.
- Bug fixes: saving analyst notes, real-time incident notifications, campaign correlation, repeated demo samples, the 50-incident limit on Reports, the Live Monitor "Connecting…" state, misleading labels, and a missing browser icon.
