> [!WARNING]
> **ARCHIVED & OBSOLETE**
> This file is part of the trial-and-error "Sketch" phase. 
> The mathematics and code herein may contain deprecated Expectation-Maximization loops or failed concepts.
> The final, verified truth is located in the `Soul/` directory.
> Tags: #archived-sketch #pairs-trading-prototype

# Pairs Trading Stage 1 & 2 Code Audit Report

## 1. Executive Summary

This report presents a rigorous quality control (QC) audit of the implementation code of **Stage 1 (Pearson Correlation Screening)** and **Stage 2 (Kalman Filter State-Space & OU Parameter Estimation)** of the Pairs Trading pipeline. 

Five critical mathematical, statistical, and data alignment bugs were identified in the Kaggle notebooks used for generation of pairs and model parameters:
1. **Redundant/Missing Data Alignment (Global Inner Joins)**: Stage 1 lacks a 1-bar forward-fill tolerance, causing over 10% data loss. Stage 2 executes `.dropna()` before `.ffill()`, rendering the forward-fill entirely redundant.
2. **Mathematically Incomplete EM Q Updates**: The vectorized M-step update for the process noise covariance matrix $Q$ omits crucial terms, leading to incorrect covariance dynamics.
3. **Invalid OLS Initialization for Intercept State**: The initial state covariance $P_0$ is initialized with the covariance of the regressor matrix `Xols` instead of the OLS estimator parameter covariance. Since one column of the regressors is a constant vector of ones, its variance is zero, resulting in zero initial uncertainty for the intercept state $\alpha$ (which locks the state parameter).
4. **Invalid ADF Stationarity Checks**: Augmented Dickey-Fuller tests are run on dynamically smoothed Kalman spreads. Because parameters update at every bar to minimize prediction errors, the spread is forced to be stationary by construction, generating false cointegration signals.
5. **Lack of Overnight Price Gap Scaling**: Consecutive intraday bars are concatenated across trading days without partitioning or scaling the Kalman state transitions, causing the large overnight gaps to be interpreted as 1-minute shocks. This inflates process noise covariance $Q$ and collapses the spread half-life.

These code deviations explain the anomalous results documented in the LLM-WIKI, such as extremely short spread half-lives (median ~9 minutes) and rapid, noisy parameter adjustments.

---

## 2. Audited Kaggle Notebooks

The audit traced the logic directly inside the fetched Kaggle notebooks:
1. **Stage 1 (Pearson Correlation)**:
   - **Kaggle Kernel**: `utkarshpatelthefirst/stage1-pairs-pearson-correlation`
   - **Local Path**: `Raw/Sources/attachments/stage1-pairs-pearson-correlation.ipynb`
   - **Focus**: Timezone conversions, global inner joins, return calculations, and correlation screening.
2. **Stage 2 (Kalman Filter & OU Parameter Estimation)**:
   - **Kaggle Kernel**: `utkarshpatelthefirst/stage2-pairs-kalman-ou`
   - **Local Path**: `Raw/Sources/attachments/stage2-pairs-kalman-ou.ipynb`
   - **Focus**: State-space equations, Expectation-Maximization (EM) loop, Rauch-Tung-Striebel (RTS) smoother, Ornstein-Uhlenbeck (OU) parameter estimation, and Augmented Dickey-Fuller (ADF) stationarity screening.

---

## 3. Detailed Verification against Documented Math

