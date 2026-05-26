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
aliases: [agent-constraints, AGENTS.md, agents-md]
---

# Agent Rules

Master rules file (`AGENTS.md`) governing all agent behavior in the [[llm-wiki]] system. Auto-read by agy on launch.

## Core Rules

1. `Raw/Sources/` = source material only — never compile directly
2. Write reusable knowledge only under `Wiki/`
3. Keep every compiled note linked to one or more Raw sources
4. Search `Wiki/catalog.jsonl` before opening broad Raw context
5. Run `build`, `lint`, `source checks` before commits — see [[wiki-tooling]]
6. Never invent citations

## Hardware Constraints (Never Override)

Applies to all [[quant-agent-system]] local operations:

- Max 2GB RAM per local process
- Max 30 minutes per local task
- No multiprocessing / no ThreadPoolExecutor / no GPU locally
- Heavy backtesting and data processing → [[kaggle-compute]] only
- Single-threaded, chunked, memory-efficient pandas only
- 0.5s sleep between all external API calls (including [[fyers-api]])
- Warn if free storage below 5GB

## Token Efficiency

- Load only the skill matching the task trigger keyword
- Never load all skills simultaneously
- Never read entire Wiki on startup
- Credentials always from `~/.quant_env` — never ask user

## Temp-Skill Auto-Creation

When same 3-step sequence repeats → auto-create temp-skill in `_temp-skills/[skill-name]/SKILL.md`.

Fields required:
```yaml
type: temp-skill
name: [kebab-case-name]
version: 1
use_count: 1
created: YYYY-MM-DD
last_used: YYYY-MM-DD
description: [one line]
tags: [temp-skill]
```

`use_count` increments on each use. Version bumped on revision. Never deleted — only by kill switch.

## API Credentials

All in `~/.quant_env` (chmod 600). Never committed. Sourced in `~/.bashrc`.

Credentials:
- `FYERS_APP_ID`, `FYERS_SECRET_KEY`, `FYERS_TOTP_KEY`, `FYERS_USERNAME`, `FYERS_PIN`, `FYERS_REDIRECT` → [[fyers-api]]
- `KAGGLE_USERNAME`, `KAGGLE_KEY` → [[kaggle-compute]]

## Connections

- [[llm-wiki]] — system these rules govern
- [[quant-agent-system]] — quantitative layer that extends these rules
- [[wiki-tooling]] — the tools that enforce these rules
- [[fyers-api]] — external API subject to rate limit rule
- [[kaggle-compute]] — heavy compute layer (never local)
- [[raw-vs-wiki]] — core data separation rule
