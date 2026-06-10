# Pairs Trading QC Audit — Mathematical & Methodological Verification

**Review Conducted By**: teamwork_preview_critic  
**Date**: 2026-06-04T15:35:00Z  
**Verdict**: **APPROVE WITH CRITICAL REFINEMENTS**

---

## 1. Review Summary

This report presents a rigorous mathematical and methodological verification of the Pairs Trading pipeline audit conducted by `teamwork_preview_explorer`. All eleven (11) identified flaws and code-documentation gaps have been analyzed, cross-referenced with quantitative finance theory, and verified. 

While the explorer's findings are conceptually and mathematically correct, several of their proposed corrections require critical mathematical refinements to prevent execution errors and exposure mismatches. Specifically, this review contributes:
1. The **exact value-based hedge ratio and quantity adjustment** required for log-price based pairs trading.
2. The **regularization constraints** for process noise covariance ($Q_{new}$) estimation to prevent filter divergence.
3. The **exact time-scaling adjustments** for the overnight Kalman transition.
4. A unification showing how the **native Kalman Z-score** ($S_t$) mathematically resolves the rolling innovation priming issue.

---

## 2. Mathematical Verification of Identified Flaws

### Flaw 1: Lookahead Bias in Backtesting Parameters
* **Verification**: **PASSED (Verified)**
* **Mathematical/Logical Proof**: 
  In backtesting, the filtration at time $t$, denoted as $\mathcal{F}_t = \sigma(y_s, x_s : s \le t)$, must contain only historical data. Estimating the model parameters $\Theta = \{Q, R, t_{1/2}\}$ using the entire sample $\mathcal{F}_T$ ($T > t$) and then running the trading engine on $\mathcal{F}_t$ using $\Theta$ violates the non-anticipating property of trading strategies. The EM algorithm finds the optimal parameters that fit the specific realized historical path, meaning the backtest results are heavily over-optimized and exhibit in-sample bias.
* **Refinement**: Implement a strictly walk-forward or rolling calibration framework. Since running the EM algorithm at every bar is computationally prohibitive, parameters $\Theta$ should be estimated on a rolling historical window (e.g., 10 to 20 trading days) and updated periodically (e.g., weekly or monthly) out-of-sample.

---

### Flaw 2: Dimensionality and Mathematical Errors in the EM Update Formula for Q
* **Verification**: **PASSED (Verified)**
* **Mathematical/Logical Proof**:
  Let the state vector be $\theta_t = [\beta_t, \alpha_t]^\top$ (dimension $2 \times 1$). The smoothed state estimate is $\hat{\theta}_{t|T} = \mathbb{E}[\theta_t | y_{1:T}]$ ($2 \times 1$). Its transpose $\hat{\theta}_{t|T}^\top$ is a $1 \times 2$ row vector. The smoother gain matrix $G_{t-1}$ is $2 \times 2$, and the smoothed state covariance $P_{t|T}$ is $2 \times 2$.
  - In the original formula: $G_{t-1} P_{t|T} \hat{\theta}_{t|T}^\top$ involves $(2 \times 2) \times (1 \times 2)$, which is a dimensional mismatch.
  - Similarly, $\hat{\theta}_{t|T} P_{t|T} G_{t-1}^\top$ involves $(2 \times 1) \times (2 \times 2)$, which is also dimensionally invalid.
  
  The correct EM update is derived by maximizing the expected log-likelihood of the state transitions. For a random walk transition model $\theta_t = \theta_{t-1} + w_t$ where $w_t \sim \mathcal{N}(0, Q)$, the M-step update for $Q_{new}$ is:
  $$Q_{new} = \frac{1}{T} \sum_{t=1}^T \mathbb{E}\left[ (\theta_t - \theta_{t-1})(\theta_t - \theta_{t-1})^\top \middle| y_{1:T} \right]$$
  Expanding the expectation:
  $$\mathbb{E}\left[ (\theta_t - \theta_{t-1})(\theta_t - \theta_{t-1})^\top \middle| y_{1:T} \right] = \mathbb{E}[\theta_t \theta_t^\top | y_{1:T}] - \mathbb{E}[\theta_{t-1}\theta_t^\top | y_{1:T}] - \mathbb{E}[\theta_t \theta_{t-1}^\top | y_{1:T}] + \mathbb{E}[\theta_{t-1}\theta_{t-1}^\top | y_{1:T}]$$
  Substituting the smoothed covariances:
  - $\mathbb{E}[\theta_t \theta_t^\top | y_{1:T}] = P_{t|T} + \hat{\theta}_{t|T} \hat{\theta}_{t|T}^\top$
  - $\mathbb{E}[\theta_{t-1}\theta_{t-1}^\top | y_{1:T}] = P_{t-1|T} + \hat{\theta}_{t-1|T} \hat{\theta}_{t-1|T}^\top$
  - $\mathbb{E}[\theta_t \theta_{t-1}^\top | y_{1:T}] = P_{t,t-1|T} + \hat{\theta}_{t|T} \hat{\theta}_{t-1|T}^\top$
  - $\mathbb{E}[\theta_{t-1}\theta_t^\top | y_{1:T}] = P_{t,t-1|T}^\top + \hat{\theta}_{t-1|T} \hat{\theta}_{t|T}^\top$
  
  This yields the correct, dimensionally consistent $2 \times 2$ matrix update:
  $$Q_{new} = \frac{1}{T} \sum_{t=1}^T \left[ (P_{t|T} + \hat{\theta}_{t|T} \hat{\theta}_{t|T}^\top) - (P_{t,t-1|T} + \hat{\theta}_{t|T} \hat{\theta}_{t-1|T}^\top) - (P_{t,t-1|T}^\top + \hat{\theta}_{t-1|T} \hat{\theta}_{t|T}^\top) + (P_{t-1|T} + \hat{\theta}_{t-1|T} \hat{\theta}_{t-1|T}^\top) \right]$$
