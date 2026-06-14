# Percentile Optimization in Pairs Trading

Instead of relying on rigid, arbitrary, hard-coded statistical thresholds (e.g. demanding a Pearson correlation `> 0.85` or a P-Value `< 0.05`), robust quantitative strategies use **Percentile Optimization**.

By calculating statistical properties (like [[log-return-computation]] derived volatility or Half-Life) for the *entire* universe of assets, we can establish dynamic percentile boundaries. This guarantees that the execution engine only ever trades the absolute most mathematically extreme pairs in the current market regime. 

## The Physical Boundaries of Fortune
Deep analysis of 124,000+ NSE pairs proved that maximum intraday OLS profitability naturally emerges when pairs are strictly isolated by:

1. **Intraday Mean Reversion Speed (Half-Life)**
   - `Half-Life <= 10th Percentile`
   - Only the fastest reverting spreads are viable; anything slower gets crushed by [[fee-drag-and-microstructure-noise]].

2. **Macro Structural Correlation**
   - `1D Pearson Correlation >= 99th Percentile`
   - Isolates pairs whose underlying price trajectories are practically identical on a macro scale.

3. **Macro Cointegration Strength**
   - `1D ADF P-Value <= 20th Percentile`
   - `1D ADF Trend P-Value <= 50th Percentile`
   - Proves zero-mean stationarity on the macro level, ensuring the intraday swings aren't a symptom of long-term structural divergence. 

This multi-timeframe dual-verification (1m for execution properties, 1D for structural validation) systematically replaces the [[correlation-vs-cointegration-fallacy]] by honoring both.

## Connections
- [[latent-factor-arbitrage]]
- [[predictive-parameter-extraction]]
- [[pairs-trading-strategy]]
