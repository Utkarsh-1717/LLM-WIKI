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

add_markdown("# Stage 2 Validation: EM Convergence (With Floating-Point Safety Net V5)")

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
""")

add_code("""
# The Top 5 pairs extracted from Stage 1
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
""")

add_code("""
# Stage 1 Data Cleansing (Strict Pairwise)
import gc

time_int = df['dt'].dt.hour * 100 + df['dt'].dt.minute
df_trading = df[(time_int >= 915) & (time_int <= 1529)].copy()

price_matrix = df_trading.pivot(index='dt', columns='symbol', values='close')
del df, df_trading
gc.collect()

log_prices = np.log(price_matrix)
""")

add_code("""
# Core EM and Kalman Math (Corrected RTS + Underflow Safety Net)
import numpy as np

def kalman_filter_em(ya, yb, timestamps, max_iter=100, tol=1e-5):
    T = len(ya)
    N = 2 
    
    # --- P0 Initialization via OLS ---
    X = np.column_stack([yb, np.ones(T)])
    Y = ya
    beta_hat = np.linalg.inv(X.T @ X) @ X.T @ Y
    residuals = Y - X @ beta_hat
    sigma2_ols = np.sum(residuals**2) / (T - N)
    P0 = sigma2_ols * np.linalg.inv(X.T @ X)
    
    x_init = beta_hat
    
    # Initialize Q and R safely
    Q = np.eye(N) * (sigma2_ols * 1e-4)
    R = sigma2_ols
    
    H_seq = X.reshape(T, 1, N)
    
    prev_loglik = -np.inf
    converged = False
    
    for iteration in range(max_iter):
        # --- FORWARD PASS ---
        x_upd = np.zeros((T, N))
        P_upd = np.zeros((T, N, N))
        x_pred = np.zeros((T, N))
        P_pred = np.zeros((T, N, N))
        loglik = 0.0
        
        x_u = x_init
        P_u = P0
        
        for t in range(T):
            # Predict
            x_p = x_u
            P_p = P_u + Q
            
            x_pred[t] = x_p
            P_pred[t] = P_p
            
            H_t = H_seq[t]
            v_t = Y[t] - H_t @ x_p
            S_t = H_t @ P_p @ H_t.T + R
            S_inv = np.linalg.inv(np.atleast_2d(S_t))
            
            K_t = P_p @ H_t.T @ S_inv
            
            x_u = x_p + K_t @ v_t
            P_u = P_p - K_t @ H_t @ P_p
            
            x_upd[t] = x_u
            P_upd[t] = P_u
            
            loglik -= 0.5 * (np.log(2 * np.pi) + np.log(S_t[0,0]) + (v_t**2)*S_inv[0,0])
            
        # Check convergence
        if abs(loglik - prev_loglik) < tol and iteration > 5:
            converged = True
            break
        prev_loglik = loglik
        
        # --- BACKWARD PASS (RTS Smoother) ---
        x_smooth = np.zeros((T, N))
        P_smooth = np.zeros((T, N, N))
        P_cross = np.zeros((T, N, N))
        
        x_smooth[-1] = x_upd[-1]
        P_smooth[-1] = P_upd[-1]
        
        for t in range(T-2, -1, -1):
            P_p_next = P_pred[t+1]
            J_t = P_upd[t] @ np.linalg.pinv(P_p_next)
            
            x_smooth[t] = x_upd[t] + J_t @ (x_smooth[t+1] - x_pred[t+1])
            P_smooth[t] = P_upd[t] + J_t @ (P_smooth[t+1] - P_p_next) @ J_t.T
            P_cross[t+1] = P_smooth[t+1] @ J_t.T
            
        # --- M-STEP ---
        dx = x_smooth[1:] - x_smooth[:-1]
        sum_dx_sq = np.einsum('ti,tj->ij', dx, dx)
        P_cross_T = np.transpose(P_cross[1:], axes=(0, 2, 1))
        sum_P = np.sum(P_smooth[1:] + P_smooth[:-1] - P_cross[1:] - P_cross_T, axis=0)
        
        Q = (sum_dx_sq + sum_P) / (T - 1)
        
        err = Y - np.einsum('ti,ti->t', H_seq[:, 0, :], x_smooth)
        H_P_H = np.einsum('tij,tjk,tik->t', H_seq, P_smooth, np.transpose(H_seq, axes=(0,2,1)))
        R = np.mean(err**2 + H_P_H)
        
        # --- THE SAFETY NET: Preventing Floating-Point Underflow ---
        # Matrix diagonals can hit negative e-18 due to floating point subtraction artifacts.
        # We enforce a strict floor to ensure matrix invertibility and positive logarithms.
        np.fill_diagonal(Q, np.maximum(Q.diagonal(), 1e-8))
        R = max(R, 1e-8)
        
    return converged, iteration, Q, R, x_smooth, x_upd
""")

add_code("""
# Execute on Top 5 Pairs
results = []

for pair in top_pairs:
    sym_a, sym_b = pair
    df_pair = log_prices[[sym_a, sym_b]].dropna(how='any')
    print(f"\\nProcessing {sym_a} vs {sym_b} | Valid Pairwise Bars: {len(df_pair)}")
    
    ya = df_pair[sym_a].values
    yb = df_pair[sym_b].values
    times = df_pair.index
    
    converged, iters, Q, R, x_smooth, x_upd = kalman_filter_em(ya, yb, times)
    
    H_m = np.column_stack([yb, np.ones(len(yb))])
    spread = ya - np.einsum("ti,ti->t", H_m, x_smooth)
    
    s_t = spread[1:]
    s_t1 = spread[:-1]
    X_ar = np.column_stack([s_t1, np.ones(len(s_t1))])
    phi, _, _, _ = np.linalg.lstsq(X_ar, s_t, rcond=None)
    theta = phi[0]
    
    if theta > 0 and theta < 1:
        hl = -np.log(2) / np.log(theta)
    else:
        hl = np.inf
        
    print(f"Converged: {converged} in {iters} iterations | Half-life: {hl:.2f} mins")
    
    results.append({
        "symbol_a": sym_a,
        "symbol_b": sym_b,
        "converged": converged,
        "iterations": iters,
        "half_life_min": hl,
        "Q_beta": Q[0,0],
        "Q_alpha": Q[1,1],
        "R": R
    })

res_df = pd.DataFrame(results)
res_df.to_csv("stage2_top5_validation.csv", index=False)
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
with open("kaggle_stage2_run/stage2-kalman-validation.ipynb", "w") as f:
    json.dump(nb, f, indent=2)

meta = {
    "id": "utkarshpatelthefirst/stage-2-kalman-validation-final-v5",
    "title": "Stage 2 Kalman Validation Final V5",
    "code_file": "stage2-kalman-validation.ipynb",
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

print("Created notebook v5 inside kaggle_stage2_run/")
