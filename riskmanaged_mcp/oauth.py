"""OAuth browser-flow login for the RiskManaged MCP CLI.

W6.4: the user runs `riskmanaged auth login` → a localhost HTTP
listener is bound to a random free port → the browser opens to
`{base_url}/mcp-authorize?code=<cli_generated_code>&port=<port>&redirect_uri=...`
→ the user clicks "Authorize" on the page → the page POSTs the
code back to the CLI's listener → the CLI exchanges the code
for a long-lived API token via `POST /mcp-token-exchange` →
saves the token to `~/.riskmanaged/config.json` (chmod 600).

The state nonce prevents CSRF (a malicious page on the same
origin that knows the code can't replay it because it doesn't
know the state). The state is a separate random nonce generated
by the CLI and embedded in the URL; the page returns it on
the callback, and the CLI validates it matches what it sent.

Single-use codes: the in-memory store deletes the code on first
exchange. The `mcp-token-exchange` endpoint enforces this.

Security:
  - The listener binds to 127.0.0.1 (no LAN exposure).
  - The state is 32 bytes of `secrets.token_urlsafe`.
  - The token file is chmod 600.
  - The user has to actively click "Authorize" in their browser
    (the CLI cannot mint a token on the user's behalf without
    their session cookie).
"""

from __future__ import annotations

import logging
import os
import secrets
import socket
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional, Tuple

import httpx

from riskmanaged_mcp import config

logger = logging.getLogger(__name__)

# How long the CLI waits for the user to click "Authorize" before
# timing out. 60s matches the server-side code TTL.
OAUTH_TIMEOUT_SECONDS = 60


class _CallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler that captures the OAuth callback from the
    /mcp-authorize page. The page POSTs the original code + the
    CLI's state nonce to the listener. The handler validates the
    state, stores the code on the server instance, and serves a
    tiny "you can close this tab now" HTML page.

    A class-level attribute holds the captured values; the CLI
    polls the server instance after starting it.
    """

    # Populated when the CLI binds the listener
    expected_state: str = ""
    received_code: Optional[str] = None
    received_state: Optional[str] = None

    def log_message(self, format, *args):
        # Quiet the default access log; we have our own logger
        return

    def do_POST(self):  # noqa: N802 — http.server convention
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length else ""
        params = dict(urllib.parse.parse_qsl(body))
        # Validate state to prevent CSRF
        if params.get("state") != self.expected_state:
            self.send_response(400)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"State mismatch - possible CSRF")
            return
        _CallbackHandler.received_code = params.get("code")
        _CallbackHandler.received_state = params.get("state")
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(
            b"<html><body><h2>Authorized</h2>"
            b"<p>You can close this tab and return to your terminal.</p>"
            b"</body></html>"
        )

    def do_GET(self):  # noqa: N802
        # Health check — the CLI pings the listener to confirm it's up
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"ok")


def _pick_free_port() -> int:
    """Bind to port 0 to get a kernel-picked free port, then release
    the socket. The listener rebinds immediately after, so there's
    a small window where another process could grab the port —
    acceptable risk for a 60s OAuth window."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _build_authorize_url(base_url: str, port: int, state: str) -> str:
    """Construct the URL the CLI opens the browser to.

    The page reads `port` (so it knows where to POST back) and
    `state` (the CLI's CSRF nonce). The `code` is NOT yet known —
    the page mints it via `POST /mcp-authorize` with the user's
    session cookie, then POSTs `(code, state)` back to the
    localhost listener.
    """
    return (
        f"{base_url.rstrip('/')}/mcp-authorize"
        f"?port={port}&state={urllib.parse.quote(state)}"
    )


def oauth_login(base_url: str) -> Tuple[str, str]:
    """Run the OAuth browser flow. Returns `(token, base_url)` on
    success, raises on timeout/error.

    The flow:
      1. Pick a free port + generate a state nonce.
      2. Start a localhost HTTP listener on that port.
      3. Open the browser to `{base_url}/mcp-authorize?port=<port>&state=<state>`.
         The `code` is NOT yet known — the page will mint it via
         `POST /mcp-authorize` with the user's session cookie.
      4. The page reads `port` + `state` from the URL, calls
         `POST /mcp-authorize` to mint a code (with the user's cookie),
         then POSTs `(code, state)` back to `http://127.0.0.1:<port>/callback`.
      5. The CLI's listener captures the code, validates the state,
         then calls `POST /mcp-token-exchange` with the code.
      6. The server returns a fresh API token.
      7. The CLI saves the token to disk and shuts down the listener.

    The page mints the code, not the CLI, because the page has
    the user's session cookie. The CLI never sees the cookie.
    """
    port = _pick_free_port()
    state = secrets.token_urlsafe(32)

    # Reset the handler's state
    _CallbackHandler.expected_state = state
    _CallbackHandler.received_code = None
    _CallbackHandler.received_state = None

    server = HTTPServer(("127.0.0.1", port), _CallbackHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    # NB: this module's `logger` is a stdlib logging.Logger, not structlog —
    # keyword context has to be interpolated, not passed as kwargs.
    logger.info("oauth.listener.bound port=%s", port)

    # Open the browser. The page mints the code (via the user's
    # session cookie) and POSTs it back to us.
    authorize_url = _build_authorize_url(base_url, port, state)
    print(f"Opening browser to: {authorize_url}")
    if not webbrowser.open(authorize_url):
        print("Could not open browser. Please visit the URL above manually.")

    # Wait for the callback
    deadline = time.time() + OAUTH_TIMEOUT_SECONDS
    while time.time() < deadline:
        if _CallbackHandler.received_code:
            break
        time.sleep(0.2)
    else:
        server.shutdown()
        raise TimeoutError(
            f"OAuth flow timed out after {OAUTH_TIMEOUT_SECONDS}s. "
            f"User did not click 'Authorize' in the browser."
        )

    code = _CallbackHandler.received_code
    server.shutdown()
    logger.info("oauth.code.received")

    # Exchange the code for a token
    with httpx.Client(base_url=base_url, timeout=30.0) as client:
        resp = client.post("/api/internal/auth/mcp-token-exchange", json={"code": code})
        resp.raise_for_status()
        data = resp.json()

    token = data["token"]
    logger.info("oauth.token.minted name=%s", data.get("name"))
    return token, base_url


def save_credentials(token: str, base_url: str) -> None:
    """Persist the token + base URL to ~/.riskmanaged/config.json
    with chmod 600. Overwrites any existing config."""
    config.set_credentials(token, base_url)
    # Tighten perms (config.set_credentials may have created the
    # file with the default umask).
    cfg_path = config.CONFIG_FILE
    if cfg_path.exists():
        os.chmod(cfg_path, 0o600)
        logger.info("oauth.credentials.saved path=%s", cfg_path)
