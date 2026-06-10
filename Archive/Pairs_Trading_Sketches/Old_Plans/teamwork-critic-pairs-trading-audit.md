> [!WARNING]
> **ARCHIVED & OBSOLETE**
> This file is part of the trial-and-error "Sketch" phase. 
> The mathematics and code herein may contain deprecated Expectation-Maximization loops or failed concepts.
> The final, verified truth is located in the `Soul/` directory.
> Tags: #archived-sketch #pairs-trading-prototype

# Plan: Pairs Trading QC Audit Critic Verification

## Objective
Mathematically and methodologically verify the 11 flaws and proposed corrections identified by the explorer agent in the Pairs Trading pipeline. Scrutinize the Kalman Filter EM updates, Rauch-Tung-Striebel (RTS) smoother cross-covariance, Ornstein-Uhlenbeck (OU) parameter estimation, Kalman innovation Z-score calculation, execution timing biases, and single-sided execution. Propose refinements where necessary and write the final verification report.

## Open Questions (for user review)
- None. We will proceed with the analytical mathematical verification based on standard state-space modeling and econometrics literature.

## Proposed Approach & Actual Results

### Step 1 — Analyze Explorer's Findings
- **Plan**: Read and decompose the 11 flaws reported in `teamwork_preview_explorer_audit_1/findings.md` and formulate mathematical checks.
- **Actual Results**: Analyzed findings.md in detail. Verified that all 11 findings were correct.

### Step 2 — Verify Kalman Filter EM Updates & RTS Smoother
- **Plan**: Scrutinize the mathematical validity of the process noise covariance matrix ($Q_{new}$) and cross-covariance ($P_{t,t-1|T}$) updates.
- **Actual Results**: Verified the dimensional mismatches in the original plan. Proved the mathematical correctness of the explorer's proposed $Q_{new}$ and recursive $P_{t,t-1|T}$ formulas.
- **Deviations/Refinement**: Refined the EM updates to support diagonal structure constraints and a positive semi-definite regularization bound ($Q_{ii} \ge \delta > 0$) to prevent filter divergence.

### Step 3 — Verify OU Parameter Estimation & Constraints
- **Plan**: Verify AR(1) to OU parameter mapping and log constraints.
- **Actual Results**: Verified the mapping formulas $\kappa = -\ln(\phi)$ and $\sigma_{OU} = \sigma_{AR}\sqrt{-2\ln(\phi)/(1-\phi^2)}$. 
- **Deviations/Refinement**: Highlighted that $0 < \phi < 1$ must be enforced in code as a filter for stationary mean reversion to prevent negative logs and infinite half-lives.

### Step 4 — Verify Kalman Z-Score Formulation
- **Plan**: Compare rolling standard deviation versus native innovation variance $S_t$.
- **Actual Results**: Proved that native Kalman standardization $z_t = e_t / \sqrt{S_t}$ is the mathematically correct and model-consistent formulation.
- **Deviations/Refinement**: Demonstrated that using native Z-scores naturally resolves the rolling window priming issue (Flaw 10) by eliminating the rolling window entirely.

### Step 5 — Verify Execution Timing, Lookahead Bias, and Single-sided Trading
- **Plan**: Analyze lookahead bias and market neutrality.
- **Actual Results**: Confirmed that entering at the close of the signaling bar is a lookahead bias, and trading only the lagging asset violates market neutrality.
- **Deviations/Refinement**: Refined the explorer's correction for two-sided trading. Because the model uses log-prices, the quantity hedge ratio must be adjusted by the asset price ratio: $Q_B = -\beta_t (P_A / P_B) Q_A$ to ensure dollar-neutral hedging.

### Step 6 — Write Verification Report
- **Plan**: Save the report to `/storage/emulated/0/Quant/LLM-WIKI/.agents/teamwork_preview_critic_audit_1/math_qc_review.md`.
- **Actual Results**: Successfully saved `math_qc_review.md` in the working directory.

## Time Estimate
- **Estimated**: 10 minutes.
- **Actual**: 10 minutes.

## Connections to Existing Skills
- [[plan-first]]

