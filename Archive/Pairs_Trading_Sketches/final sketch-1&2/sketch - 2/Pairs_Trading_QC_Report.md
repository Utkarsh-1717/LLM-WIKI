> [!WARNING]
> **ARCHIVED & OBSOLETE**
> This file is part of the trial-and-error "Sketch" phase. 
> The mathematics and code herein may contain deprecated Expectation-Maximization loops or failed concepts.
> The final, verified truth is located in the `Soul/` directory.
> Tags: #archived-sketch #pairs-trading-prototype

# Pairs Trading Quality Control (QC) Audit Report

**Audit Date**: June 4, 2026  
**Auditor Archetype**: teamwork_preview_orchestrator  
**Reviewers**: teamwork_preview_explorer & teamwork_preview_critic  
**Status**: COMPLETED & VERIFIED  
**Scope**: LLM-WIKI Pairs Trading Pipeline (Stages 1, 2, and 3)

---

## 1. Executive Summary

This Quality Control (QC) Audit Report presents a comprehensive evaluation of the methodology, mathematical formulations, and codebase of the Pairs Trading pipeline in the LLM-WIKI workspace. The objective is to identify mathematical discrepancies, structural flaws, and implementation errors that affect the validity of the backtest results and the theoretical integrity of the strategy.

Eleven (11) critical flaws have been identified, verified, and mathematically refined across all stages of the pipeline. These include lookahead biases in parameter calibration, matrix dimensional errors in the Expectation-Maximization (EM) equations, recursive errors in the Rauch-Tung-Striebel (RTS) smoother, statistical inconsistencies in the standardization of Kalman innovations, and a severe deviation from market neutrality (single-sided trading). 

These flaws explain the persistent losses documented in the backtesting logs. For instance, the backtest results show significant losses across all 41 pairs (up to 200%+ of capital per pair) due to the lack of hedging legs (leaving the portfolio exposed to unhedged market beta) and high transaction fees. Implementing the corrections proposed in this report is required to achieve statistical correctness and real-world viability.

---

## 2. Explicit Files and Code Reviewed

The audit team reviewed the following files, plans, notebooks, and source code:
1. **Stage 1: Pearson Correlation & Alignment**:
   - `Plans/stage-1-pairs-trading-pearson-correlation.md`: Methodology for data alignment, log-return calculations, and Pearson correlation screening.
   - `Raw/Sources/Stage 1, Scale Invariant Data.md`: Mathematical principles for return computation and alignment.
2. **Stage 2: Kalman Filter & OU Parameter Estimation**:
   - `Plans/stage-2-pairs-trading-kalman-filter-state-space.md`: Mathematical formulations for state-space transition, measurement updates, RTS smoother, and EM parameter updates.
   - `Raw/Sources/attachments/qt.py`: Python code containing state transition logic, covariance propagation, and parameter estimation.
   - `Raw/Sources/attachments/stage2-pairs-kalman-ou.log`: Execution statistics, convergence rates, and parameter estimation outputs.
3. **Stage 3: Intraday Backtesting Engine & Execution**:
   - `Plans/stage-3-pairs-trading-kalman-filter-state-space.md`: Portfolio sizing, exit timeouts, transaction fees, and execution logic.
   - `Raw/Sources/attachments/stage3_pairs_backtest.ipynb` (specifically Cells 1, 3, 4, 5, 6, 7, 8, 9): Database queries, online Kalman filter loops, leader/lagger cross-correlation, Zerodha MIS fees, and signal generation.
   - `Raw/Sources/attachments/stage3-pairs-backtest.log`: Execution output logs showing loss profiles.
4. **Risk Controls & Parameter Sweeps**:
   - `scripts/generate_z_stoploss_nb.py`: Logic modifications for stop-loss and baseline recovery.

---

## 3. Tracing of the Data Flow

The flow of data from raw ingestion to backtest performance reporting is traced below:

