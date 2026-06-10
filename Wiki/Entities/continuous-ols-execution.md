# Continuous OLS Execution Engine
**Type**: Entity  
**Domain**: Quantitative Finance / Statistical Arbitrage  
**Status**: ✅ COMPLETE — 500 pairs validated  
**Updated**: 2026-06-10  
**Kaggle Kernel**: `utkarshpatelthefirst/pairs-continuous-ols-pipeline-v1`

---

## What It Is

The Continuous Vectorized Rolling OLS is an alternative execution engine to the Kalman Filter for pairs trading. Beta and alpha are updated every 1-minute bar using a 7,500-bar (20-day) rolling window computed entirely via Pandas vectorized operations (no Python loops).

---

## Core Formula

```python
ROLLING_WINDOW = 7500  # 20 trading days

beta  = ya.rolling(ROLLING_WINDOW).cov(yb) / yb.rolling(ROLLING_WINDOW).var()
alpha = ya.rolling(ROLLING_WINDOW).mean() - beta * yb.rolling(ROLLING_WINDOW).mean()
spread = ya - (alpha + beta * yb)
```

---

## Key Properties

| Property | Value |
|---|---|
| Lookback window | 7,500 bars (20 trading days) |
| Update frequency | Every 1-minute bar |
| Spread type | Smooth, continuous — no daily jumps |
| ADF testable | **Yes** — unlike Kalman residuals |
| Kaggle runtime | ~14 minutes (500 pairs) |

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
- [[stage1b-cointegration]]
- [[stage3-execution-engine]]
- [[production-logic]]
- [[kaggle-notebook-run]]
