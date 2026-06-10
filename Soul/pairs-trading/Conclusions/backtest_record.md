# Backtest Record — Pairs Trading
**Updated**: 2026-06-10  
**Data**: NSE 1-min OHLCV | ~104 trading days (5.5 months) | 09:15–15:29 IST  
**Universe**: Top 500 pairs by Pearson ρ  
**Capital**: ₹10,000 base × 5x MIS = ₹50,000 per pair (fixed, not compounding)

---

## 1. All Methods Overview

| Method | Description |
|---|---|
| **Fixed Speed-Limit Q** (archived) | τ fixed at 120 min manually. No OU calibration. |
| **OU Worst-Case Anchored Q** | τ = max(chunk HLs) × 2.0. Sizes filter for slowest regime. |
| **OU Dominant Regime Q** | τ = medoid(chunk HLs) × 2.0. Sizes filter for most common regime. |
| **EOD-Updated OLS** | Beta/alpha computed daily at close; stationary intraday. |
| **Continuous Vectorized OLS** | Beta/alpha updated every 1-minute bar via 7500-bar rolling window. |

---

## 2. Z-Score Window Fix (Critical)

> ⚠️ **CORRECTED in full 500-pair run (2026-06-09)**

Original implementation used `ZSCORE_WINDOW = 375` (1 trading day). This caused the rolling mean to re-center faster than pairs could revert, generating premature false exits and massive friction drag.

**Measured half-lives**: 642 minutes (Dominant Regime) to 3,409 minutes (Worst-Case).  
**Required window**: ≥ max half-life × safety factor = 3,409 × 2 ≈ 7,000 bars → **rounded up to 7,500**.

All results below use `ZSCORE_WINDOW = 7500`.

---

## 3. Full 500-Pair Results (2026-06-09/10)

### 3.1 Net Portfolio PnL — All 500 Pairs

| Method | Net PnL | Trades | Profitable Pairs | PnL/Trade |
|---|---|---|---|---|
| Kalman: Fixed Speed-Limit (τ=120) | −₹41,56,689 | 94,492 | 54/500 | −₹43.99 |
| Kalman: Dominant Regime | −₹15,40,224 | 29,673 | 138/500 | −₹51.91 |
| Kalman: Worst-Case | −₹12,87,723 | 24,526 | 168/500 | −₹52.50 |
| OLS (EOD-updated beta) | −₹13,93,181 | 9,116 | 131/500 | −₹152.86 |
| **Continuous OLS (7500-bar)** | **−₹4,09,911** | **10,164** | **228/500** | −₹40.33 |

### 3.2 Profitable Pairs Only — Where the Alpha Lives

| Method | Profitable Pairs | Sum Positive PnL | Avg Trades/Pair | PnL/Trade |
|---|---|---|---|---|
| Kalman: Fixed Speed-Limit | 54 | ₹1,85,143 | 185.7 | ₹18.46 |
| Kalman: Dominant Regime | 138 | ₹5,07,145 | 66.7 | ₹55.12 |
| **Kalman: Worst-Case** | **168** | **₹6,29,847** | **53.3** | **₹70.29** |
| OLS (EOD-updated) | 131 | ₹4,69,331 | 18.0 | ₹199.12 |

### 3.3 Cointegration Filter Results (Continuous OLS only)

| Filter | Pairs | Net PnL | Profitable | PnL/Trade |
|---|---|---|---|---|
| No filter | 500 | −₹4,09,911 | 228/500 | −₹40.33 |
| **ADF p < 0.05** | **358** | **+₹54,937** | **185/358** | **+₹7.70** |

**Applying the Engle-Granger filter flips the portfolio from −₹4.1 Lakh to +₹54,937 profit.**

---

## 4. Half-Life Analysis (500 pairs)

| Method | Profitable Pairs Avg HL | All Pairs Avg HL |
|---|---|---|
| Kalman: Dominant Regime | 642.37 minutes | — |
| Kalman: Worst-Case | 3,409.77 minutes | — |

