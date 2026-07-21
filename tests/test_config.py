"""Credential resolution, and proof that the test harness is actually isolated.

The isolation tests come first deliberately. Every other file in this suite
assumes `_isolate_credentials` works; if it silently didn't, the suite would
read the developer's real token and call production while still passing. So the
guarantee gets asserted rather than assumed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from riskmanaged_mcp import config

from .conftest import FAKE_BASE_URL, FAKE_TOKEN


class TestHarnessIsolation:
    """If these fail, nothing else in the suite can be trusted."""

    def test_config_file_is_redirected_away_from_home(self):
        real_home_config = Path.home() / ".riskmanaged" / "config.json"
        assert config.CONFIG_FILE != real_home_config
        assert Path.home() not in config.CONFIG_FILE.parents, (
            "the isolated config must not live under the real HOME"
        )

    def test_writing_config_does_not_touch_the_real_one(self):
        """`save_config` reads the module global at call time, which is why
        patching the attribute works where patching HOME would not."""
        config.save_config({"token": "written-by-a-test"})
        assert config.CONFIG_FILE.exists()
        assert Path.home() not in config.CONFIG_FILE.parents

    def test_default_base_url_is_production_and_never_the_test_target(self):
        """A reminder in test form: the module default is a live host, so any
        test that reaches the network would reach production."""
        assert config.DEFAULT_BASE_URL == "https://agent.riskmanaged.io"
        assert config.get_base_url() == FAKE_BASE_URL


class TestTokenPrecedence:
    def test_env_wins(self, write_config):
        write_config(token="on-disk")
        assert config.get_token() == FAKE_TOKEN

    def test_disk_used_when_env_absent(self, no_env_credentials, write_config):
        write_config(token="on-disk")
        assert config.get_token() == "on-disk"

    def test_none_when_neither(self, no_env_credentials):
        assert config.get_token() is None


class TestBaseUrlPrecedence:
    def test_env_wins(self, write_config):
        write_config(base_url="https://on-disk.invalid")
        assert config.get_base_url() == FAKE_BASE_URL

    def test_disk_used_when_env_absent(self, no_env_credentials, write_config):
        write_config(base_url="https://on-disk.invalid")
        assert config.get_base_url() == "https://on-disk.invalid"

    def test_falls_back_to_default(self, no_env_credentials):
        assert config.get_base_url() == config.DEFAULT_BASE_URL


class TestLoadConfig:
    def test_missing_file_is_empty_dict(self, no_env_credentials):
        assert config.load_config() == {}

    def test_malformed_json_is_reported_clearly(self, no_env_credentials):
        """A truncated or hand-edited config should say so.

        `json.loads` raises `JSONDecodeError`, which reaches the user as a
        stack trace mentioning neither the file nor what to do about it. The
        CLI's own error path can't help because it never learns which file was
        at fault.
        """
        config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        config.CONFIG_FILE.write_text("{not valid json")

        with pytest.raises(ValueError) as exc:
            config.load_config()

        message = str(exc.value)
        assert str(config.CONFIG_FILE) in message, (
            "the error must name the file the user has to fix"
        )


class TestSetCredentials:
    def test_stores_token(self, no_env_credentials):
        config.set_credentials("abc123")
        assert json.loads(config.CONFIG_FILE.read_text())["token"] == "abc123"

    def test_omitted_base_url_preserves_the_existing_one(self, no_env_credentials):
        config.set_credentials("first", base_url="https://kept.invalid")
        config.set_credentials("second")

        stored = json.loads(config.CONFIG_FILE.read_text())
        assert stored["token"] == "second"
        assert stored["base_url"] == "https://kept.invalid"

    def test_creates_the_directory(self, no_env_credentials):
        assert not config.CONFIG_DIR.exists()
        config.set_credentials("abc123")
        assert config.CONFIG_DIR.is_dir()
