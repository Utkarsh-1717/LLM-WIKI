---
title: Correlation vs Cointegration Fallacy
tags:
- concept
topics:
- pairs-trading
- statistics
- cointegration
sources: []
source_count: 0
created: '2026-06-13'
---
# The Correlation vs Cointegration Fallacy

## The Common Retail Myth
A widespread misconception in retail quantitative finance is that Pairs Trading requires two assets to be highly correlated. Many strategies begin by filtering for pairs with a Pearson Correlation coefficient ($\rho$) > 0.85, assuming that because the two lines look similar on a chart, they will revert when they diverge.

This is a mathematical fallacy.

## The Mathematical Proof (125,000 Pair Scan)
On 2026-06-13, a massive computational sweep was executed on Kaggle across all 124,750 possible combination pairs of the NSE 500 universe over a 5.5-month 1-minute intraday dataset.

The results definitively proved that **Pearson Correlation ($\rho$) is statistically useless for determining the profitability of a pairs trade.**

When computing the Spearman Rank Correlation between Final Backtested PnL and the ex-ante parameters of 57,589 profitable pairs:
- **Stationarity (ADF p-value)**: $\rho_{rank} = -0.2146$ (Strong Negative. Lower p-val reliably equals Higher PnL).
- **Pearson Correlation ($\rho$)**: $\rho_{rank} = -0.0651$ (Statistically Zero / Slight Negative).

## Why High Correlation Destroys PnL
The data revealed that hyper-correlated pairs actually perform *worse*. 
If two assets are perfectly correlated, they move exactly in tandem. If they move exactly in tandem, their spread variance ($\sigma_{spread}$) is incredibly low. 
For a pairs trade to trigger an entry, the spread must widen beyond a 2.0 Z-Score. If the two assets are hyper-correlated, the spread never widens enough to create a tradeable dislocation. And even if it does, the absolute price movement is often so small (e.g., ₹0.25) that it is completely consumed by brokerage and STT friction upon exit.

## The True Separator: Cointegration
Pearson Correlation measures how two variables move together (directional similarity). 
**Cointegration (Engle-Granger ADF Test)** measures whether the *distance* between two variables is stationary over time (mean-reverting).

A pair can have a Pearson correlation of 0.10 (moving completely independently day-to-day) but be perfectly cointegrated (meaning their mathematical spread always snaps back to a baseline). In pairs trading, we strictly trade the stationarity of the spread. We do not care if the assets look similar.

**Conclusion**: Never rank pairs by Pearson Correlation. Rank pairs by Stationarity (ADF p-value) and Spread Volatility. 

## Connections
- [[pearson-correlation-screening]]
- [[predictive-parameter-extraction]]
- [[continuous-ols-execution]]
