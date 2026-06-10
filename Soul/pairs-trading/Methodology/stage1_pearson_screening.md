# Stage 1 — Pearson Correlation Screening
**Status**: ✅ COMPLETE (Sketch 1 → validated in Sketch 3)  
**Source**: `Archive/Pairs_Trading_Sketches/final sketch-1&2/sketch - 1/stage-1-pairs-trading-pearson-correlation.md`  
**Bugs Corrected**: Global dropna → pairwise alignment; static 09:15 mask → dynamic date-boundary mask

---

## 1. Objective

Identify the most robustly co-moving NSE equity pairs using 1-minute OHLCV data. Rank ~124,750 candidate pairs (N≈500 symbols) by the **Pearson correlation of log-returns** and export the top 500 for downstream cointegration testing.

**Outputs**:
- `pairs_all.csv` — all valid pairs (~124,201 rows)
- `pairs_top500.csv` — top 500 by correlation

---

## 2. Why Log-Returns (Not Raw Prices)

Raw close prices are **I(1)** processes — non-stationary random walks. Computing Pearson correlation on two random walks yields spurious correlation caused by shared trends (co-trending), not genuine co-movement of returns.

Log-returns `r_t = ln(P_t / P_{t-1})` are approximately **I(0)** — stationary. Pearson correlation on `r_t` measures genuine intraday co-movement.

Additionally, Pearson ρ is **scale-invariant** — multiplying returns by any constant leaves ρ unchanged. No scaling or normalization of prices is needed.

---

## 3. Verified Data Cleansing Rules

### 3.1 NSE Hours Filter
Only bars where `09:15 ≤ time ≤ 15:29 IST` are retained. All pre-market, post-market, and non-trading bars are unconditionally dropped.

**Implementation** (vectorized — no Python datetime objects):
```python
time_int = df['dt'].dt.hour * 100 + df['dt'].dt.minute
df_trading = df[(time_int >= 915) & (time_int <= 1529)]
```

### 3.2 No Forward-Filling (Intentional Design)
If Asset A has no trade at minute `t`, its price is left as `NaN`. Forward-filling to minute `t` from `t-1` while Asset B has a fresh price at `t` creates a **phantom spread movement** — a fake divergence that would trigger a false trading signal.

**Rule**: Never `ffill` before computing pairwise correlations. Missing data = dropped pairwise observation.

### 3.3 Overnight Gap Annihilation (Dynamic)
The return `r_t = ln(P_t / P_{t-1})` at the first bar of a trading session bridges against the **previous day's close** — this is an overnight gap return, not an intraday return. Overnight gaps can have 5–10× the variance of genuine 1-minute intraday returns and must be nulled before correlation.

**Correct method** — detect the first return of every session via date-boundary crossing:
```python
dates = df_trading['dt'].dt.date
session_open_mask = dates != dates.shift(1)  # True at first bar of each day
log_returns[session_open_mask] = np.nan
```

**Why NOT static `time == 09:15`**: If a stock's first bar of the day is at 09:16 (e.g., illiquid open), the 09:16 return bridges against yesterday's close. The static mask misses this entirely.

### 3.4 Pairwise Alignment (NOT Global Dropna)

**The Bug (Sketch 1 & 2)**: `price_matrix.dropna(how='any', axis=0)` — if one illiquid stock out of 500 missed a 1-minute bar, that entire minute was deleted for all 499 other stocks. With 500 symbols and real-world gaps, this caused catastrophic, unnecessary data loss.

**The Fix**: Leave `NaN`s in place. When computing `df.corr()`, pandas computes correlation **pairwise by default** — it isolates Asset A and Asset B, drops rows where either is `NaN`, and computes ρ on their specific overlapping timestamps only. No global drop needed.

### 3.5 Minimum Observations Filter
Pairs with fewer than **5,000** overlapping valid 1-minute bars are excluded. With ~120 trading days × 374 intraday returns/day ≈ 44,880 total bars, 5,000 bars represents ~11 trading days of overlap — a conservative threshold to prevent small-sample statistical noise.

### 3.6 Statistical Significance Test
For each pair, compute the t-statistic:

$$t = \rho \sqrt{\frac{n - 2}{1 - \rho^2}}$$

Under H₀: ρ = 0, this follows a t-distribution with (n−2) degrees of freedom. Filter: **p < 0.05** (two-tailed).

