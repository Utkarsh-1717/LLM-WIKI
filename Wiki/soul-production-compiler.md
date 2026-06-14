---
title: Soul Production Compiler
tags:
- concept
topics:
- production
- compiler
- soul
sources: []
source_count: 0
created: '2026-06-13'
---

# Soul Production Compiler

**Type**: Concept / Standard  
**Domain**: Quantitative Pipeline Architecture  

## Purpose

The `Soul` directory represents the final, immutable, verified production codebase for the LLM-WIKI project. Any code that successfully graduates through rigorous mathematical verification, statistical testing, and Kaggle scale-testing is "compiled" into the Soul directory.

## Core Rules

1. **No Scratch Code**: The Soul directory only contains production-ready pipeline builders, monitors, and execution scripts.
2. **Kaggle Execution Only**: All pipelines built in the Soul folder must be formatted as Jupyter Notebook generators that produce Kaggle-ready `kernel-metadata.json` configurations.
3. **Hardware Maximization**: The final production engine inside Soul must make maximum use of available hardware. If iterating over combinatorial spaces > 10,000, standard Python loops are strictly forbidden. The logic must be vectorized via Pandas, or compiled to C++ via Numba `@njit`, and parallelized across multiple CPUs using `joblib.Parallel`.
4. **Lazy Evaluation Filters**: Heavy statistical tests (such as Engle-Granger Cointegration `adfuller` testing) must never be run on the entire universe sequentially. The compiler pipeline MUST utilize a fast preliminary screen (e.g. Numba execution backtest) to filter the universe, and only run the slow test on the profitable subset.

## Active Projects

### Pairs Trading

- `build_continuous_ols_pipeline_nb.py`: Uses Numba `@njit` and Joblib 4-core parallelization to scan all 124,750 pairs of the NSE 500 matrix using continuous rolling OLS, followed by a Lazy ADF Cointegration Test only on the mathematically profitable subset.
- `build_full_pipeline_nb.py`: The Kalman Filter Worst-Case scenario execution engine.
- `monitor_dual.py`: Background system designed to monitor dual Kaggle kernel pipelines simultaneously.

## Connections

- [[continuous-ols-execution]]
- [[stage3-execution-engine]]
- [[PM_125h_Kaggle_Timeout]]
