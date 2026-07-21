# RiskManaged — Autonomous Strategy Research Cron

> **Purpose**: This document defines a deterministic, step-by-step workflow for an autonomous agent to research trading strategy ideas from the web, implement them on the RiskManaged platform via MCP tools, validate them, optimize via grid search, and compile learnings for the next run.
>
> **Required Skills**: `riskmanaged-mcp` (MCP server), `web-search-plus` (web search)
>
> **Success Criteria**: A completed grid search with results reviewed and learnings saved to memory.

---

## Overview — State Machine

```
START
  │
  ├─► PHASE 1: Preflight Checks
  ├─► PHASE 2: Research a Strategy Idea
  ├─► PHASE 3: Build the Strategy
  ├─► PHASE 4: Validate the Strategy
  ├─► PHASE 5: Grid Template & Variation Tuning
  ├─► PHASE 6: Execute Grid Search
  ├─► PHASE 7: Review Results
  ├─► PHASE 8: Compile Learnings
  │
  ▼
 END
```

Each phase ends with a **GATE** — a pass/fail check. If the gate fails, the phase includes explicit recovery steps before retrying or aborting.

---

## PHASE 1 — Preflight Checks

**Goal**: Confirm the agent has everything it needs before doing anything.

### Step 1.1 — Verify Authentication

Run:

```bash
riskmanaged auth whoami
```

- **IF** the response shows `Username`, `Plan`, and `Tokens` → **PASS**. Record `Tokens` value as `$BALANCE`.
- **IF** the response is an error → **ABORT**. Print: `"Authentication failed. Ensure RISKMANAGED_TOKEN is set correctly."`

### Step 1.2 — Check Token Balance

- **IF** `$BALANCE >= 10` → **PASS**. Proceed to Phase 2.
- **IF** `$BALANCE < 10` → **ABORT**. Print: `"Insufficient tokens ($BALANCE). Grid creation costs 10 tokens. Top up at riskmanaged.io/profile."`

### Step 1.3 — Load Prior Learnings (if any)

Check your memory/context for a file or memory entry called `strategy_learnings`. If it exists, read it. These are findings from prior runs and MUST influence your research queries and strategy design in Phase 2.

- If no prior learnings exist, that is fine — this is a first run.

---

## PHASE 2 — Research a Strategy Idea

**Goal**: Find a concrete, implementable trading strategy idea from the web.

### Step 2.1 — Discover Available Indicators

Before formulating search queries, run:

```bash
riskmanaged indicators list-types
```

This returns the **full catalog** of indicators the platform supports, grouped by category. Scan the list and note any indicators that are unfamiliar — these may inspire novel strategy ideas you wouldn't otherwise consider. Do NOT limit yourself to well-known indicators like RSI or MACD; the platform may support specialized indicators that are worth exploring.

Save the list for reference — you will cross-check your hypothesis against it in Step 2.5.

### Step 2.2 — Formulate Search Queries

Generate **3 search queries** designed to find actionable indicator-based trading strategies. Use varied angles:

1. A query about a specific indicator combination (e.g., `"RSI MACD crossover trading strategy crypto"`)
2. A query about a market condition or style (e.g., `"mean reversion strategy with Bollinger Bands intraday crypto"`)
3. A query informed by prior learnings (e.g., if a past run found RSI oversold worked well, try: `"RSI divergence strategy with volume confirmation"`)

If prior learnings exist from Phase 1.3, at least one query **MUST** build upon those findings.

**TIP**: Use the indicator list from Step 2.1 to diversify your queries. If you see an indicator you haven't used before, formulate a query around it.

### Step 2.3 — Execute Searches

For each query, run:

```bash
uv run python ~/.openclaw/skills/web-search-plus/scripts/search.py --provider searxng --query "<query>"
```

### Step 2.4 — Read and Extract

