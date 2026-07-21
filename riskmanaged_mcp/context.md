# RiskManaged — LLM Agent Guide

You are connected to the RiskManaged trading platform. You can research, build,
backtest and optimise trading strategies, run LLM agent committees over them,
and read the market context those committees use.

Everything you touch belongs to the user whose API token you are holding. You
never name a user id — the server resolves identity from the token.

## Core concepts

- **Strategy** — the *logic*: a root ticker/exchange/timeframe plus indicators,
  signal groups, bias generators and risk management. A strategy has no venue
  and no money.
- **Exchange mapping** — the *unit of trading*: one user's venue for one
  strategy. It holds the capital, the risk limits and the positions. A strategy
  can have several, owned by different users, in different modes.
- **Paper vs live** is a property of the mapping, never of the strategy.
  `strategy.mode` is a read-only rollup: `"live"` if any mapping is live, else
  `"paper"`. It is not settable, and the values `backtest` and `grid` no longer
  exist.
- **Indicator** — a calculation attached to a strategy (RSI, MACD, …) with
  configurable parameters and named output lines.
- **Signal group** — named rules that trigger entries and exits.
- **Bias generator** — directional filters restricting trading to long, short
  or neutral.
- **Grid template / grid search** — a parameterised strategy, and the run that
  backtests every variation of it.
- **Committee** — a group of LLM agents that deliberate over a strategy and
  raise trade *proposals*. Its `autonomy_tier` decides what happens next:
  `suggest` (you approve each one), `paper_track` (fills on paper to build a
  record), `auto_live` (fills for real).

## Indicator names and lines — read this before writing any condition

An indicator's name defaults to **its type name**, and its lines are
`{name}.{line}`.

```
RSI              →  RSI.rsi, RSI.rsi_ob, RSI.rsi_os
MACD             →  MACD.macd, MACD.signal, MACD.histogram, MACD.zero
BollingerBands   →  BollingerBands.bband_top, .bband_mid, .bband_low
ATR              →  ATR.atr, ATR.atr_sma, ATR.previous_atr
```

There is **no ticker or timeframe in a line name**. If you want two of the same
indicator on one strategy, give them explicit names:

```
add_indicator(strategy_id, "RSI", {"length": 7,  "name": "fast_rsi"})
add_indicator(strategy_id, "RSI", {"length": 21, "name": "slow_rsi"})
→ fast_rsi.rsi, slow_rsi.rsi
```

Always call `get_indicator_schema` before `add_indicator`. It returns
`required_input` (the fields you may set) and `lines` (what you may reference).
Do not send `exchange`, `timeframe`, `ticker` or `category` — they are filled in
from the strategy.

**Unknown config fields are rejected with a 400** that lists the valid ones.
Read it and retry; do not guess a second time.

## Signal and bias conditions

Each condition is an object:

- `trigger_line` — an indicator line, or a raw OHLCV column
  (`open`, `high`, `low`, `close`, `volume`)
- `trigger` — one of `crossover`, `crossunder`, `gt`, `ge`, `lt`, `le`, `eq`
- `threshold_line` *or* `threshold_value` — what to compare against

```json
[
  {"trigger_line": "RSI.rsi", "trigger": "crossover", "threshold_value": 30},
  {"trigger_line": "MACD.macd", "trigger": "gt", "threshold_line": "MACD.signal"}
]
```

Conditions may nest under `and` / `or`. Two optional fields, `trigger_line_shift`
and `threshold_line_shift` (both default `0`), compare against an earlier bar.

If a line does not exist you get **422** with `error_code:
"invalid_condition_line"` and an `available_lines` list — use it to self-correct.
A malformed condition (a bare string instead of an object) gives
`invalid_condition_structure`.

## Risk management

Stop-loss types and their fields:

| Type | Fields |
|---|---|
| `StopLossSimple` | `stoploss_pct` (negative, e.g. `-0.03`) |
| `StopLossTrailing` | `trailing_pct` |
| `StopLossAtr` | `atr_multiplier`, `atr_line` |

Take-profit types:

| Type | Fields |
|---|---|
| `TakeProfitSpread` | `order_spread` — a list of `{"profit_target": 0.05}` |
| `TakeProfitAtr` | `atr_multiplier`, `atr_line` |

`StopLossAtr` and `TakeProfitAtr` need `atr_line` pointed at a real ATR line on
*this* strategy — add an `ATR` indicator first and pass `ATR.atr_sma`. The
field's default refers to an indicator your strategy will not have.

## Available values

- Timeframes: `1m`, `5m`, `15m`, `30m`, `1h`, `4h`, `1d`
- Exchanges: `binance`
- Strategy modes (read-only): `paper`, `live`

## Workflow: build and backtest a strategy

1. `search_tickers` — confirm the pair exists
2. `list_indicator_types` → `get_indicator_schema` — discover parameters and lines
3. `create_strategy`
4. `add_indicator` — one per indicator
5. `add_signal_group` → `add_signal_rule` — entry and exit
6. `set_stop_loss` / `set_take_profit`
7. `run_backtest` → `get_reports` — metrics are under the `stats` key
8. `commit_version` — save a version you want to keep

## Workflow: grid search

1. `create_grid_template` — returns the template id **as a bare string**
2. `check_variations` — returns `{count, limit}`
3. `update_grid_template` — if `count` exceeds `limit`, widen the step or narrow
   the ranges and resubmit the whole `template_data`
4. `create_grid` — costs 10 tokens unless a free daily run is available
5. `get_grid` — poll until `completed`; per-variation metrics live under
   `variation["backtest"]` and are absent for untested variations

## Workflow: agent committees

1. `list_templates` → `clone_template` — bind a committee to a strategy
2. `trigger_committee_run` — one deliberation cycle
3. `get_committee_messages` — read the deliberation
4. `list_pending_proposals` → `approve_proposal` / `reject_proposal`
5. `get_committee_track_record`, `get_committee_promotion_status` — is it ready
   for a higher autonomy tier?

Committees cost LLM tokens. `get_user_settings` shows the daily cap and today's
spend; `set_daily_token_cap` changes it.

## News-driven strategies

The `NewsSentiment` indicator publishes `sentiment_score`, `article_count`,
`high_urgency_count`, `bullish_count`, `bearish_count` and `dominant_news_type`.

Three things to know before relying on it:

- It reads only articles that have already been **sentiment-tagged**. Check with
  `list_news_articles` that tagged articles exist for your symbol; historical
  backtests over periods before tagging began will see nothing.
- `sentiment_score` is a weighted **sum**, not a bounded average — it scales
  with article volume, so thresholds must be tuned per symbol rather than copied.
- `min_articles` is accepted but not applied. Gate on `article_count` in your
  conditions instead.

## Notes

- Line names are case-sensitive.
- Grid creation costs 10 tokens — check the balance with `get_me` first.
- Backtests take up to 60 seconds on first run; candles are cached afterwards.
- A new or cloned strategy is created **not enabled** and does not trade. Taking
  it live means creating a live exchange mapping for it.
- Errors are returned as errors, not as text. Read the message — 4xx bodies name
  the offending field and the valid alternatives.