* **Refinement**: To enforce a diagonal process noise structure (preventing cross-parameter drift coupling and overfitting), we extract only the diagonal elements:
  $$Q_{new, \text{diag}} = \text{diag}([Q_{new}]_{1,1}, [Q_{new}]_{2,2})$$
  Furthermore, to prevent **filter divergence** (where the estimated process noise covariance collapses to zero, $Q_{ii} \to 0$, causing the Kalman gain to decay to $K_t \to 0$ and ignoring new data), we must enforce a regularization lower bound during updates:
  $$[Q_{new}]_{ii} = \max([Q_{new}]_{ii}, \delta)$$
  where $\delta > 0$ is a small threshold (e.g., $10^{-8}$).

---

### Flaw 3: Mathematically Incorrect Cross-Covariance Formula in RTS Smoother
* **Verification**: **PASSED (Verified)**
* **Mathematical/Logical Proof**:
  The simplified expression in the project plan, $P_{t,t-1|T} = G_{t-1} P_{t|T}$, is incorrect because it ignores the recursive backward flow of future information. In the Rauch-Tung-Striebel (RTS) smoother, the cross-covariance $P_{t-1,t-2|T} = \text{Cov}(\theta_{t-1}, \theta_{t-2} | y_{1:T})$ must be computed recursively backward from $t = T$ to $2$:
  $$P_{t-1,t-2|T} = P_{t-1|t-1} G_{t-2}^\top + G_{t-1} (P_{t,t-1|T} - F P_{t-1|t-1}) G_{t-2}^\top$$
  For a random walk model ($F = I$), the recursion is:
  $$P_{t-1,t-2|T} = P_{t-1|t-1} G_{t-2}^\top + G_{t-1} (P_{t,t-1|T} - P_{t-1|t-1}) G_{t-2}^\top$$
  with the initialization at the terminal boundary $t = T$:
  $$P_{T,T-1|T} = (I - K_T H_T) P_{T-1|T-1} = P_{T|T} G_{T-1}^\top$$
  This recursive structure is mathematically required to correctly estimate the joint density of adjacent states given the full dataset.

---

### Flaw 4: Mathematical Inconsistency in Z-Score Calculation
* **Verification**: **PASSED (Verified)**
* **Mathematical/Logical Proof**:
  The Kalman Filter model assumes that the measurement equation is $y_t = H_t \theta_t + v_t$, where $v_t \sim \mathcal{N}(0, R)$.
  The innovation at step $t$ is $e_t = y_t - H_t \hat{\theta}_{t|t-1}$.
  By definition of the Kalman updates, the conditional variance of the innovation is:
  $$S_t = \text{Var}(e_t | y_{1:t-1}) = H_t P_{t|t-1} H_t^\top + R$$
  Under the null hypothesis that the state-space model is correctly specified, the innovation is distributed as:
  $$e_t \sim \mathcal{N}(0, S_t)$$
  To standardize this innovation, we must divide by its native conditional standard deviation:
  $$z_t = \frac{e_t}{\sqrt{S_t}}$$
  This ensures that $z_t \sim \mathcal{N}(0, 1)$ is homoscedastic and statistically consistent.
  Standardizing by a rolling sample standard deviation $\sigma_{w}$ over 3,750 bars:
  1. Assumes the innovations are homoscedastic ($\text{Var}(e_t) = \text{const}$), which contradicts the time-varying nature of $H_t$ (log price of asset B) and $P_{t|t-1}$.
  2. Introduces a 10-day phase lag in adapting to rapid volatility regime shifts.
  3. Wastes 3,750 bars of data for rolling priming.

