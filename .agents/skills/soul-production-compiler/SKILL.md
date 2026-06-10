---
name: soul-production-compiler
trigger: [finalize to soul, productionize, create soul artifacts, final stage, production grade, update soul, ingest everything]
description: Consolidates verified math, logical rules, QC reports, and corrected Python/Notebook code into the final 'Soul/' production directory and keeps the Wiki knowledge graph in sync.
version: 2.0.0
last_updated: 2026-06-10
---

# Soul Production Compiler Skill

## Purpose
The `Soul/` directory is the final Source of Truth for production deployment. This skill orchestrates the compilation of all drafting phases (Plans, QC Audits, Rebuttals) into finalized, production-ready assets. No flawed or experimental code belongs here.

---

## Soul Directory Architecture (Current)

The `Soul/pairs-trading/` directory is the canonical structure. Use this as the template for all strategies:

```
Soul/pairs-trading/
├── Methodology/
│   ├── production_logic.md         ← Master whitepaper (all stages, all methods, all results)
│   ├── QC_decisions.md             ← Design choices, rebuttals, why X was rejected
│   ├── stage1_pearson_screening.md ← Stage 1 math and implementation
│   ├── stage1b_cointegration.md    ← Stage 1B: Engle-Granger ADF screening (NEW)
│   ├── stage2_ou_calibration.md    ← Stage 2: OU Chunked Fit math
│   ├── stage3_execution_engine.md  ← Stage 3A: Kalman execution engine
│   └── stage3b_continuous_ols.md   ← Stage 3B: Continuous Vectorized OLS (NEW)
├── Code/
│   ├── build_full_pipeline_nb.py    ← Generates Kalman notebook (pairs-full-pipeline-v3)
│   ├── build_continuous_ols_pipeline_nb.py ← Generates Continuous OLS notebook
│   ├── build_stage1b_cointegration_nb.py   ← Stage 1B cointegration (diagnostic)
│   └── kaggle_staging/             ← Generated notebooks + output CSVs
│       ├── full_pipeline/          ← Kalman notebook + kernel-metadata.json
│       ├── continuous_ols_pipeline/ ← OLS notebook + kernel-metadata.json
│       └── outputs_*/              ← Downloaded CSV results per run
└── Conclusions/
    └── backtest_record.md          ← All backtest results, all methods, all pair counts
```

---

## Workflow Execution

When the user triggers this skill (keywords: "update soul", "ingest everything", "finalize"), the agent MUST follow these steps in order:

### 1. Audit Current State
Read the following files FIRST before writing anything:
- `Soul/<strategy>/Conclusions/backtest_record.md` — what results are already recorded
- `Soul/<strategy>/Methodology/production_logic.md` — what the whitepaper currently says
- `Wiki/catalog.jsonl` — what wiki nodes exist

### 2. Identify All Deltas
Compare what is in Soul/Wiki against what was actually done in the current session:
- New Kaggle kernels run → new results to record in backtest_record.md
- New methodology files added → new catalog.jsonl entries needed
- New code scripts created → Code/ section needs updating
- New design decisions made → QC_decisions.md update needed

### 3. Update Soul Files (in order)
Update files in this dependency order to maintain consistency:
1. `Methodology/QC_decisions.md` — record any new design choices first
2. `Methodology/production_logic.md` — the master whitepaper (references QC decisions)
3. Stage-specific files (`stage1b_`, `stage3b_`, etc.) — if stages were added/changed
4. `Conclusions/backtest_record.md` — update results tables

### 4. Update Wiki Knowledge Graph
For each updated Soul file:
1. Check if a corresponding `Wiki/Entities/` note exists
2. If yes: update it with new results/connections
3. If no: create a new entity note with minimum 3 `[[wikilinks]]` and a `## Connections` section
4. Update `Wiki/catalog.jsonl` with new entries

### 5. Session Log
Always create a `Wiki/Logs/session-YYYY-MM-DD.md` log documenting:
- Key discoveries made
- Kernels run and their durations
- Files updated
- Links to all updated files

### 6. Git Commit
```bash
cd /storage/emulated/0/Quant/LLM-WIKI
git add -A
git commit -m "feat: <brief description>\n\n- <file1>: <what changed>\n- <file2>: <what changed>"
```

---

## Wikilink Rules (Never Violate)

Every Wiki/ note MUST:
- Contain minimum 3 `[[wikilinks]]` to other existing `.md` files
- End with a `## Connections` section listing all related notes
- Never reference `[[a-note-name]]` unless that `.md` file actually exists

---

## Connection Topology for Pairs Trading

Use this as a reference for linking new notes correctly:

```
pairs-trading-strategy
├── stage1-pearson-screening
├── stage1b-cointegration ← NEW
│   └── continuous-ols-execution ← NEW
├── stage2-ou-calibration
├── stage3-execution-engine
│   └── stage3b-continuous-ols (same as continuous-ols-execution)
├── QC-decisions-pairs-trading
├── backtest-record-pairs-trading
├── kaggle-notebook-run
└── master-data-1min-dataset
```

---

## Connections
- [[plan-first]]
- [[kaggle-notebook-run]]
- [[pairs-trading-strategy]]
- [[backtest-record-pairs-trading]]
