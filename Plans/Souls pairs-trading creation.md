# Soul / Pairs-Trading: Finalization Plan (v2)

> **Status**: AWAITING APPROVAL  
> **Updated**: 2026-06-09  
> **Goal**: Finalize Soul/pairs-trading/ with complete methodology docs, all 3 stage builders, and two properly-named OU-based Q calibration strategies.

---

## Background & Sketch Evolution

| Sketch | Core Approach | Outcome |
|---|---|---|
| Sketch 1 | EM Kalman + global dropna + static 09:15 mask | Inflated half-lives, data loss, poor EM convergence |
| Sketch 2 | Complete EM M-step (RTS smoother) + OLS P0 | 2.7 min half-life, 0% EM convergence, economically unviable |
| Sketch 3 | Abandoned EM → Deterministic OU Chunked Fit | OU Worst-Case beat Fixed Speed-Limit by ₹30,740 |

**Top 5 production pairs**: PFC/RECLTD, BDL/MAZDOCK, GRSE/MAZDOCK, BANKBARODA/CANBK, BPCL/HINDPETRO

---

## CRITICAL: Renaming — No More "Approach 1/2"

| Old Label | Proper Name | Description |
|---|---|---|
| "Approach 1" | **Fixed Speed-Limit Q** | Q set by manually chosen tau (120 min). No OU calibration. Archived/reference only. |
| "Approach 2" | **OU Worst-Case Anchored Q** | Q from max(chunk HLs) * 2.0. Original production winner. |
| *(New)* | **OU Dominant Regime Q** | Q from medoid(chunk HLs) * 2.0. The chunk HL that most other chunks cluster around — the most repeating regime. |

---

## New Requirements (v2)

### 1. Two OU Q Calibration Methods

Both use the same chunked OU fit foundation. Only the aggregation statistic differs:

**Method A — OU Worst-Case Anchored Q**
- `target_tau = max(valid_chunk_half_lives) * 2.0`
- Builds for the slowest observed regime. Conservative. Fewer trades. Noise-resistant.
- Proven production winner from Sketch 3.

**Method B — OU Dominant Regime Q**
- `target_tau = medoid(valid_chunk_half_lives) * 2.0`
- **"Medoid"** = the actual observed chunk half-life that has the minimum total distance to all other chunk half-lives. It is the real, literal chunk value that the majority of other chunks cluster around.
- Not yet backtested — new addition.

> **Why medoid, not median and not mean?**
> Example: chunk HLs = [32.1, 33.8, 65.4, 33.0]
> - Mean = 41.1 min → distorted by the 65 outlier. Not real.
> - Median = 33.4 min → interpolated midpoint. Not an actual observed value.
> - Medoid = 33.0 min → the actual chunk value that is closest to ALL others (sum of distances: |33-32.1|+|33-33.8|+|33-65.4|+|33-33| = 0.9+0.8+32.4+0 = 34.1, which is minimum). This IS an observed regime.
>
> The medoid directly answers: **"which chunk half-life is most common / most surrounded by others?"** It picks the real, repeating value, not an interpolated estimate.
>
> Implementation:
> ```python
> def find_medoid(half_lives):
>     hls = np.array(half_lives)
>     distances = np.array([np.sum(np.abs(hl - hls)) for hl in hls])
>     return hls[np.argmin(distances)]
> ```

### 2. Configurable NUM_CHUNKS

```python
NUM_CHUNKS = 4   # Top of notebook config. Change to 6, 8, 10 for finer resolution.
```
- Never hardcoded internally.
- More chunks = finer regime resolution but shorter, noisier AR(1) per chunk.
- Fewer chunks = more data per chunk = more stable but misses regime shifts.

### 3. Full Half-Life Distribution Output Per Pair

Stage 2 CSV output columns:

| Column | Description |
|---|---|
| `pair` | e.g. GRSE-MAZDOCK |
| `num_chunks` | configurable value used |
| `chunk_half_lives` | JSON list of per-chunk HL values in minutes |
| `n_valid_chunks` | chunks where 0 < phi < 1 |
| `hl_min` | minimum chunk HL |
| `hl_max` | maximum chunk HL → Method A tau/2 |
| `hl_median` | median chunk HL (reference only) |
| `hl_mean` | mean (reference only, not used for Q) |
| `hl_medoid` | medoid chunk HL → Method B tau/2 (most common, clustered) |
| `hl_std` | spread/consistency of half-life across regimes |
| `target_tau_worst_case` | hl_max * 2.0 |
| `target_tau_dominant` | hl_medoid * 2.0 |
| `Q_beta_worst_case` | Q[0,0] for Method A |
| `Q_alpha_worst_case` | Q[1,1] for Method A |
| `Q_beta_dominant` | Q[0,0] for Method B |
| `Q_alpha_dominant` | Q[1,1] for Method B |
| `R_est` | shared OLS residual variance |

