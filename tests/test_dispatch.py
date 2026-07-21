"""`_dispatch` argument translation, and how `call_tool` reports failure.

`_dispatch` is a long if-chain translating a tool's argument dict into a client
call. It needs no HTTP — a `Mock` client records exactly what it was asked for —
so the defaults and the arg-shuffling are cheap to pin and easy to break
silently.

`call_tool` is the other half, and it had two real problems:

  * `_get_client()` sat outside the `try`, so an unconfigured token escaped as an
    exception from a different layer than every other failure.
  * *Every* failure was swallowed into a `TextContent` string. The MCP SDK marks
    a result as an error only when the handler **raises** (it catches and calls
    `_make_error_result`), so catching everything meant returning `isError:
    False` with the word "Error" in the body. To a model that is a successful
    tool call whose result happens to be prose, which is how "your token
    expired" ends up being reasoned about as though it were data.
"""

from __future__ import annotations

import asyncio
from unittest.mock import Mock

import httpx
import pytest

from riskmanaged_mcp import mcp_server


@pytest.fixture
def fake_client():
    return Mock()


def _call_tool(name: str, args: dict):
    return asyncio.run(mcp_server.call_tool(name, args))


def _text(result) -> str:
    return "".join(part.text for part in result)


class TestArgumentTranslation:
    def test_simple_passthrough(self, fake_client):
        mcp_server._dispatch(fake_client, "get_strategy", {"strategy_id": "S1"})
        fake_client.get_strategy.assert_called_once_with("S1")

    def test_no_arg_tool(self, fake_client):
        mcp_server._dispatch(fake_client, "get_me", {})
        fake_client.get_me.assert_called_once_with()

    def test_search_tickers_defaults_to_binance(self, fake_client):
        mcp_server._dispatch(fake_client, "search_tickers", {"search": "BTC"})
        fake_client.search_tickers.assert_called_once_with(
            search="BTC", exchange="binance"
        )

    def test_none_valued_args_are_stripped(self, fake_client):
        """`list_strategies` splats its args as query params. Passing `None`
        through would serialise as the literal string 'None' and filter the
        result set to nothing."""
        mcp_server._dispatch(
            fake_client,
            "list_strategies",
            {"search": "rsi", "timeframe": None, "limit": 10},
        )
        fake_client.list_strategies.assert_called_once_with(search="rsi", limit=10)

    def test_promotion_events_default_limit(self, fake_client):
        mcp_server._dispatch(
            fake_client, "get_committee_promotion_events", {"instance_id": "I1"}
        )
        _, kwargs = fake_client.get_committee_promotion_events.call_args
        assert kwargs["limit"] > 0

    def test_reject_proposal_forwards_the_reason(self, fake_client):
        mcp_server._dispatch(
            fake_client,
            "reject_proposal",
            {"proposal_id": "P1", "reason": "too risky"},
        )
        args, _ = fake_client.reject_proposal.call_args
        assert args[0] == "P1"
        assert args[1]["reason"] == "too risky"

    def test_unknown_tool_raises(self, fake_client):
        with pytest.raises(ValueError, match="Unknown tool"):
            mcp_server._dispatch(fake_client, "not_a_tool", {})


class TestIdentityIsNeverTakenFromArguments:
    """Complements the schema check in test_tools.py: even if a caller sends a
    `user_id` the schema doesn't advertise, it must not reach the client."""

    def test_user_id_is_ignored_on_a_self_scoped_tool(self, fake_client):
        mcp_server._dispatch(
            fake_client, "list_model_routes", {"user_id": "somebody-else"}
        )
        args, kwargs = fake_client.list_model_routes.call_args
        assert "somebody-else" not in args
        assert "somebody-else" not in kwargs.values()

    def test_admin_tool_does_forward_its_target(self, fake_client):
        """The deliberate exception — an admin naming who to report on."""
        mcp_server._dispatch(fake_client, "admin_per_user_spend", {"user_id": "U9"})
        fake_client.admin_per_user_spend.assert_called_once_with("U9")


class TestCallToolErrorReporting:
    def test_success_returns_the_payload_as_json(self, monkeypatch):
        client = Mock()
        client.get_me.return_value = {"id": "U1", "username": "tester"}
        monkeypatch.setattr(mcp_server, "_get_client", lambda: client)

        assert "tester" in _text(_call_tool("get_me", {}))

    def test_missing_credentials_are_reported_like_any_other_failure(
        self, monkeypatch
    ):
        """`_get_client()` used to sit outside the try, so this escaped as a
        bare ValueError from a different code path than every other error."""

        def _no_token():
            raise ValueError("No API token configured. Run: riskmanaged auth login")

        monkeypatch.setattr(mcp_server, "_get_client", _no_token)

        with pytest.raises(ValueError, match="auth login"):
            _call_tool("get_me", {})

    def test_http_errors_raise_so_the_sdk_marks_them_as_errors(self, monkeypatch):
        """The SDK sets `isError: True` only when the handler raises; returning
        a string that starts with "Error:" is reported as a *successful* call."""
        client = Mock()
        request = httpx.Request("GET", "https://x.invalid/api/external/account/me")
        response = httpx.Response(
            401, json={"detail": "Invalid, expired, or revoked API token"},
            request=request,
        )
        client.get_me.side_effect = httpx.HTTPStatusError(
            "401", request=request, response=response
        )
        monkeypatch.setattr(mcp_server, "_get_client", lambda: client)

        with pytest.raises(Exception) as exc:
            _call_tool("get_me", {})

        message = str(exc.value)
        assert "401" in message
        assert "revoked API token" in message, (
            "the response body carries the actionable detail; str(HTTPStatusError) "
            "drops it"
        )

    def test_unknown_tool_surfaces_as_an_error(self, monkeypatch):
        monkeypatch.setattr(mcp_server, "_get_client", lambda: Mock())
        with pytest.raises(ValueError, match="Unknown tool"):
            _call_tool("no_such_tool", {})


class TestResourceHandling:
    def test_context_resource_is_served(self):
        text = asyncio.run(mcp_server.read_resource("riskmanaged://context"))
        assert "RiskManaged" in text

    def test_unknown_resource_raises(self):
        with pytest.raises(ValueError, match="Unknown resource"):
            asyncio.run(mcp_server.read_resource("riskmanaged://nope"))
