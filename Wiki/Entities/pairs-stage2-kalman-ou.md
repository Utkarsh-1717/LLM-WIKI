---
title: pairs-stage2-kalman-ou
type: entity
tags:
  - "entity"
  - "dataset"
  - "pairs-trading"
  - "kalman-filter"
topics: [pairs-trading, datasets]
created: 2026-06-03
updated: 2026-06-03
status: completed
sources:
  - Raw/Sources/pairs-stage2-kalman-ou-csv.md
source_count: 1
---

# Pairs Stage 2 Kalman OU Dataset

The `pairs-stage2-kalman-ou` dataset is the final output of the Stage 2 Pairs Trading computation. It contains the mathematically optimal State-Space hedge ratios, Ornstein-Uhlenbeck (OU) mean-reversion parameters, and Augmented Dickey-Fuller (ADF) stationarity tests for 500 top-correlated asset pairs.

## Execution History
- **Executed on**: 2026-06-03
- **Environment**: Kaggle CPU (4-core multiprocessing)
- **Runtime**: 1043 seconds (~17 minutes)
- **Bar Count**: 44,000 per pair
- **Algorithm**: Unconstrained Expectation-Maximization (EM) loop over Kalman Filter state-space model.

## Key Statistical Findings
The unconstrained EM algorithm successfully processed all 500 pairs. The optimization algorithm found that for many pairs, the mathematically optimal hedge ratio shifted too rapidly, absorbing the spread variance into structural shift rather than mean-reversion (median half-life: 9.1 minutes). 

However, the filters correctly identified **124 strictly tradeable pairs** that satisfied all conditions:
- Stationarity: ADF `p-value < 0.05`
- Half-life Bounds: `15 mins <= half_life_minutes <= 1440 mins`

## Usage in Pipeline
This dataset is the terminal output for Stage 2 and serves as the strict filtering layer for Stage 3 (Backtesting). Only the 124 tradeable pairs will pass forward to the signal generation engine.

## Connections
- [Stage 2 Plan](../../Plans/stage-2-pairs-trading-kalman-filter-state-space.md) -- The executed plan.
- [[kaggle-compute]] -- Execution platform.
- [[pairs-trading-pipeline]] -- The parent workflow.
- [[kaggle-notebook-hardening]] -- During the execution of this dataset, critical multiprocessing fork deadlocks were discovered and documented.
