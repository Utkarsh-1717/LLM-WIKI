# Pairs Trading: Stage 1 — Monthly Re-Roll Engine
**Final Production Plan v1.0** | Date: 2026-06-13

---

## Overview

A two-stage algorithmic trading system. This plan covers **Stage 1 only**: a fully automated, self-sustaining monthly engine that identifies the Top 50 highest-potential NSE pairs for the coming month using Walk-Forward physics filtering.

> [!IMPORTANT]
> **The core execution logic is not being changed.** The `build_continuous_ols_pipeline_nb.py` file is the canonical reference. Stage 1 uses the *identical* Numba backtest engine, `detect_lagger()`, `calc_zerodha_friction()`, and `process_pair()` functions — lifted verbatim. The only additions are: (1) a live data fetch step before the engine runs, and (2) a physics filter and ranked CSV export step after it runs.

---

## Architecture

```
[GitHub Actions — Monthly CRON: 3 AM IST, every 4 weeks starting 2026-06-15]
    │
    ▼
[Kaggle Notebook: pair_trading_stage1.ipynb]
    │
    ├─ Step 0: Auth → Fyers API (TOTP)
    ├─ Step 1: Fetch Live NSE 500 List (NSE Archives)
    ├─ Step 2: Download 120 Exact Trading Days @ 1-min (Fyers API)
    ├─ Step 3: 70% Coverage Filter → le_70_coverage_MMDDYY.csv
    ├─ Step 4: Continuous Rolling OLS + Numba Backtest (IDENTICAL to build_continuous_ols_pipeline_nb.py)
    ├─ Step 5: Walk-Forward Physics Filter + Ranking
    ├─ Step 6: Export 4 CSVs → Kaggle Dataset (Safe Place)
    └─ Step 7: Trigger GitHub notification (optional)
```

---

## Safe Place for Outputs

> [!IMPORTANT]
> The CSVs produced by Stage 1 are the *input* to Stage 2 live execution. They must be accessible from a cloud environment, not just a local device.

**Chosen Safe Place: Kaggle Dataset** (`utkarshpatelthefirst/pairs-stage1-outputs`)
- Free, permanent, cloud-hosted, zero cost.
- Write: from inside the Kaggle notebook using `api.dataset_create_version()`.
- Read: Stage 2 engine mounts the dataset as a Kaggle input at `/kaggle/input/pairs-stage1-outputs/`.
- Old files are automatically versioned and overwritten — no manual cleanup needed.

---

## Proposed Changes

### Component: Stage 1 Kaggle Notebook Builder

#### [NEW] `pair_trading_stage1.py`
`Soul/pairs-trading/Stage-1/Code/pair_trading_stage1.py`

The new Kaggle notebook generator. Builds `pair_trading_stage1.ipynb`.

**Step 0 — Fyers Authentication**
- Identical TOTP 5-step auth from `fyers-auth` skill.
- Credentials hardcoded in the notebook (Kaggle has no `.quant_env`).

**Step 1 — Live NSE 500 Fetch**
- Fetches `https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv` with `User-Agent` header.
- Saves `NSE-500_MMDDYY.csv` with plain symbols (e.g., `RELIANCE`).
- Works every year, zero hardcoding.

**Step 2 — Exact 120 Trading Days Download**
- Uses Fyers `fyers.history()` API with `resolution=1`.
- Chunks requests into ≤90-day calendar windows (2 chunks covers 175 days → always includes 120+ trading days).
- Uses `exchange_utils.get_holidays()` or NSE Bhav Copy calendar API to enumerate exactly which calendar dates were active trading days, then trims to the most recent 120.

> [!IMPORTANT]
> **No arbitrary approximation like "175 calendar days → ~120 trading days".** The system will explicitly verify actual trading days by checking which dates have data after the fetch and trimming to the latest 120 unique trading dates.

- Only stores `(symbol, timestamp, close)` in memory — open/high/low/volume discarded.
- `0.5s` sleep between every API call.
- Silent error collection: failed symbols are logged, not raised.

**Step 3 — 70% Coverage Filter**
- Minimum required bars: `120 × 375 × 0.70 = 31,500 bars`.
- Any symbol below this is excluded from all further analysis.
- Saves `le_70_coverage_MMDDYY.csv` (will be empty for established stocks, populated for new IPOs etc).

