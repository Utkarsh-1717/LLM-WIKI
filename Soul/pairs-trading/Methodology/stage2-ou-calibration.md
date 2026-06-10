# Stage 2 — OU Chunked Q Calibration
**Status**: ✅ COMPLETE (Sketch 3 — EM permanently abandoned)  
**Source**: `Archive/Pairs_Trading_Sketches/final sketch-1&2/sketch - 3/`

---

## 1. Objective

For each of the Top 5 pairs, compute the Kalman Filter's Process Noise matrix **Q** such that the filter acts as a stable **macro-anchor** — tracking the slow, structural drift in the hedge ratio while being slow enough to leave the short-term, tradeable spread intact for signal generation.

---

## 2. Why EM Was Permanently Abandoned

The standard approach for fitting a Kalman state-space model is the **Expectation-Maximization (EM)** algorithm, which iteratively finds Q and R that maximise the likelihood of the observed price series.

### 2.1 The Mathematical Problem (E-Step)
The E-step requires an **RTS (Rauch-Tung-Striebel) backward smoother** — a full backward pass over the entire time series:

$$G_t = P_{t|t} \cdot P_{t+1|t}^{-1}$$
$$\hat{\theta}_{t|T} = \hat{\theta}_{t|t} + G_t(\hat{\theta}_{t+1|T} - \hat{\theta}_{t+1|t})$$
$$P_{t|T} = P_{t|t} + G_t(P_{t+1|T} - P_{t+1|t})G_t^\top$$

On 150,000 sequential bars, this loop takes **~17 minutes per pair** in Python — fundamentally unviable for any repeated calibration.

### 2.2 The Mathematical Problem (M-Step)
The M-step Q update requires the complete covariance expectation:

$$Q_{new} = \frac{1}{T-1}\sum_{t=1}^{T}\left[P_{t|T} + \hat{\theta}_{t|T}\hat{\theta}_{t|T}^\top - P_{t,t-1|T} - \hat{\theta}_{t|T}\hat{\theta}_{t-1|T}^\top + \text{transpose terms}\right]$$

Sketch 2 omitted the cross-covariance terms ($P_{t,t-1|T}$), systematically underestimating Q and causing premature convergence to an over-confident (too small) Q.

Even with the complete M-step algebra implemented correctly, EM converged **~0%** of the time on high-frequency cointegrated 1-minute data. The parameter space is fundamentally non-identifiable at this data frequency.

### 2.3 Conclusion
EM is unsuitable for HF cointegrated data. We permanently replace it with the **Deterministic OU Chunked Fit** — a closed-form, sub-second calibration that is mathematically grounded and empirically validated.

---

## 3. The OU Chunked Fit — Shared Foundation

### 3.1 Core Idea
Instead of searching blindly for Q, we **measure** the pair's actual mean-reversion speed directly from the data by fitting an Ornstein-Uhlenbeck (OU) process to the spread in multiple temporal windows (chunks). We then set Q such that the Kalman filter's effective adaptation speed is **deliberately slower** than the pair's mean-reversion speed — guaranteeing the filter tracks the macro drift without consuming the intraday spread.

### 3.2 Step-by-Step Procedure

```
CONFIG: NUM_CHUNKS = 4  (configurable: 4, 6, 8, 10 — see Section 6)

For each chunk i in [0 .. NUM_CHUNKS-1]:
```

**Step 1 — Chunk Slice**:
```python
chunk_size = len(ya) // num_chunks
start = i * chunk_size
end = (i+1)*chunk_size if i < num_chunks-1 else len(ya)
ya_c, yb_c = ya[start:end], yb[start:end]
```

**Step 2 — OLS to Extract Local Spread**:

Within each chunk, fit a static OLS hedge ratio:
$$y_c = \beta_c x_c + \alpha_c + \epsilon_c$$

The local spread is:
$$S_{c,t} = y_{c,t} - (\hat{\beta}_c x_{c,t} + \hat{\alpha}_c)$$

