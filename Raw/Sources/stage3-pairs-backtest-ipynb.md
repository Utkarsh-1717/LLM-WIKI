---
Title: Stage 3 Pairs Backtest Notebook
Reference: stage3_pairs_backtest.ipynb
format: notebook
source_file: Raw/Sources/attachments/stage3_pairs_backtest.ipynb
Created: 2026-06-04
updated: 2026-06-04
Processed: true
tags:
  - source
sources:
  - Raw/Sources/attachments/stage3_pairs_backtest.ipynb
source_count: 1
---

## Section 1 — Notebook Purpose
Runs walk-forward 1-minute intraday mean reversion backtest using Kalman Z-Score.

## Section 2 — Stage Summary
Loads session-continuous prices. Uses Stage 2 Q/R matrices. Detects leader/lagger. Computes Z-score dynamically. Generates one-sided trades. Calculates Zerodha MIS fees.

## Section 3 — Strategy/Logic Extracted
Trades the Lagger when |Z| >= 2.0. Exits on Z-score mean reversion (Z crosses 0) based on entry sign. Halflife timeout and EOD timeout present.

## Section 4 — Results Found
Strategy has positive gross PnL but fails under 1-minute fee drag.

## Section 5 — Dependencies
sqlite3, numpy, pandas.

