# PCAP fixtures (productionization P1)

Committed for CI — **no system-wide `cicflowmeter` required**.

| File | Purpose |
|------|---------|
| `minimal.pcap` | Valid classic libpcap global header (24 bytes, no packets). Used for upload validation + 501 path. |
| `golden_flows.csv` | Schema-aligned MachineLearningCVE-style flow row (78 features). Stands in for CICFlowMeter CSV output in mocked extract tests. |

## Honesty rule

- Real `POST /api/ingest/pcap` and `POST /api/ingest/queue/submit-pcap` still return **501** when `cicflowmeter` is not on PATH.
- CI mocks only `run_cicflowmeter` to return `golden_flows.csv`, proving: validated PCAP → extract CSV → **existing queue** → frozen DT/RF path.

Do not treat golden values as real captured traffic.
