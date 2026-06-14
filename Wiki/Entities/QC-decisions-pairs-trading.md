---
title: QC-decisions-pairs-trading
tags:
- entity
topics:
- pairs-trading
sources: []
source_count: 0
created: '2026-06-10'
---
# QC-decisions-pairs-trading

> This entity directly mirrors the production methodology file: `[[QC-decisions-pairs-trading]]`

# QC Decisions — Intentional Design Choices
**Status**: ✅ PERMANENT REFERENCE  
**Source**: Sketch 2 `QC_Rebuttals_and_Context.md` + Sketch 3 `QC_Audit.md`

> These are **intentional design choices** that automated QC agents repeatedly flagged as "bugs." They are NOT bugs. Every item here has been explicitly decided and validated. Do not correct these in any future revision.

---

## 1. No Forward-Filling of Missing Prices

**What agents flagged**: Calling `.dropna()` before `.ffill()` renders forward-fill useless, causing data loss.

**Why it is intentional**:  
In high-frequency intraday pairs trading, Asset A's price at minute `t` must be a **live, fresh price** to be comparable with Asset B's live price at `t`. If Asset A had no trade at `t`, forward-filling from `t-1` creates a **phantom spread movement** — an artificial divergence that triggers a false entry signal on a price that cannot actually be executed.

**Rule**: Always drop incomplete rows. Both assets must have a fresh print at the exact same timestamp. Missing data is not a problem — phantom spreads are.

---

## 2. Pairwise Alignment Only — No Global Dropna

**What agents flagged**: Using `.dropna(how='any')` on a 500-symbol matrix causes data loss; should keep all common timestamps.

**The real bug**: The original code used `price_matrix.dropna(how='any', axis=0)` — this dropped any minute where even ONE of the 500 symbols had a missing bar. One illiquid stock with a gap destroyed that minute for all 499 other stocks. This was catastrophic and incorrect.

**The fix**: Leave NaN in place. Use `df.corr()` (Stage 1) and `.dropna(how='any')` **per pair** (Stage 2/3). Pandas computes pairwise correlation by naturally isolating each pair's overlapping timestamps.

---

## 3. Dynamic Overnight Gap Mask (Not Static 09:15)

**What agents flagged**: The 09:15 session mask is insufficient; some overnight gap returns are missed.

**Why the static mask fails**: If a stock's first bar of a given day is 09:16 (e.g., illiquid open), the 09:16 return bridges against yesterday's 15:29 close — an overnight gap return. A static `time == 09:15` mask completely misses this.

**The correct method**: Detect the first bar of every session via date-boundary crossing:
```python
dates = index.date
session_open_mask = np.array(dates) != np.roll(np.array(dates), 1)
```
This dynamically identifies the first bar of every session regardless of its timestamp.

---

## 4. OU Chunked Fit — Not EM — for Q Calibration

**What agents suggested**: Use the standard Expectation-Maximization (EM) algorithm to find Q and R optimally.

**Why EM is permanently rejected**:
- RTS backward smoother on 150,000 bars: ~17 minutes per pair — unviable
- On high-frequency cointegrated data, Q either explodes (unidentifiability) or collapses (float underflow)
- Even with the mathematically complete M-step (all cross-covariance terms), EM converged ~0% on the Top 5 pairs

**The production method**: Deterministic OU Chunked Fit — measures the pair's empirical mean-reversion speed across temporal chunks and analytically derives Q. Sub-second. Deterministic. Empirically validated.

---

## 5. P₀ Initialized via OLS Covariance — Not Sample Covariance of X

**What agents flagged (and what Sketch 1 got wrong)**: Initializing P₀ using the sample covariance of the regressor matrix X.

**The bug**: The regressor matrix X = [ln_price_b, 1]. The intercept column is a constant (all 1s) — its sample variance is exactly 0. Setting P₀ from the sample covariance of X locks the intercept's initial uncertainty to 0, permanently preventing the Kalman filter from updating the intercept.

