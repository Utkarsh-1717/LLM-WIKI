---
title: Higher-Level Tick Pipeline
tags:
- concept
topics:
- quant
- tick-data
- pipeline
- cloud
- fyers
- real-time
- alpha
status: evergreen
created: 2026-05-30
updated: 2026-05-30
sources: []
source_count: 0
---

# Higher-Level Tick Pipeline

A proposed cloud-native system for collecting maximum-resolution tick data from NSE index futures, running automatically every trading day without any local device dependency.

## Motivation

The current [[qt-tick-collector]] (QT v2.0) runs on a local Android device, which introduces:
- Device/battery availability risk
- No holiday detection
- No cloud storage or redundancy

The goal is a fully autonomous, cloud-hosted pipeline that collects **maximum-resolution** tick-by-tick data for alpha research.

## Target Assets

| Asset | Symbol Type | Reason |
|---|---|---|
| Nifty 50 Futures (current month) | Index future | Highest liquidity, benchmark |
| Bank Nifty Futures (current month) | Index future | Sector proxy, high vol |

> **Note:** Both symbols must use the **current month expiry** contract, auto-rolling on expiry date (last Thursday of month). The same logic as in [[qt-tick-collector]] applies.

## Requirements

1. **Fully autonomous** — starts 5 minutes before trading window, ends at session close
2. **Holiday-aware** — detects NSE non-trading days and skips gracefully
3. **Auto-rolls expiry** — always fetches the active front-month futures contract
4. **Max data** — every field the Fyers API provides (tick-by-tick, not 1-min bars)
5. **Single output file** — one efficient, append-only file format (SQLite or Parquet) per symbol
6. **Cloud-only** — no local downloads; data stays and is updated on cloud storage
7. **Cloud compute** — runs on [[kaggle-compute]] or equivalent (no local device required)

## Architecture Options

### Option A — Kaggle Scheduled Notebook
- A Kaggle notebook running on a daily schedule
- Authenticates via [[fyers-api]] using credentials from Kaggle Secrets
- Streams ticks via Fyers WebSocket for the trading session
- Appends to a Parquet or SQLite file published to a Kaggle Dataset
- **Limitation:** Kaggle notebooks have a 9-hour GPU/12-hour CPU time limit — covers a full 6.25-hour trading session

### Option B — GitHub Actions + Cloud Storage
- GitHub Actions scheduled workflow (`cron: '9 3 * * 1-5'` → 09:00 IST on weekdays)
- Runs a Python container collecting ticks
- Pushes daily SQLite/Parquet to Google Drive or S3

### Option C — PythonAnywhere / Railway / Render (always-on)
- Persistent cloud process that wakes up at 09:09 IST daily
- Most reliable for long-running WebSocket connections

## Data Storage Design

### Recommended: Single Parquet File (append mode) per Symbol

```
tick_data/
  nifty_fut_ticks.parquet    ← appended daily
  banknifty_fut_ticks.parquet
```

**Schema** (same 28-field schema as QT v2.0 — see [[qt-tick-collector]]):
- `recv_ts`, `exch_ts`, `trade_ts` (milliseconds)
- `ltp`, `ltq`, `avg_trade_price`
- `tot_buy_qty`, `tot_sell_qty`, `vol_traded_today` (CVD-ready)
- `bid_price`, `bid_size`, `ask_price`, `ask_size`
- `open_price`, `high_price`, `low_price`, `prev_close_price`
- `ch`, `chp`, `open_interest`, `oi_day_high`, `oi_day_low`
- `upper_circuit`, `lower_circuit`, `week52_high`, `week52_low`
- `raw_json`

### Alternative: SQLite with WAL mode (cloud-compatible)
Same schema as QT v2.0, but with `journal_mode=WAL` for cloud Linux environments.

## Holiday Detection

NSE trading calendar options:
1. `pandas_market_calendars` — `XNSE` calendar (open-source, updated)
2. `nsetools` or `nsepy` — programmatic NSE holiday list
3. Fyers REST API: `/data/holidays` endpoint — authoritative source

## Expiry Roll Logic

Identical to [[qt-tick-collector]]:
- Last Thursday of current month = expiry date
- If `today >= expiry` → use next month's contract
- Symbol format: `NSE:NIFTY{YY}{MON}FUT` / `NSE:BANKNIFTY{YY}{MON}FUT`

## Stage 1 — Scale Invariant Data

> *Source: `Stage 1, Scale Invariant Data.md` (placeholder, content TBD by user)*

The "scale invariant" framing suggests that the raw tick data collected by this pipeline will be used as input to a **feature extraction layer** that produces signals invariant to absolute price level or volatility regime. This is typical of:
- Volume delta / CVD normalization
- Tick imbalance ratio
- Relative OI change (not absolute OI)
- Price change in ATR units

The tick schema (especially `tot_buy_qty`, `tot_sell_qty`, `open_interest`) is designed to feed these scale-invariant features directly.

## Connections
- [[session-2026-05-30]]
- [[pairs-stage1-pearson]]
- [[kaggle-github-scheduler]]
- [[index]]
- [[cloud-tick-pipeline]]

- [[qt-tick-collector]] — current local v2.0 implementation; cloud version inherits its schema and auth logic
- [[fyers-api]] — the data source; WebSocket SymbolUpdate feed used for all tick collection
- [[fyers-historical-kaggle]] — complementary skill for 1-min OHLCV (different resolution, same Fyers source)
- [[kaggle-compute]] — primary cloud compute target for this pipeline
- [[master-data-1min-dataset]] — 1-min dataset that coexists with this tick-level dataset
