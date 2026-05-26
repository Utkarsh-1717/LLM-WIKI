---
tags:
  - "concept"
topics: [llm-wiki, wiki, ingest, multiformat]
status: evergreen
created: 2026-05-26
updated: 2026-05-26
sources:
  - Raw/Sources/quant-wiki-multiformat.md
source_count: 1
aliases: [attachment-ingest, file-ingest]
---

# Multi-Format Ingest

System for converting non-markdown files into wiki source notes. Files dropped into `Raw/Sources/attachments/` are auto-detected, summarized in `.md`, and compiled into Wiki notes.

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

Output .md file: `[original-stem-lowercased-hyphenated]-[ext].md`  
Example: `strategy.pdf` → `Raw/Sources/strategy-pdf.md`  
Example: `qt.py` → `Raw/Sources/qt-py.md`

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
- Batch: "Process all attachments" → attachment-scan then process all NEEDS SUMMARY files

## Skill

`multi-format-ingest` — trigger: ingest file, process attachments, scan attachments

## Related

- [[raw-vs-wiki]] — how raw and wiki layers relate
- [[llm-wiki]] — the parent system
