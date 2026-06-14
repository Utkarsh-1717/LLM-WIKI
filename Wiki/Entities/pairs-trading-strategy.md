---
title: Pairs Trading Strategy
tags:
- entity
topics:
- pairs-trading
sources: []
source_count: 0
created: '2026-06-10'
---
# Pairs Trading Strategy
**Type**: Entity  
**Domain**: Quantitative Finance / Statistical Arbitrage  
**Status**: ✅ Fully validated — 124,750 pairs (entire NSE 500 combinations matrix), 5.5 months, Lazy Cointegration filter produces profitable portfolio  
**Soul Location**: `Soul/pairs-trading/`  
**Updated**: 2026-06-10

---

## What It Is

An intraday mean-reversion strategy that trades the **lagging asset** in an NSE equity pair when their spread (Kalman-filtered or OLS-computed) deviates beyond ±2σ from its 20-day rolling mean. All positions are closed by 15:15 PM.

**Classification**: Relative-value directional strategy (single-sided, not market-neutral).

---

## Pipeline Summary

| Stage | Tool | Key Output |
|---|---|---|
| 1 — Pair Discovery | Pearson correlation of log-returns | `pairs_all.csv` (All 124,750 valid pairs) |
| **1B — Cointegration** | Lazy Engle-Granger ADF on profitable spread | `adf_pval` per profitable pair |
| 2 — Q Calibration | OU Chunked Fit (2 methods) | Q, P0 per pair per method |
| 3A — Kalman Execution | Kalman Filter + Z-score backtest | Net PnL (Worst-Case / DR) |
| **3B — Numba OLS Execution** | Continuous Vectorized Numba OLS | Net PnL, Trades, WinRate per pair |

---

## Three Execution Methods Validated

| Method | Net PnL (500 pairs) | Profitable Pairs | Trades | PnL/Trade |
|---|---|---|---|---|
| Kalman: Fixed Speed-Limit | −₹41,56,689 | 54 | 94,492 | −₹43.99 |
| Kalman: Dominant Regime | −₹15,40,224 | 138 | 29,673 | −₹51.91 |
| Kalman: Worst-Case | −₹12,87,723 | 168 | 24,526 | −₹52.50 |
| OLS (EOD-updated) | −₹13,93,181 | 131 | 9,116 | −₹152.86 |
| **Continuous OLS (7500-bar)** | −₹4,09,911 | 228 | 10,164 | −₹40.33 |
| **Continuous OLS + ADF filter** | **+₹54,937** | **185/358** | 7,136 | **+₹7.70** |

---

## Kalman vs OLS — Key Insight

| Property | Kalman Worst-Case | Continuous OLS |
|---|---|---|
| Beta update | Every minute (dynamic) | Every minute (vectorized) |
| PnL/trade (profitable pairs) | **₹70.29** | ₹7.70 (all cointegrated pairs) |
| Cointegration testable? | **No** (filter forces stationarity) | **Yes** (smooth spread, valid ADF) |
| Best use | Execution engine | Pair pre-screening + Execution |

---

## Elite Pairs (by Cointegration Strength)

Top pairs confirmed structurally cointegrated by intraday Engle-Granger ADF test:

| Pair | Sector | ADF p-val | Continuous OLS PnL |
|---|---|---|---|
| BEML–IRCON | Railways | 1e-6 | +₹16,903 |
| KEI–POLYCAB | Cables | 4e-6 | +₹8,757 |
| DLF–PRESTIGE | Real Estate | 3e-6 | +₹5,279 |
| IRCON–RITES | Railways | ~0 | +₹5,664 |
| ACC–AMBUJACEM | Cement | ~0 | +₹3,479 |

---

## Key Design Decisions

- No ffill — pairwise strict timestamp alignment only
- Single-sided lagger execution — two-sided doubles fees for zero extra alpha
- P_pred×2 at 09:15 open — NOT Q scaling
- OU Chunked Fit permanently replaces EM (EM: ~0% convergence, 17 min/run)
- Medoid for dominant regime — not mean, not median
- **Critical Z-Score Fix**: `ZSCORE_WINDOW = 7500` (20 days). The original 375-bar (1-day) window re-centered faster than the true 642–3400 minute half-lives, causing premature exits and friction death.
- **Cointegration Filter**: ADF must be run on Continuous OLS spread (not Kalman, not EOD OLS). Only method that gives valid, meaningful p-values.
- **Numba Execution**: Testing combinatorial spaces N > 10,000 mandates C++ compilation via Numba `@njit` and multiprocessing via `joblib`. Pure Python sequential backtests crash the Kaggle 12-hour timeout.
- **Lazy Evaluation**: The 1.5s/pair ADF test must be executed _after_ the 9ms/pair Numba backtest, applied only to profitable pairs. This drops Kaggle runtime from 52 hours down to 1.5 hours.

→ All decisions: [[QC-decisions-pairs-trading]], [[PM_125h_Kaggle_Timeout]]

---

## Connections

- [[pairs-stage1-pearson]]
- [[pairs-stage1b-cointegration]]
- [[pairs-stage2-kalman-ou]]
- [[stage3-execution-engine]]
- [[continuous-ols-execution]]
- [[pairs-trading-strategy]]
- [[QC-decisions-pairs-trading]]
- [[backtest-record-pairs-trading]]
- [[kaggle-notebook-run]]
- [[master-data-1min-dataset]]

- [[continuous-ols-execution]]
- [[pairs-stage1b-cointegration]]
- [[session-2026-06-09]]