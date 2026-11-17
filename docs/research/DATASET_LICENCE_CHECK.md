# Dataset licence and structure check (R3 Stage 0, 2026-11-17)

**Status: verification only. Nothing was downloaded.** These are findings from the official pages, with sources listed per dataset. Items marked *unconfirmed* must be checked before any download.

## Summary

| Dataset | Official source | Licence | Redistribution | Access / size | Timestamps | Features | Fit to protocol |
|---|---|---|---|---|---|---|---|
| LycoS-IDS2017 | lycos-ids.univ-lemans.fr (Le Mans Univ.); git at maupiti-git.univ-lemans.fr/lycos/lycos-ids2017 | **No licence stated.** "available for researchers"; citing Rosay et al. 2021 (doi:10.1145/3486622.3493973) is required | Not stated. The CIC-2017 parent is also silent, so commit **code and metrics only** | Repo zip, no registration, ≈532 MB | Yes: per-day files and a µs `timestamp`, plus IPs | LycoSTand: 7 ID columns, 75 features and a label. Names are snake_case, not CICFlowMeter | Per-day: yes. Cross-network: with LycoS-Unicas-18 (column parity unconfirmed: 75 vs 77). Families: all except Infiltration (Thursday afternoon dropped) |
| LycoS-Unicas-IDS2018 | github.com/MarcoCantone/LycoS-Unicas-IDS2018 (README only) | **No licence stated**; cite Cantone et al., IEEE Access 2024 | Not stated (CSE-CIC-IDS2018 parent permits redistribution with citation) | Google Drive. One CSV of 13.69 M rows; file size unconfirmed | **Unconfirmed**: one file, and benign was randomly subsampled to 10 M | "77 features" plus a label | Per-day: doubtful. Families: no PortScan, no Infiltration |
| NF-v3 (UNSW-NB15, ToN-IoT, BoT-IoT, CSE-CIC-IDS2018) | staff.itee.uq.edu.au/marius/NIDS_datasets, hosted on UQ RDM | **No licence stated** on the UQ page; cite Luay et al. (arXiv 2503.04404; IEEE Access 2026). RDM metadata unreadable | Not stated | CSVs of 2.4–27.5 M flows; sizes unconfirmed | Yes: `FLOW_START/END_MILLISECONDS`, plus IPs | 53 NetFlow v9 (nProbe) fields | Cross-network: yes, within NF-v3 only. **There is no NF-CICIDS2017-v3.** Family mapping is coarse for UNSW, ToN and BoT |
| CICIDS2017 (in use) | unb.ca/cic/datasets/ids-2017.html | "publicly available for researchers"; cite Sharafaldin et al. 2018 | Not stated | — | — | — | — |
| CSE-CIC-IDS2018 (in use) | unb.ca/cic/datasets/ids-2018.html | "You may redistribute, republish, and mirror … must include a citation … and a link" | Allowed, with citation | — | — | — | — |

## Notes

- **CLOSR's Google Drive copy of LycoS.** The CLOSR README links a "preprocessed version" on Google Drive. Nothing states that redistribution was authorised, and Apache-2.0 covers only CLOSR's code. **Use the official LycoS source** and rebuild the authors' merge, recording the steps.
- **LycoS-IDS2017 is small in places.** Heartbleed has 11 flows and SQL injection 12. Thursday afternoon (Infiltration) and some Friday flows are dropped by its labelling script.
- **Consequence for Contribution 1.**
  - NF-v3 is the only option that offers both timestamps and a shared schema across networks.
  - It has no 2017 member, so confirmation would be NF-CSE-CIC-IDS2018-v3 ↔ NF-UNSW-NB15-v3 / NF-ToN-IoT-v3, in NetFlow feature space.
  - The LycoS pair suits Contribution 2 (extractor attribution), but the 2018 member lacks confirmed timestamps.
- **Recommendation.** If you approve the downloads, commit only code, crosswalks and metrics, never raw or processed flow files, and cite every source.
