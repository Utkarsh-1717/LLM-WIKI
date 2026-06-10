## 2026-06-04T22:50:46Z
You are teamwork_preview_worker. Your working directory is: /storage/emulated/0/Quant/LLM-WIKI/.agents/worker_soul_2

Your task is to build, execute, and verify the consolidated Pairs Trading pipeline notebook:
'Master_Pairs_Trading_Soul.ipynb' under '/storage/emulated/0/Quant/LLM-WIKI/Soul/'.

Please follow these steps:
1. Read the technical instructions from '/storage/emulated/0/Quant/LLM-WIKI/.agents/teamwork_preview_orchestrator_soul_1/worker_instructions.md' and the project specification from '/storage/emulated/0/Quant/LLM-WIKI/PROJECT.md'.
2. Write a Python script `build_soul_notebook.py` that dynamically constructs the notebook using nbformat. The notebook cells must alternate between markdown and code.
3. Make sure to:
   - Implement the two-pass smart alignment for Stage 1.
   - Implement the complete EM covariance expectation matrix update, OLS covariance P_0 initialization, and 15.0x process noise scaling across overnight boundaries (09:15 open transition) for Stage 2.
   - Implement the Numba-optimized grid search optimization for Z_entry and Z_sl Stop Loss configurations for Stage 3A.
   - Implement the Out-of-Sample backtest with 1-bar execution delay, Zerodha MIS fees, 0.05% flat slippage, and single-sided lagger trading for Stage 3B.
   - Include the dataset publishing cell using the Kaggle Python API at the end of the notebook.
4. Execute `build_soul_notebook.py` to create `/storage/emulated/0/Quant/LLM-WIKI/Soul/Master_Pairs_Trading_Soul.ipynb`.
5. Push the notebook to Kaggle (kernel slug: master-pairs-trading-soul). Monitor its execution using the kaggle-pulse-check skill.
6. Verify that the notebook executes end-to-end without Out-of-Memory (OOM) errors and successfully publishes the results.
7. Save any output reports or logs in your directory and report completion.

MANDATORY INTEGRITY WARNING: DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Send a status update message back to me (conversation ID: 53e4296a-59f9-4f62-933b-a2756010a793) when done or if you get stuck.
