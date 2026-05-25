---
name: kaggle-notebook-run
trigger: [run on Kaggle, backtest, Kaggle notebook, strategy, kaggle run]
description: Creates, runs, and retrieves results from a Kaggle notebook
---

## Mandatory Notebook Cell Structure

Every notebook built by this skill MUST follow this structure for EVERY stage.
No exceptions. Never skip markdown cells.

CELL 1 — Markdown (always first):
```
## Stage N — [Stage Name]
**Methodology:** [what this stage does in plain English]
**Input:** [exact variable names and data types entering this stage]
**Output:** [exact variable names and data types produced]
**Core Logic:** [step-by-step plain English explanation]
**Formula/Equation:**
$$ [LaTeX formula if applicable, else write: No formula — procedural logic] $$
```

CELL 2 — Code (immediately after markdown):
Implementation of that stage only. No mixing of stages in one cell.

Repeat CELL 1 + CELL 2 pattern for every stage.

## Execution Rules

1. Use credentials from ~/.quant_env
2. Create notebook via Kaggle API or push .ipynb file
3. Enable GPU accelerator: True
4. Enable internet: True
5. On Kaggle: use full parallel processing, all CPUs, GPU — no restrictions there
6. Save version after run completes
7. Download output files to ~/storage/shared/Quant/kaggle-outputs/[notebook-name]/
8. Report: notebook URL, version number, runtime, key output metrics
9. If run fails: download logs, report exact error to user
