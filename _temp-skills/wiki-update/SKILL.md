---
type: temp-skill
name: wiki-update
version: 1
use_count: 5
created: 2026-06-01
last_used: 2026-06-04
description: Routine procedure for ingesting new notes into the LLM-WIKI, running validation checks, and committing to git.
tags: [temp-skill, wiki, maintenance]
---

# Wiki Update & Ingestion Skill

## Trigger
Use this skill whenever you need to update the LLM-WIKI with new knowledge, session logs, or entity notes.

## Workflow Sequence

1. **Write the Markdown Note(s)**
   - Create or edit the markdown file in the appropriate directory (`Wiki/Concepts/`, `Wiki/Entities/`, `Wiki/Logs/`, etc.).
   - **Crucial step**: Ensure the YAML frontmatter is completely filled out:
     - `title`
     - `tags` (e.g. `[concept]`, `[entity]`, `[log]`)
     - `topics`
     - `status`
     - `created` and `updated` dates (YYYY-MM-DD)
     - `source_count`
     - `sources` (must link to valid `.md` files in `Raw/Sources/`)
   - Ensure you include a `## Connections` section at the bottom linking to related notes using `[[wikilinks]]`.

2. **Update the Catalog**
   - Append the new note's metadata as a JSON object to `Wiki/catalog.jsonl`.
   - Format: `{"path": "Wiki/...", "title": "...", "tag": "...", "topics": [...], "sources": [...], "updated": "YYYY-MM-DD"}`

3. **Run Validation Checks**
   - Run the strict validation suite: 
     ```bash
     python3 scripts/wiki_tool.py lint && python3 scripts/wiki_tool.py build && python3 scripts/wiki_tool.py doctor
     ```
   - Resolve any errors (e.g. missing frontmatter, broken source links) before proceeding.

4. **Git Commit & Push**
   - Once all checks pass, commit the changes to the LLM-WIKI repo:
     ```bash
     git add .
     git commit -m "docs: ingest [brief description of what was ingested]"
     git push
     ```

## Usage Rules
- **Bidirectional Links:** If a new entity or concept is mentioned frequently, create a dedicated note and link back to it.
- **Failures:** If `lint` fails, do not bypass it. Read the error message, correct the markdown frontmatter or `catalog.jsonl` entry, and run it again.
