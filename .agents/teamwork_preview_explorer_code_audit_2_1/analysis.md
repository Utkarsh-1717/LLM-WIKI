# Rigorous Static Code and Quantitative Audit Report
**File Audited:** `/storage/emulated/0/Quant/LLM-WIKI/Soul/Master_Pairs_Trading_Soul.ipynb`
**Date:** 2026-06-05

## Executive Summary
This report summarizes the static code and quantitative audit of the Jupyter Notebook `Master_Pairs_Trading_Soul.ipynb`. The audit focused on compliance with mathematical formulations, data alignment integrity, Kalman Filter & EM convergence details, numerical stability, and statistics exporting.

Four key issues were identified:
1. **P0 State Covariance Initialization Bug:** The state covariance matrix $P_0$ is hardcoded to a scaled identity matrix (`np.eye(2) * 1e-3`), completely ignoring the OLS parameter covariance calculations (`sigma2` and `XtX_inv`) computed in the same block.
2. **Open Price Incomplete Alignment & NaN Risk:** The Stage 1 smart alignment drops NaNs only from the close price matrix and index-aligns the open price matrix without verifying it is free of NaNs. This introduces a risk of NaNs propagating into the backtest.
3. **Missing Grid Search Stats Exporting:** The grid search optimization in Stage 3A calculates detailed trade stats (exit counts and average profit/loss in points) via `run_backtest_numba` but fails to append them to `optimized_rows` or export them to `pairs_stage3a_optimized.csv`.
4. **OU Fitting Boundary Stability:** While the AR(1) parameter $\phi$ is checked to be within $0.0 < \phi < 1.0$, it is not bounded away from the limits, which can cause mathematical instability (e.g. division by zero or exploding half-life) when $\phi$ is extremely close to 1.0.

---

## Detailed Findings

### 1. Data Ingestion & Alignment
* **Requirement:** 2-pass smart alignment: (a) pivot open/close prices, (b) drop symbols with < 80% coverage, (c) forward-fill remaining gaps by at most 1 bar first, (d) then execute the inner join (`dropna(how='any')`).
* **Direct Observations:**
  * **Pivoting & Drop Coverage:** Correctly done at lines 96-108.
  * **Forward Fill:** Correctly implemented with `limit=1` on both open and close matrices at lines 111-112.
  * **Inner Join:** The inner join is executed as follows (lines 115-117):
    ```python
    price_matrix_close = price_matrix_close.dropna(how='any', axis=0)
    common_idx = price_matrix_close.index
    price_matrix_open = price_matrix_open.loc[common_idx]
    ```
* **Bugs & Deviations:**
  * **Open Price NaN Risk:** By calling `dropna` only on `price_matrix_close` and then slicing `price_matrix_open.loc[common_idx]`, there is no guarantee that `price_matrix_open` contains no NaNs. If a survivor asset has a missing open price at a bar where its close price is present, it will pass the close-price `dropna` but remain a NaN in the open-price cache, corrupting the backtest.
* **Proposed Code Modification:**
  Modify lines 115-117 in cell `[ca17c2f1]` (Stage 1):
  ```python
  # Pass 2: Inner join on survivors (drop timestamps missing ANY survivor's close or open price)
  price_matrix_close = price_matrix_close.dropna(how='any', axis=0)
  price_matrix_open = price_matrix_open.dropna(how='any', axis=0)
  common_idx = price_matrix_close.index.intersection(price_matrix_open.index)
  price_matrix_close = price_matrix_close.loc[common_idx]
  price_matrix_open = price_matrix_open.loc[common_idx]
  ```

---

### 2. Kalman Filter & EM Update
* **Requirement:** Verify the state covariance $P_0$ initialization in `kalman_smoother_scaled`. It must use the OLS estimator parameter covariance scaled for uncertainty (e.g. `sigma2 * XtX_inv * 10.0`), NOT a hardcoded identity. Verify the EM M-step process noise covariance matrix $Q$ vectorized update (all terms present, correct EM formulation, properly scaled across overnight gaps).
* **Direct Observations:**
  * **P0 Initialization (Lines 444-458):**
    ```python
    n_i = min(390, T // 4)
    Xols = np.column_stack([yb[:n_i], np.ones(n_i)])
    th0, _, _, _ = np.linalg.lstsq(Xols, ya[:n_i], rcond=None)
    resid = ya[:n_i] - Xols @ th0
    sigma2 = np.var(resid)
    XtX_inv = np.linalg.inv(Xols.T @ Xols)
    P0 = np.eye(2) * 1e-3
    ```
  * **EM Q Vectorized Update (Lines 531-545 and 650-664):**
    ```python
    Q_correct = (Ps_t + t_t_t) + (Ps_tm1 + t_tm1_tm1) - (Pc_t_tm1 + t_t_tm1) - (Pc[:T-1] + t_tm1_t)
    Q_weighted = Q_correct.copy()
    for i in range(T - 1):
        if is_new_day[i + 1]:
            Q_weighted[i] = Q_correct[i] / 15.0
    Q_n = np.mean(Q_weighted, axis=0)
    ```
