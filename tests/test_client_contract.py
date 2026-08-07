"""The HTTP contract: every client method against the request it must issue.

`CASES` is a hand-written table, deliberately. Deriving the expectations from
`client.py` would make this tautological — it would assert the code does what
the code does. Written out, the path lives in two places, so changing an
endpoint means changing both, and an accidental change fails here.

This is the drift net for the platform boundary. Every entry is one route the
open-source client depends on; if the backend moves it, this is where it shows.

The whole file is offline: `mock_api` runs respx with `assert_all_mocked`, so an
unmocked request raises rather than reaching the network. That matters more than
usual here, because the client's default base URL is production.
"""

from __future__ import annotations

import inspect

import httpx
import pytest

from riskmanaged_mcp.client import RiskManagedClient

from .conftest import API_ROOT, FAKE_BASE_URL, FAKE_TOKEN

S = "STRAT1"
I = "INST1"
T = "TMPL1"
G = "GRID1"
C = "CONN1"
P = "PROP1"

# (method, kwargs, expected verb, expected path under /api/external)
CASES: list[tuple[str, dict, str, str]] = [
    # ---- Account ----
    ("get_me", {}, "GET", "/account/me"),
    ("get_positions", {"state": "open"}, "GET", "/account/positions"),
    ("get_grid_usage", {}, "GET", "/account/grid-usage"),
    # ---- Strategies ----
    ("list_strategies", {"limit": 10}, "GET", "/strategies/"),
    ("get_strategy", {"strategy_id": S}, "GET", f"/strategies/{S}"),
    ("create_strategy", {"data": {"name": "x"}}, "POST", "/strategies/"),
    ("update_strategy", {"strategy_id": S, "data": {}}, "PUT", f"/strategies/{S}"),
    ("delete_strategy", {"strategy_id": S}, "DELETE", f"/strategies/{S}"),
    ("archive_strategy", {"strategy_id": S}, "POST", f"/strategies/{S}/archive"),
    ("unarchive_strategy", {"strategy_id": S}, "POST", f"/strategies/{S}/unarchive"),
    ("clone_strategy", {"strategy_id": S}, "POST", f"/strategies/{S}/clone"),
    # ---- Indicators ----
    (
        "add_indicator",
        {"strategy_id": S, "indicator_name": "RSI", "config": {"length": 14}},
        "POST",
        f"/strategies/{S}/indicators/RSI",
    ),
    (
        "update_indicator",
        {"strategy_id": S, "indicator_name": "RSI", "config": {"length": 21}},
        "PUT",
        f"/strategies/{S}/indicators/RSI",
    ),
    (
        "delete_indicator",
        {"strategy_id": S, "indicator_name": "RSI"},
        "DELETE",
        f"/strategies/{S}/indicators/RSI",
    ),
    # ---- Signals ----
    (
        "add_signal_group",
        {"strategy_id": S, "data": {"name": "entry"}},
        "POST",
        f"/strategies/{S}/signals",
    ),
    (
        "delete_signal_group",
        {"strategy_id": S, "signal_name": "entry"},
        "DELETE",
        f"/strategies/{S}/signals/entry",
    ),
    (
        "add_signal_rule",
        {
            "strategy_id": S,
            "signal_name": "entry",
            "trigger_action": "enter_position",
            "trigger_direction": "long",
            "conditions": [],
        },
        "POST",
        f"/strategies/{S}/signals/entry/rules",
    ),
    (
        "edit_signal_rule",
        {
            "strategy_id": S,
            "signal_name": "entry",
            "rule_index": 0,
            "trigger_action": "enter_position",
            "trigger_direction": "long",
            "conditions": [],
        },
        "PUT",
        f"/strategies/{S}/signals/entry/rules/0",
    ),
    (
        "delete_signal_rule",
        {"strategy_id": S, "signal_name": "entry", "rule_index": 0},
        "DELETE",
        f"/strategies/{S}/signals/entry/rules/0",
    ),
    # ---- Bias ----
    (
        "add_bias_generator",
        {"strategy_id": S, "data": {"name": "trend"}},
        "POST",
        f"/strategies/{S}/bias",
    ),
    (
        "delete_bias_generator",
        {"strategy_id": S, "bias_name": "trend"},
        "DELETE",
        f"/strategies/{S}/bias/trend",
    ),
    (
        "add_bias_rule",
        {
            "strategy_id": S,
            "bias_name": "trend",
            "bias_direction": "long",
            "conditions": [],
        },
        "POST",
        f"/strategies/{S}/bias/trend/rules",
    ),
    (
        "edit_bias_rule",
        {
            "strategy_id": S,
            "bias_name": "trend",
            "rule_index": 0,
            "bias_direction": "long",
            "conditions": [],
        },
        "PUT",
        f"/strategies/{S}/bias/trend/rules/0",
    ),
    (
        "delete_bias_rule",
        {"strategy_id": S, "bias_name": "trend", "rule_index": 0},
        "DELETE",
        f"/strategies/{S}/bias/trend/rules/0",
    ),
    # ---- Risk management ----
    (
        "set_take_profit",
        {"strategy_id": S, "tp_type": "TakeProfitSpread", "config": {}},
        "PUT",
        f"/strategies/{S}/risk/take-profit/TakeProfitSpread",
    ),
    (
        "set_stop_loss",
        {"strategy_id": S, "sl_type": "StopLossSimple", "config": {}},
        "PUT",
        f"/strategies/{S}/risk/stop-loss/StopLossSimple",
    ),
    (
        "remove_take_profit",
        {"strategy_id": S},
        "DELETE",
        f"/strategies/{S}/risk/take-profit",
    ),
    (
        "remove_stop_loss",
        {"strategy_id": S},
        "DELETE",
        f"/strategies/{S}/risk/stop-loss",
    ),
    # ---- Backtest / Monte Carlo ----
    ("run_backtest", {"strategy_id": S}, "POST", f"/strategies/{S}/backtest"),
    ("get_reports", {"strategy_id": S}, "GET", f"/strategies/{S}/reports"),
    ("run_monte_carlo", {"strategy_id": S}, "POST", f"/strategies/{S}/montecarlo"),
    ("get_monte_carlo", {"strategy_id": S}, "GET", f"/strategies/{S}/montecarlo"),
    # ---- Versioning ----
    ("commit_version", {"strategy_id": S}, "POST", f"/strategies/{S}/commit"),
    ("get_versions", {"strategy_id": S}, "GET", f"/strategies/{S}/versions"),
    (
        "restore_version",
        {"strategy_id": S, "version_id": 3},
        "POST",
        f"/strategies/{S}/restore/3",
    ),
    # ---- Grid templates ----
    ("create_grid_template", {"strategy_id": S}, "POST", "/grids/templates"),
    ("list_grid_templates", {}, "GET", "/grids/templates"),
    ("get_grid_template", {"template_id": T}, "GET", f"/grids/templates/{T}"),
    (
        "update_grid_template",
        {"template_id": T, "data": {}},
        "PUT",
        f"/grids/templates/{T}",
    ),
    ("delete_grid_template", {"template_id": T}, "DELETE", f"/grids/templates/{T}"),
    (
        "check_variations",
        {"template_id": T},
        "GET",
        f"/grids/templates/{T}/variations",
    ),
    # ---- Grids ----
    ("create_grid", {"template_id": T}, "POST", "/grids/"),
    ("list_grids", {}, "GET", "/grids/"),
    ("get_grid", {"grid_id": G}, "GET", f"/grids/{G}"),
    ("analyze_grid", {"grid_id": G}, "POST", f"/grids/{G}/analyze"),
    ("grid_suggestions", {"grid_id": G}, "GET", f"/grids/{G}/suggestions"),
    ("refine_grid", {"grid_id": G, "kind": "zoom_in"}, "POST", f"/grids/{G}/refine"),
    ("archive_grid", {"grid_id": G}, "POST", f"/grids/{G}/archive"),
    # ---- Reference (public) ----
    ("list_indicator_types", {}, "GET", "/reference/indicators"),
    (
        "get_indicator_schema",
        {"indicator_name": "RSI"},
        "GET",
        "/reference/indicators/RSI/schema",
    ),
    ("list_patterns", {}, "GET", "/reference/patterns"),
    ("list_take_profit_types", {}, "GET", "/reference/risk/take-profit-types"),
    ("list_stop_loss_types", {}, "GET", "/reference/risk/stop-loss-types"),
    (
        "get_take_profit_schema",
        {"name": "TakeProfitSpread"},
        "GET",
        "/reference/risk/take-profit/TakeProfitSpread/schema",
    ),
    (
        "get_stop_loss_schema",
        {"name": "StopLossSimple"},
        "GET",
        "/reference/risk/stop-loss/StopLossSimple/schema",
    ),
    ("search_tickers", {"search": "BTC"}, "GET", "/reference/tickers"),
    ("get_constants", {}, "GET", "/reference/constants"),
    # ---- Agent: templates + committees ----
    ("list_templates", {}, "GET", "/agent/templates"),
    ("get_template", {"slug": "macro-fund"}, "GET", "/agent/templates/macro-fund"),
    ("list_committees", {}, "GET", "/agent/instances"),
    ("get_committee", {"instance_id": I}, "GET", f"/agent/instances/{I}"),
    ("clone_template", {"body": {}}, "POST", "/agent/instances/from-template"),
    ("delete_committee", {"instance_id": I}, "DELETE", f"/agent/instances/{I}"),
    (
        "get_committee_messages",
        {"instance_id": I},
        "GET",
        f"/agent/instances/{I}/messages",
    ),
    (
        "get_committee_track_record",
        {"instance_id": I},
        "GET",
        f"/agent/instances/{I}/track-record-summary",
    ),
    ("set_committee_tier", {"instance_id": I, "body": {}}, "POST", f"/agent/instances/{I}/tier"),
    ("list_instance_runs", {"instance_id": I}, "GET", f"/agent/instances/{I}/runs"),
    # ---- Agent: promotion + rollback ----
    (
        "get_committee_promotion_status",
        {"instance_id": I},
        "GET",
        f"/agent/instances/{I}/promotion-status",
    ),
    (
        "get_committee_promotion_events",
        {"instance_id": I},
        "GET",
        f"/agent/instances/{I}/promotion-events",
    ),
    (
        "list_rollback_candidates",
        {"instance_id": I},
        "GET",
        f"/agent/instances/{I}/rollback-candidates",
    ),
    (
        "rollback_instance",
        {"instance_id": I, "event_id": "EV1"},
        "POST",
        f"/agent/instances/{I}/rollback",
    ),
    # ---- Agent: proposals ----
    # ---- Agent: model routes ----
    ("list_model_routes", {}, "GET", "/agent/model-routes"),
    ("upsert_model_route", {"body": {}}, "POST", "/agent/model-routes"),
    (
        "delete_model_route",
        {"task_class": "deep_reasoning"},
        "DELETE",
        "/agent/model-routes/deep_reasoning",
    ),
    # ---- Agent: LLM connections ----
    ("list_llm_connections", {}, "GET", "/agent/llm-connections"),
    ("create_llm_connection", {"body": {}}, "POST", "/agent/llm-connections/direct"),
    (
        "update_llm_connection",
        {"connection_id": C, "body": {}},
        "PATCH",
        f"/agent/llm-connections/{C}",
    ),
    (
        "delete_llm_connection",
        {"connection_id": C},
        "DELETE",
        f"/agent/llm-connections/{C}",
    ),
    (
        "test_llm_connection",
        {"connection_id": C},
        "POST",
        f"/agent/llm-connections/{C}/test",
    ),
    (
        "reveal_llm_connection_key",
        {"connection_id": C},
        "POST",
        f"/agent/llm-connections/{C}/reveal",
    ),
    # ---- Agent: news + macro ----
    ("list_news_articles", {"limit": 5}, "GET", "/agent/news/articles"),
    ("get_news_article", {"article_id": "ART1"}, "GET", "/agent/news/articles/ART1"),
    ("list_news_sources", {}, "GET", "/agent/news/sources"),
    ("list_macro_events", {"limit": 5}, "GET", "/agent/macro/events"),
    ("get_macro_event", {"event_id": "EVT1"}, "GET", "/agent/macro/events/EVT1"),
    # ---- Agent: user settings ----
    ("get_user_settings", {}, "GET", "/agent/user-settings"),
    ("set_daily_token_cap", {"cap": 1000}, "PUT", "/agent/user-settings"),
    # ---- Agent: admin observability ----
    (
        "admin_per_user_spend",
        {"user_id": "U1"},
        "GET",
        "/agent/admin/per-user-spend",
    ),
    (
        "admin_per_user_spend_history",
        {"user_id": "U1"},
        "GET",
        "/agent/admin/per-user-spend/history",
    ),
    (
        "admin_platform_spend_today",
        {},
        "GET",
        "/agent/admin/platform-spend-today",
    ),
    # ---- Community ----
    ("share_strategy", {"strategy_id": S}, "POST", f"/community/share/{S}"),
]