**Step 4 — Continuous Vectorized OLS + Numba Backtest**
- **Identical to `build_continuous_ols_pipeline_nb.py`**: same `ROLLING_WINDOW = 7500` (≈20 trading days × 375 bars), `Z_ENTRY = 2.0`, `EOD_EXIT_TIME = 1515`, `BASE_CAPITAL = 10_000`, `LEVERAGE = 5.0`.
- Same `detect_lagger()` using warmup `7500` bars.
- Same `process_pair()` → `run_backtest_numba()` → `_numba_backtest_loop()`.
- Same Zerodha Equity MIS fee structure: `calc_zerodha_friction()`.
- Same `is_locked_out` logic after every EOD exit.
- Same `OPENBLAS_NUM_THREADS=1` + `OMP_NUM_THREADS=1` thread-locking before numpy import.
- Same Lazy ADF: only run `adfuller()` on pairs where `net_pnl > 0`.
- Output: `Ranked_Profit_All_MMDDYY.csv` — all executed pairs, sorted by `ols_net_pnl` descending, all original fields preserved.

**Step 5 — Walk-Forward Physics Filter**
- Take `Ranked_Profit_All_MMDDYY.csv`.
- Apply the validated 4-bound physics filter (derived from 124,750-pair sweep):
  - `adf_pval < 0.005`
  - `spread_vol > 0.045`
  - `half_life < 1000`
  - `kalman_q > 3.0e-06`
- Sort remaining pairs by `ols_net_pnl` descending.
- Take Top 50.
- Save `Top_50_Pure_MMDDYY.csv`.

**Step 6 — Output 4 CSVs**

Exactly 4 CSV files, named with `MMDDYY` suffix of the actual run date:

| File | Contents |
|---|---|
| `NSE-500_MMDDYY.csv` | 500 symbols fetched live from NSE |
| `le_70_coverage_MMDDYY.csv` | Symbols with < 70% data coverage (usually empty) |
| `Ranked_Profit_All_MMDDYY.csv` | All pairs, all fields, ranked by net PnL |
| `Top_50_Pure_MMDDYY.csv` | Top 50 pairs passing physics filter |

All files published to Kaggle Dataset: `utkarshpatelthefirst/pairs-stage1-outputs`.

---

### Component: GitHub Actions Trigger

#### [NEW] `.github/workflows/stage1-monthly.yml`
`LLM-WIKI/.github/workflows/stage1-monthly.yml`

- Triggers: **Cron `30 21 * * 0` UTC** (= 3:00 AM IST every Sunday, starting 2026-06-15)
- Action: calls `kaggle kernels push` to submit the pre-staged notebook.
- Requires GitHub Secrets: `KAGGLE_USERNAME`, `KAGGLE_KEY`.
- The `.github/` folder sits at the root of the `LLM-WIKI` git repo.

---

### Component: Methodology Document

#### [NEW] `pair-trading_stage-1_methodology.md`
`Soul/pairs-trading/Stage-1/pair-trading_stage-1_methodology.md`

Full in-depth blueprint: mathematical derivations, code structure explanations, reasoning behind each design decision, and the complete Walk-Forward physics proof.

---

## Open Questions

> [!IMPORTANT]
> **120 Trading Day Verification**: Should the system use the NSE Bhav Copy API (`https://www.nseindia.com/api/holiday-master?type=trading`) to enumerate exact trading holidays, or simply verify by checking that exactly 120 unique dates exist in the downloaded data? The latter is simpler and self-validating.

> [!NOTE]
> **GitHub Actions Secret Setup**: The `KAGGLE_USERNAME` and `KAGGLE_KEY` secrets need to be manually added to the LLM-WIKI GitHub repo under `Settings → Secrets → Actions` before the first run. This is a one-time manual step.

---

## Verification Plan

### Automated
1. Run `python3 pair_trading_stage1.py` locally — it should generate `pair_trading_stage1.ipynb` and `kernel-metadata.json` without error.
2. Push to Kaggle manually once (`kaggle kernels push`) and verify all 4 CSVs appear in the output dataset.
3. Check GitHub Actions workflow file syntax using `act` or GitHub's built-in validator.

### Manual
1. Confirm the NSE 500 list is dynamically fetched (varies if stocks are added/removed).
2. Confirm `Top_50_Pure_MMDDYY.csv` contains only pairs where `adf_pval < 0.005`, `spread_vol > 0.045`, `half_life < 1000`, `kalman_q > 3e-06`.
3. Confirm file naming uses actual run date, not hardcoded date.