* **Bugs & Deviations:**
  * **P0 Initialization Bug:** The code calculates the OLS parameter covariance terms `sigma2` and `XtX_inv` but ignores them, hardcoding `P0` to `np.eye(2) * 1e-3`. This is a direct mathematical deviation.
  * **EM Q Update Compliance:** The vectorized code for `Q_correct` is mathematically correct. It includes all covariance and mean outer-product terms. The overnight gap scaling (division by 15.0) is mathematically sound because the variance propagates as $Q \Delta t$, requiring division by the gap size ($\Delta t = 15$) during the M-step optimization.
  * **Code Quality Issue:** The `em_kalman_scaled` function is defined twice in the same cell (Lines 470-577 and Lines 589-697). The duplicate code should be removed.
* **Proposed Code Modification:**
  Modify line 458 of the notebook (in `kalman_smoother_scaled` function):
  ```python
  P0 = sigma2 * XtX_inv * 10.0
  ```

---

### 3. OU Fitting Block
* **Requirement:** Verify if the AR(1) phi mapping in the OU fitting block rejects values <= 0.0 or >= 1.0, and bounds them properly for numerical stability.
* **Direct Observations (Lines 732-738):**
  ```python
  c, phi = float(b[0]), float(b[1])
  
  if not (0.0 < phi < 1.0) or not np.isfinite(phi):
      return _nan()
  ```
* **Bugs & Deviations:**
  * **Numerical Stability Bounding:** While the code rejects $\phi \le 0$ or $\phi \ge 1$, it does not bound them away from the boundaries. When $\phi$ is extremely close to 1 (e.g. `0.9999999`), $1 - \phi^2$ approaches zero, causing division-by-zero or numeric overflow when computing `sig_ou = np.std(resid) * np.sqrt(-2.0 * np.log(phi) / (1.0 - phi**2))`, and resulting in extreme half-life values `hl = np.log(2.0) / kappa`.
* **Proposed Code Modification:**
  Modify lines 736-738 in `fit_ou_scaled` to enforce a numerical safety margin:
  ```python
  if not (1e-5 < phi < 1.0 - 1e-5) or not np.isfinite(phi):
      return _nan()
  ```

---

### 4. Stage 3A Optimization Filter
* **Requirement:** Verify if Stage 3A is processing all 500 pairs (dropping the `tradeable == True` filter).
* **Direct Observations (Lines 948-950):**
  ```python
  s2_results = pd.read_csv('pairs_stage2_kalman_ou.csv')
  valid_pairs = s2_results[s2_results['skipped'] == False].copy().reset_index(drop=True)
  ```
* **Assessment:**
  The code is compliant. It does not apply `tradeable == True` filtering in Stage 3A, meaning all calibrated (non-skipped) pairs are optimized.

---

### 5. Detailed Statistics Exporting
* **Requirement:** Verify if `run_backtest_numba` correctly calculates the detailed stats (`avg_points_profit`, `avg_points_loss`, `exit_mr_count`, `exit_sl_count`, `exit_hl_count`, `exit_session_count`), and if they are appended to `optimized_rows` and exported to `pairs_stage3a_optimized.csv`.
* **Direct Observations:**
  * **Calculation:** The stats are correctly calculated and returned by `run_backtest_numba` at lines 1053-1056.
  * **Grid Search Mapping:** The statistics are correctly unpacked into `best_stats` during grid search (lines 1139-1162).
  * **Export Omission (Lines 1165-1185):**
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
* **Bugs & Deviations:**
  * **Missing Export Columns:** The detailed statistics are completely omitted from the appended dictionary. Consequently, they are missing from `pairs_stage3a_optimized.csv`.
* **Proposed Code Modification:**
  Modify the `optimized_rows.append` block (lines 1165-1185) to:
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
      "exit_mr_count": int(best_stats[0]),
      "exit_sl_count": int(best_stats[1]),
      "exit_hl_count": int(best_stats[2]),
      "exit_session_count": int(best_stats[3]),
      "avg_points_profit": float(best_stats[4]),
      "avg_points_loss": float(best_stats[5]),
      "lagger": lagger,
  })
  ```

---

## Verification Method
To verify the changes and make sure the pipeline runs without error:
1. Run the Stage 1 data preparation cells to confirm the close and open matrices are successfully aligned and have no NaNs.
2. Verify that `P0` matrix in the Kalman smoother matches OLS estimator parameter covariance. For any pair, check that `P0[0,0]` and `P0[1,1]` are proportional to OLS covariance.
3. Validate that fitting OU does not throw NaNs/division errors by checking that `fit_ou_scaled` handles extreme AR(1) phi parameter fits gracefully.
4. Verify the output CSV `pairs_stage3a_optimized.csv` contains all the new columns: `exit_mr_count`, `exit_sl_count`, `exit_hl_count`, `exit_session_count`, `avg_points_profit`, and `avg_points_loss`.