### A. Data Alignment (Global Inner Joins)
- **Documented Math/Rule**: `Plans/stage-1-pairs-trading-pearson-correlation.md` (lines 84-86) and `Plans/stage-2-pairs-trading-kalman-filter-state-space.md` (lines 41-42) specify that microstructure gaps must be handled by forward-filling at most 1 bar before dropping remaining NaNs.
- **Code implementation**:
  - In Stage 1 (Cell `8e23cf0b`):
    ```python
    price_matrix = df_trading.pivot(index='dt', columns='symbol', values='close')
    ...
    price_matrix = price_matrix.dropna(how='any', axis=0)
    ```
    No forward-fill is implemented, leading to a strict inner join on all N symbols that destroys over 10% of overlapping timestamps.
  - In Stage 2 (Cell `8f8261b5` in `get_pair_log_prices(sym_a, sym_b)`):
    ```python
    aligned = pd.DataFrame({"a": pa, "b": pb}).dropna(how="any")
    aligned = aligned.ffill(limit=1).dropna(how="any")
    ```
    The `.dropna(how="any")` on line 1 deletes any row with NaNs, meaning `aligned.ffill(limit=1)` on line 2 runs on a dataset with zero NaNs, rendering the forward-fill useless.

### B. EM Matrix Updates
- **Documented Math**: `Plans/stage-2-pairs-trading-kalman-filter-state-space.md` (line 131) defines the Expectation-Maximization update for process noise covariance matrix $Q_{new}$. For a random-walk parameter transition model $\theta_t = \theta_{t-1} + w_t$ where $w_t \sim \mathcal{N}(0, Q)$, the expectation is expanded as:
  $$Q_{\text{correct}, t} = \mathbb{E}[(\theta_t - \theta_{t-1})(\theta_t - \theta_{t-1})^\top \mid y_{1:T}] = (P_{t|T} + \hat{\theta}_{t|T} \hat{\theta}_{t|T}^\top) + (P_{t-1|T} + \hat{\theta}_{t-1|T} \hat{\theta}_{t-1|T}^\top) - (P_{t, t-1|T} + \hat{\theta}_{t|T} \hat{\theta}_{t-1|T}^\top) - (P_{t, t-1|T}^\top + \hat{\theta}_{t-1|T} \hat{\theta}_{t|T}^\top)$$
- **Code implementation** (Stage 2 Cell `aa9105d7` in `em_kalman(ya_full, yb_full)`):
  ```python
  ts1 = ts[1:]; ts0 = ts[:-1]
  Ps1 = Ps[1:]; Pc_ = Pc[:T-1]
  oss = np.einsum("ti,tj->tij", ts1, ts1)
  osc = np.einsum("ti,tj->tij", ts1, ts0)
  Q_s = Ps1 + oss - Pc_ - osc
  ```
  This code only computes the terms $(Ps1 + oss)$ corresponding to $\mathbb{E}[\theta_t \theta_t^\top]$ and $(Pc\_ + osc)$ corresponding to $\mathbb{E}[\theta_t \theta_{t-1}^\top]$. It completely omits the terms for $\mathbb{E}[\theta_{t-1}\theta_{t-1}^\top]$ and $\mathbb{E}[\theta_{t-1}\theta_t^\top]$, representing only half the expectation matrix. This makes the estimated process noise $Q$ mathematically invalid.

### C. Initial State Covariance $P_0$
- **Documented Math**: `Plans/stage-2-pairs-trading-kalman-filter-state-space.md` (line 80) states that initial state covariance $P_0$ must be the covariance of the OLS estimator parameter estimates, scaled for uncertainty.
- **Code implementation** (Stage 2 Cell `aa9105d7` in `kalman_smoother(ya, yb, Q, R)`):
  ```python
  Xols = np.column_stack([yb[:n_i], np.ones(n_i)])
  th0, _, _, _ = np.linalg.lstsq(Xols, ya[:n_i], rcond=None)
  P0 = np.cov(Xols.T) * 10.0
  ```
  This code calculates the sample covariance of the regressor matrix $X$. Since the second column of $X$ is a constant vector of ones, `np.cov(Xols.T)` sets all elements of the second column and row to zero. Consequently, $P_0[1,1] = 0$. This sets the initial variance of the intercept $\alpha$ to zero (absolute certainty), locking the state parameter at start and preventing the filter from adapting to early prediction errors.

