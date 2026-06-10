# Handoff Report — Pairs Trading QC Audit Critic

## 1. Observation

I have reviewed the explorer agent's findings in `teamwork_preview_explorer_audit_1/findings.md`, the backtesting notebook `Raw/Sources/attachments/stage3_pairs_backtest.ipynb`, the Kalman filter state-space plan `Plans/stage-2-pairs-trading-kalman-filter-state-space.md`, and the logs. The key observations include:

- The project plan `/storage/emulated/0/Quant/LLM-WIKI/Plans/stage-2-pairs-trading-kalman-filter-state-space.md` defines the EM update for process noise covariance $Q_{new}$ (on line 131) as:
  $$Q_{new} = \frac{1}{T} \sum_{t=1}^{T} \left[ P_{t|T} + \hat{\theta}_{t|T}\hat{\theta}_{t|T}^\top - G_{t-1}P_{t|T}\hat{\theta}_{t|T}^\top - \hat{\theta}_{t|T}P_{t|T}G_{t-1}^\top - P_{t,t-1|T} - \hat{\theta}_{t|T}\hat{\theta}_{t-1|T}^\top \right]$$
  This formula contains matrix multiplications where a $2 \times 2$ matrix is multiplied by a $1 \times 2$ row vector from the right (e.g., $G_{t-1}P_{t|T}\hat{\theta}_{t|T}^\top$), and a $2 \times 1$ vector is multiplied by a $2 \times 2$ matrix from the left (e.g., $\hat{\theta}_{t|T}P_{t|T}G_{t-1}^\top$). These are dimensionally invalid.
  
- The plan's cross-covariance formulation (on line 121) is:
  $$P_{t,t-1|T} = G_{t-1} P_{t|T}$$
  This ignores the recursive backward update from future observations.

- The backtesting engine in `/storage/emulated/0/Quant/LLM-WIKI/Raw/Sources/attachments/stage3_pairs_backtest.ipynb` (Cell 7) standardizes the innovations using a rolling 10-day (3,750 bars) sample standard deviation, while the Kalman state space model assumes $e_t \sim \mathcal{N}(0, S_t)$.

- The backtester (Cell 7, line 165) enters positions on the lagging asset only:
  `this_qty = int(CAPITAL // price)`
  `is_long = this_is_long`
  without placing any hedging orders on the leading asset.

- The log `Raw/Sources/attachments/stage2-pairs-kalman-ou.log` shows the minimum half-life estimated is `0.033448` minutes (2 seconds), which is anomalous for 1-minute sampled data.

- The stop-loss script `scripts/generate_z_stoploss_nb.py` checks:
  `elif bars_held == hl_bars: if current_gross < 0:`
  which is a single-bar check.

---

## 2. Logic Chain

1. **Flaws 2 & 3 (Kalman updates)**: Based on state-space theory, the state vector is $\theta_t = [\beta_t, \alpha_t]^\top$ ($2 \times 1$). Multiplying a $2 \times 2$ matrix by a $1 \times 2$ row vector is undefined. Therefore, the plan's $Q_{new}$ formula is mathematically invalid. The correct EM update for $Q$ in a random walk parameter model is derived as:
   $$Q_{new} = \frac{1}{T} \sum_{t=1}^T \mathbb{E}\left[ (\theta_t - \theta_{t-1})(\theta_t - \theta_{t-1})^\top \middle| y_{1:T} \right]$$
   Substituting the smoothed estimates yields the correct $2 \times 2$ matrix formula. The cross-covariance $P_{t,t-1|T}$ must be computed recursively backward from $t = T$ using the RTS smoother recursion because future observations modify the joint distribution of adjacent states.
   
2. **Flaw 7 (Market Neutrality)**: A pairs trading strategy trades the spread. In a log-price model $\ln P_{A,t} = \beta_t \ln P_{B,t} + \alpha_t + e_t$, taking a derivative gives the return relation $r_{A,t} = \beta_t r_{B,t} + de_t$. The portfolio value change is $dV_t = Q_A P_{A,t} r_{A,t} + Q_B P_{B,t} r_{B,t}$. To make $dV_t$ independent of $r_{B,t}$, we must set $Q_A P_{A,t} \beta_t + Q_B P_{B,t} = 0$, which yields the price-ratio adjusted quantity hedge ratio $Q_B = -\beta_t \frac{P_{A,t}}{P_{B,t}} Q_A$. Trading only the lagging asset exposes the strategy to unhedged market beta, explaining the large backtest losses.

3. **Flaw 4 & 10 (Z-Score & Priming)**: Under the model, $e_t \sim \mathcal{N}(0, S_t)$ where $S_t = H_t P_{t|t-1} H_t^\top + R$. Standardizing by $\sqrt{S_t}$ is the mathematically correct way to obtain a standard normal $\mathcal{N}(0, 1)$ Z-score. Using a rolling sample standard deviation assumes homoscedasticity and lags behind volatility changes. Moreover, priming the rolling standard deviation using in-sample warm-up innovations underestimates variance (since OLS residuals have lower variance), inflating Z-scores and triggering false entries at the start of trading. Using native $S_t$ standardizations naturally resolves the rolling priming issue.

4. **Flaw 9 (Time-Scale Transition)**: Parameters drift overnight (17.75 hours) and over weekends (65 hours). Using a constant $Q$ assumes parameter drift is uniform in trading time, which is a major model misspecification. Scaling $Q$ overnight or resetting state uncertainty $P$ at the open is necessary to handle overnight gap shocks.

---

## 3. Caveats

- **API and Data Quality**: We did not verify the integrity of close prices in the SQLite database. Gaps or price spikes could corrupt the correlation screening.
- **Transaction Fees**: We assumed Zerodha's MIS fee calculation is correct.
- **Short-Selling Constraints**: Shorting in Indian markets is restricted to intraday. If holding periods exceed 1 session (forced exit at 15:28 is applied), short positions are covered daily. The backtester enforces this, but daily exit and entry costs will severely erode profits for long-duration pairs.

---

## 4. Conclusion

The explorer subagent's 11 findings are mathematically and methodologically verified. However, the proposed corrections must be refined to:
1. Use the price-ratio adjusted quantity hedge ratio:
   $$Q_B = -\beta_t \left( \frac{P_{A,t}}{P_{B,t}} \right) Q_A$$
2. Enforce a regularization lower bound on process noise covariance to prevent filter divergence:
   $$Q_{ii} = \max([Q_{new}]_{ii}, \delta)$$
3. Scale process noise covariance overnight by time step $\Delta t$ or reset state covariance $P$ at the open.
4. Standardize innovations using native Kalman variance $z_t = e_t / \sqrt{S_t}$, which also resolves the rolling window priming issue.

---

## 5. Verification Method

- **Inspected Files**: 
  - Verification Report: `/storage/emulated/0/Quant/LLM-WIKI/.agents/teamwork_preview_critic_audit_1/math_qc_review.md`
  - Explorer findings: `/storage/emulated/0/Quant/LLM-WIKI/.agents/teamwork_preview_explorer_audit_1/findings.md`
  - Plan files under `/storage/emulated/0/Quant/LLM-WIKI/Plans/`
- **Commands**: Since this is a mathematical and methodological review, there are no project-specific unit test suites to run locally. The verification is conducted via analytical derivation.
- **Invalidation Condition**: If the spread is modeled on raw prices ($P_{A,t} = \beta P_{B,t} + \alpha$), then the quantity ratio is indeed $Q_B = -\beta Q_A$. However, since Cell 3 of the backtest notebook explicitly loads log-prices (`np.log(...)`), the log-price formulation holds, and the price-ratio adjusted formula is the only correct one.
