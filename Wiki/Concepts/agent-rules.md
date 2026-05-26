---
tags:
  - "concept"
topics: [llm-wiki, agents, rules]
status: evergreen
created: 2026-05-26
updated: 2026-05-26
sources:
  - Raw/Sources/agents-rules.md
  - Raw/Sources/quant-agent-setup.md
source_count: 2
aliases: [agent-constraints, AGENTS.md]
---

# Agent Rules

Master rules file (AGENTS.md) governing all agent behavior in the LLM Wiki system. Auto-read by agy on launch.

## Core Rules

1. `Raw/Sources/` = source material only — never compile directly
2. Write reusable knowledge only under `Wiki/`
3. Keep every compiled note linked to one or more Raw sources
4. Search `Wiki/catalog.jsonl` before opening broad Raw context
5. Run `build`, `lint`, `source checks` before commits
6. Never invent citations

## Hardware Constraints (Never Override)

- Max 2GB RAM per local process
- Max 30 minutes per local task
- No multiprocessing / no ThreadPoolExecutor / no GPU locally
- Heavy backtesting and data processing → Kaggle only
- Single-threaded, chunked, memory-efficient pandas only
- 0.5s sleep between all external API calls
- Warn if free storage below 5GB

## Token Efficiency

- Load only the skill matching the task trigger keyword
- Never load all skills simultaneously
- Never read entire Wiki on startup
- Credentials always from `~/.quant_env` — never ask user

## Temp-Skill Auto-Creation

When same 3-step sequence repeats → auto-create temp-skill in `_temp-skills/[skill-name]/SKILL.md`.
Fields: type=temp-skill, name, version, use_count, created, last_used, description, tags.
use_count increments on each use. Version bumped on revision. Never deleted — only by kill switch.

## API Credentials

All in `~/.quant_env` (chmod 600). Never committed. Sourced in `~/.bashrc`.