```
[Data Ingestion]
   │  Fyers API WebSocket / REST (Intraday 1-Min OHLCV)
   ▼
[SQLite Database: Master-Data-1min.sqlite (table: ohlcv_1min)]
   │  Query 'close' prices for target tickers (e.g. Nifty 500 futures)
   ▼
[Stage 1: Pearson Correlation Screening]
   │  1. Localize timestamps to 'Asia/Kolkata' timezone (09:15-15:29 IST).
   │  2. Align all tickers via global inner-join (dropna on price matrix).
   │  3. Calculate log-returns: r_t = ln(P_t / P_{t-1}).
   │  4. Null out session-open (09:15) returns to eliminate overnight gaps.
   │  5. Compute Pearson correlation and filter pairs (p < 0.05).
   │  6. Output top 500 pairs to 'pairs_top500.csv'.
   ▼
[Stage 2: Kalman Filter & OU Parameter Estimation]
   │  1. Load 'pairs_top500.csv' and fetch session-continuous log-prices.
   │  2. Fit state-space model: y_t = beta_t * x_t + alpha_t + v_t.
   │  3. Run EM algorithm via RTS Smoother backward pass to estimate Q (process noise) and R (measurement noise).
   │  4. Extract smoothed spread and fit continuous-time OU process via AR(1).
   │  5. Calculate half-life, ADF statistic, and Hurst exponent.
   │  6. Output tradeable pairs (124 pairs) to 'pairs_stage2_kalman_ou.csv'.
   ▼
[Stage 3: Intraday Backtesting Engine]
   │  1. Filter pairs on half-life (5.0 <= HL <= 120.0 minutes) to yield 41 active pairs.
   │  2. Fetch intraday prices from SQLite, align pairwise, and restrict to market hours.
   │  3. Warm-up Period (3,750 bars):
   │       a. Initialize parameters (beta_0, alpha_0) using static OLS.
   │       b. Determine leader/lagger via 1-bar lagged cross-correlation.
   │       c. Run online Kalman Filter to prime the rolling Z-score deque.
   │  4. Trading Phase:
   │       a. Update online Kalman Filter (fixed Q, R from Stage 2) to get innovations e_t.
   │       b. Standardize innovations using rolling 10-day mean and std.
   │       c. Trigger entry: |z_t| >= 2.0 -> trade the Lagger asset (unhedged).
   │       d. Trigger exit: z_t crosses 0, half-life timeout, or session end (15:28).
   │  5. Deduct fees using the Zerodha MIS transaction fee schedule.
   │  6. Save output performance metrics to 'pairs_stage3_backtest.csv'.
```

---

## 4. Identified Flaws and Proposed Corrections

### Flaw 1: Lookahead Bias in Backtesting Parameters
* **Location**: `Raw/Sources/attachments/stage3_pairs_backtest.ipynb` (Cell 7, line 165) & `Plans/stage-3-pairs-trading-kalman-filter-state-space.md` (lines 60-64).
* **Flaw**: The process noise covariance parameters ($Q_{\beta}, Q_{\alpha}$) and measurement noise covariance ($R$) are estimated using the EM algorithm over the *entire* historical dataset in Stage 2. Similarly, the half-life ($t_{1/2}$) used for the exit timeout is calculated from the full-sample AR(1) fit. The Stage 3 backtesting engine loads these parameters to filter the spread and execute trades over the exact same period. This represents a significant lookahead bias because the trading signals and exit rules are based on parameters optimized using future price data.
* **Proposed Mathematical/Logical Correction**: Implement a strictly walk-forward or rolling calibration framework. Since running the EM algorithm at every bar is computationally prohibitive, parameters $\Theta$ should be estimated on a rolling historical window (e.g., 10 to 20 trading days) and updated periodically (e.g., weekly or monthly) out-of-sample.

### Flaw 2: Dimensionality and Mathematical Errors in the EM Update Formula for Q
* **Location**: `Plans/stage-2-pairs-trading-kalman-filter-state-space.md` (line 131).
* **Flaw**: The formula for updating the process noise covariance matrix $Q_{new}$ is written as:
  $$Q_{new} = \frac{1}{T} \sum_{t=1}^{T} \left[ P_{t|T} + \hat{\theta}_{t|T}\hat{\theta}_{t|T}^\top - G_{t-1}P_{t|T}\hat{\theta}_{t|T}^\top - \hat{\theta}_{t|T}P_{t|T}G_{t-1}^\top - P_{t,t-1|T} - \hat{\theta}_{t|T}\hat{\theta}_{t-1|T}^\top \right]$$
  This formula contains severe dimensional mismatches:
  - $G_{t-1} P_{t|T} \hat{\theta}_{t|T}^\top$: The product of the 2x2 matrix $G_{t-1} P_{t|T}$ and the 1x2 row vector $\hat{\theta}_{t|T}^\top$ is dimensionally invalid for matrix multiplication.
  - $\hat{\theta}_{t|T} P_{t|T} G_{t-1}^\top$: The product of the 2x1 column vector $\hat{\theta}_{t|T}$ and the 2x2 matrix $P_{t|T} G_{t-1}^\top$ is also dimensionally invalid.
  - Additionally, the formula is missing the terms for $\mathbb{E}[\theta_{t-1}\theta_{t-1}^\top]$ and has incorrect signs for several cross-covariance terms. If implemented literally in code, this would fail with shape errors or compute completely incorrect values.
