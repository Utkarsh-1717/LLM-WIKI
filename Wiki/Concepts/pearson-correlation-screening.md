---
title: pearson-correlation-screening
type: concept
tags:
  - "concept"
  - "quant"
  - "methodology"
  - "pairs-trading"
topics: [quant, statistics, pairs-trading, correlation, screening]
created: 2026-06-02
updated: 2026-06-02
status: evergreen
---

# Pearson Correlation Screening (Pairs Trading Stage 1)

Stage 1 of the [[pairs-trading-pipeline]]. Computes pairwise Pearson correlation of log-returns across all equities in a universe to identify candidate pairs for further testing.

## Formula

$$\rho_{A,B} = \frac{\sum_t (r_t^A - \bar{r}^A)(r_t^B - \bar{r}^B)}{\sqrt{\sum_t (r_t^A - \bar{r}^A)^2 \cdot \sum_t (r_t^B - \bar{r}^B)^2}}$$

Where `r_t^A`, `r_t^B` are the [[log-return-computation|log-returns]] of symbols A and B at time `t`.

## Statistical Significance Test

With `n` aligned observations, test H₀: ρ = 0 using:

$$t = \rho \cdot \sqrt{\frac{n - 2}{1 - \rho^2}} \sim t_{n-2}$$

Two-tailed p-value computed from the t-distribution. Filter: **p < 0.05**.

With n = 39,220 (as in [[pairs-stage1-pearson]]), any |ρ| > 0.01 is statistically significant. The p-value filter mainly guards against pairs with very low n_obs.

## Key Properties

| Property | Description |
|---|---|
| Range | −1 to +1 |
| Scale-invariant | ρ(k·r_A, r_B) = ρ(r_A, r_B) — multiplying by a constant changes nothing |
| Symmetric | ρ(A, B) = ρ(B, A) — only compute upper triangle of the matrix |
| Measures linear association | Does NOT detect nonlinear co-movement |

## Why Pearson ρ on Log-Returns (Not Raw Prices)

See [[log-return-computation]] for the full rationale. In brief: raw prices are non-stationary. High ρ on raw prices is almost always **spurious co-trending**, not genuine co-movement of returns.

## Minimum Observation Threshold

Require **n ≥ 5,000 aligned observations** per pair. With ~39,000 intraday bars available (see [[session-continuous-returns]]), 5,000 bars ≈ 13 trading days — a conservative minimum. Pairs below this threshold are excluded from output.

## Implementation Pattern (Kaggle)

```python
# GPU path (try first)
try:
    import cudf
    corr_df = cudf.DataFrame(log_returns).corr().to_pandas()
except Exception:          # catches AttributeError, MemoryError, ImportError
    corr_df = log_returns.corr(method='pearson')

# Extract upper triangle pairs with t-stat and p-value
from scipy.stats import t as t_dist
import numpy as np

rows = []
syms = corr_df.columns.tolist()
n    = len(log_returns)
for i in range(len(syms)):
    for j in range(i+1, len(syms)):
        rho   = float(np.clip(corr_df.iloc[i,j], -0.999999, 0.999999))
        t_val = rho * np.sqrt((n-2) / (1 - rho**2))
        p_val = 2.0 * t_dist.sf(abs(t_val), df=n-2)
        rows.append((syms[i], syms[j], rho, t_val, p_val, n))
```

## Critical Warning: Correlation ≠ Cointegration

> High Pearson ρ is **necessary but NOT sufficient** for a tradeable pairs trade.

Two stocks can be highly correlated over a period while their spread (P_A − β·P_B) is non-stationary (trending, not mean-reverting). Stage 1 is a fast pre-screen only. **Stage 2 (cointegration testing) is mandatory** before any live trading.

- Correlation: do the returns move together? (Stage 1)
- Cointegration: is the price spread mean-reverting? (Stage 2, Engle-Granger / Johansen)

## NSE 500 Results (2026-06-02)

See [[pairs-stage1-pearson]] for full output.

| Metric | Value |
|---|---|
| Total pairs screened | 124,750 |
| Valid pairs (p<0.05, n≥5000) | 124,201 |
| n_obs per pair | 39,220 |
| Top pair | PFC / RECLTD — ρ = 0.6702 |
| #2 | INFY / TCS — ρ = 0.6596 |
| Top-500 cutoff | ρ = 0.3726 |

## Connections
- [[session-2026-06-02b]]
- [[index]]
- [[log-return-computation]]
- [[session-continuous-returns]]
- [[timeseries-alignment]]
- [[pairs-trading-pipeline]]
- [[pairs-stage1-pearson]]
- [[kaggle-compute]]
- [[master-data-1min-dataset]]
