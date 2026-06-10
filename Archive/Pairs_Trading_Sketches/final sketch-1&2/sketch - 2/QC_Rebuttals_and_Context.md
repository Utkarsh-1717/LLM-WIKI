> [!WARNING]
> **ARCHIVED & OBSOLETE**
> This file is part of the trial-and-error "Sketch" phase. 
> The mathematics and code herein may contain deprecated Expectation-Maximization loops or failed concepts.
> The final, verified truth is located in the `Soul/` directory.
> Tags: #archived-sketch #pairs-trading-prototype

# Pairs Trading: Intentional Design Choices & QC Rebuttals

This document serves to preserve the actual, intended methodologies and rationale behind the Pairs Trading codebase, specifically addressing and clarifying why certain choices were made that automated QC audits might flag as "bugs."

## 1. Strict Data Alignment vs. Forward Filling (ffill)

**The Agent's Flag:** 
The audit flagged that calling `.dropna(how='any')` before `.ffill(limit=1)` rendered the forward-fill useless, causing a 10% data loss.

**The Intended Design (User Rationale):**
This is **INTENTIONAL**. 
- In high-frequency intraday pairs trading, comparing a stale price (forward-filled) with a fresh price creates "phantom" spread movements. 
- If Asset A doesn't print a trade at minute `t`, forward-filling its price from `t-1` while Asset B updates at `t` creates an artificial distortion in the spread. 
- The strategy strictly requires that Asset A and Asset B prices are perfectly aligned at the exact same timestamp. 
- Missing data (gaps) do not matter for the core objective, which is evaluating the mean-reverting spread on continuous, valid, contemporaneous data points.
- Therefore, dropping any incomplete row is the correct, conservative choice to prevent generating trading signals based on stale, un-executable prices.

## 6. Single-Sided Trading (Lack of Market Neutrality)

**The Agent's Flag:** 
The execution engine only buys or sells the lagging asset, completely ignoring the leading asset. The agents flagged this because standard pairs trading is supposed to be market-neutral (hedged).

**The Intended Design (User Rationale):**
This is a highly intentional, cost-optimized execution choice. 
1. **Transaction Costs:** Trading two legs doubles the fees, which destroys intraday high-frequency profitability. 
2. **Alpha Source:** The leader is already "arbitraged away" and has priced in the information. The true alpha (catch-up potential) lies entirely in the laggard. Taking a position in the leader is essentially paying fees for zero expected return.
3. **Risk Profile:** Since the strategy is strictly intraday, the risk of unhedged market crashes is significantly minimized compared to overnight holds.
**Decision**: The user's logic is fundamentally correct and mathematically sound for a high-fee environment. This is a valid "relative-value directional strategy" rather than strict market-neutral arbitrage. We completely reject the agents' suggestion to hedge. We will explicitly enforce single-sided execution in the final `Soul/Code/` production scripts.

## 7. Execution Lookahead Bias

**The Agent's Flag:** 
The backtest enters trades on the exact same 1-minute close price that is used to generate the signal, assuming zero execution latency.

**The Intended Design (User Rationale):**
This was an acceptable approximation for backtesting simplicity, as live execution will likely use tick data for precision entries (within 3-4 seconds).
**Decision**: While acceptable for an initial draft, for the strict production-grade `Soul/Code/` backtester, we will implement a 1-bar execution delay (entering on the next bar's open) or model a minor slippage penalty. This is the industry standard for conservative backtesting and ensures our simulated profits are not artificially inflated by lookahead bias.

## 5. Lack of Overnight Price Gap Scaling

**The Agent's Flag:** 
Intraday bars are concatenated across trading days without scaling the state transition, treating massive overnight gaps (17 hours) as standard 1-minute intervals. 

**The Intended Design (User Rationale):**
The core strategy is focused on macro-level cointegration drift (weekly/monthly). The parameters (beta and alpha) shouldn't wildly change overnight. The goal is simply to compare contemporaneous prices. Any spread widening at the open should ideally be treated as a trading signal, not a parameter shock.
**Decision**: The user's intuition about the macro drift is exactly right—beta doesn't radically change overnight. *However*, mathematically, the Kalman filter calculates its confidence based on time. If we don't scale the process noise ($Q$) for the weekend, the filter assumes only 1 minute has passed and becomes dangerously overconfident in Friday's parameters, causing it to react too slowly if the macro-relationship *did* shift slightly over the weekend. 
To honor the user's design, we will ACCEPT a mild mathematical correction: we will completely drop the non-trading data (as the user intended), but at the 09:15 open, we will simply inject a small "time-elapsed multiplier" into the filter's uncertainty ($P$). This tells the filter "a weekend passed, be slightly more adaptable this morning," allowing it to catch up to macro-drifts without breaking the spread signal.

## 2. Incomplete EM 'Q' Matrix Updates

**The Agent's Flag:** 
The vectorized M-step update for the process noise covariance matrix Q omitted half the required cross-product terms, leading to incorrect covariance dynamics.

**The Intended Design (User Rationale):**
This was a mathematical oversight, potentially from attempting to optimize the loop speed. 
**Decision**: We will ACCEPT the agents' proposed correction. For the final production code in `Soul/Code/`, we must implement the mathematically complete covariance expectation calculation to ensure strict accuracy of the Kalman parameters.
