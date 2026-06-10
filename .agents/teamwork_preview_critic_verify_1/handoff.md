# QC Review and Handoff Report: Pairs Trading Notebook Audit (Verification & Corrections)

This report presents the mathematical and logical verification of the identified flaws in the Stage 1 and Stage 2 pairs trading notebooks, along with their exact Python/NumPy corrections.

---

## 1. Observation

Direct observations from the notebooks located in `Raw/Sources/attachments/`:

### A. Data Alignment (Global Inner Joins)
- **Stage 1 (Pearson Correlation)** (`stage1-pairs-pearson-correlation.ipynb` Cell `8e23cf0b`):
  ```python
  price_matrix = df_trading.pivot(index='dt', columns='symbol', values='close')
  ...
  price_matrix = price_matrix.dropna(how='any', axis=0)
  ```
  *Observation*: The code performs a strict inner join on all symbols by calling `.dropna(how='any', axis=0)` before any forward-fill (`ffill(limit=1)`) logic is applied, which deviates from the plan's 1-bar tolerance.
- **Stage 2 (Kalman Filter)** (`stage2-pairs-kalman-ou.ipynb` Cell `8f8261b5`):
  ```python
  aligned = pd.DataFrame({"a": pa, "b": pb}).dropna(how="any")
  aligned = aligned.ffill(limit=1).dropna(how="any")
  ```
  *Observation*: The call to `.dropna(how="any")` on line 1 eliminates all rows with missing data. The subsequent `.ffill(limit=1)` is evaluated on a clean dataframe with zero NaNs, rendering the forward-fill entirely redundant.

### B. EM Process Noise $Q$ Matrix Update
- **Stage 2 (Kalman Filter)** (`stage2-pairs-kalman-ou.ipynb` Cell `aa9105d7`):
  ```python
  ts1 = ts[1:]; ts0 = ts[:-1]
  Ps1 = Ps[1:]; Pc_ = Pc[:T-1]
  oss = np.einsum("ti,tj->tij", ts1, ts1)
  osc = np.einsum("ti,tj->tij", ts1, ts0)
  Q_s = Ps1 + oss - Pc_ - osc
  ```
  *Observation*: The expression `Q_s = Ps1 + oss - Pc_ - osc` represents only a subset of the expectation matrix $\mathbb{E}[(\theta_t - \theta_{t-1})(\theta_t - \theta_{t-1})^\top \mid y_{1:T}]$, omitting the $\theta_{t-1}\theta_{t-1}^\top$ covariance/mean terms and the transpose cross-product terms.

### C. State Covariance Initialization $P_0$
- **Stage 2 (Kalman Filter)** (`stage2-pairs-kalman-ou.ipynb` Cell `aa9105d7`):
  ```python
  Xols = np.column_stack([yb[:n_i], np.ones(n_i)])
  th0, _, _, _ = np.linalg.lstsq(Xols, ya[:n_i], rcond=None)
  P0 = np.cov(Xols.T) * 10.0
  ```
  *Observation*: The initial state covariance $P_0$ is set to the sample covariance of the regressor matrix `Xols`. Since the second column of `Xols` is a constant vector of ones, its variance is zero, leading to `P0[1,1] = 0` (zero initial variance for the intercept state $\alpha$).

### D. ADF Stationarity Checks on Smoothed Spread
- **Stage 2 (Kalman Filter)** (`stage2-pairs-kalman-ou.ipynb` Cell `e2f4ea3f`):
  ```python
  try:
      adf = adfuller(s, maxlag=20, autolag="AIC", regression="c")
  ```
  where `s` is the dynamically smoothed spread series:
  ```python
  spread = ya - np.einsum("ti,ti->t", H_m, ts)
  ```
  *Observation*: The ADF test is performed on the Kalman smoothed spread, which dynamically updates parameters $\beta_t$ and $\alpha_t$ at every step to minimize prediction errors, forcing the spread to look stationary by construction.

### E. Return Gaps & Overnight Transitions
- **Stage 1 (Pearson Correlation)** (`stage1-pairs-pearson-correlation.ipynb` Cell `1eb47544`):
  Log-returns are computed on a price matrix that has already dropped missing timestamps. Any missing bar creates a "synthetic" return across a non-contiguous period.
- **Stage 2 (Kalman Filter)** (`stage2-pairs-kalman-ou.ipynb` Cell `8f8261b5`):
  No scale adjustments or partitioning are applied to the state equations across the overnight gap (15:29 to 09:15), treating the overnight transition as a standard 1-minute step.

---

## 2. Logic Chain

