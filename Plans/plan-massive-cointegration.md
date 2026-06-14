# Plan: Massive Cointegration Execution & Zerodha Fees

## Objective
To scale the `continuous-ols-pipeline.ipynb` Kaggle notebook so that it calculates the ADF cointegration test (and the OLS backtest) across **all mathematically significant combinations** (~125,000 base pairs). Additionally, we will replace the arbitrary `0.05%` friction penalty with a mathematically precise calculation of the **actual Zerodha Intraday Equity** tax and fee structure.

## Proposed Approach

### Step 1 — Precise Zerodha Fee Function
- **What**: Remove the flat `FRICTION_PCT` and inject a highly accurate fee calculator.
- **Why**: An arbitrary 0.05% penalty distorts reality. We will calculate the exact Brokerage, STT, Exchange Transaction Charges, GST, Stamp Duty, and SEBI charges on every single trade leg.
- **How**:
  ```python
  def calc_zerodha_charges(buy_value, sell_value):
      brok_buy = min(buy_value * 0.0003, 20.0)
      brok_sell = min(sell_value * 0.0003, 20.0)
      stt = sell_value * 0.00025  # STT on sell side only
      etc = (buy_value + sell_value) * 0.0000325 # Exchange Transaction Charge
      gst = (brok_buy + brok_sell + etc) * 0.18
      stamp = buy_value * 0.00003 # Stamp duty on buy side only
      sebi = (buy_value + sell_value) * 0.000001
      return brok_buy + brok_sell + stt + etc + gst + stamp + sebi
  ```

### Step 2 — Modify Stage 1 (Pearson)
- **What**: Remove the `.head(500)` truncation.
- **Why**: We want to pass the entire universe of statistically valid correlated pairs down to the execution engine.
- **How**: 
  We will save the full array of correlated pairs to `pairs_all.csv` and pass all of them into the Execution loop.

### Step 3 — Scale Stage 3 (Continuous OLS & ADF)
- **What**: Update the execution engine loop to use the exact `calc_zerodha_charges` logic. It will naturally scale and loop over all pairs.

### Step 4 — Export Logic Update
- **What**: Sort the final results strictly by `adf_pval` (ascending) and save two files.
- **Why**: Matches your request to see the total ranked list and the top 10,000.
- **How**:
  ```python
  res_df = pd.DataFrame(results_st3).sort_values("adf_pval", ascending=True)
  res_df.to_csv("continuous_ols_production_results_all.csv", index=False)
  res_df.head(10000).to_csv("continuous_ols_top10000.csv", index=False)
  ```

## Time Estimate
~4.5 hours for the Kaggle notebook to run in production for all 100k+ pairs.

## Connections to Existing Skills
- [[kaggle-notebook-run]]
- [[plan-first]]
