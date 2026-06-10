> [!WARNING]
> **ARCHIVED & OBSOLETE**
> This file is part of the trial-and-error "Sketch" phase. 
> The mathematics and code herein may contain deprecated Expectation-Maximization loops or failed concepts.
> The final, verified truth is located in the `Soul/` directory.
> Tags: #archived-sketch #pairs-trading-prototype

# Master Plan: Deep Validation & Finalization of Pairs Trading (Sketch 3)

## 1. Objective
To conduct a rigorous, unbiased, in-depth verification of the pairs trading methodologies found in `sketch - 1` (Original) and `sketch - 2` (Post-QC). We will treat both sketches with a grain of salt, identifying discrepancies, mathematical errors, and root causes of failures. The ultimate goal is to create a united, mathematically pure, and finalized pairs trading structure in `sketch - 3` with zero errors or misconceptions.

## 2. Core Strategy: The Top 5 Pairs Isolation
Because running computations on 500 pairs is computationally heavy and obscures root causes, **all validation, debugging, and finalizing will be performed exclusively on the Top 5 Pairs**. 
We will extract these top 5 pairs from the existing Stage 1 CSV files. Once the methodology, math, and code perfectly achieve our goals on these 5 pairs, scaling to 500 will be a trivial final step.

## 3. Stage-by-Stage Focus

### Stage 1 (Pearson Correlation)
- **Status**: Mostly consistent between Sketch 1 and Sketch 2.
- **Action**: Quickly validate the log-return calculation, handling of overnight gaps, and alignment. Extract the top 5 pairs to be used for the rest of the project.

### Stage 2 (Kalman Filter & EM Calibration) - THE CRITICAL BOTTLENECK
- **The Problem**: Sketch 1 had massive half-lives (~9 min to 90,000 min depending on the run) but "somewhat converged." Sketch 2 had ultra-short half-lives (~2.7 min) and a 1e-7 floor, but EM convergence was abysmal (nearly 0%). 
- **The Goal**: Achieve near 90%-100% EM convergence for the top 5 pairs. We must discover the mathematical root cause of the EM failures. Why did Sketch 1 converge better, and was its approach actually correct despite the bugs? What is the *true* half-life?
- **Action**: A multi-agent deep dive into the EM algorithm, the Expectation (RTS Smoother) and Maximization (Matrix updates) steps, the initialization of $P_0$, and the handling of overnight jumps.

### Stage 3 (Backtesting & Execution)
- **The Problem**: Discrepancies in Z-score formulas (Kalman innovation Z vs OU Z) and single-sided vs market-neutral execution.
- **Action**: Finalize the exact trading logic, signal generation, and realistic fee/slippage modeling once Stage 2 outputs are mathematically perfected.

## 4. Deliverables in `sketch - 3`
Throughout this process, the following documents will be constructed in the `sketch - 3` folder:

1. **`plan.md`** *(This document)*: The master roadmap and rules of engagement.
2. **`QC_Audit.md`**: The living forensic log. It will contain all audit information, discrepancies found between Sketch 1 and Sketch 2, the root causes of failures (especially EM non-convergence), and the reasoning behind the final chosen methodology.
3. **`full_methodology.md`**: The definitive, in-depth mathematical and logical specification for each stage.
4. **Final Code/Notebooks**: The perfectly validated code, strictly tested on the Top 5 pairs before any full-scale deployment.

## 5. Rules of Engagement
- **No Bias**: Sketch 1 and Sketch 2 are equally suspect until proven mathematically sound.
- **No Blind Running**: No full Kaggle runs on 500 pairs until the Top 5 are perfectly solved. Kaggle will only be used for targeted validation and verification of the 5 pairs.
- **Math First**: Code is secondary. If the math doesn't guarantee convergence, the code will not be written.
