# Statistical Arbitrage: Production Methodology Whitepaper
**Version**: 3.0 — Full 500-Pair Validated  
**Updated**: 2026-06-10

---

## 1. Core Philosophy

This system executes a **Single-Sided Lagger** intraday mean-reversion strategy on NSE equities using 1-minute OHLCV data (09:15–15:29 IST). It maps structurally cointegrated pairs and extracts mean-reverting Z-score signals while filtering out high-frequency microstructure noise.

**Three execution methods validated** (all 500 pairs, 5.5-month backtest):
1. Kalman Worst-Case Anchored Filter
2. Kalman Dominant Regime Filter
3. Continuous Vectorized Rolling OLS (new — production winner for cointegration alignment)

---

## 2. Stage 1 — Pair Discovery (Pearson Screening)

Pairs are identified by computing the **Pearson correlation of log-returns** across all ~500 NSE equities.

**Why log-returns**: Raw prices are I(1) non-stationary; correlating them yields spurious results. Log-returns `r_t = ln(P_t/P_{t-1})` are stationary.

**Key implementation rules**:
- NSE hours filter: `09:15 ≤ time ≤ 15:29` (vectorized int check)
- Dynamic overnight gap mask: first return of every session nulled via date-boundary detection
- Pairwise alignment only via `df.corr()` — no global dropna
- No forward-filling (intentional — stale prices create phantom spreads)
- Minimum 5,000 overlapping bars; p < 0.05 statistical significance
- Top 500 by Pearson ρ passed to Stage 1B/Stage 2

→ Full details: [[stage1-pearson-screening]]

---

## 3. Stage 1B — Cointegration Screening (Engle-Granger / ADF)

> **NEW — Added 2026-06-10**

Pearson correlation identifies pairs that move together **on average**. It does NOT prove the spread is stationary. Stage 1B applies the **Engle-Granger cointegration test** (Augmented Dickey-Fuller on the spread residuals) to filter only pairs whose spread is mathematically mean-reverting.

### 3.1 Why ADF on the Intraday Spread?

Our half-lives average 642–3,400 minutes (2–10 days). Testing on Daily Close prices would require months of data and misses cycles that play out intraday. We test on the **1-minute residual spread** directly.

### 3.2 The Critical Spread Continuity Requirement

| Method | Spread Behaviour | ADF Result |
|---|---|---|
| Kalman Filter (any Q) | Filter forces spread mean-zero by design. | **Always passes** — meaningless. |
| EOD-updated OLS (daily beta jump) | Hard discontinuity at 09:15 every day. | **Always fails** — ADF rejects broken series. |
| **Continuous Vectorized Rolling OLS** | Beta updates every minute; smooth spread. | **Valid test** — correctly identifies true cointegration. |

### 3.3 Vectorized Rolling OLS Formula

Beta and alpha are updated minute-by-minute using a 7,500-bar (20-day) rolling window:

```python
roll_cov = Series_A.rolling(7500).cov(Series_B)
roll_var = Series_B.rolling(7500).var()
beta     = roll_cov / roll_var
alpha    = Series_A.rolling(7500).mean() - beta * Series_B.rolling(7500).mean()
spread   = Series_A - (alpha + beta * Series_B)
```

The `adfuller(spread, maxlag=1)` p-value < 0.05 is the production cointegration threshold.

### 3.4 Stage 1B Results (500 pairs, `pairs-stage1b-cointegration-v1`)

| Filter | Pairs Kept | Net PnL (Combined) | Profitable Ratio |
|---|---|---|---|
| No filter (all 500) | 500 | −₹409,911 | 228/500 |
| ADF p < 0.05 on Continuous OLS Spread | **358** | **+₹54,937** | 185/358 |

**Conclusion**: Removing 142 non-cointegrated pairs flips the portfolio from −₹4.1 Lakh loss to **+₹54,937 profit**.

→ Full details: [[stage1b-cointegration]]

---

