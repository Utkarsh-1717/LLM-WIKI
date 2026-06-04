# Stage 3 — Pairs Trading: Intraday Backtesting (Kalman Z-Score Signal)

**Status**: PLAN  
**Created**: 2026-06-03  
**Input Datasets**:
- `utkarshpatelthefirst/pairs-stage2-kalman-ou` — `pairs_stage2_kalman_ou.csv` (66 columns)
- `utkarshpatelthefirst/master-data-1min-db` — `Master-Data-1min.sqlite`
- `utkarshpatelthefirst/pairs-stage1-pearson` — `pairs_top500.csv`

**Compute**: Kaggle CPU (single process — 41 pairs × <1s each)  
**Output**: `pairs_stage3_backtest.csv` → Ranked by Calmar Ratio → Kaggle Dataset `utkarshpatelthefirst/pairs-stage3-backtest`

---

## Objective

Run a rigorous walk-forward intraday mean-reversion backtest on all **41 pairs** that pass the Stage 3 half-life filter. Use fixed Q and R from Stage 2 EM output for online Kalman filtering. Generate Z-score signals on a rolling 10-day normalisation window. Simulate one-sided intraday trades with full Zerodha MIS fee calculation.

---

## Stage 3 Filter — Which Pairs Enter

From `pairs_stage2_kalman_ou.csv`:

```
Filter: 5.0 <= half_life_minutes <= 120.0
Result: 41 pairs
```

**Note**: ADF p-value is NOT used as a filter in Stage 3. Half-life alone determines entry eligibility.

**Half-life distribution of filtered set:** Min 5.1 min | Median 8.7 min | Max 113.8 min

---

## A. Price Series Construction (Per Pair)

The entire backtesting engine operates on a **session-continuous 1-minute log-price series** — meaning only NSE trading hours are included and the bars are stitched together as if overnight gaps do not exist. This is the foundation of the entire signal.

**Steps:**
1. Load all `close` prices for `symbol_a` and `symbol_b` from `ohlcv_1min` table in SQLite.
2. **Drop all non-trading days and non-trading hours explicitly:**
   - Filter timestamp to NSE market hours only: **09:15 ≤ time ≤ 15:29 IST** (375 bars per day).
   - Any row outside this window (pre-market, post-market, weekends, NSE holidays) is **unconditionally dropped** before any further processing.
   - Do NOT assume the database is clean — always apply this filter explicitly in code.
3. Inner-join on timestamp — drop any bar where either symbol has no close price.
4. **No gap-filling between sessions.** The 15:29 bar of day N is immediately followed by the 09:15 bar of day N+1. Overnight gaps simply do not exist in the series — they are dropped. The result is one seamless session-continuous time series of pure market-hours bars.
5. Compute `ln_price_a = ln(close_a)`, `ln_price_b = ln(close_b)`.
6. Sort chronologically. Assert all timestamps are strictly within 09:15–15:29 IST and no duplicates exist. Total expected bars ≈ 44,250 (375 min/day × ~118 trading days).

> **Why session-continuous?** The Kalman filter sees a continuous stream of log-prices. Overnight gaps would inject a massive, spurious innovation (`e_t = large jump`) into the filter at 09:15, corrupting β and α estimates. By stitching only trading hours together, every bar is a genuine market-hours observation.

---

## B. Warm-Up Phase (First 10 Trading Days = 3,750 Bars)

The first 3,750 bars are used to **initialize** the Kalman filter. No trades are placed during this period.

**Kalman Initialisation:**
- OLS regression over the 3,750 warm-up bars: `ln_price_a ~ ln_price_b`
- `β₀ = OLS beta`, `α₀ = OLS intercept`
- `P₀ = Cov(θ_OLS) × 10` (inflate for initial uncertainty)
- **Q and R are fixed from Stage 2 EM output** for this specific pair (`Q_beta`, `Q_alpha`, `R` columns from CSV). These are NOT re-estimated.

**Innovation (Spread) Tracking:**
- During the warm-up, record every Kalman innovation: `e_t = ln_price_a(t) - H_t × θ̂_{t|t-1}`
- These 3,750 innovations form the **initial normalisation window** for Z-scoring.

