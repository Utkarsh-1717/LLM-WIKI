---
name: soul-production-compiler
trigger: [finalize to soul, productionize, create soul artifacts, final stage, production grade]
description: Consolidates verified math, logical rules, QC reports, and corrected Python/Notebook code into the final 'Soul/' production directory using the multi-agent teamwork interface.
version: 1.0.0
last_updated: 2026-06-04
---

# Soul Production Compiler Skill

## Purpose
The `Soul/` directory is the final Source of Truth for production deployment. This skill orchestrates the compilation of all drafting phases (Plans, QC Audits, Rebuttals) into finalized, production-ready assets. No flawed or experimental code belongs here.

## Required Target Architecture
The agent must ensure the `Soul/` directory contains exactly these subfolders (create them if missing):
- `/storage/emulated/0/Quant/LLM-WIKI/Soul/Methodology/`: Stores in-depth markdown files explaining the core logic, verified math formulas, and accepted design choices (e.g., `QC_Rebuttals_and_Context.md`).
- `/storage/emulated/0/Quant/LLM-WIKI/Soul/Code/`: Stores the absolute final, production-ready Kaggle notebooks (`.ipynb`) and Python scripts (`.py`).
- `/storage/emulated/0/Quant/LLM-WIKI/Soul/Conclusions/`: Stores rigorous backtest results, limitations, and forward-looking action items.

## Workflow Execution

When the user triggers this skill, the agent MUST follow these steps in order:

### 1. Context Assembly
Read the `Soul/QC_Rebuttals_and_Context.md` file FIRST. This file dictates which QC bugs must be fixed in the code (e.g., EM matrix expansion, overnight Kalman scaling, execution delays) and which "bugs" are actually intentional features (e.g., single-sided execution, dropping incomplete bars, macro-drift ADF targeting).

### 2. Multi-Agent Delegation (The Engine)
Do not attempt to rewrite massive codebases single-handedly. You must construct a rigorous prompt and use the `invoke_subagent` tool to spawn the `teamwork_preview` agent team to do the heavy lifting. 
Your prompt to the teamwork agent must include:
- The exact paths of the raw/flawed notebooks to fetch (e.g., from `Raw/Sources/attachments/`).
- The explicit list of mathematical fixes required (pulled from Context Assembly).
- The explicit list of intentional design choices that *must remain untouched*.
- A strict requirement that the teamwork agent saves the rewritten, production-grade outputs directly into `Soul/Code/`.

### 3. Methodology Distillation
While the agent team works on the code in the background, synthesize the mathematical models (from the `Plans/` directory) into a single, elegant `Soul/Methodology/production_logic.md` document. This document should read like a whitepaper, explaining exactly how the production code operates under the hood.

### 4. Verification Check
Once the agent team claims victory, read their output in `Soul/Code/` to ensure they actually applied the fixes correctly before telling the user the deployment is complete.

## Connections
- [[teamwork_preview]]
- [[plan-first]]
