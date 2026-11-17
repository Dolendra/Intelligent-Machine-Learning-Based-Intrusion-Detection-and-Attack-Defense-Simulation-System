@echo off
REM Start IDS API (run from repo root)
REM Local development only: the API refuses to start unauthenticated outside AEGIS_ENV=development/test.
set AEGIS_ENV=development
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
