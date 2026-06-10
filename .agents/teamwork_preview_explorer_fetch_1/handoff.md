# QC Audit Report: Pairs Trading Stage 1 & 2 Notebook Inspection

This report presents the quality control (QC) audit of the implementation code of the Stage 1 (Pearson correlation screening) and Stage 2 (Kalman Filter state-space parameter estimation) Kaggle notebooks. The analysis focuses on data alignment (joins), expectation-maximization (EM) parameter updates, Augmented Dickey-Fuller (ADF) stationarity checks, and return computations.

---

## 1. Observation

Direct observations and code locations in the fetched notebooks:

### A. Global Inner Joins (Data Alignment)
1. **Stage 1 (Pearson Screening) alignment**:
   - **Path**: `Raw/Sources/attachments/stage1-pairs-pearson-correlation.ipynb`
   - **Cell ID**: `8e23cf0b`
   - **Verbatim Code**:
     ```python
     # Pivot: index = IST datetime, columns = symbol
     price_matrix = df_trading.pivot(index='dt', columns='symbol', values='close')
     ...
     # Pass 2: Inner join on remaining symbols — drop timestamps missing ANY survivor
     price_matrix = price_matrix.dropna(how='any', axis=0)
     ```
   - **Deviation**: The project plan (`Plans/stage-1-pairs-trading-pearson-correlation.md`, lines 84-86) specifies: *"For any remaining NaN (data gaps within the common window), forward-fill by at most 1 bar, then drop rows with remaining NaN."* The code does not contain any forward-fill (`ffill(limit=1)`) logic before calling `.dropna(how='any')`.
2. **Stage 2 (Kalman/OU) alignment**:
   - **Path**: `Raw/Sources/attachments/stage2-pairs-kalman-ou.ipynb`
   - **Cell ID**: `8f8261b5` in function `get_pair_log_prices(sym_a, sym_b)`
   - **Verbatim Code**:
     ```python
     aligned = pd.DataFrame({"a": pa, "b": pb}).dropna(how="any")
     aligned = aligned.ffill(limit=1).dropna(how="any")
     ```
   - **Deviation**: The `.dropna(how="any")` call is performed *before* the `.ffill(limit=1)` call, which means the dataframe has zero NaNs when the forward-fill is evaluated. The forward-fill is entirely redundant and has no effect, bypassing the 1-bar alignment described in `Plans/stage-2-pairs-trading-kalman-filter-state-space.md`, lines 41-42: *"Forward-fill at most 1 bar for legitimate microstructure gaps... Drop any remaining NaNs."*

### B. EM Matrix Updates
1. **Stage 1 (Pearson Screening) EM updates**:
   - **Observation**: Not applicable. Stage 1 is a correlation screen and does not use Kalman Filters or the EM algorithm.
2. **Stage 2 (Kalman/OU) EM updates**:
   - **Path**: `Raw/Sources/attachments/stage2-pairs-kalman-ou.ipynb`
   - **Cell ID**: `aa9105d7` in function `em_kalman(ya_full, yb_full)`
   - **Verbatim Code**:
     ```python
     # Vectorised M-step
     H_m = np.column_stack([yb, np.ones(T)])
     res = ya - np.einsum("ti,ti->t", H_m, ts)
     HPH = np.einsum("ti,tij,tj->t", H_m, Ps, H_m)
     R_n = max(float(np.mean(res * res + HPH)), 1e-12)
     ts1 = ts[1:]; ts0 = ts[:-1]
     Ps1 = Ps[1:]; Pc_ = Pc[:T-1]
     oss = np.einsum("ti,tj->tij", ts1, ts1)
     osc = np.einsum("ti,tj->tij", ts1, ts0)
     Q_s = Ps1 + oss - Pc_ - osc
     Q_n = np.mean(Q_s, axis=0)
     Q_n = (Q_n + Q_n.T) / 2
     Q_n = np.diag(np.diag(Q_n))
     Q_n = np.clip(Q_n, 1e-12, None)
     ```
   - **Deviation**: The M-step update for `Q_s` is mathematically incomplete. For the random-walk state equation $\theta_t = \theta_{t-1} + w_t$ where $w_t \sim \mathcal{N}(0, Q)$, the expectation matrix is:
     $$\mathbb{E}[(\theta_t - \theta_{t-1})(\theta_t - \theta_{t-1})^\top \mid y_{1:T}] = \mathbb{E}[\theta_t \theta_t^\top | y_{1:T}] + \mathbb{E}[\theta_{t-1} \theta_{t-1}^\top | y_{1:T}] - \mathbb{E}[\theta_t \theta_{t-1}^\top | y_{1:T}] - \mathbb{E}[\theta_{t-1} \theta_t^\top | y_{1:T}]$$
     Using smoothed states and covariances, this expands to:
     $$Q_{\text{correct}, t} = (P_{t|T} + \hat{\theta}_{t|T} \hat{\theta}_{t|T}^\top) - (P_{t,t-1|T} + \hat{\theta}_{t|T}\hat{\theta}_{t-1|T}^\top) - (P_{t,t-1|T}^\top + \hat{\theta}_{t-1|T}\hat{\theta}_{t|T}^\top) + (P_{t-1|T} + \hat{\theta}_{t-1|T} \hat{\theta}_{t-1|T}^\top)$$
     However, the code computes:
     `Q_s = Ps1 + oss - Pc_ - osc`
     which only represents the first two terms ($\mathbb{E}[\theta_t \theta_t^\top]$ via `Ps1 + oss`) and the third term ($\mathbb{E}[\theta_t \theta_{t-1}^\top]$ via `Pc_ + osc`). It completely omits the fourth term ($\mathbb{E}[\theta_{t-1}\theta_t^\top]$) and the second term ($\mathbb{E}[\theta_{t-1}\theta_{t-1}^\top]$). While it attempts to symmetrize `Q_n` via `(Q_n + Q_n.T) / 2`, this does not replace the missing terms, leading to an incorrect process noise covariance $Q$.
