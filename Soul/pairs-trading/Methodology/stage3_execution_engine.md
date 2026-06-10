# Stage 3 — Execution Engine (Single-Sided Lagger)
**Status**: ✅ COMPLETE (500 pairs — Kalman + Continuous OLS both validated)  
**Source**: `Soul/pairs-trading/Code/build_full_pipeline_nb.py` (Kalman) | `build_continuous_ols_pipeline_nb.py` (OLS)

---

## 1. Objective

Run a realistic intraday mean-reversion backtest on the **Top 5 pairs** using the Kalman-filtered spread and Z-score signal. The execution engine is **identical** for all Q calibration methods — only the Q input matrix changes between methods.

---

## 2. Kalman Forward Filter (Online)

The Stage 3 engine runs a **forward-only Kalman filter** — no backward smoother, no EM. Q and R are fixed from Stage 2 calibration. The filter continuously updates the hedge ratio estimate $\hat{\theta}_t = [\hat{\beta}_t, \hat{\alpha}_t]$ and tracks the residual spread.

### 2.1 State-Space Model

**State vector** (hedge ratio + intercept):
$$\theta_t = \begin{bmatrix} \beta_t \\ \alpha_t \end{bmatrix}$$

**State transition** (random walk prior):
$$\theta_t = \theta_{t-1} + w_t, \quad w_t \sim \mathcal{N}(0, Q)$$

**Observation** (log-price of Asset A):
$$y_t = H_t \theta_t + v_t, \quad v_t \sim \mathcal{N}(0, R)$$

where $y_t = \ln(P_{A,t})$ and $H_t = [\ln(P_{B,t}),\; 1]$.

### 2.2 Warmup Initialization

The first 1875 bars (5 trading days) are used for warmup — no trades during this period:

```python
warmup_n = min(1875, len(ya) // 10)
X_w = np.column_stack([yb[:warmup_n], np.ones(warmup_n)])
beta0 = np.linalg.lstsq(X_w, ya[:warmup_n], rcond=None)[0]
res = ya[:warmup_n] - X_w @ beta0
R_est = np.sum(res**2) / (warmup_n - 2)
P0 = R_est * np.linalg.inv(X_w.T @ X_w)
x_upd = beta0
P_upd = P0
```

### 2.3 Leader/Lagger Detection (Fixed Once)

During warmup, determine which asset leads (has already priced in the information) and which lags (the one to trade):

```python
# 1-bar lagged cross-correlation on log-return differences
delta_a = np.diff(ya[:warmup_n])
delta_b = np.diff(yb[:warmup_n])

corr_a_leads = np.corrcoef(delta_a[1:], delta_b[:-1])[0, 1]
corr_b_leads = np.corrcoef(delta_b[1:], delta_a[:-1])[0, 1]

# sym_a lags if sym_b leads more strongly
lagger = sym_a if corr_b_leads > corr_a_leads else sym_b
```

This assignment is **fixed for the entire backtest** — no re-detection mid-run.

### 2.4 Filter Predict & Update Cycle

For each bar `t` in the live phase (bar 1876 onwards):

**Predict**:
$$\hat{\theta}_{t|t-1} = \hat{\theta}_{t-1|t-1}$$
$$P_{t|t-1} = P_{t-1|t-1} + Q$$

**09:15 Gap Adjustment** (every session open):
$$P_{t|t-1} = P_{t|t-1} \times 2$$

**Update**:
$$v_t = y_t - H_t \hat{\theta}_{t|t-1} \qquad \text{(innovation = spread)}$$
$$S_t = H_t P_{t|t-1} H_t^\top + R$$
$$K_t = P_{t|t-1} H_t^\top / S_t$$
$$\hat{\theta}_{t|t} = \hat{\theta}_{t|t-1} + K_t v_t$$
$$P_{t|t} = P_{t|t-1} - K_t H_t P_{t|t-1}$$

```python
time_int = timestamps.hour * 100 + timestamps.minute
is_open = (time_int == 915)

for t in range(len(ya)):
    x_p = x_upd
    P_p = P_upd + Q
    if is_open[t]:
        P_p *= 2.0                          # Gap Protocol

    H_t = np.array([yb[t], 1.0])
    v_t = ya[t] - H_t @ x_p               # spread (innovation)
    S_t = H_t @ P_p @ H_t + R
    K_t = P_p @ H_t / S_t
    x_upd = x_p + K_t * v_t
    P_upd = P_p - np.outer(K_t, H_t) @ P_p
    spread[t] = v_t
```

---

## 3. Z-Score Signal Generation

> ⚠️ **CRITICAL Z-SCORE WINDOW: 7500 bars (20 trading days) — NOT 375**

The original implementation used a 375-bar window (1 day). Measured pair half-lives are 642–3,400 minutes. A 375-bar window re-centered the rolling mean *faster* than pairs could revert, causing premature exits and severe friction drag. Window corrected to 7,500 bars.

The Z-score measures how far the current spread has deviated from its recent mean, normalized by recent volatility:

$$Z_t = \frac{\text{spread}_t - \mu_{7500}}{\sigma_{7500}}$$