### A. Data Alignment Order
1. By executing `.dropna(how='any')` first, any row with a single NaN in any asset is permanently deleted.
2. If asset A has a price at $t_1$ and asset B has a price at $t_2$, but one is missing at the other's time, both rows are dropped.
3. If forward-fill was executed first, the last known price would populate the 1-bar gap, allowing both rows to be retained.
4. Hence, the current code defeats the 1-bar alignment tolerance.

### B. EM $Q$ Update Completeness
1. The state transition is $\theta_t = \theta_{t-1} + w_t$, with $w_t \sim \mathcal{N}(0, Q)$.
2. The M-step update for $Q$ requires calculating the smoothed expectation:
   $$\mathbb{E}[(\theta_t - \theta_{t-1})(\theta_t - \theta_{t-1})^\top \mid y_{1:T}] = \mathbb{E}[\theta_t \theta_t^\top \mid y_{1:T}] + \mathbb{E}[\theta_{t-1} \theta_{t-1}^\top \mid y_{1:T}] - \mathbb{E}[\theta_t \theta_{t-1}^\top \mid y_{1:T}] - \mathbb{E}[\theta_{t-1} \theta_t^\top \mid y_{1:T}]$$
3. In terms of smoothed states $\hat{\theta}_{t|T}$ and covariances $P_{t|T}$, this yields:
   $$Q_{s, t} = (P_{t|T} + \hat{\theta}_{t|T} \hat{\theta}_{t|T}^\top) + (P_{t-1|T} + \hat{\theta}_{t-1|T} \hat{\theta}_{t-1|T}^\top) - (P_{t, t-1|T} + \hat{\theta}_{t|T} \hat{\theta}_{t-1|T}^\top) - (P_{t, t-1|T}^\top + \hat{\theta}_{t-1|T} \hat{\theta}_{t|T}^\top)$$
4. The code:
   `Q_s = Ps1 + oss - Pc_ - osc`
   omits the second term (`Ps0 + os00`) and the fourth term (the transpose of the third term), leading to an mathematically incomplete and incorrect covariance matrix.

### C. State Covariance $P_0$ Initialization
1. In the OLS regressor matrix $X$, the second column is a constant vector of ones.
2. The variance of a constant is zero: $\text{Var}(1) = 0$.
3. Thus, `np.cov(Xols.T)` produces a covariance matrix where all elements in the second row and column are 0.
4. Setting $P_0$ to this matrix means the intercept state covariance starts at 0, representing absolute parameter certainty.
5. In a Kalman Filter, starting with zero variance locks the intercept parameter, preventing it from adjusting to prediction errors (Kalman Gain $K_{\alpha} = 0$), forcing the filter to absorb all initial discrepancies through the $\beta$ state.
6. The mathematically correct initial state covariance is the parameter estimator covariance $\text{Cov}(\hat{\theta}_{\text{OLS}}) = \sigma^2 (X^\top X)^{-1}$, where $\sigma^2$ is the OLS residual variance.

### D. ADF Validity on Smoothed Spread
1. The Kalman state equation allows states $\beta_t$ and $\alpha_t$ to drift continuously via process noise $Q$.
2. The smoothed spread is defined as the observation residual: $s_t = y_{a, t} - \beta_t y_{b, t} - \alpha_t$.
3. By construction, the filter dynamically adjusts $\beta_t$ and $\alpha_t$ to minimize this residual. Even if $y_a$ and $y_b$ are independent drift-less random walks, the states will track the path of the random walks, making $s_t$ appear as a stationary white-noise process.
4. Performing an ADF test on $s_t$ results in an artificially high rejection rate of the unit root (yielding false-positive cointegration signals). Cointegration requires a *static* linear relationship to be stationary.

### E. Return Gaps & Overnight Transitions
1. Dropping timestamps before computing returns in Stage 1 causes $\Delta t > 1$ minute for gaps, inflating return variance.
2. Across the overnight gap (15:29 to 09:15), the true parameters drift significantly. The Kalman filter, expecting a 1-minute step, interprets the overnight price jump as a standard 1-minute observation shock.
3. This inflates the estimated baseline process noise $Q$ in the EM loop, making the filter over-responsive intraday and causing the spread's half-life to collapse (~9 minutes).

---

## 3. Caveats

- **Time-step assumption**: We assume the timestamps in the database represent consecutive 1-minute intervals during market hours.
- **Multimodal assets**: Different asset types may exhibit different overnight drift dynamics. The multiplier $M_{\text{overnight}} = 15.0$ is a standard heuristic and may require tuning via cross-validation.

---

## 4. Conclusion

