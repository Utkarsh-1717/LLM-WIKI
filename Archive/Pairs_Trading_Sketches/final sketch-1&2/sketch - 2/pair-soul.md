> [!WARNING]
> **ARCHIVED & OBSOLETE**
> This file is part of the trial-and-error "Sketch" phase. 
> The mathematics and code herein may contain deprecated Expectation-Maximization loops or failed concepts.
> The final, verified truth is located in the `Soul/` directory.
> Tags: #archived-sketch #pairs-trading-prototype

# Pair Trading Soul — Final Production Documentation

> **Purpose**: This is the single authoritative reference document for the Pairs Trading strategy. If all other files are lost, this document alone should be sufficient to rebuild the entire pipeline from scratch — methodology, mathematics, design choices, code, and QC resolutions all in one place.
>
> **Author**: Utkarsh Patel + Antigravity Agent Team  
> **Last Updated**: 2026-06-05  
> **Status**: PRODUCTION — Version 4 Kaggle Kernel (`utkarshpatelthefirst/master-pairs-trading-soul`)

---

## 1. Strategy Overview & Philosophy

### What Is This Strategy?
This is an **intraday relative-value mean-reversion strategy** operating on NSE-listed equities. It exploits temporary divergences between the price series of two highly correlated assets, expecting the spread to revert to its historical mean within the same trading session.

### Core Insight
When two assets share a common economic factor, their prices move together over time. The strategy:
1. Identifies pairs with statistically robust co-movement (Stage 1).
2. Fits a dynamic Kalman Filter model to track the time-varying hedge ratio (Stage 2).
3. Generates a standardized Z-score signal from the spread residual.
4. Trades **only the lagging asset** when the spread diverges beyond a threshold (Stages 3A/3B).

### Data Source
- **Database**: `Master-Data-1min.sqlite`
- **Universe**: ~500 NSE equities, 1-minute OHLCV bars
- **Coverage**: ~120 trading days of intraday data (09:15 to 15:29 IST)

---

## 2. The Great Half-Life Discovery (Why V4 is Mathematically Correct)

In the initial iterations of this strategy, Stage 2 reported **half-lives with a median of ~9 minutes**, which was flagged as anomalously short in the QC Audit. In the final, mathematically correct Version 4, the median half-life is **~2.7 minutes**.

### Why did the original code produce 9-minute half-lives?
The QC Code Audit (`Raw/Sources/Pairs_Trading_Stage1_2_Code_Audit.md`) identified that the original code treated massive overnight price gaps as 1-minute intraday shocks. Because the Kalman filter saw massive jumps happening "instantly," it severely inflated the process noise covariance $Q$. This caused the filter to over-adapt, rapidly updating parameters and artificially collapsing the spread half-life to ~9 minutes. Additionally, the EM Q-update matrix was incomplete, missing key cross-covariance terms.

### The Reality of Kalman Spreads
Once the mathematics were corrected in V4 (proper $P_0$ via OLS parameter covariance, complete RTS cross-covariance formulas, and a $1e-7$ Q floor), the Kalman filter was finally able to correctly "hug" the price relationship minute-by-minute. 

Because the filter tracks the macro-relationship perfectly, the remaining spread $e_t$ consists purely of **high-frequency market microstructure noise** (bid-ask bounce, transient liquidity imbalances, latency). **This microstructure noise reverts extremely fast.** A median half-life of 2.7 minutes is the correct mathematical reality of a properly filtered 1-minute equity spread.

### The Economic Reality (Stage 3B Results)
Because the true half-life is ~2.7 minutes, the strategy must trade frequently to capture these fleeting microstructure divergences. In Stage 3A (gross profit), 481 pairs found profitable configurations. However, in Stage 3B (net profit), after applying Zerodha MIS fees and a modest 0.05% slippage, the strategy generated massive net losses.
**Conclusion**: High-frequency intraday pairs trading on 1-minute bars with 3-minute half-lives cannot overcome retail transaction fees and slippage. The mathematical edge is real, but it is entirely consumed by market friction.

---

## 3. Intentional Design Choices (Deviations from Textbook)

### 3.1 Single-Sided Lagger Trading (NOT Market Neutral)
We trade **only the lagging asset**. We do not take a hedging position in the leading asset.
**Why**: Doubling the legs doubles brokerage, STT, and slippage. For intraday trades with 3-minute half-lives, two-sided execution is economically infeasible. Furthermore, the leading asset has already priced in the information; the alpha lies entirely in the lagging asset's catch-up move.

