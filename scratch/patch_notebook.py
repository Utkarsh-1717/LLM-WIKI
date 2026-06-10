import nbformat
import re

def patch_notebook():
    nb_path = '/storage/emulated/0/Quant/LLM-WIKI/Soul/Master_Pairs_Trading_Soul.ipynb'
    with open(nb_path, 'r') as f:
        nb = nbformat.read(f, as_version=4)

    # 1. Patch Stage 2 Cell (Cell index 4)
    c2 = nb.cells[4].source
    
    # Relax P0 initialization
    c2 = re.sub(
        r'P0 = 10\.0 \* sigma2 \* XtX_inv',
        r'P0 = np.eye(2) * 1e-3',
        c2
    )
    
    # Increase EM iterations
    c2 = re.sub(
        r'for itr in range\(15\):  # Max 15 iterations',
        r'for itr in range(50):  # Max 50 iterations',
        c2
    )
    
    # Change Q_n clipping floor
    c2 = re.sub(
        r'Q_n = np\.clip\(Q_n, 1e-12, None\)',
        r'Q_n = np.clip(Q_n, 1e-7, None)',
        c2
    )
    
    nb.cells[4].source = c2

    # 2. Patch Stage 3A Cell (Cell index 6)
    c3a = nb.cells[6].source
    
    # Remove tradeable filter
    c3a = re.sub(
        r"valid_pairs = s2_results\[s2_results\['tradeable'\] == True\]\.copy\(\)\.reset_index\(drop=True\)",
        r"valid_pairs = s2_results[s2_results['skipped'] == False].copy().reset_index(drop=True)",
        c3a
    )
    
    # Rewrite run_backtest_numba
    # Find the function definition
    pattern_numba = r'@njit\ndef run_backtest_numba\(.*?return total_profit, trade_count, win_rate\n'
    
    new_numba = """@njit
def run_backtest_numba(prices, z_scores, times_in_min, half_life_bars, lagger_is_a, z_entry, z_sl, hl_stop):
    T = len(prices)
    in_trade = False
    pos = 0 # 1: Long, -1: Short
    entry_idx = 0
    entry_price = 0.0
    entry_z = 0.0
    frozen = False
    
    total_profit = 0.0
    trade_count = 0
    win_count = 0
    
    exit_mr_count = 0
    exit_sl_count = 0
    exit_hl_count = 0
    exit_session_count = 0
    profit_sum_wins = 0.0
    loss_sum_losses = 0.0
    
    for t in range(T):
        z = z_scores[t]
        if np.isnan(z):
            continue
            
        p = prices[t]
        tm = times_in_min[t]
        
        if frozen:
            if abs(z) < z_entry / 2.0:
                frozen = False
                
        if in_trade:
            bars_held = t - entry_idx
            exit_reason = 0
            
            if entry_z >= z_entry and z <= 0.0:
                exit_reason = 1
            elif entry_z <= -z_entry and z >= 0.0:
                exit_reason = 1
                
            if exit_reason == 0 and z_sl > 0.0 and abs(z) >= z_sl:
                exit_reason = 2
                frozen = True
                
            if exit_reason == 0 and hl_stop and bars_held == half_life_bars:
                pnl = (p - entry_price) * pos
                if pnl < 0.0:
                    exit_reason = 3
                    frozen = True
                    
            if exit_reason == 0 and tm >= 928:
                exit_reason = 4
                
            if exit_reason > 0:
                pnl = (p - entry_price) * pos
                total_profit += pnl
                trade_count += 1
                if pnl > 0.0:
                    win_count += 1
                    profit_sum_wins += pnl
                else:
                    loss_sum_losses += pnl
                    
                if exit_reason == 1: exit_mr_count += 1
                elif exit_reason == 2: exit_sl_count += 1
                elif exit_reason == 3: exit_hl_count += 1
                elif exit_reason == 4: exit_session_count += 1
                
                in_trade = False
                pos = 0
                continue
                
        if not in_trade and not frozen and tm < 928:
            if z >= z_entry:
                pos = -1 if lagger_is_a else 1
                in_trade = True
                entry_idx = t
                entry_price = p
                entry_z = z
            elif z <= -z_entry:
                pos = 1 if lagger_is_a else -1
                in_trade = True
                entry_idx = t
                entry_price = p
                entry_z = z
                
    if in_trade:
        pnl = (prices[T-1] - entry_price) * pos
        total_profit += pnl
        trade_count += 1
        if pnl > 0.0:
            win_count += 1
            profit_sum_wins += pnl
        else:
            loss_sum_losses += pnl
        exit_session_count += 1
            
    win_rate = win_count / trade_count if trade_count > 0 else 0.0
    loss_count = trade_count - win_count
    avg_points_profit = profit_sum_wins / win_count if win_count > 0 else 0.0
    avg_points_loss = loss_sum_losses / loss_count if loss_count > 0 else 0.0
    
    return total_profit, trade_count, win_rate, exit_mr_count, exit_sl_count, exit_hl_count, exit_session_count, avg_points_profit, avg_points_loss
"""
    
    c3a = re.sub(pattern_numba, new_numba, c3a, flags=re.DOTALL)
    
    # Update best_config initialization
    c3a = re.sub(
        r'best_config = \(2\.0, 0\.0, False\) # \(z_entry, z_sl, hl_stop\)',
        r'best_config = (2.0, 0.0, False)\n    best_stats = (0,0,0,0,0.0,0.0)',
        c3a
    )
    
    # Update grid sweep
    pattern_sweep = r'        # Stop loss sweep.*?        # 1\. No Stop Loss.*?                best_config = \(z_ent, z_s, False\)'
    
    new_sweep = """        # Stop loss sweep
        # 1. No Stop Loss
        prof, trades, wr, e_mr, e_sl, e_hl, e_sess, avg_p_win, avg_p_loss = run_backtest_numba(prices_lagger, z_scores_is, times_in_min_is, hl_bars, lagger_is_a, z_ent, 0.0, False)
        if prof > best_profit or (prof == best_profit and trades > best_trade_count):
            best_profit = prof; best_trade_count = trades; best_win_rate = wr
            best_config = (z_ent, 0.0, False)
            best_stats = (e_mr, e_sl, e_hl, e_sess, avg_p_win, avg_p_loss)
            
        # 2. Half-life negative exit
        prof, trades, wr, e_mr, e_sl, e_hl, e_sess, avg_p_win, avg_p_loss = run_backtest_numba(prices_lagger, z_scores_is, times_in_min_is, hl_bars, lagger_is_a, z_ent, 0.0, True)
        if prof > best_profit or (prof == best_profit and trades > best_trade_count):
            best_profit = prof; best_trade_count = trades; best_win_rate = wr
            best_config = (z_ent, 0.0, True)
            best_stats = (e_mr, e_sl, e_hl, e_sess, avg_p_win, avg_p_loss)
            
        # 3. Z_sl exit
        z_sl_vals = np.arange(2.5, 16.5, 0.5)
        for z_s in z_sl_vals:
            if z_s <= z_ent:
                continue
            prof, trades, wr, e_mr, e_sl, e_hl, e_sess, avg_p_win, avg_p_loss = run_backtest_numba(prices_lagger, z_scores_is, times_in_min_is, hl_bars, lagger_is_a, z_ent, z_s, False)
            if prof > best_profit or (prof == best_profit and trades > best_trade_count):
                best_profit = prof; best_trade_count = trades; best_win_rate = wr
                best_config = (z_ent, z_s, False)
                best_stats = (e_mr, e_sl, e_hl, e_sess, avg_p_win, avg_p_loss)"""
    
    c3a = re.sub(pattern_sweep, new_sweep, c3a, flags=re.DOTALL)
    
    # Update optimized_rows.append
    pattern_append = r'    optimized_rows\.append\(\{\n.*?"lagger": lagger,\n    \}\)'
    
    new_append = """    optimized_rows.append({
        "symbol_a": sym_a,
        "symbol_b": sym_b,
        "best_z_entry": best_config[0],
        "best_z_sl": best_config[1],
        "best_hl_stop": best_config[2],
        "gross_profit": best_profit,
        "trade_count": best_trade_count,
        "win_rate": best_win_rate,
        "lagger": lagger,
        "exit_mr_count": best_stats[0],
        "exit_sl_count": best_stats[1],
        "exit_hl_count": best_stats[2],
        "exit_session_count": best_stats[3],
        "avg_points_profit": best_stats[4],
        "avg_points_loss": best_stats[5],
    })"""
    
    c3a = re.sub(pattern_append, new_append, c3a, flags=re.DOTALL)
    
    nb.cells[6].source = c3a

    with open(nb_path, 'w') as f:
        nbformat.write(nb, f)
    
    print("Notebook successfully patched!")

if __name__ == '__main__':
    patch_notebook()
