# Simulation engine

**Path:** `simulation/engine/core.py`

## What it is

A **safe visualization** of:

`idle → normal → attack_start → attack_impact → detected → recommended → defended → recovered`

Topology: Attacker → Internet → Firewall → Router → {IDS, Server, PCs}

## What it is not

It does **not** generate real attack traffic or compromise hosts.

## API

- `POST /api/simulation/start`
- `POST /api/simulation/advance` (`action`: omit for next, or `defend` / `reset`)