- **Verdict**: **REQUEST_CHANGES**
- **Risk Assessment**: **HIGH** (The current mathematical bugs invalidate parameter tracking, distort statistical testing, and cause artificial model collapse).

### Formulated Python/NumPy Corrections

#### A. Data Alignment Fixes
**Stage 1 Alignment (`stage1-pairs-pearson-correlation.ipynb` Cell `8e23cf0b`)**:
```python
# Pivot to index = IST datetime, columns = symbol
price_matrix = df_trading.pivot(index='dt', columns='symbol', values='close')

# Pass 1: Drop symbols with < 80% coverage
coverage = price_matrix.notna().sum() / len(price_matrix)
sparse_symbols = coverage[coverage < 0.80].index.tolist()
if sparse_symbols:
    price_matrix = price_matrix.drop(columns=sparse_symbols)

# Pass 2: Forward-fill microstructure gaps by at most 1 bar FIRST, then drop remaining NaNs
price_matrix = price_matrix.ffill(limit=1).dropna(how='any', axis=0)
```

**Stage 2 Alignment (`stage2-pairs-kalman-ou.ipynb` Cell `8f8261b5`)**:
```python
aligned = pd.DataFrame({"a": pa, "b": pb})
# Forward-fill up to 1 bar FIRST, then drop remaining NaNs
aligned = aligned.ffill(limit=1).dropna(how="any")
```

#### B. Expectation-Maximization $Q$ Update
In `stage2-pairs-kalman-ou.ipynb` Cell `aa9105d7` inside `em_kalman(ya_full, yb_full)`:
```python
        ts1 = ts[1:]; ts0 = ts[:-1]
        Ps1 = Ps[1:]; Ps0 = Ps[:-1]; Pc_ = Pc[:T-1]
        
        # Smooth state outer products
        oss = np.einsum("ti,tj->tij", ts1, ts1)          # E[theta_t] E[theta_t]^T
        os00 = np.einsum("ti,tj->tij", ts0, ts0)         # E[theta_{t-1}] E[theta_{t-1}]^T
        osc_t0_t1 = np.einsum("ti,tj->tij", ts0, ts1)    # E[theta_{t-1}] E[theta_t]^T
        
        # Complete cross-covariance term E[theta_{t-1} theta_t^T | y]
        term3 = Pc_ + osc_t0_t1
        
        # Full expansion of transition residuals variance
        Q_s = (Ps1 + oss) + (Ps0 + os00) - term3 - np.transpose(term3, (0, 2, 1))
        
        # Scale each transition by the overnight multiplier vector d
        Q_s_weighted = Q_s / d[:, np.newaxis, np.newaxis]
        Q_n = np.mean(Q_s_weighted, axis=0)
        
        # Force symmetry and diagonalize
        Q_n = (Q_n + Q_n.T) / 2
        Q_n = np.diag(np.diag(Q_n))
        Q_n = np.clip(Q_n, 1e-12, None)
```

#### C. Initial State Covariance $P_0$
In `stage2-pairs-kalman-ou.ipynb` Cell `aa9105d7` inside `kalman_smoother(ya, yb, Q, R)`:
```python
    Xols = np.column_stack([yb[:n_i], np.ones(n_i)])
    th0, _, _, _ = np.linalg.lstsq(Xols, ya[:n_i], rcond=None)
    y_pred = Xols @ th0
    resid = ya[:n_i] - y_pred
    sigma2 = np.sum(resid**2) / (n_i - 2)
    XTX_inv = np.linalg.inv(Xols.T @ Xols)
    P0 = sigma2 * XTX_inv * 10.0  # Scale by 10 for diffuse prior
```

#### D. Guarding against Negative or Zero $\phi$
In `stage2-pairs-kalman-ou.ipynb` Cell `e2f4ea3f` inside `fit_ou(spread)`:
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

#### E. Overnight Price Gap Transition
In `stage2-pairs-kalman-ou.ipynb` Cell `7965c676` inside `_kf_forward`:
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
    ll  = 0.0
    LOG2PI = 1.8378770664093453
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
    # Pass to em_kalman and kalman_smoother
```

---

## 5. Verification Method

To independently verify the corrections:
1. Run the python script `/storage/emulated/0/Quant/LLM-WIKI/.agents/teamwork_preview_critic_verify_1/verify_critic_math.py`:
   - It performs shape and algebraic correctness checks on the proposed updates.
   - It asserts that `P0` has non-zero intercept variance.
   - It asserts that `Q_n` is symmetric and computes correct dimensions.
2. Invalidation conditions:
   - If the date transitions do not match `MARKET_OPEN` timestamps, `is_new_day` will fail to identify overnight gaps.
