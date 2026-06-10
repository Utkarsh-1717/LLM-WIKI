> [!WARNING]
> **ARCHIVED & OBSOLETE**
> This file is part of the trial-and-error "Sketch" phase. 
> The mathematics and code herein may contain deprecated Expectation-Maximization loops or failed concepts.
> The final, verified truth is located in the `Soul/` directory.
> Tags: #archived-sketch #pairs-trading-prototype

# Plan: Master Pairs Trading Soul Pipeline

## Objective
Build, run, and verify a consolidated production-grade Pairs Trading pipeline in a single, memory-efficient Kaggle notebook (`Master_Pairs_Trading_Soul.ipynb`). The pipeline runs Pearson screening, Kalman Filter EM calibration, grid search parameter optimization, and out-of-sample backtesting with execution delays, slippage, and transaction fees.

## Open Questions (for user review)
- Are there specific parameters for the EM calibration we want to bound or seed other than the first day's OLS? We will initialize $P_{0|0} = 10 \cdot \sigma^2 \cdot (X^\top X)^{-1}$ and state vector $\theta_{0|0}$ from the first 390 bars.
- Do we have the Kaggle credentials set in `~/.quant_env`? Yes, KAGGLE_USERNAME and KAGGLE_KEY are in the env file, and we will hardcode them in the dataset publishing cell.

## Proposed Approach

### Step 1 — Plan Creation
- What: Create the plan file at `/storage/emulated/0/Quant/LLM-WIKI/Plans/Master_Pairs_Trading_Soul.md`.
- Why: Comply with the plan-first rule.
- How: Write to the target path.

### Step 2 — Construct and write `build_soul_notebook.py`
- What: Create a Python script `build_soul_notebook.py` that dynamically generates `Master_Pairs_Trading_Soul.ipynb` using `nbformat`.
- Why: Alternate markdown and code cells for each stage as required by instructions. Include the correct math, Numba backtest, and publishing code.
- How: Use `write_to_file` in the workspace directory.

### Step 3 — Generate the Notebook locally
- What: Execute `build_soul_notebook.py` to create `/storage/emulated/0/Quant/LLM-WIKI/Soul/Master_Pairs_Trading_Soul.ipynb`.
- Why: Create the notebook before pushing it to Kaggle.
- How: Propose running the python script.

### Step 4 — Write Kaggle Metadata
- What: Create `/storage/emulated/0/Quant/LLM-WIKI/Soul/kernel-metadata.json` matching the slug `master-pairs-trading-soul`.
- Why: Required for kaggle kernels push.
- How: Write `kernel-metadata.json`.

### Step 5 — Push and Pulse Check
- What: Push the notebook to Kaggle using `kaggle kernels push -p /storage/emulated/0/Quant/LLM-WIKI/Soul/`.
- Why: Trigger execution on Kaggle.
- How: Propose `kaggle kernels push` and monitor with `kaggle-pulse-check` python script running in the background or foreground.

### Step 6 — Verify Results & Handoff
- What: Confirm end-to-end execution without OOM, dataset publishing, and write the handoff report.
- Why: Complete the milestone.
- How: Verify the output files, read logs if needed, and write `handoff.md`.

## Time Estimate
~10 minutes build and local validation, ~20-30 minutes for Kaggle execution and monitoring.

## Connections to Existing Skills
- [[plan-first]]
- [[kaggle-notebook-run]]
- [[kaggle-pulse-check]]
