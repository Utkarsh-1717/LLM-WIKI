---
Title: "Agent Rules and Constraints"
Author: "Utkarsh"
Reference: "AGENTS.md"
ContentType:
  - "markdown"
Created: 2026-05-26
Processed: true
tags:
  - "source"
---

# Agent Rules and Constraints

Current state of AGENTS.md — the master rules file for the LLM Wiki system. All agents automatically read this file on launch.

## Core Rules

- Treat Raw/Sources/ as source material only — never compile directly from there
- Write reusable knowledge only under Wiki/
- Keep every compiled note linked to one or more Raw sources
- Search Wiki/catalog.jsonl before opening broad Raw context
- Run build, lint, and source checks before commits
- Do not invent citations or create unsupported claims

## Hardware Constraints

Device: Realme GT 6T | Snapdragon 7+ Gen 3 | 8GB RAM | 128GB storage

- Never use multiprocessing or parallel processing locally
- Never exceed 2GB RAM in any local script
- Never run any local task over 30 minutes
- Never use GPU locally
- All heavy compute → Kaggle only
- Single-threaded, chunked, memory-efficient code for all local scripts
- Sleep 0.5s between all external API calls
- Check free storage before any download — warn if below 5GB

## Token Efficiency Rules

- Load only the skill whose trigger keyword matches the current task
- Never load all skills simultaneously
- Never read entire Wiki on startup
- Read only files directly relevant to current task
- Credentials always from ~/.quant_env — never ask user for them
- After every completed task: check if a pattern was repeated 3+ times → create temp-skill automatically

## Temp-Skill Auto-Creation Rule

1. Check if same sequence of 3+ steps executed before
2. If yes → create temp-skill in _temp-skills/[skill-name]/SKILL.md
3. Use standard frontmatter from _temp-skills/README.md
4. Set use_count to 1 on creation
5. On every subsequent use → increment use_count and update last_used
6. On revision → bump version, archive old to _temp-skills/archive/
7. Never delete temp-skills — only the kill switch can do that

## API Credentials

All credentials in ~/.quant_env — never committed, never hardcoded.
Credentials: FYERS_APP_ID, FYERS_SECRET_KEY, FYERS_TOTP_KEY, FYERS_USERNAME, FYERS_PIN, FYERS_REDIRECT, KAGGLE_USERNAME, KAGGLE_KEY
