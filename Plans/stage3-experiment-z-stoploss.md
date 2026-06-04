# Stage 3 Strict Stop-Loss & Suspension Experiment (V5)

## Objective
To test the "Strict Stop-Loss" hypothesis: If a trade has a negative Gross PNL exactly at its half-life time (e.g. 42 minutes), exit immediately and suspend all further trading until the spread naturally returns to `|Z| < 1.0`. Only enter trades at `Z=3` and `Z=4`.

## Final Kaggle Output Results

| Z_ENTRY | TRADES | NET_WIN% | GROSS_WIN% | GROSS_PNL | NET_PNL |
|---------|--------|----------|------------|-----------|---------|
| 3.0     | 72     | 43.1%    | 47.2%      | 4889.4    | 202.6   |
| 4.0     | 31     | 48.4%    | 48.4%      | 1962.0    | -58.2   |

*(Note: Capital = ₹50,000 isolated per pair, representing ₹10,000 at 5x MIS Leverage. Tested over 20 trading days).*

## Comparative Analysis vs V4 (Pure Mean Reversion)

Let's compare these results to the previous experiment where we just held until `Z=0` with **no structural stop-loss**:

| Experiment | Z_ENTRY | EXIT_MODE | TRADES | NET_WIN% | NET_PNL  |
|------------|---------|-----------|--------|----------|----------|
| **V4 (No Stop-Loss)** | 3.0 | `z_zero` | 69 | 59.4% | **+2925.0** |
| **V5 (Strict Stop)**  | 3.0 | `hl_stop`| 72 | 43.1% | **+202.6**  |
| **V4 (No Stop-Loss)** | 4.0 | `z_zero` | 30 | 63.3% | **+2564.5** |
| **V5 (Strict Stop)**  | 4.0 | `hl_stop`| 31 | 48.4% | **-58.2**   |

## Conclusion & Discovery
The Strict Stop-Loss logic **destroyed the edge** of the strategy.

Why? Mean reversion is mathematically driven by "fat tails". A spread might trigger an entry at `Z=3`, continue widening to `Z=5` (putting the trade temporarily deeply negative exactly at the half-life mark), and then suddenly snap back to `Z=0`. 

In V4, the algorithm calmly held through that temporary pain until the snap-back occurred, resulting in a ~60% win rate and massive profits. 

In V5, your hypothesis forced the algorithm to panic and exit precisely when the trade was at maximum pain, locking in a loss and missing the eventual reversion. 

**Recommendation:** Do not use the structural stop-loss at half-life. The V4 `z_zero` exit logic is the mathematical peak for this model.
