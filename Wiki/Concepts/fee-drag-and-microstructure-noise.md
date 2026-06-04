---
tags:
  - "concept"
topics: [pairs-trading, mean-reversion, market-microstructure, slippage]
status: evergreen
created: 2026-06-04
updated: 2026-06-04
sources:
  - Raw/Sources/stage3-pairs-backtest-ipynb.md
  - Raw/Sources/pairs-stage3-backtest-csv.md
source_count: 2
aliases: [fee-drag, bid-ask-bounce, microstructure-noise, EM-overfit]
---

# Fee Drag and Microstructure Noise

A common failure mode in quantitative pairs trading when working with very high-frequency (e.g., 1-minute) equity data.

## The Bid-Ask Bounce Problem

At a 1-minute resolution, stock prices constantly oscillate between the bid price and the ask price, even if the "true" underlying value of the stock hasn't moved. This oscillation is called the **bid-ask bounce** or **microstructure noise**.

## EM Algorithm Overfitting

When applying unconstrained parameter estimation algorithms like Expectation-Maximization (EM) or Ornstein-Uhlenbeck (OU) calibrations to 1-minute data:
1. The algorithm detects the constant back-and-forth of the bid-ask bounce.
2. It incorrectly models this noise as a highly mean-reverting "spread" signal.
3. This leads to an artificially short **Half-Life** (e.g., 5-10 minutes) and highly frequent trading signals.

## The Fee Drag Devastation

While the strategy may achieve a mathematically positive **Gross PnL** (correctly predicting the bounce), the profit per trade is infinitesimal (e.g., ₹0.69). 

Because brokers charge flat fees per trade (like Zerodha's ₹40 flat intraday equity brokerage) alongside volume-based taxes like STT, the flat fees absolutely decimate the tiny gross profit. 

> [!WARNING]
> A highly frequent strategy that trades the bid-ask bounce will mathematically bleed to death from fee drag, even if its underlying statistical edge is greater than 0.

## Mitigation Strategies
- **Timeframe Scaling**: Use 5-minute or 15-minute bars to smooth out the bid-ask bounce and isolate the true fundamental spread.
- **Capital Scaling**: Since flat brokerages like ₹40 do not scale, applying leverage (e.g., trading ₹500,000 instead of ₹10,000) dilutes the fee percentage from 0.4% down to 0.008%, potentially flipping the strategy to net profitability.
- **Fee Filters**: Do not trigger trades unless the expected Z-score reversion amplitude far exceeds the known fixed and variable transaction costs.

## Connections
- [[pairs-trading-pipeline]] -- Stage 3 of the pipeline was killed by this exact fee drag problem.
- [[session-continuous-returns]] -- The session continuous logic provides the clean data for this analysis.
- [[kaggle-compute]] -- We proved this failure mode using 41 parallel backtests on Kaggle.
