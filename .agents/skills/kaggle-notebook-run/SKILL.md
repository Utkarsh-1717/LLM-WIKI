---
name: kaggle-notebook-run
trigger: [run on Kaggle, backtest, Kaggle notebook, strategy, kaggle run, kaggle fetch]
description: Creates, runs, and monitors Kaggle notebooks. Covers all known failure modes from production use. Data fetch AND dataset publish happen in ONE notebook.
version: 3.2.0
last_updated: 2026-06-04
---

# Kaggle Notebook Run Skill

---

## CRITICAL RULES (Never Violate)

1. **ONE notebook, all stages** — data fetching AND dataset publishing MUST happen in the same notebook. Never split.
2. **Hardcode all API credentials** directly in notebook code — Kaggle has no access to `~/.quant_env`.
3. **Never download large outputs locally** — always publish from within Kaggle using the Kaggle Python API.
4. **Always save plan files** to `/storage/emulated/0/Quant/LLM-WIKI/Plans/<task-name>.md` before execution.
5. **Always pulse-check** after pushing — use the `kaggle-pulse-check` skill **with the real slug from push output**.
6. **All notebook cells MUST have an `id` field** (8-char UUID) — required by nbformat 4.5+. Missing IDs cause papermill to skip/reorder cells.
7. **Never hardcode input file paths** — always use a path-discovery cell first.
8. **Never use `except ImportError` alone for GPU code** — use `except Exception`.
9. **Always lock threads before multiprocessing** — set `os.environ["OPENBLAS_NUM_THREADS"] = "1"` and `OMP_NUM_THREADS = "1"` before importing NumPy if using `multiprocessing.Pool` (fork) to prevent thread clashing and silent deadlocks.
10. **Never pre-compile Numba before a `fork`** — let each child process compile its own JIT functions to avoid fatal LLVM lock deadlocks.
11. **Strict Loop Hoisting (O(N) & I/O)** — In any parallel processing script (`joblib`, `multiprocessing`), ALL database loads must happen exactly ONCE in the global parent. ALL invariant complex calculations (Kalman Filters, Rolling Z-Scores, Variances) MUST be hoisted out of the parallel loop. Failure to do so will cause 50+ minute disk thrashing and memory exhaustion deadlocks.

---

## Known Failure Modes & Fixes (Learned from Production)

### ❌ Failure 1 — Wrong slug in pulse-check ("Cannot access kernel")
**Cause:** The kernel slug Kaggle assigns is derived from the **title** field, not the `id` field in `kernel-metadata.json`. If they don't match, Kaggle creates a different slug and warns you. Monitoring the wrong slug gives `UNKNOWN: Cannot access kernel` forever.

**Fix:** Always parse the real slug from the push output URL:
```
Kernel version N successfully pushed.  Please check progress at
https://www.kaggle.com/code/utkarshpatelthefirst/<REAL-SLUG>
```
Pass this exact slug to the pulse-checker. Never use the `id` field from `kernel-metadata.json`.

**Prevention:** Make the `id` slug match what Kaggle would generate from the title. Kaggle slugifies titles by lowercasing and replacing spaces/special chars with hyphens. Test: `re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')`.

---

### ❌ Failure 2 — `unable to open database file` (hardcoded path)
**Cause:** For `dataset_sources`, Kaggle mounts datasets at:
- Standard: `/kaggle/input/<dataset-slug>/<filename>`
- But sometimes: `/kaggle/input/datasets/<owner>/<slug>/<filename>` (depends on Kaggle version)

Hardcoding either path will fail on the other variant.

**Fix:** Always use a **path-discovery cell** as the very first code cell. It finds the file at runtime regardless of mount variant:

```python
import os, glob

print("=== /kaggle/input contents ===")
for root, dirs, files in os.walk('/kaggle/input'):
    for f in files:
        fpath = os.path.join(root, f)
        print(f"  {fpath}  ({os.path.getsize(fpath)/(1024**3):.2f} GB)")

# Find SQLite DB (adjust extension/name as needed)
hits = glob.glob('/kaggle/input/**/*.sqlite', recursive=True)
if not hits:
    raise FileNotFoundError("No .sqlite found under /kaggle/input — check dataset attachment")
DB_PATH = hits[0]
print(f"\n✅ DB_PATH = {DB_PATH}")
```

This cell sets `DB_PATH` as a global. All subsequent cells reference `DB_PATH` — never hardcode.

---

### ❌ Failure 3 — `AttributeError: cudf.DataFrame has no attribute 'from_pandas'`
**Cause:** `cudf.DataFrame.from_pandas()` was removed in newer cuDF versions. The `except ImportError` block never caught it because cuDF imported successfully — the method just didn't exist.

**Fix:**
1. Use `cudf.DataFrame(pandas_df)` constructor directly (works in all cuDF versions)
2. Use `except Exception` (not `except ImportError`) to catch ALL GPU failures:

```python
try:
    import cudf
    lr_gpu  = cudf.DataFrame(log_returns)       # ← constructor, not from_pandas()
    corr_df = lr_gpu.corr().to_pandas()
    backend = "cuDF (GPU)"
except Exception as gpu_err:                    # ← catches ImportError, AttributeError, MemoryError, etc.
    print(f"GPU failed ({type(gpu_err).__name__}: {gpu_err}) — using CPU")
    corr_df = log_returns.corr(method='pearson')
    backend = "pandas (CPU)"
```

---

### ❌ Failure 4 — `MissingIDFieldWarning` / cell execution order issues
**Cause:** nbformat 4.5+ requires every cell (code AND markdown) to have a unique `id` field. Without it, papermill may skip or reorder cells, causing `NameError` on variables set in earlier cells.

