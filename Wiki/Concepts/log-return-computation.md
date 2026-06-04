---
title: log-return-computation
type: concept
tags:
  - "concept"
  - "quant"
  - "methodology"
topics: [quant, returns, mathematics, methodology]
created: 2026-06-02
updated: 2026-06-02
status: evergreen
---

# Log-Return Computation

The standard method for computing returns in quantitative finance. Always preferred over simple (arithmetic) returns for statistical analysis of financial time series.

## Formula

$$r_t = \ln\left(\frac{P_t}{P_{t-1}}\right)$$

Where:
- `P_t` = closing price at time `t`
- `P_{t-1}` = closing price at previous bar
- `r_t` = log-return at time `t`

## Why Log-Returns, Not Raw Prices

| Property | Raw Prices | Log-Returns |
|---|---|---|
| Stationarity | Non-stationary (has trend, unit root) | Approximately stationary |
| Additivity | Not additive across time | Additive: `r_total = Σ r_t` |
| Symmetry | Asymmetric (+50% then −33% ≠ 0) | Symmetric: `+r` and `−r` cancel |
| Normality | Not normal | Approximately normal (CLT) |
| Spurious correlation | Very high (co-trending) | Genuine co-movement |

**For [[pearson-correlation-screening]]**: Never compute ρ on raw prices. Two stocks can appear 99% correlated on price purely because both trend upward over time — this is co-trending, not co-movement. Log-returns remove the trend component.

## Why Log-Returns, Not Simple Returns

Simple return: `r_t = (P_t − P_{t-1}) / P_{t-1}`

Log-return has two key advantages:
1. **No lower bound issue**: Simple returns are bounded at −100% (price can't go negative). Log-returns are unbounded, easier to model with normal distributions.
2. **Time additivity**: Log-return over N periods = sum of N 1-period log-returns exactly. Simple returns require compounding.

## Why No Multiplier / Scaling

A common error is applying a price multiplier before computing returns to "avoid rounding issues with decimal places". This is incorrect because:

1. `ln(P_t / P_{t-1})` is a **ratio** — inherently free from absolute magnitude or decimal-place bias
2. **Pearson correlation is scale-invariant**: `ρ(k·r_A, r_B) = ρ(r_A, r_B)` for any constant `k`
3. Multiplying returns adds complexity without improving precision

## Stationarity Note

Log-returns are **approximately** stationary for most equity return series. They are not perfectly stationary — volatility clustering (ARCH effects) and fat tails are common. For Stage 1 correlation screening this is acceptable. For Stage 3 spread modelling, stationarity of the **spread** (not individual returns) is what matters.

## Implementation

```python
import numpy as np
import pandas as pd

# price_matrix: DataFrame with timestamps as index, symbols as columns
# All prices must be positive and the series must be session-continuous
# See: [[session-continuous-returns]]

log_returns_raw = np.log(price_matrix / price_matrix.shift(1))

# Null session-open bars (overnight returns) before dropping NaN
session_open_mask = (price_matrix.index.time == datetime.time(9, 15))
log_returns_raw[session_open_mask] = np.nan
log_returns = log_returns_raw.dropna(how='any')

# Sanity checks
assert log_returns.isnull().sum().sum() == 0
assert not np.isinf(log_returns.values).any()
assert (log_returns.abs() < 1.0).all().all()  # |return| >= 100% → data error
```

## Connections
- [[session-2026-06-02b]]
- [[index]]
- [[session-continuous-returns]]
- [[pearson-correlation-screening]]
- [[pairs-trading-pipeline]]
- [[timeseries-alignment]]
- [[master-data-1min-dataset]]
