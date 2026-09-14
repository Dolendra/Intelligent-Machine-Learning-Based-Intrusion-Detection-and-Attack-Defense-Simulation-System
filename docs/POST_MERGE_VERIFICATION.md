# Post-merge verification (`main`)

**Date:** 2026-09-15  
**Merge:** PR #2 → `main`  
**Merge commit:** `b6c93267c728de86eab4089aa56e5c36c40e92cc`  
**Result:** **PASS**

## Checklist

| Check | Result | Evidence |
|-------|--------|----------|
| `main` contains PR #2 merge | PASS | `b6c9326 Merge pull request #2 from Dolendra/productionization` |
| CI on `main` (merge push) | PASS | Run `34890440660` — `test-python`, `build-frontend`, `docker-build`, `stage2-gate` all **success** |
| Tag `v1.1-research` exists | PASS | Local + `origin` (`refs/tags/v1.1-research`) |
| Frozen joblib hashes unchanged | PASS | `binary_best`/`multiclass_best`/`feature_bundle` match `model_metadata.json` (`9b0158aacd2cde3c`, `d6da28dae45ca4c0`, `008dfe62ef5e663d`); binary F1 **0.99048**, macro-F1 **0.99813** |
| `productionization` branch preserved | PASS | `origin/productionization` @ `76da103`; is ancestor of `main` |
| P12 report present | PASS | `reports/final_security_validation_report.json` + mirror; **overall: PASS** |
| P11 empirical report present | PASS | `empirical_mitigation_report.json` — EXP-018/019; measured DDoS **1.00**, DoS **0.80**; sim priors **0.82** / **0.78** |
| P10 generalization artifact | PASS | `generalization_report.json` present |
| No raw CICIDS trees in git | PASS | `MachineLearningCVE/` / `TrafficLabelling/` gitignored, not tracked |
| No accidental large CSVs/PCAPs | PASS | Tracked: only `tests/fixtures/pcap/golden_flows.csv`, `minimal.pcap` |
| Structure sane | PASS | backend, frontend, ml, security, empirical, simulation, docs, reports, scripts, tests present |

## Notes

- Local `MachineLearningCVE/` / `TrafficLabelling/` may exist on disk for research; they are **not** part of the git tree.
- Largest tracked blobs remain model joblibs / docs (~3.3 MB multiclass), not dataset dumps.
- Next provenance step (after this PASS): annotated tag **`v2.0-aegis-productionized`** on `main` @ `b6c9326`.

## Commands used

```bash
git fetch origin --tags
git checkout main && git pull
gh run view 34890440660
# hash verify vs model_metadata.json
# presence checks for P11/P12 JSON + docs
```
