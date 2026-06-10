# Handoff Report: Master Pairs Trading Soul Code Audit

This report presents a rigorous code audit of the Jupyter Notebook `Master_Pairs_Trading_Soul.ipynb` located at `/storage/emulated/0/Quant/LLM-WIKI/Soul/Master_Pairs_Trading_Soul.ipynb`.

## 1. Observation
The following file, lines, and blocks of code were directly observed in `/storage/emulated/0/Quant/LLM-WIKI/Soul/Master_Pairs_Trading_Soul.ipynb`:

### Stage 1 Data Alignment (Lines 114-118)
```python
# Pass 2: Inner join on survivors (drop timestamps missing ANY survivor)
price_matrix_close = price_matrix_close.dropna(how='any', axis=0)
common_idx = price_matrix_close.index
price_matrix_open = price_matrix_open.loc[common_idx]
```

### Stage 2 Kalman Smoother P0 Initialization (Lines 444-458)
```python
# P_0 Initialization: OLS on first 390 bars of In-Sample
n_i = min(390, T // 4)
Xols = np.column_stack([yb[:n_i], np.ones(n_i)])
th0, _, _, _ = np.linalg.lstsq(Xols, ya[:n_i], rcond=None)
resid = ya[:n_i] - Xols @ th0
sigma2 = np.var(resid)
XtX_inv = np.linalg.inv(Xols.T @ Xols)
P0 = np.eye(2) * 1e-3
```

### Stage 2 EM M-step Process Noise Covariance Q Update (Lines 531-545 and duplicated at 650-664)
```python
# Complete M-step Q update
Q_correct = (Ps_t + t_t_t) + (Ps_tm1 + t_tm1_tm1) - (Pc_t_tm1 + t_t_tm1) - (Pc[:T-1] + t_tm1_t)

Q_weighted = Q_correct.copy()
for i in range(T - 1):
    if is_new_day[i + 1]:
        Q_weighted[i] = Q_correct[i] / 15.0
        
Q_n = np.mean(Q_weighted, axis=0)
Q_n = np.diag(np.diag((Q_n + Q_n.T) / 2.0))
Q_n = np.clip(Q_n, 1e-7, None)
```

### Stage 2 OU Fitting Phi Mapping (Lines 732-738)
```python
c, phi = float(b[0]), float(b[1])

if not (0.0 < phi < 1.0) or not np.isfinite(phi):
    return _nan()
```

### Stage 3A Grid Search Optimization Pair Loading (Lines 948-950)
```python
s2_results = pd.read_csv('pairs_stage2_kalman_ou.csv')
valid_pairs = s2_results[s2_results['skipped'] == False].copy().reset_index(drop=True)
print(f"Stage 3A Tradeable Pairs: {len(valid_pairs)}")
```

### Stage 3A Optimization Output Omission (Lines 1165-1185)
```python
optimized_rows.append({
    "symbol_a": sym_a,
    "symbol_b": sym_b,
    "best_z_entry": best_config[0],
    "best_z_sl": best_config[1],
    "best_hl_stop": best_config[2],
    "gross_profit": best_profit,
    "trade_count": best_trade_count,
    "win_rate": best_win_rate,
    "lagger": lagger,
})
```

---

## 2. Logic Chain
- **Stage 1 Alignment NaN Risk:**
  - *Observation:* `price_matrix_close` is dropped for NaNs using `dropna(how='any')`, but `price_matrix_open` is simply indexed using `.loc[common_idx]`.
  - *Reasoning:* If a survivor symbol has an open price NaN (e.g. at the first bar or due to a localized data gap that `ffill(limit=1)` did not cover) but its close price is valid, that timestamp is kept in `common_idx`. Hence, `price_matrix_open` will contain a NaN.
  - *Conclusion:* During backtesting, reading open prices from `price_matrix_open` will yield `NaN`, leading to corrupted execution price/PnL calculations. An inner join must drop NaNs on both matrices and intersect their indexes.

- **P0 Covariance Initialization Bug:**
  - *Observation:* The OLS variance `sigma2` and parameter variance inverse product matrix `XtX_inv` are correctly computed in `kalman_smoother_scaled` but not used. Instead, `P0` is initialized to the hardcoded identity matrix `np.eye(2) * 1e-3`.
  - *Reasoning:* This contradicts the required implementation mathematical specifications, which state that $P_0$ should be initialized to the OLS estimator parameter covariance scaled for uncertainty (e.g. `sigma2 * XtX_inv * 10.0`).
  - *Conclusion:* The initialization of `P0` must be changed from `np.eye(2) * 1e-3` to `sigma2 * XtX_inv * 10.0`.

