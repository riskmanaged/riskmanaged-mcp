"""Config management — stores API token and base URL in ~/.riskmanaged/config.json."""

import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".riskmanaged"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_BASE_URL = "https://agent.riskmanaged.io"


def _ensure_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    """Load config from disk. Returns empty dict if not found."""
    if not CONFIG_FILE.exists():
        return {}
    return json.loads(CONFIG_FILE.read_text())


def save_config(data: dict):
    """Save config to disk."""
    _ensure_dir()
    CONFIG_FILE.write_text(json.dumps(data, indent=2))


def get_token() -> str | None:
    """Get the stored API token."""
    return load_config().get("token")


def get_base_url() -> str:
    """Get the stored base URL."""
    return load_config().get("base_url", DEFAULT_BASE_URL)


def set_credentials(token: str, base_url: str = None):
    """Store API token and optional base URL."""
    cfg = load_config()
    cfg["token"] = token
    if base_url:
        cfg["base_url"] = base_url
    save_config(cfg)