**The fix**:
$$P_0 = \hat{\sigma}^2_{OLS} \cdot (X^\top X)^{-1}$$

This is the standard OLS parameter covariance — it correctly initializes both the hedge ratio and intercept uncertainties.

---

## 6. P_pred Doubled at 09:15 — Q Is NOT Scaled Overnight

**What agents suggested**: Scale Q across the overnight gap (more time = more drift).

**Why Q is not scaled**:  
The macro hedge relationship (β) between two cointegrated assets does not radically change overnight. β is a structural economic relationship — it reflects sector fundamentals, regulatory linkage, shared revenue drivers — none of which flip overnight. Scaling Q would permanently inflate process noise for the rest of the trading session.

**What we do instead**: At the 09:15 open bar, we inject uncertainty into the **prediction covariance P** only:
$$P_{pred} = P_{pred} \times 2$$

This tells the filter: "some time has passed; be slightly more adaptable this morning" — without corrupting Q, which governs the filter's long-run responsiveness.

---

## 7. Single-Sided Lagger Execution — Not Market-Neutral

**What agents flagged**: Strategy is not market-neutral; should trade both legs.

**Why single-sided is correct**:
1. **Transaction costs**: Trading two legs doubles brokerage, STT, exchange charges, and slippage. For intraday mean-reversion with 3-65 minute half-lives, two-sided execution consumes the entire gross edge.
2. **Alpha location**: The leader has already priced in the information. The alpha (catch-up potential) resides entirely in the lagging asset. A position in the leader has ~zero expected return and 100% of the cost.
3. **Risk profile**: Strictly intraday with 15:15 forced square-off. The overnight gap risk that market-neutral pairs trading hedges against does not apply.

**Classification**: This is a **relative-value directional strategy**, not strict statistical arbitrage. This is intentional.

---

## 8. Rolling Z-Score for Signal — Not Kalman Innovation Z

**What agents suggested**: Use the Kalman innovation Z-score ($Z = v_t / \sqrt{S_t}$) as the trading signal.

**Why the Kalman Z does not work**:  
The Kalman innovation variance $S_t = H_t P H_t^\top + R$ is dominated by the measurement noise R. In practice, $\sqrt{S_t}$ is much larger than the innovation $v_t$, causing the Kalman Z to rarely exceed 0.1 in absolute value — far too small to generate tradeable signals.

**The correct signal**: The rolling Z-score normalizes the spread against its own recent distribution:
$$Z_t = \frac{\text{spread}_t - \mu_{375}}{\sigma_{375}}$$

This correctly captures structural dislocations in the spread's own context.

---

## 9. ADF Threshold at p < 0.01 (99% Confidence)

In early sketches, pairs were accepted at p < 0.05. This was raised to **p < 0.01** (99% confidence in stationarity) for the production pair selection.

**Why**: At p < 0.05, ~5% of pairs pass purely by chance even if the spread is non-stationary. At the scale of 500 pairs, this could introduce ~6 spurious pairs. A 99% threshold eliminates this false-positive risk.

---

## 10. 15:15 PM Forced Square-Off

All open positions are forcibly closed at 15:15 PM regardless of Z-score state.

**Why 15:15 (not 15:28 or 15:29)**:
- **Broker MIS penalty**: Zerodha and most Indian brokers auto-square-off MIS positions starting at 15:20. A 15:15 cutoff provides a safety buffer.
- **Execution slippage**: The last 15 minutes of the NSE session are often illiquid and volatile. Exiting before 15:20 avoids adverse fills.
- **Overnight gap risk**: Any position held overnight converts to CNC and exposes the capital to the next day's open gap — a fundamentally different risk profile.

---

## 11. Reference-Driven Execution (No OLS Swapping)

**What agents hallucinated**: When detecting that Asset B is the lagger, agents attempted to physically swap the `A` and `B` arrays before the OLS/Kalman calculation to "fix" the regression math (forcing `B` to be regressed against `A`).