* **Proposed Mathematical/Logical Correction**: The mathematically correct closed-form update for the transition noise covariance $Q_{new}$ in a random walk parameter model (where $F = I$) is:
  $$Q_{new} = \frac{1}{T} \sum_{t=1}^T \left[ (P_{t|T} + \hat{\theta}_{t|T} \hat{\theta}_{t|T}^\top) - (P_{t,t-1|T} + \hat{\theta}_{t|T} \hat{\theta}_{t-1|T}^\top) - (P_{t,t-1|T}^\top + \hat{\theta}_{t-1|T} \hat{\theta}_{t|T}^\top) + (P_{t-1|T} + \hat{\theta}_{t-1|T} \hat{\theta}_{t-1|T}^\top) \right]$$
  where every term is a valid 2x2 matrix and the dimensions are fully consistent.
  - **Refinement**: Extract only the diagonal elements to enforce a diagonal process noise structure and prevent cross-drift overfitting:
    $$Q_{new, \text{diag}} = \text{diag}([Q_{new}]_{1,1}, [Q_{new}]_{2,2})$$
  - Enforce a regularization lower bound during updates to prevent filter divergence ($Q_{ii} \to 0$, causing $K_t \to 0$):
    $$[Q_{new}]_{ii} = \max([Q_{new}]_{ii}, \delta)$$
    where $\delta > 0$ is a small threshold (e.g., $10^{-8}$).

### Flaw 3: Mathematically Incorrect Cross-Covariance Formula in RTS Smoother
* **Location**: `Plans/stage-2-pairs-trading-kalman-filter-state-space.md` (line 121).
* **Flaw**: The plan simplifies the smoothed cross-covariance between state $\theta_t$ and state $\theta_{t-1}$ to:
  $$P_{t,t-1|T} = G_{t-1} P_{t|T}$$
  This is mathematically incorrect because it ignores the recursive backward flow of future information.
* **Proposed Mathematical/Logical Correction**: The cross-covariance $P_{t-1,t-2|T} = \text{Cov}(\theta_{t-1}, \theta_{t-2} | y_{1:T})$ must be computed recursively backward from $t = T$ to $2$:
  $$P_{t-1,t-2|T} = P_{t-1|t-1} G_{t-2}^\top + G_{t-1} (P_{t,t-1|T} - F P_{t-1|t-1}) G_{t-2}^\top$$
  For a random walk model ($F = I$), the recursion is:
  $$P_{t-1,t-2|T} = P_{t-1|t-1} G_{t-2}^\top + G_{t-1} (P_{t,t-1|T} - P_{t-1|t-1}) G_{t-2}^\top$$
  initialized at the terminal boundary $t = T$ as:
  $$P_{T,T-1|T} = (I - K_T H_T) P_{T-1|T-1} = P_{T|T} G_{T-1}^\top$$

### Flaw 4: Mathematical Inconsistency in Z-Score Calculation
* **Location**: `Raw/Sources/attachments/stage3_pairs_backtest.ipynb` (Cell 7, lines 165-175).
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
* **Location**: `Plans/stage-1-pairs-trading-pearson-correlation.md` (lines 147-158) & `Plans/stage-2-pairs-trading-kalman-filter-state-space.md` (lines 38-40).
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
* **Location**: `Plans/stage-3-pairs-trading-kalman-filter-state-space.md` (lines 126-135, 153-157) & `Raw/Sources/attachments/stage3_pairs_backtest.ipynb` (Cell 7, lines 165-175: position sizing).
* **Flaw**: A standard pairs trading strategy is market-neutral because it trades both assets in the pair simultaneously (long one, short the other) in a proportion determined by the hedge ratio $\beta_t$. The Stage 3 backtesting engine only trades the lagging asset:
  `this_qty = int(CAPITAL // price)`
  `is_long = this_is_long` (on the lagging asset only)
  It does not take any position in the leading asset. This is a major structural flaw for a "pairs trading" strategy, as it is not market-neutral. It exposes the portfolio to the directional market risk (beta) of the lagging asset. If the market moves sharply, the position can suffer large losses that would have been hedged by the leading asset.