For each search result set:
1. Identify the **top 2-3 most relevant** results (pages that describe a specific strategy with indicator names, parameters, and entry/exit rules).
2. Read those pages to extract:
   - **Indicator(s)** used (e.g., RSI, MACD, Bollinger Bands, EMA)
   - **Parameter values** mentioned (e.g., RSI period=14, EMA period=21)
   - **Entry conditions** (e.g., "buy when RSI crosses above 30 and MACD histogram turns positive")
   - **Exit conditions** (e.g., "sell when RSI crosses below 70")
   - **Timeframe** recommendation (e.g., "works best on 4h")
   - **Ticker/market** recommendation (e.g., "BTC", "high-cap altcoins")

### Step 2.5 — Formulate Hypothesis

Write a clear hypothesis in this format:

```
HYPOTHESIS: [Name of Strategy]
DESCRIPTION: [1-2 sentence summary]
INDICATORS: [List of indicators with initial parameters]
ENTRY RULE: [Precise conditions for entering long/short]
EXIT RULE: [Precise conditions for exiting]
RISK MANAGEMENT: [Stop loss type + take profit type]
TIMEFRAME: [Primary timeframe]
TICKER: [Primary ticker]
```

### Step 2.6 — Verify Indicators Are Supported

Cross-check every indicator in your hypothesis against the list you retrieved in Step 2.1.

- For **each indicator** in your hypothesis, confirm it exists in the list.
- **IF** an indicator is not available → substitute with the closest available alternative from the list.
- **IF** no suitable substitute exists → return to Step 2.5 and reformulate with available indicators.

### GATE 2

- You have a hypothesis with only supported indicators → **PASS**. Proceed to Phase 3.
- You cannot form a valid hypothesis from any search results → **ABORT**. Print: `"No actionable strategy found. Try different search terms next run."`

---

## PHASE 3 — Build the Strategy

**Goal**: Create a fully configured strategy on the platform using MCP tools. Each sub-step must succeed before moving to the next.

### Step 3.1 — Get Indicator Schemas

For **each indicator** in your hypothesis, run:

```bash
riskmanaged indicators schema <IndicatorType>
```

Record the response. You need:
- The **parameter names and types** (from `required_input`)
- The **output line names** (from `lines`)

**CRITICAL**: The output line names determine what you can reference in signal rules. Write them down exactly as returned. Lines follow the naming convention: `{IndicatorType}_{ticker}_{timeframe}.{line_name}` where **ticker is always lowercase**.

### Step 3.2 — Verify Ticker Exists

Run:

```bash
riskmanaged reference tickers --search "<TICKER>" --exchange binance
```

- **IF** the ticker appears in results → **PASS**. Record the exact symbol (e.g., `BTCUSDT`).
- **IF** not found → retry the search with a shorter fragment of the symbol. If still not found → **pick a default**: `BTCUSDT`.

### Step 3.3 — Create the Strategy

Run:

```bash
riskmanaged strategies create --name "<hypothesis_name>" --exchange binance --timeframe "<timeframe>" --ticker "<TICKER>"
```

- **IF** response contains an `id` field → **PASS**. Record `$STRATEGY_ID` = the returned `id`.
- **IF** error → check the error message. Common issues:
  - Invalid timeframe: use one of `1m`, `5m`, `15m`, `30m`, `1h`, `4h`, `1d`
  - Invalid ticker: go back to Step 3.2
  - Retry once after fixing. If still fails → **ABORT**.

### Step 3.4 — Add Indicators (One at a Time)

For **each indicator** in your hypothesis, run:

```bash
riskmanaged indicators add $STRATEGY_ID <IndicatorType> --params '{"<param>": <value>}'
```

**IMPORTANT CONFIG RULES**:
- Do NOT include `exchange`, `timeframe`, `ticker`, or `category` in the config — those are inherited from the strategy's root settings.
- Only include parameters that the schema's `required_input` lists (excluding exchange/timeframe/ticker).
- If the schema shows a parameter with a `default`, you may omit it to use the default.

**RECORD THE INDICATOR NAME** — You will need it in Step 3.6 for signal rules:
- **IF you did NOT pass a custom `name`** in `--params` → the indicator name is **the type name itself** (e.g., adding `RSI` → the indicator is named `RSI`, and its lines are `RSI.rsi`, `RSI.rsi_ob`, `RSI.rsi_os`). The ticker and timeframe do **not** appear in the name.
- **IF you passed a custom `name`** in `--params` (e.g., `--params '{"name": "fast_rsi", "length": 7}'`) → the indicator name is exactly what you provided (e.g., `fast_rsi`).
- **Write down every indicator name** as you add them. These names are the prefix for all line references in signal conditions.

