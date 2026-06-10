# Technical Instructions for Master_Pairs_Trading_Soul.ipynb

You are tasked with implementing the final, production-ready Kaggle notebook `Master_Pairs_Trading_Soul.ipynb` under `/storage/emulated/0/Quant/LLM-WIKI/Soul/`.
You must strictly follow all mathematical formulations and structural requirements outlined below.

## 1. Setup & Path Discovery (Cell 0)
- Write a path-discovery cell to find `Master-Data-1min.sqlite` under `/kaggle/input/` dynamically.
- Import standard libraries: `pandas`, `numpy`, `sqlite3`, `scipy`, `statsmodels`, `gc`, `os`, `glob`, `multiprocessing`, `joblib`.
- Set thread environment variables before importing numpy:
  ```python
  import os
  os.environ["OPENBLAS_NUM_THREADS"] = "1"
  os.environ["OMP_NUM_THREADS"] = "1"
  os.environ["MKL_NUM_THREADS"] = "1"
  import numpy as np
  ```

## 2. Ingestion & Timezone Formatting
- Load all prices from the database.
- Explicitly restrict to NSE trading hours: **09:15 to 15:29 IST** inclusive.
- Convert timestamps to datetime and filter out weekends, pre-market, and post-market.

## 3. Stage 1 — Pearson Correlation Screening
- **Smart Alignment**:
  - Pivot close prices to a `(timestamp x symbol)` matrix.
  - Drop symbols with coverage < 80% to protect the inner join from collapsing the dataset.
  - Forward-fill remaining price gaps by at most 1 bar: `price_matrix = price_matrix.ffill(limit=1)`.
  - Drop rows with remaining NaNs (inner join).
  - Verify that the aligned price matrix has at least 5,000 bars.
- **Return Calculation**:
  - Calculate log-returns: $r_t = \ln(P_t / P_{t-1})$ individually.
  - Mask the overnight returns: identify 09:15 open bars and set their return to NaN.
- **Correlation**:
  - Compute the Pearson correlation matrix using GPU (cuDF) if available, with a standard CPU NumPy fallback.
  - For each pair, calculate the t-statistic:
    $$t = \rho \sqrt{\frac{n - 2}{1 - \rho^2}}$$
    and the p-value using the t-distribution.
  - Select pairs with p-value < 0.05 and $n\_obs \ge 5000$.
  - Rank by correlation, output the top 500 pairs to `pairs_top500.csv` and all pairs to `pairs_all.csv`.

## 4. IS/OOS Data Split
- Slices the data into In-Sample (IS - first 70% of aligned price series) and Out-of-Sample (OOS - final 30% of aligned price series).
- Let $T$ be the total length of the aligned price matrix.
- $T_{is} = \text{int}(0.7 \times T)$.
- All parameter calibration (Stage 2) and optimization (Stage 3A) must run strictly on the IS period (`0` to $T_{is}$).
- Out-of-sample backtest (Stage 3B) must run on the OOS period ($T_{is}$ to $T$).

## 5. Stage 2 — Kalman Filter & EM Calibration (In-Sample Only)
- For the top 500 pairs, run the EM algorithm to estimate diagonal $Q$ and scalar $R$ on the IS data.
- **Initial state covariance $P_0$ fix**:
  - Run OLS on the first 390 bars (1 trading day) of the IS period: $y_t = \beta x_t + \alpha$.
  - Initialize the state vector $\theta_{0|0} = [\beta_{OLS}, \alpha_{OLS}]^\top$.
  - Compute $P_{0|0} = 10 \cdot \sigma^2 \cdot (X_{OLS}^\top X_{OLS})^{-1}$, where $\sigma^2$ is the OLS residual variance.
- **Overnight Process Noise Scaling**:
  - Define `is_new_day` as a boolean mask where the bar time is 09:15.
  - In the Kalman Filter predict step, if `is_new_day[t]` is True, propagate covariance as:
    $$P_{t|t-1} = P_{t-1|t-1} + Q_{\text{overnight}}$$
    where $Q_{\text{overnight}} = 15.0 \cdot Q$. Otherwise, use $P_{t|t-1} = P_{t-1|t-1} + Q$.