```python
X_mat = np.column_stack([yb_c, np.ones(len(yb_c))])
beta, _, _, _ = np.linalg.lstsq(X_mat, ya_c, rcond=None)
spread = ya_c - X_mat @ beta
```

**Step 3 — AR(1) Fit to Extract Half-Life**:

Fit an autoregressive AR(1) model to the spread:
$$S_t = \phi S_{t-1} + c + \eta_t$$

The AR(1) coefficient $\phi$ gives the **mean-reversion speed** of the spread. The half-life in minutes is:
$$HL = -\frac{\ln(2)}{\ln(\phi)}$$

This is valid only when $0 < \phi < 1$ (mean-reverting). If $\phi \geq 1$ (non-stationary) or $\phi \leq 0$ (oscillatory), the chunk is discarded.

```python
X_ar = np.column_stack([spread[:-1], np.ones(len(spread)-1)])
phi, _, _, _ = np.linalg.lstsq(X_ar, spread[1:], rcond=None)
phi = phi[0]
if 0 < phi < 1:
    hl = -np.log(2) / np.log(phi)   # half-life in minutes
    valid_hls.append(hl)
```

**Step 4 — Collect Valid Half-Lives**:
```python
valid_HLs = [HL_i for all valid chunks]
```

---

## 4. Two Q Calibration Methods

Both methods use the **same Q construction formula** — only the `target_tau` input differs.

### 4.1 Method A — OU Worst-Case Anchored Q

```python
target_tau_A = max(valid_HLs) * 2.0
```

**Philosophy**: Size the filter for the **slowest observed regime**. If in any temporal chunk the pair took 65 minutes to revert, the Kalman filter must be slow enough to survive that regime without collapsing the spread to noise. Conservative and noise-resistant — generates fewer, higher-quality signals.

**This was the proven production winner from Sketch 3 backtesting.**

### 4.2 Method B — OU Dominant Regime Q

```python
hl_medoid = find_medoid(valid_HLs)
target_tau_B = hl_medoid * 2.0
```

**Philosophy**: Size the filter for the regime the pair **most commonly inhabits**. The medoid is the actual observed chunk half-life with the minimum total distance to all other chunk half-lives — it identifies the real, repeating regime, not an outlier extreme.

**Why medoid, not median, not mean**:
- **Mean** (e.g., 41.1 min): Distorted by a single outlier slow chunk (e.g., 65 min pulls the mean). Not a real observed regime.
- **Median** (e.g., 33.4 min): Interpolated midpoint — not an actual chunk value, could lie between two clusters.
- **Medoid** (e.g., 33.0 min): The real, observed chunk value that most others cluster around. Answers: *"which half-life appeared most commonly?"*

Example with `valid_HLs = [32.1, 33.8, 65.4, 33.0]`:
- Mean = 41.1 (not real)
- Median = 33.4 (not a real observation)  
- Medoid = 33.0 (real chunk value, minimum sum of distances to others)

```python
def find_medoid(half_lives):
    """
    Returns the actual observed chunk half-life that is closest to all others.
    = the half-life regime the pair most commonly exhibits.
    """
    hls = np.array(half_lives)
    if len(hls) == 1:
        return hls[0]
    distances = np.array([np.sum(np.abs(hl - hls)) for hl in hls])
    return hls[np.argmin(distances)]
```

---

## 5. Q Construction Formula (Shared)

Given `target_tau` (from either Method A or B), Q is computed analytically from warmup OLS statistics:

**Step 1 — Warmup OLS** (first 1875 bars = 5 trading days):
```python
warmup_n = min(1875, len(ya) // 10)
X_w = np.column_stack([yb[:warmup_n], np.ones(warmup_n)])
beta0 = np.linalg.lstsq(X_w, ya[:warmup_n], rcond=None)[0]
residuals = ya[:warmup_n] - X_w @ beta0
R_est = np.sum(residuals**2) / (warmup_n - 2)    # measurement noise variance
```

**Step 2 — Lambda from Target Tau**:

The Kalman Gain $K$ at steady state decays as $K \approx 1 - 0.5^{1/\tau}$ per bar for a target half-life of $\tau$ bars. The corresponding process-to-measurement noise ratio is:

$$K = 1 - 0.5^{1/\tau} \qquad \lambda = \frac{K^2}{1-K}$$

```python
K_factor = 1.0 - np.power(0.5, 1.0 / target_tau)
lam = (K_factor**2) / (1.0 - K_factor)
```

**Step 3 — Q Matrix**:
$$Q = \lambda \cdot \hat{\sigma}^2_{OLS} \cdot \Sigma_X^{-1}$$

$$P_0 = \hat{\sigma}^2_{OLS} \cdot (X_w^\top X_w)^{-1}$$

```python
Sigma_X_inv = np.linalg.inv(X_w.T @ X_w / warmup_n)
Q  = lam * R_est * Sigma_X_inv        # 2×2 process noise matrix
P0 = R_est * np.linalg.inv(X_w.T @ X_w)  # 2×2 initial covariance
```

> **Critical**: $P_0$ must use $\hat{\sigma}^2_{OLS} \cdot (X^\top X)^{-1}$ — the OLS parameter covariance. Using the sample covariance of the regressor matrix $X$ sets the intercept's initial variance to 0 (since the intercept column is a constant 1 — zero sample variance), permanently locking the intercept. This was a major bug in Sketch 1.

---

## 6. 09:15 Gap Protocol

At the first bar of every trading session (`time == 09:15`), the overnight gap is absorbed by doubling the **prediction uncertainty** $P$:

$$P_{pred} = P_{pred} \times 2$$

This tells the filter: *"more time has passed than usual; be slightly more adaptable this morning"* — without corrupting the process noise Q that defines the macro-drift anchor.

**We do NOT scale Q overnight**: The macro-relationship (hedge ratio β) does not radically change overnight. Scaling Q would permanently alter the filter's responsiveness for the rest of the day.

```python
time_int = timestamps.hour * 100 + timestamps.minute
is_open_bar = (time_int == 915)
# ...inside Kalman loop:
if is_open_bar[t]:
    P_pred *= 2.0
```

---

## 7. Chunk Sweep — Stability Analysis

To avoid choosing `NUM_CHUNKS` blindly, the Stage 2 notebook sweeps across multiple chunk counts (4, 6, 8, 10) and reports the resulting half-life statistics for each pair at each chunk count. This reveals:

- **Regime-stable pairs** (HL estimates consistent across chunk counts): trustworthy, robust Q calibration
- **Regime-volatile pairs** (HL estimates vary wildly by chunk count): fragile pairs where the regime shifts significantly — trade with caution

```python
CHUNK_SWEEP = [4, 6, 8, 10]
```

---

## 8. Stage 2 Output Schema

| Column | Description |
|---|---|
| `pair` | e.g. `GRSE-MAZDOCK` |
| `num_chunks` | configurable value used |
| `chunk_half_lives` | JSON list of per-chunk HL values [minutes] |
| `n_valid_chunks` | how many chunks yielded 0 < φ < 1 |
| `hl_min` | minimum valid chunk HL |
| `hl_max` | maximum valid chunk HL → Method A |
| `hl_median` | median of valid chunk HLs (reference only) |
| `hl_medoid` | medoid of valid chunk HLs → Method B |
| `hl_mean` | mean (reference, not used for Q) |
| `hl_std` | std dev — regime consistency indicator |
| `target_tau_worst_case` | `hl_max * 2.0` |
| `target_tau_dominant` | `hl_medoid * 2.0` |
| `Q_beta_worst_case` | Q[0,0] for Method A |
| `Q_alpha_worst_case` | Q[1,1] for Method A |
| `Q_beta_dominant` | Q[0,0] for Method B |
| `Q_alpha_dominant` | Q[1,1] for Method B |
| `R_est` | shared OLS residual variance |

---

## Connections

- [[pairs-trading-strategy]]
- [[stage1-pearson-screening]]
- [[stage3-execution-engine]]
- [[QC-decisions-pairs-trading]]
- [[master-data-1min-dataset]]
- [[kaggle-notebook-run]]

- [[production-logic]]
- [[backtest-record-pairs-trading]]