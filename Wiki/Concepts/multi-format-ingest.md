---
tags:
  - "concept"
topics: [llm-wiki, wiki, ingest, multiformat]
status: evergreen
created: 2026-05-26
updated: 2026-05-26
sources:
  - Raw/Sources/quant-wiki-multiformat.md
  - Raw/Sources/termux-guided-installation-setup-html.md
source_count: 2
aliases: [attachment-ingest, file-ingest, multiformat-ingest]
---

# Multi-Format Ingest

System for converting non-markdown files into wiki source notes. Part of the [[llm-wiki]] system. Files dropped into `Raw/Sources/attachments/` are auto-detected, summarized as `.md`, and compiled into [[llm-wiki]] notes.

## Supported Formats

| Extension | Format Name | What Is Extracted |
|---|---|---|
| `.py` | python | Functions, logic, data flow, dependencies |
| `.pdf` | pdf | Summary, concepts, methodology, findings |
| `.ipynb` | notebook | Stage summaries, strategy logic, results |
| `.jpg/.png` | image | Description, chart values, interpretation |
| `.csv` | csv | Schema, date range, data quality, use cases |
| `.json` | json | Structure, content summary, key fields |
| `.xlsx` | spreadsheet | Sheet summaries, key tables |

## Naming Convention

Output `.md` file: `[original-stem-lowercased-hyphenated]-[ext].md`

Examples:
- `strategy.pdf` → `Raw/Sources/strategy-pdf.md`
- `qt.py` → `Raw/Sources/qt-py.md`

## Required Frontmatter for Attachment Source Notes

```yaml
title: [descriptive title]
format: [python|pdf|notebook|image|csv|json|spreadsheet]
source_file: Raw/Sources/attachments/[filename]
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: [inferred topic tags]
sources: [Raw/Sources/attachments/filename]
source_count: 1
```

## Commands

- `python3 scripts/wiki_tool.py attachment-scan` — show all files needing summaries
- `python3 scripts/wiki_tool.py source-scan` — check coverage across all sources

## Skill Trigger

`multi-format-ingest` skill triggers on: `ingest file`, `process attachments`, `scan attachments`, `ingest pdf/notebook/image/csv/json/py/xlsx`

## Batch Mode

"Process all attachments" → `attachment-scan` → process all `NEEDS SUMMARY` files.

## Connections
- [[starter-demo]]
- [[quant-wiki-system-v1]]
- [[session-2026-05-26b]]
- [[session-2026-05-26]]
- [[index]]

- [[llm-wiki]] — parent system, enforces the Raw/Wiki separation
- [[raw-vs-wiki]] — conceptual foundation for why ingest creates source notes, not wiki notes
- [[wiki-tooling]] — `attachment-scan` command lives here
- [[quant-agent-system]] — uses multi-format ingest for strategy notebooks and data files
- [[kaggle-compute]] — `.ipynb` notebooks from Kaggle can be ingested this way
- [[first-ingest]] — first time this concept was used in this system
- [[session-2026-05-25]] — session where multi-format ingest was set up