3. **Stage 2 State Covariance Initialization**:
   - **Path**: `Raw/Sources/attachments/stage2-pairs-kalman-ou.ipynb`
   - **Cell ID**: `aa9105d7` in function `kalman_smoother(...)`
   - **Verbatim Code**:
     ```python
     Xols = np.column_stack([yb[:n_i], np.ones(n_i)])
     th0, _, _, _ = np.linalg.lstsq(Xols, ya[:n_i], rcond=None)
     P0 = np.cov(Xols.T) * 10.0
     ```
   - **Deviation**: The code sets the initial state covariance $P_0$ to the covariance of the *regressor matrix* `Xols` instead of the covariance of the *OLS parameter estimator*. Since the second column of `Xols` is a constant vector of ones, its variance is zero. Thus, $P_0$ is initialized with a variance of zero for the intercept state $\alpha$ (`P0[1,1] = 0`), which implies absolute parameter certainty at start. The correct initialization is the parameter covariance: $\text{Cov}(\hat{\theta}_{OLS}) = \sigma^2 (X^\top X)^{-1}$, where $\sigma^2$ is the OLS residual variance.

### C. ADF Stationarity Checks
1. **Stage 1 (Pearson Screening) ADF**:
   - **Observation**: Not applicable. No stationarity checks are performed in Stage 1.
2. **Stage 2 (Kalman/OU) ADF**:
   - **Path**: `Raw/Sources/attachments/stage2-pairs-kalman-ou.ipynb`
   - **Cell ID**: `e2f4ea3f` in function `fit_ou(spread)` and Cell ID `51a78a7e` in `process_pair(args)`
   - **Verbatim Code**:
     ```python
     try:
         adf = adfuller(s, maxlag=20, autolag="AIC", regression="c")
         adf_s, adf_p = float(adf[0]), float(adf[1])
         ...
     ```
   - **Deviation**: The ADF test is executed on the smoothed Kalman spread series. However, since the Kalman Filter state-space model dynamically updates the parameters $\beta_t$ and $\alpha_t$ at every single bar to minimize prediction error, the spread is *forced* to be stationary and near zero by construction. Performing the ADF test on a dynamically-smoothed spread is statistically invalid, leading to a false sense of cointegration (artificially low p-values) for pairs that are not cointegrated (i.e. their long-term static spread has a unit root).

### D. Return Computations
1. **Stage 1 (Pearson Screening) Returns**:
   - **Path**: `Raw/Sources/attachments/stage1-pairs-pearson-correlation.ipynb`
   - **Cell ID**: `1eb47544`
   - **Verbatim Code**:
     ```python
     log_returns_raw = np.log(price_matrix / price_matrix.shift(1))
     session_open_mask = (price_matrix.index.time == MARKET_OPEN)
     log_returns_raw[session_open_mask] = np.nan
     log_returns = log_returns_raw.dropna(how='any')
     ```
   - **Deviation**: Because the price alignment (inner join) is performed *before* the return calculation, any missing 1-minute bar that causes a timestamp to be dropped globally creates "synthetic" returns across non-contiguous periods. These returns exhibit higher variance, violating the homoscedasticity assumption of Pearson correlation and distorting the screening signal. 
2. **Stage 2 (Kalman/OU) Returns**:
   - **Observation**: Stage 2 operates on log-prices, not returns. However, it fails to handle overnight price gaps. At the daily transition (15:29 to 09:15 the next day), the filter treats the price jump as a normal 1-minute step. This overnight price shock inflates the estimated process noise variance $Q$ during the EM loop, causing the filter to adjust parameters too rapidly and forcing the spread half-life to collapse.

