> [!WARNING]
> **ARCHIVED & OBSOLETE**
> This file is part of the trial-and-error "Sketch" phase. 
> The mathematics and code herein may contain deprecated Expectation-Maximization loops or failed concepts.
> The final, verified truth is located in the `Soul/` directory.
> Tags: #archived-sketch #pairs-trading-prototype

# Stage 2 — Pairs Trading: Kalman Filter State-Space + OU Half-Life Estimation

**Status**: COMPLETED  
**Created**: 2026-06-03  
**Executed**: 2026-06-03 (Runtime: 17 mins / 1043s)  
**Dataset Input**: `utkarshpatelthefirst/pairs-stage1-pearson` (pairs_top500.csv)  
**Market Data**: `utkarshpatelthefirst/master-data-1min-db` (Master-Data-1min.sqlite, 2.3 GB)  
**Compute**: Kaggle CPU (4 cores, OPENBLAS_NUM_THREADS=1, full multiprocessing)  
**Output**: `pairs_stage2_kalman_ou.csv` → 124 Tradeable Pairs identified.

---

## Objective

Take the top 500 correlated pairs from Stage 1 and for each pair:

1. Load the session-continuous log-price series for both symbols from the SQLite DB.
2. Fit a **Kalman Filter State-Space model** to estimate the dynamic hedge ratio β_t and intercept α_t using the **Expectation-Maximization (EM) algorithm** to find optimal Q (process noise covariance) and R (measurement noise variance) — no guessing.
3. Extract the final **smoothed spread series** from the Kalman filter.
4. Fit an **Ornstein-Uhlenbeck (OU) process** to the spread to estimate:
   - Mean-reversion speed κ (per minute)
   - Long-run mean μ
   - OU volatility σ_OU
   - **Half-life in minutes** = ln(2) / κ
   - ADF test p-value (stationarity confirmation)
5. Save all parameters per pair to CSV.

---

## Methodology — Standard Quantitative Finance

### A. Data Preparation (Session-Continuous Log-Prices)

Per pair (symbol_a, symbol_b):

1. Query `ohlcv_1min` table for both symbols over the full available history.
2. Filter to NSE market hours only: **09:15 ≤ time ≤ 15:29 IST**.
3. Pivot to `(timestamp × symbol)` price matrix.
4. **Inner-join** on timestamps — only rows where both symbols have data.
5. Apply the session-open mask: set the 09:15 return to NaN (overnight gap). **Do NOT remove these price rows** — only the return at that bar is contaminated, not the price. The Kalman filter operates on **log-prices**, not returns.
6. Forward-fill at most 1 bar for legitimate microstructure gaps (single missing bar within a session). Drop any remaining NaNs.
7. Take `ln_price_a = ln(close_a)`, `ln_price_b = ln(close_b)`.

> **Note**: Unlike Stage 1 (which operated on log-returns for correlation), the Kalman filter here operates directly on **log-prices**. The spread `e_t = ln_price_a - β_t * ln_price_b - α_t` is stationary by design when β_t and α_t are correct.

---

### B. State-Space Model

The state vector is:

$$\theta_t = \begin{bmatrix} \beta_t \\ \alpha_t \end{bmatrix}$$

**State (Transition) Equation** — random walk prior:

$$\theta_t = \theta_{t-1} + w_t, \quad w_t \sim \mathcal{N}(0, Q)$$

$$Q = \begin{bmatrix} Q_{\beta\beta} & 0 \\ 0 & Q_{\alpha\alpha} \end{bmatrix}$$

Q is diagonal (β drift and α drift are independent). Off-diagonal terms are set to zero. Q is the key parameter — it controls how fast the hedge ratio is allowed to evolve.

**Observation (Measurement) Equation**:

$$y_t = H_t \theta_t + v_t, \quad v_t \sim \mathcal{N}(0, R)$$

Where:
- `y_t = ln_price_a(t)` — the dependent asset's log-price
- `H_t = [ln_price_b(t), 1]` — the row vector of observables
- `v_t` — scalar measurement noise (market microstructure noise)
- `R` — scalar measurement noise variance (1×1)

---

### C. Kalman Filter Cycle

**Initialization** (t=0):

$$\hat{\theta}_{0|0} = \text{OLS estimate of } [\beta, \alpha] \text{ over first 390 bars (1 trading day)}$$

$$P_{0|0} = \text{Cov}(\hat{\theta}_{OLS}) \cdot 10 \quad \text{(inflate for uncertainty)}$$

**Predict Step** (prior):

$$\hat{\theta}_{t|t-1} = \hat{\theta}_{t-1|t-1}$$

$$P_{t|t-1} = P_{t-1|t-1} + Q$$

**Update Step** (posterior):

