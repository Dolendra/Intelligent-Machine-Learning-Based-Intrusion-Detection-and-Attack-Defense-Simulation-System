# Aegis IDS — P8 Performance Baseline

**Branch:** `productionization`  
**Rule:** DT/RF research baseline (`v1.1-research`) is **not** modified for performance.

## How to measure

```bash
# Offline suite → results/performance/
python scripts/37_performance_baseline.py
python scripts/37_performance_baseline.py --quick

# Individual benches
python scripts/30_benchmark_prediction.py --n 50
python scripts/31_benchmark_batch.py --sizes 100,500,1000,5000
python scripts/32_benchmark_shap.py --n 15
python scripts/34_benchmark_queue.py --jobs 25
python scripts/34_benchmark_queue.py --saturate
python scripts/35_benchmark_db.py
python scripts/36_benchmark_stages.py

# API (requires uvicorn; DISABLE_RATE_LIMIT=true on API for predict-heavy runs)
python scripts/33_benchmark_api.py --base http://127.0.0.1:8000 --include-predict
```

CI runs only `tests/test_productionization_p8_performance.py` (harness shape) — **not** heavy benches.

## Result schema

JSON under `results/performance/` (`schema_version: p8.1`):

- `experiment_id`, `commit`, `timestamp`, `workload`, `scenario`
- `environment`, `metrics`, `throughput`, `stages_ms`, `error_rate`
- Flags: `prototype_only`, `not_a_capacity_claim`, `ml_baseline_untouched`

Canonical aggregate: [`results/performance/operating_envelope_latest.json`](../results/performance/operating_envelope_latest.json)

## Measured operating envelope (dev host, full baseline)

From `scripts/37_performance_baseline.py` on the development Windows host (see JSON for commit/platform). **Re-run on target hardware before citing.**

| Workload | Measured point |
|----------|----------------|
| Single-flow offline predict (no SHAP) | **~68 flows/s**, p50 **~15 ms**, p95 **~16 ms**, error rate **0%** |
| Pipeline batch 100 | **~113 flows/s** wall-clock |
| Pipeline batch 500 (API max) | **~125 flows/s** wall-clock |
| Predictor vectorized 1000 / 5000 | **~15k–22k flows/s** (ML only; no risk/enrichment loop) |
| Queue (single worker) | Jobs complete; **saturation → 1 reject at max_jobs**, no silent drop |
| Concurrent approve | **1** successful atomic claim / 8 racers |
| PCAP validation | **<1 ms**; extraction **skipped** without cicflowmeter |
| SHAP (TreeExplainer on frozen DT) | Same order of magnitude as predict on this host (~0.7× p50 ratio in run) |

### Bottleneck insight (measurement, not optimization)

The large gap between **pipeline batch (~10² flows/s)** and **vectorized predictor (~10⁴ flows/s)** shows the cost is largely in the **per-flow enrichment/persistence path**, not the frozen DT/RF inference itself. P8 records this; it does **not** rewrite that path.

## Resource limits

| Limit | Behavior |
|-------|----------|
| API batch >500 | Rejected (422) |
| Oversized body / bad PCAP | 413 / validation reject + audit (P5) |
| Ingest queue full | Explicit error — no silent drop |
| Disk exhaustion | Monitor free space (P7); full DR is P9 |

## Claim wording

> Under the tested hardware/software configuration and workload recorded in `operating_envelope_latest.json`, Aegis processed about **68 flows/sec** single-flow offline prediction at **~16 ms p95**, and about **125 flows/sec** through the pipeline batch path at size 500, with **0%** error rate on the scripted prediction runs. Vectorized ML-only throughput is much higher (~10⁴ flows/sec), indicating enrichment—not the frozen models—as the primary batch bottleneck on this host. Queue overflow is rejected at capacity. This is a **measured operating point**, not an SLA or multi-node capacity claim.

## Out of scope for P8

- Retraining or swapping DT/RF
- Blind optimization without a measured bottleneck
- Prometheus / k8s autoscaling
