---
tags:
  - "entity"
topics: [quant, kaggle, compute]
status: evergreen
created: 2026-05-26
updated: 2026-05-26
sources:
  - Raw/Sources/quant-agent-setup.md
  - Raw/Sources/agents-rules.md
source_count: 2
aliases: [kaggle, kaggle-gpu]
---

# Kaggle Compute

Kaggle is used as the heavy compute layer for the [[quant-agent-system]]. All backtesting, large data processing, and GPU workloads run here. Android/Termux is thin client only.

## Why Kaggle

| Constraint | Local (Android) | Kaggle |
|---|---|---|
| RAM | 2GB max | 32GB |
| CPU | Single-threaded | All CPUs |
| GPU | Not allowed | P100 / T4 |
| Runtime | 30 min max | 12 hours |
| Parallel | Never | Full multiprocessing |

## Credentials

```bash
source ~/.quant_env
# KAGGLE_USERNAME=utkarshpatelthefirst
# KAGGLE_KEY=...
```

Also requires `~/.config/kaggle/kaggle.json`.

## Dataset

- Dataset name: `quant-stock-db` (always)
- Contains SQLite database with `ohlcv_1min` table
- Versioned — each update: `"update-YYYY-MM-DD"`
- Uploaded via kaggle-db-update skill

## Notebook Structure (Mandatory)

Every notebook MUST follow the markdown+code cell pattern:

**CELL 1 — Markdown:**
```
## Stage N — [Stage Name]
**Methodology:** ...
**Input:** ...
**Output:** ...
**Core Logic:** ...
**Formula/Equation:** $$ ... $$
```

**CELL 2 — Code:** implementation only. No mixing stages.

## Execution Settings

| Setting | Value |
|---|---|
| GPU accelerator | Enabled |
| Internet | Enabled |
| Output path | `~/storage/shared/Quant/kaggle-outputs/[notebook-name]/` |

## Related

- [[quant-agent-system]] — orchestrates all Kaggle usage
- [[fyers-api]] — data source that feeds into Kaggle datasets
- [[agent-rules]] — hardware constraint: all heavy compute → Kaggle only
- [[wiki-tooling]] — kaggle-db-update records uploads in Wiki
- [[higher-level-tick-pipeline]] — planned cloud tick collector to run on this platform
- [[qt-tick-collector]] — current local tick collector; cloud upgrade targets Kaggle
- [[pairs-trading-pipeline]] — Stage 1 Pearson correlation screening ran here (2026-06-02)
- [[kaggle-notebook-hardening]] — production failure modes and fixes for notebooks
- [[pairs-stage1-pearson]] — first completed pairs screening output dataset

## Connections
- [[quant-wiki-system-v1]]
- [[session-2026-06-02b]]
- [[session-2026-05-30]]
- [[session-2026-05-26b]]
- [[session-2026-05-25]]
- [[master-data-1min-dataset]]
- [[kaggle-pulse-check]]
- [[fyers-historical-kaggle]]
- [[pearson-correlation-screening]]
- [[multi-format-ingest]]
- [[index]]
- [[fyers-1min-ingestion-pipeline]]
- [[cloud-tick-pipeline]]
- [[quant-agent-system]]
- [[fyers-api]]
- [[agent-rules]]
- [[wiki-tooling]]
- [[higher-level-tick-pipeline]]
- [[qt-tick-collector]]
- [[pairs-trading-pipeline]]
- [[kaggle-notebook-hardening]]
- [[pairs-stage1-pearson]]
- [[pairs-stage2-kalman-ou]]
