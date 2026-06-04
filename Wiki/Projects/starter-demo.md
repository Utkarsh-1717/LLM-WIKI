---
tags:
  - "project"
topics: [llm-wiki, demo]
status: evergreen
created: 2026-05-24
updated: 2026-05-26
sources:
  - Raw/Sources/demo.md
source_count: 1
aliases: [demo-project, first-project]
---

# Starter Demo Project

Demonstration project used to validate the core [[llm-wiki]] structure by establishing the first source and compiling it into wiki notes.

## Purpose

Proves that the two-layer system works end-to-end:
1. Source in `Raw/Sources/demo.md` → [[raw-vs-wiki]]
2. Compiled into `Wiki/Topics/llm-wiki.md`, `Wiki/Concepts/raw-vs-wiki.md`
3. Indexed in `Wiki/catalog.jsonl` → [[wiki-tooling]]

## What This Established

- The Raw/Wiki separation works — [[raw-vs-wiki]]
- `wiki_tool.py lint` passes on the first real note — [[wiki-tooling]]
- The ingest workflow functions correctly — [[multi-format-ingest]]

## Session

- [[first-ingest]] — the log entry for this demo ingest

## Connections
- [[session-2026-05-26b]]
- [[index]]

- [[llm-wiki]] — the system this demo validates
- [[raw-vs-wiki]] — the concept demonstrated
- [[wiki-tooling]] — the tools verified by running against this note
- [[first-ingest]] — log entry for this ingest
- [[multi-format-ingest]] — ingest skill used to process source
