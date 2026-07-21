"""Config management — stores API token and base URL in ~/.riskmanaged/config.json.

Precedence for reads: env vars (RISKMANAGED_TOKEN / RISKMANAGED_URL)
override the on-disk config. This lets CI / Docker / the MCP server
itself pass credentials without writing to disk.
"""

import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".riskmanaged"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_BASE_URL = "https://agent.riskmanaged.io"


def _ensure_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    """Load config from disk. Returns empty dict if not found.

    A corrupt file raises a `ValueError` that names the path: the bare
    `JSONDecodeError` reports a line and column but not *which* file, which is
    useless when the file is one the user never opens by hand.
    """
    if not CONFIG_FILE.exists():
        return {}
    raw = CONFIG_FILE.read_text()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Config file {CONFIG_FILE} is not valid JSON ({exc}). "
            f"Delete it and re-run: riskmanaged auth login"
        ) from exc


def save_config(data: dict):
    """Save config to disk."""
    _ensure_dir()
    CONFIG_FILE.write_text(json.dumps(data, indent=2))


def get_token() -> str | None:
    """Get the stored API token. Env var RISKMANAGED_TOKEN wins."""
    env_token = os.environ.get("RISKMANAGED_TOKEN")
    if env_token:
        return env_token
    return load_config().get("token")


def get_base_url() -> str:
    """Get the stored base URL. Env var RISKMANAGED_URL wins."""
    return (
        os.environ.get("RISKMANAGED_URL")
        or load_config().get("base_url")
        or DEFAULT_BASE_URL
    )


def set_credentials(token: str, base_url: str = None):
    """Store API token and optional base URL."""
    cfg = load_config()
    cfg["token"] = token
    if base_url:
        cfg["base_url"] = base_url
    save_config(cfg)
