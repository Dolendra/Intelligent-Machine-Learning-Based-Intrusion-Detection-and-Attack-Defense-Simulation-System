# Cyber range — experiment results (auto-generated)

_Generated 2026-11-10T11:06:41+00:00 by `scripts/56_cyber_range_experiments.py`. Seeds 1–10 (10 per cell); brackets are 95% t-intervals over seeds._

The range replays recorded CICIDS2017 flows on a seeded 1-second clock. Detector verdicts are computed by the frozen v1.1 model and the Aegis-OSR gate; an incident is raised after 3 alerts from one source within 5 s; responses change which later flows reach the target. **Modelled, not measured:** arrival rates, per-family service cost of a flow, the 20% rate-limit pass-through, and target capacity (60 units/s).

## E8 — Defense comparison (all scenarios, auto mode, 3 s approval delay)

Mean over the nine scenarios:

| Defense | Attack success after defense | Availability (mean, attack) | Availability (min, attack) | Benign collateral | Recovery time (s) |
|---|---|---|---|---|---|
| Block source | 0.000 | 0.998 | 0.964 | 0.000 | 2.6 |
| Rate limit | 0.197 | 0.996 | 0.962 | 0.000 | 3.6 |
| Isolate target | 0.000 | 0.108 | 0.000 | 0.274 | 52.4 |
| Monitor only | — | 0.897 | 0.847 | 0.000 | — |
| Increase inspection | 1.000 | 0.897 | 0.847 | 0.000 | 47.4 |

Per scenario:

| Scenario | Defense | Detection latency (s) | Attack success after | Availability (attack) | Collateral | Recovery (s) |
|---|---|---|---|---|---|---|
| Port scanning | Block source | 0.2 [0.0, 0.5] | 0.000 | 1.000 | 0.000 | 2.6 [2.2, 3.0] |
| Port scanning | Rate limit | 0.2 [0.0, 0.5] | 0.199 [0.184, 0.214] | 1.000 | 0.000 | 3.2 [1.9, 4.5] |
| Port scanning | Isolate target | 0.2 [0.0, 0.5] | 0.000 | 0.091 [0.085, 0.098] | 0.274 [0.267, 0.280] | 49.8 [49.5, 50.1] |
| Port scanning | Monitor only | 0.2 [0.0, 0.5] | — | 1.000 | 0.000 | — |
| Port scanning | Increase inspection | 0.2 [0.0, 0.5] | 1.000 | 1.000 | 0.000 | 44.8 [44.5, 45.1] |
| Host / service discovery | Block source | 2.4 [0.9, 3.9] | 0.000 | 1.000 | 0.000 | 2.5 [2.1, 2.9] |
| Host / service discovery | Rate limit | 2.4 [0.9, 3.9] | 0.190 [0.168, 0.213] | 1.000 | 0.000 | 3.0 [2.1, 3.9] |
| Host / service discovery | Isolate target | 2.4 [0.9, 3.9] | 0.000 | 0.125 [0.096, 0.154] | 0.271 [0.263, 0.279] | 52.6 [51.1, 54.1] |
| Host / service discovery | Monitor only | 2.4 [0.9, 3.9] | — | 1.000 | 0.000 | — |
| Host / service discovery | Increase inspection | 2.4 [0.9, 3.9] | 1.000 | 1.000 | 0.000 | 47.6 [46.1, 49.1] |
| Controlled brute force | Block source | 0.8 [0.5, 1.1] | 0.000 | 1.000 | 0.000 | 2.6 [2.2, 3.0] |
| Controlled brute force | Rate limit | 0.8 [0.5, 1.1] | 0.196 [0.177, 0.214] | 1.000 | 0.000 | 4.0 [2.7, 5.3] |
| Controlled brute force | Isolate target | 0.8 [0.5, 1.1] | 0.000 | 0.089 [0.083, 0.094] | 0.284 [0.278, 0.290] | 57.2 [56.9, 57.5] |
| Controlled brute force | Monitor only | 0.8 [0.5, 1.1] | — | 1.000 | 0.000 | — |
| Controlled brute force | Increase inspection | 0.8 [0.5, 1.1] | 1.000 | 1.000 | 0.000 | 52.2 [51.9, 52.5] |
| Controlled DoS | Block source | 0.1 [0.0, 0.3] | 0.000 | 1.000 | 0.000 | 2.7 [2.4, 3.0] |
| Controlled DoS | Rate limit | 0.1 [0.0, 0.3] | 0.203 [0.196, 0.211] | 1.000 [0.999, 1.000] | 0.000 | 3.9 [2.6, 5.2] |
| Controlled DoS | Isolate target | 0.1 [0.0, 0.3] | 0.000 | 0.076 [0.072, 0.080] | 0.294 [0.287, 0.301] | 57.9 [57.7, 58.1] |
| Controlled DoS | Monitor only | 0.1 [0.0, 0.3] | — | 0.663 [0.654, 0.673] | 0.000 | — |
| Controlled DoS | Increase inspection | 0.1 [0.0, 0.3] | 1.000 | 0.663 [0.654, 0.673] | 0.000 | 52.9 [52.7, 53.1] |
| Multi-source load (DDoS) | Block source | 0.0 | 0.000 | 0.980 [0.976, 0.984] | 0.000 | 2.8 [2.5, 3.1] |
| Multi-source load (DDoS) | Rate limit | 0.0 | 0.201 [0.194, 0.207] | 0.966 [0.962, 0.971] | 0.000 | 3.2 [2.7, 3.7] |
| Multi-source load (DDoS) | Isolate target | 0.0 | 0.000 | 0.067 [0.063, 0.071] | 0.273 [0.265, 0.280] | 50.0 |
| Multi-source load (DDoS) | Monitor only | 0.0 | — | 0.410 [0.403, 0.417] | 0.000 | — |
| Multi-source load (DDoS) | Increase inspection | 0.0 | 1.000 | 0.410 [0.403, 0.417] | 0.000 | 45.0 |
| Suspicious request burst | Block source | 2.6 [0.6, 4.6] | 0.000 | 1.000 | 0.000 | 2.7 [2.4, 3.0] |
| Suspicious request burst | Rate limit | 2.6 [0.6, 4.6] | 0.194 [0.175, 0.214] | 1.000 | 0.000 | 3.4 [2.0, 4.8] |
| Suspicious request burst | Isolate target | 2.6 [0.6, 4.6] | 0.000 | 0.122 [0.085, 0.160] | 0.278 [0.267, 0.289] | 55.4 [53.4, 57.4] |
| Suspicious request burst | Monitor only | 2.6 [0.6, 4.6] | — | 1.000 | 0.000 | — |
| Suspicious request burst | Increase inspection | 2.6 [0.6, 4.6] | 1.000 | 1.000 | 0.000 | 50.4 [48.4, 52.4] |
| Beacon-style periodic traffic | Block source | 2.4 [0.9, 3.9] | 0.000 | 1.000 | 0.000 | 2.5 [2.1, 2.9] |
| Beacon-style periodic traffic | Rate limit | 2.4 [0.9, 3.9] | 0.187 [0.165, 0.210] | 1.000 | 0.000 | 3.0 [2.1, 3.9] |
| Beacon-style periodic traffic | Isolate target | 2.4 [0.9, 3.9] | 0.000 | 0.139 [0.107, 0.171] | 0.258 [0.249, 0.266] | 47.6 [46.1, 49.1] |
| Beacon-style periodic traffic | Monitor only | 2.4 [0.9, 3.9] | — | 1.000 | 0.000 | — |
| Beacon-style periodic traffic | Increase inspection | 2.4 [0.9, 3.9] | 1.000 | 1.000 | 0.000 | 42.5 [41.1, 43.9] |
| Zero-day intrusion (never-seen families) | Block source | 4.3 [2.6, 6.0] | 0.000 | 1.000 | 0.000 | 2.5 [2.1, 2.9] |
| Zero-day intrusion (never-seen families) | Rate limit | 4.3 [2.6, 6.0] | 0.202 [0.188, 0.216] | 1.000 | 0.000 | 4.5 [2.0, 7.0] |
| Zero-day intrusion (never-seen families) | Isolate target | 4.3 [2.6, 6.0] | 0.000 | 0.180 [0.143, 0.218] | 0.249 [0.240, 0.258] | 45.7 [44.0, 47.4] |
| Zero-day intrusion (never-seen families) | Monitor only | 4.3 [2.6, 6.0] | — | 1.000 | 0.000 | — |
| Zero-day intrusion (never-seen families) | Increase inspection | 4.3 [2.6, 6.0] | 1.000 | 1.000 | 0.000 | 40.5 [38.8, 42.2] |
| Multi-stage campaign | Block source | 0.3 [0.0, 0.6] | 0.000 | 1.000 | 0.000 | 2.3 [2.0, 2.6] |
| Multi-stage campaign | Rate limit | 0.3 [0.0, 0.6] | 0.199 [0.179, 0.220] | 1.000 | 0.000 | 4.1 [2.4, 5.8] |
| Multi-stage campaign | Isolate target | 0.3 [0.0, 0.6] | 0.000 | 0.083 [0.076, 0.089] | 0.286 [0.279, 0.293] | 55.7 [55.4, 56.0] |
| Multi-stage campaign | Monitor only | 0.3 [0.0, 0.6] | — | 1.000 | 0.000 | — |
| Multi-stage campaign | Increase inspection | 0.3 [0.0, 0.6] | 1.000 | 1.000 | 0.000 | 50.7 [50.4, 51.0] |