---

## Current Soul/ State (Gaps)

```
Soul/pairs-trading/
├── Code/
│   └── build_production_engine.py  ← BUG: wrong output path, hardcoded tau, no Method B, old naming
├── Methodology/
│   └── production_logic.md          ← INCOMPLETE: Stage 3 empty, "Approach 2" language
└── Conclusions/
    └── backtest_record.md            ← INCOMPLETE: old naming, no Next Steps
```

**Missing**: stage1_pearson_screening.md, stage2_ou_calibration.md, stage3_execution_engine.md, QC_decisions.md, stage1_pearson_nb.py, stage2_ou_nb.py

---

## Target Architecture

```
Soul/pairs-trading/
├── Methodology/
│   ├── production_logic.md              ← UPDATE
│   ├── stage1_pearson_screening.md      ← NEW
│   ├── stage2_ou_calibration.md         ← NEW (both OU methods + configurable chunks)
│   ├── stage3_execution_engine.md       ← NEW
│   └── QC_decisions.md                  ← NEW (all 10 intentional choices)
├── Code/
│   ├── stage1_pearson_nb.py             ← NEW
│   ├── stage2_ou_nb.py                  ← NEW (both methods, NUM_CHUNKS config)
│   └── build_production_engine.py       ← UPDATE (fix path, both methods, fix naming)
└── Conclusions/
    └── backtest_record.md               ← UPDATE (fix naming, add Next Steps)
```

---

## Full Verified Methodology

### Stage 1 — Pearson Correlation Screening
- Log-returns: r_t = ln(P_t / P_{t-1})
- NSE hours: 09:15–15:29 IST (vectorized int check)
- Overnight gap: date-boundary mask (NOT static 09:15 mask)
- Pairwise alignment: df.corr() — NOT global dropna on 500 symbols
- Min 5,000 bars; p < 0.05 t-test; no ffill

### Stage 2 — OU Chunked Q Calibration

**Why EM was abandoned**: ~17 min RTS smoother per 5 pairs; Q collapses or explodes on HF cointegrated data; ~0% convergence.

**Shared chunked OU procedure**:
```
For each chunk [0..NUM_CHUNKS-1]:
  1. OLS: [beta, alpha] = lstsq([yb_chunk, 1], ya_chunk)
     spread = ya_chunk - beta*yb_chunk - alpha
  2. AR(1): phi = lstsq([spread[:-1], 1], spread[1:])[0]
  3. If 0 < phi < 1: HL = -ln(2)/ln(phi)  [minutes]

valid_HLs = [HL for all valid chunks]
```

**Method A (OU Worst-Case Anchored Q)**:
```
target_tau_A = max(valid_HLs) * 2.0
```

**Method B (OU Dominant Regime Q)**:
```
# medoid = actual chunk HL with minimum total distance to all other chunk HLs
# = the chunk half-life that most other chunks cluster around (the repeating regime)
hl_medoid = valid_HLs[argmin( sum(|hl_i - hl_j| for j) for each i )]
target_tau_B = hl_medoid * 2.0
```

**Q construction** (shared formula, different tau):
```
K = 1 - 0.5^(1/target_tau)
lambda = K^2 / (1-K)

# 5-day warmup OLS:
R_est = sum(residuals^2) / (n_warmup - 2)
Sigma_X_inv = inv(X_warmup.T @ X_warmup / n_warmup)
Q = lambda * R_est * Sigma_X_inv    [2x2]
P0 = R_est * inv(X_warmup.T @ X_warmup)  [NOT sample cov of X]
```

**09:15 Gap Protocol** (same for both):
```
At every 09:15 bar: P_pred *= 2.0   [do NOT scale Q]
```

### Stage 3 — Single-Sided Lagger Execution Engine

**Kalman forward filter** (online, no backward pass):
```
For each bar t:
  x_pred = x_upd; P_pred = P_upd + Q
  if time[t] == 09:15: P_pred *= 2.0
  H_t = [yb[t], 1]
  v_t = ya[t] - H_t @ x_pred          ← spread
  S_t = H_t @ P_pred @ H_t.T + R
  K_t = P_pred @ H_t.T / S_t
  x_upd = x_pred + K_t * v_t
  P_upd = P_pred - K_t @ H_t @ P_pred
  spread[t] = v_t
```

**Signal**:
```
Z_t = (spread[t] - mean(spread[t-374:t])) / std(spread[t-374:t])
Entry: |Z| >= 2.0  (LONG lagger if Z<=-2, SHORT if Z>=+2)
Exit:  Z crosses 0, OR time == 15:15 (forced EOD)
```