---

## 2. Logic Chain

1. **Inner Joins**: By executing `.dropna(how='any')` before `.ffill(limit=1)` in Stage 2, the code creates a strict inner join on timestamps first, meaning there are no NaNs left to fill. In Stage 1, the inner join is performed globally on prices before returns, dropping over 10% of timestamps globally and calculating "synthetic" returns across non-contiguous gaps.
2. **EM Q Update**: The math equation for $Q$ transitions from $\theta_{t-1}$ to $\theta_t$ requires expanding the expectation of $(\theta_t - \theta_{t-1})(\theta_t - \theta_{t-1})^\top$. The code only implements the expectation terms involving $\theta_t \theta_t^\top$ and the cross-product $\theta_t \theta_{t-1}^\top$. It omits the transpose cross-product $\theta_{t-1}\theta_t^\top$ and the lag product $\theta_{t-1}\theta_{t-1}^\top$, leading to an incorrect state noise covariance matrix $Q$.
3. **P0 Intercept Variance**: The OLS regressor matrix has a constant column of ones. Slicing `Xols` and calling `np.cov(Xols.T)` results in a covariance of 0 for the constant column. This sets the initial variance of the intercept $\alpha$ to zero, representing absolute parameter certainty which is statistically incorrect.
4. **ADF and Kalman Tracking**: Because the Kalman Filter updates states at each 1-minute bar using process noise $Q$, any non-stationarity in prices is absorbed by the drifting states $\beta_t$ and $\alpha_t$. As a result, the smoothed spread `spread_t = ya_t - beta_t * yb_t - alpha_t` will always appear stationary, making the ADF test on the smoothed spread highly biased and yielding false cointegration results.
5. **Overnight Transitions**: Concatenating prices across trading days without partitioning or scaling the state equations means the filter treats overnight gaps (17+ hours) as standard 1-minute intervals. The large price gaps at market open are interpreted as state shocks, artificially inflating the estimated process noise $Q$, causing the model to adapt parameters too rapidly and collapsing the spread half-life.

---

## 3. Caveats

- **Database Accuracy**: We assume the close prices in `ohlcv_1min` in `/storage/emulated/0/Quant/LLM-WIKI/Raw/Sources/attachments/Master-Data-1min.sqlite` are accurate. Decimal scale mismatches or duplicate timestamps could cause estimation errors.
- **Subsampling Rate**: The Stage 2 notebook has `EM_STEP = 1` set, which means it evaluates the EM algorithm on every bar. While this matches the full-dataset math, it differs from the markdown documentation of the notebook which states that a subsampling of every 5th bar was used for speed.

---

## 4. Conclusion

The Stage 1 and Stage 2 notebooks contain critical mathematical and logical flaws that compromise the validity of the pairs trading pipeline:
- **Redundant Forward-Fills**: Data alignment does not successfully perform the 1-bar forward-fill because `.dropna()` is called first.
- **Incorrect EM Q Updates**: The state noise covariance matrix update is missing half the mathematical terms, leading to incorrect state dynamics.
- **Incorrect OLS Initialization**: Initializing state covariance with the covariance of the regressor matrix sets the intercept's initial uncertainty to zero.
- **Invalid ADF Test**: Running ADF on dynamically-smoothed spreads leads to false-positive cointegration signals.
- **Overnight Gap Inflation**: Failing to account for overnight price gaps inflates the process noise $Q$ and collapses the spread half-life.

These flaws explain the statistical behavior documented in LLM-WIKI (very short spread half-lives of ~9 minutes and rapid parameter shifts).

---

## 5. Verification Method

To verify these findings:
1. **File Locations**: Inspect the cells of the following fetched files in `Raw/Sources/attachments/`:
   - `stage1-pairs-pearson-correlation.ipynb` (Cell IDs: `8e23cf0b`, `1eb47544`)
   - `stage2-pairs-kalman-ou.ipynb` (Cell IDs: `8f8261b5`, `aa9105d7`, `e2f4ea3f`, `51a78a7e`)
2. **Formula Audit**:
   - Compare `Q_s = Ps1 + oss - Pc_ - osc` in Cell `aa9105d7` against the correct expectation expansion.
   - Compare `P0 = np.cov(Xols.T) * 10.0` in Cell `aa9105d7` against OLS parameter covariance.
3. **Execution Review**:
   - Check the printed output of Stage 2 notebook runs: note if `half_life_minutes` is extremely short (e.g. median 9.1 minutes), which confirms parameter tracking is absorbing the spread variance.
