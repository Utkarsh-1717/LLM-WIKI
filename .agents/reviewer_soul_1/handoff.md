# Handoff Report: `Master_Pairs_Trading_Soul.ipynb` Review

## 1. Observation
We have inspected the notebook at path:
`/storage/emulated/0/Quant/LLM-WIKI/Soul/Master_Pairs_Trading_Soul.ipynb`

Direct observations from the notebook cells:
* **Stage 1 (Alignment and Filtering)**:
  * Drop symbols with < 80% coverage:
    ```python
    coverage = price_matrix_close.notna().sum() / n_total_bars
    sparse_symbols = coverage[coverage < 0.80].index.tolist()
    if sparse_symbols:
        price_matrix_close = price_matrix_close.drop(columns=sparse_symbols)
    ```
  * Forward fill up to 1 bar:
    ```python
    price_matrix_close = price_matrix_close.ffill(limit=1)
    ```
  * Inner join (dropna):
    ```python
    price_matrix_close = price_matrix_close.dropna(how='any', axis=0)
    ```
  * Log-returns and 09:15 masking:
    ```python
    log_returns_raw = np.log(price_matrix_close / price_matrix_close.shift(1))
    session_open_mask = (price_matrix_close.index.time == MARKET_OPEN)
    log_returns_raw[session_open_mask] = np.nan
    log_returns = log_returns_raw.dropna(how='any')
    ```

* **Stage 2 (Kalman Filter & EM Calibration)**:
  * State vector is $\theta_t = [\beta_t, \alpha_t]^\top$.
  * Initial parameter covariance $P_{0|0}$ utilizes the OLS parameters covariance scaled by 10.0:
    ```python
    n_i = min(390, T // 4)
    Xols = np.column_stack([yb[:n_i], np.ones(n_i)])
    th0, _, _, _ = np.linalg.lstsq(Xols, ya[:n_i], rcond=None)
    resid = ya[:n_i] - Xols @ th0
    sigma2 = np.var(resid)
    XtX_inv = np.linalg.inv(Xols.T @ Xols)
    P0 = 10.0 * sigma2 * XtX_inv
    ```
  * Overnight process noise scaling of 15.0x:
    * Predictor step:
      ```python
      if t > 0 and is_new_day[t]:
          qq1 = 15.0 * q1
          qq2 = 15.0 * q2
      else:
          qq1 = q1
          qq2 = q2
      ```
    * EM M-step update weight scaling:
      ```python
      Q_weighted = Q_correct.copy()
      for i in range(T - 1):
          if is_new_day[i + 1]:
              Q_weighted[i] = Q_correct[i] / 15.0
      ```
  * Mathematically complete M-step process noise covariance update:
    ```python
    Q_correct = (Ps_t + t_t_t) + (Ps_tm1 + t_tm1_tm1) - (Pc_t_tm1 + t_t_tm1) - (Pc[:T-1] + t_tm1_t)
    ```
  * OU parameter stability guard:
    ```python
    if not (0.0 < phi < 1.0) or not np.isfinite(phi):
        return _nan()
    ```
  * Stationarity filter run on the unsmoothed spread:
    ```python
    beta_mean = np.mean(ts[:, 0])
    alpha_mean = np.mean(ts[:, 1])
    spread_fixed = ya - (yb * beta_mean + alpha_mean)
    adf = adfuller(spread_fixed, maxlag=20, autolag="AIC", regression="c")
    ```

* **Stage 3A (Optimization Grid Search)**:
  * Sweeps $Z_{\text{entry}}$ from 2.0 to 15.0 in steps of 0.5: `np.arange(2.0, 15.5, 0.5)`.
  * Sweeps Stop Loss:
    * No stop loss (`z_sl = 0.0, hl_stop = False`).
    * Half-life negative exit (`hl_stop = True`), which exits if PnL is negative at `bars_held == hl_bars`.
    * $Z_{sl}$ exits (`z_sl = z_s` for $Z_{sl} > Z_{\text{entry}}$ from `np.arange(2.5, 16.5, 0.5)`).
  * Post-SL freeze logic:
    ```python
    if frozen:
        if abs(z) < z_entry / 2.0:
            frozen = False
    ```
  * Optimization is accelerated with `@njit` decorator on `run_backtest_numba`.