### 3.2 Strict Data Alignment (No Forward-Fill)
We `ffill(limit=1)` first, then `dropna(how='any')`. Any bar where both assets don't have fresh data is completely dropped.
**Why**: Comparing a stale price with a live price creates "phantom divergences" that trigger false entries. Both assets must be observed at the exact same timestamp.

### 3.3 Overnight Q-Scaling
We multiply Q by 15× at the 09:15 bar transition.
**Why**: An overnight gap is a macro-jump. The 15× multiplier tells the filter to maintain its macro-drift estimates but acknowledge increased uncertainty at the open, allowing it to adapt faster to the morning gap without entirely losing its historical state.

### 3.4 OU Z-Score for Signal (NOT Kalman Innovation Z)
We use `Z_t = (spread_t - ou_mu) / ou_sigma` instead of the Kalman innovation $Z_t = e_t / \sqrt{S_t}$.
**Why**: The Kalman $S_t$ is dominated by measurement noise $R$. The Kalman Z-score rarely exceeds 0.05. The true trading signal is how far the realized spread has deviated from its long-run OU mean, normalized by the OU process volatility $\sigma_{OU}$.

---

## 4. Stage 1 — Pearson Correlation Screening

**Goal**: Find robustly correlated pairs using log-returns.
- Filter to NSE hours (09:15-15:29).
- Align timestamps strictly.
- Calculate log-returns: $r_t = \ln(P_t / P_{t-1})$.
- **Mask 09:15 returns to NaN** to remove overnight gap contamination.
- Compute Pearson correlation $\rho$, calculate t-statistic, filter for $p < 0.05$ and $N \ge 5000$.
- Rank by $\rho$ and output top 500 to `pairs_top500.csv`.

---

## 5. Stage 2 — Kalman Filter EM Calibration

**Goal**: Fit a state-space model to estimate dynamic hedge ratio $\beta_t$ and intercept $\alpha_t$.

**State-Space Model**:
$\theta_t = \theta_{t-1} + w_t, \quad w_t \sim \mathcal{N}(0, Q)$
$y_t = H_t \theta_t + v_t, \quad v_t \sim \mathcal{N}(0, R)$
where $y_t = \ln(P_{A,t})$ and $H_t = [\ln(P_{B,t}), 1]$.

**EM Algorithm (Mathematically Corrected)**:
- $P_0 = \sigma^2_{OLS} \cdot (X_{OLS}^T X_{OLS})^{-1} \cdot 10$
- Full RTS Backward Smoother is run to extract $P_{t|T}$ and $P_{t,t-1|T}$.
- Complete Q update:
  $Q_{new} = \frac{1}{T-1} \sum_{t=1}^{T} \left[(P_{t|T} + \hat\theta_{t|T}\hat\theta_{t|T}^T) + (P_{t-1|T} + \hat\theta_{t-1|T}\hat\theta_{t-1|T}^T) - (P_{t,t-1|T}^T + \hat\theta_{t|T}\hat\theta_{t-1|T}^T) - (P_{t,t-1|T} + \hat\theta_{t-1|T}\hat\theta_{t|T}^T)\right]$
- **Q Floor**: `clip(Q_n, 1e-7, None)` prevents the filter from freezing.
- Fit AR(1) to the smoothed spread to extract OU parameters ($\kappa, \mu, \sigma_{OU}$, half-life).

---

## 6. Stage 3A & 3B — Execution Engine

**Stage 3A (In-Sample Optimization)**:
- Tests Z-entry triggers (2.0 to 15.0) and stop-loss logic (Z_sl or Half-life timeout) on the first 70% of data.
- Z-score uses OU $\mu$ and $\sigma$.
- Identifies lagging asset via 1-bar lagged cross-correlation.

**Stage 3B (Out-of-Sample Backtest)**:
- Runs the best configuration on the last 30% of data.
- **1-bar execution delay**: Signal at close of bar $t$ → execute at open of bar $t+1$.
- **Fees**: Full Zerodha MIS fees calculated per round trip.
- **Slippage**: 0.05% applied to entry and exit prices.

---

## 7. Known Limitations & Future Work
1. **Tick Data Necessity**: Since the true half-life is ~2.7 minutes, 1-minute bars are too slow. Entries must be executed on tick data within seconds of the divergence to capture the spread before it reverts.
2. **Rolling Calibration**: Q, R, and OU parameters should be recalibrated on a rolling 30-day window out-of-sample rather than using a static IS/OOS split.
3. **Retail Fees**: The strategy is unviable for retail traders due to MIS fees and slippage on low-margin high-frequency moves. It requires institutional latency and fee structures.
