---
title: timeseries-alignment
type: concept
tags:
  - "concept"
  - "quant"
  - "methodology"
topics: [quant, timeseries, data-engineering, alignment, methodology]
created: 2026-06-02
updated: 2026-06-02
status: evergreen
---

# Time Series Alignment (Multi-Symbol)

When working with multiple equity symbols, their timestamp series must be aligned before computing any cross-sectional statistic (correlation, covariance, spread). Misaligned series corrupt all downstream calculations.

## The Problem

NSE 500 equities have different:
- **Listing dates** — new IPOs have shorter history
- **Halted sessions** — individual stocks can be suspended
- **Data gaps** — API/exchange issues can leave missing bars

Pivoting these into a `(timestamp × symbol)` matrix without alignment produces NaN values that, if ignored, cause incorrect correlation estimates or silent errors.

## Two-Pass Smart Alignment (Recommended)

A strict inner-join on all symbols collapses the data window to the most restrictive symbol's coverage. If even one recent IPO or frequently-halted stock is in the universe, you can lose 60%+ of your data.

**Solution: Two-pass approach**

```python
n_total = len(price_matrix)

# Pass 1 — Drop sparse symbols (< 80% coverage)
# These are recent IPOs or halted stocks that would collapse the inner-join
coverage      = price_matrix.notna().sum() / n_total
sparse_syms   = coverage[coverage < 0.80].index.tolist()
price_matrix  = price_matrix.drop(columns=sparse_syms)
print(f"Dropped {len(sparse_syms)} sparse symbols: {sparse_syms[:5]}...")

# Pass 2 — Inner join on survivors
# All remaining timestamps where every survivor has data
price_matrix = price_matrix.dropna(how='any', axis=0)
print(f"Aligned: {price_matrix.shape[0]:,} bars × {price_matrix.shape[1]} symbols")
assert price_matrix.shape[0] >= 5000, "Too few bars — check data quality"
```

## Why 80% Coverage Threshold

- 80% means the symbol was present for at least 96 of 120 trading days
- This excludes recent IPOs (listed < 24 trading days ago) and structurally halted stocks
- It is conservative: a symbol at 80% coverage will still contribute ~35,776 bars to the aligned window (which the inner-join will then refine)
- Adjust down to 70% if universe retention is critical (trade-off: fewer bars retained)

## Data Observed (NSE 500, 2026-06-02)

| Step | Shape | Notes |
|---|---|---|
| Raw pivot | (44,250, 500) | All timestamps, all symbols |
| NaN count | 33,901 | Mostly from sparse/new listings |
| After Pass 1 (80%) | fewer symbols, same rows | Sparse symbols removed |
| After Pass 2 (inner-join) | (39,220, N) | ~104 trading days of clean overlap |

With strict inner-join (no Pass 1), we got only 17,566 bars (~47 days). Two-pass gave 39,220 bars (+123% more data).

## When to Use Pairwise Alignment Instead

For **Stage 2 (cointegration testing)**, pairwise alignment is often better: each pair uses its own maximum overlapping window. This adds computation but extracts more information per pair.

For **Stage 1 (correlation screening)** where all pairs share the same `n_obs`, global alignment is simpler and correct.

## Connections
- [[session-2026-06-02b]]
- [[kaggle-notebook-hardening]]
- [[index]]
- [[session-continuous-returns]]
- [[log-return-computation]]
- [[pearson-correlation-screening]]
- [[pairs-trading-pipeline]]
- [[master-data-1min-dataset]]