- **Complete EM M-step $Q$ updates**:
  - The process noise covariance updates must compute all cross-covariance terms.
  - In the M-step, compute:
    $$Q_{\text{correct}, t} = (P_{t|T} + \hat{\theta}_{t|T}\hat{\theta}_{t|T}^\top) + (P_{t-1|T} + \hat{\theta}_{t-1|T}\hat{\theta}_{t-1|T}^\top) - (P_{t, t-1|T} + \hat{\theta}_{t|T}\hat{\theta}_{t-1|T}^\top) - (P_{t, t-1|T}^\top + \hat{\theta}_{t-1|T}\hat{\theta}_{t|T}^\top)$$
  - Scale the overnight transition terms:
    $$Q_{\text{weighted}, t} = Q_{\text{correct}, t} / 15.0 \quad \text{if } is\_new\_day[t], \quad \text{else } Q_{\text{correct}, t}$$
  - Compute the new $Q$ as the mean of $Q_{\text{weighted}, t}$ over $t = 1 \dots T_{is}$.
  - Force symmetry and diagonalize: `Q_new = np.diag(np.diag((Q_new + Q_new.T)/2))`.
  - Regularize: `Q_new = np.clip(Q_new, 1e-12, None)`.
- **OU Fitting & Stability Guards**:
  - Fit the smoothed spread to an AR(1) model.
  - If the AR(1) coefficient $\phi \le 0.0$ or $\phi \ge 1.0$ or is non-finite, reject the pair (set parameter values to NaN).
  - Compute $\kappa = -\ln(\phi) / \Delta t$ and half-life $t_{1/2} = \ln(2) / \kappa$.
- **ADF Stationarity Filter**:
  - Run the ADF test on the unsmoothed Kalman innovation series $e_t$ or on the spread computed using final fixed $\beta_{mean}$ and $\alpha_{mean}$ (not dynamically-smoothed state spreads).
  - Keep pairs that pass ADF test p-value < 0.05 and half-life $5.0 \le t_{1/2} \le 120.0$.
  - Output results to `pairs_stage2_kalman_ou.csv`.

## 6. Stage 3A — In-Sample Optimization Grid Search
- Pre-compute the Kalman Z-score series $z_t = e_t / \sqrt{S_t}$ over the IS period for all valid pairs.
- Run a grid search optimization sweep:
  - $Z$-entry trigger: $2.0, 2.5, 3.0, ..., 15.0$
  - Stop Loss: (a) "Half-life time negative" exit (if gross PnL is negative at exactly $\text{ceil}(t_{1/2})$ bars since entry, exit immediately and suspend), (b) $Z_{sl} = 2.5, 3.0, 3.5, ..., 16.0$ (exit if $|Z| \ge Z_{sl}$), or (c) no stop loss (exit at 15:28).
  - Post-SL Freeze logic: If stopped out by SL, suspend further entries until $|Z| < Z_{\text{entry}} / 2$.
  - Mean reversion exit: Exit when $Z$ crosses $0.0$.
  - Force exit at 15:28 IST (no overnight positions).
  - Maximize gross points profit and trade count on the lagging asset (trading lagger only, no fees).
- Optimize by JIT-compiling the backtest loop using Numba for maximum speed.
- Save the best parameter set per pair to `pairs_stage3a_optimized.csv`.

## 7. Stage 3B — Out-of-Sample Backtesting
- For the optimized configurations, run the out-of-sample backtest on the OOS period ($T_{is}$ to $T$).
- Use the optimal $Z_{\text{entry}}$ and Stop Loss parameters found in Stage 3A.
- **Strict single-sided lagger trading**: trade only the lagging asset (buy if spread underpriced and lagging asset is B, short if B is lagger and spread is overpriced, etc. Position size is ₹50,000 representing ₹10k base and 5x leverage).
- **Execution delay**: delay trade entry/exit by 1 bar (enter/exit on the open price of the bar following the signal).
- **Transaction cost and slippage**:
  - Apply 0.05% slippage of the execution price on entry and exit.
  - Apply full Zerodha MIS fee schedule: Brokerage (flat Rs 20 per order leg), STT (0.025% on sell side), Exchange charges (0.00345% on total turnover), GST (18% on brokerage + exchange charges), SEBI charges (Rs 10/crore), Stamp duty (0.003% buy side).
- Output final results to `pairs_stage3b_backtest.csv`.

## 8. Dataset Publishing (In-Notebook)
- Copy all output CSVs (`pairs_all.csv`, `pairs_top500.csv`, `pairs_stage2_kalman_ou.csv`, `pairs_stage3a_optimized.csv`, `pairs_stage3b_backtest.csv`) to `/kaggle/working/dataset_export/`.
- Generate `dataset-metadata.json` with title "Master Pairs Trading Soul Results" and ID `utkarshpatelthefirst/master-pairs-trading-soul-results`.
- Use the Kaggle API inside the notebook to publish or update the dataset.

Execute this flow, verify the output notebook runs end-to-end, and send a message back to me with the Kaggle URL.
