---
Title: Top 500 Pairs by Pearson Correlation
Reference: pairs_top500.csv
format: csv
source_file: Raw/Sources/attachments/pairs_top500.csv
Created: 2026-06-04
updated: 2026-06-04
Processed: true
tags:
  - source
sources:
  - Raw/Sources/attachments/pairs_top500.csv
source_count: 1
---

## Section 1 — Dataset Overview
Output of Stage 1 Pearson correlation. 500 rows.

## Section 2 — Schema
symbol_a, symbol_b, pearson_rho, stage1_rank.

## Section 3 — Date Range
N/A

## Section 4 — Data Quality Notes
Filtered for rho > 0.37 approx.

## Section 5 — Potential Uses
Input to Stage 2 EM optimization.

