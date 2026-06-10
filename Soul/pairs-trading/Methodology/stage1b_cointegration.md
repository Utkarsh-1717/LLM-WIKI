# Stage 1B — Engle-Granger Cointegration Screening
**Status**: ✅ COMPLETE (500 pairs validated — `pairs-stage1b-cointegration-v1`)  
**Updated**: 2026-06-10  
**Kaggle Kernel**: `utkarshpatelthefirst/pairs-stage1b-cointegration-v1`

---

## 1. Objective

After Stage 1 (Pearson) identifies 500 correlated pairs, Stage 1B applies the **Engle-Granger cointegration test** to separate pairs that are *structurally* mean-reverting from those that are merely correlated by chance or over a finite window.

A pair that passes Pearson screening but fails Engle-Granger will produce a spread that drifts forever — no true mean reversion exists. Trading such pairs bleeds capital to friction on directional losses.

---

## 2. The Engle-Granger Test

The Engle-Granger two-step test runs an **Augmented Dickey-Fuller (ADF)** unit root test on the OLS regression residuals. If the residual (spread) is stationary (I(0)), the pair is cointegrated.

$$y_t = \alpha + \beta x_t + \varepsilon_t$$
$$\text{ADF}(\varepsilon_t): H_0 = \text{unit root (non-stationary)}$$

Rejection of H₀ at `p < 0.05` → spread is stationary → pair is cointegrated.

---

## 3. Why Intraday 1-Minute Spread Must Be Used

Our pairs have half-lives of **642–3,400 minutes (2–9 days)**. Testing on Daily Close data:
- Requires 1+ year of data to see enough cycles
- Tests the wrong timeframe (daily vs intraday execution)
- Cannot distinguish 2-day intraday cycles from 2-day daily cycles

We test on the **1-minute intraday spread** to match our execution timeframe exactly.

---

## 4. Critical: Spread Continuity for Valid ADF Test

The ADF test mathematically requires a **continuous, unbroken time series**. Three spread generation methods were tested:

### 4.1 Kalman Filter Residuals — INVALID
The Kalman filter updates beta every minute *and* is designed to force the innovation toward zero. The resulting residual is always near-zero by construction. ADF will declare this stationary whether or not the pair has any real structural relationship.
- **Result**: 500/500 pairs pass at p < 0.05 → entirely meaningless

### 4.2 EOD-Updated OLS Residuals — INVALID
Beta is recalculated once at day-end and applied to next day's 1-minute data. At 09:15 every morning, a hard jump occurs as the new beta is applied to the overnight gap price. ADF interprets these daily jumps as structural breaks and rejects all pairs.
- **Result**: Only 9/500 pairs pass → all 9 are net-losers in backtest

### 4.3 Continuous Vectorized Rolling OLS — ✅ VALID
Beta and alpha are updated minute-by-minute using 7,500-bar rolling OLS. The spread changes smoothly with no discontinuities. ADF correctly identifies structurally mean-reverting pairs.
- **Result**: 358/500 pairs pass → 185/358 profitable, **net portfolio +₹54,937**

---

## 5. The Vectorized Implementation

Computing 7,500-bar rolling OLS at every minute for 500 pairs without loops (Pandas vectorized):

```python
ROLLING_WINDOW = 7500  # 20 trading days × 375 bars/day

roll_cov = ya.rolling(ROLLING_WINDOW).cov(yb)   # E[(ya - ȳ)(yb - ȳb)]
roll_var = yb.rolling(ROLLING_WINDOW).var()      # E[(yb - ȳb)²]
beta     = roll_cov / roll_var                   # rolling OLS beta
alpha    = ya.rolling(ROLLING_WINDOW).mean() - beta * yb.rolling(ROLLING_WINDOW).mean()

spread   = ya - (alpha + beta * yb)             # continuous smooth spread

# Engle-Granger ADF test
from statsmodels.tsa.stattools import adfuller
adf_stat, p_val = adfuller(spread.dropna(), maxlag=1)
# p_val < 0.05 → cointegrated → include in production universe
```

---

## 6. Results Summary

| Filter | Pairs | Net PnL | Prof. Pairs | PnL/Trade |
|---|---|---|---|---|
| None (all 500) | 500 | −₹4,09,911 | 228 | −₹40.33 |
| ADF p < 0.05 | **358** | **+₹54,937** | **185** | +₹7.70 |

### Top 10 Most Cointegrated Pairs

| Pair | Sector | ADF p-val | PnL |
|---|---|---|---|
| IRCON–RITES | Railways | ~0 | +₹5,664 |
| ACC–AMBUJACEM | Cement | ~0 | +₹3,479 |
| RAILTEL–RITES | Railways | ~0 | +₹2,648 |
| BEML–IRCON | Railways/HvyEng | 1e-6 | +₹16,903 |
| DLF–PRESTIGE | Real Estate | 3e-6 | +₹5,279 |
| KEI–POLYCAB | Cables/Wires | 4e-6 | +₹8,757 |
| JBCHEPHARM–TORNTPHARM | Pharma | 8e-6 | −₹402 |
| IOB–MAHABANK | PSU Banks | 2.9e-5 | +₹2,454 |
| RITES–RVNL | Railways | 3.2e-5 | −₹1,964 |
| IRFC–RITES | Railways | 4.9e-5 | +₹846 |

---

## 7. Code Reference

| Script | Purpose |
|---|---|
| `Soul/pairs-trading/Code/build_stage1b_cointegration_nb.py` | EOD OLS + ADF (diagnostic — proved invalid method) |
| `Soul/pairs-trading/Code/build_continuous_ols_pipeline_nb.py` | **Continuous OLS + ADF + Backtest (production method)** |

---

## Connections

- [[production-logic]]
- [[stage1-pearson-screening]]
- [[stage3-execution-engine]]
- [[continuous-ols-execution]]
- [[QC-decisions-pairs-trading]]
- [[pairs-trading-strategy]]
- [[kaggle-notebook-run]]
