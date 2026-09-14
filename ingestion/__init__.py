"""Stage-2 network ingestion package (opt-in; does not alter v1.1 training)."""

from ingestion.pipeline import IngestResult, ingest_flows_csv, ingest_pcap, ingestion_capabilities
from ingestion.schema_info import load_feature_schema, schema_summary

__all__ = [
    "IngestResult",
    "ingest_flows_csv",
    "ingest_pcap",
    "ingestion_capabilities",
    "load_feature_schema",
    "schema_summary",
]
