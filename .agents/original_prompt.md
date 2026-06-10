## 2026-06-04T15:28:00Z

Conduct a rigorous quality control (QC) audit of the LLM-WIKI project and related Kaggle implementations, focusing specifically on the **Pairs Trading** methodology, code, and mathematics. Identify any potential errors, logic flaws, or incorrect mathematical implementations.

Working directory: /storage/emulated/0/Quant/LLM-WIKI/
Integrity mode: development

## Requirements

### R1. Audit Pairs Trading Methodology & Math
Review all code, scripts, notebooks, and plans related to the Pairs Trading pipeline (e.g., Pearson correlation, Kalman Filter State Space, Ornstein-Uhlenbeck, backtesting). Scrutinize the mathematical formulas, variable alignment, data pipelines, and logic for correctness.

### R2. Detailed Finding Report
Produce a comprehensive summary report (`Pairs_Trading_QC_Report.md`) in the working directory that categorizes any identified errors, potential edge cases, or methodological flaws. 

## Acceptance Criteria

### Audit Quality
- [ ] The report explicitly identifies the specific files and mathematical formulas reviewed.
- [ ] Any identified flaw includes a concrete explanation of *why* it is wrong and a proposed mathematical/logical correction.
- [ ] The audit explicitly covers all stages of the pairs trading pipeline (Stage 1 Pearson, Stage 2 Kalman/OU, and Stage 3 Backtesting).

### Integrity & Verification
- [ ] The agents must trace the logic directly from data ingestion to the final backtest logic.
- [ ] The final report must be saved as `Pairs_Trading_QC_Report.md` and be easily verifiable by the user.

## 2026-06-04T15:29:19Z

User update: Please ensure that the final report `Pairs_Trading_QC_Report.md` is saved inside the source folder (e.g. `Raw/Sources/` or the appropriate source directory locally) instead of just the root working directory.

## 2026-06-04T15:47:00Z

Fetch the correct Kaggle notebooks corresponding to Stage 1 (Pearson Correlation) and Stage 2 (Kalman Filter & OU Parameter Estimation) of the Pairs Trading pipeline. Perform a rigorous code verification of these notebooks to ensure that every mathematical principle and methodology documented in the LLM-WIKI regarding pairs trading is correctly implemented in the code.

Working directory: /storage/emulated/0/Quant/LLM-WIKI/
Integrity mode: development

## Requirements

### R1. Fetch and Locate Kaggle Notebooks
Identify and fetch the correct Kaggle notebooks or scripts for Stage 1 and Stage 2 of the Pairs Trading pipeline. Ensure these are the actual codebase files used for generating the historical data or parameters (e.g., using `kaggle-notebook-run` or similar mechanisms if needed, or locating them if they exist under a different name).

### R2. Comprehensive Code Verification
Perform a line-by-line verification of the code in these Stage 1 and Stage 2 notebooks against the documented math in `Plans/stage-1-pairs-trading-pearson-correlation.md` and `Plans/stage-2-pairs-trading-kalman-filter-state-space.md`. Scrutinize data alignment (global inner joins), EM matrix updates, ADF stationarity checks, and return computations.

### R3. Detailed Finding Report
Produce a supplementary summary report (`Pairs_Trading_Stage1_2_Code_Audit.md`) detailing any implementation bugs, missing logic, or deviations from the theoretical wiki documentation found specifically within these Stage 1 and Stage 2 Kaggle codebases.

## Acceptance Criteria

### Audit Quality
- [ ] The report explicitly names the Kaggle notebooks/files that were fetched and analyzed for Stage 1 and Stage 2.
- [ ] The audit explicitly verifies if the code implements the Augmented Dickey-Fuller (ADF) filter and the correct dimensions for the EM matrix updates.
- [ ] Any identified code flaw includes the specific line number, a concrete explanation of *why* it deviates from the wiki, and a proposed code correction.

### Integrity & Verification
- [ ] The agents must trace the logic directly inside the fetched Kaggle notebooks, not just the markdown plans.
- [ ] The final report must be saved as `Pairs_Trading_Stage1_2_Code_Audit.md` in the `Raw/Sources/` directory and be easily verifiable by the user.

## 2026-06-04T22:47:16Z

Develop a highly optimized, single-notebook Kaggle pipeline (`Master_Pairs_Trading_Soul.ipynb`) that executes the finalized Pairs Trading methodology. It must consolidate all stages (1, 2, 3A, and 3B), strictly implement all QC rebuttals (e.g., single-sided execution, mathematical corrections for EM matrices), and execute efficiently without crashing Kaggle's memory limits.

Working directory: /storage/emulated/0/Quant/LLM-WIKI/Soul
Integrity mode: development

## Requirements

### R1. Context Assimilation
The teamwork agents MUST read all relevant methodology plans from `Plans/` and specifically the `Soul/QC_Rebuttals_and_Context.md` document to ensure all mathematical corrections and intentional design choices (like strict single-sided lagger trading and correct $P_0$ initialization) are strictly enforced in the new codebase.

