"""Run the cyber-range experiment program and write tables + figures.

Suites (pre-implementation report §18):
  defense    E8  every scenario × every defense
  intensity  E6  attack intensity 0.5× / 1× / 2×
  attackers  E7  1 / 2 / 4 / 8 DDoS sources
  detector   —   frozen v1.1 vs Zero-Day Gate vs union as the incident source
  threshold  E3  alert threshold k vs. detection latency and false incidents
  delay      —   analyst approval delay vs. service impact

Outputs
  results/cyber_range/experiments/latest.json   (+ timestamped copy, raw runs included)
  research_artifacts/figures/range_*.png
  docs/research/CYBER_RANGE_RESULTS.md

Usage
  python scripts/56_cyber_range_experiments.py                 # all suites, seeds 1..10
  python scripts/56_cyber_range_experiments.py --suites defense --seeds 1 2 3
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from cyberrange.engine import DEFENSES  # noqa: E402
from cyberrange.experiments import SUITES, run_all  # noqa: E402
from cyberrange.scenarios import SCENARIOS  # noqa: E402

FIG_DIR = ROOT / "research_artifacts" / "figures"
DOC = ROOT / "docs" / "research" / "CYBER_RANGE_RESULTS.md"


def f(x, nd=2, pct=False):
    if x is None:
        return "—"
    return f"{100 * x:.{max(nd - 1, 0)}f}%" if pct else f"{x:.{nd}f}"


def ci(s, key, nd=2, pct=False):
    v = s[key]
    if v["mean"] is None:
        return "—"
    if v["ci_low"] == v["ci_high"]:
        return f(v["mean"], nd, pct)
    return f"{f(v['mean'], nd, pct)} [{f(v['ci_low'], nd, pct)}, {f(v['ci_high'], nd, pct)}]"


def table(rows, header):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--suites", nargs="+", choices=list(SUITES), default=list(SUITES))
    ap.add_argument("--seeds", nargs="+", type=int, default=list(range(1, 11)))
    args = ap.parse_args()
    res = run_all(args.suites, args.seeds)
    suites = res["suites"]
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    md = [
        "# Cyber range — experiment results (auto-generated)",
        "",
        f"_Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} by `scripts/56_cyber_range_experiments.py`. "
        f"Seeds {args.seeds[0]}–{args.seeds[-1]} ({len(args.seeds)} per cell); brackets are 95% t-intervals over seeds._",
        "",
        "The range replays recorded CICIDS2017 flows on a seeded 1-second clock. Detector verdicts are computed by the "
        "frozen v1.1 model and the Aegis-OSR gate; an incident is raised after 3 alerts from one source within 5 s; "
        "responses change which later flows reach the target. **Modelled, not measured:** arrival rates, per-family "
        "service cost of a flow, the 20% rate-limit pass-through, and target capacity (60 units/s).",
        "",
    ]

    if "defense" in suites:
        cells = suites["defense"]["cells"]
        md += ["## E8 — Defense comparison (all scenarios, auto mode, 3 s approval delay)", ""]
        # aggregated per defense across scenarios
        by_def: dict[str, list] = {}
        for c in cells:
            by_def.setdefault(c["cell"]["defense"], []).append(c["summary"])
        rows = []
        for d, ss in by_def.items():
            def avg(k):
                vals = [s[k]["mean"] for s in ss if s[k]["mean"] is not None]
                return sum(vals) / len(vals) if vals else None
            rows.append([DEFENSES[d]["title"], f(avg("attack_success_after_defense"), 3),
                         f(avg("availability_mean_during_attack"), 3), f(avg("availability_min_during_attack"), 3),
                         f(avg("collateral_rate"), 3), f(avg("recovery_time_s"), 1)])
        md += ["Mean over the nine scenarios:", "",
               table(rows, ["Defense", "Attack success after defense", "Availability (mean, attack)",
                            "Availability (min, attack)", "Benign collateral", "Recovery time (s)"]), ""]
        rows = []
        for c in cells:
            s = c["summary"]
            rows.append([SCENARIOS[c["cell"]["scenario"]].name, DEFENSES[c["cell"]["defense"]]["title"],
                         ci(s, "detection_latency_s", 1), ci(s, "attack_success_after_defense", 3),
                         ci(s, "availability_mean_during_attack", 3), ci(s, "collateral_rate", 3),
                         ci(s, "recovery_time_s", 1)])
        md += ["Per scenario:", "", table(rows, ["Scenario", "Defense", "Detection latency (s)", "Attack success after",
                                                   "Availability (attack)", "Collateral", "Recovery (s)"]), ""]
        # figure: availability vs collateral per defense, one point per scenario
        fig, ax = plt.subplots(figsize=(6.2, 4.0))
        markers = {"block_source": "o", "rate_limit": "s", "isolate_host": "X", "monitor_only": "^", "increase_inspection": "D"}
        for d, mk in markers.items():
            pts = [(c["summary"]["collateral_rate"]["mean"] or 0, c["summary"]["availability_mean_during_attack"]["mean"] or 0)
                   for c in cells if c["cell"]["defense"] == d]
            if pts:
                ax.scatter([p[0] * 100 for p in pts], [p[1] * 100 for p in pts], marker=mk, s=40, label=DEFENSES[d]["title"],
                           edgecolor="black", linewidth=0.5)
        ax.set_xlabel("legitimate traffic blocked by the defense (%)")
        ax.set_ylabel("service availability during the attack (%)")
        ax.legend(fontsize=7, frameon=False)
        ax.spines[["top", "right"]].set_visible(False)
        fig.tight_layout()
        fig.savefig(FIG_DIR / "range_defense_tradeoff.png", dpi=220)
        plt.close(fig)

    if "detector" in suites:
        cells = suites["detector"]["cells"]
        md += ["## Detector comparison — which model raises the incident", ""]
        rows = []
        for c in cells:
            s = c["summary"]
            rows.append([SCENARIOS[c["cell"]["scenario"]].name, c["cell"]["detector"], ci(s, "detected", 2),
                         ci(s, "detection_latency_s", 1), ci(s, "attack_flow_recall", 3), ci(s, "fpr_flows", 4, pct=True),
                         ci(s, "false_incidents", 2)])
        md += [table(rows, ["Scenario", "Detector", "Detected (share of runs)", "Detection latency (s)",
                            "Attack-flow recall", "Benign flow FPR", "False incidents"]), ""]

    if "threshold" in suites:
        cells = suites["threshold"]["cells"]
        md += ["## E3 — Alert threshold k (alerts from one source within 5 s)", ""]
        rows = [[SCENARIOS[c["cell"]["scenario"]].name, c["cell"]["alert_threshold"], ci(c["summary"], "detected", 2),
                 ci(c["summary"], "detection_latency_s", 1), ci(c["summary"], "false_incidents", 2)] for c in cells]
        md += [table(rows, ["Scenario", "k", "Detected", "Detection latency (s)", "False incidents"]), ""]
        fig, ax = plt.subplots(figsize=(6.2, 3.6))
        for sc in dict.fromkeys(c["cell"]["scenario"] for c in cells):
            xs = [c["cell"]["alert_threshold"] for c in cells if c["cell"]["scenario"] == sc]
            ys = [c["summary"]["detection_latency_s"]["mean"] for c in cells if c["cell"]["scenario"] == sc]
            ax.plot(xs, [y if y is not None else float("nan") for y in ys], marker="o", label=SCENARIOS[sc].name)
        fi = [c["summary"]["false_incidents"]["mean"] or 0 for c in cells if c["cell"]["scenario"] == "dos"]
        ax2 = ax.twinx()
        ax2.bar([c["cell"]["alert_threshold"] for c in cells if c["cell"]["scenario"] == "dos"], fi, alpha=0.25,
                color="grey", width=0.6, label="false incidents (DoS runs)")
        ax.set_xlabel("alert threshold k"); ax.set_ylabel("detection latency (s)"); ax2.set_ylabel("false incidents per run")
        ax.legend(fontsize=7, frameon=False, loc="upper left")
        fig.tight_layout(); fig.savefig(FIG_DIR / "range_threshold.png", dpi=220); plt.close(fig)

    if "intensity" in suites:
        cells = suites["intensity"]["cells"]
        md += ["## E6 — Attack intensity (recommended defense)", ""]
        rows = [[SCENARIOS[c["cell"]["scenario"]].name, f"{c['cell']['intensity']}×", ci(c["summary"], "detection_latency_s", 1),
                 ci(c["summary"], "availability_min_during_attack", 3), ci(c["summary"], "attack_success_after_defense", 3)]
                for c in cells]
        md += [table(rows, ["Scenario", "Intensity", "Detection latency (s)", "Min availability", "Attack success after"]), ""]

    if "attackers" in suites:
        cells = suites["attackers"]["cells"]
        md += ["## E7 — Number of DDoS sources (block source)", ""]
        rows = [[c["cell"]["attackers"], ci(c["summary"], "attackers_detected", 2), ci(c["summary"], "detection_latency_s", 1),
                 ci(c["summary"], "attack_success_after_defense", 4), ci(c["summary"], "availability_min_during_attack", 3)]
                for c in cells]
        md += [table(rows, ["Sources", "Sources detected", "Detection latency (s)", "Attack success after defense",
                            "Min availability"]), ""]

    if "delay" in suites:
        cells = suites["delay"]["cells"]
        md += ["## Analyst approval delay", ""]
        rows = [[SCENARIOS[c["cell"]["scenario"]].name, c["cell"]["approval_delay_s"], ci(c["summary"], "time_to_mitigate_s", 1),
                 ci(c["summary"], "availability_mean_during_attack", 3), ci(c["summary"], "attack_success_rate" if False else "attack_success_after_defense", 3)]
                for c in cells]
        md += [table(rows, ["Scenario", "Approval delay (s)", "Time to mitigate (s)", "Availability (attack)",
                            "Attack success after defense"]), ""]
        fig, ax = plt.subplots(figsize=(5.4, 3.4))
        for sc in ("dos", "ddos"):
            xs = [c["cell"]["approval_delay_s"] for c in cells if c["cell"]["scenario"] == sc]
            ys = [100 * c["summary"]["availability_mean_during_attack"]["mean"] for c in cells if c["cell"]["scenario"] == sc]
            ax.plot(xs, ys, marker="o", label=SCENARIOS[sc].name)
        ax.set_xlabel("analyst approval delay (s)"); ax.set_ylabel("availability during attack (%)")
        ax.legend(fontsize=7, frameon=False); ax.spines[["top", "right"]].set_visible(False)
        fig.tight_layout(); fig.savefig(FIG_DIR / "range_delay.png", dpi=220); plt.close(fig)

    total_runs = sum(len(s["cells"]) * len(args.seeds) for s in suites.values())
    md += ["## Provenance", "",
           f"* Runs: {total_runs} ({len(args.seeds)} seeds per cell); wall time "
           f"{sum(s['runtime_seconds'] for s in suites.values()):.1f} s.",
           "* Raw per-run metrics: `results/cyber_range/experiments/latest.json`.",
           "* Same configuration + seed reproduces a run exactly (`tests/test_cyber_range.py`).", ""]
    DOC.write_text("\n".join(md), encoding="utf-8")
    print(f"wrote {DOC} and figures; {total_runs} runs")


if __name__ == "__main__":
    main()
