import json
import uuid

def generate_id():
    return str(uuid.uuid4())[:8]

cells = []

def add_markdown(text):
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "id": generate_id(),
        "source": [line + "\n" for line in text.split("\n")]
    })

def add_code(text):
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "id": generate_id(),
        "outputs": [],
        "source": [line + "\n" for line in text.split("\n")]
    })

add_markdown("# Stage 3: Backtest Engine (Approach 1 vs Approach 2)")

add_code("""
import os, glob
import sqlite3
import pandas as pd
import numpy as np

print("=== Loading DB ===")
hits = glob.glob('/kaggle/input/**/*.sqlite', recursive=True)
if not hits:
    raise FileNotFoundError("No .sqlite found under /kaggle/input")
DB_PATH = hits[0]

top_pairs = [
    ("PFC", "RECLTD"),
    ("BDL", "MAZDOCK"),
    ("GRSE", "MAZDOCK"),
    ("BANKBARODA", "CANBK"),
    ("BPCL", "HINDPETRO")
]

symbols_to_load = list(set([sym for pair in top_pairs for sym in pair]))

con = sqlite3.connect(DB_PATH)
placeholders = ",".join(["?"] * len(symbols_to_load))
query = f"SELECT symbol, timestamp, close FROM ohlcv_1min WHERE symbol IN ({placeholders}) ORDER BY timestamp"
df = pd.read_sql(query, con, params=symbols_to_load)
con.close()

df['dt'] = pd.to_datetime(df['timestamp'], unit='s', utc=True).dt.tz_convert('Asia/Kolkata')
time_int = df['dt'].dt.hour * 100 + df['dt'].dt.minute
df_trading = df[(time_int >= 915) & (time_int <= 1529)].copy()

price_matrix = df_trading.pivot(index='dt', columns='symbol', values='close')
del df, df_trading
import gc; gc.collect()

log_prices = np.log(price_matrix)
""")

add_code("""
# Utility Functions
def target_lambda(half_life_bars):
    K = 1.0 - np.power(0.5, 1.0 / half_life_bars)
    return (K**2) / (1.0 - K)

def calculate_worst_case_hl(ya, yb, num_chunks=4):
    chunk_size = len(ya) // num_chunks
    half_lives = []
    for i in range(num_chunks):
        start_idx = i * chunk_size
        end_idx = (i + 1) * chunk_size if i < num_chunks - 1 else len(ya)
        
        y_chunk = ya[start_idx:end_idx]
        x_chunk = yb[start_idx:end_idx]
        
        X_mat = np.column_stack([x_chunk, np.ones(len(x_chunk))])
        beta_hat, _, _, _ = np.linalg.lstsq(X_mat, y_chunk, rcond=None)
        
        spread = y_chunk - (X_mat @ beta_hat)
        s_t = spread[1:]
        s_t1 = spread[:-1]
        
        X_ar = np.column_stack([s_t1, np.ones(len(s_t1))])
        phi_hat, _, _, _ = np.linalg.lstsq(X_ar, s_t, rcond=None)
        phi = phi_hat[0]
        
        if 0 < phi < 1:
            half_lives.append(-np.log(2) / np.log(phi))
    
    return np.max(half_lives) if half_lives else np.inf

def run_kalman_filter(ya, yb, timestamps, target_tau):
    T = len(ya)
    N = 2 
    warmup = min(1875, T//10)
    
    X_warm = np.column_stack([yb[:warmup], np.ones(warmup)])
    Y_warm = ya[:warmup]
    beta_hat = np.linalg.inv(X_warm.T @ X_warm) @ X_warm.T @ Y_warm
    res = Y_warm - X_warm @ beta_hat
    R_est = np.sum(res**2) / (warmup - N)
    
    X_full = np.column_stack([yb, np.ones(T)])
    Sigma_X_inv = np.linalg.inv(X_warm.T @ X_warm / warmup)
    P0 = R_est * np.linalg.inv(X_warm.T @ X_warm)
    
    lam = target_lambda(target_tau)
    Q = lam * R_est * Sigma_X_inv
    R = R_est
    
    x_upd = np.zeros((T, N))
    x_u = beta_hat
    P_u = P0
    
    time_int = timestamps.hour * 100 + timestamps.minute
    is_open_bar = (time_int == 915)
    
    for t in range(T):
        x_p = x_u
        P_p = P_u + Q
        
        if is_open_bar[t]:
            P_p *= 2.0  # 09:15 Gap multiplier
            
        H_t = X_full[t].reshape(1, N)
        v_t = ya[t] - H_t @ x_p
        S_t = H_t @ P_p @ H_t.T + R
        S_inv = np.linalg.inv(S_t)
        
        K_t = P_p @ H_t.T @ S_inv
        x_u = x_p + K_t @ v_t
        P_u = P_p - K_t @ H_t @ P_p
        
        x_upd[t] = x_u.flatten()
        
    return ya - np.sum(X_full * x_upd, axis=1)

""")

