"""Docker Compose smoke: wait for API health (and optional frontend).

Usage (after `docker compose up -d --build`):
  python scripts/19_docker_compose_smoke.py

Or:
  set COMPOSE_SMOKE=1 && python scripts/19_docker_compose_smoke.py
"""
from __future__ import annotations

import os
import sys
import time
import urllib.error
import urllib.request


def _get(url: str, timeout: float = 5.0) -> tuple[int, str]:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read().decode("utf-8", errors="replace")


def wait_ok(url: str, attempts: int = 40, delay: float = 3.0) -> None:
    last = ""
    for i in range(attempts):
        try:
            status, body = _get(url)
            if status == 200:
                print(f"OK {url} ({i+1}/{attempts}) body_snip={body[:120]!r}")
                return
            last = f"status={status}"
        except Exception as exc:  # noqa: BLE001
            last = str(exc)
        time.sleep(delay)
    raise SystemExit(f"Smoke failed for {url}: {last}")


def main() -> None:
    api = os.getenv("SMOKE_API_URL", "http://127.0.0.1:8000/api/health")
    front = os.getenv("SMOKE_FRONTEND_URL", "http://127.0.0.1:5173/")
    wait_ok(api)
    try:
        wait_ok(front, attempts=15, delay=2.0)
    except SystemExit as exc:
        print(f"WARN frontend not reachable (optional): {exc}")
    print("docker compose smoke passed")


if __name__ == "__main__":
    main()
