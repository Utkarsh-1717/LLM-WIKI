# Plan: Master Pairs Trading Soul Notebook Implementation

## Objective
Develop, run, and verify a consolidated, highly-optimized, memory-efficient Kaggle notebook `Master_Pairs_Trading_Soul.ipynb` that executes the complete Pairs Trading pipeline:
- **Stage 1**: Smart return alignment, timezone filtering, and Pearson correlation screening of log-returns (output top 500 pairs).
- **Stage 2**: Expectation-Maximization (EM) parameter estimation (with complete process noise $Q$ covariance, $P_0$ parameter covariance initialization, and overnight processes noise scaling) and Ornstein-Uhlenbeck (OU) parameter estimation.
- **Stage 3A**: In-sample grid search optimization for $Z$-entry and stop-loss ($Z_{sl}$) with post-SL freeze logic.
- **Stage 3B**: Out-of-sample backtesting with native Kalman innovation variance standardization, single-sided lagger trading, 1-bar execution delay, and realistic transaction cost/slippage models.

## Open Questions (for user review)
- **Kaggle API Credentials**: Checked from `~/.quant_env` (Username: `utkarshpatelthefirst`, Key is active). Will hardcode inside the notebook for dataset/kernel interactions.
- **SQLite Database Path**: Located dynamically in Kaggle under `/kaggle/input/` using glob.
- **Overnight process noise scaling**: We will inject a multiplier of 15.0 to $Q$ for state transition across day boundaries (at 09:15 open) to allow the Kalman filter to adapt to overnight drift without breaking the spread.
- **Initial State Covariance $P_0$**: Will initialize $P_0 = 10 \cdot \sigma^2 \cdot (X^T X)^{-1}$ using the first 390 bars (1 trading day) OLS parameter covariance to ensure intercept $\alpha$ is not locked.
- **Slippage**: We will apply a flat slippage of 0.05% of the asset price on both entry and exit.
- **ADF test selection**: To prevent false stationarity signals from dynamically-smoothed Kalman spreads, the ADF test is run on the unsmoothed innovations or standard residuals.

## Proposed Approach

### Step 1 — Project and Plan Initialization (Worker)
- Worker writes `PROJECT.md` at root and `/storage/emulated/0/Quant/LLM-WIKI/Plans/Master_Pairs_Trading_Soul.md`.

### Step 2 — Develop Notebook Builder Script (Worker)
- Worker writes a Python script `build_soul_notebook.py` that generates `Master_Pairs_Trading_Soul.ipynb`.
- The builder script uses `nbformat` and ensures:
  1. Alternating markdown and code cells.
  2. Each cell has a unique 8-character string `id`.
  3. Cell 0 is a dynamic path-discovery cell.
  4. Memory-efficiency measures: load SQLite once globally, use chunked processing for Stage 2/3, call garbage collection `gc.collect()`, set OpenBLAS and OMP threads to 1, and no pre-compilation before parallel forks.

### Step 3 — Ingest & Stage 1 Implementation (Worker)
- Filter symbols to those with >= 80% coverage to avoid inner join collapsing data.
- Pivot prices, forward-fill microstructure gaps by at most 1 bar, then drop remaining NaNs (inner join).
- Compute log-returns: $r_t = \ln(P_t / P_{t-1})$.
- Null out overnight returns (first bar at 09:15 is set to NaN).
- Run Pearson correlation using GPU (cuDF) with CPU NumPy fallback. Filter to pairs with >= 5,000 observations and statistical significance (t-stat p-value < 0.05). Output top 500 ranked pairs.

### Step 4 — Stage 2 Implementation: Kalman & EM & OU (Worker)
- Run EM algorithm for top 500 pairs.
- Incorporate fixes:
  1. Complete $Q_{new}$ expectation matrix update (all cross terms).
  2. Initial state covariance $P_0$ set to OLS parameter covariance scaled by 10.
  3. Overnight process noise scaling using a multiplier of 15.0 at the 09:15 transition.
  4. OU parameter mapping from AR(1) with stability guards ($0 < \phi < 1$).
  5. ADF test run on unsmoothed innovations (or raw spread using fixed parameter estimates).

### Step 5 — Stage 3A Grid Search Implementation (Worker)
- Sweep $Z$-entry triggers ($2.0, 2.5, ..., 15.0$) and Stop Loss triggers ($Z_{sl} = 2.5, 3.0, ..., 16.0$ or no stop loss).
- If stopped out, wait until $|Z| < \text{entry\_trigger} / 2$ before allowing re-entry (post-SL freeze).
- Optimize gross points profit/loss (no fees/slippage) on the in-sample period.
- Output the single best configuration per pair.

### Step 6 — Stage 3B Out-of-Sample Backtester (Worker)
- Standardize innovations using native Kalman variance: $z_t = e_t / \sqrt{S_t}$.
- Strict single-sided lagger trading: take position only in lagging asset (B), no position in leading asset (A).
- Delay execution by 1 bar: enter on the bar after signal trigger (using open price).
- Deduct full Zerodha MIS fees and 0.05% slippage on entry and exit.

### Step 7 — Run & Verify on Kaggle (Worker & Auditor)
- Create `kernel-metadata.json` with appropriate sources (dataset: `utkarshpatelthefirst/master-data-1min-db`).
- Push notebook using Kaggle API.
- Monitor execution using the `kaggle-pulse-check` skill.
- Once complete, verify that the dataset containing output CSVs is published to Kaggle.
- Run Forensic Auditor to perform static/runtime checks verifying that:
  1. No expected values or outputs are hardcoded.
  2. Implementations are mathematically correct.
  3. Spread calculations and backtest rules are adhered to.

## Time Estimate
- Development: 15-20 mins
- Kaggle Run & Pulse Check: ~20 mins
- Audit & Review: ~10 mins
- Total: ~50 mins

## Connections to Existing Skills
- [[plan-first]]
- [[kaggle-notebook-run]]
- [[kaggle-pulse-check]]
- [[soul-production-compiler]]
