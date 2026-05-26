---
Title: "LLM Wiki Complete Reference Guide v1.0.0"
Author: "Utkarsh"
Reference: "quant-wiki-complete-guide-v1.0.0.md"
ContentType:
  - "markdown"
Created: 2026-05-26
Processed: true
tags:
  - "source"
---

# LLM Wiki Complete Reference Guide v1.0.0

The master reference document for the entire Quant Wiki system. Dual-purpose: Section A is the one-time self-evaluation + ingest + backup prompt for agy. Section B is the personal daily reference.

## Section A (Agent Prompt)

Three-part execution prompt:
- **Part 1**: Deep self-evaluation — reads all key files, runs 30+ checklist items, fixes all FAILs
- **Part 2**: Ingest 4 source documents into wiki with proper source notes and compiled wiki notes
- **Part 3**: Full 8-command maintenance gate + git commit + git push

## Section B (Daily Reference)

- System architecture diagram (You → agy → skill → Wiki → Kaggle)
- Folder structure explained
- Daily 5-step workflow: launch → health check → add knowledge → quant work → end-of-session backup
- Complete prompt cheat sheet for all task types
- Hardware rules table
- Self-improvement loop (auto temp-skill creation)
- Credentials location (`~/.quant_env`)
- Emergency commands
- File types quick reference
- Git reference

## Key Prompts Documented

| Task | Prompt |
|---|---|
| Full backup | `Run maintenance gate and push to origin main` |
| Ingest all | `Process all attachments` |
| Download data | `Download 1 year of 1-min OHLCV data for [SYMBOL]` |
| Run backtest | `Load [SYMBOL] 1-min data from Kaggle. Run [strategy]. Kaggle notebook.` |
