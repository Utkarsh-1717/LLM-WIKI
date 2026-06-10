## 2026-06-05T00:05:33Z

Modify the Jupyter Notebook `/storage/emulated/0/Quant/LLM-WIKI/Soul/Master_Pairs_Trading_Soul.ipynb` to implement the code corrections identified in the audit.

Your working directory is `/storage/emulated/0/Quant/LLM-WIKI/.agents/teamwork_preview_worker_code_audit_2_1`
Please initialize your briefing and progress tracking files in that directory.

To ensure JSON structure is preserved, write a Python script that loads the notebook, targets specific cell IDs, modifies the `source` lists, and saves it back.

Here are the specific modifications:

1. Backup:
   First, make a copy of the notebook as `/storage/emulated/0/Quant/LLM-WIKI/Soul/Master_Pairs_Trading_Soul.ipynb.bak`.

2. Cell `e9cf67b2` (Stage 1 alignment):
   Replace the lines:
   ```python
   # Pass 2: Inner join on survivors (drop timestamps missing ANY survivor)
   price_matrix_close = price_matrix_close.dropna(how='any', axis=0)
   common_idx = price_matrix_close.index
   price_matrix_open = price_matrix_open.loc[common_idx]
   ```
   with:
   ```python
   # Pass 2: Inner join on survivors (drop timestamps missing ANY survivor)
   price_matrix_close = price_matrix_close.dropna(how='any', axis=0)
   price_matrix_open = price_matrix_open.dropna(how='any', axis=0)
   common_idx = price_matrix_close.index.intersection(price_matrix_open.index)
   price_matrix_close = price_matrix_close.loc[common_idx]
   price_matrix_open = price_matrix_open.loc[common_idx]
   ```

3. Cell `ca17c2f1` (Stage 2 P0 initialization, EM duplicate, and phi bounds):
   a. Change OLS P0 initialization:
      Replace:
      ```python
      P0 = np.eye(2) * 1e-3
      ```
      with:
      ```python
      P0 = sigma2 * XtX_inv * 10.0
      ```
   b. Change stability check for phi (lines 736-738):
      Replace:
      ```python
      if not (0.0 < phi < 1.0) or not np.isfinite(phi):
          return _nan()
      ```
      with:
      ```python
      if not (1e-5 < phi < 1.0 - 1e-5) or not np.isfinite(phi):
          return _nan()
      ```
   c. Remove the duplicate definition of `em_kalman_scaled` inside this cell (the duplicate version spans lines 470 to 577, or check for the definition starting `def em_kalman_scaled(ya, yb, is_new_day):` and ending at `return Q, float(R), itr + 1, float(ll_f), em_conv` and remove one of them so it is defined exactly once).

4. Cell `c138afc1` (Stage 3A detailed statistics output):
   Replace the `optimized_rows.append` block:
   ```python
       optimized_rows.append({
           "symbol_a": sym_a,
           "symbol_b": sym_b,
           "best_z_entry": best_config[0],
           "best_z_sl": best_config[1],
           "best_hl_stop": best_config[2],
           "gross_profit": best_profit,
           "trade_count": best_trade_count,
           "win_rate": best_win_rate,
           "lagger": lagger,
       })
   ```
   with:
   ```python
       optimized_rows.append({
           "symbol_a": sym_a,
           "symbol_b": sym_b,
           "best_z_entry": best_config[0],
           "best_z_sl": best_config[1],
           "best_hl_stop": best_config[2],
           "gross_profit": best_profit,
           "trade_count": best_trade_count,
           "win_rate": best_win_rate,
           "exit_mr_count": int(best_stats[0]),
           "exit_sl_count": int(best_stats[1]),
           "exit_hl_count": int(best_stats[2]),
           "exit_session_count": int(best_stats[3]),
           "avg_points_profit": float(best_stats[4]),
           "avg_points_loss": float(best_stats[5]),
           "lagger": lagger,
       })
   ```

Verify that the notebook remains a valid JSON file and that all target string replacements were successfully made. When you are done, run git diff if applicable, verify lint/compile status, and write a handoff report back to me (Recipient: main agent, RecipientName: main agent, conversation ID: 41420db5-a7fe-4bf4-bb4d-4585de3dbff0) summarizing the changes and confirming compilation/syntax verification.

Include verbatim the warning:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