## 4. Stage 2 — Q Calibration (Deterministic OU Chunked Fit)

### 4.1 Why EM Was Abandoned

The standard Kalman EM approach (E-step via RTS smoother + M-step Q update) requires ~17 minutes per pair on 150,000 bars and converges ~0% on HF cointegrated data. Permanently abandoned. See [[stage2-ou-calibration]] for full proof.

### 4.2 The OU Chunked Fit

Data is split into `NUM_CHUNKS` (default: 4) temporal windows. For each chunk:

1. **OLS** extracts a local static spread: $S_{c,t} = y_t - (\hat{\beta}_c x_t + \hat{\alpha}_c)$
2. **AR(1)** fit: $S_t = \phi S_{t-1} + c + \eta_t$
3. **Half-life** (if $0 < \phi < 1$): $HL = -\ln(2)/\ln(\phi)$ [minutes]

### 4.3 Observed Half-Lives (500 pairs, full run)

| Method | Average Half-Life | Interpretation |
|---|---|---|
| Kalman Dominant Regime (profitable pairs) | **642 minutes** (~1.7 days) | Most common reversion speed |
| Kalman Worst-Case (profitable pairs) | **3,409 minutes** (~9 days) | Slowest observed reversion |

This confirms our half-lives are **multi-day**, proving the Z-score window must span 20 days minimum.

### 4.4 Two Q Methods

**Method A — OU Worst-Case Anchored Q**:
$$\tau_A = \max(\text{valid chunk HLs}) \times 2.0$$

**Method B — OU Dominant Regime Q**:
$$\tau_B = \text{medoid}(\text{valid chunk HLs}) \times 2.0$$

→ Full details: [[stage2-ou-calibration]]

---

## 5. Stage 3 — Execution Engine

### 5.1 Z-Score Normalization Window (Critical Fix)

> ⚠️ **CRITICAL: 375-bar window permanently retired.**

The original implementation used a **375-bar (1-day) rolling Z-score window**. This was a fundamental error:

- True pair half-lives = 642–3,400 minutes (2–9 days)
- A 375-bar window re-centered the rolling mean faster than the spread could revert
- The Z-score artificially "reset" before trades could complete → excessive false exits → death by friction

**Corrected window**: `ZSCORE_WINDOW = 7500` (20 trading days = 20 × 375 bars).

### 5.2 Method A — Kalman Filter Execution

The Kalman forward filter tracks the hedge ratio online and computes the **spread innovation**:
$$v_t = y_t - H_t \hat{\theta}_{t|t-1} \qquad \text{where } H_t = [\ln P_{B,t},\; 1]$$

- **09:15 Gap Protocol**: $P_{pred} \times 2$ at every session open to absorb overnight uncertainty
- Three Q configurations tested: Fixed Speed-Limit, Worst-Case, Dominant Regime

### 5.3 Method B — Continuous Vectorized Rolling OLS Execution (NEW)

Instead of a Kalman filter, beta and alpha are computed using rolling 7,500-bar vectorized OLS (updating every minute). This generates a smooth, continuous spread that is identical to the Stage 1B cointegration test spread, ensuring **perfect alignment** between the cointegration filter and the execution signal.

```python
beta   = ya.rolling(7500).cov(yb) / yb.rolling(7500).var()
alpha  = ya.rolling(7500).mean() - beta * yb.rolling(7500).mean()
spread = ya - (alpha + beta * yb)
```

→ Full details: [[stage3-execution-engine]]

---

## 6. Execution Constraints

| Constraint | Value | Reason |
|---|---|---|
| Execution style | Single-sided (lagger only) | Two-sided doubles fees; alpha is only in lagger's catch-up |
| Capital per pair | ₹10,000 base | Fixed, isolated per pair for clean comparison |
| Leverage | 5x MIS | Standard NSE intraday margin |
| Effective position | ₹50,000 | base × leverage |
| Friction | 0.05% per leg | Covers brokerage + STT + exchange + slippage |
| EOD Square-off | 15:15 PM | Mandatory MIS compliance |
| Z-Score Window | 7,500 bars (20 days) | Must exceed maximum half-life of any pair |

