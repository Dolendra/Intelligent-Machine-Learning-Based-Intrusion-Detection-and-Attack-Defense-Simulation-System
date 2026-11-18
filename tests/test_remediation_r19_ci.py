"""R-19 (ARCH-15): CI covers the research/remediation branches and the checks the audit asked for."""
from __future__ import annotations

import yaml

from ids_config import ROOT

CI = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))
TRIGGERS = CI.get("on") or CI.get(True)            # YAML 1.1 reads the key `on` as True


def _steps(job: str) -> str:
    return "\n".join(str(s.get("run", "")) + str(s.get("name", "")) for s in CI["jobs"][job]["steps"])


def test_branches_covered():
    push = TRIGGERS["push"]["branches"]
    for b in ("main", "v3-openset-research", "audit/**", "remediation/**"):
        assert b in push, b


def test_ci_runs_as_test_environment():
    assert CI["env"]["AEGIS_ENV"] == "test"


def test_python_job_checks_integrity_and_migrations():
    s = _steps("test-python")
    assert "verify_manifest" in s and "frozen_v11_diff" in s
    assert "alembic upgrade head" in s and "alembic check" in s
    assert CI["jobs"]["test-python"]["steps"][0]["with"]["fetch-depth"] == 0


def test_docker_job_starts_the_container():
    s = _steps("docker-build")
    assert "docker compose up -d api" in s and "/api/ready" in s


def test_node_version_matches_frontend_image():
    node = next(st["with"]["node-version"] for st in CI["jobs"]["build-frontend"]["steps"]
                if "with" in st and "node-version" in st["with"])
    assert str(node) == "22"
    assert "node:22" in (ROOT / "Dockerfile.frontend").read_text(encoding="utf-8")
