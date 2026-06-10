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

add_markdown("# Stage 2 Validation: Approach 1 (Speed Limits: 30m, 60m, 120m)")

add_code("""
import os, glob
import sqlite3
import pandas as pd
import numpy as np

print("=== /kaggle/input contents ===")
hits = glob.glob('/kaggle/input/**/*.sqlite', recursive=True)
if not hits:
    raise FileNotFoundError("No .sqlite found under /kaggle/input")
DB_PATH = hits[0]
print(f"\\n✅ DB_PATH = {DB_PATH}")

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
# Approach 1: The Speed Limit Kalman Filter

def target_lambda(half_life_bars):
    # K = 1 - 0.5^(1 / tau)
    K = 1.0 - np.power(0.5, 1.0 / half_life_bars)
    # lambda = K^2 / (1 - K)
    lam = (K**2) / (1.0 - K)
    return lam

def run_speed_limit_kalman(ya, yb, timestamps, target_tau):
    T = len(ya)
    N = 2 
    
    # Use first 5 days (~1875 bars) for warm-up OLS
    warmup = min(1875, T//10)
    X_warm = np.column_stack([yb[:warmup], np.ones(warmup)])
    Y_warm = ya[:warmup]
    
    beta_hat = np.linalg.inv(X_warm.T @ X_warm) @ X_warm.T @ Y_warm
    res = Y_warm - X_warm @ beta_hat
    R_est = np.sum(res**2) / (warmup - N)
    
    # P0 based on OLS standard errors
    X_full = np.column_stack([yb, np.ones(T)])
    Sigma_X_inv = np.linalg.inv(X_warm.T @ X_warm / warmup)
    
    P0 = R_est * np.linalg.inv(X_warm.T @ X_warm)
    
    lam = target_lambda(target_tau)
    Q = lam * R_est * Sigma_X_inv
    R = R_est
    
    x_upd = np.zeros((T, N))
    x_u = beta_hat
    P_u = P0
    
    # 09:15 Gap Protocol Prep
    time_int = timestamps.hour * 100 + timestamps.minute
    is_open_bar = (time_int == 915)
    
    # Single Forward Pass (No EM)
    for t in range(T):
        x_p = x_u
        P_p = P_u + Q
        
        # Overnight Gap protocol
        if is_open_bar[t]:
            P_p *= 2.0  # double uncertainty at open
            
        H_t = X_full[t].reshape(1, N)
        v_t = ya[t] - H_t @ x_p
        S_t = H_t @ P_p @ H_t.T + R
        S_inv = np.linalg.inv(S_t)
        
        K_t = P_p @ H_t.T @ S_inv
        
        x_u = x_p + K_t @ v_t
        P_u = P_p - K_t @ H_t @ P_p
        
        x_upd[t] = x_u.flatten()
        
    spread = ya - np.sum(X_full * x_upd, axis=1)
    
    # Analyze the resulting spread
    s_t = spread[1:]
    s_t1 = spread[:-1]
    X_ar = np.column_stack([s_t1, np.ones(len(s_t1))])
    phi, _, _, _ = np.linalg.lstsq(X_ar, s_t, rcond=None)
    theta = phi[0]
    
    hl_actual = -np.log(2) / np.log(theta) if 0 < theta < 1 else np.inf
    zscore_variance = np.var(spread)
    
    return hl_actual, zscore_variance, Q[0,0]

""")

add_code("""
results = []
taus = [30, 60, 120]

for pair in top_pairs:
    sym_a, sym_b = pair
    df_pair = log_prices[[sym_a, sym_b]].dropna(how='any')
    ya = df_pair[sym_a].values
    yb = df_pair[sym_b].values
    times = df_pair.index
    
    for tau in taus:
        actual_hl, spread_var, q_beta = run_speed_limit_kalman(ya, yb, times, tau)
        
        results.append({
            "Pair": f"{sym_a}-{sym_b}",
            "Target_HL_Mins": tau,
            "Resulting_Spread_HL": actual_hl,
            "Spread_Variance": spread_var,
            "Q_Beta_Used": q_beta
        })

res_df = pd.DataFrame(results)
res_df.to_csv("approach1_speedlimit_results.csv", index=False)
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
os.makedirs("kaggle_stage2_run", exist_ok=True)
with open("kaggle_stage2_run/stage2-approach1-test.ipynb", "w") as f:
    json.dump(nb, f, indent=2)

meta = {
    "id": "utkarshpatelthefirst/stage-2-approach1-test-v2",
    "title": "Stage 2 Approach 1 Speed Limit v2",
    "code_file": "stage2-approach1-test.ipynb",
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

with open("kaggle_stage2_run/kernel-metadata.json", "w") as f:
    json.dump(meta, f, indent=2)

print("Created notebook for Approach 1 Speed Limits!")