### D. ADF Stationarity Check
- **Documented Math**: `Plans/stage-2-pairs-trading-kalman-filter-state-space.md` (line 183) specifies checking the Augmented Dickey-Fuller (ADF) test statistic on the spread to confirm stationarity ($p < 0.05$).
- **Code implementation** (Stage 2 Cell `e2f4ea3f`):
  The ADF test is executed on the smoothed Kalman spread series `s = ya - np.einsum("ti,ti->t", H_m, ts)`. Because the Kalman filter dynamically updates $\beta_t$ and $\alpha_t$ at every single bar to minimize prediction errors, the spread is *forced* to be stationary by design. Running ADF on a dynamically smoothed spread is statistically invalid and yields false-positive cointegration signals.

### E. Return Computations & Overnight Price Gaps
- **Documented Math**: `Plans/stage-1-pairs-trading-pearson-correlation.md` (lines 63-76) states that returns must be continuous intraday returns and overnight return gap contamination must be removed.
- **Code implementation**:
  - In Stage 1 (Cell `1eb47544`):
    Dropping timestamps due to strict inner join before computing returns creates synthetic return gaps with artificially high variance, violating homoscedasticity.
  - In Stage 2 (Cell `8f8261b5` / `7965c676`):
    The filter runs across day boundaries (15:29 to 09:15) without scaling process noise or resetting state covariance. The large overnight price jumps are interpreted as a standard 1-minute transition shock, inflating the estimated process noise $Q$ and collapsing the spread half-life.

---

## 4. Proposed Code Corrections

### A. Data Alignment Fixes
**Stage 1 Alignment (`stage1-pairs-pearson-correlation.ipynb` Cell `8e23cf0b`)**:
```python
# Pivot: index = IST datetime, columns = symbol
price_matrix = df_trading.pivot(index='dt', columns='symbol', values='close')

# Filter symbols with < 80% coverage to protect alignment from extremely sparse tickers
coverage = price_matrix.notna().sum() / len(price_matrix)
sparse_symbols = coverage[coverage < 0.80].index.tolist()
if sparse_symbols:
    price_matrix = price_matrix.drop(columns=sparse_symbols)

# Forward-fill microstructure gaps by at most 1 bar FIRST, then drop remaining NaNs
price_matrix = price_matrix.ffill(limit=1).dropna(how='any', axis=0)
```

**Stage 2 Alignment (`stage2-pairs-kalman-ou.ipynb` Cell `8f8261b5`)**:
```python
aligned = pd.DataFrame({"a": pa, "b": pb})
# Forward-fill up to 1 bar FIRST, then drop remaining NaNs
aligned = aligned.ffill(limit=1).dropna(how="any")
```

### B. Expectation-Maximization $Q$ Update Fix
**Stage 2 EM Update (`stage2-pairs-kalman-ou.ipynb` Cell `aa9105d7` inside `em_kalman(ya_full, yb_full)`)**:
```python
        ts1 = ts[1:]; ts0 = ts[:-1]
        Ps1 = Ps[1:]; Ps0 = Ps[:-1]; Pc_ = Pc[:T-1]
        
        # Smooth state outer products
        oss = np.einsum("ti,tj->tij", ts1, ts1)          # E[theta_t] E[theta_t]^T
        os00 = np.einsum("ti,tj->tij", ts0, ts0)         # E[theta_{t-1}] E[theta_{t-1}]^T
        osc_t0_t1 = np.einsum("ti,tj->tij", ts0, ts1)    # E[theta_{t-1}] E[theta_t]^T
        
        # Cross-covariance term E[theta_{t-1} theta_t^T | y]
        term3 = Pc_ + osc_t0_t1
        
        # Complete expansion of transition residuals variance
        Q_s = (Ps1 + oss) + (Ps0 + os00) - term3 - np.transpose(term3, (0, 2, 1))
        
        # Scale each transition by the overnight multiplier vector d
        Q_s_weighted = Q_s / d[:, np.newaxis, np.newaxis]
        Q_n = np.mean(Q_s_weighted, axis=0)
        
        # Force symmetry and diagonalize
        Q_n = (Q_n + Q_n.T) / 2
        Q_n = np.diag(np.diag(Q_n))
        Q_n = np.clip(Q_n, 1e-12, None)
```

