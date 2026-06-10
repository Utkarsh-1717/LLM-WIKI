> [!WARNING]
> **ARCHIVED & OBSOLETE**
> This file is part of the trial-and-error "Sketch" phase. 
> The mathematics and code herein may contain deprecated Expectation-Maximization loops or failed concepts.
> The final, verified truth is located in the `Soul/` directory.
> Tags: #archived-sketch #pairs-trading-prototype

# Pairs Trading QC & Forensic Audit (Sketch 3)

## 1. Introduction
This document serves as the living forensic log of the deep validation process. It records every discrepancy found between `sketch - 1` and `sketch - 2`, the mathematical root causes of historical failures (especially EM non-convergence), and the rigorous reasoning behind the finalized methodology.

## 2. Methodology & Rules
- **Top 5 Pairs Only**: To prevent computational bloat and allow for exact step-by-step mathematical tracing, all validation and testing is strictly restricted to the Top 5 pairs identified in Stage 1:
  1. `PFC` / `RECLTD`
  2. `BDL` / `MAZDOCK`
  3. `GRSE` / `MAZDOCK`
  4. `BANKBARODA` / `CANBK`
  5. `BPCL` / `HINDPETRO`
- **Unbiased Assessment**: No prior assumption is held as sacred. Both Sketch 1 and Sketch 2 are scrutinized equally.

---

## 3. Stage 1 Audit: Pearson Correlation & Alignment

### Alignment with the User's QC Rebuttals
Upon rigorous review of the `QC_Rebuttals_and_Context.md` document, we must correct a major misconception from the automated agent audit regarding Data Alignment. 

The automated agents flagged the lack of forward-filling (`ffill`) and the dropping of rows as a "flaw." However, the User's Rebuttal explicitly dictates that **this is INTENTIONAL.** In high-frequency pairs trading, comparing a stale, forward-filled price with a fresh price creates "phantom" spread movements. The strategy strictly requires that Asset A and Asset B prices are perfectly aligned at the exact same timestamp. Therefore, **forward-filling is mathematically banned**, and incomplete rows MUST be dropped.

The *only* true error in Sketch 1 & 2 was how the dropping was executed programmatically: it used a **Global Inner Join** (`dropna(how='any')` on the entire 500-symbol matrix) rather than a **Pairwise Inner Join**. 

### Flaws Discovered & Final Resolutions

**1. The Global vs. Pairwise Drop Bug (Corrected)**
- **Flaw**: Sketch 1 & 2 used `price_matrix.dropna(how='any', axis=0)`.
- **Impact**: If one illiquid stock out of 500 missed a 1-minute bar, that minute was deleted for all 499 other stocks. This caused catastrophic, unnecessary data loss. 
- **Resolution**: Adhering strictly to the User's Rebuttal (no forward-filling, strictly aligned timestamps), we simply compute correlation using `df.corr()`. Pandas computes correlation **pairwise by default**, meaning it naturally isolates Asset A and Asset B, drops any rows where either is `NaN`, and computes the correlation purely on their overlapping timestamps. No global `dropna` is required, and no phantom spreads are created.

**2. Overnight Gap Masking Bug**
- **Flaw**: The prior code tried to remove overnight gaps by masking `time == 09:15`. 
- **Impact**: If a stock didn't trade at exactly 09:15, its first bar might be 09:16. The 09:16 return would thus bridge against yesterday's 15:29 close, injecting a massive overnight gap return into the intraday series.
- **Resolution**: Dynamically mask the first return of the day by checking for a date change across the index (`dates != dates.shift(1)`), regardless of what time the first bar occurs.

**3. OOM Memory Leaks in Implementation**
- **Flaw**: Generating 37 million Python `datetime.time` objects.
- **Impact**: Memory spikes capable of instantly crashing a Kaggle CPU instance.
- **Resolution**: Use vectorized integer checks: `(dt.hour * 100 + dt.minute).between(915, 1529)`.

### Stage 1 Verdict
The underlying philosophy of Stage 1 (no forward-filling, strictly aligned timestamps, log-returns) is absolutely correct and rigorously defended by the User's Rebuttals. The only required updates are fixing the Python implementation of the pairwise drop and the dynamic overnight gap masking.

---

