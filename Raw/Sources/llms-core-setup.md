---
Title: "LLM Wiki Core Setup Guide"
Author: "LLM Wiki"
Reference: "llms-core-setup.md"
ContentType:
  - "markdown"
Created: 2026-05-26
Processed: true
tags:
  - "source"
---

# LLM Wiki Core Setup Guide

A complete agent-facing guide for building a core LLM Wiki from an empty Obsidian vault or git repo. Covers the 6-step build order: empty vault → core structure → schema + agent rules → templates → deterministic tooling → first ingest → query and lint.

## Key Points

- Raw/Sources/ holds source material only — never compiled notes
- Wiki/ holds compiled, reusable knowledge linked to Raw sources
- Schema/ holds rules and documentation for how the wiki works
- wiki_tool.py provides: doctor, build, lint, source-scan, source-lint, source-delta, source-coverage, search-catalog, log
- audit_public.py checks for leaked secrets and obsidian plugin state
- AGENTS.md instructs future agents on rules, search-first workflow, and not inventing citations
- Maintenance gate: doctor → build → lint → source-lint → audit_public.py before every commit
- Catalog contract: one JSON per compiled note with path, title, tag, topics, sources, updated
- Source manifest contract: one JSON per Raw source with path, title, processed, covered_by, updated

## Folder Structure

Raw/Sources/ → Raw/Files/ → Wiki/Topics/ → Wiki/Concepts/ → Wiki/Entities/ → Wiki/Projects/ → Wiki/Logs/ → Schema/ → _templates/ → .agents/skills/ → scripts/ → tutorial/

## Ingest Workflow

1. Put cleaned Markdown in Raw/Sources/
2. search-catalog for related topics
3. Open most relevant compiled Wiki notes
4. Create or update focused notes in Wiki/
5. Add source links + keep source_count accurate
6. Run build, lint, source-scan --update --accept-covered, source-lint

## Templates Required

source-note, concept-note, topic-note, entity-note, project-note, log-note

## Allowed Wiki Tags

topic | concept | entity | project | log
