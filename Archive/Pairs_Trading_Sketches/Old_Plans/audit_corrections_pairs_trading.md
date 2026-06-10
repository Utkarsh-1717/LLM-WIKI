> [!WARNING]
> **ARCHIVED & OBSOLETE**
> This file is part of the trial-and-error "Sketch" phase. 
> The mathematics and code herein may contain deprecated Expectation-Maximization loops or failed concepts.
> The final, verified truth is located in the `Soul/` directory.
> Tags: #archived-sketch #pairs-trading-prototype

# Plan: Audit Corrections for Master Pairs Trading Soul

## Objective
Modify `/storage/emulated/0/Quant/LLM-WIKI/Soul/Master_Pairs_Trading_Soul.ipynb` to apply specific code corrections identified in the audit. These include Stage 1 alignment logic improvements, OLS initialization tuning, stabilization bounds for phi estimation, removal of duplicate `em_kalman_scaled` helper definitions, and expanding detailed backtest stats returned in the optimization loop.

## Open Questions (for user review)
- No open questions as the exact modifications were specified in detail in the prompt.
- Design decisions: We will write a small Python utility script to parse, modify target cell sources by cell ID, and save the notebook back, preserving its JSON structure completely.

## Proposed Approach

### Step 1 — Backup the Notebook
- **What**: Create a backup of the original notebook.
- **Why**: Prevent data loss or corruption during programmatical edits.
- **How**: Run command `cp /storage/emulated/0/Quant/LLM-WIKI/Soul/Master_Pairs_Trading_Soul.ipynb /storage/emulated/0/Quant/LLM-WIKI/Soul/Master_Pairs_Trading_Soul.ipynb.bak`.

### Step 2 — Parse Notebook and Locating Target Cells
- **What**: Inspect the cell IDs and search for source snippets in cell IDs `e9cf67b2`, `ca17c2f1`, `c138afc1`.
- **Why**: Make sure target cell IDs match the audit description and that target strings exist within them.
- **How**: Use `view_file` or write a Python inspection script to print out contents of those cell IDs.

### Step 3 — Perform Replacements
- **What**: Write and run a Python script to do JSON-safe replacement of the target substrings inside the target cells:
  1. In `e9cf67b2`: replace Stage 1 alignment lines.
  2. In `ca17c2f1`: replace OLS P0, change phi stability check, and remove the duplicate definition of `em_kalman_scaled`.
  3. In `c138afc1`: replace `optimized_rows.append` block to export more stats.
- **Why**: Modifying `.ipynb` raw text via search-and-replace can break JSON/escaping. Reading as JSON, parsing the source array, doing text replacement, and saving back is much safer.
- **How**: Run a Python script `modify_notebook.py` to perform the changes.

### Step 4 — Verification
- **What**: Verify JSON validity, check git diff, and run a syntax/compile check on the python code cells.
- **Why**: Guarantee that the notebook is not corrupted and is syntactically sound.
- **How**: Run `python -m json.tool` on the notebook file, and compile/parse cells to verify syntax.

## Time Estimate
~10 minutes

## Connections to Existing Skills
- [[soul-production-compiler]]
- [[plan-first]]
