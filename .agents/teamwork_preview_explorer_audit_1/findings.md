# Pairs Trading QC Audit Report

**Audit Conducted By**: teamwork_preview_explorer  
**Date**: 2026-06-04T15:30:05Z  
**Status**: COMPLETED  
**Scope**: LLM-WIKI Pairs Trading Pipeline (Stages 1, 2, and 3)

---

## 1. Executive Summary

This audit report presents a rigorous quality control (QC) review of the methodology, mathematical formulations, and implementation code of the Pairs Trading pipeline in the LLM-WIKI workspace. The audit spanned all three stages of the pipeline: Pearson correlation screening, Kalman Filter state-space parameter estimation, and the backtesting engine.

Ten (10) critical flaws were identified across the pipeline, including:
- **Lookahead bias** in parameter estimation and exit timeouts.
- **Mathematical/dimensional errors** in the Expectation-Maximization (EM) update formulas.
- **Incorrect cross-covariance** formulas in the Rauch-Tung-Striebel (RTS) smoother.
- **Statistical inconsistencies** in the Z-score calculation.
- **Methodological violations** of market neutrality (single-sided trading in a "pairs" strategy).
- **Execution delays** not captured in signal-execution synchronicity.
- **Data destruction** in timeseries alignment.

Backtest results show that the current implementation leads to **consistent losses across all 41 pairs** (losses up to 200%+ of capital per pair) due to the lack of hedging legs (exposing positions to unhedged market beta) and high transaction fees. 

---

## 2. Explicit Files and Code Reviewed

The following files, plans, and formulas were reviewed in detail:
1. **Stage 1 (Pearson Correlation & Alignment)**:
   - `Plans/stage-1-pairs-trading-pearson-correlation.md` — Time alignment, return calculation, and correlation screening.
2. **Stage 2 (Kalman Filter & OU)**:
   - `Plans/stage-2-pairs-trading-kalman-filter-state-space.md` — State-space transition, measurement equations, RTS smoother, and EM algorithm updates.
   - `Raw/Sources/attachments/stage2-pairs-kalman-ou.log` — Convergence rates, half-life statistics, and parameters.
3. **Stage 3 (Backtesting)**:
   - `Raw/Sources/attachments/stage3_pairs_backtest.ipynb` (specifically Cells 1, 3, 4, 5, 6, 7, 8, 9) — Continuous log-price loader, online Kalman Filter, leader/lagger cross-correlation, Zerodha MIS fee structure, signal generation, and trade execution loop.
   - `Plans/stage-3-pairs-trading-kalman-filter-state-space.md` — Execution rules, position sizing, and capital allocation.
   - `Raw/Sources/attachments/stage3-pairs-backtest.log` — Live run output statistics and final performance.
4. **Risk Controls & Stop Loss**:
   - `scripts/generate_z_stoploss_nb.py` — Stop-loss and baseline recovery logic modifications.

---

## 3. Tracing of the Data Flow

The data flow from ingestion to terminal backtest metrics is mapped below:

