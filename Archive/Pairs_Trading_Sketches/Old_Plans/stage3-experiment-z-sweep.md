> [!WARNING]
> **ARCHIVED & OBSOLETE**
> This file is part of the trial-and-error "Sketch" phase. 
> The mathematics and code herein may contain deprecated Expectation-Maximization loops or failed concepts.
> The final, verified truth is located in the `Soul/` directory.
> Tags: #archived-sketch #pairs-trading-prototype

# Stage 3 Z-Score Sweep Experiment (V4)

## Objective
To test the sensitivity of the Kalman-OU strategy against the top pair (BDL vs COCHINSHIP) by sweeping `Z_ENTRY` from 2.0 to 9.0 and testing two isolated exit strategies: `z_zero` (Mean Reversion) vs `hl_time` (Half-Life Timeout).

## Verification of Core Engine Integrity
The core logic remains entirely identical to Stage 3 Version 10:
* **Lagger-Leg Only Engine:** Position sizing is strictly applied only to the lagging asset via the logic: `lagging_asset = sym_a if lagger_side == "a" else sym_b`.
* **Kalman Filter & Variance:** The Kalman loop and `deque(maxlen=3750)` Welford variance remain untouched.
* **Fee Calculator:** `calc_zerodha_mis_fees` is fully preserved.

## Verified Changes (The Sweep Logic)

### 1. Hardcoded Pair Filter
We explicitly override the Half-Life Stage 3 filter to perfectly lock the dataset to the top pair:
```python
s3_df = s2_df[(s2_df["symbol_a"]=="BDL") & (s2_df["symbol_b"]=="COCHINSHIP")].copy().reset_index(drop=True)
```

### 2. Capital & Leverage Logic
Capital is correctly scaled to match 5x MIS leverage (deploying full capital into the lagger leg).
```python
CAPITAL = 50_000.0  # Represents ₹10,000 isolated capital * 5x MIS Leverage
```

### 3. Exit Condition Sweep Separation
The `exit_reason` block evaluates the `EXIT_MODE` loop variable:
* **`z_zero`**: Triggers purely on `z <= 0.0` (or `z >= 0.0` for shorts).
* **`hl_time`**: Triggers purely on `bars_held >= hl_bars`.
* *(Note: The fail-safe `FORCE_EXIT_TIME` at 15:28 remains in both to prevent overnight holds, maintaining MIS fidelity).*

---

## Final Kaggle Output Results

| Z_ENTRY | EXIT_MODE | TRADES | NET_WIN% | GROSS_PNL | NET_PNL  |
|---------|-----------|--------|----------|-----------|----------|
| 2.0     | hl_time   | 422    | 41.2%    | 8954.1    | -18522.4 |
| 2.0     | z_zero    | 196    | 58.7%    | 10029.4   | -2732.9  |
| 3.0     | hl_time   | 139    | 38.8%    | 612.7     | -8438.9  |
| **3.0** | **z_zero**| **69** | **59.4%**| **7417.5**| **2925.0** |
| **4.0** | **z_zero**| **30** | **63.3%**| **4520.2**| **2564.5** |
| 5.0     | hl_time   | 31     | 51.6%    | 1834.3    | -185.8   |
| 5.0     | z_zero    | 15     | 60.0%    | 1324.1    | 345.9    |
| 6.0     | hl_time   | 17     | 47.1%    | 3597.9    | 2490.1   |
| 6.0     | z_zero    | 10     | 40.0%    | 1187.7    | 535.6    |
| **7.0** | **hl_time**| **13**| **53.8%**| **3994.9**| **3147.9** |
| 7.0     | z_zero    | 9      | 44.4%    | 2950.9    | 2364.2   |
| 8.0     | hl_time   | 7      | 57.1%    | 1482.7    | 1026.7   |
| 8.0     | z_zero    | 6      | 50.0%    | 490.8     | 100.0    |
| 9.0     | hl_time   | 4      | 25.0%    | -297.7    | -557.9   |
| 9.0     | z_zero    | 3      | 33.3%    | -737.0    | -931.7   |

*(Note: Capital = ₹50,000 isolated per pair, representing ₹10,000 at 5x MIS Leverage. Tested over 20 trading days).*

## Key Insights

1. **Trade Frequency vs Exit Logic**: The `z_zero` exit drastically cuts down trade frequency compared to `hl_time` at lower Z-thresholds (e.g., Z=2 drops from 422 to 196 trades). This immediately saves massive amounts of capital from Zerodha fee bleed.
2. **Net Win Rate**: `z_zero` (Mean Reversion) holds a remarkably stable ~60% Net Win Rate from Z=2 to Z=5.
3. **The Sweet Spot (High Frequency)**: At **Z=3 with `z_zero`**, the strategy takes 69 trades in 20 days (3.4 trades/day), yielding **₹2925 Net PNL** on ₹50,000 capital. That is a **5.85% return in 20 days** (~73% annualized yield).
4. **The Sweet Spot (Low Frequency)**: At **Z=4 with `z_zero`**, the strategy takes 30 trades (1.5 trades/day), keeping over 50% of its Gross PNL because fees are low, yielding **₹2564 Net PNL**.
5. **Extreme Divergences**: At Z=6 and Z=7, `hl_time` outperforms `z_zero`. Why? Because at such extreme Z-scores, the price is so dislocated that simply waiting out the half-life captures a massive macro reversion, resulting in fewer but highly profitable trades.

## Conclusion
The logic of the strategy is mathematically sound and highly profitable if the Z-score and exit logic are appropriately tuned to outpace standard brokerage fees. For a balanced intraday execution, **Z=3 to Z=4 using `z_zero` exit** proves to be the optimal parameter band for this specific pair.
