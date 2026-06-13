# Pairs Trading — Stage 1 Methodology Blueprint

**File**: `pair_trading_stage1.py`  
**Version**: 1.0 | **Date**: 2026-06-13  
**Authors**: Production pipeline derived from 124,750-pair sweep analysis.

---

## Architecture Overview

Stage 1 is a fully automated **monthly re-roll engine**. It runs on a cloud (Kaggle) machine, triggered by a GitHub Actions CRON job every Sunday at 3:00 AM IST, and answers exactly one question:

> **Which pairs should we trade this month?**

It produces exactly 4 CSV files and publishes them to a private Kaggle dataset, which Stage 2 (live execution) will read.

---

## Pipeline Flow

```
GitHub CRON (3 AM IST Sunday)
    │
    ▼ kaggle kernels push
Kaggle Kernel: pair_trading_stage1.ipynb
    │
    ├─ Step 0: Thread Lock (OPENBLAS/OMP = 1) + Imports
    ├─ Step 1: Fyers TOTP Authentication (5-step)
    ├─ Step 2: Live NSE 500 List (NSE Archives)
    ├─ Step 3: Download 120 Exact Trading Days 1-min Close (Fyers)
    ├─ Step 4: Trim to exactly 120 unique trading dates + build price matrix
    ├─ Step 5: 70% Coverage Filter
    ├─ Step 6: Pearson Correlation Screening
    ├─ Step 7: Numba Engine Definition
    ├─ Step 8: Joblib Parallel Sweep (all N×(N-1)/2 pairs)
    ├─ Step 9: Walk-Forward Physics Filter → Top 50 Pure
    └─ Step 10: Publish 4 CSVs to private Kaggle dataset
```

---

## Step-by-Step Explanation

### Step 0 — Thread Locking & Imports
```python
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
```
**Why**: With `joblib.Parallel(n_jobs=-1)` using all 4 Kaggle CPU cores, each worker also internally spawns OpenBLAS thread pools for NumPy matrix operations. Without locking, you get `4 cores × 4 NumPy threads = 16 threads fighting for 4 CPUs`, causing immediate CPU thrashing, memory exhaustion, and kernel crash. Setting both environment variables to `"1"` forces NumPy to use single-threaded mode, giving joblib clean exclusive control over each core.

> **Critical Rule**: These two lines must appear BEFORE `import numpy` — otherwise the threads are already spawned and the environment variables have no effect.

---

### Step 1 — Fyers TOTP Authentication
5-step TOTP flow using production credentials hardcoded in the notebook (Kaggle has no access to `~/.quant_env`).

```
send_login_otp → verify_otp (TOTP) → verify_pin → get_auth_code → generate_token
```

- The TOTP key (`pyotp.TOTP(totp_key).now()`) rotates every 30 seconds. The entire authentication must complete within one 30-second window.
- The final `fyers` object is used for all subsequent `fyers.history()` calls.

---

### Step 2 — Live NSE 500 Symbol Fetch
```python
url = "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"
```
- Always fetched live. Never hardcoded. Works in any year.
- Produces `NSE-500_MMDDYY.csv`.
- Converts plain symbols (e.g., `RELIANCE`) to Fyers format: `NSE:RELIANCE-EQ`.

---

### Step 3 — Exact 120 Trading Days Download
**The Key Design Decision**: Instead of using holiday calendars or approximations (`"175 calendar days ≈ 120 trading days"`), the system downloads 2 chunks of 90 calendar days each (180 calendar days total = always contains 120+ trading days), then counts the actual unique trading dates present in the downloaded data and trims to exactly the latest 120.

```
Chunk 1: (today - 180 days) → (today - 91 days)
Chunk 2: (today - 90 days)  → (today)
```

- `0.5s` sleep between every API call (Fyers rate limit compliance).
- Errors for individual symbols are collected silently — never break the main loop.
- Only `(timestamp, close)` stored — open/high/low/volume discarded to save RAM.
- 500 symbols × 2 chunks × 0.5s = ~8.5 minutes of sleep. Total fetch time ≈ 15-20 minutes.

