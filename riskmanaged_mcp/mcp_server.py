"""MCP Server for RiskManaged — stdio transport for LLM clients."""

import json
import os
from pathlib import Path

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, TextContent, Tool
from riskmanaged_mcp.client import RiskManagedClient

CONTEXT_FILE = Path(__file__).parent / "context.md"

server = Server("riskmanaged-mcp")


def _get_client() -> RiskManagedClient:
    token = os.environ.get("RISKMANAGED_TOKEN")
    base_url = os.environ.get("RISKMANAGED_URL")
    return RiskManagedClient(token=token, base_url=base_url)


# ---------------------------------------------------------------------------
# Resources — static context for the LLM
# ---------------------------------------------------------------------------


@server.list_resources()
async def list_resources():
    return [
        Resource(
            uri="riskmanaged://context",
            name="RiskManaged Platform Guide",
            description="Core concepts, workflows, and instructions for using the RiskManaged platform",
            mimeType="text/markdown",
        )
    ]


@server.read_resource()
async def read_resource(uri: str):
    if uri == "riskmanaged://context":
        if CONTEXT_FILE.exists():
            return CONTEXT_FILE.read_text()
        return "Context file not found."
    raise ValueError(f"Unknown resource: {uri}")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

TOOLS = [
    # Account
    Tool(
        name="get_me",
        description="Get current user info and token balance",
        inputSchema={"type": "object", "properties": {}},
    ),
    # Reference
    Tool(
        name="list_indicator_types",
        description="List all available indicator types grouped by category",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="get_indicator_schema",
        description="Get parameter schema and output lines for an indicator type",
        inputSchema={
            "type": "object",
            "properties": {
                "indicator_name": {
                    "type": "string",
                    "description": "Indicator type name (e.g. RSI, MACD, BollingerBands)",
                }
            },
            "required": ["indicator_name"],
        },
    ),
    Tool(
        name="list_patterns",
        description="List all available candlestick patterns",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="search_tickers",
        description="Search available trading tickers",
        inputSchema={
            "type": "object",
            "properties": {
                "search": {"type": "string", "default": ""},
                "exchange": {
                    "type": "string",
                    "default": "binance",
                    "enum": ["binance"],
                },
            },
        },
    ),
    Tool(
        name="get_constants",
        description="Get platform constants: timeframes, exchanges, trigger types, directions",
        inputSchema={"type": "object", "properties": {}},
    ),
    # Strategies
    Tool(
        name="list_strategies",
        description="List user's strategies",
        inputSchema={
            "type": "object",
            "properties": {
                "search": {"type": "string"},
                "timeframe": {"type": "string"},
                "mode": {"type": "string"},
                "limit": {"type": "integer", "default": 50},
            },
        },
    ),
    Tool(
        name="get_strategy",
        description="Get full strategy details including indicators, signals, bias, risk management",
        inputSchema={
            "type": "object",
            "properties": {"strategy_id": {"type": "string"}},
            "required": ["strategy_id"],
        },
    ),
    Tool(
        name="create_strategy",
        description="Create a new trading strategy",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "root_exchange": {"type": "string", "default": "binance"},
                "root_timeframe": {"type": "string", "default": "30m"},
                "root_ticker": {"type": "string", "default": "BTCUSDT"},
                "mode": {"type": "string", "default": "backtest"},
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="delete_strategy",
        description=(
            "Permanently delete a strategy and its backtest results. This "
            "cannot be undone — prefer archive_strategy to hide a strategy "
            "while keeping its history."
        ),
        inputSchema={
            "type": "object",
            "properties": {"strategy_id": {"type": "string"}},
            "required": ["strategy_id"],
        },
    ),
    # Indicators
    Tool(
        name="add_indicator",
        description="Add a technical indicator to a strategy. Get the schema first with get_indicator_schema.",
        inputSchema={
            "type": "object",
            "properties": {
                "strategy_id": {"type": "string"},
                "indicator_name": {"type": "string"},
                "config": {"type": "object", "default": {}},
            },
            "required": ["strategy_id", "indicator_name"],
        },
    ),
    Tool(
        name="delete_indicator",
        description="Remove an indicator from a strategy",
        inputSchema={
            "type": "object",
            "properties": {
                "strategy_id": {"type": "string"},
                "indicator_name": {"type": "string"},
            },
            "required": ["strategy_id", "indicator_name"],
        },
    ),
    # Signals
    Tool(
        name="add_signal_group",
        description="Add a signal group (set of entry/exit rules) to a strategy",
        inputSchema={
            "type": "object",
            "properties": {
                "strategy_id": {"type": "string"},
                "name": {"type": "string"},
            },
            "required": ["strategy_id", "name"],
        },
    ),
    Tool(
        name="add_signal_rule",
        description="Add a rule to a signal group. Conditions compare indicator lines using operators (crossover, crossunder, gt, lt, ge, le, eq).",
        inputSchema={
            "type": "object",
            "properties": {
                "strategy_id": {"type": "string"},
                "signal_name": {"type": "string"},
                "trigger_action": {
                    "type": "string",
                    "enum": ["enter_position", "exit_position"],
                },
                "trigger_direction": {"type": "string", "enum": ["long", "short"]},
                "conditions": {"type": "array", "items": {"type": "object"}},
            },
            "required": [
                "strategy_id",
                "signal_name",
                "trigger_action",
                "trigger_direction",
                "conditions",
            ],
        },
    ),
    Tool(
        name="delete_signal_rule",
        description="Remove a rule from a signal group",
        inputSchema={
            "type": "object",
            "properties": {
                "strategy_id": {"type": "string"},
                "signal_name": {"type": "string"},
                "rule_index": {"type": "integer"},
            },
            "required": ["strategy_id", "signal_name", "rule_index"],
        },
    ),
    # Bias
    Tool(
        name="add_bias_generator",
        description="Add a bias generator to a strategy",
        inputSchema={
            "type": "object",
            "properties": {
                "strategy_id": {"type": "string"},
                "name": {"type": "string"},
            },
            "required": ["strategy_id", "name"],
        },
    ),
    Tool(
        name="add_bias_rule",
        description="Add a rule to a bias generator",
        inputSchema={
            "type": "object",
            "properties": {
                "strategy_id": {"type": "string"},
                "bias_name": {"type": "string"},
                "bias_direction": {
                    "type": "string",
                    "enum": ["long", "short", "neutral"],
                },
                "conditions": {"type": "array", "items": {"type": "object"}},
            },
            "required": ["strategy_id", "bias_name", "bias_direction", "conditions"],
        },
    ),
    # Risk Management
    Tool(
        name="set_stop_loss",
        description="Set stop-loss on a strategy. Types: StopLossSimple, StopLossTrailing, StopLossAtr",
        inputSchema={
            "type": "object",
            "properties": {
                "strategy_id": {"type": "string"},
                "sl_type": {"type": "string"},
                "config": {"type": "object"},
            },
            "required": ["strategy_id", "sl_type", "config"],
        },
    ),
    Tool(
        name="set_take_profit",
        description="Set take-profit on a strategy. Type: TakeProfitSpread",
        inputSchema={
            "type": "object",
            "properties": {
                "strategy_id": {"type": "string"},
                "tp_type": {"type": "string"},
                "config": {"type": "object"},
            },
            "required": ["strategy_id", "tp_type", "config"],
        },
    ),
    # Backtest
    Tool(
        name="run_backtest",
        description="Run a historical backtest on a strategy. May take 30-60 seconds.",
        inputSchema={
            "type": "object",
            "properties": {"strategy_id": {"type": "string"}},
            "required": ["strategy_id"],
        },
    ),
    Tool(
        name="get_reports",
        description="Get backtest report metrics (Sharpe, return, drawdown, etc.)",
        inputSchema={
            "type": "object",
            "properties": {"strategy_id": {"type": "string"}},
            "required": ["strategy_id"],
        },
    ),
    Tool(
        name="run_monte_carlo",
        description="Run Monte Carlo simulation on backtest results",
        inputSchema={
            "type": "object",
            "properties": {
                "strategy_id": {"type": "string"},
                "sims": {"type": "integer", "default": 1000},
            },
            "required": ["strategy_id"],
        },
    ),
    # Versioning
    Tool(
        name="commit_version",
        description="Commit the current strategy state as a version",
        inputSchema={
            "type": "object",
            "properties": {
                "strategy_id": {"type": "string"},
                "change_log": {"type": "string"},
            },
            "required": ["strategy_id"],
        },
    ),
    Tool(
        name="get_versions",
        description="List all committed versions of a strategy",
        inputSchema={
            "type": "object",
            "properties": {"strategy_id": {"type": "string"}},
            "required": ["strategy_id"],
        },
    ),
    # Grids
    Tool(
        name="create_grid_template",
        description="Create a grid template from a strategy for parameter optimization",
        inputSchema={
            "type": "object",
            "properties": {"strategy_id": {"type": "string"}},
            "required": ["strategy_id"],
        },
    ),
    Tool(
        name="check_variations",
        description="Check how many variations a grid template will produce",
        inputSchema={
            "type": "object",
            "properties": {"template_id": {"type": "string"}},
            "required": ["template_id"],
        },
    ),
    Tool(
        name="create_grid",
        description="Create a grid search from a template (costs tokens, backtests all variations)",
        inputSchema={
            "type": "object",
            "properties": {"template_id": {"type": "string"}},
            "required": ["template_id"],
        },
    ),
    Tool(
        name="get_grid",
        description=(
            "Get grid search results: the robustness verdict (robust_plateau / "
            "weak_plateau / isolated_peaks / no_survivors), the ranked parameter "
            "plateaus (each with its width, member settings and a recommended pick) "
            "under cluster_analysis, plus every variation's metrics"
        ),
        inputSchema={
            "type": "object",
            "properties": {"grid_id": {"type": "string"}},
            "required": ["grid_id"],
        },
    ),
    Tool(
        name="analyze_grid",
        description=(
            "(Re)compute the robustness/cluster analysis for a completed grid. "
            "Needed to backfill grids finished before analysis existed; new grids "
            "are analysed automatically"
        ),
        inputSchema={
            "type": "object",
            "properties": {"grid_id": {"type": "string"}},
            "required": ["grid_id"],
        },
    ),
    Tool(
        name="get_grid_suggestions",
        description=(
            "Get proposed next searches for a grid: zoom_in (finer step inside a "
            "found plateau) and explore_higher/explore_lower (a fresh parameter set "
            "that excludes the already-tested ranges). Each includes a ready-to-run "
            "template_data and an estimated variation count"
        ),
        inputSchema={
            "type": "object",
            "properties": {"grid_id": {"type": "string"}},
            "required": ["grid_id"],
        },
    ),
    Tool(
        name="refine_grid",
        description=(
            "Turn a chosen next-search into a new grid template and return its "
            "template_id (then call create_grid to launch it). Use kind=zoom_in to "
            "refine a plateau, or kind=explore_higher/explore_lower to iterate on a "
            "separate parameter set. Pass the suggestion's template_data to run it "
            "exactly, or a custom template_data for a fully bespoke sweep"
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "grid_id": {"type": "string"},
                "kind": {
                    "type": "string",
                    "description": "zoom_in | explore_higher | explore_lower",
                },
                "template_data": {
                    "type": "object",
                    "description": "Optional exact search to persist (from a suggestion, or custom)",
                },
            },
            "required": ["grid_id", "kind"],
        },
    ),
    # ================================================================
    # Docs-gap tools — these are documented on the landing page
    # (#/docs/mcp-overview) but were never wired into the MCP server.
    # The client methods already exist (they wrap existing /api/external
    # endpoints); we just add the Tool() defs + dispatch entries.
    # ================================================================
    Tool(
        name="update_strategy",
        description="Update an existing strategy (name, ticker, timeframe, mode)",
        inputSchema={
            "type": "object",
            "properties": {
                "strategy_id": {"type": "string"},
                "name": {"type": "string"},
                "root_exchange": {"type": "string"},
                "root_timeframe": {"type": "string"},
                "root_ticker": {"type": "string"},
                "mode": {"type": "string"},
            },
            "required": ["strategy_id"],
        },
    ),
    Tool(
        name="remove_indicator",
        description="Remove an indicator from a strategy (alias of delete_indicator)",
        inputSchema={
            "type": "object",
            "properties": {
                "strategy_id": {"type": "string"},
                "indicator_name": {"type": "string"},
            },
            "required": ["strategy_id", "indicator_name"],
        },
    ),
    Tool(
        name="update_grid_template",
        description="Modify the parameter ranges of a grid search template",
        inputSchema={
            "type": "object",
            "properties": {
                "template_id": {"type": "string"},
                "parameter_ranges": {"type": "object"},
            },
            "required": ["template_id"],
        },
    ),
    Tool(
        name="get_backtest_results",
        description="Get the latest backtest results for a strategy (alias of get_reports)",
        inputSchema={
            "type": "object",
            "properties": {"strategy_id": {"type": "string"}},
            "required": ["strategy_id"],
        },
    ),
    Tool(
        name="list_versions",
        description="List version history for a strategy (alias of get_versions)",
        inputSchema={
            "type": "object",
            "properties": {"strategy_id": {"type": "string"}},
            "required": ["strategy_id"],
        },
    ),
    Tool(
        name="restore_version",
        description="Restore a strategy to a previous version",
        inputSchema={
            "type": "object",
            "properties": {
                "strategy_id": {"type": "string"},
                "version_id": {"type": "integer"},
            },
            "required": ["strategy_id", "version_id"],
        },
    ),
    # ---- Community share (W6.4-B) ----
    Tool(
        name="share_strategy",
        description="Share a strategy to the community. Default subscription cost is 10 tokens; can be overridden.",
        inputSchema={
            "type": "object",
            "properties": {
                "strategy_id": {"type": "string"},
                "message": {"type": "string"},
                "subscription_token_cost": {"type": "number", "default": 10.0},
            },
            "required": ["strategy_id"],
        },
    ),
    # ================================================================
    # W6 surface — agent committees, templates, model routes, LLM
    # connections, news, macro, user settings, proposals. Each tool
    # is a thin wrapper over a /api/internal/agent/* endpoint. One
    # tool per logical operation; parameters mirror the REST API.
    # ================================================================
    # ---- Hedge-fund templates (W6.1) ----
    Tool(
        name="list_templates",
        description="List the 3 day-1 hedge-fund templates (momentum_4h_crypto, mean_reversion_defi, event_driven_news)",
        inputSchema={
            "type": "object",
            "properties": {
                "enabled_only": {"type": "boolean", "default": True},
            },
        },
    ),
    Tool(
        name="get_template",
        description="Get one template by slug, including the full cast (12 agents) and default contexts/thresholds",
        inputSchema={
            "type": "object",
            "properties": {"slug": {"type": "string"}},
            "required": ["slug"],
        },
    ),
    # ---- Agent committees (W6.1) ----
    Tool(
        name="list_committees",
        description="List your Squads (returns instance_id, name, autonomy_tier, strategy binding)",
        inputSchema={
            "type": "object",
            "properties": {"enabled_only": {"type": "boolean", "default": True}},
        },
    ),
    Tool(
        name="get_committee",
        description="Get one squad (AgentInstance) by id, with its members + thresholds",
        inputSchema={
            "type": "object",
            "properties": {"instance_id": {"type": "string"}},
            "required": ["instance_id"],
        },
    ),
    Tool(
        name="clone_template",
        description="Clone a day-1 template into a working squad bound to a strategy. Returns the new instance_id.",
        inputSchema={
            "type": "object",
            "properties": {
                "template_slug": {"type": "string"},
                "name": {"type": "string"},
                "binding_type": {"type": "string", "default": "strategy"},
                "strategy_id": {"type": "string"},
                "basket_id": {"type": "string"},
                "autonomy_tier": {"type": "string", "default": "suggest"},
            },
            "required": ["template_slug", "name"],
        },
    ),
    Tool(
        name="get_committee_messages",
        description="Replay the deliberation message bus for a squad (since_id=0 returns the full transcript)",
        inputSchema={
            "type": "object",
            "properties": {
                "instance_id": {"type": "string"},
                "since_id": {"type": "integer", "default": 0},
                "limit": {"type": "integer", "default": 200},
            },
            "required": ["instance_id"],
        },
    ),
    # ---- Committee cadence, markets, readings and decisions ----
    Tool(
        name="get_committee_decision_board",
        description=(
            "One row per market a squad covers: its current call, "
            "cumulative points, accuracy, streak and when it next wakes. The "
            "fastest way to see what a squad is saying right now."
        ),
        inputSchema={
            "type": "object",
            "properties": {"instance_id": {"type": "string"}},
            "required": ["instance_id"],
        },
    ),
    Tool(
        name="list_committee_decisions",
        description=(
            "A squad's recent decisions, newest first. Each carries the "
            "price it was stamped with and, once the next decision supplied a "
            "closing price, the points it scored. The newest decision is "
            "always unscored."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "instance_id": {"type": "string"},
                "symbol": {"type": "string", "description": "Filter to one market"},
                "limit": {"type": "integer", "default": 50},
            },
            "required": ["instance_id"],
        },
    ),
    Tool(
        name="get_committee_decision_summary",
        description=(
            "A squad's standing: cumulative points, recent form, accuracy, "
            "streak and current call. Positive points mean its calls have been "
            "paying off."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "instance_id": {"type": "string"},
                "symbol": {"type": "string", "description": "Scope to one market"},
            },
            "required": ["instance_id"],
        },
    ),
    Tool(
        name="set_committee_cadence",
        description=(
            "Configure how a squad wakes. cadence_interval_seconds has a "
            "30-minute floor and rounds to a timeframe (30m/1h/2h/4h/6h/12h/1d); "
            "context_bars is how many trailing values of each reading the "
            "specialists see."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "instance_id": {"type": "string"},
                "cadence_enabled": {"type": "boolean"},
                "cadence_interval_seconds": {"type": "integer"},
                "score_deadband_pct": {"type": "number"},
                "context_bars": {"type": "integer"},
            },
            "required": ["instance_id"],
        },
    ),
    Tool(
        name="list_committee_markets",
        description="The markets a squad covers, one decision each per wake",
        inputSchema={
            "type": "object",
            "properties": {"instance_id": {"type": "string"}},
            "required": ["instance_id"],
        },
    ),
    Tool(
        name="add_committee_market",
        description=(
            "Cover a market (e.g. BTCUSDT). Idempotent — re-adding re-enables "
            "a paused market rather than duplicating it."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "instance_id": {"type": "string"},
                "symbol": {"type": "string"},
            },
            "required": ["instance_id", "symbol"],
        },
    ),
    Tool(
        name="remove_committee_market",
        description="Stop covering a market. Its past decisions are kept.",
        inputSchema={
            "type": "object",
            "properties": {
                "instance_id": {"type": "string"},
                "symbol": {"type": "string"},
            },
            "required": ["instance_id", "symbol"],
        },
    ),
    Tool(
        name="get_committee_readings",
        description=(
            "The indicator readings fed to a squad's specialists, in the "
            "same {name: {type, config}} shape a strategy stores its "
            "indicators in"
        ),
        inputSchema={
            "type": "object",
            "properties": {"instance_id": {"type": "string"}},
            "required": ["instance_id"],
        },
    ),
    Tool(
        name="set_committee_readings",
        description=(
            "Replace a squad's whole reading map. Omit `ticker` from each "
            "config — a reading is computed separately for every market the "
            "squad covers."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "instance_id": {"type": "string"},
                "indicators": {
                    "type": "object",
                    "description": '{"rsi_1h": {"type": "RSI", "config": {"timeframe": "1h", "length": 14}}}',
                },
            },
            "required": ["instance_id", "indicators"],
        },
    ),
    # ---- Model routes (W3.5) ----
    Tool(
        name="list_model_routes",
        description="List the user's per-task-class LLM model routes",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="upsert_model_route",
        description="Create or update a (user, task_class) route. Body fields mirror the REST API.",
        inputSchema={
            "type": "object",
            "properties": {
                "task_class": {"type": "string"},
                "provider": {"type": "string"},
                "model": {"type": "string"},
                "use_gateway": {"type": "boolean", "default": False},
                "gateway_endpoint": {"type": "string"},
                "connection_id": {"type": "string"},
                "max_tokens_per_call": {"type": "integer"},
                "temperature": {"type": "number"},
                "fallback_chain": {"type": "array", "items": {"type": "object"}},
            },
            "required": ["task_class", "provider", "model"],
        },
    ),
    Tool(
        name="delete_model_route",
        description="Delete a (user, task_class) route",
        inputSchema={
            "type": "object",
            "properties": {
                "task_class": {"type": "string"},
            },
            "required": ["task_class"],
        },
    ),
    # ---- LLM connections (W3.7) ----
    Tool(
        name="list_llm_connections",
        description="List the user's LLM credentials (platform + direct + remote). Returns three buckets.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="create_llm_connection",
        description="Create a direct (user-provided API key) LLM connection. The key is Fernet-encrypted server-side.",
        inputSchema={
            "type": "object",
            "properties": {
                "provider": {"type": "string"},
                "label": {"type": "string"},
                "api_key": {"type": "string"},
                "endpoint": {"type": "string"},
            },
            "required": ["provider", "label", "api_key"],
        },
    ),
    Tool(
        name="test_llm_connection",
        description="Ping a connection to verify the credentials work",
        inputSchema={
            "type": "object",
            "properties": {"connection_id": {"type": "string"}},
            "required": ["connection_id"],
        },
    ),
    Tool(
        name="reveal_llm_connection_key",
        description="Reveal the decrypted API key for a direct connection (use sparingly — secrets are shown in plaintext)",
        inputSchema={
            "type": "object",
            "properties": {"connection_id": {"type": "string"}},
            "required": ["connection_id"],
        },
    ),
    Tool(
        name="update_llm_connection",
        description="Update a connection (label, endpoint, etc.)",
        inputSchema={
            "type": "object",
            "properties": {
                "connection_id": {"type": "string"},
                "label": {"type": "string"},
                "endpoint": {"type": "string"},
                "is_active": {"type": "boolean"},
            },
            "required": ["connection_id"],
        },
    ),
    Tool(
        name="delete_llm_connection",
        description="Delete a direct or remote LLM connection",
        inputSchema={
            "type": "object",
            "properties": {"connection_id": {"type": "string"}},
            "required": ["connection_id"],
        },
    ),
    # ---- News (W3.1) ----
    Tool(
        name="list_news_articles",
        description="List recent news articles (filter by ticker, source, date range). Citations for agent grounding.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "source_id": {"type": "string"},
                "since": {"type": "string"},
                "limit": {"type": "integer", "default": 50},
            },
        },
    ),
    Tool(
        name="get_news_article",
        description="Get one news article by id, with full body + cited_by counts",
        inputSchema={
            "type": "object",
            "properties": {"article_id": {"type": "string"}},
            "required": ["article_id"],
        },
    ),
    Tool(
        name="list_news_sources",
        description="List the user's news sources (RSS feeds, CryptoPanic, Fear&Greed, etc.)",
        inputSchema={"type": "object", "properties": {}},
    ),
    # ---- Macro (W3.2) ----
    Tool(
        name="list_macro_events",
        description="List macro events (FOMC, CPI, etc.) with optional date range filter",
        inputSchema={
            "type": "object",
            "properties": {
                "since": {"type": "string"},
                "until": {"type": "string"},
                "importance": {"type": "string", "enum": ["low", "medium", "high"]},
                "limit": {"type": "integer", "default": 50},
            },
        },
    ),
    Tool(
        name="get_macro_event",
        description="Get one macro event by id, with full description + source URL",
        inputSchema={
            "type": "object",
            "properties": {"event_id": {"type": "string"}},
            "required": ["event_id"],
        },
    ),
    # ---- User settings (W6.3) ----
    Tool(
        name="get_user_settings",
        description="Get the user's daily token cap + today's spend so far. Lazy-creates the row on first call.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="set_daily_token_cap",
        description="Set (or clear) the user's daily token cap. Pass null to disable enforcement.",
        inputSchema={
            "type": "object",
            "properties": {
                "cap": {"type": ["integer", "null"], "minimum": 0},
            },
            "required": ["cap"],
        },
    ),
    # ---- Promotion ----
    # ---- W6.5 — Observability (per-instance + admin) ----
    Tool(
        name="list_instance_runs",
        description=(
            "List the last N runs for an agent instance, with token "
            "counts and estimated cost. Open to the instance owner "
            "(no admin role required). Powers the 5th 'Runs' view-tab "
            "on the squad detail page."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "instance_id": {"type": "string"},
                "limit": {"type": "integer", "default": 50, "minimum": 1, "maximum": 200},
            },
            "required": ["instance_id"],
        },
    ),
    Tool(
        name="admin_per_user_spend",
        description=(
            "ADMIN-ONLY: per-user LLM spend for today UTC. Returns "
            "tokens_in, tokens_out, total_tokens, daily_token_cap, "
            "cap_pct, cap_pct_color (green/yellow/red), and the "
            "number of active squads the user has. The backend "
            "enforces the admin role; the MCP server forwards."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
            },
            "required": ["user_id"],
        },
    ),
    Tool(
        name="admin_per_user_spend_history",
        description=(
            "ADMIN-ONLY: per-user daily LLM spend for the last N "
            "days (UTC). Returns a daily series suitable for "
            "plotting — oldest first, includes zero-spend days. "
            "The series has one row per UTC day."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "days": {"type": "integer", "default": 30, "minimum": 1, "maximum": 365},
            },
            "required": ["user_id"],
        },
    ),
    # ---- W6.5 — Rollback (tier flip via the audit log) ----
]


