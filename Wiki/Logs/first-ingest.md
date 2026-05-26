---
tags:
  - "log"
topics: [llm-wiki, demo, ingest]
status: done
created: 2026-05-24
updated: 2026-05-26
sources:
  - Raw/Sources/demo.md
source_count: 1
aliases: [first-ingest-log]
---

# First Ingest Log

The first source note, `Raw/Sources/demo.md` ("LLM Wiki Starter Demo Source"), was ingested into the system to validate the core [[llm-wiki]] structure.

## What Happened

1. Created `Raw/Sources/demo.md` — a minimal source note following [[raw-vs-wiki]] rules
2. Compiled it into:
   - `Wiki/Topics/llm-wiki.md` — topic overview
   - `Wiki/Concepts/raw-vs-wiki.md` — the two-layer concept
   - `Wiki/Projects/starter-demo.md` — this demo project
3. Ran [[wiki-tooling]]: `build → lint → source-lint` — all passed
4. Verified `catalog.jsonl` now contains the compiled notes

## Why This Matters

Proved the full pipeline works end-to-end before any real data was added.

## Connections

- [[llm-wiki]] — system this validated
- [[raw-vs-wiki]] — the concept first demonstrated here
- [[starter-demo]] — the project containing this ingest
- [[wiki-tooling]] — the tools verified in this ingest
- [[multi-format-ingest]] — the skill used
- [[session-2026-05-25]] — session where more work followed this
