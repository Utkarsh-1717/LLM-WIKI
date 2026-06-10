> [!WARNING]
> **ARCHIVED & OBSOLETE**
> This file is part of the trial-and-error "Sketch" phase. 
> The mathematics and code herein may contain deprecated Expectation-Maximization loops or failed concepts.
> The final, verified truth is located in the `Soul/` directory.
> Tags: #archived-sketch #pairs-trading-prototype

# Full Methodology: Pairs Trading (Sketch 3 Final)

> **Status**: DRAFT (Stage 1 Verified. Stage 2 Pending)

---

## Stage 1: Data Alignment & Pearson Correlation

### 1. Objective
Identify the most robustly co-moving equity pairs using 1-minute OHLCV data. All analysis is restricted to the Top 5 pairs extracted for the validation phase.

### 2. The Math of Correlation
We rely exclusively on the Pearson correlation coefficient ($\rho$) of **log-returns**, not raw prices.
- **Why Log-Returns?**: Raw prices are typically $I(1)$ (non-stationary random walks). Correlating two random walks leads to spurious correlation. Log-returns $r_t = \ln(P_t / P_{t-1})$ are $I(0)$ (stationary).
- **Scale Invariance**: Pearson correlation is invariant to linear transformations. No multipliers or scaling factors are applied to the returns.

### 3. Rigorous Data Cleansing Rules (Guided by QC Rebuttals)
To prevent contamination, the following strict rules are applied mathematically, specifically honoring the User's explicit design choices in the `QC_Rebuttals_and_Context.md`:

1. **Intraday Boundary Enforcement**: All pre-market, post-market, and non-trading hours are unconditionally excluded. Only bars where `09:15 <= time <= 15:29` are retained.
2. **The Forward-Filling Ban (Intentional Design)**: If an asset lacks a trade for a specific minute, the price remains `NaN`. Forward-filling is explicitly banned because comparing a stale, forward-filled price with a fresh price creates "phantom" spread movements that would trigger false entries.
3. **Pairwise Nulling (Fixing the Global Drop Bug)**: Because we banned forward-filling, previous code versions executed a global inner join (`dropna(how='any')` on all 500 stocks) which caused catastrophic data destruction. The mathematically correct execution is a **Pairwise Inner Join**. We leave `NaN`s intact in the price matrix. When calculating correlation, pandas' `df.corr()` naturally calculates it pairwise, isolating Asset A and Asset B and computing the correlation purely on their specific overlapping timestamps.
4. **Dynamic Overnight Gap Annihilation**: The first recorded return of any trading session bridges against the previous day's close. This is an overnight gap, not an intraday return. Instead of statically masking `09:15` (which fails if the 09:15 bar is missing), the first return of *every* session is forced to `NaN` by detecting date boundary crossings in the index (`dates != dates.shift(1)`).

### 4. Selection Criteria
- **Minimum Observations**: Pairs with fewer than 5,000 overlapping valid 1-minute bars are excluded to prevent small-sample statistical noise.
- **Ranking**: Pairs are sorted descending by the absolute value of their Pearson correlation coefficient.

---

## Stage 2: Ornstein-Uhlenbeck Calibration & Kalman Parameter Tuning

### 1. Objective
Extract the "true" mean-reversion half-life of the pairs using robust, closed-form statistics, and dynamically calibrate the Kalman Filter's Process Noise ($Q$) so that it filters macro-noise without "eating" the tradable intraday spread.

### 2. The Failure of Expectation-Maximization
Traditional Expectation-Maximization (EM) on hidden state-space models is computationally hostile and mathematically unidentifiable for high-frequency 1-minute financial data. Attempting to blindly optimize $Q$ and $R$ across 150,000 unvectorized sequential bars leads to severe computational bottlenecks and parameter collapse. We explicitly bypass EM in favor of direct, deterministic Ornstein-Uhlenbeck modeling.

### 3. Step 1: Chunked AR(1) Spread Extraction
To determine how fast the pair actually reverts, we break the valid trading data into $K$ equal temporal chunks (e.g., 4 chunks). For each chunk:
1. **Initial OLS**: We run Ordinary Least Squares ($y_t = \beta x_t + \alpha + \epsilon_t$) to extract a static baseline spread: $S_t = y_t - (\beta x_t + \alpha)$.
2. **Autoregressive Fit**: We fit the spread to an AR(1) process:
   $$S_t = \theta S_{t-1} + \eta_t$$
3. **Half-Life Calculation**: If $0 < \theta < 1$ (the spread is mean-reverting), we calculate the half-life in minutes:
   $$HL_k = -\frac{\ln(2)}{\ln(\theta)}$$

### 4. Step 2: The Worst-Case Horizon Tuning
By extracting the half-life across multiple chunks, we obtain a distribution of mean-reversion speeds (e.g., Chunk 1: 45 min, Chunk 2: 52 min, Chunk 3: 65 min).
- We identify the **worst-case scenario** (the slowest mean-reversion half-life in the distribution, e.g., 65 minutes).
- **The $Q$ Scale Factor**: The purpose of the Kalman Filter is to track the *macro* drift. If the filter adapts faster than 65 minutes, it will track the intraday noise and the spread will read as `0`, generating no trades. Therefore, we analytically tune the process noise $Q$ such that the Kalman Filter's effective lookback horizon is strictly *slower* than the worst-case half-life.

### 5. Step 3: Initialization & The Gap Protocol
With $Q$ analytically defined:
- **Initial Covariance ($P_0$)**: Initialized using the OLS parameter standard errors: $P_0 = \hat{\sigma}^2_{OLS} (X^T X)^{-1}$.
- **Overnight Gap Protocol**: Following the `QC_Rebuttals`, at the $09:15$ open bar of every trading session, we inject a strictly controlled time-elapsed multiplier into the prediction uncertainty matrix ($P_{pred} = P_{pred} \times \text{gap\_multiplier}$). We explicitly do NOT scale the process noise $Q$ across the weekend, preserving the macro-drift anchor.

## Stage 3: Backtesting & Signal Logic
*(Pending Audit Validation)*
