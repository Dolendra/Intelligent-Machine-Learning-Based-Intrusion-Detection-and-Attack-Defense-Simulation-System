"""R-05/R-06 (SEC-3, SEC-28): the API fails closed outside development/test."""
from __future__ import annotations

import pytest

from security.auth import posture
from security.auth.posture import InsecureConfigurationError, enforce_startup_posture

STRONG = "x" * 48


@pytest.fixture
def clean_env(monkeypatch):
    for name in ("AEGIS_ENV", "AEGIS_AUTH_ENABLED", "AEGIS_AUTH_SECRET", "AEGIS_API_KEY", *posture.KILL_SWITCHES):
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_unset_environment_is_production(clean_env):
    assert posture.deployment_environment() == "production"
    assert not posture.is_dev_environment()


def test_production_with_auth_off_refuses_to_start(clean_env):
    clean_env.setenv("AEGIS_AUTH_ENABLED", "false")
    with pytest.raises(InsecureConfigurationError, match="authentication is disabled"):
        enforce_startup_posture()


def test_unset_environment_with_default_config_refuses_to_start(clean_env):
    # config.yaml ships auth.enabled: false, so the shipped default no longer starts unauthenticated.
    with pytest.raises(InsecureConfigurationError):
        enforce_startup_posture()


@pytest.mark.parametrize("switch", posture.KILL_SWITCHES)
def test_kill_switch_outside_dev_refuses_to_start(clean_env, switch):
    clean_env.setenv("AEGIS_ENV", "production")
    clean_env.setenv("AEGIS_AUTH_ENABLED", "true")
    clean_env.setenv("AEGIS_AUTH_SECRET", STRONG)
    clean_env.setenv(switch, "true")
    with pytest.raises(InsecureConfigurationError, match="kill switches"):
        enforce_startup_posture()


@pytest.mark.parametrize("switch", posture.KILL_SWITCHES)
def test_kill_switch_ignored_outside_dev(clean_env, switch):
    clean_env.setenv("AEGIS_ENV", "staging")
    clean_env.setenv(switch, "true")
    assert not posture.kill_switch_allowed(switch)


def test_production_with_auth_and_strong_secret_starts(clean_env):
    clean_env.setenv("AEGIS_ENV", "production")
    clean_env.setenv("AEGIS_AUTH_ENABLED", "true")
    clean_env.setenv("AEGIS_AUTH_SECRET", STRONG)
    p = enforce_startup_posture()
    assert p.auth_enabled and p.token_secret_ok and not p.dev_environment


def test_development_with_auth_off_starts_with_switches_effective(clean_env):
    clean_env.setenv("AEGIS_ENV", "development")
    clean_env.setenv("AEGIS_AUTH_ENABLED", "false")
    clean_env.setenv("DISABLE_RATE_LIMIT", "true")
    p = enforce_startup_posture()
    assert not p.auth_enabled and p.kill_switches_effective == ["DISABLE_RATE_LIMIT"]
    assert posture.kill_switch_allowed("DISABLE_RATE_LIMIT")


def test_app_import_fails_closed_in_fresh_production_process(tmp_path):
    """End to end: importing the real app with production settings and auth off must fail."""
    import os
    import subprocess
    import sys

    from ids_config import ROOT

    env = {k: v for k, v in os.environ.items() if not k.startswith(("AEGIS_", "DISABLE_"))}
    env.update({"AEGIS_ENV": "production", "AEGIS_AUTH_ENABLED": "false",
                "IDS_DB_PATH": str(tmp_path / "x.db"), "PYTHONDONTWRITEBYTECODE": "1"})
    r = subprocess.run([sys.executable, "-c", "import backend.main"], cwd=ROOT, env=env,
                       capture_output=True, text=True, timeout=300)
    assert r.returncode != 0
    assert "InsecureConfigurationError" in r.stderr and "Refusing to start" in r.stderr
