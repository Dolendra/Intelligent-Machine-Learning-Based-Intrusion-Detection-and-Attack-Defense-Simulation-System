"""Stage-2 Phase F: cyber-range simulation validation (controlled visualization).

Usage:
  python scripts/27_cyber_range_sim_validate.py
  python scripts/27_cyber_range_sim_validate.py --json

Exit code 0 when all configured attack families recover with advisory_only framing.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from simulation.validation import DEFAULT_FAMILIES, validate_families


def main() -> int:
    parser = argparse.ArgumentParser(description="Aegis IDS cyber-range sim validation (prototype)")
    parser.add_argument("--json", action="store_true", help="Print full JSON report")
    parser.add_argument(
        "--families",
        nargs="*",
        default=list(DEFAULT_FAMILIES),
        help="Attack families to validate",
    )
    args = parser.parse_args()
    report = validate_families(tuple(args.families))
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"mode={report['mode']} live_cyber_range={report['live_cyber_range']} all_ok={report['all_ok']}")
        for row in report["results"]:
            status = "OK" if row["ok"] else "FAIL"
            print(
                f"  [{status}] {row['attack_type']}: state={row['final_state']} "
                f"assumed={row['assumed_efficacy_config']} "
                f"sim_eff={row['simulated_defense_effectiveness']} "
                f"errors={row['errors']}"
            )
        print("notes:")
        for n in report["notes"]:
            print(f"  - {n}")
    return 0 if report["all_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