---

### Flaw 5: Signal-Execution Synchronicity (Execution Lookahead Bias)
* **Verification**: **PASSED (Verified)**
* **Mathematical/Logical Proof**:
  Let $P_{k, i}^{\text{close}}$ be the close price of asset $k$ at bar $i$. The signal $z_i$ is computed using $P_{A, i}^{\text{close}}$ and $P_{B, i}^{\text{close}}$.
  In the backtest, if a signal is triggered at bar $i$, the trade is entered at $P_{i}^{\text{close}}$. This is a lookahead bias. The close price is only established at the end of bar $i$. Evaluating the signal and executing the order at the same close price assumes zero latency and instant transmission. 
  In real execution, the trade would be entered at the next available price, which is the open of the subsequent bar $i+1$, $P_{i+1}^{\text{open}}$.

---

### Flaw 6: Global Inner-Join Data Destruction and Return-Gap Gaps
* **Verification**: **PASSED (Verified)**
* **Mathematical/Logical Proof**:
  Performing a global inner join on price series before return calculations:
  $$\mathbf{P}_t = [P_{1, t}, \dots, P_{N, t}]^\top \quad \text{dropped if } \exists k \text{ s.t. } P_{k, t} \text{ is NaN}$$
  causes the time grid to become non-uniform: $t_1, t_2, \dots$ where $t_j - t_{j-1} = m_j \ge 1$ minute.
  The return is then calculated as:
  $$r_{k, t_j} = \ln(P_{k, t_j}) - \ln(P_{k, t_{j-1}})$$
  If $m_j > 1$, $r_{k, t_j}$ represents a multi-minute return. Since variance scales linearly with time under a random walk, the variance of these returns is contaminated:
  $$\text{Var}(r_{k, t_j}) \approx m_j \sigma_k^2$$
  This heteroscedasticity corrupts the Pearson correlation coefficient $\rho$, as the correlation calculation assumes stationary 1-minute variances.
* **Refinement**: Compute log-returns on individual continuous series first, null out the 09:15 bar (overnight return) to prevent open-gap contamination, and only perform pairwise inner joins during correlation screening.

---