```
[Ingestion]
   │  Fyers API Websocket / REST (Intraday 1-Min OHLCV)
   ▼
[SQLite DB: Master-Data-1min.sqlite (ohlcv_1min)]
   │  Query 'close' prices for target tickers (e.g. Nifty 500)
   ▼
[Stage 1: Pearson Correlation Screening]
   │  1. Convert timestamps to 'Asia/Kolkata' timezone & keep 09:15-15:29 IST.
   │  2. Align all tickers via global inner-join (dropna on price matrix).
   │  3. Calculate log-returns: r_t = ln(P_t / P_{t-1}).
   │  4. Null out session-open (09:15) overnight returns.
   │  5. Compute Pearson correlation and filter pairs with p < 0.05.
   │  6. Save top 500 pairs to pairs_top500.csv.
   ▼
[Stage 2: Kalman Filter & OU Parameter Estimation]
   │  1. Load pairs_top500.csv and fetch their session-continuous log-prices.
   │  2. Fit state-space model: y_t = beta_t * x_t + alpha_t + v_t.
   │  3. Estimate optimal Q and R using EM algorithm (RTS Smoother backward pass).
   │  4. Extract smoothed spread series and fit continuous-time OU process via AR(1).
   │  5. Calculate half-life, ADF test, and Hurst exponent.
   │  6. Save results to pairs_stage2_kalman_ou.csv (124 tradeable pairs).
   ▼
[Stage 3: Intraday Backtesting Engine]
   │  1. Load Stage 2 CSV and filter on half-life (5.0 <= HL <= 120.0 minutes -> 41 pairs).
   │  2. Query SQLite DB for pair prices, drop non-market-hours, align pairwise.
   │  3. Warm-up (3,750 bars):
   │       a. Initialize OLS to get beta_0, alpha_0, P_0.
   │       b. Detect leader/lagger using 1-bar lagged cross-correlation.
   │       c. Run online Kalman Filter to prime rolling Z-score deque.
   │  4. Live trading:
   │       a. Run online Kalman Filter (fixed Q/R from Stage 2) to get innovations.
   │       b. Compute Z-score using rolling 10-day mean/std of innovations.
   │       c. Signal Entry: |z| >= 2.0 -> buy/short Lagger asset only (unhedged).
   │       d. Signal Exit: z crosses 0 (reversion), half-life elapsed, or 15:28 market close.
   │  5. Zerodha MIS transaction fee calculation.
   │  6. Save performance metrics to pairs_stage3_backtest.csv ranked by Calmar.
```

---

## 4. Identified Flaws and Proposed Corrections

### Flaw 1: Lookahead Bias in Backtesting Parameters
* **Location**: `Raw/Sources/attachments/stage3_pairs_backtest.ipynb` (Cell 7, line 165: `backtest_pair`), `Plans/stage-3-pairs-trading-kalman-filter-state-space.md` (lines 60-64).
* **Flaw**: The process noise covariance parameters ($Q_{\beta}, Q_{\alpha}$) and measurement noise covariance ($R$) are estimated using the EM algorithm over the *entire* historical dataset in Stage 2. Similarly, the half-life ($t_{1/2}$) used for the exit timeout is calculated from the full-sample AR(1) fit. The Stage 3 backtesting engine loads these parameters to filter the spread and execute trades over the exact same period. This represents a significant lookahead bias because the trading signals and exit rules are based on parameters optimized using future price data.
* **Proposed Mathematical/Logical Correction**: Implement a strictly walk-forward estimation process. Use *only* the warm-up period (first 3,750 bars or 10 trading days) to run the EM algorithm and estimate $Q, R$, and the half-life. Alternatively, use an expanding or rolling window of past data to update these parameters, ensuring that at any bar $t$, only data prior to $t$ is used to estimate the model parameters.

### Flaw 2: Dimensionality and Mathematical Errors in the EM Update Formula for Q
* **Location**: `Plans/stage-2-pairs-trading-kalman-filter-state-space.md` (line 131).
* **Flaw**: The formula for updating the process noise covariance matrix $Q_{new}$ is written as:
  $$Q_{new} = \frac{1}{T} \sum_{t=1}^{T} \left[ P_{t|T} + \hat{\theta}_{t|T}\hat{\theta}_{t|T}^\top - G_{t-1}P_{t|T}\hat{\theta}_{t|T}^\top - \hat{\theta}_{t|T}P_{t|T}G_{t-1}^\top - P_{t,t-1|T} - \hat{\theta}_{t|T}\hat{\theta}_{t-1|T}^\top \right]$$
  This formula contains severe dimensional mismatches:
  - $G_{t-1} P_{t|T} \hat{\theta}_{t|T}^\top$: The product of the 2x2 matrix $G_{t-1} P_{t|T}$ and the 1x2 row vector $\hat{\theta}_{t|T}^\top$ is dimensionally invalid for matrix multiplication.
  - $\hat{\theta}_{t|T} P_{t|T} G_{t-1}^\top$: The product of the 2x1 column vector $\hat{\theta}_{t|T}$ and the 2x2 matrix $P_{t|T} G_{t-1}^\top$ is also dimensionally invalid.
  - Additionally, the formula is missing the terms for $\mathbb{E}[\theta_{t-1}\theta_{t-1}^\top]$ and has incorrect signs for several cross-covariance terms. If implemented literally in code, this would fail with shape errors or compute completely incorrect values.
