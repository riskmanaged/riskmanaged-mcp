"""MCP Server for RiskManaged — stdio transport for LLM clients."""

import json
import os
from pathlib import Path

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
                    "enum": ["binance", "bittensor"],
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
        description="Delete a strategy",
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
        description="Get grid search results including all variation metrics",
        inputSchema={
            "type": "object",
            "properties": {"grid_id": {"type": "string"}},
            "required": ["grid_id"],
        },
    ),
]


@server.list_tools()
async def list_tools():
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    client = _get_client()
    try:
        result = _dispatch(client, name, arguments)
        return [
            TextContent(type="text", text=json.dumps(result, indent=2, default=str))
        ]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {e}")]


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