## Detector comparison — which model raises the incident

| Scenario | Detector | Detected (share of runs) | Detection latency (s) | Attack-flow recall | Benign flow FPR | False incidents |
|---|---|---|---|---|---|---|
| Port scanning | frozen | 1.00 | 0.2 [0.0, 0.5] | 1.000 | 0.081% [0.049%, 0.113%] | 0.00 |
| Port scanning | gate | 1.00 | 0.2 [0.0, 0.5] | 1.000 | 0.750% [0.651%, 0.849%] | 0.00 |
| Port scanning | union | 1.00 | 0.2 [0.0, 0.5] | 1.000 | 0.803% [0.697%, 0.909%] | 0.10 [0.00, 0.33] |
| Host / service discovery | frozen | 1.00 | 2.4 [0.9, 3.9] | 1.000 | 0.073% [0.048%, 0.098%] | 0.00 |
| Host / service discovery | gate | 1.00 | 2.4 [0.9, 3.9] | 1.000 | 0.830% [0.777%, 0.883%] | 0.00 |
| Host / service discovery | union | 1.00 | 2.4 [0.9, 3.9] | 1.000 | 0.866% [0.819%, 0.913%] | 0.00 |
| Controlled brute force | frozen | 1.00 | 0.8 [0.5, 1.1] | 1.000 | 0.086% [0.049%, 0.123%] | 0.00 |
| Controlled brute force | gate | 1.00 | 0.8 [0.5, 1.1] | 1.000 | 0.810% [0.715%, 0.905%] | 0.00 |
| Controlled brute force | union | 1.00 | 0.8 [0.5, 1.1] | 1.000 | 0.868% [0.777%, 0.959%] | 0.00 |
| Controlled DoS | frozen | 1.00 | 0.1 [0.0, 0.3] | 1.000 | 0.081% [0.051%, 0.111%] | 0.00 |
| Controlled DoS | gate | 1.00 | 0.1 [0.0, 0.3] | 1.000 | 0.772% [0.680%, 0.864%] | 0.00 |
| Controlled DoS | union | 1.00 | 0.1 [0.0, 0.3] | 1.000 | 0.816% [0.718%, 0.914%] | 0.00 |
| Multi-source load (DDoS) | frozen | 1.00 | 0.0 | 1.000 | 0.061% [0.033%, 0.089%] | 0.00 |
| Multi-source load (DDoS) | gate | 1.00 | 0.0 | 1.000 | 0.775% [0.652%, 0.898%] | 0.00 |
| Multi-source load (DDoS) | union | 1.00 | 0.0 | 1.000 | 0.810% [0.679%, 0.941%] | 0.00 |
| Suspicious request burst | frozen | 1.00 | 2.6 [0.6, 4.6] | 0.866 [0.710, 1.000] | 0.104% [0.064%, 0.144%] | 0.00 |
| Suspicious request burst | gate | 1.00 | 2.6 [0.6, 4.6] | 1.000 | 0.883% [0.780%, 0.986%] | 0.00 |
| Suspicious request burst | union | 1.00 | 2.6 [0.6, 4.6] | 1.000 | 0.951% [0.864%, 1.038%] | 0.00 |
| Beacon-style periodic traffic | frozen | 1.00 | 3.4 [1.7, 5.1] | 0.714 [0.627, 0.801] | 0.067% [0.042%, 0.092%] | 0.00 |
| Beacon-style periodic traffic | gate | 1.00 | 2.4 [0.9, 3.9] | 0.945 [0.888, 1.000] | 0.862% [0.778%, 0.946%] | 0.00 |
| Beacon-style periodic traffic | union | 1.00 | 2.4 [0.9, 3.9] | 0.956 [0.914, 0.998] | 0.884% [0.796%, 0.972%] | 0.00 |
| Zero-day intrusion (never-seen families) | frozen | 0.00 | — | 0.000 | 0.064% [0.044%, 0.084%] | 0.00 |
| Zero-day intrusion (never-seen families) | gate | 1.00 | 4.3 [2.6, 6.0] | 0.645 [0.584, 0.706] | 0.847% [0.778%, 0.916%] | 0.00 |
| Zero-day intrusion (never-seen families) | union | 1.00 | 4.3 [2.6, 6.0] | 0.645 [0.584, 0.706] | 0.869% [0.803%, 0.935%] | 0.00 |
| Multi-stage campaign | frozen | 1.00 | 0.3 [0.0, 0.6] | 1.000 | 0.055% [0.022%, 0.088%] | 0.00 |
| Multi-stage campaign | gate | 1.00 | 0.3 [0.0, 0.6] | 1.000 | 0.757% [0.639%, 0.875%] | 0.00 |
| Multi-stage campaign | union | 1.00 | 0.3 [0.0, 0.6] | 1.000 | 0.793% [0.673%, 0.913%] | 0.00 |