* **Proposed Mathematical/Logical Correction**: The mathematically correct closed-form update for the transition noise covariance $Q_{new}$ in a random walk parameter model (where $F = I$) is:
  $$Q_{new} = \frac{1}{T} \sum_{t=1}^{T} \left[ (P_{t|T} + \hat{\theta}_{t|T}\hat{\theta}_{t|T}^\top) - (P_{t,t-1|T} + \hat{\theta}_{t|T}\hat{\theta}_{t-1|T}^\top) - (P_{t,t-1|T}^\top + \hat{\theta}_{t-1|T}\hat{\theta}_{t|T}^\top) + (P_{t-1|T} + \hat{\theta}_{t-1|T}\hat{\theta}_{t-1|T}^\top) \right]$$
  where every term is a valid 2x2 matrix and the dimensions are fully consistent.

### Flaw 3: Mathematically Incorrect Cross-Covariance Formula in RTS Smoother
* **Location**: `Plans/stage-2-pairs-trading-kalman-filter-state-space.md` (line 121).
* **Flaw**: The plan simplifies the smoothed cross-covariance between state $\theta_t$ and state $\theta_{t-1}$ to:
  $$P_{t,t-1|T} = G_{t-1} P_{t|T}$$
  This is mathematically incorrect. In a Kalman smoother, the cross-covariance is computed recursively starting from $P_{T,T-1|T} = (I - K_T H_T) P_{T-1|T-1} G_{T-1}^\top$ and moving backward:
  $$P_{t-1,t-2|T} = P_{t-1|t-1} G_{t-2}^\top + G_{t-1} (P_{t,t-1|T} - F P_{t-1|t-1}) G_{t-2}^\top$$
  Using the simplified expression results in incorrect estimates for the cross-covariance, which directly corrupts the update of the process noise covariance $Q_{new}$ in the EM loop.
* **Proposed Mathematical/Logical Correction**: Implement the correct recursive formula for $P_{t,t-1|T}$ starting from $t=T$ backward to $t=2$.

### Flaw 4: Mathematical Inconsistency in Z-Score Calculation
* **Location**: `Raw/Sources/attachments/stage3_pairs_backtest.ipynb` (Cell 7, lines 165-175: rolling Z-score loop).
* **Flaw**: The backtest standardizes the Kalman innovation $e_t$ by calculating a rolling 10-day (3,750 bars) sample standard deviation of $e_t$. This is mathematically inconsistent with the Kalman Filter state-space model, which assumes $e_t \sim \mathcal{N}(0, S_t)$, where $S_t = H_t P_{t|t-1} H_t^\top + R$ is the exact, time-varying conditional variance of the innovation. Standardizing by a rolling sample standard deviation:
  - Assumes homoscedasticity of innovations, which contradicts the model.
  - Introduces a severe lag (10 days) in adapting to volatility changes.
  - Wastes 10 days of data for warm-up that could otherwise be traded.
* **Proposed Mathematical/Logical Correction**: Standardize the innovations using the Kalman Filter's native standard deviation:
  $$z_t = \frac{e_t}{\sqrt{S_t}}$$
  This is the mathematically correct and model-consistent formulation, which requires no rolling window and allows trading to begin as soon as the filter is initialized (after 1 day).

### Flaw 5: Signal-Execution Synchronicity (Execution Lookahead Bias)
* **Location**: `Raw/Sources/attachments/stage3_pairs_backtest.ipynb` (Cell 7, lines 165-175: entry logic).
* **Flaw**: The backtest evaluates the entry condition using the Z-score at bar $i$ (`z_scores[i]`), which is computed using the close price of bar $i$ (`lag_prices[i]`). If the condition is met, it enters the trade at the close price of the *same* bar $i$ (`entry_price = price`). Since the close price of bar $i$ is required to compute the signal `z_scores[i]`, the signal is only known *at the end of bar i*. Entering the trade at the close price of the same bar $i$ assumes zero latency and instant execution, introducing a lookahead bias that artificially inflates performance, as the spread may have already moved.
* **Proposed Mathematical/Logical Correction**: Delay the execution by 1 bar. When a signal is triggered at bar $i$, enter the trade at the open price (or close price) of the subsequent bar $i+1$.