## 4. Stage 2 Audit: Kalman Filter & EM Convergence

### The Subagent Audit Team
- **Math/Stats Expert**: Derived the complete $Q_{new}$ expectation and the correct OLS initial covariance $P_0$.
- **Coding Expert**: Vectorized the $Q_{new}$ expansion using `np.einsum` to prevent OOM memory leaks and implemented the overnight gap scalar.
- **Integrity Guardian**: Pre-emptively verified that scaling $P$ (instead of $Q$) perfectly honors the user's Rebuttal #5 and rejected any proposed global dropping or forward-filling during Stage 2 data ingestion.

### Flaws Discovered in Sketch 1 & 2 (Stage 2)

**1. The EM Non-Convergence Root Cause (Incomplete $Q$ Matrix)**
- **Flaw**: Sketch 2 had almost 0% EM convergence. The mathematical root cause was found in the M-step update for the process noise covariance matrix ($Q$). The previous code literally forgot half the algebra required to calculate the expectation $E[(\theta_t - \theta_{t-1})(\theta_t - \theta_{t-1})^T]$. It used the smoothed means but omitted the auto-covariances and cross-covariances ($P_{t|T}$, $P_{t-1|T}$, $P_{t,t-1|T}$). 
- **Impact**: Using only squared state differences systematically underestimates the true process noise, causing the EM algorithm to prematurely converge to an over-confident (too small) $Q$. This destroyed parameter adaptability.
- **Resolution**: Derived the mathematically complete, dimensionally-correct expectation equation incorporating all $P$ covariance terms, strictly utilizing `np.einsum('ti,tj->ij')` to compute the outer products across the time axis in a single memory-safe vector step.

**2. The $P_0$ Intercept Lock**
- **Flaw**: $P_0$ (initial state uncertainty) was initialized using the sample covariance of the regressor matrix `X`. Because the intercept column in `X` is a constant vector of 1s, its sample variance is exactly `0`. 
- **Impact**: Setting the initial variance of the intercept to exactly 0 locks the parameter in place permanently. It neutralizes the Kalman filter's ability to adapt the intercept, forcing the beta coefficient to absorb all systemic drift.
- **Resolution**: $P_0$ must be correctly initialized using the **OLS residual variance** ($\hat{\sigma}^2_{OLS}$) multiplied by the inverse Fisher information matrix $(X^T X)^{-1}$. This unlocks the intercept variance correctly.

**3. Overnight Gap Scaling (Honoring Rebuttal #5)**
- **Flaw**: Previous code either ignored overnight gaps entirely (inflating $Q$) or tried to scale $Q$ across the weekend, which the user explicitly rejected because the macro-relationship doesn't wildly change overnight.
- **Resolution**: We strictly implemented the user's intended design. We inject a small "time-elapsed multiplier" strictly into the filter's prediction uncertainty matrix ($P_{pred}$) at the `09:15` open bar. This tells the filter "time passed, be slightly more adaptable this morning" without corrupting the core process noise ($Q$) that defines the stable macro-drift.

### Stage 2 Verdict: The EM Abort & The OU Pivot
**The Failure of EM:** Despite fixing the rigorous linear algebra of the Expectation-Maximization loop, testing on Kaggle proved that pure unconstrained EM is mathematically hostile to highly cointegrated 1-minute financial data. Without hard bounds, the parameters either explode into unidentifiability or collapse into floating-point underflow. Because the unvectorized 150,000-row RTS smoother loop takes ~17 minutes just to calibrate 5 pairs, this approach is fundamentally unviable for a 500-pair universe.

**The Solution:** We have explicitly abandoned EM in favor of **The Ornstein-Uhlenbeck (OU) Chunked Fit**. 
By running an initial robust OLS to extract the spread, we can fit a fast, vectorized AR(1) regression to find $\theta$ (mean reversion speed). By calculating this half-life across multiple temporal chunks (e.g., 4 chunks), we identify the "worst-case scenario" half-life. We then deterministically tune the Kalman Process Noise ($Q$) so the filter lags this worst-case reversion speed, guaranteeing it won't "eat" the spread. This reduces a 17-minute blind optimization into a sub-second deterministic closed-form calculation.

## 5. Stage 3 Audit: Execution & Signal Generation
*(To be populated next)*
