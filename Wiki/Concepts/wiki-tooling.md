---
tags:
  - "concept"
topics: [llm-wiki, wiki, tooling]
status: evergreen
created: 2026-05-26
updated: 2026-05-26
sources:
  - Raw/Sources/llms-core-setup.md
  - Raw/Sources/quant-agent-setup.md
source_count: 2
aliases: [wiki-tool, maintenance-gate]
---

# Wiki Tooling

Deterministic maintenance tooling for the LLM Wiki. All scripts use Python standard library only. Run before every commit.

## wiki_tool.py Commands

| Command | Purpose |
|---|---|
| `doctor` | Non-mutating health check — folders, Python version, note counts |
| `build` | Generate catalog.jsonl, Wiki/index.md, per-folder index files |
| `lint` | Validate Wiki note frontmatter, allowed tags, source links, source_count |
| `source-scan` | List Raw sources, optionally update source-manifest.jsonl |
| `source-scan --update --accept-covered` | Update manifest after Wiki notes cover sources |
| `source-lint` | Validate source frontmatter and coverage state |
| `source-delta` | Show Raw sources not in manifest |
| `source-coverage` | Show which sources are covered by Wiki notes |
| `attachment-scan` | Show files in attachments/ needing .md summaries |
| `search-catalog --query "text"` | Search compiled Wiki through catalog |
| `log --title T --details D` | Append entry to Wiki/log.md |

## audit_public.py

Fails if: private keys (id_rsa, .pem, "secret"), obsidian plugin/cache state detected in repo.

## temp_skill_manager.py Commands

| Command | Purpose |
|---|---|
| `stats` | Show total count + top 5 by usage |
| `list` | List all temp-skills ranked by use_count |
| `promote [name]` | Copy to .agents/skills/, remove from _temp-skills/ |
| `kill` | Delete all temp-skills (requires CONFIRM input) |

## Maintenance Gate (Full)

Run in this order before every commit:
1. `python3 scripts/wiki_tool.py doctor`
2. `python3 scripts/wiki_tool.py build`
3. `python3 scripts/wiki_tool.py lint`
4. `python3 scripts/wiki_tool.py source-lint`
5. `python3 scripts/wiki_tool.py source-scan`
6. `python3 scripts/wiki_tool.py attachment-scan`
7. `python3 scripts/audit_public.py`
8. `python3 scripts/temp_skill_manager.py stats`

## Related

- [[llm-wiki]] — parent system
- [[agent-rules]] — rules that govern when to run these tools