### C. Initial State Covariance $P_0$ Fix
**Stage 2 Initialization (`stage2-pairs-kalman-ou.ipynb` Cell `aa9105d7` inside `kalman_smoother(ya, yb, Q, R)`)**:
```python
    Xols = np.column_stack([yb[:n_i], np.ones(n_i)])
    th0, _, _, _ = np.linalg.lstsq(Xols, ya[:n_i], rcond=None)
    y_pred = Xols @ th0
    resid = ya[:n_i] - y_pred
    sigma2 = np.sum(resid**2) / (n_i - 2)
    XTX_inv = np.linalg.inv(Xols.T @ Xols)
    P0 = sigma2 * XTX_inv * 10.0  # Scale by 10.0 for diffuse prior
```

### D. Guarding against Negative or Zero $\phi$ in OU Parameter Mapping
**Stage 2 OU Fitting (`stage2-pairs-kalman-ou.ipynb` Cell `e2f4ea3f` inside `fit_ou(spread)`)**:
```python
    x = s[:-1]; y = s[1:]
    X = np.column_stack([np.ones(len(x)), x])
    b, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    c, phi = float(b[0]), float(b[1])
    
    # Reject non-stationary or non-mean-reverting AR(1) parameters
    if phi <= 0.0 or phi >= 1.0 or not np.isfinite(phi):
        return _nan()
        
    resid  = y - X @ b
    sig2   = float(np.sum(resid**2) / (len(y) - 2))
    XTXi   = np.linalg.inv(X.T @ X)
    se_phi = float(np.sqrt(sig2 * XTXi[1, 1]))
    t_phi  = (phi - 1.0) / se_phi
    p_phi  = float(t_dist.cdf(t_phi, df=len(y) - 2))
    
    kappa  = -np.log(phi)
    mu     = c / (1.0 - phi)
    s_ar   = float(np.std(resid))
    sig_ou = s_ar * np.sqrt(-2.0 * np.log(phi) / (1.0 - phi**2))
    hl     = np.log(2.0) / kappa
    equil  = 3.0 * hl
    s_stat = sig_ou / np.sqrt(2.0 * kappa)
```

### E. Overnight Price Gap Transition Fix
Pass an `is_new_day` boolean mask to the Kalman Filter loop:
```python
@njit
def _kf_forward(ya, yb, q1, q2, R_val, th0, P0, is_new_day, mult_overnight=15.0):
    T   = len(ya)
    tf  = np.zeros((T, 2))
    Pf  = np.zeros((T, 2, 2))
    tp  = np.zeros((T, 2))
    Pp  = np.zeros((T, 2, 2))
    e_a = np.zeros(T)
    S_a = np.zeros(T)
    K_a = np.zeros((T, 2))
    th0b = th0[0]; th1b = th0[1]
    p00 = P0[0, 0]; p01 = P0[0, 1]; p10 = P0[1, 0]; p11 = P0[1, 1]
    for t in range(T):
        h0 = yb[t]; h1 = 1.0
        # Propagate covariance with scaled noise across overnight gap
        if t > 0 and is_new_day[t]:
            pp00 = p00 + q1 * mult_overnight
            pp11 = p11 + q2 * mult_overnight
        else:
            pp00 = p00 + q1
            pp11 = p11 + q2
        pp01 = p01
        pp10 = p10
        ...
```
In `process_pair(args)`:
```python
    is_new_day = (aligned.index.time == MARKET_OPEN).values
    # Pass is_new_day to em_kalman and kalman_smoother
```

---

## 5. Connections

- [[pairs-stage1-pearson]]
- [[pairs-stage2-kalman-ou]]
- [[pairs-trading-pipeline]]
