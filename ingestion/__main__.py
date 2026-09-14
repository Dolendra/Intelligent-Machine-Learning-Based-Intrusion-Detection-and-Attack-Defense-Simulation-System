"""CLI: python -m ingestion.cli ..."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ingestion.adapters import adapt_flows_csv, pcap_extractor_status
from ingestion.cicflowmeter_runner import dataframe_from_cicflowmeter_csv, run_cicflowmeter
from ingestion.pipeline import ingest_flows_csv, ingestion_capabilities
from ingestion.schema_info import schema_summary


def _cmd_capabilities(_: argparse.Namespace) -> int:
    print(json.dumps(ingestion_capabilities(), indent=2))
    return 0


def _cmd_schema(_: argparse.Namespace) -> int:
    print(json.dumps(schema_summary(), indent=2))
    return 0


def _cmd_normalize_csv(args: argparse.Namespace) -> int:
    aligned, validation = adapt_flows_csv(Path(args.input), fill_missing=args.fill_missing)
    if not validation.get("ok"):
        print(json.dumps({"ok": False, "validation": validation}, indent=2), file=sys.stderr)
        return 2
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    aligned.to_csv(out, index=False)
    print(json.dumps({"ok": True, "rows": len(aligned), "output": str(out), "validation": validation}, indent=2))
    return 0


def _cmd_pcap(args: argparse.Namespace) -> int:
    status = pcap_extractor_status()
    if not status.get("tools", {}).get("cicflowmeter"):
        print(json.dumps({"ok": False, **status}, indent=2), file=sys.stderr)
        return 3
    csv_path, meta = run_cicflowmeter(Path(args.input), Path(args.output) if args.output else None)
    if csv_path is None:
        print(json.dumps({"ok": False, **meta}, indent=2), file=sys.stderr)
        return 4
    if args.align:
        aligned, validation = dataframe_from_cicflowmeter_csv(csv_path, fill_missing=args.fill_missing)
        if not validation.get("ok"):
            print(json.dumps({"ok": False, "csv": str(csv_path), "validation": validation, **meta}, indent=2), file=sys.stderr)
            return 2
        aligned_path = Path(args.aligned_output) if args.aligned_output else csv_path.with_name(csv_path.stem + "_aligned.csv")
        aligned.to_csv(aligned_path, index=False)
        print(json.dumps({"ok": True, "csv": str(csv_path), "aligned": str(aligned_path), "rows": len(aligned), "validation": validation}, indent=2))
        return 0
    print(json.dumps({"ok": True, **meta}, indent=2))
    return 0


def _cmd_ingest_csv(args: argparse.Namespace) -> int:
    result = ingest_flows_csv(Path(args.input), fill_missing=args.fill_missing, max_rows=args.max_rows)
    payload = result.as_dict()
    if not args.include_flows:
        payload["flows"] = payload["flows"][:3]
        payload["flows_truncated"] = True
    print(json.dumps(payload, indent=2))
    return 0 if result.ok else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ingestion.cli", description="Aegis Stage-2 ingestion helpers")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_cap = sub.add_parser("capabilities", help="Show ingestion capabilities JSON")
    p_cap.set_defaults(func=_cmd_capabilities)

    p_schema = sub.add_parser("schema", help="Show frozen feature schema summary")
    p_schema.set_defaults(func=_cmd_schema)

    p_norm = sub.add_parser("normalize-csv", help="Normalize/align a flow CSV to schema v1.1")
    p_norm.add_argument("-i", "--input", required=True)
    p_norm.add_argument("-o", "--output", required=True)
    p_norm.add_argument("--fill-missing", action="store_true")
    p_norm.set_defaults(func=_cmd_normalize_csv)

    p_pcap = sub.add_parser("pcap", help="Run cicflowmeter on a PCAP when installed")
    p_pcap.add_argument("-i", "--input", required=True, help="Input .pcap path")
    p_pcap.add_argument("-o", "--output", help="Output raw CICFlowMeter CSV path")
    p_pcap.add_argument("--align", action="store_true", help="Also write schema-aligned CSV")
    p_pcap.add_argument("--aligned-output", help="Aligned CSV path")
    p_pcap.add_argument("--fill-missing", action="store_true")
    p_pcap.set_defaults(func=_cmd_pcap)

    p_ing = sub.add_parser("ingest-csv", help="Validate CSV via ingest_flows_csv")
    p_ing.add_argument("-i", "--input", required=True)
    p_ing.add_argument("--fill-missing", action="store_true")
    p_ing.add_argument("--max-rows", type=int, default=500)
    p_ing.add_argument("--include-flows", action="store_true")
    p_ing.set_defaults(func=_cmd_ingest_csv)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
