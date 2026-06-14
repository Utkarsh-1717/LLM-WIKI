---
title: Continuous OLS Execution Engine
tags:
- entity
topics:
- pairs-trading
- numba
- joblib
- kaggle
sources: []
source_count: 0
created: '2026-06-10'
updated: '2026-06-13'
---
# Continuous OLS Execution Engine
**Type**: Entity  
**Domain**: Quantitative Finance / Statistical Arbitrage  
**Status**: ✅ COMPLETE — 124,750 pairs massive scan capability  
**Updated**: 2026-06-13  
**Kaggle Kernel**: `utkarshpatelthefirst/pairs-continuous-ols-pipeline-v1`

---

## What It Is

The Continuous Vectorized Rolling OLS is an alternative execution engine to the Kalman Filter for pairs trading. Beta and alpha are updated every 1-minute bar using a 7,500-bar (20-day) rolling window computed entirely via Pandas vectorized operations (no Python loops). 

Due to the massive algorithmic scale of testing 124,750 combinations on Kaggle, the execution simulation itself is accelerated using the **Numba `@njit` JIT compiler** combined with **`joblib` 4-core multiprocessing**. 

---

## Core Formula

### 1. Vectorized Beta & Alpha
```python
ROLLING_WINDOW = 7500  # 20 trading days

beta  = ya.rolling(ROLLING_WINDOW).cov(yb) / yb.rolling(ROLLING_WINDOW).var()
alpha = ya.rolling(ROLLING_WINDOW).mean() - beta * yb.rolling(ROLLING_WINDOW).mean()
spread = ya - (alpha + beta * yb)
```

### 2. Numba JIT Backtest Loop
To simulate stateful logic (cash balance, tracking position size discrete integers, execution friction) instantly across thousands of pairs, the Python sequential `for t in range(...)` loop is compiled to C++ machine code using `@numba.njit`. 

Speed comparison for 1 single pair (40,000 bars):
- Python Loop: `94 ms`
- Numba `@njit` Loop: `9 ms` (10x faster)

### 3. "Lazy" ADF Cointegration Filter
Because `statsmodels.tsa.stattools.adfuller` is incredibly slow (~1.5 seconds per pair) and cannot be JIT compiled, we execute a "Lazy Filter". 
We run the 9ms Numba execution backtest on ALL 125,000 pairs FIRST. We then only trigger the heavy 1.5s ADF test on pairs that generate a mathematically positive PnL. This slashes Kaggle compute time from 52 hours down to ~1.5 hours.

### 4. Walk-Forward Predictive Parameter Extraction
As of Version 5 of the massive sweep, the Numba engine extracts deep physical structural characteristics of the spread in addition to the backtest results. These parameters are strictly independent (ex-ante) and will be used to construct a walk-forward ranking filter that does not rely on hindsight PnL.
Extracted metrics per pair include:
- **Physical Ex-Ante Metrics**: `spread_vol`, `mean_abs_dev`, `zero_crossings`, `half_life` (via OU auto-correlation), `kalman_q` (process variance).
- **Hindsight Derived Metrics**: `ols_gross_pnl`, `ols_net_pnl`, `gross_win_rate`, `net_win_rate`, `mean_rev_exits`, `eod_exits`, `avg_price_captured`, `avg_fee_drag`.

### 5. Exact Zerodha Equity MIS Fee Engine
Unlike generic percentage friction, the Numba engine mathematically computes the exact transaction cost to the literal cent for every single execution.
`Total_Fee = Brokerage (min(0.0003, 20)) + STT (0.00025 sell-only) + NSE Trans (0.0000325) + GST (18% on Brok+NSE) + SEBI + Stamp (buy-only)`.

---

## Key Properties

| Property | Value |
|---|---|
| Lookback window | 7,500 bars (20 trading days) |
| Update frequency | Every 1-minute bar |
| Spread type | Smooth, continuous — no daily jumps |
| Execution Engine | Numba `@njit` (C++ Compilation) |
| Parallelization | Joblib 4-core multiprocessing |
| ADF testing | Lazy (Only on Profitable Backtests) |
| Scan Capacity | 124,750 combinations (All NSE 500) |
| Kaggle runtime | ~1.5 to 2 hours (125,000 pairs) |

---

## Results

| Filter | Pairs | Net PnL | Profitable | PnL/Trade |
|---|---|---|---|---|
| None | 500 | −₹4,09,911 | 228/500 | −₹40.33 |
| ADF p < 0.05 | 358 | **+₹54,937** | 185/358 | +₹7.70 |

---

## Code Reference

`Soul/pairs-trading/Code/build_continuous_ols_pipeline_nb.py`

---

## Connections

- [[pairs-trading-strategy]]
- [[pairs-stage1b-cointegration]]
- [[stage3-execution-engine]]
- [[pairs-trading-strategy]]
- [[kaggle-notebook-run]]
- [[PM_125h_Kaggle_Timeout]]

- [[pairs-stage1b-cointegration]]
- [[backtest-record-pairs-trading]]
- [[session-2026-06-09]]
- [[QC-decisions-pairs-trading]]
- [[soul-production-compiler]]