**Leader/Lagger Detection (Fixed Once):**
- Compute 1-bar lagged cross-correlation over the warm-up returns:
  - `corr_a_leads = corr(Δln_a(t), Δln_b(t-1))`
  - `corr_b_leads = corr(Δln_b(t), Δln_a(t-1))`
- If `corr_a_leads > corr_b_leads` → `symbol_a` is leader, `symbol_b` is **lagger** (the traded asset)
- If `corr_b_leads > corr_a_leads` → `symbol_b` is leader, `symbol_a` is **lagger** (the traded asset)
- This assignment is **fixed for the entire backtest run** of this pair. No re-detection.

---

## C. Kalman Filter — Online Update (Live Phase)

At each 1-minute bar `t` during the live phase (bar 3,751 onwards), update the Kalman Filter:

**Observation vector**: `H_t = [ln_price_b(t), 1]`  
**Observation**: `y_t = ln_price_a(t)`

**Predict:**
$$\hat{\theta}_{t|t-1} = \hat{\theta}_{t-1|t-1}$$
$$P_{t|t-1} = P_{t-1|t-1} + Q$$

**Update:**
$$e_t = y_t - H_t\hat{\theta}_{t|t-1} \quad \text{(Kalman innovation = raw spread)}$$
$$S_t = H_t P_{t|t-1} H_t^\top + R$$
$$K_t = P_{t|t-1} H_t^\top S_t^{-1}$$
$$\hat{\theta}_{t|t} = \hat{\theta}_{t|t-1} + K_t e_t$$
$$P_{t|t} = (I - K_t H_t) P_{t|t-1}$$

**No session reset.** The Kalman state rolls forward uninterrupted through the session-continuous series. Since overnight bars are not in the series, the filter never sees overnight gaps.

---

## D. Rolling Z-Score (Session-Continuous, Bar-Count Only)

The Z-score normalisation is computed on the **same session-continuous series** — the identical cleaned array that the Kalman filter sees. There is no concept of calendar days, clock time, or overnight gaps anywhere in this logic.

**Window size**: 3,750 bars = 10 trading days × 375 bars/day.

At every bar `t` in the live phase:
$$\mu_t = \text{mean}(e_{t-3749}, \ldots, e_t)$$
$$\sigma_t = \text{std}(e_{t-3749}, \ldots, e_t)$$
$$z_t = \frac{e_t - \mu_t}{\sigma_t}$$

**Critical rule**: The window rolls forward **exactly one bar at a time**, always backward by exactly 3,750 consecutive bars in the session-continuous array. If bar `t-3749` was the 09:15 bar two weeks ago and bar `t` is a 14:30 bar today, the window simply contains those 3,750 contiguous bars — it does not care that they span multiple calendar days. Non-trading hours and non-trading days are simply absent from the array and therefore absent from every window.

**Implementation**: Use a `deque(maxlen=3750)` on the innovation series. Maintain a running sum and sum-of-squares to compute mean and std in O(1) per bar.

> **Why this matters**: If we computed the window using calendar time (e.g., "last 10 days of timestamps"), overnight gaps and weekends would shrink the window and bias the statistics. By working purely on the session-continuous bar array, every window is exactly 3,750 real market observations — no more, no less.

---

## E. Signal Generation & Trade Logic

**Core Principle:** The spread is $e_t = \ln(A_t) - (\beta \ln(B_t) + \alpha)$.
When $z_t \ge 2.0$, $e_t$ is highly positive: Asset A is overpriced relative to B.
When $z_t \le -2.0$, $e_t$ is highly negative: Asset A is underpriced relative to B.

### Entry (at bar `t`)
We ONLY trade the lagging asset, expecting it to eventually catch up to the leader.

**If Asset A is the Lagger (A is slow to react):**
- If $z_t \ge +2.0$: A is overpriced. It hasn\'t fallen to match B yet. **Short Asset A**.
- If $z_t \le -2.0$: A is underpriced. It hasn\'t risen to match B yet. **Long Asset A**.