$$e_t = y_t - H_t \hat{\theta}_{t|t-1} \quad \text{(innovation = spread)}$$

$$S_t = H_t P_{t|t-1} H_t^\top + R \quad \text{(innovation variance)}$$

$$K_t = P_{t|t-1} H_t^\top S_t^{-1} \quad \text{(Kalman Gain, 2×1 vector)}$$

$$\hat{\theta}_{t|t} = \hat{\theta}_{t|t-1} + K_t e_t$$

$$P_{t|t} = (I - K_t H_t) P_{t|t-1}$$

---

### D. EM Algorithm — Finding Optimal Q and R

**Why EM, not grid search**: EM finds the exact Q and R that maximise the log-likelihood of the observed price series. No trial-and-error, no arbitrary tuning knobs. (Run EM on every single 1-minute bar to ensure absolute rigorous precision, no subsampling).

**Initialization**: `Q = diag(1e-5, 1e-5)`, `R = var(ln_price_a) * 0.01`

**E-Step** — Forward-Backward (Kalman Smoother):

Run the Kalman filter **forward** over all T bars:
- Saves all `θ̂_{t|t}`, `P_{t|t}`, `θ̂_{t|t-1}`, `P_{t|t-1}`, `K_t`

Run the **RTS (Rauch-Tung-Striebel) Smoother backward** from T to 1:

$$G_t = P_{t|t} P_{t+1|t}^{-1}$$

$$\hat{\theta}_{t|T} = \hat{\theta}_{t|t} + G_t (\hat{\theta}_{t+1|T} - \hat{\theta}_{t+1|t})$$

$$P_{t|T} = P_{t|t} + G_t (P_{t+1|T} - P_{t+1|t}) G_t^\top$$

$$P_{t,t-1|T} = G_{t-1} P_{t|T} \quad \text{(cross-covariance, needed for Q update)}$$

**M-Step** — Closed-form Parameter Update:

Update R:

$$R_{new} = \frac{1}{T} \sum_{t=1}^{T} \left[ (y_t - H_t \hat{\theta}_{t|T})^2 + H_t P_{t|T} H_t^\top \right]$$

Update Q:

$$Q_{new} = \frac{1}{T} \sum_{t=1}^{T} \left[ P_{t|T} + \hat{\theta}_{t|T}\hat{\theta}_{t|T}^\top - G_{t-1}P_{t|T}\hat{\theta}_{t|T}^\top - \hat{\theta}_{t|T}P_{t|T}G_{t-1}^\top - P_{t,t-1|T} - \hat{\theta}_{t|T}\hat{\theta}_{t-1|T}^\top \right]$$

*(Full MLE closed-form. Diagonal of Q_{new} taken if enforcing diagonal structure.)*

**Convergence**: Repeat E → M until log-likelihood change < 1e-6, or max 100 iterations. Log-likelihood:

$$\mathcal{L} = -\frac{T}{2}\ln(2\pi) - \frac{1}{2}\sum_{t=1}^{T}\left[\ln|S_t| + e_t^2 / S_t\right]$$

---

### E. Spread Extraction

After EM convergence, run the Kalman filter one final time with the converged Q*, R*.

The **smoothed spread** (residual innovation series) is:

$$\text{spread}_t = y_t - H_t \hat{\theta}_{t|T} \quad \text{(using smoothed states)}$$

This spread is approximately zero-mean and stationary by design.

---

### F. Ornstein-Uhlenbeck (OU) Process Fitting

The spread is modelled as a continuous-time OU process:

$$dX_t = \kappa(\mu - X_t)dt + \sigma_{OU} \, dW_t$$

In discrete time at 1-minute intervals (Δt = 1):

$$X_t = \mu + (X_{t-1} - \mu)e^{-\kappa \Delta t} + \epsilon_t$$

Which reduces to a **first-order AR(1)** regression:

$$X_t = c + \phi X_{t-1} + \epsilon_t$$

**Mapping AR(1) → OU parameters**:

$$\phi = e^{-\kappa \Delta t} \implies \kappa = -\ln(\phi) \quad [\text{per minute}]$$

$$\mu = \frac{c}{1 - \phi}$$

$$\sigma_{AR}^2 = \text{Var}(\epsilon_t) \implies \sigma_{OU} = \sigma_{AR} \sqrt{\frac{-2\ln(\phi)}{1 - \phi^2}}$$

**Half-life** (in minutes):

$$t_{1/2} = \frac{\ln(2)}{\kappa} = \frac{-\ln(2)}{\ln(\phi)}$$

**Statistical tests on the spread**:

| Test | Null Hypothesis | Pass Condition |
|---|---|---|
| ADF (Augmented Dickey-Fuller) | Spread has unit root (non-stationary) | p-value < 0.05 (Maxlag capped at 20 to prevent unbounded computation) |
| Hurst Exponent | Random walk (H=0.5) | H < 0.5 (mean-reverting) |
| AR(1) φ significance | φ = 1 (no mean-reversion) | p-value < 0.05 |

---

### G. Output Schema

| Column | Description |
|---|---|
| `symbol_a`, `symbol_b` | Pair identifiers |
| `pearson_rho` | ρ from Stage 1 |
| `stage1_rank` | Rank from Stage 1 |
| `n_obs` | Number of aligned log-price bars used |
| `em_iterations` | EM iterations to convergence |
| `log_likelihood_final` | Final log-likelihood at convergence |
| `Q_beta` | Converged Q_{ββ} (β process noise variance) |
| `Q_alpha` | Converged Q_{αα} (α process noise variance) |
| `R` | Converged R (measurement noise variance) |
| `beta_mean` | Mean of smoothed β_t series |
| `beta_std` | Std dev of smoothed β_t (how much β drifted) |
| `alpha_mean` | Mean of smoothed α_t series |
| `spread_mean` | Mean of spread (should ≈ 0) |
| `spread_std` | Std dev of spread |
| `ou_kappa` | OU mean-reversion speed (per minute) |
| `ou_mu` | OU long-run mean |
| `ou_sigma` | OU volatility parameter |
| `half_life_minutes` | t_{1/2} = ln(2)/κ |
| `half_life_hours` | t_{1/2} in hours |
| `ar1_phi` | AR(1) coefficient φ |
| `ar1_phi_pvalue` | p-value for φ (H₀: φ=1, no mean-reversion) |
| `adf_stat` | ADF test statistic |
| `adf_pvalue` | ADF p-value (H₀: unit root) |
| `hurst_exponent` | Hurst exponent of spread (< 0.5 = mean-reverting) |
| `tradeable` | True if: adf_pvalue<0.05 AND 15 ≤ half_life_minutes ≤ 1440 |

**Tradeability filter**: `half_life_minutes >= 15` (not noise) AND `half_life_minutes <= 1440` (reverts within 1 trading week = ~3.8 days × 375 min/day).

---

## Compute Plan

- **All 500 pairs in parallel**: Use `multiprocessing.Pool` (Kaggle allows multiprocessing) with `cpu_count()` workers.
- **Multiprocessing Hardening**: Set `os.environ["OPENBLAS_NUM_THREADS"] = "1"` and DO NOT pre-compile Numba in the parent process to prevent fatal `fork` thread-deadlocks.
- **Per-pair runtime estimate**: ~2–5s (EM × 15 iterations max × forward-backward over 44k bars in Numba JIT)
- **Total estimate**: 500 pairs / 4 CPUs × ~3s each ≈ 6.25 min on Kaggle
- **Memory**: Each pair's price matrix is ~44k × 2 floats ≈ 0.7 MB. 4 concurrent = 2.8 MB. Trivial.
- **GPU**: Not used here — EM/Kalman is inherently sequential per pair. CPU multiprocessing is correct.
- **EM max iterations**: 15 (typically converges in 8-12). Convergence threshold: log-likelihood delta < 1e-5.
- **EM divergence guard**: If Q goes negative or NaN at any iteration → reset to prior and terminate.

---

## Error Guards

- `phi >= 1.0` → spread is non-stationary → set `tradeable=False`, `half_life_minutes=NaN`
- `phi <= 0.0` → explosive oscillation → set `tradeable=False`  
- EM non-convergence after 100 iters → save results anyway with `em_iterations=100`, flag `em_converged=False`
- Fewer than 5,000 aligned bars → skip pair, log to `skipped_pairs.csv`
- Any unhandled exception per pair → log error string to `errors` column, continue to next pair

---

## Files

| File | Location | Size estimate |
|---|---|---|
| `pairs_stage2_kalman_ou.csv` | Kaggle dataset + local attachment | ~500 rows × 25 cols |
| `skipped_pairs.csv` | Same dataset | Small |

---

## Kaggle Notebook Details

- **Title**: `Stage2 Pairs Kalman OU`
- **Slug**: `stage2-pairs-kalman-ou`
- **GPU**: Disabled (CPU-only multiprocessing)
- **Internet**: Enabled (for Kaggle API publish)
- **Dataset sources**: `utkarshpatelthefirst/master-data-1min-db`, `utkarshpatelthefirst/pairs-stage1-pearson`
- **Output dataset**: `utkarshpatelthefirst/pairs-stage2-kalman-ou`

---

## Connections
- [[pairs-trading-pipeline]]
- [[pairs-stage1-pearson]]
- [[master-data-1min-dataset]]
- [[session-continuous-returns]]
- [[log-return-computation]]
- [[kaggle-compute]]
