# Kaggle Notebook Run Skill Copy
Refer to original at /storage/emulated/0/Quant/LLM-WIKI/.agents/skills/kaggle-notebook-run/SKILL.md
Trigger: [run on Kaggle, backtest, Kaggle notebook, strategy, kaggle run, kaggle fetch]
Version: 3.2.0

## CRITICAL RULES (Never Violate)
1. ONE notebook, all stages — data fetching AND dataset publishing MUST happen in the same notebook. Never split.
2. Hardcode all API credentials directly in notebook code — Kaggle has no access to ~/.quant_env.
3. Never download large outputs locally — always publish from within Kaggle using the Kaggle Python API.
4. Always save plan files to /storage/emulated/0/Quant/LLM-WIKI/Plans/<task-name>.md before execution.
5. Always pulse-check after pushing — use the kaggle-pulse-check skill with the real slug from push output.
6. All notebook cells MUST have an id field (8-char UUID) — required by nbformat 4.5+. Missing IDs cause papermill to skip/reorder cells.
7. Never hardcode input file paths — always use a path-discovery cell first.
8. Never use except ImportError alone for GPU code — use except Exception.
9. Always lock threads before multiprocessing — set os.environ["OPENBLAS_NUM_THREADS"] = "1" and OMP_NUM_THREADS = "1" before importing NumPy if using multiprocessing.Pool (fork) to prevent thread clashing and silent deadlocks.
10. Never pre-compile Numba before a fork — let each child process compile its own JIT functions to avoid fatal LLVM lock deadlocks.
11. Strict Loop Hoisting (O(N) & I/O) — In any parallel processing script (joblib, multiprocessing), ALL database loads must happen exactly ONCE in the global parent. ALL invariant complex calculations (Kalman Filters, Rolling Z-Scores, Variances) MUST be hoisted out of the parallel loop. Failure to do so will cause 50+ minute disk thrashing and memory exhaustion deadlocks.