**Execution**: 10,000 INR capital * 5x MIS = 50,000 INR position; 0.05% fee per leg

**Sketch 3 backtest results**:
| Method | Net PnL | Trades |
|---|---|---|
| Fixed Speed-Limit Q (120 min) | −₹40,826 | Higher |
| OU Worst-Case Anchored Q | −₹10,086 | 767 fewer |
| GRSE-MAZDOCK alone (OU Worst-Case) | +₹15,482 | — |
| OU Dominant Regime Q | *not yet backtested* | — |

---

## QC Decisions — Do NOT "Fix" These

| Decision | Rationale |
|---|---|
| No ffill | Stale vs live price = phantom divergences |
| Pairwise alignment (df.corr) | Global dropna destroys data for all pairs |
| Dynamic gap mask (date boundary) | Static 09:15 mask fails if bar is missing |
| OU over EM | EM unviable on HF cointegrated data |
| Single-sided lagger only | Two-sided doubles fees; alpha is in lagger catch-up |
| P_pred*=2 at 09:15, NOT Q scaling | Q is macro drift anchor; only P absorbs gap uncertainty |
| ADF at p < 0.01 | Strict 99% cointegration gate |
| Rolling Z-score, NOT Kalman S_t | Kalman S_t dominated by measurement noise R |
| 15:15 forced square-off | Broker MIS penalty + overnight gap risk |
| Median for dominant regime, NOT mean | Mean distorted by outlier slow chunks |

---

## Code Changes Summary

### `stage2_ou_nb.py` (NEW — most important)
- `NUM_CHUNKS` config at top
- `extract_ou_half_life_distribution(ya, yb, num_chunks)` → returns all_hls, stats
- `compute_q_from_tau(target_tau, ya_warmup, yb_warmup)` → returns Q, P0, R_est
- Both methods run per pair; full distribution output in CSV

### `build_production_engine.py` (UPDATE)
- Fix path bug
- Add NUM_CHUNKS config
- Add dominant regime Q calculation alongside worst-case
- Run both OU methods head-to-head in Stage 3
- Remove all "Approach 1/2" references

### `stage1_pearson_nb.py` (NEW)
- Pairwise corr, dynamic gap mask, t-stat filter
- Outputs pairs_all.csv and pairs_top500.csv

---

## Execution Plan

| # | File | Action |
|---|---|---|
| 1 | Soul/Methodology/stage1_pearson_screening.md | CREATE |
| 2 | Soul/Methodology/stage2_ou_calibration.md | CREATE |
| 3 | Soul/Methodology/stage3_execution_engine.md | CREATE |
| 4 | Soul/Methodology/QC_decisions.md | CREATE |
| 5 | Soul/Code/stage1_pearson_nb.py | CREATE |
| 6 | Soul/Code/stage2_ou_nb.py | CREATE |
| 7 | Soul/Methodology/production_logic.md | UPDATE |
| 8 | Soul/Code/build_production_engine.py | UPDATE |
| 9 | Soul/Conclusions/backtest_record.md | UPDATE |

---

## Open Questions for Your Review

> [!IMPORTANT]
> **Q1 — Dominant Regime method**: I recommend **median** for robustness with 4-8 chunks. Alternatives: medoid (actual chunk value closest to all others) or KDE mode (theoretically ideal but needs more chunks). Do you agree with median?

> [!IMPORTANT]
> **Q2 — Stage 3 head-to-head**: Should build_production_engine.py run both OU methods (Worst-Case AND Dominant Regime) head-to-head with a comparison table? I strongly recommend yes — this directly shows if Dominant Regime outperforms.

> [!IMPORTANT]
> **Q3 — Fixed Speed-Limit Q in Stage 3**: Keep it as a third "benchmark" column (shows why OU wins) or drop it from production code entirely (only in Conclusions)?

> [!NOTE]
> **Q4 — Chunk sweep**: Should the notebook also automatically sweep NUM_CHUNKS (4, 6, 8, 10) and show HL stability across chunk sizes? Shows regime-stable vs volatile pairs.

> [!NOTE]
> **Q5 — Wiki connections**: After Soul docs, create/update Wiki/ entity notes per AGENTS.md rules?

---

## Verification Plan

1. No "Approach 1" or "Approach 2" language anywhere in Soul/
2. production_logic.md has zero "Pending" placeholders
3. stage2_ou_nb.py produces target_tau_worst_case AND target_tau_dominant columns
4. build_production_engine.py runs both methods; output path is correct
5. NUM_CHUNKS is a single top-level config variable in every relevant file
6. All Methodology docs have Connections sections with valid wikilinks
7. QC_decisions.md covers all 10 intentional choices
