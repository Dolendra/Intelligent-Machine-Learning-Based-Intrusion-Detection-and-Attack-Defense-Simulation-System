"""Pytest bootstrap — force non-interactive matplotlib on CI/Windows."""
import os

os.environ.setdefault("MPLBACKEND", "Agg")