**Fix:** Always include `"id": str(uuid.uuid4())[:8]` in every cell dict in the builder script:

```python
import uuid

def cell(cell_type, source):
    cell_id = str(uuid.uuid4())[:8]
    if cell_type == "markdown":
        return {"id": cell_id, "cell_type": "markdown", "metadata": {}, "source": [...]}
    return {"id": cell_id, "cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [...]}
```

---

### ❌ Failure 5 — Strict inner-join collapses time series to a fraction of available data
**Cause:** If even one symbol has a gap at a timestamp, the strict `dropna(how='any')` removes that entire row for all 500 symbols. Sparse symbols (recent IPOs, halted stocks) can cause the inner-join to retain only 30–40% of available bars.

**Fix:** Two-pass smart alignment:

```python
n_total_bars = len(price_matrix)

# Pass 1: Drop symbols with < 80% coverage (sparse listings, recent IPOs)
coverage = price_matrix.notna().sum() / n_total_bars
sparse   = coverage[coverage < 0.80].index.tolist()
if sparse:
    print(f"Dropping {len(sparse)} sparse symbols (<80% coverage): {sparse[:5]}...")
    price_matrix = price_matrix.drop(columns=sparse)

# Pass 2: Inner-join on survivors
price_matrix = price_matrix.dropna(how='any', axis=0)
print(f"Aligned: {price_matrix.shape[0]:,} bars × {price_matrix.shape[1]} symbols")
assert price_matrix.shape[0] >= 5000, "Too few bars — check data quality"
```

---

## Kaggle Input Path Reference

| Source type | Mount path |
|---|---|
| Dataset source (`dataset_sources`) | `/kaggle/input/<dataset-slug>/` OR `/kaggle/input/datasets/<owner>/<slug>/` |
| Kernel source (`kernel_sources`) | `/kaggle/input/notebooks/<owner>/<kernel-slug>/` |

**Always use path-discovery cell — never assume the exact path.**

---

## Mandatory Notebook Cell Structure

Every notebook MUST follow alternating Markdown → Code per stage:

**CELL N (Markdown):**
```
## Stage N — [Stage Name]
**Input:** [variables]
**Output:** [variables]
**Core Logic:** [step-by-step]
**Formula:** $$ [LaTeX or "No formula — procedural"] $$
```

**CELL N+1 (Code):** One stage only. No mixing.

**CELL 0 (Code — always first):** Path-discovery cell. Sets all input file paths as globals.

---

## kernel-metadata.json Template

```json
{
  "id": "utkarshpatelthefirst/<kernel-slug>",
  "title": "<Human Readable Title>",
  "code_file": "<notebook>.ipynb",
  "language": "python",
  "kernel_type": "notebook",
  "is_private": "true",
  "enable_gpu": "true",
  "enable_internet": "true",
  "dataset_sources": ["utkarshpatelthefirst/<dataset-slug>"],
  "competition_sources": [],
  "kernel_sources": [],
  "model_sources": []
}
```

**Slug alignment rule:** The `id` slug MUST match what Kaggle generates from the title. Compute it as:
```python
import re
slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
```
If they don't match, Kaggle warns and creates a different slug — causing monitoring to fail.

---

## Dataset Publish Template (in-notebook)

```python
import json, os, shutil
from kaggle.api.kaggle_api_extended import KaggleApi

# Hardcoded (correct for Kaggle — no ~/.quant_env available inside notebooks)
os.environ['KAGGLE_USERNAME'] = 'utkarshpatelthefirst'
os.environ['KAGGLE_KEY']      = 'fbef16329099428205f671dd5de8337b'

api = KaggleApi()
api.authenticate()

export_dir = '/kaggle/working/dataset_export'
os.makedirs(export_dir, exist_ok=True)
shutil.copy('/kaggle/working/output_file.csv', f'{export_dir}/output_file.csv')

meta = {
    "title"    : "My Dataset Title",
    "id"       : "utkarshpatelthefirst/my-dataset-slug",
    "licenses" : [{"name": "CC0-1.0"}]
}
with open(f'{export_dir}/dataset-metadata.json', 'w') as f:
    json.dump(meta, f, indent=2)

api.dataset_create_new(export_dir, dir_mode='zip', quiet=False)
print("✅ Published: https://www.kaggle.com/datasets/utkarshpatelthefirst/my-dataset-slug")
```

---

## Execution Workflow

1. Save plan to `LLM-WIKI/Plans/<task-name>.md`
2. **Perform Code Review for Loop Bloat**: Verify SQLite is read *once* globally, and invariant arrays (Kalman, Rolling metrics) are calculated *before* passing into any `joblib` loops.
3. Write builder script (`build_notebook.py`) — use the `cell()` helper with `id` fields
4. Run builder locally → generates `.ipynb`
4. Write `kernel-metadata.json` — ensure slug matches title
5. `kaggle kernels push -p <dir>` — capture full stdout
6. **Parse real slug from push output URL**
7. **Parse real slug from push output URL**
8. Start `kaggle-pulse-check` skill using the real slug (v3.0.0+):
   - `CONNECTIVITY_LOST` and `UNKNOWN` → keep polling — never report ERROR
   - `KERNEL_ERROR` requires **3 consecutive confirmations** before declaring crash
   - Phase 2 interval = **120 seconds** (robust on mobile/slow connections)
9. On COMPLETE: verify dataset published, report URL + file sizes to user
10. On ERROR (confirmed 3×): pulse-check auto-fetches log, parse last 80 lines, fix and re-push

---

## Connections
- [[fyers-auth]]
- [[kaggle-pulse-check]]
- [[kaggle-db-update]]
- [[fyers-historical-kaggle]]