@server.list_tools()
async def list_tools():
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """Run one tool and return its payload as JSON text.

    Failures are raised, not returned. The MCP SDK catches an exception here and
    builds a result with `isError: True`; returning a string that merely begins
    with "Error:" produces `isError: False`, so the model sees a *successful*
    call whose result happens to be prose. That is how an expired token ends up
    being reasoned about as though it were data.
    """
    client = _get_client()
    try:
        result = _dispatch(client, name, arguments)
    except httpx.HTTPStatusError as exc:
        # `str(HTTPStatusError)` reports the status and URL but drops the body,
        # which is where the API puts the actionable detail.
        raise RuntimeError(
            f"{name} failed: HTTP {exc.response.status_code} — "
            f"{_error_detail(exc.response)}"
        ) from exc

    return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]


def _error_detail(response: "httpx.Response") -> str:
    """The most useful message the API gave us, however it was shaped."""
    try:
        body = response.json()
    except ValueError:
        return response.text.strip()[:500] or "(empty response body)"
    if isinstance(body, dict):
        detail = body.get("detail", body)
        return detail if isinstance(detail, str) else json.dumps(detail)
    return json.dumps(body)


def _dispatch(client: RiskManagedClient, name: str, args: dict):
    """Route tool calls to the HTTP client."""
    # Account
    if name == "get_me":
        return client.get_me()
    # Reference
    if name == "list_indicator_types":
        return client.list_indicator_types()
    if name == "get_indicator_schema":
        return client.get_indicator_schema(args["indicator_name"])
    if name == "list_patterns":
        return client.list_patterns()
    if name == "search_tickers":
        return client.search_tickers(
            search=args.get("search", ""), exchange=args.get("exchange", "binance")
        )
    if name == "get_constants":
        return client.get_constants()
    # Strategies
    if name == "list_strategies":
        return client.list_strategies(
            **{k: v for k, v in args.items() if v is not None}
        )
    if name == "get_strategy":
        return client.get_strategy(args["strategy_id"])
    if name == "create_strategy":
        return client.create_strategy(args)
    if name == "delete_strategy":
        return client.delete_strategy(args["strategy_id"])
    # Indicators
    if name == "add_indicator":
        return client.add_indicator(
            args["strategy_id"], args["indicator_name"], args.get("config", {})
        )
    if name == "delete_indicator":
        return client.delete_indicator(args["strategy_id"], args["indicator_name"])
    # Signals
    if name == "add_signal_group":
        return client.add_signal_group(args["strategy_id"], {"name": args["name"]})
    if name == "add_signal_rule":
        return client.add_signal_rule(
            args["strategy_id"],
            args["signal_name"],
            args["trigger_action"],
            args["trigger_direction"],
            args["conditions"],
        )
    if name == "delete_signal_rule":
        return client.delete_signal_rule(
            args["strategy_id"], args["signal_name"], args["rule_index"]
        )
    # Bias
    if name == "add_bias_generator":
        return client.add_bias_generator(args["strategy_id"], {"name": args["name"]})
    if name == "add_bias_rule":
        return client.add_bias_rule(
            args["strategy_id"],
            args["bias_name"],
            args["bias_direction"],
            args["conditions"],
        )
    # Risk
    if name == "set_stop_loss":
        return client.set_stop_loss(
            args["strategy_id"], args["sl_type"], args["config"]
        )
    if name == "set_take_profit":
        return client.set_take_profit(
            args["strategy_id"], args["tp_type"], args["config"]
        )
    # Backtest
    if name == "run_backtest":
        return client.run_backtest(args["strategy_id"])
    if name == "get_reports":
        return client.get_reports(args["strategy_id"])
    if name == "run_monte_carlo":
        return client.run_monte_carlo(args["strategy_id"], sims=args.get("sims", 1000))
    # Versioning
    if name == "commit_version":
        return client.commit_version(
            args["strategy_id"], change_log=args.get("change_log")
        )
    if name == "get_versions":
        return client.get_versions(args["strategy_id"])
    # Grids
    if name == "create_grid_template":
        return client.create_grid_template(args["strategy_id"])
    if name == "check_variations":
        return client.check_variations(args["template_id"])
    if name == "create_grid":
        return client.create_grid(args["template_id"])
    if name == "get_grid":
        return client.get_grid(args["grid_id"])
    if name == "analyze_grid":
        return client.analyze_grid(args["grid_id"])
    if name == "get_grid_suggestions":
        return client.grid_suggestions(args["grid_id"])
    if name == "refine_grid":
        return client.refine_grid(
            args["grid_id"], args["kind"], args.get("template_data")
        )
    # ---- Docs-gap tool dispatch (W6.4-B) ----
    if name == "update_strategy":
        return client.update_strategy(
            args["strategy_id"],
            {k: v for k, v in args.items() if k != "strategy_id" and v is not None},
        )
    if name == "remove_indicator":
        return client.delete_indicator(
            args["strategy_id"], args["indicator_name"]
        )
    if name == "update_grid_template":
        return client.update_grid_template(
            args["template_id"],
            {k: v for k, v in args.items() if k != "template_id"},
        )
    if name == "get_backtest_results":
        return client.get_reports(args["strategy_id"])
    if name == "list_versions":
        return client.get_versions(args["strategy_id"])
    if name == "restore_version":
        return client.restore_version(
            args["strategy_id"], args["version_id"]
        )
    if name == "share_strategy":
        body = {k: v for k, v in args.items() if k != "strategy_id"}
        return client.share_strategy(args["strategy_id"], body)
    # ---- W6 surface dispatch ----
    # Templates
    if name == "list_templates":
        return client.list_templates(
            enabled_only=args.get("enabled_only", True)
        )
    if name == "get_template":
        return client.get_template(args["slug"])
    # Committees
    if name == "list_committees":
        return client.list_committees(
            enabled_only=args.get("enabled_only", True)
        )
    if name == "get_committee":
        return client.get_committee(args["instance_id"])
    if name == "clone_template":
        return client.clone_template(args)
    if name == "get_committee_messages":
        return client.get_committee_messages(
            args["instance_id"],
            since_id=args.get("since_id", 0),
            limit=args.get("limit", 200),
        )
    # Model routes
    # Committee cadence, markets, readings and decisions
    if name == "get_committee_decision_board":
        return client.get_committee_cadence_board(args["instance_id"])
    if name == "list_committee_decisions":
        return client.list_committee_decisions(
            args["instance_id"],
            symbol=args.get("symbol", ""),
            limit=args.get("limit", 50),
        )
    if name == "get_committee_decision_summary":
        return client.get_committee_decision_summary(
            args["instance_id"], symbol=args.get("symbol", "")
        )
    if name == "set_committee_cadence":
        body = {k: v for k, v in args.items() if k != "instance_id"}
        return client.set_committee_cadence(args["instance_id"], body)
    if name == "list_committee_markets":
        return client.list_committee_markets(args["instance_id"])
    if name == "add_committee_market":
        return client.add_committee_market(args["instance_id"], args["symbol"])
    if name == "remove_committee_market":
        return client.remove_committee_market(args["instance_id"], args["symbol"])
    if name == "get_committee_readings":
        return client.get_committee_readings(args["instance_id"])
    if name == "set_committee_readings":
        return client.set_committee_readings(args["instance_id"], args["indicators"])
    if name == "list_model_routes":
        return client.list_model_routes()
    if name == "upsert_model_route":
        return client.upsert_model_route(args)
    if name == "delete_model_route":
        return client.delete_model_route(args["task_class"])
    # LLM connections
    if name == "list_llm_connections":
        return client.list_llm_connections()
    if name == "create_llm_connection":
        return client.create_llm_connection(args)
    if name == "test_llm_connection":
        return client.test_llm_connection(args["connection_id"])
    if name == "reveal_llm_connection_key":
        return client.reveal_llm_connection_key(args["connection_id"])
    if name == "update_llm_connection":
        body = {k: v for k, v in args.items() if k != "connection_id"}
        return client.update_llm_connection(args["connection_id"], body)
    if name == "delete_llm_connection":
        return client.delete_llm_connection(args["connection_id"])
    # News
    if name == "list_news_articles":
        return client.list_news_articles(
            **{k: v for k, v in args.items() if v is not None}
        )
    if name == "get_news_article":
        return client.get_news_article(args["article_id"])
    if name == "list_news_sources":
        return client.list_news_sources()
    # Macro
    if name == "list_macro_events":
        return client.list_macro_events(
            **{k: v for k, v in args.items() if v is not None}
        )
    if name == "get_macro_event":
        return client.get_macro_event(args["event_id"])
    # User settings
    if name == "get_user_settings":
        return client.get_user_settings()
    if name == "set_daily_token_cap":
        return client.set_daily_token_cap(args.get("cap"))
    # W6.5 — Observability
    if name == "list_instance_runs":
        return client.list_instance_runs(
            args["instance_id"], limit=args.get("limit", 50)
        )
    if name == "admin_per_user_spend":
        return client.admin_per_user_spend(args["user_id"])
    if name == "admin_per_user_spend_history":
        return client.admin_per_user_spend_history(
            args["user_id"], days=args.get("days", 30)
        )
    # W6.5 — Rollback

    raise ValueError(f"Unknown tool: {name}")


async def _run():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


def main():
    import asyncio

    asyncio.run(_run())


if __name__ == "__main__":
    main()
