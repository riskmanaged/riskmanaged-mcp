# RiskManaged — Agent Skill

> **What**: an MCP server and CLI for building, backtesting and optimising
> algorithmic trading strategies on [riskmanaged.io](https://riskmanaged.io),
> and for running LLM agent committees over them.
>
> **Transport**: `stdio` — works with any MCP-compatible client.

---

## Install

```bash
curl -sSL https://riskmanaged.io/install.sh | bash
```

The installer picks the best available Python package manager (`uv` → `pipx` →
`pip`). Requires **Python ≥ 3.11**.

<details>
<summary>Manual install</summary>

```bash
uv tool install riskmanaged-mcp@git+https://github.com/riskmanaged/riskmanaged-mcp.git
pipx install git+https://github.com/riskmanaged/riskmanaged-mcp.git
pip install --user git+https://github.com/riskmanaged/riskmanaged-mcp.git
```

</details>

Two entry points are installed: `riskmanaged` (the CLI) and `riskmanaged-mcp`
(the stdio MCP server).

## Authenticate

```bash
riskmanaged auth login      # opens a browser, one click, token saved
riskmanaged auth whoami     # verify
```

`auth login` writes `~/.riskmanaged/config.json` (chmod 600). If you already
have a token from the profile page, `riskmanaged auth configure --token <TOKEN>`
works too.

The token is per-user and grants full access to that account. Everything you do
acts as its owner — no command takes a user id.

## MCP client config

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

> `RISKMANAGED_URL` must be **`agent.riskmanaged.io`**. `riskmanaged.io` is the
> marketing site and returns HTML, which surfaces as unreadable tool errors.

<details>
<summary>Claude Code, Hermes, OpenClaw, MCPorter</summary>

**Claude Code** — `claude mcp add riskmanaged -- riskmanaged-mcp`

**Hermes** — add to `~/.hermes/config.yaml`, then `/reload-mcp`:

```yaml
mcp_servers:
  riskmanaged:
    command: riskmanaged-mcp
    env:
      RISKMANAGED_TOKEN: "YOUR_TOKEN"
      RISKMANAGED_URL: "https://agent.riskmanaged.io"
```

**OpenClaw** — tell it `install this skill:
https://github.com/riskmanaged/riskmanaged-mcp`, or drop this repo into your
`skills/` directory; this file is the skill metadata.

**MCPorter** — same `mcpServers` block as above in `mcporter.json`.

</details>

---

## Available tools

<!-- BEGIN GENERATED TOOLS -->
_71 tools. This table is generated — run `riskmanaged dev sync-docs` after changing them._

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
| **Grids** | `create_grid_template`, `update_grid_template`, `check_variations`, `create_grid`, `get_grid` |
| **Community** | `share_strategy` |
| **Committee templates** | `list_templates`, `get_template` |
| **Committees** | `list_committees`, `get_committee`, `clone_template`, `trigger_committee_run`, `get_committee_messages`, `get_committee_track_record`, `set_committee_tier`, `list_instance_runs` |
| **Promotion** | `get_committee_promotion_status`, `get_committee_promotion_events`, `list_rollback_candidates`, `rollback_instance` |
| **Proposals** | `list_pending_proposals`, `get_proposal`, `approve_proposal`, `reject_proposal` |
| **Model routes** | `list_model_routes`, `upsert_model_route`, `delete_model_route` |
| **LLM connections** | `list_llm_connections`, `create_llm_connection`, `test_llm_connection`, `reveal_llm_connection_key`, `update_llm_connection`, `delete_llm_connection` |
| **News** | `list_news_articles`, `get_news_article`, `list_news_sources` |
| **Macro** | `list_macro_events`, `get_macro_event` |
| **Spend caps** | `get_user_settings`, `set_daily_token_cap` |
| **Admin (requires the admins role)** | `admin_per_user_spend`, `admin_per_user_spend_history` |
<!-- END GENERATED TOOLS -->

The CLI mirrors the same surface across 10 command groups — `auth`,
`strategies`, `indicators`, `signals`, `bias`, `risk`, `backtest`, `grids`,
`reference` and `agents`. Run `riskmanaged <group> --help` for the exact
parameters.

---

## The model: strategies vs mappings

A **strategy** is logic — indicators, rules, risk settings. It holds no money
and no venue.

An **exchange mapping** is the unit of trading: one user's venue for one
strategy, holding the capital, the risk limits and the positions. Paper vs live
is a property of the mapping.

Consequences worth internalising:

- `strategy.mode` is a **read-only rollup** — `"live"` if any mapping is live,
  otherwise `"paper"`. You cannot set it, and `backtest` / `grid` are not values.
- A newly created or cloned strategy is **not enabled** and does not trade.
- Cloning copies the logic only. The copy has no mappings, so it is paper.

---

## Indicator names and lines

This is the single most common source of failed calls, so it is worth getting
right first time.

An indicator's name defaults to **its type name**, and lines are `{name}.{line}`:

| Indicator | Lines |
|---|---|
| `RSI` | `RSI.rsi`, `RSI.rsi_ob`, `RSI.rsi_os` |
| `MACD` | `MACD.macd`, `MACD.signal`, `MACD.histogram`, `MACD.zero` |
| `BollingerBands` | `BollingerBands.bband_top`, `.bband_mid`, `.bband_low` |
| `ATR` | `ATR.atr`, `ATR.atr_sma`, `ATR.previous_atr` |

There is **no ticker or timeframe in a line name**. For two of the same
indicator, set an explicit `name`:

```bash
riskmanaged indicators add $SID RSI --params '{"length": 7, "name": "fast_rsi"}'
# → fast_rsi.rsi
```

Always call `get_indicator_schema` first. Unknown config fields are rejected
with a **400** naming the valid ones — read it rather than guessing again.

## Conditions

```json
[
  {"trigger_line": "RSI.rsi", "trigger": "crossover", "threshold_value": 30},
  {"trigger_line": "MACD.macd", "trigger": "gt", "threshold_line": "MACD.signal"}
]
```

Operators: `crossover`, `crossunder`, `gt`, `ge`, `lt`, `le`, `eq`. Raw OHLCV
columns (`open`, `high`, `low`, `close`, `volume`) are valid lines. Conditions
may nest under `and` / `or`.

A bad line gives **422** with `error_code: "invalid_condition_line"` and an
`available_lines` list — use it to self-correct.

## Risk management

| Stop loss | Fields |
|---|---|
| `StopLossSimple` | `stoploss_pct` (negative, e.g. `-0.03`) |
| `StopLossTrailing` | `trailing_pct` |
| `StopLossAtr` | `atr_multiplier`, `atr_line` |

| Take profit | Fields |
|---|---|
| `TakeProfitSpread` | `order_spread`, a list of `{"profit_target": 0.05}` |
| `TakeProfitAtr` | `atr_multiplier`, `atr_line` |

The ATR variants need `atr_line` pointed at an ATR line on *this* strategy — add
an `ATR` indicator and pass `ATR.atr_sma`. The field default refers to an
indicator your strategy will not have.

---

## Workflow: build a strategy

```bash
riskmanaged reference tickers --search BTC
riskmanaged indicators schema RSI
riskmanaged strategies create --name "RSI Mean Reversion" --ticker BTCUSDT --timeframe 30m
riskmanaged indicators add $SID RSI --params '{"length": 14}'
riskmanaged signals add-group $SID entry
riskmanaged signals add-rule $SID entry --action enter_position --direction long \
  --conditions '[{"trigger_line":"RSI.rsi","trigger":"crossover","threshold_value":30}]'
riskmanaged risk set-sl $SID StopLossSimple --params '{"stoploss_pct": -0.03}'
riskmanaged backtest run $SID
riskmanaged backtest reports $SID
```

`backtest reports` nests its metrics under **`stats`** — `sharpe`,
`cumulative_return`, `max_drawdown`, `time_in_market`.

## Workflow: grid search

```bash
riskmanaged grids create-template $SID     # returns a bare id string
riskmanaged grids variations $TID          # {count, limit}
riskmanaged grids create $TID              # costs 10 tokens
riskmanaged grids get $GID
```

If `count` exceeds `limit`, adjust with `riskmanaged grids update-template $TID
--data '{"template_data": {...}}'` — the whole `template_data` must be
resubmitted, so `get-template` first. Per-variation metrics in `grids get` live
under `variation["backtest"]` and are absent for untested variations.

## Workflow: agent committees

```bash
riskmanaged agents templates list
riskmanaged agents committees clone --template-slug macro-fund --name "My Fund" --strategy-id $SID
riskmanaged agents committees trigger $IID
riskmanaged agents proposals list
riskmanaged agents proposals approve $PID
```

Committees spend LLM tokens. `riskmanaged agents spend get` shows the daily cap
and today's usage.

---

## Notes

- Line names are case-sensitive.
- Grid creation costs **10 tokens** unless a free daily run is available — check
  with `riskmanaged auth whoami`.
- Backtests take up to 60 seconds on first run; candles are cached afterwards.
- No command takes a user id. Identity comes from the token.

## Links

- **Platform**: [riskmanaged.io](https://riskmanaged.io)
- **Docs**: [riskmanaged.io/#/docs/mcp-overview](https://riskmanaged.io/#/docs/mcp-overview)
- **GitHub**: [github.com/riskmanaged/riskmanaged-mcp](https://github.com/riskmanaged/riskmanaged-mcp)
