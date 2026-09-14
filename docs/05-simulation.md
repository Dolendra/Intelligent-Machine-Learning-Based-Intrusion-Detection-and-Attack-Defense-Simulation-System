# Simulation engine

**Path:** `simulation/engine/core.py`

## What it is

A **safe visualization** of:

`idle → normal → attack_start → attack_impact → detected → recommended → defended → recovered`

Topology: Attacker → Internet → Firewall → Router → {IDS, Server, PCs}

## What it is not

It does **not** generate real attack traffic or compromise hosts.  
It is **not** a physical cyber range. Defense effectiveness values in `config.yaml` are **visualization assumptions**, not empirically measured mitigation rates.

## API

- `POST /api/simulation/start`
- `POST /api/simulation/advance` (`action`: omit for next, or `defend` / `reset`)

## Stage-2 Phase F validation

Run the controlled-visualization harness (CI also runs this in `stage2-gate`):

```bash
python scripts/27_cyber_range_sim_validate.py
python scripts/27_cyber_range_sim_validate.py --json
```

Checks: each configured attack family reaches `recovered`, `advisory_only=true`, required latency/comparison keys, and deterministic phase timings across two runs.