CASE_IDS = [c[0] for c in CASES]


def _public_methods() -> set[str]:
    return {
        name
        for name, _ in inspect.getmembers(RiskManagedClient, inspect.isfunction)
        if not name.startswith("_")
    }


class TestContractTableIsComplete:
    def test_every_client_method_has_a_case(self):
        """A new client method without a case is an untested route."""
        missing = sorted(_public_methods() - set(CASE_IDS))
        assert not missing, f"client methods with no contract case: {missing}"

    def test_no_case_names_a_dead_method(self):
        stale = sorted(set(CASE_IDS) - _public_methods())
        assert not stale, f"contract cases for methods that no longer exist: {stale}"

    def test_no_duplicate_cases(self):
        dupes = {n for n in CASE_IDS if CASE_IDS.count(n) > 1}
        assert not dupes, f"duplicate contract cases: {sorted(dupes)}"


class TestRequestShape:
    @pytest.mark.contract
    @pytest.mark.parametrize("method,kwargs,verb,path", CASES, ids=CASE_IDS)
    def test_issues_the_expected_request(
        self, client, mock_api, method, kwargs, verb, path
    ):
        mock_api.route().mock(return_value=httpx.Response(200, json={}))

        getattr(client, method)(**kwargs)

        request = mock_api.calls.last.request
        assert request.method == verb
        assert request.url.path == f"/api/external{path}"

    @pytest.mark.parametrize("method,kwargs,verb,path", CASES, ids=CASE_IDS)
    def test_every_request_is_authenticated(
        self, client, mock_api, method, kwargs, verb, path
    ):
        """A route reached without the bearer header would 401 in production
        but pass any test that only mocks the response."""
        mock_api.route().mock(return_value=httpx.Response(200, json={}))

        getattr(client, method)(**kwargs)

        assert (
            mock_api.calls.last.request.headers.get("authorization")
            == f"Bearer {FAKE_TOKEN}"
        )


