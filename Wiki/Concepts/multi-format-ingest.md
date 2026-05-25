---
tags:
  - "concept"
topics:
  - "llm-wiki"
  - "multi-format"
status: evergreen
created: "2026-05-25"
updated: "2026-05-25"
sources:
  - "Raw/Sources/termux-guided-installation-setup-html.md"
source_count: 1
aliases:
  - "attachment-ingest"
  - "file-ingest"
---

# Multi-Format Ingest

The multi-format ingest system allows any supported file dropped into `Raw/Sources/attachments/` to be automatically converted into a wiki source note, then compiled into the Wiki like any other source.

## Supported Formats

| Extension | Format | Output md filename pattern |
|---|---|---|
| `.py` | python | `[name]-py.md` |
| `.pdf` | pdf | `[name]-pdf.md` |
| `.ipynb` | notebook | `[name]-ipynb.md` |
| `.jpg` | image | `[name]-jpg.md` |
| `.png` | image | `[name]-png.md` |
| `.csv` | csv | `[name]-csv.md` |
| `.json` | json | `[name]-json.md` |
| `.xlsx` | spreadsheet | `[name]-xlsx.md` |

Original files are **never** modified or deleted from `attachments/`.

## Naming Rule

Output `.md` file: `[original-stem-lowercased-hyphenated]-[ext].md`

Examples:
- `qt.py` → `Raw/Sources/qt-py.md`
- `strategy.pdf` → `Raw/Sources/strategy-pdf.md`
- `my_data.csv` → `Raw/Sources/my-data-csv.md`

## Required Frontmatter (every generated file)

```yaml
---
title: [descriptive title]
format: [python|pdf|notebook|image|csv|json|spreadsheet]
source_file: Raw/Sources/attachments/[filename]
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: [inferred topic tags]
sources: [Raw/Sources/attachments/filename]
source_count: 1
---
```

## Workflow

### Single File
```
Ingest Raw/Sources/attachments/strategy.pdf
```

### Batch
```
Process all attachments
```
Or check pending first:
```bash
python3 scripts/wiki_tool.py attachment-scan
```

## Scanning

`attachment-scan` reports:
- ❌ `NEEDS SUMMARY` — no corresponding `.md` exists yet
- ✅ `has summary` — `.md` already created

## Connections

- [[llm-wiki]] — parent system
- [[raw-vs-wiki]] — explains source vs wiki separation
- [[termux-agy-setup]] — device this system runs on
