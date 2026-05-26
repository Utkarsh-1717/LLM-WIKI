---
Title: "Multi-Format Ingest Extension"
Author: "Utkarsh"
Reference: "quant-wiki-multiformat-v1.0.0.md"
ContentType:
  - "markdown"
Created: 2026-05-26
Processed: true
tags:
  - "source"
---

# Multi-Format Ingest Extension

Extension guide (v1.0.0) to add multi-format source ingestion to the LLM Wiki. Builds on top of quant-agent-setup. Extends Raw/Sources/ to accept 8 additional file formats.

## Supported Formats

.py (python) | .pdf (pdf) | .ipynb (notebook) | .jpg (image) | .png (image) | .csv (csv) | .json (json) | .xlsx (spreadsheet)

## Workflow for Each File

1. File dropped into Raw/Sources/attachments/
2. Auto-scanned and format detected
3. Converted to .md summary in Raw/Sources/ with naming: [original-name]-[ext].md
4. Compiled into Wiki/ notes as normal
5. Tracked in source-manifest.jsonl with format field
6. Original file preserved in attachments/ always — never modified or deleted

## Setup Steps (00 → 03)

- Step 00: Create Raw/Sources/attachments/ with .gitkeep and README.md
- Step 01: Update wiki_tool.py — add format field to source-scan, add attachment-scan command, update manifest schema
- Step 02: Create .agents/skills/multi-format-ingest/SKILL.md
- Step 03: Final verification — full maintenance gate + push

## Source Note Frontmatter for Attachments

Required fields: title, format, source_file, created, updated, tags, sources, source_count

## attachment-scan Command

Scans Raw/Sources/attachments/ and reports files needing .md summaries.
Output: ✅ has summary | ❌ NEEDS SUMMARY | format | filepath

## Skill: multi-format-ingest

Trigger: ingest file, process attachments, scan attachments, ingest pdf/notebook/image/csv/json/py/xlsx
Rules: preserve original, named [stem]-[ext].md, required frontmatter, run lint after
Format-specific extraction rules for each of the 8 formats.
Batch mode: run attachment-scan then process all NEEDS SUMMARY files.
