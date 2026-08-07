"""HTTP client for the RiskManaged External API.

Everything goes through `/api/external/*`. There is one client, one base URL,
and one auth scheme.

This used to hold three clients: the external one plus two pointed at
`/api/internal/agent` and `/api/internal/community`, on the belief that the same
bearer token authenticated all three. It did not. The internal routers
JWT-decode the bearer, and an API token is an opaque random string, so every one
of those ~40 calls failed against any real deployment — silently, because the
internal routers skip auth entirely when `ENV` is `local`/`test`, which is what
the acceptance tests run under.

The W6 surface now lives at `/api/external/agent/*` and sharing at
`/api/external/community/*`. Those routes take identity from the token, so no
method here passes a `user_id` for the *acting* user. The only surviving
`user_id` arguments are on the admin endpoints, where the id names the user
being asked *about* and the caller must hold the `admins` role.
"""

import httpx
from riskmanaged_mcp.config import get_base_url, get_token


class RiskManagedClient:
    """Thin HTTP client wrapping the /api/external endpoints."""

    def __init__(self, token: str = None, base_url: str = None):
        self.token = token or get_token()
        self.base_url = (base_url or get_base_url()).rstrip("/")
        if not self.token:
            raise ValueError(
                "No API token configured. Run: riskmanaged auth login"
            )
        self._client = httpx.Client(
            base_url=f"{self.base_url}/api/external",
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=120.0,
        )

    def _request(self, method: str, path: str, **kwargs) -> dict | list:
        resp = self._client.request(method, path, **kwargs)
        resp.raise_for_status()
        if resp.headers.get("content-type", "").startswith("application/json"):
            return resp.json()
        return resp.text

    # ---- Account ----

    def get_me(self):
        return self._request("GET", "/account/me")

    def get_positions(self, **params):
        return self._request("GET", "/account/positions", params=params)

    def get_grid_usage(self):
        return self._request("GET", "/account/grid-usage")

    # ---- Strategies ----

    def list_strategies(self, **params):
        return self._request("GET", "/strategies/", params=params)

    def get_strategy(self, strategy_id: str):
        return self._request("GET", f"/strategies/{strategy_id}")

    def create_strategy(self, data: dict):
        return self._request("POST", "/strategies/", json=data)

    def update_strategy(self, strategy_id: str, data: dict):
        return self._request("PUT", f"/strategies/{strategy_id}", json=data)

    def delete_strategy(self, strategy_id: str):
        return self._request("DELETE", f"/strategies/{strategy_id}")

    def archive_strategy(self, strategy_id: str):
        return self._request("POST", f"/strategies/{strategy_id}/archive")

    def unarchive_strategy(self, strategy_id: str):
        return self._request("POST", f"/strategies/{strategy_id}/unarchive")

    def clone_strategy(self, strategy_id: str):
        return self._request("POST", f"/strategies/{strategy_id}/clone")

    # ---- Indicators ----

    def add_indicator(self, strategy_id: str, indicator_name: str, config: dict = None):
        return self._request(
            "POST",
            f"/strategies/{strategy_id}/indicators/{indicator_name}",
            json=config or {},
        )

    def update_indicator(
        self, strategy_id: str, indicator_name: str, config: dict, name: str = None
    ):
        params = {}
        if name:
            params["name"] = name
        return self._request(
            "PUT",
            f"/strategies/{strategy_id}/indicators/{indicator_name}",
            json=config,
            params=params,
        )

    def delete_indicator(self, strategy_id: str, indicator_name: str):
        return self._request(
            "DELETE", f"/strategies/{strategy_id}/indicators/{indicator_name}"
        )

    # ---- Signals ----

    def add_signal_group(self, strategy_id: str, data: dict):
        return self._request("POST", f"/strategies/{strategy_id}/signals", json=data)

    def delete_signal_group(self, strategy_id: str, signal_name: str):
        return self._request(
            "DELETE", f"/strategies/{strategy_id}/signals/{signal_name}"
        )

    def add_signal_rule(
        self,
        strategy_id: str,
        signal_name: str,
        trigger_action: str,
        trigger_direction: str,
        conditions: list,
    ):
        import json

        return self._request(
            "POST",
            f"/strategies/{strategy_id}/signals/{signal_name}/rules",
            params={
                "trigger_action": trigger_action,
                "trigger_direction": trigger_direction,
                "conditions": json.dumps(conditions),
            },
        )

    def edit_signal_rule(
        self,
        strategy_id: str,
        signal_name: str,
        rule_index: int,
        trigger_action: str,
        trigger_direction: str,
        conditions: list,
    ):
        import json

        return self._request(
            "PUT",
            f"/strategies/{strategy_id}/signals/{signal_name}/rules/{rule_index}",
            params={
                "trigger_action": trigger_action,
                "trigger_direction": trigger_direction,
                "conditions": json.dumps(conditions),
            },
        )

    def delete_signal_rule(self, strategy_id: str, signal_name: str, rule_index: int):
        return self._request(
            "DELETE",
            f"/strategies/{strategy_id}/signals/{signal_name}/rules/{rule_index}",
        )

    # ---- Bias ----

    def add_bias_generator(self, strategy_id: str, data: dict):
        return self._request("POST", f"/strategies/{strategy_id}/bias", json=data)

    def delete_bias_generator(self, strategy_id: str, bias_name: str):
        return self._request("DELETE", f"/strategies/{strategy_id}/bias/{bias_name}")

    def add_bias_rule(
        self, strategy_id: str, bias_name: str, bias_direction: str, conditions: list
    ):
        import json

        return self._request(
            "POST",
            f"/strategies/{strategy_id}/bias/{bias_name}/rules",
            params={
                "bias_direction": bias_direction,
                "conditions": json.dumps(conditions),
            },
        )

    def edit_bias_rule(
        self,
        strategy_id: str,
        bias_name: str,
        rule_index: int,
        bias_direction: str,
        conditions: list,
    ):
        import json

        return self._request(
            "PUT",
            f"/strategies/{strategy_id}/bias/{bias_name}/rules/{rule_index}",
            params={
                "bias_direction": bias_direction,
                "conditions": json.dumps(conditions),
            },
        )

    def delete_bias_rule(self, strategy_id: str, bias_name: str, rule_index: int):
        return self._request(
            "DELETE", f"/strategies/{strategy_id}/bias/{bias_name}/rules/{rule_index}"
        )

    # ---- Risk Management ----

    def set_take_profit(self, strategy_id: str, tp_type: str, config: dict):
        return self._request(
            "PUT", f"/strategies/{strategy_id}/risk/take-profit/{tp_type}", json=config
        )

    def set_stop_loss(self, strategy_id: str, sl_type: str, config: dict):
        return self._request(
            "PUT", f"/strategies/{strategy_id}/risk/stop-loss/{sl_type}", json=config
        )

    def remove_take_profit(self, strategy_id: str):
        return self._request("DELETE", f"/strategies/{strategy_id}/risk/take-profit")

    def remove_stop_loss(self, strategy_id: str):
        return self._request("DELETE", f"/strategies/{strategy_id}/risk/stop-loss")

    # ---- Backtest ----

    def run_backtest(self, strategy_id: str):
        return self._request("POST", f"/strategies/{strategy_id}/backtest")

    def get_reports(self, strategy_id: str):
        return self._request("GET", f"/strategies/{strategy_id}/reports")

    def run_monte_carlo(
        self,
        strategy_id: str,
        sims: int = 1000,
        bust: float = -0.20,
        goal: float = 0.50,
    ):
        return self._request(
            "POST",
            f"/strategies/{strategy_id}/montecarlo",
            json={"sims": sims, "bust": bust, "goal": goal},
        )

    def get_monte_carlo(self, strategy_id: str):
        return self._request("GET", f"/strategies/{strategy_id}/montecarlo")

    # ---- Versioning ----

    def commit_version(
        self, strategy_id: str, change_log: str = None, internal_notes: str = None
    ):
        return self._request(
            "POST",
            f"/strategies/{strategy_id}/commit",
            json={"change_log": change_log, "internal_notes": internal_notes},
        )

    def get_versions(self, strategy_id: str):
        return self._request("GET", f"/strategies/{strategy_id}/versions")

    def restore_version(self, strategy_id: str, version_id: int):
        return self._request("POST", f"/strategies/{strategy_id}/restore/{version_id}")

    # ---- Grid Templates ----

    def create_grid_template(self, strategy_id: str):
        return self._request(
            "POST", "/grids/templates", params={"strategy_id": strategy_id}
        )

    def list_grid_templates(self):
        return self._request("GET", "/grids/templates")

    def get_grid_template(self, template_id: str):
        return self._request("GET", f"/grids/templates/{template_id}")

    def update_grid_template(self, template_id: str, data: dict):
        return self._request("PUT", f"/grids/templates/{template_id}", json=data)

    def delete_grid_template(self, template_id: str):
        return self._request("DELETE", f"/grids/templates/{template_id}")

    def check_variations(self, template_id: str):
        return self._request("GET", f"/grids/templates/{template_id}/variations")

    # ---- Grids ----

    def create_grid(self, template_id: str):
        return self._request("POST", "/grids/", params={"template_id": template_id})

    def list_grids(self):
        return self._request("GET", "/grids/")

    def get_grid(self, grid_id: str):
        return self._request("GET", f"/grids/{grid_id}")

    def analyze_grid(self, grid_id: str):
        return self._request("POST", f"/grids/{grid_id}/analyze")

    def grid_suggestions(self, grid_id: str):
        return self._request("GET", f"/grids/{grid_id}/suggestions")

    def refine_grid(self, grid_id: str, kind: str, template_data: dict = None):
        return self._request(
            "POST",
            f"/grids/{grid_id}/refine",
            json={"kind": kind, "template_data": template_data},
        )

    def archive_grid(self, grid_id: str):
        return self._request("POST", f"/grids/{grid_id}/archive")

    # ---- Reference (public) ----

    def list_indicator_types(self):
        return self._request("GET", "/reference/indicators")

    def get_indicator_schema(self, indicator_name: str):
        return self._request("GET", f"/reference/indicators/{indicator_name}/schema")

    def list_patterns(self):
        return self._request("GET", "/reference/patterns")

    def list_take_profit_types(self):
        return self._request("GET", "/reference/risk/take-profit-types")

    def list_stop_loss_types(self):
        return self._request("GET", "/reference/risk/stop-loss-types")

    def get_take_profit_schema(self, name: str):
        return self._request("GET", f"/reference/risk/take-profit/{name}/schema")

    def get_stop_loss_schema(self, name: str):
        return self._request("GET", f"/reference/risk/stop-loss/{name}/schema")

    def search_tickers(self, search: str = "", exchange: str = "binance"):
        return self._request(
            "GET", "/reference/tickers", params={"search": search, "exchange": exchange}
        )

    def get_constants(self):
        return self._request("GET", "/reference/constants")


    # =================================================================
    # Agent surface — committees, templates, cadence, covered markets,
    # indicator readings, the decision line, model routes, LLM connections,
    # news, macro, user settings, observability. All under
    # /api/external/agent/*.
    #
    # None of these take the acting user's id: the server reads it from
    # the token. The `user_id` on the three admin methods names the user
    # being reported *on*, and requires the `admins` role.
    # =================================================================

    # ---- Templates ----

    def list_templates(self, enabled_only: bool = True):
        return self._request(
            "GET", "/agent/templates", params={"enabled_only": enabled_only}
        )

    def get_template(self, slug: str):
        return self._request("GET", f"/agent/templates/{slug}")

    # ---- Agent committees ----

    def list_committees(self, enabled_only: bool = True):
        return self._request(
            "GET", "/agent/instances", params={"enabled_only": enabled_only}
        )

    def get_committee(self, instance_id: str):
        return self._request("GET", f"/agent/instances/{instance_id}")

    def clone_template(self, body: dict):
        """Clone a template into a committee owned by the caller.
        Body: template_slug (required), name (required), plus optional
        binding_type / strategy_id / basket_id / autonomy_tier."""
        return self._request("POST", "/agent/instances/from-template", json=body)

    def delete_committee(self, instance_id: str):
        return self._request("DELETE", f"/agent/instances/{instance_id}")

    def get_committee_messages(
        self, instance_id: str, since_id: int = 0, limit: int = 50,
        direction: str = "oldest",
    ):
        return self._request(
            "GET",
            f"/agent/instances/{instance_id}/messages",
            params={
                "since_id": since_id,
                "limit": limit,
                "direction": direction,
            },
        )



    def list_instance_runs(self, instance_id: str, limit: int = 50,
                           strategy_id: str = ""):
        """The last `limit` runs for an instance, with token counts and
        estimated cost."""
        return self._request(
            "GET",
            f"/agent/instances/{instance_id}/runs",
            params={"limit": limit, "strategy_id": strategy_id},
        )

    # ---- Model routes ----

    def list_model_routes(self):
        return self._request("GET", "/agent/model-routes")

    def upsert_model_route(self, body: dict):
        """Body: task_class, provider, model."""
        return self._request("POST", "/agent/model-routes", json=body)

    def delete_model_route(self, task_class: str):
        return self._request("DELETE", f"/agent/model-routes/{task_class}")

    # ---- LLM connections ----

    def list_llm_connections(self):
        return self._request("GET", "/agent/llm-connections")

    def create_llm_connection(self, body: dict):
        """Body: provider, label, api_key."""
        return self._request("POST", "/agent/llm-connections/direct", json=body)

    def test_llm_connection(self, connection_id: str):
        return self._request(
            "POST", f"/agent/llm-connections/{connection_id}/test", json={}
        )

    def reveal_llm_connection_key(self, connection_id: str):
        return self._request(
            "POST", f"/agent/llm-connections/{connection_id}/reveal", json={}
        )

    def update_llm_connection(self, connection_id: str, body: dict):
        return self._request(
            "PATCH", f"/agent/llm-connections/{connection_id}", json=body
        )

    def delete_llm_connection(self, connection_id: str):
        return self._request("DELETE", f"/agent/llm-connections/{connection_id}")

    # ---- News ----

    def list_news_articles(self, **params):
        return self._request("GET", "/agent/news/articles", params=params)

    def get_news_article(self, article_id: str):
        return self._request("GET", f"/agent/news/articles/{article_id}")

    def list_news_sources(self):
        return self._request("GET", "/agent/news/sources")

    # ---- Macro ----

    def list_macro_events(self, **params):
        return self._request("GET", "/agent/macro/events", params=params)

    def get_macro_event(self, event_id: str):
        return self._request("GET", f"/agent/macro/events/{event_id}")

    # ---- User settings (daily LLM spend cap) ----

    def get_user_settings(self):
        return self._request("GET", "/agent/user-settings")

    def set_daily_token_cap(self, cap):
        """cap is an int (>= 0) or None to clear enforcement."""
        return self._request(
            "PUT", "/agent/user-settings", json={"daily_token_cap": cap}
        )

    # ---- Cadence, covered markets and readings ----

    def get_committee_cadence_board(self, instance_id: str):
        """One row per covered market: current call, standing, freshness."""
        return self._request("GET", f"/agent/instances/{instance_id}/decision-board")

    def set_committee_cadence(self, instance_id: str, body: dict):
        """Update cadence knobs: cadence_enabled, cadence_interval_seconds
        (30-minute floor), score_deadband_pct, context_bars."""
        return self._request(
            "PATCH", f"/agent/instances/{instance_id}/cadence", json=body
        )

    def list_committee_markets(self, instance_id: str):
        return self._request("GET", f"/agent/instances/{instance_id}/tickers")

    def add_committee_market(self, instance_id: str, symbol: str):
        return self._request(
            "POST", f"/agent/instances/{instance_id}/tickers", json={"symbol": symbol}
        )

    def set_committee_market_enabled(
        self, instance_id: str, symbol: str, enabled: bool
    ):
        return self._request(
            "PATCH",
            f"/agent/instances/{instance_id}/tickers/{symbol}",
            json={"enabled": enabled},
        )

    def remove_committee_market(self, instance_id: str, symbol: str):
        return self._request(
            "DELETE", f"/agent/instances/{instance_id}/tickers/{symbol}"
        )

    def get_committee_readings(self, instance_id: str):
        return self._request("GET", f"/agent/instances/{instance_id}/indicators")

    def set_committee_readings(self, instance_id: str, indicators: dict):
        """Replace the whole reading map, in the same {name: {type, config}}
        shape a strategy stores its indicators in."""
        return self._request(
            "PUT",
            f"/agent/instances/{instance_id}/indicators",
            json={"indicators": indicators},
        )

    # ---- The decision line ----

    def list_committee_decisions(
        self, instance_id: str, symbol: str = "", limit: int = 50
    ):
        params = {"limit": limit}
        if symbol:
            params["symbol"] = symbol
        return self._request(
            "GET", f"/agent/instances/{instance_id}/decisions", params=params
        )

    def get_committee_decision_summary(self, instance_id: str, symbol: str = ""):
        """Standing: cumulative points, recent form, accuracy, streak."""
        params = {"symbol": symbol} if symbol else None
        return self._request(
            "GET", f"/agent/instances/{instance_id}/decision-summary", params=params
        )

    # ---- Admin observability (requires the `admins` role) ----

    def admin_per_user_spend(self, user_id: str):
        """Per-user LLM spend for today UTC."""
        return self._request(
            "GET", "/agent/admin/per-user-spend", params={"user_id": user_id}
        )

    def admin_per_user_spend_history(self, user_id: str, days: int = 30):
        """Per-user daily spend for the last `days` days, oldest first."""
        return self._request(
            "GET",
            "/agent/admin/per-user-spend/history",
            params={"user_id": user_id, "days": days},
        )

    def admin_platform_spend_today(self):
        """Platform-wide spend for today UTC."""
        return self._request("GET", "/agent/admin/platform-spend-today")

    # ---- Community ----

    def share_strategy(self, strategy_id: str, body: dict = None):
        """Share a strategy to the community. Body: message,
        subscription_token_cost, published_mapping_id,
        set_published_mapping.

        `published_mapping_id` names the venue whose forward record is
        published — the track record the community judges the strategy
        on. `set_published_mapping` distinguishes "leave it alone" from
        "clear it" on a re-share.
        """
        return self._request(
            "POST", f"/community/share/{strategy_id}", json=body or {}
        )
