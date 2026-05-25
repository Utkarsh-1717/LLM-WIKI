---
tags:
  - "topic"
topics: []
status: evergreen
created: 2026-05-24
updated: "2026-05-25"
sources:
  - "Raw/Sources/demo.md"
source_count: 1
aliases:
  - "quant-wiki"
  - "wiki-system"
---

# LLM Wiki

An LLM Wiki is a two-layer knowledge system that strictly separates raw captured material from compiled, reusable knowledge notes.

## Core Principle

> Search the compiled Wiki first. Open Raw sources only when you need more evidence or context.

The system is optimized for AI agents operating under token constraints — keeping the working context small by letting agents hit `catalog.jsonl` first, then drilling into `Raw/Sources/` only for the specific note needed.

## Two Layers

| Layer | Location | Purpose |
|---|---|---|
| **Raw Sources** | `Raw/Sources/` | Original captured material — untouched |
| **Wiki Notes** | `Wiki/` | Compiled, reusable knowledge — agent-facing |

## Folder Structure

```
LLM-WIKI/
├── Raw/
│   └── Sources/
│       ├── *.md              ← source notes (markdown summaries)
│       └── attachments/      ← original files (.py, .pdf, .ipynb, .csv, etc.)
├── Wiki/
│   ├── Topics/               ← broad topic notes
│   ├── Concepts/             ← definitions and explanations
│   ├── Entities/             ← people, tools, services
│   ├── Projects/             ← project-specific notes
│   ├── Logs/                 ← session logs
│   └── catalog.jsonl         ← fast search index
├── Schema/
│   └── source-manifest.jsonl ← source coverage tracking
├── .agents/
│   └── skills/               ← agent skill definitions
├── scripts/
│   └── wiki_tool.py          ← maintenance CLI
└── AGENTS.md                 ← agent rules and constraints
```

## Maintenance Gate

Run before every commit:
```bash
python3 scripts/wiki_tool.py doctor
python3 scripts/wiki_tool.py build
python3 scripts/wiki_tool.py lint
python3 scripts/wiki_tool.py source-lint
python3 scripts/wiki_tool.py attachment-scan
python3 scripts/audit_public.py
```

## Multi-Format Attachment Support

Drop any of these file types into `Raw/Sources/attachments/`:
`.py` `.pdf` `.ipynb` `.jpg` `.png` `.csv` `.json` `.xlsx`

Tell the agent:
- Single file: `Ingest Raw/Sources/attachments/filename`
- All pending: `Process all attachments`
- Check pending: `python3 scripts/wiki_tool.py attachment-scan`

## Connections

- [[raw-vs-wiki]] — explains the two-layer separation in depth
- [[termux-agy-setup]] — the device environment running this system
- [[multi-format-ingest]] — attachment ingestion skill
- [[session-2026-05-25]] — session that established the full system