---

### Step 4 — 120 Trading Day Trim + Continuous Price Matrix
1. Collect all unique `date` objects across all symbol data.
2. Sort ascending, take the last 120 dates as `keep_dates`.
3. Filter all raw bars: keep only rows where `bar_date in keep_dates` and `915 <= time_int <= 1529`.
4. Pivot to a `price_matrix` DataFrame: index = IST timestamp, columns = symbols.

**Continuous Treatment**: No session gaps are inserted between trading days. The last bar of day N (15:29) is immediately followed by the first bar of day N+1 (9:15). This is intentional — the OLS and Z-Score calculations treat the full 120-day dataset as one continuous stream, ignoring overnight gaps.

---

### Step 5 — 70% Coverage Filter
```python
MIN_BARS = 120 × 375 × 0.70 = 31,500 bars
```
- Any symbol with fewer than 31,500 bars of actual data is excluded.
- Catches: newly listed IPOs, symbols with API data gaps, delisted stocks re-added to NSE 500.
- Saves `le_70_coverage_MMDDYY.csv` (typically empty for established NSE 500 constituents).

---

### Step 6 — Pearson Correlation Screening
Pre-filter to only pairs where Pearson correlation is statistically significant (`p < 0.05`). This eliminates truly uncorrelated pairs and reduces the combinatorial search space.

> **Important**: Pearson correlation ($\rho$) is NOT used as a ranking criterion. It is only used as a coarse elimination filter. From the 124,750-pair sweep analysis, we proved that $\rho$ has zero (slightly negative) correlation with final PnL. Cointegration (ADF p-value) is the true predictor.

---

### Step 7 — Numba Execution Engine

#### Lagger Detection (`detect_lagger`)
Uses the first `ROLLING_WINDOW = 7500` bars as warmup data.

Computes two cross-correlations on 1-minute log-returns:
- `c_ab`: correlation of `ret_a[t]` with `ret_b[t-1]` (does B lead A?)
- `c_ba`: correlation of `ret_b[t]` with `ret_a[t-1]` (does A lead B?)

If `|c_ba| >= |c_ab|` → B leads A → A is the lagger → trade A.

The lagger (Stock A) has more α to harvest because it consistently moves after the leader — this gives a predictive signal with real alpha before prices equalize.

#### Continuous Vectorized OLS (`process_pair`)
Uses **log-prices** (not raw prices) for OLS to compute stationary, scale-invariant spreads:

```python
beta  = rolling_cov(log_ya, log_yb, window=7500) / rolling_var(log_yb, window=7500)
alpha = rolling_mean(log_ya) - beta × rolling_mean(log_yb)
spread = log_ya - (alpha + beta × log_yb)
```

This is a minute-by-minute updating OLS. At every bar, the hedge ratio $\beta$ and intercept $\alpha$ re-estimate themselves using the rolling 7500-bar window. This means the spread is always stationary relative to the current regime — no stale fixed-coefficient lookback bias.

#### Z-Score
```python
z_score = (spread - rolling_mean(spread, 7500)) / rolling_std(spread, 7500)
```

#### Execution State Machine (`_numba_backtest_loop`)
Compiled to C++ machine code via `@numba.njit`. Runs at ~9ms per pair (vs ~94ms in Python).

**Entry Logic**:
- `z >= +2.0`: Spread is too high → short lagger (spread will fall, lagger price will rise to catch up)
- `z <= -2.0`: Spread is too low → long lagger (spread will rise, lagger price will pull back down)

**Exit Logic**:
- `z crosses 0`: Mean reversion complete → exit (ideal exit)
- `time == 15:15`: Forced EOD square-off (Indian MIS rules) → exit regardless

**Lockout Logic** (`is_locked_out`):
After every forced 15:15 exit, `is_locked_out = True`. The position cannot re-enter until `|z| < 1.0`. This prevents immediate re-entry into a still-dislocated spread the next morning, which would be "trade spam" with no expected alpha.

