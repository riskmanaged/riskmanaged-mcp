"""The browser login flow.

`riskmanaged auth login` is the documented way to get a token, and it was
completely dead: `oauth.py` contained a non-ASCII character inside a `bytes`
literal, which is a **SyntaxError** — the module could not be imported at all.
Behind that sat a missing `import os` and three structlog-style logging calls on
a stdlib logger, each of which would have raised in turn.

Three bugs stacked in one file, none of them caught, because nothing ever
imported it. So the first test here is simply that the module loads. It looks
trivial; it is the one that would have caught all three.
"""

from __future__ import annotations

import importlib
import json
import stat
import threading
import urllib.parse
import urllib.request

import pytest


class TestModuleLoads:
    def test_oauth_imports(self):
        """A SyntaxError here takes down `auth login` entirely and is invisible
        to every other test, since nothing else imports this module."""
        module = importlib.import_module("riskmanaged_mcp.oauth")
        assert hasattr(module, "oauth_login")

    def test_auth_command_group_imports_it(self):
        """The CLI must be able to reach the flow it advertises."""
        from riskmanaged_mcp.commands import auth

        assert hasattr(auth, "app")

    def test_module_source_is_ascii_safe_in_byte_literals(self):
        """The original failure mode: a typographic dash inside `b"..."`.

        Non-ASCII in a *str* literal is fine; in a bytes literal it does not
        compile. Worth pinning, because the em-dash is easy to reintroduce by
        copy-paste from prose.
        """
        import ast
        import inspect

        from riskmanaged_mcp import oauth

        source = inspect.getsource(oauth)
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Constant) and isinstance(node.value, bytes):
                node.value.decode("ascii")  # raises if a non-ASCII byte slipped in


class TestAuthorizeUrl:
    def test_carries_port_and_state(self):
        from riskmanaged_mcp import oauth

        url = oauth._build_authorize_url("https://x.invalid", 54321, "nonce-123")
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)

        assert parsed.path == "/mcp-authorize"
        assert params["port"] == ["54321"]
        assert params["state"] == ["nonce-123"]

    def test_trailing_slash_is_not_doubled(self):
        from riskmanaged_mcp import oauth

        url = oauth._build_authorize_url("https://x.invalid/", 1, "s")
        assert "//mcp-authorize" not in url


class TestCallbackListener:
    """Drive the real localhost listener rather than mocking it — the CSRF
    check is the security-relevant part of this flow."""

    def _serve_once(self, expected_state: str):
        from http.server import HTTPServer

        from riskmanaged_mcp import oauth

        oauth._CallbackHandler.expected_state = expected_state
        oauth._CallbackHandler.received_code = None
        oauth._CallbackHandler.received_state = None

        server = HTTPServer(("127.0.0.1", 0), oauth._CallbackHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server, server.server_address[1]

    def _post(self, port: int, **fields):
        data = urllib.parse.urlencode(fields).encode()
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/callback", data=data
        )
        try:
            with urllib.request.urlopen(request) as response:
                return response.status
        except urllib.error.HTTPError as exc:
            return exc.code

    def test_matching_state_captures_the_code(self):
        from riskmanaged_mcp import oauth

        server, port = self._serve_once("good-state")
        try:
            status = self._post(port, code="the-code", state="good-state")
            assert status == 200
            assert oauth._CallbackHandler.received_code == "the-code"
        finally:
            server.shutdown()

    def test_mismatched_state_is_rejected(self):
        """Without this, any page that learns the code could complete the flow
        against a CLI listener it does not own."""
        from riskmanaged_mcp import oauth

        server, port = self._serve_once("good-state")
        try:
            status = self._post(port, code="attacker-code", state="wrong-state")
            assert status == 400
            assert oauth._CallbackHandler.received_code is None, (
                "a code arriving with the wrong state must not be accepted"
            )
        finally:
            server.shutdown()


class TestSaveCredentials:
    def test_token_file_is_owner_only(self):
        """The file holds a 90-day API token with full account access.

        Note this is `oauth.save_credentials`, not `config.save_config` — the
        latter does *not* chmod, despite three docstrings implying it does.
        """
        from riskmanaged_mcp import config, oauth

        oauth.save_credentials("secret-token", "https://x.invalid")

        mode = stat.S_IMODE(config.CONFIG_FILE.stat().st_mode)
        assert mode == 0o600, f"expected 0600, got {oct(mode)}"

    def test_credentials_round_trip(self):
        from riskmanaged_mcp import config, oauth

        oauth.save_credentials("secret-token", "https://x.invalid")

        stored = json.loads(config.CONFIG_FILE.read_text())
        assert stored["token"] == "secret-token"
        assert stored["base_url"] == "https://x.invalid"