**After each `add_indicator` call**:
- **IF** success → record the indicator name, then continue to next indicator
- **IF** error → read the error carefully. The most common mistake is passing an invalid parameter name or type. Re-check the schema and retry once.

### Step 3.5 — Create Signal Group

Run:

```bash
riskmanaged signals add-group $STRATEGY_ID main_signals
```

- **IF** success → **PASS**
- **IF** error → the name may conflict. Try `name="signals_1"` instead.

### Step 3.6 — Add Entry Rule

> **⚠ CRITICAL — Determine the correct line names BEFORE writing conditions.**
>
> The line reference format is: `{indicator_name}.{line_name}`
>
> The `indicator_name` depends on how you added the indicator in Step 3.4:
>
> | How you added it | Indicator name | Example line reference |
> |---|---|---|
> | **No custom name** (default) | the type name | `RSI.rsi` |
> | **Custom name provided** via `--params '{"name": "X"}'` | Exactly `X` | `fast_rsi.rsi` |
>
> To verify, run `riskmanaged strategies get $STRATEGY_ID` and look at the keys inside the `indicators` object — those keys ARE the indicator names.

Construct the entry conditions array. Each condition is an object:

```json
{
  "trigger_line": "<indicator_name>.<line>",
  "trigger": "<operator>",
  "threshold_value": <number>
}
```

OR for comparing two indicator lines:

```json
{
  "trigger_line": "<indicator_name>.<line>",
  "trigger": "<operator>",
  "threshold_line": "<indicator_name>.<line>"
}
```

**Available operators**: `crossover`, `crossunder`, `gt`, `ge`, `lt`, `le`, `eq`

