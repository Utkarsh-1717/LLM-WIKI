# Project: Master Pairs Trading Soul

## Architecture
This project implements the consolidated, production-grade Pairs Trading pipeline in a single, memory-efficient Kaggle notebook: `Master_Pairs_Trading_Soul.ipynb`. The pipeline consists of the following sequential stages:
1. **Stage 1 (Pearson Correlation screening)**:
   - Ingests 1-minute Close prices from `Master-Data-1min.sqlite`.
   - Filters symbols to those with >= 80% coverage to protect alignment from sparse data.
   - Forward-fills at most 1 bar of microstructure gaps, then drops remaining NaNs (inner join).
   - Computes log-returns: $r_t = \ln(P_t / P_{t-1})$ individually.
   - Masks overnight/weekend return gaps (the 09:15 bar return is set to NaN).
   - Calculates Pearson correlation matrix on aligned return series.
   - Ranks all valid pairs (>= 5,000 observations) and outputs `pairs_all.csv` and `pairs_top500.csv`.
2. **Stage 2 (Kalman Filter State-Space & OU Fitting)**:
   - Ingests the top 500 pairs from Stage 1.
   - For each pair, runs the Expectation-Maximization (EM) algorithm to estimate process noise covariance matrix $Q$ and measurement noise variance $R$.
   - Includes mathematical fixes: Complete M-step $Q$ covariance expectation updates, $P_0$ OLS parameter covariance initialization, and overnight process noise covariance scaling (injecting time-elapsed multiplier).
   - Extracts the smoothed spread and fits an Ornstein-Uhlenbeck (OU) process.
   - Evaluates stationarity using Augmented Dickey-Fuller (ADF) test (run on the unsmoothed, standard innovations or with appropriate parameters, and standardizing via native Kalman variance) and filters tradeable pairs.
3. **Stage 3A (In-Sample Grid Search Optimization)**:
   - Sweeps $Z$-entry triggers ($2.0, 2.5, ..., 15.0$) and Stop Loss triggers ($Z_{sl} = 2.5, 3.0, ..., 16.0$ or no stop loss).
   - Implements post-Stop-Loss freeze logic: wait until $|Z| < \text{entry\_trigger} / 2$ before allowing re-entry.
   - Optimizes gross points profit/loss (no fees/slippage) on the in-sample period.
   - Outputs the single best configuration per pair.
4. **Stage 3B (Out-of-Sample Backtester)**:
   - Executes out-of-sample backtest using the optimized parameters from Stage 3A.
   - Applies strict single-sided lagger trading (trades only the laggard, takes no position in the leader).
   - Standardizes innovations using native Kalman variance: $z_t = e_t / \sqrt{S_t}$.
   - Delays execution by 1 bar to prevent lookahead bias (enters on next bar open).
   - Positions sized to ₹50,000 (₹10,000 base capital with 5x leverage).
   - Deducts Zerodha MIS fees (brokerage, GST, STT, transaction charges, SEBI charges, stamp duty) and slippage.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Research & Specifications | Gather existing math/code and draft specifications | None | PLANNED |
| 2 | Plan Creation | Create `/storage/emulated/0/Quant/LLM-WIKI/Plans/Master_Pairs_Trading_Soul.md` | M1 | PLANNED |
| 3 | Core Implementation | Build and run `Master_Pairs_Trading_Soul.ipynb` on Kaggle | M2 | PLANNED |
| 4 | Verification & Audit | Perform code reviews, challenger tests, and forensic audit | M3 | PLANNED |
| 5 | Delivery & Handoff | Move verified notebook to `Soul/` and write conclusions | M4 | PLANNED |

## Interface Contracts
- **Stage 1 Output**: CSV file with columns: `symbol_a`, `symbol_b`, `pearson_rho`, `t_stat`, `p_value`, `n_obs`, `rank`.
- **Stage 2 Output**: CSV file with columns: `symbol_a`, `symbol_b`, `pearson_rho`, `stage1_rank`, `n_obs`, `em_iterations`, `log_likelihood_final`, `Q_beta`, `Q_alpha`, `R`, `kappa`, `mu`, `sigma_ou`, `half_life_minutes`, `adf_pvalue`, `hurst_exponent`, `em_converged`.
- **Stage 3A Output**: CSV file with columns: `symbol_a`, `symbol_b`, `best_z_entry`, `best_z_sl`, `gross_profit`, `trade_count`, `win_rate`.
- **Stage 3B Output**: CSV file with columns: `symbol_a`, `symbol_b`, `net_profit`, `win_rate`, `trade_count`, `max_drawdown`, `exit_reasons`.

## Code Layout
- Notebook source: `/storage/emulated/0/Quant/LLM-WIKI/Soul/Master_Pairs_Trading_Soul.ipynb`
- Metadata: `/storage/emulated/0/Quant/LLM-WIKI/Soul/kernel-metadata.json`
- Output directory inside Kaggle: `/kaggle/working/dataset_export/`
- Output dataset slug: `utkarshpatelthefirst/master-pairs-trading-soul-results`
