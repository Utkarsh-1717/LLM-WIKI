---
title: kaggle-notebook-hardening
type: concept
tags:
  - "concept"
  - "kaggle"
  - "engineering"
  - "lessons-learned"
topics: [kaggle, engineering, debugging, reliability, lessons-learned]
created: 2026-06-02
updated: 2026-06-02
status: evergreen
---

# Kaggle Notebook Hardening

Lessons learned from production Kaggle notebook failures. Every rule here was learned from a real failure. Apply all of them to every notebook, always.

## Failure 1 — Wrong Kernel Slug in Pulse-Check

**Symptom:** `Cannot access kernel` — monitoring silently fails, user gets no updates.

**Root Cause:** Kaggle generates the kernel slug from the **title**, not the `id` field in `kernel-metadata.json`. If they don't match, Kaggle creates a different slug and warns you — but the agent was using the `id` field slug, which didn't exist.

**Fix:** Always parse the real slug from the push output URL:
```
Kernel version N successfully pushed.  Please check progress at
https://www.kaggle.com/code/utkarshpatelthefirst/<REAL-SLUG>
```
```python
import re
match = re.search(r'kaggle\.com/code/([^/]+/[^\s]+)', push_output)
kernel_ref = match.group(1).strip()
```

**Prevention:** Compute the expected slug from the title before creating `kernel-metadata.json`:
```python
slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
```
Set `"id": f"utkarshpatelthefirst/{slug}"` to match.

---

## Failure 2 — `unable to open database file`

**Symptom:** `OperationalError: unable to open database file` at `sqlite3.connect(DB_PATH)`.

**Root Cause:** Kaggle mounts datasets at two different paths depending on environment version:
- `/kaggle/input/<dataset-slug>/`
- `/kaggle/input/datasets/<owner>/<slug>/`

Hardcoding either path fails on the other.

**Fix:** Always use a **path-discovery cell** as the very first code cell:
```python
import glob
hits = glob.glob('/kaggle/input/**/*.sqlite', recursive=True)
if not hits:
    raise FileNotFoundError("No .sqlite found — check dataset attachment")
DB_PATH = hits[0]
```
Never hardcode `/kaggle/input/...` paths. Use `DB_PATH` as a global set by the discovery cell.

---

## Failure 3 — `AttributeError: cudf.DataFrame has no attribute 'from_pandas'`

**Symptom:** GPU code fails with `AttributeError` but CPU fallback never runs because `except ImportError` doesn't catch it.

**Root Cause:** `cudf.DataFrame.from_pandas()` was removed in newer cuDF versions. The `import cudf` succeeds — only the method call fails with `AttributeError`.

**Fix:**
1. Use `cudf.DataFrame(pandas_df)` constructor (works in all versions)
2. Use `except Exception` not `except ImportError`:

```python
try:
    import cudf
    corr_df = cudf.DataFrame(log_returns).corr().to_pandas()  # constructor, not from_pandas
except Exception as gpu_err:   # catches ImportError, AttributeError, MemoryError, etc.
    print(f"GPU failed: {gpu_err} — using CPU")
    corr_df = log_returns.corr(method='pearson')
```

---

## Failure 4 — Cell Execution Order Issues (Missing `id` Fields)

**Symptom:** `NameError: name 'DB_PATH' is not defined` — a variable set in cell N is not visible in cell N+1 despite cells being in the right order.

**Root Cause:** nbformat 4.5+ requires every cell to have a unique `id` field. Without it, papermill may skip or reorder cells. The `MissingIDFieldWarning` in logs signals this.

**Fix:** Add `"id"` field to every cell in the notebook builder:
```python
import uuid

def cell(cell_type, source):
    return {
        "id": str(uuid.uuid4())[:8],   # required by nbformat >= 4.5
        "cell_type": cell_type,
        # ... rest of cell dict
    }
```

---

## Failure 5 — Strict Inner-Join Collapses Time Series

**Symptom:** Notebook runs but `n_obs = 17,566` when 44,250 bars exist — losing 60% of data.

**Root Cause:** A single sparse symbol (recent IPO, halted stock) forces `dropna(how='any')` to drop every timestamp where that symbol has a gap.