class TestQueryAndBody:
    """Spot-checks that arguments actually reach the wire, since the path test
    above would pass even if every parameter were dropped."""

    def test_query_params_are_sent(self, client, mock_api):
        mock_api.route().mock(return_value=httpx.Response(200, json={}))
        client.get_committee_messages("I1", since_id=7, limit=25, direction="newest")

        params = mock_api.calls.last.request.url.params
        assert params["since_id"] == "7"
        assert params["limit"] == "25"
        assert params["direction"] == "newest"

    def test_json_body_is_sent(self, client, mock_api):
        import json

        mock_api.route().mock(return_value=httpx.Response(200, json={}))
        client.create_strategy({"name": "My Strategy", "root_ticker": "BTCUSDT"})

        body = json.loads(mock_api.calls.last.request.content)
        assert body["name"] == "My Strategy"
        assert body["root_ticker"] == "BTCUSDT"

    def test_conditions_are_json_encoded_into_the_query(self, client, mock_api):
        """Signal rules pass `conditions` as a JSON *string* in the query, not
        a body — an easy thing to break when refactoring."""
        import json

        mock_api.route().mock(return_value=httpx.Response(200, json={}))
        conditions = [{"trigger_line": "RSI.rsi", "trigger": "crossover",
                       "threshold_value": 30}]
        client.add_signal_rule("S1", "entry", "enter_position", "long", conditions)

        sent = mock_api.calls.last.request.url.params["conditions"]
        assert json.loads(sent) == conditions

    def test_set_daily_token_cap_can_clear_the_cap(self, client, mock_api):
        """`None` must survive as JSON null — a falsy-check would drop it and
        silently leave the cap in place."""
        import json

        mock_api.route().mock(return_value=httpx.Response(200, json={}))
        client.set_daily_token_cap(None)

        assert json.loads(mock_api.calls.last.request.content) == {
            "daily_token_cap": None
        }


class TestTransportBehaviour:
    def test_base_url_targets_the_external_api(self, client):
        assert str(client._client.base_url).rstrip("/") == API_ROOT

    def test_missing_token_is_rejected_with_a_usable_message(self, monkeypatch):
        monkeypatch.delenv("RISKMANAGED_TOKEN", raising=False)
        with pytest.raises(ValueError, match="auth login"):
            RiskManagedClient(base_url=FAKE_BASE_URL)

    @pytest.mark.parametrize("status", [400, 401, 403, 404, 422, 500])
    def test_error_statuses_raise(self, client, mock_api, status):
        mock_api.route().mock(return_value=httpx.Response(status, json={}))
        with pytest.raises(httpx.HTTPStatusError):
            client.get_me()

    def test_non_json_response_is_returned_as_text(self, client, mock_api):
        mock_api.route().mock(
            return_value=httpx.Response(200, text="plain", headers={
                "content-type": "text/plain"
            })
        )
        assert client.get_me() == "plain"
