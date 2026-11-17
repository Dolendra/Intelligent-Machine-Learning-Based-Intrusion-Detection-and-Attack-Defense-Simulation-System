"""Generate every publication table (LaTeX + Markdown + JSON) from committed result artifacts (R1b).

Order of the full publication build (each step reads only artifacts or the previous step's output):

    python scripts/61_dataset_summary.py        # committed corpus counts
    python scripts/53_summarize_research.py     # summaries from raw experiment records
    python scripts/59_paper_numbers.py          # LaTeX macros (numbers + prose facts)
    python scripts/62_publication_tables.py     # this script: tables/*.tex, TABLES.md, publication_tables.json
    python scripts/55_research_figures.py       # research figures
    python docs/research/paper_build/make_figs.py
    python docs/research/paper_build/paper.py   # DOCX (then export PDF)

Outputs: docs/research/publication/{tables/<key>.tex, TABLES.md, publication_tables.json}
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from research.publication import write_all  # noqa: E402


def main() -> None:
    tables = write_all()
    for k, t in tables.items():
        print(f"{k:13s} {len(t.rows):3d} rows  ← {', '.join(t.sources)}")


if __name__ == "__main__":
    main()