**Key insight**: True half-lives are 2–9 trading days, not 1 day. The 375-bar (1-day) Z-score window was catastrophically short.

---

## 5. Top 10 Pairs by Cointegration Strength

Ranked by Engle-Granger ADF p-value on continuous intraday OLS spread:

| Rank | Pair | Sector | ADF p-val | PnL | Trades |
|---|---|---|---|---|---|
| 1 | IRCON–RITES | Railways | ~0 | +₹5,664 | 23 |
| 2 | ACC–AMBUJACEM | Cement | ~0 | +₹3,479 | 27 |
| 3 | RAILTEL–RITES | Railways | ~0 | +₹2,648 | 27 |
| 4 | BEML–IRCON | Railways/HvyEng | 1e-6 | +₹16,903 | 25 |
| 5 | DLF–PRESTIGE | Real Estate | 3e-6 | +₹5,279 | 27 |
| 6 | KEI–POLYCAB | Cables/Wires | 4e-6 | +₹8,757 | 24 |
| 7 | JBCHEPHARM–TORNTPHARM | Pharma | 8e-6 | −₹402 | 35 |
| 8 | IOB–MAHABANK | PSU Banks | 2.9e-5 | +₹2,454 | 19 |
| 9 | RITES–RVNL | Railways | 3.2e-5 | −₹1,964 | 18 |
| 10 | IRFC–RITES | Railways | 4.9e-5 | +₹846 | 29 |

**Total Top 10 PnL: +₹43,666** over 5.5 months on ₹10,000 base capital.

---

## 6. Capital Scaling (Top 5 OLS Pairs — 5.5 months)

| Base Capital | Net Profit | Monthly Return | Annual CAGR |
|---|---|---|---|
| ₹10,000 | ₹65,461 | ~44% | ~6,600% |
| ₹1,00,000 | ₹6,54,610 | ~44% | ~6,600% |
| ₹5,00,000 | ₹32,73,050 | ~44% | ~6,600% |

> ⚠️ **Lookahead bias**: These projections use in-sample best-5 selection. Live returns require proper cointegration pre-screening.

---

## 7. Kaggle Kernels Used

| Kernel | Description | Status |
|---|---|---|
| `pairs-full-pipeline-v3` | Kalman FSL + WC + DR (500 pairs, 7500 Z-score) | ✅ COMPLETE |
| `pairs-ols-pipeline-v1` | EOD-updated OLS (500 pairs) | ✅ COMPLETE |
| `pairs-stage1b-cointegration-v1` | ADF test on Kalman/OLS residuals (diagnostic) | ✅ COMPLETE |
| `pairs-continuous-ols-pipeline-v1` | Continuous rolling OLS + ADF + backtest | ✅ COMPLETE |

---

## 8. Early 5-Pair Sketch Results (Archived)

Original experiments on Top 5 pairs only (with incorrect 375-bar Z-score window):

| Pair | FSL PnL | WC PnL | DR PnL | Winner |
|---|---|---|---|---|
| PFC-RECLTD | −₹2,862 | +₹5,114 | +₹2,224 | Worst-Case |
| BDL-MAZDOCK | −₹12,110 | −₹7,052 | −₹5,356 | Dominant Regime |
| GRSE-MAZDOCK | −₹2,673 | +₹17,874 | +₹15,550 | Worst-Case |
| BANKBARODA-CANBK | −₹6,153 | −₹10,001 | −₹11,229 | FSL |
| BPCL-HINDPETRO | −₹14,388 | −₹10,593 | −₹4,252 | Dominant Regime |

> These results are archived — the 375-bar Z-score window invalidates them. The 500-pair 7500-bar results supersede this table.

---

## Connections

- [[pairs-trading-strategy]]
- [[stage1b-cointegration]]
- [[stage2-ou-calibration]]
- [[stage3-execution-engine]]
- [[continuous-ols-execution]]
- [[production-logic]]
- [[QC-decisions-pairs-trading]]
- [[kaggle-notebook-run]]