## E3 — Alert threshold k (alerts from one source within 5 s)

| Scenario | k | Detected | Detection latency (s) | False incidents |
|---|---|---|---|---|
| Controlled DoS | 1 | 1.00 | 0.0 | 18.20 [16.86, 19.54] |
| Controlled DoS | 2 | 1.00 | 0.0 | 0.60 [0.23, 0.97] |
| Controlled DoS | 3 | 1.00 | 0.1 [0.0, 0.3] | 0.00 |
| Controlled DoS | 5 | 1.00 | 0.7 [0.2, 1.2] | 0.00 |
| Controlled DoS | 8 | 1.00 | 0.9 [0.5, 1.3] | 0.00 |
| Controlled brute force | 1 | 1.00 | 0.2 [0.0, 0.5] | 18.80 [16.99, 20.61] |
| Controlled brute force | 2 | 1.00 | 0.3 [0.0, 0.6] | 0.80 [0.35, 1.25] |
| Controlled brute force | 3 | 1.00 | 0.8 [0.5, 1.1] | 0.00 |
| Controlled brute force | 5 | 1.00 | 1.8 [1.1, 2.5] | 0.00 |
| Controlled brute force | 8 | 1.00 | 3.5 [2.4, 4.6] | 0.00 |
| Beacon-style periodic traffic | 1 | 1.00 | 1.2 [0.0, 2.5] | 17.00 [15.45, 18.55] |
| Beacon-style periodic traffic | 2 | 1.00 | 2.2 [0.6, 3.8] | 0.70 [0.02, 1.38] |
| Beacon-style periodic traffic | 3 | 1.00 | 2.4 [0.9, 3.9] | 0.00 |
| Beacon-style periodic traffic | 5 | 1.00 | 3.8 [2.5, 5.1] | 0.00 |
| Beacon-style periodic traffic | 8 | 1.00 | 7.1 [4.9, 9.3] | 0.00 |
| Host / service discovery | 1 | 1.00 | 1.2 [0.0, 2.5] | 17.90 [16.66, 19.14] |
| Host / service discovery | 2 | 1.00 | 2.1 [0.5, 3.7] | 0.80 [0.14, 1.46] |
| Host / service discovery | 3 | 1.00 | 2.4 [0.9, 3.9] | 0.00 |
| Host / service discovery | 5 | 1.00 | 3.5 [2.2, 4.8] | 0.00 |
| Host / service discovery | 8 | 1.00 | 6.8 [4.9, 8.7] | 0.00 |

