# riskmanaged-mcp

CLI and MCP server for the [RiskManaged](https://riskmanaged.io) algorithmic
trading platform.

Build, configure, backtest and optimise trading strategies from your shell or
through any MCP-enabled LLM — and run LLM agent committees over them.

> Using this from an AI assistant? Read **[AGENTS.md](AGENTS.md)** instead — it
> is written for an agent and covers the parts that are easy to get wrong.

## Installation

```bash
curl -sSL https://raw.githubusercontent.com/riskmanaged/riskmanaged-mcp/main/install.sh | bash
```

The script auto-detects the best available Python package manager: **uv**,
**pipx**, **pip/pip3**, `python3 -m pip`, falling back to `ensurepip`. Works on
macOS, Linux and WSL.

<details>
<summary>Manual install</summary>

```bash
uv tool install riskmanaged-mcp@git+https://github.com/riskmanaged/riskmanaged-mcp.git
pipx install git+https://github.com/riskmanaged/riskmanaged-mcp.git
pip install --user git+https://github.com/riskmanaged/riskmanaged-mcp.git
```

</details>

> **Requires Python ≥ 3.11**

## Setup

```bash
riskmanaged auth login      # browser flow; saves ~/.riskmanaged/config.json (chmod 600)
riskmanaged auth whoami     # verify
```

If you already have a token from the profile page:

```bash
riskmanaged auth configure --token YOUR_TOKEN
```

The token is per-user and grants full access to that account. No command takes
a user id — identity is resolved from the token.

## CLI usage

```bash
# Strategies
riskmanaged strategies list
riskmanaged strategies create --name "My Strategy" --ticker BTCUSDT --timeframe 30m
riskmanaged strategies get <STRATEGY_ID>
riskmanaged strategies archive <STRATEGY_ID>
riskmanaged strategies clone <STRATEGY_ID>
riskmanaged strategies share <STRATEGY_ID> --message "shared"

# Indicators
riskmanaged indicators list-types
riskmanaged indicators schema RSI
riskmanaged indicators add <STRATEGY_ID> RSI --params '{"length": 14}'
riskmanaged indicators remove <STRATEGY_ID> RSI

# Signals
riskmanaged signals add-group <STRATEGY_ID> entry
riskmanaged signals add-rule <STRATEGY_ID> entry --action enter_position --direction long \
  --conditions '[{"trigger_line":"RSI.rsi","trigger":"crossover","threshold_value":30},{"trigger_line":"MACD.macd","trigger":"gt","threshold_line":"MACD.signal"}]'

# Bias
riskmanaged bias add <STRATEGY_ID> trend_filter
riskmanaged bias add-rule <STRATEGY_ID> trend_filter --direction long \
  --conditions '[{"trigger_line":"close","trigger":"gt","threshold_line":"EMA.ema"}]'

# Risk
riskmanaged risk set-sl <STRATEGY_ID> StopLossTrailing --params '{"trailing_pct": 0.02}'
riskmanaged risk set-tp <STRATEGY_ID> TakeProfitSpread --params '{"order_spread": [{"profit_target": 0.05}]}'
riskmanaged risk sl-types
riskmanaged risk tp-schema TakeProfitSpread

# Backtest
riskmanaged backtest run <STRATEGY_ID>
riskmanaged backtest reports <STRATEGY_ID>
riskmanaged backtest montecarlo <STRATEGY_ID> --sims 1000

# Grids
riskmanaged grids create-template <STRATEGY_ID>
riskmanaged grids variations <TEMPLATE_ID>
riskmanaged grids create <TEMPLATE_ID>
riskmanaged grids get <GRID_ID>

# Agent committees
riskmanaged agents templates list
riskmanaged agents committees list
riskmanaged agents proposals list
riskmanaged agents spend get

# Reference
riskmanaged reference tickers --search BTC
riskmanaged reference patterns
riskmanaged reference constants
```

Run `riskmanaged <group> --help` for the full parameter list of any group.

## Indicator lines

An indicator's name defaults to **its type name**, so lines are `RSI.rsi`,
`MACD.signal`, `BollingerBands.bband_top`. There is no ticker or timeframe in a
line name. Pass `{"name": "fast_rsi"}` to add the same indicator twice.

Call `riskmanaged indicators schema <TYPE>` before adding one: it returns the
fields you may set and the lines you may reference. Unknown fields are rejected
with a 400 that lists the valid ones.

## MCP server

```json
{
  "mcpServers": {
    "riskmanaged": {
      "command": "riskmanaged-mcp",
      "env": {
        "RISKMANAGED_TOKEN": "YOUR_TOKEN",
        "RISKMANAGED_URL": "https://agent.riskmanaged.io"
      }
    }
  }
}
```

> `RISKMANAGED_URL` must be `agent.riskmanaged.io` — `riskmanaged.io` is the
> marketing site and returns HTML.

Config file locations: Claude Desktop uses
`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or
`%APPDATA%\Claude\claude_desktop_config.json` (Windows); Cursor uses
`~/.cursor/mcp.json`. For Claude Code, run
`claude mcp add riskmanaged -- riskmanaged-mcp`.

## Tools

<!-- BEGIN GENERATED TOOLS -->
_72 tools. This table is generated — run `riskmanaged dev sync-docs` after changing them._

| Category | Tools |
|---|---|
| **Account** | `get_me` |
| **Reference** | `list_indicator_types`, `get_indicator_schema`, `list_patterns`, `search_tickers`, `get_constants` |
| **Strategies** | `list_strategies`, `get_strategy`, `create_strategy`, `update_strategy`, `delete_strategy` |
| **Indicators** | `add_indicator`, `delete_indicator`, `remove_indicator` |
| **Signals** | `add_signal_group`, `add_signal_rule`, `delete_signal_rule` |
| **Bias** | `add_bias_generator`, `add_bias_rule` |
| **Risk** | `set_stop_loss`, `set_take_profit` |
| **Backtest** | `run_backtest`, `get_reports`, `get_backtest_results`, `run_monte_carlo` |
| **Versioning** | `commit_version`, `get_versions`, `list_versions`, `restore_version` |
| **Grids** | `create_grid_template`, `update_grid_template`, `check_variations`, `create_grid`, `get_grid`, `analyze_grid`, `get_grid_suggestions`, `refine_grid` |
| **Community** | `share_strategy` |
| **Squad templates** | `list_templates`, `get_template` |
| **Squads** | `list_committees`, `get_committee`, `clone_template`, `get_committee_messages`, `list_instance_runs` |
| **Squad cadence + markets** | `set_committee_cadence`, `list_committee_markets`, `add_committee_market`, `remove_committee_market`, `get_committee_readings`, `set_committee_readings` |
| **Squad decisions** | `get_committee_decision_board`, `list_committee_decisions`, `get_committee_decision_summary` |
| **Model routes** | `list_model_routes`, `upsert_model_route`, `delete_model_route` |
| **LLM connections** | `list_llm_connections`, `create_llm_connection`, `test_llm_connection`, `reveal_llm_connection_key`, `update_llm_connection`, `delete_llm_connection` |
| **News** | `list_news_articles`, `get_news_article`, `list_news_sources` |
| **Macro** | `list_macro_events`, `get_macro_event` |
| **Spend caps** | `get_user_settings`, `set_daily_token_cap` |
| **Admin (requires the admins role)** | `admin_per_user_spend`, `admin_per_user_spend_history` |
<!-- END GENERATED TOOLS -->

## Development

```bash
pip install -e ".[test]"
pytest
```

The suite is fully offline: HTTP is mocked and the API contract is checked
against a vendored OpenAPI snapshot in `tests/snapshots/`, so no backend and no
credentials are needed. Refresh the snapshot with `riskmanaged dev sync-snapshot`
and regenerate the tool tables above with `riskmanaged dev sync-docs`.

## License

MIT
