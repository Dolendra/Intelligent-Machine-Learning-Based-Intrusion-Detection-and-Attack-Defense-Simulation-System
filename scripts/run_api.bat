@echo off
REM Start IDS API (run from repo root)
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
