---
title: QT — Quantitative Tick Collector
tags:
  - entity
topics: [quant, tick-data, fyers, sqlite, android, real-time]
status: evergreen
created: 2026-05-30
updated: 2026-05-30
sources:
  - Raw/Sources/qt-py.md
source_count: 1
---

# QT — Quantitative Tick Collector

`qt.py` is a production-grade automated intraday tick data collector that:
- subscribes to the [[fyers-api]] WebSocket `SymbolUpdate` feed
- captures every tick (28 fields per row including CVD-ready buy/sell volumes, OI, bid/ask)
- stores data into per-symbol SQLite databases on Android local storage (`/sdcard/QT/`)
- auto-resolves the correct NSE futures expiry contract each day
- runs fully autonomously from 09:14 to session end

## Current Version

**QT v2.0** — supports 4 symbols simultaneously:
1. `NSE:NIFTY{YY}{MON}FUT` — Nifty 50 Futures (auto-rolling)
2. `NSE:BANKNIFTY{YY}{MON}FUT` — Bank Nifty Futures (auto-rolling)
3. `NSE:HDFCBANK-EQ` — LargeCap (static, configurable)
4. `NSE:PERSISTENT-EQ` — MidCap (static, configurable)

## Key Design Decisions

| Decision | Choice | Reason |
|---|---|---|
| Storage format | SQLite per symbol | Single file, no corruption, queryable |
| Journal mode | `DELETE` (not WAL) | Android fs compatibility |
| Commit strategy | Every 200 ticks OR 15s | Balance data safety vs. write load |
| OI field fallback | Tries 4 field names | Fyers inconsistent OI naming |
| Auth | 5-step TOTP flow | Standard Fyers auth (same as [[fyers-auth]] skill) |

## Tick Schema (28 fields + raw_json)

| Field Group | Fields |
|---|---|
| Timestamps (ms) | `recv_ts`, `exch_ts`, `trade_ts` |
| Price & trade | `ltp`, `ltq`, `avg_trade_price` |
| Volume (CVD) | `tot_buy_qty`, `tot_sell_qty`, `vol_traded_today` |
| Bid/Ask (L1) | `bid_price`, `bid_size`, `ask_price`, `ask_size` |
| OHLC | `open_price`, `high_price`, `low_price`, `prev_close_price` |
| Change | `ch`, `chp` |
| Open Interest | `open_interest`, `oi_day_high`, `oi_day_low` |
| Circuit/52w | `upper_circuit`, `lower_circuit`, `week52_high`, `week52_low` |
| Raw payload | `raw_json` |

## Limitations (v2.0)

- Runs locally on Android — bound by device availability and battery
- No cloud upload / no auto-publish
- No holiday/non-trading-day detection (always starts if device is on)
- Data stays in `/sdcard/QT/` — manual retrieval needed
- Single machine: no redundancy or failover

These limitations are addressed by the planned [[higher-level-tick-pipeline]] cloud-native upgrade.

## Connections
- [[session-2026-06-01]]
- [[session-2026-05-30]]
- [[kaggle-github-scheduler]]
- [[index]]
- [[cloud-tick-pipeline]]

- [[fyers-api]] — uses Fyers REST auth (5-step TOTP, same flow documented in [[fyers-api]]) + WebSocket for tick streaming
- [[higher-level-tick-pipeline]] — planned cloud-native successor that runs on Kaggle/cloud, auto-detects holidays, and publishes to cloud storage
- [[fyers-historical-kaggle]] — related skill for 1-min OHLCV bulk fetch (complementary data layer)
- [[kaggle-compute]] — target cloud compute for the pipeline upgrade
- [[master-data-1min-dataset]] — 1-min OHLCV dataset; tick data from this collector is the higher-resolution complement