* **Stage 3B (Out-of-Sample Backtesting)**:
  * 1-bar execution delay: Signals are evaluated on the close of bar `t` and executed at the open of `t + 1` (both for entries and exits).
  * Sized to ₹50,000: `qty = int(50000.0 // entry_execution_price)`.
  * Native Kalman variance standardization: Z-score is calculated directly as `e_a / np.sqrt(S_a)`.
  * Trades lagging asset only.
  * Fee deduction: Function `calc_zerodha_mis_fees` correctly computes the complete Zerodha MIS fee schedule (Brokerage flat ₹20/order leg, STT 0.025% on sell, Exchange charges 0.00345%, GST 18%, SEBI ₹10/crore, Stamp duty 0.003% buy).
  * Slippage: 0.05% flat slippage is applied by adjusting the entry execution price up/down by 1.0005/0.9995 and exit price by 0.9995/1.0005 depending on direction.

* **Cell Format Compliance**:
  * The notebook contains 11 cells.
  * Cells strictly alternate: code, markdown, code, markdown, code, markdown, code, markdown, code, markdown, code.
  * Cell IDs are unique 8-character hex strings: `"e44d5671"`, `"a9fb9cf3"`, `"e9cf67b2"`, `"e33cf72b"`, `"ca17c2f1"`, `"e3a1f9a2"`, `"c138afc1"`, `"e4ba2fc1"`, `"c49bf8a2"`, `"e44dcfb1"`, `"e41ba982"`.

* **Dataset Publishing & Credentials**:
  * Correctly hardcodes `KAGGLE_USERNAME` and `KAGGLE_KEY` credentials.
  * Uses `KaggleApi` class and creates or updates a Kaggle dataset.

## 2. Logic Chain
1. By examining Cell 2, we verified that symbols with coverage < 80% are dropped first, followed by forward-filling with limit=1, followed by inner-joining (`dropna`). Log-returns are individually calculated, and overnight return components are set to NaN at 09:15. This satisfies Requirement 1.
2. By examining Cell 4, we verified that the state parameter covariance $P_0$ is initialized via the OLS covariance matrix scale of parameter estimates. The process noise covariance $Q$ is scaled by 15.0x in the predictor step of the Kalman Filter forward pass, and is scaled down by 15.0x in the EM algorithm M-step process noise estimation. The EM M-step contains the full cross-covariance terms and lagged state covariance terms, representing a mathematically complete formulation. Additionally, stability guards rejecting $\phi \le 0$ or $\phi \ge 1$ are implemented in `fit_ou_scaled`. The ADF test is run on the unsmoothed spread constructed using the final fixed parameter averages. This satisfies Requirement 2.
3. By examining Cell 6, we verified that grid search sweeps $Z_{\text{entry}}$ and Stop Loss options (no SL, half-life timeout with negative PnL, and $Z_{sl}$ thresholds). The simulation loops are written in Numba JIT. When an SL or half-life timeout is hit, trading is frozen, and entries are suspended until the Z-score returns to within $|Z| < Z_{\text{entry}}/2$. This satisfies Requirement 3.
4. By examining Cell 8, we verified that the backtest applies 1-bar execution delay (entering/exiting at open of $t+1$ based on signals at close of $t$), is sized to ₹50,000, uses native innovation variance standardization, and trades only the lagging asset. Full slippage of 0.05% and Zerodha MIS fee schedules (including brokerage, STT, exchange charges, GST, SEBI fees, and stamp duties) are deducted. This satisfies Requirement 4.
5. By viewing the raw JSON cell structure, we verified that all 11 cells strictly alternate between code and markdown types, and every cell has a unique 8-character string ID. This satisfies Requirement 5.
6. By examining Cell 10, we verified that the Kaggle username and API key are hardcoded for Kaggle environment execution, and the extension Kaggle API is used to push the dataset. This satisfies Requirement 6.

## 3. Caveats
* **Multiprocessing on Termux**: The parallel processing in Stage 2 utilizes multiprocessing. While designed for Kaggle, running this notebook locally on low-end Termux environments could exceed RAM/resource constraints if not limited.
* **Lookahead Bias**: None found. Signals are generated at bar closes and executed at subsequent bar opens, using only contemporaneous/past pricing data.

## 4. Conclusion
The implementation of `Master_Pairs_Trading_Soul.ipynb` is mathematically complete, syntactically correct, and matches all functional constraints. The verdict is **APPROVE**.

## 5. Verification Method
To independently verify the cell IDs and notebook structure:
1. Open and inspect the file metadata of `/storage/emulated/0/Quant/LLM-WIKI/Soul/Master_Pairs_Trading_Soul.ipynb`.
2. Inspect the cell ID properties and verify they contain unique 8-character strings.
3. Verify that the file `/storage/emulated/0/Quant/LLM-WIKI/.agents/reviewer_soul_1/review_report.md` exists and contains the full review details.
