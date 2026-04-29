# RiskManaged MCP — Agent Skill

> **What**: MCP server exposing 30+ tools for building, backtesting, and optimizing algorithmic trading strategies on [riskmanaged.io](https://riskmanaged.io).
>
> **Transport**: `stdio` — works with any MCP-compatible client.

---

## Quick Install

```bash
curl -sSL https://riskmanaged.io/install.sh | bash
```

The installer auto-detects the best Python package manager (`uv` → `pipx` → `pip`) and installs the `riskmanaged-mcp` package. Requires **Python ≥ 3.11**.

### Manual Install

```bash
# uv (fastest)
uv tool install riskmanaged-mcp@git+https://github.com/riskmanaged/riskmanaged-mcp.git

# pipx (isolated)
pipx install git+https://github.com/riskmanaged/riskmanaged-mcp.git

# pip
pip install --user git+https://github.com/riskmanaged/riskmanaged-mcp.git
```

---

## Authentication

1. Generate an API token at [riskmanaged.io/profile](https://riskmanaged.io/profile) → **API Tokens**
2. Configure the CLI:

```bash
riskmanaged auth configure --token YOUR_TOKEN
riskmanaged auth whoami          # verify
```

---

## MCP Server Config

Use this JSON block in any MCP client that follows the standard `mcpServers` schema:

```json
{
  "mcpServers": {
    "riskmanaged": {
      "command": "riskmanaged-mcp",
      "env": {
        "RISKMANAGED_TOKEN": "YOUR_TOKEN",
        "RISKMANAGED_URL": "https://riskmanaged.io"
      }
    }
  }
}
```

---

## Hermes Setup

Add the following to `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  riskmanaged:
    command: riskmanaged-mcp
    env:
      RISKMANAGED_TOKEN: "YOUR_TOKEN"
      RISKMANAGED_URL: "https://riskmanaged.io"
```

Then reload without restarting:

```
/reload-mcp
```

Verify by asking: *"What tools do you have available?"*

---

## OpenClaw Setup

### Option A — Chat Command (easiest)

Tell OpenClaw:

```
install this skill: https://github.com/riskmanaged/riskmanaged-mcp
```

### Option B — Manual Skill

1. Clone or download this repo into your OpenClaw `skills/` directory.
2. This `AGENT.md` file serves as the skill metadata.
3. Set your API token via OpenClaw Settings → Skills → Workspace Skills → Environment Variables:
   - `RISKMANAGED_TOKEN` = your token
   - `RISKMANAGED_URL` = `https://riskmanaged.io`

### Option C — MCPorter Config

If using MCPorter, add to your `mcporter.json`:

```json
{
  "mcpServers": {
    "riskmanaged": {
      "command": "riskmanaged-mcp",
      "env": {
        "RISKMANAGED_TOKEN": "YOUR_TOKEN",
        "RISKMANAGED_URL": "https://riskmanaged.io"
      }
    }
  }
}
```

---

## Available Tools

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

---

## Workflow: Create a Strategy

1. `search_tickers` — find the trading pair (e.g., BTCUSDT)
2. `list_indicator_types` → `get_indicator_schema` — discover indicators
3. `create_strategy` — create with ticker, timeframe, exchange
4. `add_indicator` — add technical indicators
5. `add_signal_group` → `add_signal_rule` — define entry/exit signals
6. `set_stop_loss` / `set_take_profit` — configure risk management
7. `run_backtest` → `get_reports` — evaluate performance
8. `commit_version` — save if satisfied

## Workflow: Grid Search Optimization

1. `create_grid_template` — parameterize a strategy
2. `check_variations` — verify count is within limits
3. `create_grid` — execute grid search (costs 10 tokens)
4. `get_grid` — review ranked results

---

## Important Notes

- Always call `get_indicator_schema` before `add_indicator` to discover parameters and output line names.
- Indicator line names follow: `{Type}_{ticker}_{timeframe}.{line}` (e.g., `RSI_btcusdt_30m.rsi`).
- Line names are **case-sensitive**; tickers are always **lowercase** in line names.
- Grid creation costs **10 tokens** — check balance with `get_me` first.
- Backtests take 30-60 seconds.

---

## Links

- **Platform**: [riskmanaged.io](https://riskmanaged.io)
- **Docs**: [riskmanaged.io/docs](https://riskmanaged.io/#/docs/mcp-overview)
- **GitHub**: [github.com/riskmanaged/riskmanaged-mcp](https://github.com/riskmanaged/riskmanaged-mcp)
- **Install Script**: [riskmanaged.io/install.sh](https://riskmanaged.io/install.sh)
