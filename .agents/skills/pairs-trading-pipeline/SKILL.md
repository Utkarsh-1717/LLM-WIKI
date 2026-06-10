---
name: pairs-trading-pipeline
trigger: [pairs trading, run pairs, cointegration backtest, pairs pipeline, nse pairs, statistical arbitrage]
description: Runs the complete NSE intraday pairs trading pipeline (Pearson → Cointegration → OU Calibration → Kalman / Continuous OLS execution) on Kaggle. Encodes all validated design decisions and failure modes.
version: 1.0.0
last_updated: 2026-06-10
---

# Pairs Trading Pipeline Skill

## Purpose

Automates the 5-stage NSE intraday pairs trading pipeline from raw data to final backtest results. Every stage has been validated on 500 pairs across 5.5 months (104 trading days) of 1-minute NSE data.

---

## Pipeline Overview

| Stage | Purpose | Script | Kaggle Kernel |
|---|---|---|---|
| 1 — Pearson | Find top 500 correlated pairs | Inside full pipeline | `pairs-full-pipeline-vN` |
| 1B — Cointegration | ADF test on continuous OLS spread | `build_continuous_ols_pipeline_nb.py` | `pairs-continuous-ols-pipeline-vN` |
| 2 — OU Calibration | Compute half-lives and Kalman Q | Inside full pipeline | `pairs-full-pipeline-vN` |
| 3A — Kalman Execution | Worst-Case + DR backtest | `build_full_pipeline_nb.py` | `pairs-full-pipeline-vN` |
| 3B — OLS Execution | Continuous rolling OLS backtest | `build_continuous_ols_pipeline_nb.py` | `pairs-continuous-ols-pipeline-vN` |

---

## Validated Configuration (Production)

```python
# Always use these values — validated against true half-life measurements
ZSCORE_WINDOW = 7500      # 20 trading days — NEVER use 375 (see Failure 6 in kaggle-notebook-run)
Z_ENTRY = 2.0             # Entry threshold
EOD_EXIT_TIME = 1515      # 15:15 PM mandatory square-off (MIS compliance)
BASE_CAPITAL = 10_000.0   # INR per pair
LEVERAGE = 5.0            # NSE MIS intraday margin
FRICTION_PCT = 0.0005     # 0.05% per leg (brokerage + STT + exchange + slippage)
ROLLING_WINDOW = 7500     # OLS lookback = same as Z-score window
NUM_CHUNKS = 4            # OU calibration chunks
WARMUP_BARS = 1875        # 5 trading days warmup before trading begins
```

---

## Stage 1B — Cointegration (Critical Filter)

The cointegration filter is the most important part of the pipeline. Without it:
- 500 pairs → Net PnL **−₹4.1 Lakhs** (228/500 profitable)

With the Engle-Granger ADF filter (`p < 0.05` on continuous OLS spread):
- 358 pairs → Net PnL **+₹54,937** (185/358 profitable)

### Valid Spread Generation (MANDATORY for ADF)
```python
# Use this — not Kalman residuals, not EOD OLS residuals
beta   = ya.rolling(7500).cov(yb) / yb.rolling(7500).var()
alpha  = ya.rolling(7500).mean() - beta * yb.rolling(7500).mean()
spread = ya - (alpha + beta * yb)

from statsmodels.tsa.stattools import adfuller
adf_stat, p_val = adfuller(spread.dropna(), maxlag=1)
```

---

## Known Profitable Sectors (From 500-Pair Validation)

The algorithm mathematically identified these sector pairs as structurally cointegrated:

| Sector | Example Pairs |
|---|---|
| Railways | IRCON-RITES, RAILTEL-RITES, BEML-IRCON, RITES-RVNL, IRFC-RITES |
| Cement | ACC-AMBUJACEM |
| Real Estate | DLF-PRESTIGE |
| Cables/Wires | KEI-POLYCAB |
| PSU Banks | IOB-MAHABANK |

---

## Execution Method Comparison

| Method | Profitable Pairs | Total +PnL | PnL/Trade | Cointegration Testable? |
|---|---|---|---|---|
| Kalman: Fixed Speed-Limit | 54 | ₹1.85L | ₹18.46 | ❌ No |
| Kalman: Dominant Regime | 138 | ₹5.07L | ₹55.12 | ❌ No |
| **Kalman: Worst-Case** | **168** | **₹6.30L** | **₹70.29** | ❌ No |
| OLS EOD (daily beta) | 131 | ₹4.69L | ₹199.12 | ❌ No |
| **Continuous OLS + ADF** | **185/358** | **+₹54,937 net** | **+₹7.70** | **✅ Yes** |

**Decision rule**: Use Continuous OLS for pre-screening (ADF filter). Use Kalman Worst-Case for execution on screened pairs.

---

## Capital Scaling (Top 5 Cointegrated OLS Pairs)

| Base Capital | Net Profit (5.5 months) | Monthly Return |
|---|---|---|
| ₹10,000 | ₹65,461 | ~44% |
| ₹1,00,000 | ₹6,54,610 | ~44% |
| ₹5,00,000 | ₹32,73,050 | ~44% |

> ⚠️ These use in-sample best-5 selection (lookahead bias). Live trading must use ADF pre-screening.

---

## Running the Pipeline

### Step 1: Build the notebooks
```bash
cd /storage/emulated/0/Quant/LLM-WIKI/Soul/pairs-trading/Code
python build_full_pipeline_nb.py          # Kalman pipeline
python build_continuous_ols_pipeline_nb.py # OLS + cointegration
```

### Step 2: Push to Kaggle
```bash
export $(cat ~/.quant_env | xargs)
kaggle kernels push -p kaggle_staging/full_pipeline
kaggle kernels push -p kaggle_staging/continuous_ols_pipeline
```

### Step 3: Monitor both kernels
Use `monitor_dual.py` to watch both in one background task:
```bash
python monitor_dual.py  # runs in background, notifies on COMPLETE/ERROR
```

### Step 4: Download results
```bash
kaggle kernels output utkarshpatelthefirst/pairs-full-pipeline-vN -p kaggle_staging/outputs_kalman
kaggle kernels output utkarshpatelthefirst/pairs-continuous-ols-pipeline-vN -p kaggle_staging/outputs_ols
```

### Step 5: Analyze
```python
# Cross-reference cointegration p-values against PnL
coin = load_csv('outputs_ols/continuous_ols_production_results.csv')
# Filter: pval < 0.05 for structurally cointegrated pairs
profitable = [r for r in coin if float(r['adf_pval'] or 1) < 0.05]
```

---

## Output Files Reference

| File | Contents |
|---|---|
| `pairs_all.csv` | All pairs with Pearson stats |
| `pairs_top500.csv` | Top 500 pairs |
| `stage2_ou_calibration.csv` | OU half-lives per pair |
| `production_engine_results.csv` | Kalman FSL/WC/DR PnL per pair |
| `continuous_ols_production_results.csv` | OLS PnL + ADF p-value per pair |

---

## Connections

- [[kaggle-notebook-run]]
- [[kaggle-pulse-check]]
- [[pairs-trading-strategy]]
- [[stage1b-cointegration]]
- [[continuous-ols-execution]]
- [[backtest-record-pairs-trading]]
- [[master-data-1min-dataset]]
