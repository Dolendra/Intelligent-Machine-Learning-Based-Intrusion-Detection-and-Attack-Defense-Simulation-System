"""R-09 (ARCH-1) + R-06 compose: the API image contains every package the app imports at startup."""
from __future__ import annotations

import os
import re
import subprocess
import sys

from ids_config import ROOT

DOCKERFILE = (ROOT / "Dockerfile.api").read_text(encoding="utf-8")
COMPOSE = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")


def _copied_paths() -> set[str]:
    out = set()
    for src in re.findall(r"^COPY\s+(.+?)\s+\S+\s*$", DOCKERFILE, flags=re.M):
        out.update(src.split())
    return out


def _top_level_repo_packages() -> set[str]:
    return {p.name for p in ROOT.iterdir() if p.is_dir() and (p / "__init__.py").exists()}


def test_image_copies_every_runtime_package():
    copied = _copied_paths()
    for pkg in ("backend", "ml", "explainability", "security", "simulation", "ingestion",
                "database", "cyberrange", "research"):
        assert pkg in copied, pkg
    assert "research_artifacts/replay" in copied
    assert "models/trained_models" in copied


def test_app_imports_with_only_the_copied_packages(tmp_path):
    """Simulate the image: block every repo package the Dockerfile does not copy, then import."""
    blocked = sorted(_top_level_repo_packages() - _copied_paths() - {"tests"})
    code = (
        "import sys, importlib.abc\n"
        f"BLOCK = {blocked!r}\n"
        "class F(importlib.abc.MetaPathFinder):\n"
        "    def find_spec(self, name, path, target=None):\n"
        "        if name.split('.')[0] in BLOCK: raise ImportError('not in image: ' + name)\n"
        "sys.meta_path.insert(0, F())\n"
        "import backend.main\n"
        "print('IMPORT_OK')\n"
    )
    env = {k: v for k, v in os.environ.items() if not k.startswith(("AEGIS_", "DISABLE_"))}
    env.update({"AEGIS_ENV": "production", "AEGIS_AUTH_ENABLED": "true",
                "AEGIS_AUTH_SECRET": "s" * 48, "IDS_DB_URL": f"sqlite:///{(tmp_path / 'd.db').as_posix()}",
                "PYTHONDONTWRITEBYTECODE": "1"})
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True,
                       timeout=300)
    assert "IMPORT_OK" in r.stdout, r.stderr[-2000:]


def test_compose_is_loopback_bound_and_authenticated():
    assert '"127.0.0.1:8000:8000"' in COMPOSE and '"127.0.0.1:5173:80"' in COMPOSE
    assert 'AEGIS_AUTH_ENABLED: "true"' in COMPOSE and "AEGIS_ENV: production" in COMPOSE
    assert "${AEGIS_AUTH_SECRET:?" in COMPOSE                 # fail fast when missing


def test_dockerignore_excludes_secrets_and_bulk_data():
    ignore = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    for entry in (".env", ".venvs/", "CSE-CIC-IDS2018/", "research_artifacts/r3/", "MachineLearningCVE/"):
        assert entry in ignore, entry
