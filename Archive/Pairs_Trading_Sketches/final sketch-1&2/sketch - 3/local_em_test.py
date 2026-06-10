import sqlite3
import pandas as pd
import numpy as np

# Single pair test to save local memory
top_pairs = [("PFC", "RECLTD")]

symbols_to_load = ["PFC", "RECLTD"]

print("Loading data for symbols:", symbols_to_load)

# Assuming master db is at /storage/emulated/0/Quant/LLM-WIKI/Master-Data-1min.sqlite
# Or let's search for it.
import glob
hits = glob.glob('/storage/emulated/0/Quant/LLM-WIKI/**/*.sqlite', recursive=True)
DB_PATH = [h for h in hits if "Master-Data-1min.sqlite" in h][0]

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

def kalman_filter_em(ya, yb, timestamps, max_iter=100, tol=1e-5):
    T = len(ya)
    N = 2
    
    X = np.column_stack([yb, np.ones(T)])
    Y = ya
    beta_hat = np.linalg.inv(X.T @ X) @ X.T @ Y
    residuals = Y - X @ beta_hat
    sigma2_ols = np.sum(residuals**2) / (T - N)
    P0 = sigma2_ols * np.linalg.inv(X.T @ X)
    
    x_init = beta_hat
    
    Q = np.eye(N) * (sigma2_ols * 1e-4)
    R = sigma2_ols
    
    H_seq = X.reshape(T, 1, N)
    
    prev_loglik = -np.inf
    converged = False
    
    for iteration in range(max_iter):
        x_upd = np.zeros((T, N))
        P_upd = np.zeros((T, N, N))
        x_pred = np.zeros((T, N))
        P_pred = np.zeros((T, N, N))
        loglik = 0.0
        
        x_u = x_init
        P_u = P0
        
        for t in range(T):
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
            
        if abs(loglik - prev_loglik) < tol and iteration > 5:
            converged = True
            break
        prev_loglik = loglik
        print(f"Iter {iteration}: LogLik={loglik}, Q_beta={Q[0,0]:.2e}")
        
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
            P_cross[t+1] = J_t @ P_smooth[t+1]
            
        dx = x_smooth[1:] - x_smooth[:-1]
        sum_dx_sq = np.einsum('ti,tj->ij', dx, dx)
        P_cross_T = np.transpose(P_cross[1:], axes=(0, 2, 1))
        sum_P = np.sum(P_smooth[1:] + P_smooth[:-1] - P_cross[1:] - P_cross_T, axis=0)
        
        Q = (sum_dx_sq + sum_P) / (T - 1)
        
        err = Y - np.einsum('ti,ti->t', H_seq[:, 0, :], x_smooth)
        H_P_H = np.einsum('tij,tjk,tik->t', H_seq, P_smooth, np.transpose(H_seq, axes=(0,2,1)))
        R = np.mean(err**2 + H_P_H)
        
    return converged, iteration, Q, R, x_smooth, x_upd

sym_a, sym_b = "PFC", "RECLTD"
df_pair = log_prices[[sym_a, sym_b]].dropna(how='any')
print(f"\\nProcessing {sym_a} vs {sym_b} | Valid Pairwise Bars: {len(df_pair)}")
ya = df_pair[sym_a].values
yb = df_pair[sym_b].values
times = df_pair.index

converged, iters, Q, R, x_smooth, x_upd = kalman_filter_em(ya, yb, times, max_iter=20)
print(f"Converged: {converged} in {iters} iterations")
print(f"Final Q: \\n{Q}")
