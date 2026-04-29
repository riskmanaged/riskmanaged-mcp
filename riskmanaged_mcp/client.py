"""HTTP client for the RiskManaged External API"""

import httpx
from riskmanaged_mcp.config import get_base_url, get_token


class RiskManagedClient:
    """Thin HTTP client wrapping the /api/external endpoints."""

    def __init__(self, token: str = None, base_url: str = None):
        self.token = token or get_token()
        self.base_url = (base_url or get_base_url()).rstrip("/")
        if not self.token:
            raise ValueError(
                "No API token configured. Run: riskmanaged configure --token YOUR_TOKEN"
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
