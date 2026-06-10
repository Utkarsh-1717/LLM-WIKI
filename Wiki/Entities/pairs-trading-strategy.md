# Pairs Trading Strategy
**Type**: Entity  
**Domain**: Quantitative Finance / Statistical Arbitrage  
**Status**: ✅ Fully validated — 500 pairs, 5.5 months, cointegration filter produces profitable portfolio  
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
| 1 — Pair Discovery | Pearson correlation of log-returns | `pairs_top500.csv` (Top 500 by ρ) |
| **1B — Cointegration** | Engle-Granger ADF on continuous OLS spread | `adf_pval` per pair |
| 2 — Q Calibration | OU Chunked Fit (2 methods) | Q, P0 per pair per method |
| 3A — Kalman Execution | Kalman Filter + Z-score backtest | Net PnL (Worst-Case / DR) |
| **3B — OLS Execution** | Continuous Vectorized Rolling OLS | Net PnL, ADF p-val per pair |

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

→ All decisions: [[QC-decisions-pairs-trading]]

---

## Connections

- [[stage1-pearson-screening]]
- [[stage1b-cointegration]]
- [[stage2-ou-calibration]]
- [[stage3-execution-engine]]
- [[continuous-ols-execution]]
- [[production-logic]]
- [[QC-decisions-pairs-trading]]
- [[backtest-record-pairs-trading]]
- [[kaggle-notebook-run]]
- [[master-data-1min-dataset]]

- [[stage3b-continuous-ols]]
- [[pairs-stage1b-cointegration]]
- [[session-2026-06-09]]