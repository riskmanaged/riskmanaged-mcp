"""Shared fixtures for the riskmanaged-mcp suite.

Isolation here is a safety requirement, not hygiene. Two module-level constants
make the naive approach wrong:

  * `config.CONFIG_DIR` / `CONFIG_FILE` are computed from `Path.home()` **at
    import time** (`config.py:12-13`). Monkeypatching `HOME` after the module is
    imported changes nothing. The functions read the module globals at call
    time, so the fixture patches the *attributes* instead.

  * `config.DEFAULT_BASE_URL` is **production** (`config.py:15`). A test that
    forgets to override it does not fail — it quietly calls the live API with
    whatever token it found on disk.

Together those mean a careless test reads the developer's real credentials and
talks to production. So `_isolate_credentials` is autouse, and `mock_api` runs
respx in `assert_all_mocked=True` so any unmocked request raises instead of
escaping to the network. That is the enforcement; the rest is convention.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import respx

FAKE_TOKEN = "test-token-not-a-real-credential"
FAKE_BASE_URL = "https://mcp-tests.invalid"
API_ROOT = f"{FAKE_BASE_URL}/api/external"

# The package root, for tests that read docs or vendored snapshots.
REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "riskmanaged_mcp"
SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


@pytest.fixture(autouse=True)
def _isolate_credentials(tmp_path, monkeypatch):
    """Point the config module at a temp dir and pin fake credentials.

    Autouse and unconditional: no test may read `~/.riskmanaged/config.json` or
    inherit a developer's ambient `RISKMANAGED_*` environment.
    """
    from riskmanaged_mcp import config

    cfg_dir = tmp_path / ".riskmanaged"
    monkeypatch.setattr(config, "CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(config, "CONFIG_FILE", cfg_dir / "config.json")

    monkeypatch.setenv("RISKMANAGED_TOKEN", FAKE_TOKEN)
    monkeypatch.setenv("RISKMANAGED_URL", FAKE_BASE_URL)
    return cfg_dir


@pytest.fixture
def no_env_credentials(monkeypatch):
    """Drop the env vars so on-disk precedence can be exercised.

    `_isolate_credentials` still redirects CONFIG_FILE, so this falls back to
    the temp config rather than the real one.
    """
    monkeypatch.delenv("RISKMANAGED_TOKEN", raising=False)
    monkeypatch.delenv("RISKMANAGED_URL", raising=False)


@pytest.fixture
def write_config(_isolate_credentials):
    """Write a config.json into the isolated dir."""

    def _write(**data):
        _isolate_credentials.mkdir(parents=True, exist_ok=True)
        path = _isolate_credentials / "config.json"
        path.write_text(json.dumps(data))
        return path

    return _write


@pytest.fixture
def mock_api():
    """A respx router over the external API.

    `assert_all_mocked=True` is the point: an unmocked request raises
    `AllMockedAssertionError` rather than hitting the network. Without it a
    typo'd path in the client would silently attempt a real call.
    """
    with respx.mock(base_url=API_ROOT, assert_all_mocked=True) as router:
        yield router


@pytest.fixture
def client(mock_api):
    """A `RiskManagedClient` bound to the fake API."""
    from riskmanaged_mcp.client import RiskManagedClient

    return RiskManagedClient(token=FAKE_TOKEN, base_url=FAKE_BASE_URL)
