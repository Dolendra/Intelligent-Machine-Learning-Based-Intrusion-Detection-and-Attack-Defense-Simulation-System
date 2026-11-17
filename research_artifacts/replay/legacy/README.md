# Legacy replay pool — INVALID for frozen-model evaluation

`replay_pool_v1_INVALID_for_frozen.parquet` was built (Nov 2026) from the Zero-Day Gate's test
split only. The frozen v1.1 model uses an independent 70/10/20 split, so **69.6 % of these rows are
in v1.1's training split** (10.2 % validation, 20.4 % test; exact float32 row match).

* Valid for: Zero-Day Gate evaluation (its own test split) and the 47 Infiltration/Heartbleed flows.
* **Invalid for:** any frozen v1.1 metric — Live Monitor and Cyber Range detector tables, the
  `frozen_v11` block of the pre-R1a gate report, the pre-R1a XAI stability study.

Kept only as evidence for docs/research/CLAIM_AUDIT.md §0.2. The replacement is
`../replay_pool.parquet` (see `../replay_pool_manifest.json`).
