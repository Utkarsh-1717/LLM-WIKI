---
tags:
  - "topic"
topics: []
status: evergreen
created: 2026-05-26
updated: 2026-05-26
sources:
  - Raw/Sources/llms-core-setup.md
  - Raw/Sources/quant-agent-setup.md
  - Raw/Sources/quant-wiki-multiformat.md
  - Raw/Sources/agents-rules.md
source_count: 4
aliases: [llm-wiki-system]
---

# LLM Wiki System

A self-improving knowledge management system for quantitative research. Runs on Android (Termux + agy). Separates raw source material from compiled, reusable knowledge.

## Architecture

```
Raw/Sources/        ← captured source material (.md summaries)
Raw/Sources/attachments/ ← original files (.py .pdf .ipynb .jpg .png .csv .json .xlsx)
Wiki/               ← compiled, reusable knowledge linked to sources
Schema/             ← rules and documentation
_templates/         ← note templates
.agents/skills/     ← fixed permanent skills (5 quant + 4 core)
_temp-skills/       ← auto-learned skills (grows over time)
scripts/            ← maintenance tooling
```

## Core Principles

1. Raw/Sources/ = source material only — never compiled notes
2. Wiki/ = reusable knowledge — always linked back to Raw sources
3. Search catalog.jsonl before opening Raw context
4. Run maintenance gate before every commit
5. Never invent citations

## Related Topics

- [[quant-agent-system]] — the quant layer built on top
- [[multi-format-ingest]] — how non-markdown sources are ingested
- [[agent-rules]] — AGENTS.md rules governing all agent behavior