* **Proposed Mathematical/Logical Correction**: Implement standard two-sided execution. When entering a trade, take a position of size $Q_{lagger}$ in the lagging asset and a hedging position of size $Q_{leader}$ in the leading asset.
  - **Hedge Ratio Formulation (Log-Prices)**: Because the spread is modeled on log-prices:
    $$\ln P_{A,t} = \beta_t \ln P_{B,t} + \alpha_t + e_t$$
    the parameter $\beta_t$ represents the price elasticity, not a raw share ratio. The portfolio value change is:
    $$dV_t = Q_A P_{A,t} r_{A,t} + Q_B P_{B,t} r_{B,t} = (Q_A P_{A,t} \beta_t + Q_B P_{B,t}) r_{B,t} + Q_A P_{A,t} u_t$$
    To immunize the portfolio from the directional market return $r_{B,t}$, we must set the coefficient of $r_{B,t}$ to zero:
    $$Q_B = -\beta_t \left( \frac{P_{A,t}}{P_{B,t}} \right) Q_A$$
    If we trade the lagging asset B with size $Q_B$, we must execute the hedging position of size $Q_A$ in the leading asset A as:
    $$Q_A = -\frac{1}{\beta_t} \left( \frac{P_{B,t}}{P_{A,t}} \right) Q_B$$

### Flaw 8: Lack of Slippage and Bid-Ask Spread Modeling
* **Location**: `Raw/Sources/attachments/stage3_pairs_backtest.ipynb` (Cell 7, lines 165-175: exit and entry price execution).
* **Flaw**: The backtest assumes execution exactly at the 1-minute close price for both entry and exit:
  `exit_price = price`
  `entry_price = price`
  In real-world execution, transaction slippage and bid-ask spreads are significant costs. Given that the strategy is high-frequency intraday (median half-life ~9 minutes) and transaction fees are already high (~0.5% of capital per trade), the lack of slippage simulation creates a significant upward bias in backtest performance.
* **Proposed Mathematical/Logical Correction**: Include a slippage model. For example, subtract/add a fixed penalty (e.g. 0.05% of price or 1 tick) to the execution price, or use bid/ask prices if available.

### Flaw 9: Time-Scale Mismatch in Kalman Filter Process Noise Covariance
* **Location**: `Plans/stage-2-pairs-trading-kalman-filter-state-space.md` (lines 85-87) & `Raw/Sources/attachments/stage3_pairs_backtest.ipynb` (Cell 4, lines 111: `P_pred = P + Q`).
* **Flaw**: The state transition equation assumes $\theta_t = \theta_{t-1} + w_t$ with constant process noise covariance $Q$ for all $t$. However, the time elapsed between `15:29` and `09:15` is 17 hours and 46 minutes (and over 65 hours for weekends), which is over 1,000 times larger than the 1-minute intraday interval. By using a constant $Q$, the filter assumes the parameters drift no more overnight than they do in a single intraday minute. This causes the filter to either under-adjust to overnight price shocks or to over-adjust parameter values at the open, generating noisy states and corrupted spreads.
* **Proposed Mathematical/Logical Correction**: Scale the process noise covariance $Q$ for the overnight transition by the actual elapsed time, or reset the state covariance matrix $P_{t|t-1}$ at the 09:15 bar to a higher uncertainty prior.
  - **Refinement**: Let $Q_{\text{transition}} = f(\Delta t) \cdot Q_{\text{intraday}}$, where $f(\Delta t) = \max(1, k \cdot \ln(\Delta t))$ or a step-wise multiplier (e.g., $f(\Delta t) \approx 10$ to $50$ for overnight transitions). Alternatively, reset the diagonal elements of the state covariance matrix $P$ at 09:15:
    $$P_{09:15 | 15:29} = P_{15:29 | 15:29} + Q_{\text{overnight}}$$

