# riskmanaged-mcp

CLI and MCP server for the [RiskManaged](https://riskmanaged.io) algorithmic trading strategy platform.

Build, configure, backtest, and optimize trading strategies from the command line or through an MCP-enabled LLM.

## Installation

### One-liner (recommended)

```bash
curl -sSL https://raw.githubusercontent.com/riskmanaged/riskmanaged-mcp/main/install.sh | bash
```

The install script auto-detects the best available Python package manager on your system and uses it. It checks for (in order): **uv**, **pipx**, **pip/pip3**, **python3 -m pip**, and will bootstrap pip via `ensurepip` as a last resort. Works on macOS, Linux, and WSL.

### Manual install

Pick whichever tool you already have:

```bash
# uv (fastest)
uv tool install riskmanaged-mcp@git+https://github.com/riskmanaged/riskmanaged-mcp.git

# pipx (isolated environment)
pipx install git+https://github.com/riskmanaged/riskmanaged-mcp.git

# pip
pip install --user git+https://github.com/riskmanaged/riskmanaged-mcp.git
```

> **Requires Python ≥ 3.11**

## Setup

1. **Generate an API token** at [riskmanaged.io/profile](https://riskmanaged.io/profile) → API Tokens section
2. **Configure the CLI:**

```bash
riskmanaged auth configure --token YOUR_TOKEN
riskmanaged auth whoami
```

## CLI Usage

```bash
# Strategy management
riskmanaged strategies list
riskmanaged strategies create --name "My Strategy" --ticker BTCUSDT --timeframe 30m
riskmanaged strategies get <STRATEGY_ID>

# Indicators
riskmanaged indicators list-types
riskmanaged indicators schema RSI
riskmanaged indicators add <STRATEGY_ID> RSI --params '{"length": 14}'

# Signals
riskmanaged signals add-group <STRATEGY_ID> my_signals
riskmanaged signals add-rule <STRATEGY_ID> my_signals --action enter_position --direction long --conditions '[{"left":"RSI_btcusdt_30m.rsi","op":"crossover","right":"30"}]'

# Risk management
riskmanaged risk set-sl <STRATEGY_ID> StopLossTrailing --params '{"trailing_pct": 0.02}'
riskmanaged risk set-tp <STRATEGY_ID> TakeProfitSpread --params '{"order_spread": [{"profit_target": 0.05}]}'

# Backtesting
riskmanaged backtest run <STRATEGY_ID>
riskmanaged backtest reports <STRATEGY_ID>

# Grid search
riskmanaged grids create-template <STRATEGY_ID>
riskmanaged grids variations <TEMPLATE_ID>
riskmanaged grids create <TEMPLATE_ID>
riskmanaged grids get <GRID_ID>

# Reference data
riskmanaged reference tickers --search BTC
riskmanaged reference patterns
riskmanaged reference constants
```

## MCP Server (for Claude Desktop, Cursor, etc.)

Add to your MCP client config (e.g., `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "riskmanaged": {
      "command": "riskmanaged-mcp",
      "env": {
        "RISKMANAGED_TOKEN": "your_api_token_here",
        "RISKMANAGED_URL": "https://riskmanaged.io"
      }
    }
  }
}
```

The MCP server exposes 30 tools covering strategy creation, indicator management, signal rules, risk management, backtesting, versioning, and grid search optimization.

## Available MCP Tools

| Category | Tools |
|---|---|
| Account | `get_me` |
| Reference | `list_indicator_types`, `get_indicator_schema`, `list_patterns`, `search_tickers`, `get_constants` |
| Strategies | `list_strategies`, `get_strategy`, `create_strategy`, `delete_strategy` |
| Indicators | `add_indicator`, `delete_indicator` |
| Signals | `add_signal_group`, `add_signal_rule`, `delete_signal_rule` |
| Bias | `add_bias_generator`, `add_bias_rule` |
| Risk | `set_stop_loss`, `set_take_profit` |
| Backtest | `run_backtest`, `get_reports`, `run_monte_carlo` |
| Versioning | `commit_version`, `get_versions` |
| Grids | `create_grid_template`, `check_variations`, `create_grid`, `get_grid` |

## License

MIT
