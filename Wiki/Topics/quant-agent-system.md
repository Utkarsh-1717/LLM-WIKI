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
aliases: [quant-system, agy-quant, quant-agent]
---

# Quant Agent System

Self-improving quant research system built on top of [[llm-wiki]]. Android (Termux + agy) as thin client. Kaggle for all heavy compute. Designed for strategy development, backtesting, and data management.

## System Flow

```
User instruction
  ↓
agy reads AGENTS.md → [[agent-rules]]
  ↓
Loads matching skill only (token efficient)
  ↓
Fixed Skills: fyers-auth | fyers-historical | kaggle-notebook-run | kaggle-db-update | multi-format-ingest
Temp-Skills: auto-grows as patterns repeat → [[agent-rules]]
  ↓
LLM Wiki (permanent memory) → [[llm-wiki]]
  ↓
Kaggle (heavy compute) → [[kaggle-compute]]
```

## Data Source

[[fyers-api]] — provides live and historical market data via REST API.

## Skills

| Skill | Trigger | Purpose |
|---|---|---|
| fyers-auth | fyers data, authenticate fyers | 5-step TOTP auth via [[fyers-api]] |
| fyers-historical | OHLCV, historical data | Download 1-min data to SQLite |
| kaggle-notebook-run | backtest, kaggle run | Run strategy notebooks on [[kaggle-compute]] |
| kaggle-db-update | upload to Kaggle | Push SQLite to [[kaggle-compute]] dataset |
| multi-format-ingest | ingest file, process attachments | Convert any file → [[multi-format-ingest]] |

## Hardware Rules

See [[agent-rules]] for full constraints.

| Rule | Detail |
|---|---|
| Max local RAM | 2GB |
| Max local time | 30 min |
| Threading | Single-threaded only |
| Heavy compute | [[kaggle-compute]] only |
| API sleep | 0.5s between calls |

## Data Storage

- SQLite database: ohlcv_1min table (symbol, timestamp, open, high, low, close, volume)
- Kaggle dataset: quant-stock-db → [[kaggle-compute]]
- Local: ~/storage/shared/Quant/

## Maintenance

See [[wiki-tooling]] for all maintenance commands and the maintenance gate.

## Project Setup

- [[quant-wiki-system-v1]] — complete v1 setup record

## Parent System

- [[llm-wiki]] — knowledge management foundation

## Related

- [[agent-rules]] — hardware constraints and token efficiency rules
- [[wiki-tooling]] — maintenance commands
- [[multi-format-ingest]] — file ingestion
- [[raw-vs-wiki]] — data layer separation concept
- [[fyers-api]] — market data provider
- [[kaggle-compute]] — compute layer
