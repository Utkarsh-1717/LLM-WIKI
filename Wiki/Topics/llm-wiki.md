---
tags:
  - "topic"
topics: [llm-wiki]
status: evergreen
created: 2026-05-24
updated: 2026-05-26
sources:
  - Raw/Sources/llms-core-setup.md
  - Raw/Sources/quant-agent-setup.md
  - Raw/Sources/quant-wiki-multiformat.md
  - Raw/Sources/agents-rules.md
  - Raw/Sources/demo.md
source_count: 5
aliases: [llm-wiki-system, wiki-system]
---

# LLM Wiki System

A self-improving knowledge management system for quantitative research. Runs on Android (Termux + agy). Separates raw source material from compiled, reusable knowledge.

## Architecture

```
Raw/Sources/             ← captured source material (.md summaries)
Raw/Sources/attachments/ ← original files (.py .pdf .ipynb .jpg .png .csv .json .xlsx)
Wiki/                    ← compiled, reusable knowledge linked to sources
Schema/                  ← rules and documentation
_templates/              ← note templates
.agents/skills/          ← fixed permanent skills (5 quant + 4 core)
_temp-skills/            ← auto-learned skills (grows over time)
scripts/                 ← maintenance tooling
```

## Core Principles

1. `Raw/Sources/` = source material only — never compiled notes
2. `Wiki/` = reusable knowledge — always linked back to Raw sources
3. Search `Wiki/catalog.jsonl` before opening Raw context
4. Run maintenance gate before every commit
5. Never invent citations

## The Two-Layer System

See [[raw-vs-wiki]] for the conceptual foundation.

## Ingest Workflow

Drop file → [[multi-format-ingest]] → Raw/Sources/[name].md → compile → Wiki/[section]/[note].md → build → catalog.jsonl

## Tooling

See [[wiki-tooling]] for all maintenance commands.

## Agent Rules

See [[agent-rules]] for AGENTS.md rules governing all agent behavior.

## Built On Top

- [[quant-agent-system]] — the quantitative trading layer

## Projects

- [[quant-wiki-system-v1]] — complete v1 setup
- [[termux-agy-setup]] — Termux + agy installation project
- [[starter-demo]] — first demo ingest

## Logs

- [[session-2026-05-26]] — Section A full execution
- [[session-2026-05-25]] — initial system build session
- [[first-ingest]] — first source ingested

## Related Concepts

- [[raw-vs-wiki]] — two-layer separation
- [[multi-format-ingest]] — attachment ingestion
- [[wiki-tooling]] — maintenance scripts
- [[agent-rules]] — governing rules


## Connections
- [[session-2026-05-26b]]
- [[index]]
