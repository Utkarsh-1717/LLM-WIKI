---
title: pairs-stage1-pearson
type: entity
tags:
  - "entity"
  - "pairs-trading"
  - "quant"
topics: [pairs-trading, pearson-correlation, nse500, kaggle, dataset]
updated: 2026-06-02
---

# Pairs Stage 1 — Pearson Correlation Screening (NSE 500)

Output of Stage 1 of the pairs trading pipeline. Pairwise Pearson correlation of intraday log-returns computed across all NSE 500 equities using 1-minute OHLCV data from [[master-data-1min-dataset]].

## Output Files

| File | Rows | Size | Location |
|---|---|---|---|
| `pairs_all.csv` | 124,201 pairs | 5.8 MB | `Raw/Sources/attachments/pairs_all.csv` |
| `pairs_top500.csv` | 500 pairs | 23 KB | `Raw/Sources/attachments/pairs_top500.csv` |

Kaggle dataset: `utkarshpatelthefirst/pairs-stage1-pearson`
URL: https://www.kaggle.com/datasets/utkarshpatelthefirst/pairs-stage1-pearson

## Schema

| Column | Type | Description |
|---|---|---|
| `symbol_a` | str | First symbol (alphabetically earlier) |
| `symbol_b` | str | Second symbol |
| `pearson_rho` | float | Pearson ρ of 1-min intraday log-returns |
| `t_stat` | float | t-statistic under H₀: ρ = 0 |
| `p_value` | float | Two-tailed p-value (all < 0.05) |
| `n_obs` | int | Aligned observations used (39,220 bars) |
| `rank` | int | Rank by pearson_rho descending |

## Key Results

- **Total valid pairs**: 124,201 (out of 124,750 possible — 549 filtered as p≥0.05 or sparse)
- **Observations per pair**: 39,220 aligned intraday 1-min bars (~104 trading days)
- **Top pair**: PFC / RECLTD — ρ = 0.6702 (public sector lenders, highly expected)
- **#2**: INFY / TCS — ρ = 0.6596 (IT sector giants, classic pairs trade)
- **#3**: BDL / MAZDOCK — ρ = 0.6517 (defence sector)
- **Rank 500 ρ**: 0.3726 (cutoff for top-500 list)
- **ρ range (all pairs)**: −0.091 to +0.671

## Methodology

- **Return type**: Log-returns `ln(close_t / close_{t-1})` — no raw prices, no scaling
- **Session filter**: NSE market hours only (09:15–15:29 IST) — no overnight/weekend gaps
- **Session-open nulling**: 09:15 bar return (overnight gap) nulled before correlation
- **Alignment**: Two-pass — drop symbols <80% coverage, then inner-join survivors
- **Significance**: t-test p < 0.05 filter applied (with n=39,220 this catches essentially all pairs)
- **Compute**: Kaggle GPU T4 notebook, CPU fallback (pandas BLAS), ~9.5 min runtime

## Important Caveats

> ⚠️ High Pearson ρ is necessary but NOT sufficient for pairs trading. Correlated stocks may not be cointegrated — i.e., their spread may not be mean-reverting. **Stage 2 (cointegration testing) is mandatory before any live trading.**

- Negative correlations are included in `pairs_all.csv` (down to ρ = −0.09) but should be excluded for Stage 2 unless using a sum-spread construction
- Correlation is computed over the full 104-day period — it is not rolling and may not reflect current regime
- 39,220 obs ÷ 374 intraday returns/day = ~104.9 trading days of clean overlap

## Next Step — Stage 2

Pass `pairs_top500.csv` to **Stage 2: Cointegration Testing** (Engle-Granger or Johansen test on the price spread). Only pairs surviving both Stage 1 (ρ) and Stage 2 (cointegration p < 0.05) proceed to Stage 3 (spread modelling + z-score signals).

## Connections
- [[session-2026-06-02b]]
- [[pearson-correlation-screening]]
- [[pairs-trading-pipeline]]
- [[index]]
- [[master-data-1min-dataset]]
- [[fyers-historical-kaggle]]
- [[kaggle-compute]]
- [[higher-level-tick-pipeline]]
- [[fyers-api]]

- [[QC-decisions-pairs-trading]]
- [[pairs-stage1b-cointegration]]
- [[pairs-trading-strategy]]
- [[stage3-execution-engine]]