## E6 — Attack intensity (recommended defense)

| Scenario | Intensity | Detection latency (s) | Min availability | Attack success after |
|---|---|---|---|---|
| Port scanning | 0.5× | 0.6 [0.2, 1.0] | 1.000 | 0.000 |
| Port scanning | 1.0× | 0.2 [0.0, 0.5] | 1.000 | 0.000 |
| Port scanning | 2.0× | 0.0 | 1.000 | 0.000 |
| Controlled brute force | 0.5× | 2.7 [0.7, 4.7] | 1.000 | 0.023 [0.000, 0.073] |
| Controlled brute force | 1.0× | 0.8 [0.5, 1.1] | 1.000 | 0.000 |
| Controlled brute force | 2.0× | 0.3 [0.0, 0.6] | 1.000 | 0.000 |
| Controlled DoS | 0.5× | 0.5 [0.1, 0.9] | 1.000 | 0.000 |
| Controlled DoS | 1.0× | 0.1 [0.0, 0.3] | 1.000 | 0.000 |
| Controlled DoS | 2.0× | 0.0 | 1.000 | 0.000 |
| Multi-source load (DDoS) | 0.5× | 0.2 [0.0, 0.5] | 0.933 [0.867, 0.999] | 0.001 [0.000, 0.002] |
| Multi-source load (DDoS) | 1.0× | 0.0 | 0.679 [0.611, 0.747] | 0.000 |
| Multi-source load (DDoS) | 2.0× | 0.0 | 0.365 [0.344, 0.387] | 0.000 |
| Suspicious request burst | 0.5× | 4.4 [2.5, 6.3] | 1.000 | 0.000 |
| Suspicious request burst | 1.0× | 2.6 [0.6, 4.6] | 1.000 | 0.000 |
| Suspicious request burst | 2.0× | 0.5 [0.1, 0.9] | 1.000 | 0.000 |

## E7 — Number of DDoS sources (block source)

| Sources | Sources detected | Detection latency (s) | Attack success after defense | Min availability |
|---|---|---|---|---|
| 1 | 1.00 | 0.4 [0.0, 0.8] | 0.0000 | 1.000 |
| 2 | 2.00 | 0.1 [0.0, 0.3] | 0.0000 | 0.952 [0.888, 1.000] |
| 4 | 4.00 | 0.0 | 0.0000 | 0.679 [0.611, 0.747] |
| 8 | 8.00 | 0.0 | 0.0000 | 0.365 [0.340, 0.390] |

## Analyst approval delay

| Scenario | Approval delay (s) | Time to mitigate (s) | Availability (attack) | Attack success after defense |
|---|---|---|---|---|
| Controlled DoS | 0 | 0.0 | 1.000 | 0.000 |
| Controlled DoS | 3 | 3.0 | 1.000 | 0.000 |
| Controlled DoS | 10 | 10.0 | 0.998 [0.996, 1.000] | 0.000 |
| Controlled DoS | 30 | 30.0 | 0.853 [0.847, 0.859] | 0.000 |
| Multi-source load (DDoS) | 0 | 0.0 | 0.995 [0.993, 0.997] | 0.002 [0.001, 0.004] |
| Multi-source load (DDoS) | 3 | 3.0 | 0.980 [0.976, 0.984] | 0.000 |
| Multi-source load (DDoS) | 10 | 10.0 | 0.899 [0.894, 0.904] | 0.000 |
| Multi-source load (DDoS) | 30 | 30.0 | 0.620 [0.614, 0.627] | 0.000 |

## Provenance

* Runs: 1190 (10 seeds per cell); wall time 124.7 s.
* Raw per-run metrics: `results/cyber_range/experiments/latest.json`.
* Same configuration + seed reproduces a run exactly (`tests/test_cyber_range.py`).