#### Fee Model (`calc_zerodha_friction`)
Exact Zerodha Equity MIS fees per leg:
```
Brokerage = min(trade_value × 0.03%, ₹20)
STT       = trade_value × 0.025%  (sell side only)
Exchange  = trade_value × 0.00325%
GST       = (Brokerage + Exchange) × 18%
SEBI      = trade_value × 0.0001%
Stamp     = trade_value × 0.003%  (buy side only)
```

#### Physical Parameter Extraction
After the backtest, the following ex-ante structural parameters are computed from the spread itself:

| Parameter | Formula | Physical Meaning |
|---|---|---|
| `spread_vol` | `std(spread)` | Volatility / width of the rubber band |
| `mean_abs_dev` | `mean(|spread|)` | Average distance from mean |
| `zero_crossings` | Count of sign changes | Mean reversion frequency |
| `half_life` | `-log(2)/log(β_OU)` | Minutes for 50% reversion |
| `kalman_q` | `σ² × (1 - e^(-2λΔt))` | Process noise / elasticity |

Where $\beta_{OU}$ is derived from a discrete OU regression:
```python
beta_ou = cov(spread[t-1], spread[t]) / var(spread[t-1])
```

#### Lazy ADF (Cointegration Test)
The `statsmodels.adfuller()` test takes ~1.5s per pair. Running it on all pairs would add 52 hours.  
**Solution**: Only run ADF on pairs where `net_pnl > 0`. Unprofitable pairs don't need cointegration confirmation — they're already filtered out.

---

### Step 9 — Walk-Forward Physics Filter

Derived from the definitive 124,750-pair sweep on 5.5 months of NSE data (2026-06-13):

| Filter | Bound | Proof |
|---|---|---|
| `adf_pval < 0.005` | 99.5% cointegration | Decile 1 (p<0.001) → ₹3,240 avg PnL vs Decile 10 (p=0.18) → ₹1,947 avg PnL |
| `spread_vol > 0.045` | Enough width to beat fees | Top 50: 0.048 vol vs Bottom 50: 0.041 vol (+18%) |
| `half_life < 1000` | Must revert within ~2.7 days | Top 50: 970 min vs Bottom 50: 1233 min (-21%) |
| `kalman_q > 3.0e-06` | Enough elasticity for entries | Top 50: 3.64e-06 vs Bottom 50: 2.12e-06 (+71%) |

---

### Step 10 — Output Files

| File | Description |
|---|---|
| `NSE-500_MMDDYY.csv` | Live NSE 500 symbols as of run date |
| `le_70_coverage_MMDDYY.csv` | Symbols excluded for insufficient data |
| `Ranked_Profit_All_MMDDYY.csv` | All executed pairs, ALL fields, ranked by net PnL |
| `Top_50_Pure_MMDDYY.csv` | Top 50 pairs passing all 4 physics bounds |

Published to: `kaggle.com/datasets/utkarshpatelthefirst/pairs-stage1-outputs` (private)

---

## GitHub Actions Trigger

**File**: `.github/workflows/stage1-monthly.yml`  
**Cron**: `30 21 * * 6` UTC = **3:00 AM IST every Sunday**

```
GitHub Actions (ubuntu-latest)
  → pip install kaggle
  → python3 pair_trading_stage1.py    (generates .ipynb + kernel-metadata.json)
  → kaggle kernels push               (submits to Kaggle cloud)
  → Kaggle executes notebook (~2 hrs)
  → Results auto-published to private dataset
```

Kaggle credentials hardcoded directly in the workflow (`kaggle.json` written at runtime). The `LLM-WIKI` GitHub repo is private — no security risk.

## Connections

- [[build_continuous_ols_pipeline_nb]]
- [[walkforward-physics-analysis]]
- [[continuous-ols-execution]]
- [[QC-decisions-pairs-trading]]
- [[kaggle-notebook-hardening]]
- [[fyers-auth]]
