import sys

with open('/storage/emulated/0/Quant/_notebooks/stage3-experiment-z-stoploss/build_notebook.py', 'r') as f:
    code = f.read()

# 1. Signature
code = code.replace('def backtest_pair(row, db_path, Z_ENTRY, EXIT_MODE):', 'def backtest_pair(row, db_path, Z_ENTRY):')

# 2. Init Suspension
code = code.replace(
    '        is_long     = None  # True = bought lagging asset, False = shorted\n'
    '        qty         = 0\n',
    '        is_long     = None  # True = bought lagging asset, False = shorted\n'
    '        qty         = 0\n'
    '        suspended   = False # Track if we are in structural timeout\n'
)

# 3. Exit Logic
old_exit_logic = """                # Custom Sweep Exit Logic
                if EXIT_MODE == "z_zero":
                    if entry_z >= Z_ENTRY and z <= 0.0:
                        exit_reason = "mean_reversion"
                    elif entry_z <= -Z_ENTRY and z >= 0.0:
                        exit_reason = "mean_reversion"
                elif EXIT_MODE == "hl_time":
                    if bars_held >= hl_bars:
                        exit_reason = "halflife_timeout"

                # 3. Session-end forced exit at 15:28
                if exit_reason is None and bar_time >= FORCE_EXIT_TIME:
                    exit_reason = "session_end"
"""
# Note: we need to replace exactly how it is represented in the python string format
old_exit_logic_str = """    '                # Custom Sweep Exit Logic\\n'
    '                if EXIT_MODE == "z_zero":\\n'
    '                    if entry_z >= Z_ENTRY and z <= 0.0:\\n'
    '                        exit_reason = "mean_reversion"\\n'
    '                    elif entry_z <= -Z_ENTRY and z >= 0.0:\\n'
    '                        exit_reason = "mean_reversion"\\n'
    '                elif EXIT_MODE == "hl_time":\\n'
    '                    if bars_held >= hl_bars:\\n'
    '                        exit_reason = "halflife_timeout"\\n'
    '\\n'
    '                # 3. Session-end forced exit at 15:28\\n'
    '                if exit_reason is None and bar_time >= FORCE_EXIT_TIME:\\n'
    '                    exit_reason = "session_end"\\n'"""

new_exit_logic_str = """    '                # Calculate intra-trade Gross PNL\\n'
    '                if is_long:\\n'
    '                    current_gross = (price - entry_price) * qty\\n'
    '                else:\\n'
    '                    current_gross = (entry_price - price) * qty\\n'
    '\\n'
    '                # 1. Hard Z>8 Stop Loss\\n'
    '                if abs(z) >= 8.0:\\n'
    '                    exit_reason = "hard_z8_stoploss"\\n'
    '                    suspended = True\\n'
    '                # 2. Early Profit Mean Reversion\\n'
    '                elif (entry_z >= Z_ENTRY and z <= 0.0) or (entry_z <= -Z_ENTRY and z >= 0.0):\\n'
    '                    exit_reason = "mean_reversion"\\n'
    '                # 3. Structural Check at Half-Life\\n'
    '                elif bars_held == hl_bars:\\n'
    '                    if current_gross < 0:\\n'
    '                        exit_reason = "hl_stoploss"\\n'
    '                        suspended = True\\n'
    '\\n'
    '                # 4. Session-end forced exit at 15:28\\n'
    '                if exit_reason is None and bar_time >= FORCE_EXIT_TIME:\\n'
    '                    exit_reason = "session_end"\\n'"""

code = code.replace(old_exit_logic_str, new_exit_logic_str)


# 4. Entry Logic (Suspension Check)
old_entry_str = """    '            # ── Entry logic ──\\n'
    '            if not in_trade and bar_time < FORCE_EXIT_TIME:\\n'
    '                # FIXED: Mirrored entry directional logic depending on A/B lagger\\n'"""

new_entry_str = """    '            # ── Entry logic ──\\n'
    '            if not in_trade and bar_time < FORCE_EXIT_TIME:\\n'
    '                if suspended:\\n'
    '                    if abs(z) < 1.0:\\n'
    '                        suspended = False\\n'
    '                    else:\\n'
    '                        continue # Skip taking trades until baseline returns\\n'
    '\\n'
    '                # FIXED: Mirrored entry directional logic depending on A/B lagger\\n'"""
code = code.replace(old_entry_str, new_entry_str)


# 5. Add gross_win_rate_pct to metrics
old_metrics = """    '            metrics = dict(\\n'
    '                total_trades=n_trades,\\n'
    '                win_rate_pct=100.0 * sum(1 for p in net_pnls if p > 0) / n_trades,\\n'
    '                total_gross_pnl=sum(gross_pnls),\\n'"""

new_metrics = """    '            metrics = dict(\\n'
    '                total_trades=n_trades,\\n'
    '                win_rate_pct=100.0 * sum(1 for p in net_pnls if p > 0) / n_trades,\\n'
    '                gross_win_rate_pct=100.0 * sum(1 for p in gross_pnls if p > 0) / n_trades,\\n'
    '                total_gross_pnl=sum(gross_pnls),\\n'"""
code = code.replace(old_metrics, new_metrics)


# 6. Replace Cell 8 Loop completely
cell8_start = code.find('# ── CELL 8: Run Sweep ───────────────────────────────────────────────────')
cell9_start = code.find('# ── CELL 9: Publish to Kaggle Dataset ────────────────────────────────────────')

new_cell_8 = """# ── CELL 8: Run Sweep ───────────────────────────────────────────────────
cells.append(md("## Cell 8 — Run Parameter Sweep\\n"))
cells.append(code(
    'Z_THRESHOLDS = [3.0, 4.0]\\n'
    '\\n'
    'import shutil\\n'
    'row = s3_df.iloc[0]\\n'
    '\\n'
    'results = []\\n'
    'for z_thresh in Z_THRESHOLDS:\\n'
    '    print(f"Running Z={z_thresh}...")\\n'
    '    res = backtest_pair(row, DB_PATH, z_thresh)\\n'
    '    res["Z_ENTRY"] = z_thresh\\n'
    '    results.append(res)\\n'
    '    \\n'
    '    # Save individual CSV\\n'
    '    df = pd.DataFrame([res])\\n'
    '    csv_name = f"/kaggle/working/results_z{int(z_thresh)}.csv"\\n'
    '    df.to_csv(csv_name, index=False)\\n'
    '    print(f"  -> Saved {csv_name} | Trades: {res.get(\\'total_trades\\', 0)}")\\n'
    '\\n'
    '# Also save a combined summary for convenience\\n'
    'summary_df = pd.DataFrame(results)\\n'
    'summary_df.to_csv("/kaggle/working/sweep_summary.csv", index=False)\\n'
    'print("Sweep Complete.")\\n'
))

"""

code = code[:cell8_start] + new_cell_8 + code[cell9_start:]

# Change dataset metadata in CELL 9
code = code.replace('"id"       : "utkarshpatelthefirst/pairs-z-sweep-experiment"', '"id"       : "utkarshpatelthefirst/pairs-z-stoploss-experiment"')
code = code.replace('"title"    : "Pairs Z-Score Sweep Experiment"', '"title"    : "Pairs Z-Score Stoploss Experiment"')

with open('/storage/emulated/0/Quant/_notebooks/stage3-experiment-z-stoploss/build_notebook.py', 'w') as f:
    f.write(code)

print("Done generating new build_notebook.py")