**Why it is rejected**: The pipeline's architecture dictates that `Asset A` is *always* the dependent variable and `Asset B` is *always* the independent variable for the spread calculation. The entry logic handles the directional flip perfectly. Swapping the arrays fundamentally breaks the structural comparability of the spread across the backtest.

**Rule**: NEVER modify the `Spread = A - beta*B` calculation order based on lagger detection. The arrays must remain in their original order. Only flip the *entry direction* (Long vs Short) based on which asset is the lagger.

---

## 12. No Sequential Python Loops for N > 10,000 Pairs (The 125h Timeout)

**What agents hallucinated**: Attempting to run a standard Python sequential `for t in range(...)` backtest loop over the entire 124,750 possible pair combinations of the NSE 500 matrix.

**Why it is rejected**: Python is interpreted, and iterating over millions of rows of DataFrame logic causes algorithmic times of ~3.6 seconds per pair. 124,750 pairs × 3.6s = 125 hours. Kaggle kernels enforce a strict 12-hour timeout. This approach mathematically guarantees failure.

**Rule**: Any execution engine meant to scale across combinatorial spaces (N > 10,000 pairs) MUST use Numba C++ compilation (`@njit`) to execute the state-dependent trading logic in microseconds, and MUST utilize `joblib.Parallel` to divide the workload across multiple CPU cores.

---

## 13. Lazy Evaluation for Heavy Statistical Tests

**What agents hallucinated**: Running the `adfuller` Engle-Granger Cointegration test (which takes ~1.5 seconds per pair) on every single pair _before_ checking if the pair is actually profitable.

**Why it is rejected**: Running a 1.5s test on 124,750 pairs takes 52 hours. Running the test on pairs that generate negative PnL is mathematically pointless.

**Rule**: Always use **Lazy Evaluation**. Execute the ultra-fast Numba backtest FIRST (9ms per pair). Then, ONLY run the heavy ADF Cointegration test on the subset of pairs that generated a strictly positive PnL. This slashes Kaggle compute time from 52 hours to 1.5 hours.

## 14. Lagger Entry Lockout (is_locked_out)

**What agents hallucinated**: When forced to square-off an open position at 15:15 (EOD Exit), agents allowed the execution engine to immediately re-enter the exact same trade on the very next minute (15:16 or the next morning at 09:15) if the Z-Score was still > 2.0.

**Why it is rejected**: This creates artificial "trade spam" that burns capital through continuous friction, inflating trade counts without capturing any mean-reverting movement. Once forced out, the engine must wait for the spread structure to physically reset before taking on new risk.

**Rule**: Always implement an `is_locked_out` boolean state. If a trade is forced to close at EOD, the engine is locked out from re-entering *until* the Z-Score naturally falls back into the neutral zone (`-1.0 < Z < 1.0`).

---

## 15. Exact Equity MIS Friction vs Flat Percentages

**What agents hallucinated**: Applying a generic flat `0.05%` friction applied evenly to the Gross PnL to simulate Indian retail brokerage costs.

**Why it is rejected**: A flat percentage mathematically breaks down because Zerodha Equity MIS brokerage is capped (`min(0.03%, ₹20)` per leg), while STT is only applied to the sell-side. Furthermore, applying an exit fee correctly depends entirely on whether the specific asset leg was shorted or bought, as this affects the STT multiplier.

**Rule**: All backtest engines must explicitly compute exact Zerodha Equity MIS friction using the discrete elements: Brokerage (capped at ₹20), STT (0.025% sell-side only), NSE Transaction Charges, 18% GST, SEBI, and Stamp Duty.

---

## Connections

- [[pairs-trading-strategy]]
- [[pairs-stage1-pearson]]
- [[pairs-stage2-kalman-ou]]
- [[stage3-execution-engine]]
- [[pairs-trading-strategy]]

- [[pairs-stage1b-cointegration]]
- [[continuous-ols-execution]]
- [[backtest-record-pairs-trading]]
- [[PM_125h_Kaggle_Timeout]]
- [[soul-production-compiler]]