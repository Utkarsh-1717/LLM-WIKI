---
title: PM_Lagger_Lockout_Failure
tags:
- post-mortem
topics:
- pairs-trading
- execution-logic
- numba
sources: []
source_count: 0
created: '2026-06-13'
---
# Post-Mortem: Lagger Lockout Failure (Numba Execution)

## The AI's Hallucination
When converting the Python sequential pairs trading backtest into a vectorized C++ Numba engine (`@njit`), the AI completely dropped the `is_locked_out` logic state. It allowed the execution engine to immediately re-enter a trade on the very next minute after a forced End-Of-Day (15:15) exit if the Z-Score was still beyond the 2.0 threshold.

## The Human Correction
The human explicitly pointed back to the reference notebook (`stage3-pairs-backtest.ipynb`) which contained strict lockout logic preventing immediate re-entry.

## The Structural Root Cause
The AI was overly focused on speeding up the loop for the 125,000 pair combinatorial explosion and failed to trace the *state-dependent physical requirements* of mean-reversion. 
When a position is forcibly closed at EOD (due to intraday MIS constraints), the mathematical spread itself has *not* reverted. The dislocation is still > 2.0. If you do not lock the strategy out, the engine will instantly buy back into the broken spread at 09:15 the next morning (or 15:16 if testing later times), guaranteeing immediate drawdown and artificial trade count inflation purely driven by friction.

## The Permanent Rule
**Rule**: All mean-reverting execution engines MUST contain a lockout state (`is_locked_out`). If a trade is exited for any reason OTHER than the Z-score physically crossing the mean (e.g., forced EOD square-off, Stop Loss hit), the engine is mathematically forbidden from re-entering the same directional trade until the Z-score naturally decays back into the neutral zone (`-1.0 < Z < 1.0`).

## Connections
- [[QC-decisions-pairs-trading]]
- [[continuous-ols-execution]]
- [[pairs-trading-strategy]]
