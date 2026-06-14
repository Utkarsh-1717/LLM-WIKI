# Plan: Advanced Telemetry & Dynamic Lagger Detection

## Objective
To implement a "smart" Single-Sided Lagger Engine. Instead of blindly trading `sym_a`, the algorithm will use the first 20 days of data (the `ZSCORE_WINDOW` / 7500 bars) as a training buffer to dynamically detect which asset is the true "lagger" using 1-bar lagged cross-correlation. It will then exclusively trade that lagging asset for the remainder of the session, outputting deep analytical telemetry.

## 1. Dynamic Lagger Detection
I reviewed the archived `stage3_pairs_backtest.ipynb` and the `Pairs_Trading_QC_Report.md`. I will extract the `detect_lagger` logic and apply the exact correction mentioned in your QC report (nulling out 09:15 overnight gaps).

**Logic Flow:**
1. Slice the first 7,500 bars (20 days).
2. Calculate 1-minute log returns.
3. **QC Correction:** Force all returns at 09:15 AM to `0.0` so massive overnight gaps do not pollute the correlation calculation.
4. Calculate 1-bar lagged cross-correlation:
   - `corr_a_lags`: Correlation of A's returns today vs B's returns yesterday.
   - `corr_b_lags`: Correlation of B's returns today vs A's returns yesterday.
5. Whichever asset responds more strongly to the other asset's past movements is mathematically defined as the **Lagger**.

## 2. Updated Entry Logic
The algorithm will still calculate the spread as $Spread = Y_A - (\alpha + \beta Y_B)$, but the entry logic will mirror the archive structure to correctly reverse directions depending on who the lagger is:

- **If $Z \ge 2.0$ (Spread is Wide, A is relatively overvalued):**
  - If `sym_a` is lagger: Expect A to fall $\rightarrow$ **SHORT A**
  - If `sym_b` is lagger: Expect B to rise $\rightarrow$ **LONG B**
- **If $Z \le -2.0$ (Spread is Narrow, A is relatively undervalued):**
  - If `sym_a` is lagger: Expect A to rise $\rightarrow$ **LONG A**
  - If `sym_b` is lagger: Expect B to fall $\rightarrow$ **SHORT B**

## 3. Advanced Telemetry Outputs
The engine will export the following new columns into `continuous_ols_production_results_all.csv`:
- `lagger_asset`: Which asset was traded ("A" or "B").
- `ols_gross_pnl` vs `ols_net_pnl`: Profit before and after Zerodha fees.
- `gross_win_rate` vs `net_win_rate`: The win rate strictly on price movement vs after fee drag.
- `avg_price_captured`: The actual average ₹ movement per share captured per trade.
- `avg_fee_drag`: The average transaction cost per trade (the required Breakeven Hurdle).
- `mean_rev_exits`: Count of trades hitting Z=0.
- `eod_exits`: Count of trades locked out at 15:15 PM.

## Next Steps
Once you approve this plan, I will completely rewrite the `run_backtest_ols` execution engine in the Kaggle notebook to implement these upgrades and push the new version!