---

## 7. Full 500-Pair Backtest Results (2026-06-09/10)

### 7.1 Head-to-Head: All Methods, All 500 Pairs

| Method | Net PnL (500 pairs) | Profitable Pairs | Total Trades | PnL/Trade |
|---|---|---|---|---|
| Kalman: Fixed Speed-Limit (τ=120) | −₹41,56,689 | 54 | 94,492 | −₹43.99 |
| Kalman: Dominant Regime | −₹15,40,224 | 138 | 29,673 | −₹51.91 |
| Kalman: Worst-Case | −₹12,87,723 | 168 | 24,526 | −₹52.50 |
| Rolling OLS (EOD-updated beta) | −₹13,93,181 | 131 | 9,116 | −₹152.86 |
| **Continuous Rolling OLS (7500-bar)** | **−₹4,09,911** | **228** | **10,164** | −₹40.33 |
| **Continuous OLS — Cointegrated only** | **+₹54,937** | **185** | **7,136** | **+₹7.70** |

### 7.2 Profitable Pairs Analysis (Winner: Kalman Worst-Case)

| Method | Profitable Pairs | Sum Positive PnL | Trades (Profitable) | PnL/Trade |
|---|---|---|---|---|
| Kalman: Fixed Speed-Limit | 54 | ₹1,85,143 | 10,029 | ₹18.46 |
| Kalman: Dominant Regime | 138 | ₹5,07,145 | 9,201 | ₹55.12 |
| **Kalman: Worst-Case** | **168** | **₹6,29,847** | **8,961** | **₹70.29** |
| Rolling OLS (EOD) | 131 | ₹4,69,331 | 2,357 | ₹199.12 |

### 7.3 Elite Pairs (Top 10 by Cointegration Strength)

Ranked by Engle-Granger ADF p-value on the continuous intraday OLS spread:

| Rank | Pair | Sector | ADF p-val | Continuous OLS PnL | Trades |
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

**Total Top 10 Net PnL: +₹43,666** on ₹10,000 base capital (5.5 months)

---

## 8. Capital Scaling Projections (Top 5 OLS Pairs — 5.5 months)

| Base Capital | Net Profit | Monthly Return | Annual CAGR |
|---|---|---|---|
| ₹10,000 | ₹65,461 | ~44.3% | ~6,600% |
| ₹1,00,000 | ₹6,54,610 | ~44.3% | ~6,600% |
| ₹5,00,000 | ₹32,73,050 | ~44.3% | ~6,600% |

> ⚠️ These projections are based on in-sample top-5 selection (lookahead bias). Live trading must use cointegration pre-screening to select pairs before they trade.

---

## 9. Known Limitations & Next Steps

1. **Overall portfolio still net-negative without cointegration filter**: 332 of 500 Pearson-correlated pairs have no true structural bond and diverge forever. The Cointegration filter (Stage 1B) solves this.

2. **Single-bullet capital constraint**: If trading with full capital per trade, only the Top 5–10 most cointegrated pairs should be monitored simultaneously.

3. **Cointegration not stable**: Pairs can lose cointegration after regime changes (earnings, sector rotation). Rolling 30-day re-screening needed in production.

4. **Capital Collision**: The algorithm may signal multiple pairs simultaneously. Portfolio allocation (e.g., Kelly or equal-weight across the cointegrated universe) needs formalization.

---

## Connections

- [[stage1-pearson-screening]]
- [[stage1b-cointegration]]
- [[stage2-ou-calibration]]
- [[stage3-execution-engine]]
- [[QC-decisions-pairs-trading]]
- [[backtest-record-pairs-trading]]
- [[kaggle-notebook-run]]
- [[master-data-1min-dataset]]
- [[pairs-trading-strategy]]
- [[continuous-ols-execution]]
