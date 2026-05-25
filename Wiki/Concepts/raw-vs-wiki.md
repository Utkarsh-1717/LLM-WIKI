---
tags:
  - "concept"
topics:
  - "llm-wiki"
status: evergreen
created: 2026-05-24
updated: "2026-05-25"
sources:
  - "Raw/Sources/demo.md"
source_count: 1
aliases:
  - "source-vs-wiki"
  - "two-layer"
---

# Raw Sources vs Wiki Notes

The LLM Wiki enforces a strict two-layer separation between raw captured material and compiled knowledge.

## The Two Layers

### Raw Sources (`Raw/Sources/`)
- Original captured material — untouched or summarized verbatim
- Chat exports, PDFs, notebooks, scripts, data files
- Converted to `.md` via the multi-format ingest skill
- **Rule**: Never edit the substance of a source note; it reflects the original

### Wiki Notes (`Wiki/`)
- Compiled, reusable knowledge written by the agent
- Short, linked, claim-focused
- **Rule**: Every wiki note must cite at least one source

## Why This Separation Matters

| Problem it solves | How |
|---|---|
| Context bloat | Agents search `catalog.jsonl` first — O(1) lookup |
| Citation drift | Every wiki note's `sources` field links back to raw evidence |
| Hallucination risk | Claims without a source cannot enter the Wiki |
| Reusability | Wiki notes are brief enough to paste directly into prompts |

## Workflow

```
Drop file into attachments/
  → ingest → Raw/Sources/[name].md (source note)
    → compile → Wiki/[section]/[note].md (wiki note)
      → build → Wiki/catalog.jsonl (search index)
```

## Source Note Required Frontmatter

```yaml
Title: "..."
Reference: "..."
Created: YYYY-MM-DD
Processed: true/false
tags:
  - source
```

## Connections

- [[llm-wiki]] — parent system
- [[multi-format-ingest]] — how non-markdown files become source notes
- [[first-ingest]] — first time this system was used
