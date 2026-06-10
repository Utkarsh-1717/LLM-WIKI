> [!WARNING]
> **ARCHIVED & OBSOLETE**
> This file is part of the trial-and-error "Sketch" phase. 
> The mathematics and code herein may contain deprecated Expectation-Maximization loops or failed concepts.
> The final, verified truth is located in the `Soul/` directory.
> Tags: #archived-sketch #pairs-trading-prototype

# Stage 1 — Pairs Trading: Pearson Correlation Screening
**Status**: ✅ COMPLETE
**Completed**: 2026-06-02 | Kaggle runtime: 568s (~9.5 min) | Kernel v3
**Last Updated**: 2026-06-02

## Actual Results
- **Total valid pairs**: 124,201 (of 124,750 possible)
- **n_obs per pair**: 39,220 intraday 1-min bars (~104 trading days)
- **Top pair**: PFC / RECLTD — ρ = 0.6702
- **#2**: INFY / TCS — ρ = 0.6596
- **Rank-500 cutoff**: ρ = 0.3726
- **Outputs**: `Raw/Sources/attachments/pairs_all.csv` (124,201 rows) + `pairs_top500.csv` (500 rows)
- **Kaggle dataset**: `utkarshpatelthefirst/pairs-stage1-pearson`
- **Wiki note**: [[pairs-stage1-pearson]]
- **Next**: Stage 2 — Cointegration testing on top 500 pairs
**Dataset**: [[master-data-1min-dataset]] (`utkarshpatelthefirst/master-data-1min-db`)
**Compute**: [[kaggle-compute]] (GPU + CPU T4 x2)
**Outputs**: Two CSV files → saved to `Raw/Sources/attachments/` in [[llm-wiki]]

---

## 1. Objective

Compute the pairwise **Pearson correlation coefficient** of **log-returns** across all ~500 NSE equities using 1-minute OHLCV data. Rank pairs from highest to lowest correlation and export:

- `pairs_top500.csv` — Top 500 most correlated pairs
- `pairs_all.csv` — All valid pairs (~124,750 total for N=500)

These outputs feed directly into **Stage 2** (cointegration testing) and **Stage 3** (spread modelling + z-score signal generation).

---

## 2. Critical Methodology Corrections from Original Sketch

### ❌ Error 1 — "Magnifier / Multiplier on Price Differences"
The original sketch proposed scaling prices before subtraction to avoid rounding error. This is **incorrect and unnecessary**.

**Why it's wrong:**
- Log-returns are computed as `ln(P_t / P_{t-1})`, which is a **ratio**, not a subtraction.
- Ratios are inherently free from absolute magnitude / decimal-place bias.
- Pearson correlation is **scale-invariant** — multiplying returns by any constant leaves ρ unchanged.
- Introducing a multiplier adds no precision and can mislead downstream code.

**Correct approach:** Compute log-returns directly, no scaling needed.

```
r_t = ln(close_t / close_{t-1})
```

### ❌ Error 2 — "Use Full GPU"
Pearson correlation on a returns matrix is a **linear algebra operation** (matrix dot product). On Kaggle:
- NumPy / Pandas `.corr()` runs on CPU with BLAS-optimised LAPACK routines.
- GPU (cuDF / RAPIDS) can accelerate this, but only if data fits in GPU RAM (~15GB on T4).
- For N=500 symbols × ~75,000 rows of 1-min data the returns matrix is ~500×75k float32 ≈ 150 MB — fits in GPU RAM easily.

**Correct approach:** Use **GPU via cuDF** (`import cudf`) for the correlation matrix, with CPU NumPy fallback if cuDF is unavailable.

### ❌ Error 3 — "Pearson Correlation on Raw Prices"
The sketch correctly identifies log-returns as the input, but it's worth making the exact anti-pattern explicit: **never compute Pearson ρ on raw Close prices**. Raw price series are non-stationary and will yield spuriously high correlations due to shared trends (co-trending), not co-movement of returns.

**Correct approach:** Always compute ρ on log-return series. Log-returns are approximately stationary (mean-reverting, no unit root in most equity returns).