### R2. Stage 1 & 2 (Methodology & Parameters)
Implement Stage 1 to calculate Pearson correlation and output the top 500 ranked pairs to a CSV. 
Implement Stage 2 to calculate EM Kalman/OU parameters for these 500 pairs. Ensure the EM algorithm is robust enough to converge for almost all 500 pairs. Required outputs: Stage 1 rank, Pearson coeff, Q/R values, noise-to-signal ratio, Kalman OU half-life, ADF p-value (standard and Kalman), EM convergence status, EM iterations, and Hurst exponent.

### R3. Stage 3A (Optimization Phase - In-Sample)
Run a grid search optimization for all 500 pairs to maximize profit and trade count using gross price variation (no fees). 
- **Entry triggers**: $Z = 2.0, 2.5, ..., 15.0$
- **Stop Loss conditions**: Half-life time negative, $Z_{sl} = 2.5, 3.0, ..., 16.0$, or no stop loss (exit at 15:28).
- **Post-SL Freeze logic**: If stopped out, wait until $|Z| < \text{entry\_trigger} / 2$ before allowing re-entry.
- Output the single best configuration per pair to a CSV, including gross win rate, avg points profit/loss, and exit categorizations.

### R4. Stage 3B (Final Backtest Phase - Out-of-Sample)
Execute a formal out-of-sample backtest using the optimized parameters from Stage 3A.
- Strict single-sided lagger trading.
- Capital allocation: ₹10,000 base with 5x leverage (₹50,000 position size per pair).
- Apply full Zerodha MIS transaction fees and slippage models.

### R5. Kaggle Optimization
The notebook must be designed to utilize max Kaggle power (CPU/GPU) while implementing strict memory-efficiency measures (e.g., chunked processing, garbage collection) to prevent parallel processing crashes that occurred in previous iterations.

## Acceptance Criteria

### Execution & Viability
- [ ] The notebook runs completely end-to-end on a standard Kaggle environment without throwing Out-of-Memory (OOM) errors.
- [ ] The code explicitly includes the mathematical fixes for the EM updates and $P_0$ initialization.
- [ ] The Stage 3B execution logic explicitly only trades the lagging asset and takes no position in the leading asset.
- [ ] The post-stop-loss freeze logic (waiting for Z to revert to half its entry threshold) is functionally present in the code.

## 2026-06-05T00:01:16Z

Conduct a rigorous, full-team code and quantitative audit on the `Master_Pairs_Trading_Soul.ipynb` notebook located in `/storage/emulated/0/Quant/LLM-WIKI/Soul/`. 

Working directory: /storage/emulated/0/Quant/LLM-WIKI/Soul
Integrity mode: development

## Requirements

### R1. Cross-Reference LLM Wiki & QC Context
The team MUST review all existing documentation in the directory (specifically `Soul/QC_Rebuttals_and_Context.md` and the `llm_wiki` knowledge base files under `Raw/Sources/`). Ensure that the code strictly follows standard quant practices for intraday pairs trading (e.g., 1-bar execution delays, single-sided lagger trading, correct OLS $P_0$ initialization).

### R2. Verify Stage 2 (EM Convergence & Q/R Ratio)
The previous version suffered a catastrophic collapse where $Q$ hit $10^{-12}$ and the EM algorithm failed to converge, resulting in all pairs being marked `tradeable=False`. 
- Verify that the new $Q$ matrix floor (e.g., $10^{-7}$) successfully prevents this pile-up.
- Ensure the EM max iterations are sufficiently high (e.g., 50).
- Confirm that this fix allows valid pairs to pass the ADF stationarity checks.

### R3. Verify Stage 3 (Zeroes Bug & Detailed Stats)
The previous Stage 3 output was all zeroes because non-tradeable pairs were skipped.
- Verify that Stage 3A is now processing **ALL** 500 pairs (dropping the `tradeable == True` filter).
- Verify that the `run_backtest_numba` engine correctly calculates and exports the newly added detailed statistics: `avg_points_profit`, `avg_points_loss`, `exit_mr_count`, `exit_sl_count`, `exit_hl_count`, and `exit_session_count`.

### R4. Final Kaggle Production Run
Once the code is thoroughly audited and any remaining bugs are patched, push the notebook to Kaggle as the final production-grade run. Monitor the run using the `kaggle-pulse-check` skill until complete.

## Acceptance Criteria
- [ ] The notebook passes all static checks by the `Code & Quant Audit Team`.
- [ ] Stage 2 correctly produces a non-collapsed Q/R ratio.
- [ ] Stage 3A correctly processes all 500 pairs and outputs the detailed exit stats.
- [ ] The Kaggle kernel `master-pairs-trading-soul` executes to `COMPLETE` status without crashing.
