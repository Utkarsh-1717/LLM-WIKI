---
title: pairs-trading-pipeline
type: concept
tags:
  - "concept"
  - "pairs-trading"
  - "quant"
topics: [quant, pairs-trading, strategy, pipeline, nse500]
created: 2026-06-02
updated: 2026-06-04
status: active
sources:
  - Raw/Sources/nse-futures-tick-collector-ipynb.md
  - Raw/Sources/pairs-all-csv.md
  - Raw/Sources/pairs-stage2-kalman-ou-csv.md
  - Raw/Sources/pairs-stage3-backtest-csv.md
  - Raw/Sources/pairs-top500-csv.md
  - Raw/Sources/skipped-pairs-stage2-csv.md
  - Raw/Sources/skipped-stage3-csv.md
  - Raw/Sources/stage2-dataset-metadata-json.md
  - Raw/Sources/stage3-pairs-backtest-ipynb.md
source_count: 9
---

# Pairs Trading Pipeline

A multi-stage quantitative pipeline for identifying, validating, and trading mean-reverting equity pairs on the NSE 500 universe. Built on top of [[master-data-1min-dataset]] (1-minute OHLCV, 120 trading days).

## Pipeline Architecture

```
Stage 1 — Pearson Correlation Screening   ← COMPLETE ✅
  Input : master-data-1min-dataset (500 symbols × ~45k 1-min bars)
  Method: Pairwise Pearson ρ on session-continuous log-returns
  Output: pairs_all.csv (124,201 pairs) + pairs_top500.csv (500 pairs)
  Wiki  : [[pairs-stage1-pearson]]

Stage 2 — Cointegration Testing           ← COMPLETE ✅
  Input : pairs_top500.csv (500 candidate pairs)
  Method: Kalman Filter (EM algorithm) for state space parameters. Half-life computed via Ornstein-Uhlenbeck (OU) process.
  Output: pairs_stage2_kalman_ou.csv (41 tradeable pairs with HL 5-120 mins)
  Wiki  : [[pairs-stage2-kalman-ou]]

Stage 3 — Intraday Backtesting            ← COMPLETE ✅
  Input : pairs_stage2_kalman_ou.csv (41 filtered pairs)
  Method: Online Kalman Filter + 10-day rolling Z-score. Strict session-continuous filtering. Zerodha MIS fee model.
  Output: pairs_stage3_backtest.csv
  Result: Gross PnL was mathematically positive across the board, proving the Kalman hypothesis works. However, the 1-minute EM fit optimized for the bid-ask bounce (microstructure noise), leading to extremely short half-lives (~8.5 mins). Under a ₹10,000 base capital, fixed broker fees devastated the net PnL. Simulation proved that leveraging the capital (e.g. ₹5,00,000 via 5x MIS) effectively dilutes the fixed fee drag, flipping the strategy to net profitable.
  Wiki  : [[fee-drag-and-microstructure-noise]]

## Key Design Principles

- **Intraday only**: All analysis uses session-continuous log-returns (no overnight gap contamination). See [[session-continuous-returns]].
- **Two conditions for a tradeable pair**: High Pearson ρ AND cointegration (spread stationary). Correlation alone is not sufficient.
- **Universe**: NSE 500 equities. ~124,750 possible pairs → 500 top-ρ candidates → cointegrated survivors.
- **Compute**: All heavy stages run on [[kaggle-compute]]. Data source is [[master-data-1min-dataset]].
- **Awareness of Fee Drag**: Extremely high frequency intraday strategies require massive capital scaling to survive fixed broker fee structures. See [[fee-drag-and-microstructure-noise]].

## Stage 1 Results (Completed 2026-06-02)

| Metric | Value |
|---|---|
| Valid pairs | 124,201 of 124,750 |
| n_obs per pair | 39,220 intraday 1-min bars |
| Top pair | PFC / RECLTD (ρ = 0.6702) |
| #2 | INFY / TCS (ρ = 0.6596) |
| Top-500 cutoff | ρ = 0.3726 |

## Related Concepts

- [[session-continuous-returns]] — how returns are computed (removes overnight gaps)
- [[log-return-computation]] — why log-returns, not prices
- [[pearson-correlation-screening]] — the Stage 1 method in detail
- [[timeseries-alignment]] — how symbols are aligned before correlation

## Connections
- [[quant-agent-system]]
- [[session-2026-06-02b]]
- [[kaggle-pulse-check]]
- [[index]]
- [[pairs-stage1-pearson]]
- [[master-data-1min-dataset]]
- [[session-continuous-returns]]
- [[log-return-computation]]
- [[pearson-correlation-screening]]
- [[timeseries-alignment]]
- [[kaggle-compute]]
- [[kaggle-notebook-hardening]]
- [[pairs-stage2-kalman-ou]]

- [[pairs-trading-stop-loss-dynamics]]