### ❌ Error 4 — "Overnight/Weekend Gap Returns Not Removed" *(Added per user instruction)*
The original sketch treats the price series naively without removing non-trading periods. When you compute `ln(P_t / P_{t-1})` across a weekend or overnight boundary, you get a **gap return** — the price move from Friday's close to Monday's open. This is NOT an intraday return. It mixes two fundamentally different return regimes (intraday vs overnight/overnight-gap) and will corrupt the correlation signal.

**The problem concretely:**
- Friday 15:29 → Monday 09:15: a 64.5-hour gap masquerading as a 1-minute return
- A single overnight return can have 5–10× the variance of a true 1-min intraday return
- Pairs that are highly correlated intraday may open gap in different directions — these "ghost returns" add noise

**Correct approach:**
1. Filter rows to **NSE market hours only**: `09:15 ≤ time ≤ 15:29` IST — discard all pre-market, post-market, and non-trading timestamps.
2. Compute log-returns on the filtered matrix.
3. **Drop the first bar of every trading session** (the 09:15 bar's return = `ln(open_today / close_yesterday)` = an overnight return). Mark and null these out before correlation.
4. Result: a clean, session-continuous return series with no gap contamination.

---

### ❌ Error 5 — "No Alignment / Missing Data Handling"
The original plan ignores the critical issue of **timestamp alignment**. NSE 500 stocks have different listing dates, halted sessions, and missing bars. Misaligned series will corrupt correlation estimates.

**Correct approach:**
1. Pivot the close prices into a `(timestamp × symbol)` matrix.
2. Drop any timestamps that are **not common to all symbols** (inner join on timestamp).
3. For any remaining NaN (data gaps within the common window), **forward-fill by at most 1 bar**, then drop rows with remaining NaN.
4. Compute log-returns on the aligned, clean matrix.

### ❌ Error 6 — "No Minimum Observation Threshold"
A pair with only 100 overlapping 1-min bars will yield a statistically meaningless ρ.

**Correct approach:** Require a **minimum of 5,000 common observations** per pair. After removing overnight returns (~375 bars/day × 120 days = ~45,000 intraday bars total, minus first-bar drops = ~44,625 net bars), 5,000 is a conservative threshold (~11 trading days overlap).

### ❌ Error 7 — "No Statistical Significance Test"
High ρ can occur by chance with small N. Quant finance standard is to verify statistical significance.

**Correct approach:** For each pair, compute the **t-statistic**:

```
t = ρ × sqrt((n - 2) / (1 - ρ²))
```

With n = number of overlapping observations, this follows a t-distribution with `(n-2)` degrees of freedom under H₀: ρ = 0.

- Include a `p_value` column in both CSVs.
- **Only include pairs with p < 0.05** in the final ranked output (two-tailed test).
- In practice with n > 5,000 any |ρ| > 0.03 will be significant — this mainly filters pairs with very low n.

---

## 3. Full Methodology (Correct)

### Step 1 — Load Raw Data
```python
import sqlite3
import pandas as pd
import numpy as np

con = sqlite3.connect("/kaggle/input/master-data-1min-db/Master-Data-1min.sqlite")
df = pd.read_sql("SELECT symbol, timestamp, close FROM ohlcv_1min ORDER BY timestamp", con)
con.close()

print(f"Raw rows loaded: {len(df):,}")
print(f"Symbols: {df['symbol'].nunique()}")
print(f"Timestamp range: {df['timestamp'].min()} → {df['timestamp'].max()}")
```

### Step 2 — Filter to NSE Market Hours & Build Session-Continuous Series
```python
# Convert timestamp to pandas datetime (assumed stored as UNIX epoch or ISO string)
# Fyers stores timestamps as UNIX epoch integers (seconds, UTC)
df['dt'] = pd.to_datetime(df['timestamp'], unit='s', utc=True).dt.tz_convert('Asia/Kolkata')

# NSE trading hours: 09:15 to 15:29 IST (last 1-min bar opens at 15:29)
df['time_only'] = df['dt'].dt.time
import datetime
market_open  = datetime.time(9, 15)
market_close = datetime.time(15, 29)

df_trading = df[(df['time_only'] >= market_open) & (df['time_only'] <= market_close)].copy()
print(f"After market-hours filter: {len(df_trading):,} rows")
print(f"Bars per symbol approx: {len(df_trading) // df_trading['symbol'].nunique()}")

# Add date column to identify session boundaries
df_trading['date'] = df_trading['dt'].dt.date
```

### Step 3 — Pivot to Price Matrix & Align Timestamps
```python
# Pivot: rows = timestamp (IST), cols = symbol
price_matrix = df_trading.pivot(index='dt', columns='symbol', values='close')

# Inner join alignment: keep only timestamps present in ALL symbols
# This treats the series as one continuous intraday block — no symbol-specific gaps
price_matrix = price_matrix.dropna(how='any', axis=0)

print(f"Aligned price matrix shape: {price_matrix.shape}")
print(f"= {price_matrix.shape[0]} common bars × {price_matrix.shape[1]} symbols")
assert (price_matrix > 0).all().all(), "Non-positive prices detected — data quality issue"
```

> **Note**: If strict inner join retains fewer than 10,000 bars, relax to keeping symbols with ≥80% coverage, drop remaining NaN rows, then proceed.

### Step 4 — Compute Log-Returns & Drop Session-Open Bars
```python
# Log-return: ln(close_t / close_{t-1})  — ratio, no scaling needed
log_returns_raw = np.log(price_matrix / price_matrix.shift(1))

# ── CRITICAL: Drop first bar of every trading session ──────────────────────
# The 09:15 bar's return = ln(today_open / yesterday_close) = overnight gap return
# This is NOT an intraday return — it must be nulled before correlation
session_open_mask = price_matrix.index.time == market_open  # True for every 09:15 bar
log_returns_raw[session_open_mask] = np.nan  # Null all session-open returns

# Drop all rows that contain any NaN (first row from shift, and all session-open rows)
log_returns = log_returns_raw.dropna(how='any')

# Sanity checks
assert log_returns.isnull().sum().sum() == 0, "NaN remains in log_returns"
assert not np.isinf(log_returns.values).any(), "Inf in log_returns — zero-price row exists"

n_bars = len(log_returns)
n_symbols = log_returns.shape[1]
print(f"Clean log-return matrix: {n_bars:,} bars × {n_symbols} symbols")
print(f"Expected ~{120 * 374:,} bars (120 days × 374 intraday returns/day)")
# NSE has 375 bars/day (09:15–15:29), minus 1 session-open drop = 374 net returns/day
```

### Step 4 — Pearson Correlation Matrix
```python
# Option A: GPU (cuDF/RAPIDS) — preferred on Kaggle T4
try:
    import cudf
    import cupy as cp
    lr_gpu = cudf.DataFrame.from_pandas(log_returns)
    corr_matrix = lr_gpu.corr()  # Uses GPU BLAS
    corr_df = corr_matrix.to_pandas()
    print("GPU correlation complete")
except ImportError:
    # Option B: CPU NumPy — BLAS-optimised, perfectly adequate
    corr_df = log_returns.corr(method="pearson")
    print("CPU correlation complete")
```

### Step 5 — Extract Upper Triangle Pairs
```python
# Avoid duplicate pairs (A-B == B-A) and self-pairs (A-A)
symbols = corr_df.columns.tolist()
n_symbols = len(symbols)
n_obs = len(log_returns)  # number of aligned 1-min bars

rows = []
for i in range(n_symbols):
    for j in range(i + 1, n_symbols):
        rho = corr_df.iloc[i, j]
        if np.isnan(rho):
            continue
        # t-statistic for significance
        t_stat = rho * np.sqrt((n_obs - 2) / (1 - rho ** 2))
        # Two-tailed p-value from t-distribution
        from scipy.stats import t as t_dist
        p_val = 2 * t_dist.sf(abs(t_stat), df=n_obs - 2)
        rows.append({
            "symbol_a": symbols[i],
            "symbol_b": symbols[j],
            "pearson_rho": round(rho, 6),
            "t_stat": round(t_stat, 4),
            "p_value": round(p_val, 6),
            "n_obs": n_obs,
        })

pairs_df = pd.DataFrame(rows)
# Filter: significance + minimum obs
pairs_df = pairs_df[
    (pairs_df["p_value"] < 0.05) &
    (pairs_df["n_obs"] >= 5000)
]
# Rank: highest |ρ| first (we rank on raw ρ, positively correlated pairs are target)
pairs_df = pairs_df.sort_values("pearson_rho", ascending=False).reset_index(drop=True)
pairs_df["rank"] = pairs_df.index + 1
```

### Step 6 — Export CSVs
```python
pairs_df.to_csv("pairs_all.csv", index=False)
pairs_df.head(500).to_csv("pairs_top500.csv", index=False)
print(f"Total valid pairs: {len(pairs_df)}")
print(f"Top 500 saved. Min ρ in top 500: {pairs_df.iloc[499]['pearson_rho']:.4f}")
```

### Step 7 — Save to LLM-WIKI (via Kaggle Dataset Publish)
- Publish both CSVs as a new Kaggle dataset: `utkarshpatelthefirst/pairs-stage1-pearson`.
- Download locally and place in `Raw/Sources/attachments/`.
- Create a Wiki entity note: `Wiki/Entities/pairs-stage1-pearson.md`.

---

## 4. Expected Output Schema

| Column | Type | Description |
|---|---|---|
| `symbol_a` | str | First symbol (alphabetically earlier) |
| `symbol_b` | str | Second symbol |
| `pearson_rho` | float | Pearson correlation of 1-min log-returns |
| `t_stat` | float | t-statistic for H₀: ρ = 0 |
| `p_value` | float | Two-tailed p-value |
| `n_obs` | int | Number of aligned 1-min observations used |
| `rank` | int | Rank by pearson_rho descending |

---

## 5. Stage 2 Preview (Do NOT implement yet)

Top 500 pairs from this screen will be passed to **Stage 2: Cointegration Testing** (Engle-Granger or Johansen test). High Pearson ρ is a necessary but NOT sufficient condition for a tradeable pairs trade — cointegration confirms the spread is mean-reverting.

> ⚠️ Do not trade on correlation alone. Two stocks can be highly correlated without being cointegrated. Stage 2 is mandatory.

---

## 6. Compute & Resource Estimates (Kaggle)

| Item | Estimate |
|---|---|
| Symbols | ~500 |
| 1-min bars per symbol | ~75,000 (120 trading days) |
| Log-returns matrix size | ~500 × 75,000 × 4 bytes ≈ 150 MB |
| Correlation matrix size | 500 × 500 × 8 bytes ≈ 2 MB |
| Pairs upper triangle | 500×499/2 = 124,750 pairs |
| `pairs_all.csv` estimated size | ~12 MB |
| `pairs_top500.csv` estimated size | ~50 KB |
| GPU runtime estimate | < 5 min |
| CPU fallback runtime estimate | < 15 min |

---

## 7. Validation Checklist (Run Before Accepting Output)

- [ ] `price_matrix` has zero NaN after alignment step
- [ ] `log_returns` has zero NaN after `.dropna()`
- [ ] No infinite values in `log_returns` (check with `np.isinf().any()`)
- [ ] All `n_obs` values are equal (common timestamp alignment used)
- [ ] `pearson_rho` range: strictly in [-1, 1]
- [ ] `p_value` < 0.05 for ALL rows in output files
- [ ] `rank` column is 1-indexed, contiguous, no gaps
- [ ] `pairs_top500.csv` has exactly 500 rows
- [ ] `symbol_a` is always alphabetically before `symbol_b` (no duplicate pairs)

---

## 8. Open Questions / Decisions

1. **Strict vs. Pairwise Alignment**: Should we use strict inner-join (same timestamp window for all 500 symbols) or pairwise alignment (each pair uses its own maximum overlap)? 
   - **Recommendation**: Use strict inner join for Stage 1 screening — it's simpler, consistent, and if the dataset has good coverage (120 days, all NSE 500) there should be sufficient overlap. Pairwise alignment is more powerful but adds 10× computation complexity.
   
2. **Negative Correlation**: Should we include negatively correlated pairs (ρ < −0.5)?
   - **Recommendation**: Exclude for now. Standard pairs trading targets positively correlated pairs. Negatively correlated pairs require a different spread construction (sum instead of difference). Keep for Stage 1 simplicity.

3. **Rolling vs. Full-Period Correlation**: Should ρ be computed on the entire 120-day history or on a rolling window (e.g., last 30 days)?
   - **Recommendation**: Full-period for Stage 1 (stable, less noise). Rolling correlation is a Stage 3 concept (for dynamic position sizing / pair staleness detection).

---

*Status: PLAN APPROVED — ready for notebook execution*
*Next action: Create Kaggle notebook using [[kaggle-notebook-run]] skill*