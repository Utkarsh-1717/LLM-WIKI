---
title: session-continuous-returns
type: concept
tags:
  - "concept"
  - "quant"
  - "methodology"
topics: [quant, returns, intraday, timeseries, methodology]
created: 2026-06-02
updated: 2026-06-02
status: evergreen
---

# Session-Continuous Returns

A return series is **session-continuous** when it contains only genuine intraday returns — no overnight gaps, no weekend gaps, no holiday gaps. This is the correct input for any intraday correlation or mean-reversion analysis.

## Why This Matters

When computing `ln(P_t / P_{t-1})` naively on 1-min data, the first bar of each trading day produces an **overnight return**: `ln(today_09:15_open / yesterday_15:29_close)`. This is not a 1-minute return — it spans 17.75 hours (or 64.5 hours over weekends).

**The contamination problem:**
- Overnight returns have 5–10× the variance of genuine intraday 1-min returns
- Pairs that are highly correlated intraday may gap in opposite directions overnight (e.g., one stock has news, the other doesn't)
- Including overnight returns in correlation calculations adds noise that makes intraday signal detection harder and less accurate

## Correct Implementation (NSE)

NSE trading hours: **09:15 to 15:29 IST** (375 bars/day, last bar opens at 15:29)

### Step 1 — Filter to Market Hours
```python
import datetime
MARKET_OPEN  = datetime.time(9, 15)
MARKET_CLOSE = datetime.time(15, 29)

df['dt'] = pd.to_datetime(df['timestamp'], unit='s', utc=True).dt.tz_convert('Asia/Kolkata')
df_trading = df[(df['dt'].dt.time >= MARKET_OPEN) & (df['dt'].dt.time <= MARKET_CLOSE)]
```

### Step 2 — Compute Log-Returns
```python
log_returns_raw = np.log(price_matrix / price_matrix.shift(1))
```

### Step 3 — Null Session-Open Bars (CRITICAL)
```python
# The 09:15 bar's return = ln(today / yesterday_close) = overnight return
# It must be removed even after the market-hours filter
session_open_mask = (price_matrix.index.time == MARKET_OPEN)
log_returns_raw[session_open_mask] = np.nan
log_returns = log_returns_raw.dropna(how='any')
```

## Key Numbers (NSE 1-min)

| Item | Value |
|---|---|
| Bars per trading day | 375 (09:15 through 15:29) |
| Genuine intraday returns per day | 374 (375 bars − 1 session-open drop) |
| Over 120 trading days | ~44,880 clean returns per symbol |
| Actual achieved (with alignment) | 39,220 (104 trading days of common overlap) |

## What Gets Dropped

| Row type | Why dropped |
|---|---|
| Pre-09:15 timestamps | Not market hours |
| Post-15:29 timestamps | Not market hours |
| 09:15 bar return | Overnight gap return — not intraday |
| First row of shift() | Always NaN after log-return computation |

## Common Mistake

> "Just filter to market hours and you're done."

**Wrong.** Filtering to market hours removes the price rows for non-trading periods, but the log-return at the very first bar of each session (`09:15`) is still computed as `ln(P_09:15 / P_yesterday_15:29)` — an overnight return. You must explicitly null these bars after computing returns.

## Applications

- [[pearson-correlation-screening]] — uses session-continuous returns as input
- [[pairs-trading-pipeline]] — Stage 1 and all downstream stages require this
- [[log-return-computation]] — the formula applied to the filtered series

## Connections
- [[session-2026-06-02b]]
- [[index]]
- [[log-return-computation]]
- [[pearson-correlation-screening]]
- [[pairs-trading-pipeline]]
- [[timeseries-alignment]]
- [[master-data-1min-dataset]]

- [[fee-drag-and-microstructure-noise]]