**Fix:** Two-pass alignment — see [[timeseries-alignment]] for full details.
```python
# Pass 1: Remove sparse symbols
coverage = price_matrix.notna().sum() / len(price_matrix)
price_matrix = price_matrix.drop(columns=coverage[coverage < 0.80].index)
# Pass 2: Inner join survivors
price_matrix = price_matrix.dropna(how='any', axis=0)
```

---

## Failure 6 — Silent Hang (Multiprocessing Fork Deadlock)

**Symptom:** Kaggle kernel CPU drops to 0%, but the notebook stays `RUNNING` forever until the 12-hour timeout.

**Root Cause:** Using `multiprocessing.Pool` (which defaults to `fork` on Linux) *after* initializing heavily threaded C/C++ libraries like **Numba (LLVM)** or **NumPy (OpenBLAS)**.
When `fork()` is called, the OS duplicates the parent's memory state, including internal mutex locks that were currently held by LLVM/OpenBLAS background threads. However, the background threads themselves are *not* copied to the child process. When the child process calls a Numba/NumPy function, it waits forever for a non-existent thread to release the lock, causing a permanent deadlock.

**Fix:**
1. **Never warm-up or pre-compile Numba** in the parent process before a `fork`. Let each child process compile it on their first call (the 1-second overhead is worth the stability).
2. **Lock NumPy threads**: Always set `os.environ["OPENBLAS_NUM_THREADS"] = "1"` and `os.environ["OMP_NUM_THREADS"] = "1"` before importing NumPy if you plan to use `multiprocessing`. This prevents OpenBLAS from spawning internal thread pools that clash with `fork`, and prevents CPU thrashing (e.g., 4 workers × 4 NumPy threads = 16 threads fighting for 4 Kaggle CPU cores).

---

## Failure 7 — SQLite Thrashing via Parallel Disk Reads

**Symptom:** In parallel grid searches (e.g. `joblib.Parallel` with 5000+ permutations), the kernel takes 50+ minutes instead of 2 minutes, and memory spikes until OOM.

**Root Cause:** The parallel worker function is connecting to SQLite and reading data from the disk for *every single iteration*. 5,000 workers trying to read from a single SQLite file simultaneously causes catastrophic disk I/O thrashing and memory exhaustion.

**Fix:** Read all required database tables into pandas/numpy exactly *once* in the global parent process, *before* triggering `joblib.Parallel`. Pass the lightweight numpy arrays into the parallel loop.

---

## Failure 8 — Joblib Loop Bloat (O(N) Optimization)

**Symptom:** A parallel parameter sweep takes astronomically long (e.g., 40+ minutes for a 5,000-cell grid) even with CPU usage at 100%.

**Root Cause:** Complex math that *does not depend on the grid parameters* (e.g., calculating a Kalman filter array, or computing a 3750-bar rolling variance) is trapped inside the parallel worker function. If a 50,000-bar rolling metric is calculated inside a 5,000-iteration grid search, it results in ~1 billion redundant python operations.

**Fix:** **Hoist all invariant calculations completely out of the parallel loop.** Pre-compute the Kalman Filter, Rolling Z-Scores, and any other fixed time-series arrays globally. Pass only the pre-computed arrays to the worker, so the worker only does the bare minimum logic (e.g., fast entry/exit checks).

---

## Hardening Checklist (Apply to Every Notebook)

- [ ] Path-discovery cell is the **first** code cell — sets all file paths as globals
- [ ] Every cell has a UUID `id` field (8 chars)
- [ ] GPU try/except uses `except Exception` not `except ImportError`
- [ ] GPU code uses `cudf.DataFrame()` constructor, not `from_pandas()`
- [ ] Kernel metadata `id` slug is computed from title — not made up
- [ ] Real slug parsed from push output before starting pulse-check
- [ ] Pulse-check uses `except` on UNKNOWN status (don't crash — keep polling)
- [ ] Two-pass alignment applied before any cross-sectional computation
- [ ] Sanity assertions after every major step (NaN check, inf check, shape check)

## Connections
- [[quant-agent-system]]
- [[session-2026-06-02b]]
- [[index]]
- [[kaggle-compute]]
- [[kaggle-notebook-run]]
- [[kaggle-pulse-check]]
- [[timeseries-alignment]]
- [[pairs-trading-pipeline]]
- [[pairs-stage2-kalman-ou]]