**If Asset B is the Lagger (B is slow to react):**
- If $z_t \ge +2.0$: B is underpriced relative to A (because A rose and B hasn\'t yet). **Long Asset B**.
- If $z_t \le -2.0$: B is overpriced relative to A (because A fell and B hasn\'t yet). **Short Asset B**.

*Conditions:*
- If already in a trade → skip entry (one active trade per pair at all times).
- If within 1 bar of session close (bar is 15:29) → skip entry (no time to hold).

### Exit (checked at every bar while in trade)
The following exits are checked **in order of priority**:

1. **Mean Reversion Exit**: Exit logic is unified and depends *strictly* on the Z-score at entry, regardless of whether we are long/short or trading A/B.
   - If we entered when $z \ge +2.0$, we exit as soon as $z_t \le 0.0$.
   - If we entered when $z \le -2.0$, we exit as soon as $z_t \ge 0.0$.
   Record `exit_reason = "mean_reversion"`.
2. **Half-Life Timeout Exit**: If bars elapsed since entry ≥ `ceil(half_life_minutes)` bars → exit immediately. Record `exit_reason = "halflife_timeout"`.
3. **Session-End Forced Exit**: At bar 15:28 IST, exit any open position regardless of Z-score. Record `exit_reason = "session_end"`. No overnight positions.

> **No stop-loss.** The user has explicitly chosen to rely only on the half-life timeout and session-end exit as risk controls.

### Capital & Position Sizing
- **Capital per pair**: Fixed ₹10,000 (does NOT compound or deplete across trades — each trade starts fresh from the ₹10,000 base). This isolates pair performance cleanly.
- **Quantity**: `qty = floor(10000 / entry_price_of_lagging_asset)`.
- If `qty = 0` (stock price > ₹10,000) → skip trade, log.
- Trade direction: **long or short** on the lagging asset only.

---

## F. Fee Calculation — Zerodha MIS Intraday Equity

All trades are **MIS (Margin Intraday Square-off)** intraday equity trades. Fees are computed per **order leg** (entry = 1 leg, exit = 1 leg = 1 round trip total).

### Per-Order Fee Components

| Component | Rate | Applied On | Notes |
|---|---|---|---|
| **Brokerage** | ₹20 flat per executed order | Per leg | Zerodha flat rate (not % based for equity delivery; ₹20 for intraday) |
| **STT (Securities Transaction Tax)** | 0.025% | Sell-side turnover only | Mandatory; applies at exit for long trades, at entry for short trades |
| **Exchange Transaction Charges (NSE)** | 0.00345% | Total turnover (buy + sell) | NSE equity segment rate |
| **GST** | 18% | On (Brokerage + Exchange Charges) | Central + State GST |
| **SEBI Charges** | ₹10 per crore | Total turnover | = 0.0000001 × turnover |
| **Stamp Duty** | 0.003% | Buy-side turnover only | Maharashtra rate (where Zerodha is registered) |

### Calculation Per Round Trip

```
entry_turnover = qty × entry_price
exit_turnover  = qty × exit_price
total_turnover = entry_turnover + exit_turnover

# Brokerage: ₹20 per leg × 2 legs = ₹40 per round trip
brokerage = 40.00

# STT: 0.025% on the sell-side turnover
# For LONG trade: sell side is the exit
# For SHORT trade: sell side is the entry
if long_trade:
    stt = 0.00025 × exit_turnover
else:  # short trade
    stt = 0.00025 × entry_turnover

# Exchange transaction charge: 0.00345% on total turnover
exchange_charge = 0.0000345 × total_turnover

# GST: 18% on (brokerage + exchange_charge)
gst = 0.18 × (brokerage + exchange_charge)

# SEBI charges: ₹10 per crore = 10 / 10,000,000 per rupee
sebi = (10 / 10_000_000) × total_turnover

# Stamp duty: 0.003% on buy-side turnover
# For LONG trade: buy side is entry
# For SHORT trade: buy side is exit (to cover/close short)
if long_trade:
    stamp = 0.00003 × entry_turnover
else:
    stamp = 0.00003 × exit_turnover

total_fees = brokerage + stt + exchange_charge + gst + sebi + stamp
```

### Profit Metrics Per Trade

```
gross_pnl = (exit_price - entry_price) × qty   [for LONG]
gross_pnl = (entry_price - exit_price) × qty   [for SHORT]
net_pnl   = gross_pnl - total_fees
fees_multiple = gross_pnl / total_fees          [how many × fees we earned]
```

---

## G. Per-Pair Performance Metrics

After all trades for a pair are simulated:

| Metric | Definition |
|---|---|
| `total_trades` | Total completed round-trip trades |
| `win_rate_pct` | % of trades with `net_pnl > 0` |
| `total_gross_pnl` | Σ gross_pnl across all trades |
| `total_net_pnl` | Σ net_pnl across all trades |
| `total_fees_paid` | Σ total_fees across all trades |
| `avg_fees_multiple` | Mean(fees_multiple) — how many times fees per trade on average |
| `avg_gross_pnl_per_trade` | Mean gross P&L per trade |
| `avg_net_pnl_per_trade` | Mean net P&L per trade |
| `avg_trade_duration_minutes` | Mean minutes held per trade |
| `max_drawdown_pct` | Max peak-to-trough in cumulative net_pnl / initial_capital × 100 |
| `sharpe_ratio` | `mean(daily_pnl) / std(daily_pnl) × sqrt(250)` |
| `calmar_ratio` | `annualised_return / abs(max_drawdown_pct)` where `annualised_return = (total_net_pnl / capital) × (250 / n_trading_days) × 100` |
| `n_exits_mean_reversion` | Trades exited at Z=0 cross |
| `n_exits_halflife_timeout` | Trades exited due to half-life timeout |
| `n_exits_session_end` | Trades exited at 15:28 |
| `lagging_asset` | The asset traded (long/short) |
| `leader_asset` | The asset NOT traded |

---

## H. Final Ranked Output CSV

`pairs_stage3_backtest.csv` — **one row per pair, ranked by Calmar Ratio (highest first)**

**Stage 1 columns (from pairs_top500.csv):**
`symbol_a`, `symbol_b`, `pearson_rho`, `stage1_rank`

**Stage 2 columns (from pairs_stage2_kalman_ou.csv):**
`Q_beta`, `Q_alpha`, `R`, `SNR_beta_R`, `half_life_minutes`, `half_life_hours`, `adf_pvalue`, `hurst_exponent`, `beta_mean`, `beta_std`

**Stage 3 columns (computed here):**
All metrics from section G above, plus: `lagging_asset`, `leader_asset`, `warmup_bars`, `live_bars`, `data_start`, `data_end`, `capital_inr`, `stage3_rank`

---

## Error Guards

| Condition | Action |
|---|---|
| Fewer than 4,126 bars (10 warm-up days + 1 live day) | Skip pair → `skipped_stage3.csv` |
| Qty = 0 (stock price > ₹10,000 per share) | Skip this trade, log `skip_reason = "price_too_high"` |
| `σ_t = 0` (degenerate spread — e.g. identical prices) | Skip Z-score computation for this bar |
| Any unhandled exception per pair | Log to `error` column, continue to next pair |

---

## Compute Plan

- **41 pairs** × ~37,000 live bars each = single-process Python (< 2 minutes total on Kaggle)
- **No multiprocessing needed** — 41 pairs is trivial
- **Memory**: 41 × 44k bars × 2 cols × 8 bytes ≈ 57 MB total — trivial

---

## Kaggle Notebook Details

- **Title**: `Stage3 Pairs Backtest`
- **Slug**: `stage3-pairs-backtest`
- **GPU**: Disabled
- **Internet**: Enabled
- **Dataset sources**:
  - `utkarshpatelthefirst/master-data-1min-db`
  - `utkarshpatelthefirst/pairs-stage2-kalman-ou`
  - `utkarshpatelthefirst/pairs-stage1-pearson`
- **Output dataset**: `utkarshpatelthefirst/pairs-stage3-backtest`

---

## Connections
- [[pairs-trading-pipeline]]
- [[pairs-stage2-kalman-ou]]
- [[pairs-stage1-pearson]]
- [[master-data-1min-dataset]]
- [[kaggle-compute]]
- [[kaggle-notebook-hardening]]