### Flaw 7: Lack of Market Neutrality (Single-Asset Trading)
* **Verification**: **PASSED (Verified) with Critical Mathematical Refinement**
* **Explorer's Proposed Correction**: Trade the lagging asset and hedge with the leading asset in a ratio of $-\beta_t$.
* **Critical Mathematical Refinement**:
  Because the spread is modeled on **log-prices**:
  $$\ln P_{A,t} = \beta_t \ln P_{B,t} + \alpha_t + e_t$$
  the parameter $\beta_t$ represents the **price elasticity** of asset A with respect to asset B, not a raw share ratio.
  Let $r_{A,t} = \frac{dP_{A,t}}{P_{A,t}}$ and $r_{B,t} = \frac{dP_{B,t}}{P_{B,t}}$ represent the returns of assets A and B.
  The model implies:
  $$r_{A,t} = \beta_t r_{B,t} + u_t$$
  where $u_t$ is the return of the mean-reverting spread.
  Let the portfolio consist of $Q_A$ shares of A and $Q_B$ shares of B. The total value is $V_t = Q_A P_{A,t} + Q_B P_{B,t}$.
  The change in portfolio value is:
  $$dV_t = Q_A dP_{A,t} + Q_B dP_{B,t} = Q_A P_{A,t} r_{A,t} + Q_B P_{B,t} r_{B,t}$$
  Substituting $r_{A,t}$:
  $$dV_t = Q_A P_{A,t} (\beta_t r_{B,t} + u_t) + Q_B P_{B,t} r_{B,t} = (Q_A P_{A,t} \beta_t + Q_B P_{B,t}) r_{B,t} + Q_A P_{A,t} u_t$$
  To achieve market neutrality (i.e., to immunize the portfolio value from the directional return $r_{B,t}$), we must set the coefficient of $r_{B,t}$ to zero:
  $$Q_A P_{A,t} \beta_t + Q_B P_{B,t} = 0 \implies Q_B = -\beta_t \left( \frac{P_{A,t}}{P_{B,t}} \right) Q_A$$
  - If we long the spread (buying A, shorting B):
    $$Q_A > 0, \quad Q_B = -\beta_t \left( \frac{P_{A,t}}{P_{B,t}} \right) Q_A$$
  - If we short the spread (shorting A, buying B):
    $$Q_A < 0, \quad Q_B = -\beta_t \left( \frac{P_{A,t}}{P_{B,t}} \right) Q_A$$
  If B is the lagging asset (so we trade B with size $Q_B$ and hedge with A):
  $$Q_A = -\frac{1}{\beta_t} \left( \frac{P_{B,t}}{P_{A,t}} \right) Q_B$$
  
  **Why this matters**: If we use the raw quantity-based ratio $Q_B = -\beta_t Q_A$ (as is correct only for raw-price models), the portfolio will be severely under-hedged or over-hedged. For example, if $P_{A,t} = \text{₹}1,500$ and $P_{B,t} = \text{₹}500$ with $\beta_t = 1.0$, the raw ratio yields $Q_B = -1.0 Q_A$. The value of A is ₹1,500 and B is ₹500, leaving an unhedged exposure of ₹1,000. Under the corrected formula, $Q_B = -1.0 \times \frac{1500}{500} Q_A = -3 Q_A$. The value of B is $3 \times 500 = \text{₹}1,500$, which perfectly offsets A.

---

### Flaw 8: Lack of Slippage and Bid-Ask Spread Modeling
* **Verification**: **PASSED (Verified)**
* **Mathematical/Logical Proof**:
  Let the mid-price PnL of a trade be $PnL_{\text{mid}}$. The realized net PnL is:
  $$PnL_{\text{net}} = PnL_{\text{mid}} - 2 \cdot \text{slippage} - \text{transaction\_fees}$$
  For high-frequency intraday trades (median half-life of 9 minutes), transaction fees are already high. Omitting the slippage/spread penalty (e.g., 1 tick or 0.02% per leg per order) creates an upward performance bias, hiding real-world unprofitability.

---

### Flaw 9: Time-Scale Mismatch in Kalman Filter Process Noise Covariance
* **Verification**: **PASSED (Verified) with Mathematical Refinement**
* **Explorer's Proposed Correction**: Scale the process noise covariance $Q$ overnight or reset the state covariance matrix $P$.
* **Mathematical Refinement**:
  If the parameters drift as a continuous-time Brownian motion:
  $$d\theta_t = dW_t, \quad dW_t \sim \mathcal{N}(0, q \, dt)$$
  the discrete-time transition covariance over an elapsed time $\Delta t$ is:
  $$Q_{\Delta t} = q \cdot \Delta t$$
  During the trading session, the step is $\Delta t = 1$ minute. Overnight, the elapsed calendar time is $\Delta t = 1,066$ minutes (and over 4,000 minutes for weekends).
  Enforcing a constant $Q$ assumes $\Delta t_{\text{overnight}} = 1$. 
  To scale $Q$ correctly without causing numerical instability (since linear calendar scaling might over-inflate variance due to market closure), we can define a time-scaled process noise:
  $$Q_{\text{transition}} = f(\Delta t) \cdot Q_{\text{intraday}}$$
  where $f(\Delta t) = \max(1, k \cdot \ln(\Delta t))$ or a step-wise multiplier (e.g., $f(\Delta t) \approx 10$ to $50$ for overnight transitions).
  Alternatively, reset the diagonal elements of the state covariance matrix $P_{t|t-1}$ at 09:15:
  $$P_{09:15 | 15:29} = P_{15:29 | 15:29} + Q_{\text{overnight}}$$

---

