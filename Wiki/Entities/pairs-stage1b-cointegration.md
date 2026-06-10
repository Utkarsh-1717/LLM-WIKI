# Stage 1B — Cointegration Screening
**Type**: Entity  
**Domain**: Quantitative Finance / Statistical Arbitrage  
**Status**: ✅ COMPLETE — 500 pairs validated  
**Updated**: 2026-06-10  
**Kaggle Kernel**: `utkarshpatelthefirst/pairs-continuous-ols-pipeline-v1`

---

## What It Is

Stage 1B applies the **Engle-Granger cointegration test** (Augmented Dickey-Fuller on OLS residuals) to filter truly mean-reverting pairs from the Top 500 Pearson-correlated pairs. Only pairs where the continuous OLS spread is stationary (ADF p < 0.05) are admitted to the production portfolio.

---

## Why This Stage Matters

Without Stage 1B: 500 pairs → Net PnL **−₹4,09,911**  
With Stage 1B (ADF p < 0.05): 358 pairs → Net PnL **+₹54,937**

The cointegration filter rejects 142 pairs that have no structural mean-reversion, saving capital from being destroyed on directional losses.

---

## Valid Spread for ADF Test

| Spread Method | ADF Valid? | Reason |
|---|---|---|
| Kalman residuals | ❌ No | Filter forces stationarity by design |
| EOD OLS (daily jump) | ❌ No | Daily discontinuities break the test |
| Continuous Rolling OLS | ✅ Yes | Smooth, objective, minute-by-minute |

---

## Threshold

`ADF p-value < 0.05` → structurally cointegrated → include in portfolio

---

## Top 5 Most Cointegrated Pairs

| Pair | Sector | ADF p-val |
|---|---|---|
| IRCON–RITES | Railways | ~0 |
| ACC–AMBUJACEM | Cement | ~0 |
| RAILTEL–RITES | Railways | ~0 |
| BEML–IRCON | Railways | 1e-6 |
| DLF–PRESTIGE | Real Estate | 3e-6 |

---

## Connections

- [[pairs-trading-strategy]]
- [[continuous-ols-execution]]
- [[stage1-pearson-screening]]
- [[stage3-execution-engine]]
- [[production-logic]]
- [[kaggle-notebook-run]]
