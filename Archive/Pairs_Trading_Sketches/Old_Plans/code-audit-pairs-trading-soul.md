> [!WARNING]
> **ARCHIVED & OBSOLETE**
> This file is part of the trial-and-error "Sketch" phase. 
> The mathematics and code herein may contain deprecated Expectation-Maximization loops or failed concepts.
> The final, verified truth is located in the `Soul/` directory.
> Tags: #archived-sketch #pairs-trading-prototype

# Plan: Rigorous Static Code and Quantitative Audit of Master Pairs Trading Soul

## Objective
Perform a rigorous static code and quantitative audit on `Master_Pairs_Trading_Soul.ipynb` located at `/storage/emulated/0/Quant/LLM-WIKI/Soul/Master_Pairs_Trading_Soul.ipynb` for compliance with the required mathematical formulas, data alignment, EM convergence, and statistics exporting.

## Open Questions (for user review)
- None. This is a read-only investigation and audit.

## Proposed Approach

### Step 1 — Verify Data Ingestion & Alignment
- Check `Stage 1` code to verify the 2-pass smart alignment: (a) pivot open/close prices, (b) drop symbols with < 80% coverage, (c) forward-fill remaining gaps by at most 1 bar first, (d) then execute the inner join (`dropna(how='any')`). Check for other dropna/ffill issues.

### Step 2 — Verify Kalman Filter & EM Update
- Verify state covariance $P_0$ initialization in `kalman_smoother_scaled`. It must use the OLS estimator parameter covariance scaled for uncertainty (e.g. `sigma2 * XtX_inv * 10.0`), NOT a hardcoded identity or regressor covariance matrix.
- Verify the EM M-step process noise covariance matrix $Q$ vectorized update: check if all expected terms are present, if it follows the correct EM formulation, and if they are scaled properly across overnight gaps.

### Step 3 — Verify OU Fitting Block
- Verify if the AR(1) phi mapping in the OU fitting block rejects values <= 0.0 or >= 1.0, and bounds them properly for numerical stability.

### Step 4 — Verify Stage 3A Optimization
- Verify if Stage 3A is processing all 500 pairs (dropping the `tradeable == True` filter).

### Step 5 — Verify Detailed Statistics Exporting
- Verify if the `run_backtest_numba` engine correctly calculates the detailed statistics (`avg_points_profit`, `avg_points_loss`, `exit_mr_count`, `exit_sl_count`, `exit_hl_count`, and `exit_session_count`), and crucially, verify if they are appended to `optimized_rows` and exported to `pairs_stage3a_optimized.csv`.

### Step 6 — Write Analysis and Handoff Reports
- Write a comprehensive finding report to `analysis.md` in working directory.
- Send a handoff report to `handoff.md` and message the main agent.

## Time Estimate
~15-20 minutes of static analysis.

## Connections to Existing Skills
- [[plan-first]]
