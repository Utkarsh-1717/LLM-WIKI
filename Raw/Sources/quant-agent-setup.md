---
Title: "Quant Agent System Setup"
Author: "Utkarsh"
Reference: "quant-agent-setup-v1.0.0.md"
ContentType:
  - "markdown"
Created: 2026-05-26
Processed: true
tags:
  - "source"
---

# Quant Agent System Setup

Master setup guide (v1.0.0) for building a self-improving quant agentic system on top of the LLM Wiki. Runs on Android (Termux + agy). Heavy compute on Kaggle. Android is thin client only.

## Hardware Constraints

- Device: Realme GT 6T | Snapdragon 7+ Gen 3 | 8GB RAM | 128GB storage
- Max 2GB RAM per local process
- No multiprocessing, no ThreadPoolExecutor, no GPU locally
- No local task over 30 minutes
- ALL heavy compute → Kaggle only
- Single-threaded, chunked, memory-efficient code locally
- Sleep 0.5s between all API calls
- Alert if free storage below 5GB

## Setup Steps (00 → 05)

- Step 00: Environment bootstrap — ~/.quant_env with 8 credentials, pip packages, kaggle CLI
- Step 01: Update AGENTS.md — append HARDWARE CONSTRAINTS + TOKEN EFFICIENCY RULES
- Step 02: Core fixed skills — fyers-auth, fyers-historical, kaggle-notebook-run, kaggle-db-update
- Step 03: Temp-skills system — _temp-skills/README.md + temp_skill_manager.py + AGENTS.md auto-creation rule
- Step 04: Full maintenance gate — all checks must pass
- Step 05: Final push — git add -A, commit, push origin main

## Fixed Skills

- fyers-auth: 5-step TOTP auth flow from ~/.quant_env
- fyers-historical: chunked 100-day requests, SQLite ohlcv_1min, 0.5s sleep, single-threaded
- kaggle-notebook-run: mandatory markdown+code cell structure, LaTeX formulas, GPU on Kaggle
- kaggle-db-update: dataset named quant-stock-db, version note with date, record in wiki

## Temp-Skills System

Auto-created when same 3-step sequence repeats. Tracked in _temp-skills/. use_count incremented on each use. Promoted to .agents/skills/ via temp_skill_manager.py promote. Kill switch requires CONFIRM.

## Credentials Location

~/.quant_env — chmod 600 — sourced in ~/.bashrc — never committed

## Token Efficiency Rules

Load only matching skill. Never read entire wiki on startup. Credentials always from ~/.quant_env. Auto-create temp-skill after 3+ repeated pattern.
