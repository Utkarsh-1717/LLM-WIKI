# Handoff Report - Pairs Trading QC Audit

## 1. Observation

During the review of the LLM-WIKI Pairs Trading pipeline, the following files and code snippets were observed:

### A. Stage 3 Backtesting Engine and Signal Generation
* **File**: `/storage/emulated/0/Quant/LLM-WIKI/Raw/Sources/attachments/stage3_pairs_backtest.ipynb`
* **Cell 7 (Trade Execution Loop)**:
  ```python
  # Price array for lagging asset (raw price recovered from log_price)
  if lagger_side == "a":
      lag_prices = np.exp(ln_a)
  else:
      lag_prices = np.exp(ln_b)
  ...
  for i in range(WARMUP_BARS, T):
      z = z_scores[i]
      if np.isnan(z):
          continue
      bar_time = timestamps[i].time()
      price    = lag_prices[i]
      ...
      # Entry Logic
      if not in_trade and bar_time < FORCE_EXIT_TIME:
          if z >= Z_ENTRY:
              if lagger_side == "a":
                  this_is_long = False
              else:
                  this_is_long = True
          elif z <= -Z_ENTRY:
              if lagger_side == "a":
                  this_is_long = True
              else:
                  this_is_long = False
          ...
          this_qty = int(CAPITAL // price)
          ...
          in_trade    = True
          entry_bar   = i
          entry_price = price
          is_long     = this_is_long
          qty         = this_qty
  ```
* **Cell 4 (Kalman Filter)**:
  ```python
  def kalman_filter_fixed(ln_a, ln_b, beta0, alpha0, P0, Q_beta, Q_alpha, R):
      ...
      for t in range(T):
          H = np.array([ln_b[t], 1.0], dtype=np.float64)
          theta_pred = theta.copy()
          P_pred     = P + Q
          y_t   = ln_a[t]
          e_t   = y_t - H @ theta_pred
          S_t   = H @ P_pred @ H + R
          K_t   = (P_pred @ H) / S_t
          theta = theta_pred + K_t * e_t
          P     = (np.eye(2) - np.outer(K_t, H)) @ P_pred
          innovations[t] = e_t
      return innovations, betas, alphas
  ```

### B. Stage 2 EM and RTS Smoother Formulas
* **File**: `/storage/emulated/0/Quant/LLM-WIKI/Plans/stage-2-pairs-trading-kalman-filter-state-space.md`
* **Line 121 (Cross-Covariance)**:
  $$P_{t,t-1|T} = G_{t-1} P_{t|T}$$
* **Line 131 (Q Update)**:
  $$Q_{new} = \frac{1}{T} \sum_{t=1}^{T} \left[ P_{t|T} + \hat{\theta}_{t|T}\hat{\theta}_{t|T}^\top - G_{t-1}P_{t|T}\hat{\theta}_{t|T}^\top - \hat{\theta}_{t|T}P_{t|T}G_{t-1}^\top - P_{t,t-1|T} - \hat{\theta}_{t|T}\hat{\theta}_{t-1|T}^\top \right]$$

### C. Live Execution Results
* **File**: `/storage/emulated/0/Quant/LLM-WIKI/Raw/Sources/attachments/stage3-pairs-backtest.log`
* **Lines 85-95 (P&L and Win Rates)**:
  ```
  [  1/41] BDL - MAZDOCK  (HL=43.0min) ... trades=145  net_pnl=Rs-8913.1  calmar=-1.55
  [  2/41] BDL - HAL  (HL=25.5min) ... trades=178  net_pnl=Rs-9206.1  calmar=-1.55
  [  3/41] ADANIENSOL - ADANIGREEN  (HL=6.1min) ... trades=556  net_pnl=Rs-27463.0  calmar=-1.54
  ```

---

## 2. Logic Chain

1. **Flaw 1 (Unhedged Position)**: From Observation A (Cell 7), we see that the quantity traded is `this_qty = int(CAPITAL // price)` on the lagging asset, and `in_trade` only opens a long/short position on the lagging asset (`is_long = this_is_long`). No position is taken on the leading asset.
   * *Inference*: The strategy is not market-neutral. It is a directional bet on a single asset with no offsetting leg to hedge market beta.
   * *Conclusion*: This structural flaw explains why all 41 pairs show severe losses (Observation C), as any market-wide move generates losses on the unhedged asset that are not offset.
2. **Flaw 2 (Lookahead Bias in Backtest)**: In Stage 3, the fixed parameters $Q_{\beta}, Q_{\alpha}, R$, and the exit timeout half-life are loaded from `pairs_stage2_kalman_ou.csv`, which was estimated using the EM algorithm over the *entire* series in Stage 2.
   * *Inference*: The parameters used at time $t$ contain information about prices at times $> t$.
   * *Conclusion*: This represents a lookahead bias that invalidates the out-of-sample backtest.
3. **Flaw 3 (EM Update Matrix Dimensions)**: From Observation B (Line 131), the terms $G_{t-1}P_{t|T}\hat{\theta}_{t|T}^\top$ and $\hat{\theta}_{t|T}P_{t|T}G_{t-1}^\top$ multiply a 2x2 matrix by a 1x2 row vector on the right, and a 2x1 column vector by a 2x2 matrix on the right.
   * *Inference*: These multiplications are mathematically invalid and dimensionally inconsistent.
   * *Conclusion*: The EM algorithm update formulas in the plan are incorrect and cannot be coded as written without causing dimensional exceptions or numerical errors.

---

## 3. Caveats

- We did not execute the Stage 2 EM code directly because the code is executed on Kaggle to handle the size of `Master-Data-1min.sqlite` (2.3 GB) and the network is in `CODE_ONLY` mode.
- We assumed the Fyers API ticks are clean of large outliers before database insertion.

---

## 4. Conclusion

The LLM-WIKI Pairs Trading pipeline is currently non-viable for trading due to critical mathematical, statistical, and structural flaws. The backtesting results (showing 100% loss rates across all pairs) are a direct consequence of these flaws — specifically, the lack of market neutrality (unhedged single-sided trading) and high transaction fees. 

---

## 5. Verification Method

To verify these findings:
1. **Inspect Code Files**: View the Z-score calculation, entry logic, and position sizing in `Raw/Sources/attachments/stage3_pairs_backtest.ipynb` to confirm that only a single stock is traded (no hedging leg is opened on the leading stock).
2. **Review Output Logs**: Inspect `Raw/Sources/attachments/stage3-pairs-backtest.log` to confirm that all 41 pairs generated negative net returns and have low win rates (~10%).
3. **Matrix Dimensions**: Manually calculate the matrix multiplication dimensions for the EM $Q_{new}$ update formula in the Stage 2 Plan to verify the shape mismatch.