### Flaw 6: Global Inner-Join Data Destruction and Return-Gap Gaps
* **Location**: `Plans/stage-1-pairs-trading-pearson-correlation.md` (lines 147-158), `Plans/stage-2-pairs-trading-kalman-filter-state-space.md` (lines 38-40).
* **Flaw**: Stage 1 aligns the price series by performing a global inner-join across ALL symbols in the universe:
  `price_matrix = price_matrix.dropna(how='any', axis=0)`
  If a single stock has missing data on a particular 1-minute bar, that entire timestamp is dropped for *all* stocks. This is a severe data destruction issue. In the actual execution, ~5,000 bars (more than 10% of the dataset) were discarded globally because of this global inner-join.
  Furthermore, because rows are dropped *before* calculating returns, the subsequent return calculation:
  `log_returns_raw = np.log(price_matrix / price_matrix.shift(1))`
  will calculate returns across the missing data gaps (e.g. from $t$ to $t-2$), which results in multi-minute returns that have higher variance and corrupt the Pearson correlation calculation.
* **Proposed Mathematical/Logical Correction**: 
  - Compute log-returns on each stock's price series individually first.
  - Mask the first bar (09:15) of each day on the individual return series.
  - Perform the alignment by inner-joining the *return* series rather than the price series. This avoids creating "synthetic" returns across missing gaps and isolates the missing data of one stock from corrupting the returns of other stocks.

### Flaw 7: Lack of Market Neutrality (Single-Asset Trading)
* **Location**: `Plans/stage-3-pairs-trading-kalman-filter-state-space.md` (lines 126-135, 153-157), `Raw/Sources/attachments/stage3_pairs_backtest.ipynb` (Cell 7, lines 165-175: position sizing).
* **Flaw**: A standard pairs trading strategy is market-neutral because it trades both assets in the pair simultaneously (long one, short the other) in a proportion determined by the hedge ratio $\beta_t$. The Stage 3 backtesting engine only trades the lagging asset:
  `this_qty = int(CAPITAL // price)`
  `is_long = this_is_long` (on the lagging asset only)
  It does not take any position in the leading asset. This is a major structural flaw for a "pairs trading" strategy, as it is not market-neutral. It exposes the portfolio to the directional market risk (beta) of the lagging asset. If the market moves sharply, the position can suffer large losses that would have been hedged by the leading asset.
* **Proposed Mathematical/Logical Correction**: Implement standard two-sided execution. When entering a trade, take a position of size $Q_{lagger}$ in the lagging asset and a hedging position of size $-\beta_t Q_{lagger}$ (or similar ratio) in the leading asset to achieve market neutrality.

### Flaw 8: Lack of Slippage and Bid-Ask Spread Modeling
* **Location**: `Raw/Sources/attachments/stage3_pairs_backtest.ipynb` (Cell 7, lines 165-175: exit and entry price execution).
* **Flaw**: The backtest assumes execution exactly at the 1-minute close price for both entry and exit:
  `exit_price = price`
  `entry_price = price`
  In real-world execution, transaction slippage and bid-ask spreads are significant costs. Given that the strategy is high-frequency intraday (median half-life ~9 minutes) and transaction fees are already high (~0.5% of capital per trade), the lack of slippage simulation creates a significant upward bias in backtest performance.
* **Proposed Mathematical/Logical Correction**: Include a slippage model. For example, subtract/add a fixed penalty (e.g. 0.05% of price or 1 tick) to the execution price, or use bid/ask prices if available.

### Flaw 9: Time-Scale Mismatch in Kalman Filter Process Noise Covariance
* **Location**: `Plans/stage-2-pairs-trading-kalman-filter-state-space.md` (lines 85-87), `Raw/Sources/attachments/stage3_pairs_backtest.ipynb` (Cell 4, lines 111: `P_pred = P + Q`).
* **Flaw**: The state transition equation assumes $\theta_t = \theta_{t-1} + w_t$ with constant process noise covariance $Q$ for all $t$. However, the time elapsed between `15:29` and `09:15` is 17 hours and 46 minutes (and over 65 hours for weekends), which is over 1,000 times larger than the 1-minute intraday interval. By using a constant $Q$, the filter assumes the parameters drift no more overnight than they do in a single intraday minute. This causes the filter to either under-adjust to overnight price shocks or to over-adjust parameter values at the open, generating noisy states and corrupted spreads.
* **Proposed Mathematical/Logical Correction**: Scale the process noise covariance $Q$ for the overnight transition by the actual elapsed time, or reset the state covariance matrix $P_{t|t-1}$ at the 09:15 bar to a higher uncertainty prior.