### Flaw 10: In-Sample Standard Deviation in Primed Rolling Z-Score
* **Verification**: **PASSED (Verified)**
* **Mathematical/Logical Proof**:
  The warm-up innovations $e_1, \dots, e_M$ (where $M = 3,750$ bars) are generated using a filter initialized with OLS parameters fit on that exact same window. These represent in-sample residuals. The in-sample variance $\sigma_{\text{in}}^2 = \frac{1}{M} \sum_{t=1}^M e_t^2$ is biased downward relative to out-of-sample prediction error variance. Standardizing the out-of-sample innovations $e_{M+1}, \dots$ using $\sigma_{\text{in}}$ inflates the Z-scores:
  $$|z_t| = \frac{|e_t|}{\sigma_{\text{in}}} > \frac{|e_t|}{\sigma_{\text{out}}}$$
  leading to false entry signals at the start of the live trading phase.
* **Refinement**: As established in Flaw 4, standardizing via the native Kalman variance $S_t$ ($z_t = e_t / \sqrt{S_t}$) completely bypasses this issue because $S_t$ is computed analytically at each step, eliminating the need to prime a rolling window.

---

### Flaw 11: Overnight Return Contamination in Leader/Lagger Detection
* **Verification**: **PASSED (Verified)**
* **Mathematical/Logical Proof**:
  The log-return series is $r_t = \ln P_t - \ln P_{t-1}$. The overnight return (at 09:15) spans 17.75 hours and exhibits a variance $\sigma_{\text{overnight}}^2 \gg \sigma_{\text{intraday}}^2$.
  In the cross-correlation calculation:
  $$\rho_{A, B}(\tau) = \frac{\sum_t (r_{A, t} - \bar{r}_A)(r_{B, t-\tau} - \bar{r}_B)}{\sqrt{\sum_t (r_{A, t} - \bar{r}_A)^2 \sum_t (r_{B, t} - \bar{r}_B)^2}}$$
  the overnight terms act as leverage points/outliers. Since they are squared in the denominator and multiplied in the numerator, they dominate the entire sum, biasing the lead-lag coefficient toward overnight gaps instead of intraday dynamics. Nulling out the 09:15 bar is mathematically required to isolate intraday relationships.

---

## 3. Verification of Discrepancies & Code-Documentation Gaps

### ADF Stationarity Filter
Bypassing the ADF stationarity check in Stage 3 backtesting is a critical methodological violation.
An Ornstein-Uhlenbeck process is only stationary if the mean reversion speed is positive ($\kappa > 0$). If a pair has a small half-life in-sample but is non-stationary (ADF $p \ge 0.05$), the spread can drift indefinitely. Executing a mean-reverting strategy on a non-stationary spread leads to unbounded losses, which is reflected in the backtest logs.

### OU Parameter Constraints
The continuous-time mean reversion speed $\kappa$ is mapped from the discrete AR(1) coefficient $\phi$ via:
$$\kappa = -\frac{\ln(\phi)}{\Delta t}$$
1. If $\phi \le 0$, $\ln(\phi)$ is mathematically undefined in $\mathbb{R}$. This represents a rapid, anti-persistent oscillation that cannot be modeled by a continuous-time OU process.
2. If $\phi \ge 1$, then $\kappa \le 0$, which represents a non-stationary or divergent process.
The code must enforce the constraint $0 < \phi < 1$ to ensure a valid mean-reverting OU process.

### Stop-Loss Execution Defect
In the stop-loss parameter sweep script, the check `elif bars_held == hl_bars` is a single-point evaluation. If the trade is profitable at `hl_bars` but subsequently becomes unprofitable, it bypasses the conditional check and is held indefinitely until the session end, violating risk limits. The check must be changed to `bars_held >= hl_bars`.

---

## 4. Coverage Gaps & Unverified Items

### Coverage Gaps
* **Execution slippage impact on highly mean-reverting pairs** — Risk level: **HIGH**
  - **Recommendation**: Investigate. Because the median half-life is ~9 minutes, the strategy trades frequently. A slippage of 0.02% to 0.05% per leg must be implemented in the backtester to assess whether any pair remains profitable after realistic execution costs.

* **Leverage and Capital Allocation** — Risk level: **MEDIUM**
  - **Recommendation**: Investigate. The backtest allocates ₹10,000 to the lagging asset only. In a two-sided portfolio, the total capital must cover the margin requirements of both the long and short positions. If shorting is conducted in India (intraday MIS), margin requirements (typically 20% for equities) and short-selling constraints must be modeled.

### Unverified Items
* **Fyers API data accuracy in the SQLite database**
  - **Reason not verified**: We assume the close prices in `ohlcv_1min` are clean and correct. Any bad data points or decimal shifts in the database could corrupt the Pearson correlation and Kalman Filter states. Propose a basic data-scrubbing audit on the SQLite database as a future step.
