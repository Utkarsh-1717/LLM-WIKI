---
title: Predictive Parameter Extraction
tags:
- concept
topics:
- pairs-trading
- machine-learning
- statistics
sources: []
source_count: 0
created: '2026-06-13'
---
# Predictive Parameter Extraction (Walk-Forward Physics)

## The Danger of Hindsight PnL
When scanning a massive combinatorial space (e.g., 125,000 pairs from the NSE 500), it is a catastrophic statistical error to rank the pairs purely by their backtested Net PnL or Win Rate. 
PnL and Win Rate are **Hindsight Derived Metrics**. They are the result of specific price paths interacting with a specific entry threshold (Z > 2.0). If a non-stationary pair happens to spike wildly and cross Z=2.0 several times before collapsing, it may register a massive backtested PnL purely by luck. Because this PnL is derived from historical path-dependency, it has near-zero predictive power for the future (Walk-Forward).

## The Solution: Ex-Ante Physical Parameters
To predict which pairs will be profitable *tomorrow*, we must extract the structural physical properties of the spread *before* any trading logic is applied. These are independent variables.

By computing these physical properties for all 125,000 pairs, we can build a predictive ranking filter (e.g., isolating pairs with high volatility, extremely fast half-lives, and 99% stationarity confidence). 

### 1. Stationarity (ADF p-value)
The ultimate prerequisite. It measures the absolute strength of the "rubber band" tying the two assets together. 
- **Predictive Power**: Extremely High. Our 125,000 pair scan proved a strong negative correlation between p-value and PnL. (Lower p-value = Higher Profit).

### 2. Ornstein-Uhlenbeck (OU) Half-Life
Measures exactly how fast (in minutes) the spread reverts to its mean after a dislocation. 
- **Predictive Power**: High. A 15-minute half-life guarantees high trade frequency and minimal exposure time. A 3,000-minute half-life means capital will be tied up for days, bleeding to intraday square-off rules.

### 3. Spread Volatility ($\sigma$)
The standard deviation of the raw spread.
- **Predictive Power**: High. Even if a pair is perfectly cointegrated, if its spread only moves ₹0.50, all gross profit will be destroyed by the ₹2.00 brokerage fee. High spread volatility ensures the "meat" of the move is large enough to survive friction.

### 4. Zero-Crossings Rate
A strict physical count of how many times the spread crosses the 0-mean line over the dataset.
- **Predictive Power**: Moderate/High. This is a pure physical measure of mean-reversion frequency, entirely independent of Z-score entry logic.

### 5. Kalman Q (Process Variance)
The theoretical variance of the state relationship. Derived analytically from the OU process ($Q = \sigma^2 \cdot (1 - \exp(-2\lambda \Delta t))$).
- **Predictive Power**: High. A low Q means the Beta relationship is structurally stable. A high Q means the relationship is constantly warping.

## Connections
- [[continuous-ols-execution]]
- [[pairs-trading-strategy]]
- [[correlation-vs-cointegration-fallacy]]