where $\mu_{7500}$ and $\sigma_{7500}$ are the rolling mean and standard deviation over the last **7,500 bars** (= 20 full trading days).

```python
ZSCORE_WINDOW = 7500
spread_series = pd.Series(spread)
rolling_mean = spread_series.rolling(window=ZSCORE_WINDOW).mean()
rolling_std  = spread_series.rolling(window=ZSCORE_WINDOW).std()
z_scores = ((spread_series - rolling_mean) / rolling_std).values
```

> **Why rolling Z-score (not Kalman innovation Z)?** The Kalman innovation variance $S_t$ is dominated by measurement noise R, making the Kalman Z rarely exceed 0.05 in absolute value. The rolling Z-score uses the spread's actual realized distribution as the reference — this is the true signal of structural dislocation.

---

## 4. Trade Logic

### 4.1 Entry

Trades begin at bar 376 (first bar with a valid 375-bar window). Only one active position per pair at a time.

| Condition | Action |
|---|---|
| `Z_t ≤ −2.0` | **LONG** the lagging asset (it is underpriced; lagger is below its structural level) |
| `Z_t ≥ +2.0` | **SHORT** the lagging asset (it is overpriced; lagger is above its structural level) |
| `time == 15:15` | Skip entry — insufficient time to hold |
| Already in trade | Skip entry |

### 4.2 Exit (checked every bar while in trade, in priority order)

1. **EOD Square-Off** (`time == 15:15`): All positions closed unconditionally. Avoids broker MIS auto-squareoff penalties and overnight gap risk. Exit reason: `"EOD"`
2. **Mean Reversion Exit**: Z crosses back to 0.  
   - Long position: exit when `Z_t ≥ 0`  
   - Short position: exit when `Z_t ≤ 0`  
   Exit reason: `"MEAN_REV"`

No stop-loss — the half-life timeout and EOD square-off are the only risk controls. This is intentional: a stop-loss on a mean-reverting spread would exit precisely when the pair is most likely to snap back.

### 4.3 Capital & Position Sizing

```python
base_capital = 10_000.0          # INR, fixed per pair (does not compound)
leverage      = 5.0               # 5x MIS intraday margin
pos_size      = base_capital * leverage   # = 50,000 INR
qty = int(pos_size // price_of_lagger)   # whole shares only
```

Capital is **fixed and isolated per pair** — each pair is evaluated independently at ₹10,000 base. This makes performance metrics directly comparable across pairs.

### 4.4 Fee Model

A simplified friction model of **0.05% per leg** (entry + exit) captures brokerage, STT, exchange charges, and slippage collectively:

```python
friction_pct = 0.0005   # 0.05% per leg

# Entry friction (subtracted from cash at entry):
cash -= (qty * entry_price) * friction_pct

# Exit gross P&L:
gross_pnl = (exit_price - entry_price) * qty   # LONG
gross_pnl = (entry_price - exit_price) * qty   # SHORT

# Exit friction:
net_pnl = gross_pnl - (qty * exit_price) * friction_pct
```

---

## 5. Backtest Results (500 Pairs — 7500-bar Z-Score)

| Method | Net PnL (500 pairs) | Profitable Pairs | Trades | PnL/Trade |
|---|---|---|---|---|
| Kalman: Fixed Speed-Limit (τ=120 min) | −₹41,56,689 | 54 | 94,492 | −₹43.99 |
| Kalman: Dominant Regime | −₹15,40,224 | 138 | 29,673 | −₹51.91 |
| **Kalman: Worst-Case** | **−₹12,87,723** | **168** | **24,526** | −₹52.50 |
| Continuous OLS (7500-bar) | −₹4,09,911 | 228 | 10,164 | −₹40.33 |
| **Continuous OLS + ADF filter** | **+₹54,937** | **185/358** | 7,136 | **+₹7.70** |

> See [[stage3b-continuous-ols]] and [[stage1b-cointegration]] for OLS details.

> **Kalman Worst-Case profitable pairs only**: 168 pairs → +₹6,29,847 total → **₹70.29/trade** net of friction.

---

## 6. Per-Pair Output Metrics

| Metric | Definition |
|---|---|
| `total_trades` | Completed round-trip trades |
| `win_rate_pct` | % of trades with net_pnl > 0 |
| `total_gross_pnl` | Σ gross P&L |
| `total_net_pnl` | Σ net P&L (after fees) |
| `total_fees_paid` | Σ friction costs |
| `avg_trade_duration` | Mean bars held per trade |
| `n_exits_eod` | Trades cut short by 15:15 |
| `n_exits_mean_rev` | Trades that fully mean-reverted |
| `lagging_asset` | The asset traded |

---

## Connections

- [[pairs-trading-strategy]]
- [[stage1b-cointegration]]
- [[stage2-ou-calibration]]
- [[stage1-pearson-screening]]
- [[continuous-ols-execution]]
- [[QC-decisions-pairs-trading]]
- [[kaggle-notebook-run]]
- [[master-data-1min-dataset]]
- [[backtest-record-pairs-trading]]