- **EM Q Vectorized Update:**
  - *Observation:* The calculation of `Q_correct` is `(Ps_t + t_t_t) + (Ps_tm1 + t_tm1_tm1) - (Pc_t_tm1 + t_t_tm1) - (Pc[:T-1] + t_tm1_t)`.
  - *Reasoning:* Expanded expected values $E[(x_t - x_{t-1})(x_t - x_{t-1})^T]$ equal $P_{t|T} + \hat{\theta}_{t|T}\hat{\theta}_{t|T}^\top + P_{t-1|T} + \hat{\theta}_{t-1|T}\hat{\theta}_{t-1|T}^\top - (P_{t, t-1|T} + \hat{\theta}_{t|T}\hat{\theta}_{t-1|T}^\top) - (P_{t-1, t|T} + \hat{\theta}_{t-1|T}\hat{\theta}_{t|T}^\top)$. This is mathematically equivalent. The division of `Q_correct[i]` by 15.0 when `is_new_day[i+1]` is true correctly handles overnight gaps by dividing the transition variance contribution by the gap duration.
  - *Conclusion:* The M-step process noise covariance update is mathematically sound and correct.

- **OU Fitting Stability Bounding:**
  - *Observation:* The check `0.0 < phi < 1.0` ensures the parameter $\phi$ is stable, but does not bound it away from the limits.
  - *Reasoning:* If $\phi$ is extremely close to 1.0 (e.g., $1.0 - 1e-15$), the term $1 - \phi^2$ will be zero or extremely close to it in float64 precision. This causes division-by-zero errors in the calculation of `sig_ou` or yields unstable half-lives.
  - *Conclusion:* The parameter $\phi$ should be restricted to a tighter range such as `1e-5 < phi < 1.0 - 1e-5` to ensure numerical stability.

- **Stage 3A Filter Verification:**
  - *Observation:* The rows loaded in Stage 3A are filtered with `skipped == False` only.
  - *Reasoning:* No `tradeable == True` filter is applied, which means all 500 pairs that survived calibration are optimized.
  - *Conclusion:* This correctly matches the directive to process all 500 pairs.

- **Missing Detailed Statistics Export:**
  - *Observation:* `run_backtest_numba` correctly returns the detailed statistics. However, they are completely omitted in the dictionary appended to `optimized_rows`.
  - *Reasoning:* Because they are not in the dictionary, they are not exported to `pairs_stage3a_optimized.csv`.
  - *Conclusion:* The keys `exit_mr_count`, `exit_sl_count`, `exit_hl_count`, `exit_session_count`, `avg_points_profit`, and `avg_points_loss` must be added to the dictionary.

---

## 3. Caveats
- **No Kaggle Execution:** This is a read-only code audit. Actual notebook execution was not performed, but the code structure was audited with high mathematical rigor.
- **Assumed Data Integrity:** The audit assumes the original source SQLite database `ohlcv_1min` contains standard timestamped pricing.

---

## 4. Conclusion
The notebook contains three critical mathematical/logic bugs and one numerical stability issue:
1. Hardcoded state covariance matrix $P_0$ (violating OLS covariance initialization).
2. Unaligned open price matrix (inducing NaN risk in backtesting).
3. Omitted detailed backtesting statistics in the output CSV `pairs_stage3a_optimized.csv`.
4. Lack of safety margin bounding for the AR(1) phi parameter.

Applying the proposed code modifications will bring the codebase in full compliance with the quantitative design specifications.

---

## 5. Verification Method
Verify correct execution and column compliance by checking:
1. Output file `pairs_stage3a_optimized.csv` contains all the new columns: `exit_mr_count`, `exit_sl_count`, `exit_hl_count`, `exit_session_count`, `avg_points_profit`, and `avg_points_loss`.
2. Inspect values of `P0` during execution to confirm they change dynamically per pair based on OLS fit rather than staying constant at `1e-3 * I`.
3. Check `price_matrix_open.isnull().sum().sum()` is exactly 0 after Stage 1 alignment.