### Flaw 10: In-Sample Standard Deviation in Primed Rolling Z-Score
* **Location**: `Raw/Sources/attachments/stage3_pairs_backtest.ipynb` (Cell 7, lines 165-175: rolling Z-score loop).
* **Flaw**: The rolling Z-score window is primed using the warm-up innovations (first 3,750 bars). These innovations were generated using the filter initialized with OLS parameters fit on that exact same window. This makes their variance (`sigma_w`) artificially small because they are in-sample residuals of an OLS fit. Since the rolling Z-score is primed using these warm-up innovations, the Z-score standard deviation at the start of the live phase will be underestimated, causing Z-scores to be artificially inflated and triggering false entry signals at the start of the trading period.
* **Proposed Mathematical/Logical Correction**: Initialize the Kalman filter on a much smaller window (e.g., 375 bars, 1 day) and run it forward *without trading* for the next 9 days, allowing the state covariance and innovations to stabilize to out-of-sample prediction errors before live trading begins.

### Flaw 11: Overnight Return Contamination in Leader/Lagger Detection
* **Location**: `Raw/Sources/attachments/stage3_pairs_backtest.ipynb` (Cell 5, line 129: `detect_lagger`).
* **Flaw**: The `detect_lagger` function computes the cross-correlation on the return series using `np.diff(ln_a)`. This return series contains overnight gap returns (the price change from 15:29 of the previous day to 09:15 of the current day). Because overnight returns have much larger variance than intraday 1-minute returns, these few gap return observations will dominate the cross-correlation calculation, rendering the leader/lagger classification statistically noisy and biased by overnight shocks rather than true intraday lead-lag dynamics.
* **Proposed Mathematical/Logical Correction**: Null out the 09:15 returns from the return series in `detect_lagger` before computing `np.corrcoef`.

---

## 5. Discrepancies and Code-Documentation Gaps

1. **Stationarity Filtering Discrepancy**:
   - In `Plans/stage-2-pairs-trading-kalman-filter-state-space.md`, a pair is defined as "tradeable" only if it passes the Augmented Dickey-Fuller (ADF) test (`adf_pvalue < 0.05`) and the half-life test.
   - In `Raw/Sources/attachments/stage3_pairs_backtest.ipynb` (Cell 2), the filter only selects pairs based on the half-life bounds (`5.0 <= half_life_minutes <= 120.0`), explicitly bypassing the ADF stationarity test:
     ```python
     # Stage 3 filter: HL only (no ADF filter per design spec)
     s3_df = s2_df[
         (s2_df["half_life_minutes"] >= HL_MIN) &
         (s2_df["half_life_minutes"] <= HL_MAX)
     ].copy().reset_index(drop=True)
     ```
     This allows statistically non-stationary pairs (which do not mean-revert) to enter the trading engine, leading to persistent losses.

2. **Numerical Instability in OU Estimation**:
   - In `Plans/stage-2-pairs-trading-kalman-filter-state-space.md`, the mapping uses $\kappa = -\ln(\phi)$.
   - In practice, $\phi$ can be negative due to noise or high-frequency oscillations. If $\phi \le 0$, `np.log(phi)` is mathematically undefined and throws a `ValueError` in Python. There is no code-level guard for this other than a generic catch-all exception, which causes the pair to be skipped entirely rather than handled gracefully.

3. **Stop-Loss Execution Defect in Parameter Sweep Script**:
   - In `scripts/generate_z_stoploss_nb.py`, the exit condition check for the half-life stop-loss is:
     ```python
     elif bars_held == hl_bars:
         if current_gross < 0:
             exit_reason = "hl_stoploss"
             suspended = True
     ```
     If the trade is profitable at `bars_held == hl_bars`, no exit is triggered. On subsequent bars, `bars_held > hl_bars` is true, so the condition `bars_held == hl_bars` is never met again. This means that if a trade is profitable at the half-life timeout, it bypasses the timeout and is held indefinitely (until the session end at 15:28), which violates the strict risk parameter of half-life timeouts.