In practice with n > 5,000, any |ρ| > 0.03 will be significant — this filter mainly removes pairs with very small overlap.

---

## 4. Full Implementation

```python
import sqlite3, gc
import pandas as pd
import numpy as np
from scipy.stats import t as t_dist

# --- Step 1: Load ---
con = sqlite3.connect(DB_PATH)
df = pd.read_sql(
    "SELECT symbol, timestamp, close FROM ohlcv_1min ORDER BY timestamp", con
)
con.close()
df['dt'] = pd.to_datetime(df['timestamp'], unit='s', utc=True).dt.tz_convert('Asia/Kolkata')

# --- Step 2: NSE hours filter (vectorized) ---
time_int = df['dt'].dt.hour * 100 + df['dt'].dt.minute
df_trading = df[(time_int >= 915) & (time_int <= 1529)].copy()
del df; gc.collect()

# --- Step 3: Pivot to price matrix ---
price_matrix = df_trading.pivot(index='dt', columns='symbol', values='close')
del df_trading; gc.collect()

# --- Step 4: Log-returns ---
log_returns = np.log(price_matrix / price_matrix.shift(1))

# --- Step 5: Annihilate overnight gaps (dynamic date-boundary) ---
dates = price_matrix.index.date
session_open_mask = np.array(dates) != np.roll(np.array(dates), 1)
session_open_mask[0] = True  # always mask first row
log_returns[session_open_mask] = np.nan  # null first return of every session

# --- Step 6: Pairwise correlation (pandas handles NaN pairwise) ---
corr_df = log_returns.corr(method='pearson')

# --- Step 7: Extract upper triangle with t-stat filter ---
symbols = corr_df.columns.tolist()
n_obs = len(log_returns.dropna(how='all'))  # conservative n for t-stat

rows = []
for i in range(len(symbols)):
    for j in range(i + 1, len(symbols)):
        rho = corr_df.iloc[i, j]
        if np.isnan(rho):
            continue
        # Pairwise n — count rows where both are non-NaN
        n_pair = log_returns[[symbols[i], symbols[j]]].dropna().shape[0]
        if n_pair < 5000:
            continue
        t_stat = rho * np.sqrt((n_pair - 2) / max(1 - rho**2, 1e-12))
        p_val = 2 * t_dist.sf(abs(t_stat), df=n_pair - 2)
        if p_val >= 0.05:
            continue
        rows.append({
            "symbol_a": symbols[i], "symbol_b": symbols[j],
            "pearson_rho": round(rho, 6),
            "t_stat": round(t_stat, 4),
            "p_value": round(p_val, 8),
            "n_obs": n_pair,
        })

pairs_df = pd.DataFrame(rows).sort_values("pearson_rho", ascending=False).reset_index(drop=True)
pairs_df["rank"] = pairs_df.index + 1
pairs_df.to_csv("pairs_all.csv", index=False)
pairs_df.head(500).to_csv("pairs_top500.csv", index=False)
print(f"Total valid pairs: {len(pairs_df)} | Top pair: {pairs_df.iloc[0]['symbol_a']}/{pairs_df.iloc[0]['symbol_b']} ρ={pairs_df.iloc[0]['pearson_rho']:.4f}")
```

---

## 5. Known Results (Sketch 1 Kaggle Run)

| Metric | Value |
|---|---|
| Total valid pairs | 124,201 (of 124,750 possible) |
| Top pair | PFC / RECLTD — ρ = 0.6702 |
| Rank-500 cutoff | ρ = 0.3726 |
| Bars per symbol | ~39,220 intraday 1-min bars (~104 trading days) |
| Kaggle dataset | `utkarshpatelthefirst/pairs-stage1-pearson` |

---

## 6. Output Schema

| Column | Type | Description |
|---|---|---|
| `symbol_a` | str | First symbol (alphabetically earlier) |
| `symbol_b` | str | Second symbol |
| `pearson_rho` | float | Pearson ρ of log-returns |
| `t_stat` | float | t-statistic for H₀: ρ = 0 |
| `p_value` | float | Two-tailed p-value |
| `n_obs` | int | Pairwise overlapping observations used |
| `rank` | int | Rank by pearson_rho descending |

---

## Connections

- [[pairs-trading-strategy]]
- [[stage2-ou-calibration]]
- [[master-data-1min-dataset]]
- [[kaggle-notebook-run]]
- [[QC-decisions-pairs-trading]]