**LINE NAME RULES** (these are the #1 source of errors):
- Format: **`{indicator_name}.{line_name}`**
- `indicator_name` = the name recorded in Step 3.4 (either the default or your custom name)
- Default name: the type name exactly as listed by `riskmanaged indicators list-types` (e.g., `RSI`, `MACD`, `BollingerBands`). No ticker, no timeframe, no lowercasing.
- `line_name` = exactly as returned in the schema's `lines` array from `riskmanaged indicators schema <type>`

**Examples**:
- Default: RSI added to BTCUSDT 30m → line is `RSI.rsi`
- Custom: RSI added with `"name": "fast_rsi"` → line is `fast_rsi.rsi`
- Default: MACD added to ETHUSDT 1h → lines are `MACD.macd`, `MACD.signal`, `MACD.histogram`, `MACD.zero`

> There is no `macd_signal` or `macd_hist` line. Always take line names verbatim
> from the schema's `lines` array — never construct them.

Run:

```bash
riskmanaged signals add-rule $STRATEGY_ID main_signals --action enter_position --direction <long/short> --conditions '<your conditions JSON array>'
```

- **IF** success → continue
- **IF** error mentioning "invalid_condition_line" → the API validates lines at rule creation time. Read the `available_lines` array from the error response body to see exactly which lines exist on this strategy. Fix your line references to match and retry.
- **IF** other error → double-check your line names against the indicator schema output. Fix and retry.

### Step 3.7 — Add Exit Rule

Construct exit conditions following the same format as Step 3.6.

Run:

```bash
riskmanaged signals add-rule $STRATEGY_ID main_signals --action exit_position --direction <long/short> --conditions '<your exit conditions JSON array>'
```

- **IF** success → continue
- **IF** error → fix line names and retry (same as Step 3.6).

### Step 3.8 — (Optional) Add Bias Generator

If your hypothesis includes a directional bias filter (e.g., "only trade long when price is above 200 EMA"):

```bash
riskmanaged bias add $STRATEGY_ID trend_filter
```

Then:

```bash
riskmanaged bias add-rule $STRATEGY_ID trend_filter --direction long --conditions '<conditions JSON array>'
```

Skip this step if no bias filter is part of your hypothesis.

### Step 3.9 — Set Risk Management

**Stop Loss** — Choose one:

| Type | Config | When to Use |
|------|--------|-------------|
| `StopLossSimple` | `{"stoploss_pct": -0.03}` | Fixed percentage stop (negative) |
| `StopLossTrailing` | `{"trailing_pct": 0.025}` | Trailing stop (recommended) |
| `StopLossAtr` | `{"atr_multiplier": 2.0, "atr_line": "ATR.atr_sma"}` | Volatility-based stop |

> `StopLossAtr` needs `atr_line` pointing at an ATR line on **this** strategy —
> add an `ATR` indicator first. Its built-in default refers to an indicator your
> strategy will not have.

Run:
```bash
riskmanaged risk set-sl $STRATEGY_ID <type> --params '{"trailing_pct": 0.025}'
```

**Take Profit** — Use `TakeProfitSpread`:

```bash
riskmanaged risk set-tp $STRATEGY_ID TakeProfitSpread --params '{"order_spread": [{"profit_target": 0.03}, {"profit_target": 0.06}, {"profit_target": 0.10}]}'
```

**Timeframe-based TP/SL guidelines**:
- **1m–5m**: SL 1.5–3%, TP targets 2–4%
- **15m**: SL 2–3.5%, TP targets 3–5%
- **30m**: SL 2.5–4%, TP targets 4–8%
- **1h**: SL 3–5%, TP targets 5–10%
- **4h–1d**: SL 4–8%, TP targets 8–15%

### GATE 3

Run `riskmanaged strategies get $STRATEGY_ID` and verify the response contains:
- `indicators` → at least 1 indicator present
- `alert_generators` → at least 1 signal group with at least 2 rules (entry + exit)
- `risk_management` → has both `stop_loss` and `take_profit`

- **IF** all three checks pass → **PASS**. Proceed to Phase 4.
- **IF** any check fails → go back to the specific failing step (3.4, 3.5–3.7, or 3.9) and fix.

---

## PHASE 4 — Validate the Strategy (Backtest)

**Goal**: Run a backtest to confirm the strategy is functional and produces results.

### Step 4.1 — Run Backtest

Run:
```bash
riskmanaged backtest run $STRATEGY_ID
```

This may take 30–60 seconds. Wait for the response.

- **IF** the response contains backtest results (has `sharpe`, `cumulative_return`, etc.) → **PASS**
- **IF** error → the strategy configuration is invalid. Common causes:
  - Signal conditions reference indicator lines that don't exist → go back to Step 3.6/3.7
  - Indicator parameters are out of range → go back to Step 3.4
  - Fix and retry. **Maximum 3 retries** before ABORT.

### Step 4.2 — Check Results Are Reasonable

Run:
```bash
riskmanaged backtest reports $STRATEGY_ID
```

Record — these live under the response's **`stats`** object, not at the top level:
- `$SHARPE` = `stats.sharpe`
- `$RETURN` = `stats.cumulative_return`
- `$DRAWDOWN` = `stats.max_drawdown`
- `$TIME_IN_MARKET` = `stats.time_in_market`

> If the strategy has never been backtested, this returns **404**. Run
> `riskmanaged backtest run $STRATEGY_ID` first.

**Reasonableness check** (not about performance — just about whether the strategy is functional):
- **IF** `$TIME_IN_MARKET == 0` → the strategy never entered a trade. Entry conditions are too restrictive. Go back to Step 3.6 and loosen conditions.
- **IF** `$TIME_IN_MARKET > 0` → **PASS**. The strategy is functional regardless of performance. Proceed to Phase 5.

### Step 4.3 — Commit Initial Version

Use the MCP tool `commit_version`:
```
commit_version(strategy_id="$STRATEGY_ID", change_log="Initial version - pre-grid baseline")
```

> **Note**: Version commit is only available via MCP, not the CLI.

This saves the baseline configuration as version 1.

### GATE 4

- Strategy has been backtested and time_in_market > 0 → **PASS**. Proceed to Phase 5.
- Cannot get strategy to produce trades after 3 fix attempts → **ABORT**. Save the hypothesis and error details to learnings.

---

## PHASE 5 — Grid Template & Variation Tuning

**Goal**: Create a grid template from the strategy and tune parameter ranges to run as close to the variation limit as possible. **Exceeding the limit is never acceptable** — the agent must always self-correct.

### Step 5.1 — Create Grid Template

Run:
```bash
riskmanaged grids create-template $STRATEGY_ID
```

- **IF** the response is a template id → **PASS**. Record `$TEMPLATE_ID`.
  The endpoint returns the id as a **bare JSON string**, not an object — there is
  no `template_id` key to read.
- **IF** error → the strategy may not be valid for grid search. Check gate 3 conditions again.

### Step 5.2 — Check Variation Count

Run:
```bash
riskmanaged grids variations $TEMPLATE_ID
```

Record:
- `$COUNT` = the `count` field (number of variations)
- `$LIMIT` = the `limit` field (maximum allowed)

### Step 5.3 — Validate and Adjust (Mandatory Loop)

The grid template auto-generates default parameter ranges. You **must** validate the variation count and adjust until the count is within the acceptable range.

**Target**: Get `$COUNT` as close to `$LIMIT` as possible without exceeding it. Ideal range: `$LIMIT * 0.5` to `$LIMIT`.

**How variations are calculated**: The total count is the **product** of all parameter values across all indicators. For example:
- Indicator A has `period` range 10-20 step 1 = 11 values
- Indicator B has `period` range 5-15 step 1 = 11 values
- Total variations = 11 × 11 = 121

---

**IF `$COUNT > $LIMIT`** (over the limit — **must fix before proceeding**):

> ⚠ **This is never acceptable.** You cannot proceed to Phase 6 while over the limit.

**How to apply any adjustment.** There is exactly one way to change a template,
and it replaces the whole `template_data` — so always read it first, edit the
structure, then write it back:

```bash
riskmanaged grids get-template $TEMPLATE_ID      # read the current template_data
riskmanaged grids update-template $TEMPLATE_ID --data '{"template_data": { ...edited... }}'
riskmanaged grids variations $TEMPLATE_ID        # re-check {count, limit}
```

Apply these in order until `$COUNT <= $LIMIT`, re-checking after each:

1. **Increase `range_step`**: Double the step on the parameter with the most values. This roughly halves that parameter's contribution to the product.
2. **Narrow ranges**: Reduce `range_start` and/or `range_end` to shrink the number of discrete values per parameter.
3. **Remove indicator variations**: If the template varies parameters on 3+ indicators, fix the least important indicator's parameters to single values by setting `range_start == range_end`.
4. **Remove timeframe/ticker variations**: Reduce `grid` arrays to a single value.

---

**IF `$COUNT < $LIMIT * 0.5`** (under-utilizing the limit):

1. Get the current template: `riskmanaged grids get-template $TEMPLATE_ID`.
2. Identify parameters with narrow ranges or large step sizes. Apply edits with
   `riskmanaged grids update-template $TEMPLATE_ID --data '{"template_data": {...}}'`,
   which replaces the whole `template_data`.
3. **Widen ranges**: Expand `range_start` and `range_end`. For integer parameters like periods, use broader exploration windows.
4. **Reduce step sizes**: If `range_step` is large, reduce it to produce more values (e.g., step 5 → step 2).
5. **Add timeframe variations**: Add timeframes to the `grid` array (e.g., `["15m", "30m", "1h"]`).
6. **Add ticker variations**: Test across multiple markets.
7. Recalculate mentally: multiply all individual parameter value counts together. **Ensure the estimate stays ≤ `$LIMIT` before applying.**
8. Re-check: `riskmanaged grids variations $TEMPLATE_ID`.

> ⚠ When widening, always verify **before applying** that your estimated count won't exceed `$LIMIT`. If widening would push you over, widen less aggressively.

---

**IF `$LIMIT * 0.5 <= $COUNT <= $LIMIT`** → **PASS**. The count is in the ideal range.

### Step 5.4 — Tuning Loop

Repeat Step 5.3 until one of these conditions is met:
- `$COUNT` is in the ideal range (`$LIMIT * 0.5` to `$LIMIT`) → **PASS**
- You have completed **5 adjustment cycles** → proceed with the current count as long as `$COUNT <= $LIMIT`

**Maximum iterations**: 5 adjustment cycles.

**HARD RULE**: If after 5 cycles `$COUNT` is still **above** `$LIMIT`, apply the **emergency fallback**:
1. Set ALL indicator parameters to single values (`range_start == range_end`)
2. Pick the **2 most impactful parameters** and restore only those to small ranges
3. Re-check variations — this is guaranteed to bring `$COUNT` under `$LIMIT`
4. You **must not** proceed to Phase 6 until `$COUNT <= $LIMIT`

### GATE 5

- `$COUNT <= $LIMIT` → **PASS**. Proceed to Phase 6.
- `$COUNT <= 10` → the strategy doesn't have enough tunable parameters. Proceed to Phase 6 anyway (a small grid is still useful).
- `$COUNT > $LIMIT` → **DO NOT PROCEED**. Return to Step 5.3 and apply the emergency fallback. This gate cannot be passed while over the limit.

---

## PHASE 6 — Execute Grid Search

**Goal**: Create the grid search, which will backtest all variations.

### Step 6.1 — Final Balance Check

Run `riskmanaged auth whoami` and verify `Tokens >= 10`.

- **IF** sufficient → continue
- **IF** insufficient → **ABORT**. Print: `"Not enough tokens to create grid. Balance: $BALANCE, Required: 10"`

### Step 6.2 — Create Grid

Run:
```bash
riskmanaged grids create $TEMPLATE_ID
```

This will:
1. Charge 10 tokens (or use a free daily run if available)
2. Create all strategy variations
3. Start backtesting all of them (this happens server-side)

- **IF** response contains `grid_id` → **PASS**. Record `$GRID_ID`. Record `$VARIATION_COUNT` from the response.
- **IF** error about tokens → **ABORT** with balance message.
- **IF** error about too many variations → go back to Phase 5, Step 5.3 and reduce.
- **IF** other error → **ABORT** with error details.

### Step 6.3 — Wait for Grid Completion

The grid backtests all variations server-side. This can take several minutes depending on the number of variations.

Run `riskmanaged grids get $GRID_ID` to check progress.

- Look at `tested_count` vs `total_variations`.
- **IF** `tested_count == total_variations` or `completed == true` → **PASS**. Proceed to Phase 7.
- **IF** `tested_count < total_variations` → wait 30 seconds and re-check. **Maximum 20 checks** (10 minutes total).
- **IF** still not complete after 20 checks → proceed to Phase 7 anyway with partial results (the grid results are available incrementally).

### GATE 6

- Grid created and at least some results available → **PASS**. Proceed to Phase 7.

---

## PHASE 7 — Review Results

**Goal**: Analyze the grid search results and identify the best-performing variations.

### Step 7.1 — Get Grid Results

Run:
```bash
riskmanaged grids get $GRID_ID
```

### Step 7.2 — Extract Top Performers

From the `variations` array in the response, filter to variations where `tested == true` and a `backtest` object is present.

The metrics are nested under `backtest` — only `id`, `name`, `root_ticker`,
`root_timeframe` and `tested` are top-level, and `backtest` is **absent
entirely** for untested variations. Sorting on a top-level `sharpe` yields
`None` for every row.

Sort by `backtest.sharpe` descending. Record the **top 5**:

For each, note:
- `id` (strategy_id)
- `name`
- `backtest.sharpe`
- `backtest.cumulative_return`
- `backtest.max_drawdown`
- `backtest.time_in_market`

### Step 7.3 — Analyze Patterns

Look at the top 5 variations and identify:
1. **Which parameter values appear most frequently in top results?** (e.g., "RSI period 14-18 dominates the top 5")
2. **Which timeframes perform best?** (if timeframe was varied)
3. **Which tickers perform best?** (if ticker was varied)
4. **What is the distribution of Sharpe ratios?** (are most variations profitable, or only a few?)

### Step 7.4 — Get Detailed Report on Best Strategy

Take the strategy ID of the #1 ranked variation and run:
```bash
riskmanaged backtest reports <best_strategy_id>
```

Record the full report metrics.

### Step 7.5 — (Optional) Run Monte Carlo on Best Strategy

If the best strategy has a Sharpe > 0.5:
```bash
riskmanaged backtest montecarlo <best_strategy_id> --sims 1000
```

This provides statistical confidence in the backtest results.

### GATE 7

- Results reviewed and top performers identified → **PASS**. Proceed to Phase 8.

---

## PHASE 8 — Compile Learnings

**Goal**: Save structured findings so the next run builds on this one.

### Step 8.1 — Compile Results Summary

Create a structured summary containing:

```
=== RUN RESULTS ===
Date: <current date>
Hypothesis: <name from Phase 2>
Description: <description from Phase 2>
Ticker: <ticker used>
Timeframe: <timeframe used>
Indicators Used: <list>
Grid Variations Tested: <number>
Grid ID: <grid_id>

--- TOP 5 RESULTS ---
1. <name> | Sharpe: <value> | Return: <value>% | MaxDD: <value>% | TiM: <value>%
2. <name> | Sharpe: <value> | Return: <value>% | MaxDD: <value>% | TiM: <value>%
3. ...
4. ...
5. ...

--- KEY FINDINGS ---
- <Finding 1: e.g., "RSI period 14 consistently outperforms period 21">
- <Finding 2: e.g., "30m timeframe produced higher Sharpe than 1h">
- <Finding 3: e.g., "Strategy shows strong mean reversion characteristics">

--- WHAT WORKED ---
- <What worked well in this run>

--- WHAT TO TRY NEXT ---
- <Suggested next hypothesis based on findings>
- <Parameter ranges to explore further>
- <Alternative indicators to test>

--- WHAT TO AVOID ---
- <What didn't work>
- <Parameter ranges that consistently underperform>
```

### Step 8.2 — Save to Memory

Save the compiled results to your persistent memory/context under the key `strategy_learnings`. If prior learnings exist, **append** this run's results — do not overwrite.

This ensures the next run (starting from Phase 1.3) can read past findings and make informed decisions.

### Step 8.3 — Final Status Report

Print a summary to the user:

```
✅ Strategy Research Run Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Hypothesis: <name>
Variations Tested: <count>
Best Sharpe: <value>
Best Return: <value>%
Grid ID: <grid_id>
Learnings saved to memory.
```

---

## Error Recovery Reference

| Error | Likely Cause | Fix |
|-------|-------------|-----|
| `"invalid_condition_line"` in signal/bias rules | `trigger_line` or `threshold_line` references a line that doesn't exist on any indicator in the strategy | Read the `available_lines` array from the error response. Correct the line name and retry. Run `riskmanaged strategies get $STRATEGY_ID` to see all indicator names. |
| `"line not found"` in signal rules | Indicator line name is wrong | Re-check `riskmanaged indicators schema <type>` output. Remember: ticker is **lowercase** in line names |
| `"Indicator not found"` | Wrong indicator type name | Run `riskmanaged indicators list-types` to get exact names |
| `"Strategy not found"` | Strategy ID is wrong or was deleted | Re-check `$STRATEGY_ID` |
| `"Too many variations"` | Grid template exceeds limit | Reduce parameter ranges in Phase 5 |
| `"Insufficient tokens"` | Balance too low | Cannot proceed without tokens |
| Backtest returns no trades | Entry conditions too restrictive | Loosen signal conditions (use `gt`/`lt` instead of `crossover`, lower thresholds) |
| Backtest takes too long | Large timeframe + long history | Use a shorter timeframe for initial testing |

## Discovering Indicators and Line Names

Do **not** rely on a hardcoded list of indicators. The platform's indicator catalog evolves and may include specialized indicators not covered by any static reference.

**To discover all available indicators:**
```bash
riskmanaged indicators list-types
```

**To get the exact parameters and output line names for a specific indicator:**
```bash
riskmanaged indicators schema <IndicatorType>
```

The `schema` command returns the `lines` array — these are the **exact** output line names you must use in signal and bias rule conditions. Always run `schema` before adding an indicator or writing conditions.

> **Remember**: The full line reference is `{indicator_name}.{line}`. With the default name that is just the type — `RSI.rsi`. With a custom name it is that name — `fast_rsi.rsi`.

## Condition Format Quick Reference

**Compare indicator to fixed value:**
```json
{"trigger_line": "RSI.rsi", "trigger": "crossover", "threshold_value": 30}
```

**Compare two indicator lines:**
```json
{"trigger_line": "MACD.macd", "trigger": "crossover", "threshold_line": "MACD.signal"}
```

**Available triggers:** `crossover`, `crossunder`, `gt`, `ge`, `lt`, `le`, `eq`

## Risk Management Quick Reference

**Stop Loss Types:**
```json
// Simple
{"sl_type": "StopLossSimple", "stoploss_pct": -0.03}

// Trailing (recommended)
{"sl_type": "StopLossTrailing", "trailing_pct": 0.025}

// ATR-based
{"sl_type": "StopLossAtr", "atr_multiplier": 2.0, "atr_line": "ATR.atr_sma"}
```

**Take Profit:**
```json
{
  "tp_type": "TakeProfitSpread",
  "order_spread": [
    {"profit_target": 0.03},
    {"profit_target": 0.06},
    {"profit_target": 0.10}
  ]
}
```

---

## Scheduling as a Cron

This workflow is designed to run autonomously on a schedule. Below are setup instructions for the two supported agent runtimes.

### OpenClaw

OpenClaw supports cron-style scheduled tasks via files in `~/.openclaw/crons/`.

**1. Create the cron file:**

```bash
mkdir -p ~/.openclaw/crons
cp /path/to/cron.md ~/.openclaw/crons/strategy_research.md
```

**2. Add a schedule header** to the top of the copied file:

```markdown
---
schedule: "0 6 * * *"   # Runs daily at 06:00 UTC
skills:
  - riskmanaged-mcp
  - web-search-plus
---
```

**3. Ensure required environment variables are set** in OpenClaw's skill configuration:

| Variable | Where to Set | Value |
|----------|-------------|-------|
| `RISKMANAGED_TOKEN` | OpenClaw Settings → Skills → Environment Variables | Your API token from [riskmanaged.io/profile](https://riskmanaged.io/profile) |
| `RISKMANAGED_URL` | OpenClaw Settings → Skills → Environment Variables | `https://agent.riskmanaged.io` |

**4. Verify the cron is registered:**

Ask OpenClaw: `"What crons do I have scheduled?"` — it should list `strategy_research.md`.

The agent will execute this workflow end-to-end on each scheduled run, saving learnings to memory so subsequent runs build on prior findings.

### Hermes

Hermes supports scheduled tasks via the `crons` key in `~/.hermes/config.yaml`.

**1. Add the cron entry to your Hermes config:**

```yaml
crons:
  strategy_research:
    schedule: "0 6 * * *"   # Daily at 06:00 UTC
    prompt_file: /path/to/cron.md
    skills:
      - riskmanaged-mcp
      - web-search-plus
    env:
      RISKMANAGED_TOKEN: "YOUR_TOKEN"
      RISKMANAGED_URL: "https://agent.riskmanaged.io"
```

**2. Reload Hermes** to pick up the new cron:

```
/reload-config
```

**3. Verify** by asking: `"What scheduled tasks are running?"`

### Recommended Schedules

| Schedule | Cron Expression | Use Case |
|----------|----------------|----------|
| Daily (recommended) | `0 6 * * *` | Steady research cadence, one strategy per day |
| Twice daily | `0 6,18 * * *` | More aggressive exploration |
| Weekly | `0 6 * * 1` | Conservative, one deep research per week |

### Notes

- Each run costs **10 tokens** for the grid search. Ensure your account has sufficient balance or a daily free run available.
- The workflow is self-contained — it handles authentication, research, building, optimization, and learning compilation in a single execution.
- Learnings persist across runs via the agent's memory system, so each run becomes progressively more informed.
- If a run fails (e.g., insufficient tokens), it will abort gracefully with a clear message. The next scheduled run will attempt fresh research.
