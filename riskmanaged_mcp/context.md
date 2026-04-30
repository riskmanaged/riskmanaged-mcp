# RiskManaged MCP — LLM Agent Guide

You are connected to the RiskManaged trading strategy platform via MCP.
You can create, configure, backtest, and optimize trading strategies on behalf of the user.

## Platform Overview

RiskManaged is a no-code algorithmic trading strategy builder supporting Binance (crypto) and Bittensor exchanges. Users create strategies by combining technical indicators, signal rules, bias generators, and risk management, then backtest and optimize via grid search.

## Core Concepts

- **Strategy**: A trading configuration with a root ticker/exchange/timeframe, indicators, signal groups, bias generators, and risk management settings.
- **Indicator**: A technical analysis calculation (RSI, MACD, Bollinger Bands, etc.) attached to a strategy. Each has configurable parameters and named output lines.
- **Signal Group**: A named group of rules that trigger trade entries/exits. Each rule has conditions comparing indicator lines.
- **Bias Generator**: Directional filters that restrict trading to long, short, or neutral based on conditions.
- **Risk Management**: Take-profit (TakeProfitSpread) and stop-loss (StopLossSimple, StopLossTrailing, StopLossAtr) configurations.
- **Grid Template**: A parameterized version of a strategy for optimization.
- **Grid Search**: Creates many strategy variations by varying parameters, backtests all of them.

## Indicator Line Naming Convention

Lines follow the pattern: `{IndicatorType}_{ticker}_{timeframe}.{line_name}`

Examples:
- `RSI_btcusdt_30m.rsi`
- `MACD_btcusdt_1h.macd`
- `MACD_btcusdt_1h.macd_signal`
- `BollingerBands_ethusdt_4h.upper`

Always call `get_indicator_schema` first to discover the available output lines for an indicator type.

## Signal Rule Condition Format

Each condition is an object with:
- `trigger_line`: indicator line name or numeric value
- `trigger`: operator — `crossover`, `crossunder`, `gt`, `ge`, `lt`, `le`, `eq`

- `threshold_line`: indicator line or `threshold_value` (a numeric value)

Example conditions:
```json
[
  {"trigger_line": "RSI_btcusdt_30m.rsi", "trigger": "crossover", "threshold_value": 30},
  {"trigger_line": "MACD_btcusdt_30m.macd", "trigger": "gt", "threshold_line": "MACD_btcusdt_30m.macd_signal"}
]
```

## Available Timeframes

`1m`, `5m`, `15m`, `30m`, `1h`, `4h`, `1d`

## Available Exchanges

- `binance` — Crypto pairs (BTCUSDT, ETHUSDT, etc.)
- `bittensor` — Bittensor subnets

## Workflow: Creating a Strategy

1. `search_tickers` — find the trading pair
2. `list_indicator_types` — browse available indicators
3. `get_indicator_schema` — get parameters and output lines
4. `create_strategy` — create with basic config
5. `add_indicator` — add indicators one by one
6. `add_signal_group` — create entry/exit signal groups
7. `add_signal_rule` — add rules with conditions
8. `set_stop_loss` / `set_take_profit` — configure risk management
9. `run_backtest` — evaluate performance
10. `get_reports` — review metrics (Sharpe, return, drawdown)
11. `commit_version` — save if satisfied

## Workflow: Grid Search Optimization

1. Start with a backtested strategy
2. `create_grid_template` — create parameterized template
3. `check_variations` — verify variation count is within limits
4. `create_grid` — run grid search (costs tokens)
5. `get_grid` — review results ranked by performance

## Important Notes

- Always call `get_indicator_schema` before adding an indicator to understand its parameters and output lines.
- Line names are case-sensitive. The ticker in line names is always lowercase (e.g., `btcusdt` not `BTCUSDT`).
- Grid creation costs 10 tokens. Check the user's balance with `get_me` first.
- Backtests may take 30-60 seconds. Inform the user you're waiting.
- The `share` parameter in `commit_version` is always false via MCP (social features are human-only).
- Signal and bias rule conditions are validated at creation time. If a `trigger_line` or `threshold_line` doesn't exist in the strategy, the API returns a `422` error with `error_code: "invalid_condition_line"` and the list of valid `available_lines`. Use this to self-correct line references.