### Flaw 10: In-Sample Standard Deviation Priming
* **Location**: `Raw/Sources/attachments/stage3_pairs_backtest.ipynb` (Cell 7, lines 165-175: rolling Z-score loop).
* **Flaw**: The rolling Z-score window is primed using the warm-up innovations (first 3,750 bars). These innovations were generated using the filter initialized with OLS parameters fit on that exact same window. This makes their variance (`sigma_w`) artificially small because they are in-sample residuals of an OLS fit. Since the rolling Z-score is primed using these warm-up innovations, the Z-score standard deviation at the start of the live phase will be underestimated, causing Z-scores to be artificially inflated and triggering false entry signals at the start of the trading period.
* **Proposed Mathematical/Logical Correction**: As established in Flaw 4, standardizing via the native Kalman variance $S_t$ ($z_t = e_t / \sqrt{S_t}$) completely bypasses this issue because $S_t$ is computed analytically at each step, eliminating the need to prime a rolling window.

### Flaw 11: Overnight Return Contamination in Lead-Lag Detection
* **Location**: `Raw/Sources/attachments/stage3_pairs_backtest.ipynb` (Cell 5, line 129: `detect_lagger`).
* **Flaw**: The `detect_lagger` function computes the cross-correlation on the return series using `np.diff(ln_a)`. This return series contains overnight gap returns (the price change from 15:29 of the previous day to 09:15 of the current day). Because overnight returns have much larger variance than intraday 1-minute returns, these few gap return observations will dominate the cross-correlation calculation, rendering the leader/lagger classification statistically noisy and biased by overnight shocks rather than true intraday lead-lag dynamics.
* **Proposed Mathematical/Logical Correction**: Null out the 09:15 returns from the return series in `detect_lagger` before computing `np.corrcoef`.

---

## 5. Verification of Discrepancies and Code-Documentation Gaps

### ADF Stationarity Filter
* **Gaps**: Bypassing the Augmented Dickey-Fuller (ADF) stationarity filter in Stage 3 backtesting (`stage3_pairs_backtest.ipynb` Cell 2) is a critical methodological violation.
* **Verification**: In `Plans/stage-2-pairs-trading-kalman-filter-state-space.md`, a pair is defined as "tradeable" only if it passes the ADF test (`adf_pvalue < 0.05`). However, the backtester only filters on half-life bounds (`5.0 <= half_life_minutes <= 120.0`). This allows non-stationary spreads (which have no statistical mean reversion) to enter the execution engine, causing unbounded losses when the spread drifts.

### OU Parameter Constraints
* **Gaps**: In `Plans/stage-2-pairs-trading-kalman-filter-state-space.md`, the mean reversion speed $\kappa$ is mapped from the discrete AR(1) coefficient $\phi$ via:
  $$\kappa = -\frac{\ln(\phi)}{\Delta t}$$
* **Verification**: If the discrete coefficient $\phi \le 0$ (due to noise or high-frequency oscillation), $\ln(\phi)$ is mathematically undefined in real numbers. If $\phi \ge 1$, then $\kappa \le 0$, indicating a non-stationary or divergent process. The code must enforce the constraint $0 < \phi < 1$ to ensure a valid mean-reverting OU process.

### Stop-Loss Execution Defect
* **Gaps**: In `scripts/generate_z_stoploss_nb.py`, the exit condition check for the half-life stop-loss is:
  ```python
  elif bars_held == hl_bars:
      if current_gross < 0:
          exit_reason = "hl_stoploss"
          suspended = True
  ```
* **Verification**: This represents a single-point evaluation. If a position is profitable at exactly `hl_bars` but later turns negative, the condition `bars_held == hl_bars` is never met again because `bars_held > hl_bars`. The position is held indefinitely until the session end, violating risk limits. The check must be changed to `bars_held >= hl_bars`.

---

## 6. Gaps and Recommendations

1. **Slippage Impact on High-Frequency Strategy**: Since the median half-life is ~9 minutes, the strategy trades frequently. Slippage of 0.02% to 0.05% per leg must be implemented in the backtester to assess whether any pair remains profitable after realistic execution costs.
2. **Margin and Capital Allocation Modeling**: The backtester assumes a static ₹10,000 capital allocated per trade on the lagging asset. In a two-sided portfolio, the capital must cover the margin requirements of both the long and short legs. Intraday equity margin requirements (typically 20% in India) and short-selling restrictions must be modeled.
3. **Data Scrubbing on SQLite Database**: The integrity of the source data in `ohlcv_1min` must be audited. Any decimal errors or decimal-shifting discrepancies would propagate through Stage 1 correlation and corrupt the Kalman Filter state.