add_code("""
# Backtest Engine
def run_backtest(spread, raw_lagger_prices, timestamps):
    # Calculate Z-Score using a 375-bar (1 Day) rolling window
    spread_series = pd.Series(spread)
    rolling_mean = spread_series.rolling(window=375).mean()
    rolling_std = spread_series.rolling(window=375).std()
    z_scores = ((spread_series - rolling_mean) / rolling_std).values
    
    base_capital = 10000.0
    leverage = 5.0
    pos_size = base_capital * leverage
    friction_pct = 0.0005 # 0.05% per leg
    
    cash = base_capital
    pos_qty = 0
    pos_type = 0 # 1 for Long, -1 for Short
    entry_price = 0.0
    
    trade_log = []
    
    time_int = timestamps.hour * 100 + timestamps.minute
    is_eod = (time_int == 1515)
    
    for t in range(375, len(spread)):
        z = z_scores[t]
        price = raw_lagger_prices[t]
        
        if np.isnan(z):
            continue
            
        # Exit Logic
        if pos_qty > 0:
            if is_eod[t] or (pos_type == 1 and z >= 0) or (pos_type == -1 and z <= 0):
                exit_val = pos_qty * price
                friction = exit_val * friction_pct
                
                if pos_type == 1:
                    gross_pnl = (price - entry_price) * pos_qty
                else:
                    gross_pnl = (entry_price - price) * pos_qty
                    
                net_pnl = gross_pnl - friction
                cash += net_pnl
                
                trade_log.append({
                    "exit_time": timestamps[t],
                    "type": "LONG" if pos_type == 1 else "SHORT",
                    "gross_pnl": gross_pnl,
                    "net_pnl": net_pnl,
                    "reason": "EOD" if is_eod[t] else "MEAN_REV"
                })
                
                pos_qty = 0
                pos_type = 0
                
        # Entry Logic (Only if no open position and NOT EOD)
        if pos_qty == 0 and not is_eod[t]:
            if z <= -2.0: # Long Lagger
                qty = int(pos_size // price)
                if qty > 0:
                    entry_price = price
                    pos_qty = qty
                    pos_type = 1
                    cash -= (qty * price) * friction_pct
            elif z >= 2.0: # Short Lagger
                qty = int(pos_size // price)
                if qty > 0:
                    entry_price = price
                    pos_qty = qty
                    pos_type = -1
                    cash -= (qty * price) * friction_pct
                    
    total_trades = len(trade_log)
    win_rate = sum(1 for tr in trade_log if tr['net_pnl'] > 0) / total_trades if total_trades > 0 else 0
    final_pnl = cash - base_capital
    return final_pnl, total_trades, win_rate
""")

add_code("""
results = []

for pair in top_pairs:
    sym_a, sym_b = pair  # sym_a is lagger (y), sym_b is leader (x)
    df_pair = log_prices[[sym_a, sym_b]].dropna(how='any')
    ya = df_pair[sym_a].values
    yb = df_pair[sym_b].values
    times = df_pair.index
    
    raw_lagger = price_matrix[sym_a].loc[times].values
    
    print(f"\\nProcessing {sym_a}-{sym_b}...")
    
    # Approach 1: 120m Speed Limit
    spread_app1 = run_kalman_filter(ya, yb, times, target_tau=120)
    pnl_1, trades_1, wr_1 = run_backtest(spread_app1, raw_lagger, times)
    
    # Approach 2: True OU Worst-Case
    worst_hl = calculate_worst_case_hl(ya, yb, num_chunks=4)
    target_tau_2 = worst_hl * 2.0 if worst_hl != np.inf else 1000.0
    spread_app2 = run_kalman_filter(ya, yb, times, target_tau=target_tau_2)
    pnl_2, trades_2, wr_2 = run_backtest(spread_app2, raw_lagger, times)
    
    results.append({
        "Pair": f"{sym_a}-{sym_b}",
        "App1_Target_Lag": 120,
        "App1_Net_PnL": round(pnl_1, 2),
        "App1_Trades": trades_1,
        "App1_WinRate": round(wr_1 * 100, 2),
        "App2_Target_Lag": round(target_tau_2, 2),
        "App2_Net_PnL": round(pnl_2, 2),
        "App2_Trades": trades_2,
        "App2_WinRate": round(wr_2 * 100, 2)
    })
    print(f"  App 1 (120m) -> PnL: ₹{pnl_1:.2f} | Trades: {trades_1}")
    print(f"  App 2 ({target_tau_2:.1f}m) -> PnL: ₹{pnl_2:.2f} | Trades: {trades_2}")

res_df = pd.DataFrame(results)
res_df.to_csv("stage3_backtest_results.csv", index=False)
display(res_df)
""")

nb = {
    "cells": cells,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "codemirror_mode": {"name": "ipython", "version": 3},
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "nbconvert_exporter": "python",
            "pygments_lexer": "ipython3",
            "version": "3.10.12"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 5
}

import os
os.makedirs("kaggle_stage3_run", exist_ok=True)
with open("kaggle_stage3_run/stage3-backtest-engine.ipynb", "w") as f:
    json.dump(nb, f, indent=2)

meta = {
    "id": "utkarshpatelthefirst/stage-3-backtest-engine",
    "title": "Stage 3 Backtest Engine",
    "code_file": "stage3-backtest-engine.ipynb",
    "language": "python",
    "kernel_type": "notebook",
    "is_private": "true",
    "enable_gpu": "false",
    "enable_internet": "true",
    "dataset_sources": ["utkarshpatelthefirst/master-data-1min-db"],
    "competition_sources": [],
    "kernel_sources": [],
    "model_sources": []
}

with open("kaggle_stage3_run/kernel-metadata.json", "w") as f:
    json.dump(meta, f, indent=2)

print("Created Stage 3 Backtest Engine Notebook!")
