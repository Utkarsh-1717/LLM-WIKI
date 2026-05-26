---
tags:
  - "project"
topics: [quant, llm-wiki, setup, agy, skills]
status: complete
created: 2026-05-26
updated: 2026-05-26
sources:
  - Raw/Sources/quant-agent-setup.md
  - Raw/Sources/quant-wiki-multiformat.md
  - Raw/Sources/agents-rules.md
  - Raw/Sources/llms-core-setup.md
source_count: 4
aliases: [quant-system-setup, v1-setup, quant-v1]
---

# Quant Wiki System v1

Complete setup and initialization of the [[quant-agent-system]] v1.0.0 on top of the [[llm-wiki]]. Covers environment, skills, temp-skills, maintenance, and [[multi-format-ingest]].

## Status

**COMPLETE** — all acceptance criteria pass as of 2026-05-26

## Acceptance Criteria (All PASS)

- [x] `~/.quant_env` exists, chmod 600, all 8 credentials present
- [x] `~/.config/kaggle/kaggle.json` configured — [[kaggle-compute]]
- [x] Python packages: kaggle, pyotp, fyers_apiv3, requests
- [x] `AGENTS.md`: HARDWARE CONSTRAINTS, TOKEN EFFICIENCY RULES, TEMP-SKILL AUTO-CREATION RULE, API CREDENTIALS — see [[agent-rules]]
- [x] `.agents/skills/fyers-auth/SKILL.md` — 5-step TOTP auth — [[fyers-api]]
- [x] `.agents/skills/fyers-historical/SKILL.md` — chunking + SQLite
- [x] `.agents/skills/kaggle-notebook-run/SKILL.md` — LaTeX+code structure — [[kaggle-compute]]
- [x] `.agents/skills/kaggle-db-update/SKILL.md` — dataset versioning
- [x] `.agents/skills/multi-format-ingest/SKILL.md` — all 8 formats — [[multi-format-ingest]]
- [x] `_temp-skills/` with README.md
- [x] `scripts/temp_skill_manager.py` — stats, list, promote, kill
- [x] `scripts/wiki_tool.py` — all commands pass — [[wiki-tooling]]
- [x] `scripts/audit_public.py` — passes
- [x] `Raw/Sources/attachments/` with README.md
- [x] All maintenance gate checks pass

## Components

- **Fixed Skills** (5): fyers-auth, fyers-historical, kaggle-notebook-run, kaggle-db-update, multi-format-ingest
- **Temp-Skills System**: auto-grows with repeated patterns → [[agent-rules]]
- **Wiki Tooling**: doctor, build, lint, source-lint, source-scan, attachment-scan, audit → [[wiki-tooling]]

## Session Log

- [[session-2026-05-25]] — initial system build
- [[session-2026-05-26]] — Section A self-evaluation + full ingest

## Connections

- [[llm-wiki]] — foundation this project builds on
- [[quant-agent-system]] — system this project sets up
- [[agent-rules]] — rules enforced by this system
- [[wiki-tooling]] — maintenance tools verified in this project
- [[multi-format-ingest]] — attachment system set up in this project
- [[fyers-api]] — Fyers broker integration configured
- [[kaggle-compute]] — Kaggle integration configured
- [[raw-vs-wiki]] — separation principle this project follows
