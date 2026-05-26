---
tags:
  - "topic"
topics: [quant, llm-wiki]
status: evergreen
created: 2026-05-26
updated: 2026-05-26
sources:
  - Raw/Sources/quant-agent-setup.md
  - Raw/Sources/agents-rules.md
source_count: 2
aliases: [quant-system, agy-quant]
---

# Quant Agent System

Self-improving quant research system built on top of LLM Wiki. Android (Termux + agy) as thin client. Kaggle for all heavy compute. Designed for strategy development, backtesting, and data management.

## System Flow

```
User instruction
  ↓
agy reads AGENTS.md automatically
  ↓
Loads matching skill only (token efficient)
  ↓
Fixed Skills: fyers-auth | fyers-historical | kaggle-notebook-run | kaggle-db-update | multi-format-ingest
Temp-Skills: auto-grows as patterns repeat
  ↓
LLM Wiki (permanent memory)
  ↓
Kaggle (heavy compute — backtesting, data processing)
```

## Skills

| Skill | Trigger | Purpose |
|---|---|---|
| fyers-auth | fyers data, authenticate fyers | 5-step TOTP auth |
| fyers-historical | OHLCV, historical data | Download 1-min data to SQLite |
| kaggle-notebook-run | backtest, kaggle run | Run strategy notebooks |
| kaggle-db-update | upload to Kaggle | Push SQLite to Kaggle dataset |
| multi-format-ingest | ingest file, process attachments | Convert any file to wiki source |

## Hardware Rules

| Rule | Detail |
|---|---|
| Max local RAM | 2GB |
| Max local time | 30 min |
| Threading | Single-threaded only |
| Heavy compute | Kaggle only |
| API sleep | 0.5s between calls |

## Data Storage

- SQLite database: ohlcv_1min table (symbol, timestamp, open, high, low, close, volume)
- Kaggle dataset: quant-stock-db
- Local: ~/storage/shared/Quant/

## Related

- [[llm-wiki]] — foundation system
- [[fyers-api]] — data source
- [[kaggle-compute]] — compute layer
