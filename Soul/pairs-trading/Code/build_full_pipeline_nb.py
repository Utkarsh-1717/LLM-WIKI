import json, uuid, os

def gen_id():
    return str(uuid.uuid4())[:8]

cells = []

def md(text):
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "id": gen_id(),
        "source": [line + "\n" for line in text.strip().split("\n")]
    })

def code(text):
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "id": gen_id(),
        "outputs": [],
        "source": [line + "\n" for line in text.strip().split("\n")]
    })

# ── TITLE
md("""# Full Pipeline: Pairs Trading (Stage 1 to 3)
**Strategy**: NSE Intraday Pairs Trading — Single-Sided Lagger  
**Stages**:
1. Pearson Correlation Screening
2. OU Chunked Q Calibration & Chunk Sweep
3. Execution Engine (3 Q Methods Head-to-Head)
""")

# ── IMPORTS & PATH DISCOVERY
code("""
import os, glob, gc, json, shutil
import sqlite3
import pandas as pd
import numpy as np
from scipy.stats import t as t_dist

print("=== /kaggle/input contents ===")
for root, dirs, files in os.walk('/kaggle/input'):
    for f in files:
        fpath = os.path.join(root, f)
        print(f"  {fpath}  ({os.path.getsize(fpath)/(1024**3):.2f} GB)")

hits = glob.glob('/kaggle/input/**/*.sqlite', recursive=True)
if not hits:
    raise FileNotFoundError("No .sqlite found under /kaggle/input")
DB_PATH = hits[0]
print(f"\\n✅ DB_PATH = {DB_PATH}")
""")

# ── LOAD ALL DATA 
code("""
print("=== Loading All DB Data ===")
con = sqlite3.connect(DB_PATH)
df = pd.read_sql("SELECT symbol, timestamp, close FROM ohlcv_1min ORDER BY timestamp", con)
con.close()

df['dt'] = pd.to_datetime(df['timestamp'], unit='s', utc=True).dt.tz_convert('Asia/Kolkata')
time_int = df['dt'].dt.hour * 100 + df['dt'].dt.minute
df_trading = df[(time_int >= 915) & (time_int <= 1529)].copy()
del df; gc.collect()

print("Pivoting to price matrix...")
price_matrix = df_trading.pivot(index='dt', columns='symbol', values='close')
del df_trading; gc.collect()

log_prices = np.log(price_matrix)
print(f"Price matrix: {price_matrix.shape}")
""")

# ── STAGE 1
md("""## Stage 1 — Pearson Correlation Screening
**Output**: `pairs_all.csv`, `pairs_top500.csv`
""")
code("""
log_returns = log_prices - log_prices.shift(1)
dates_arr = np.array(price_matrix.index.date)
session_open_mask = np.concatenate([[True], dates_arr[1:] != dates_arr[:-1]])
log_returns.iloc[session_open_mask] = np.nan

print("Computing pairwise Pearson correlation...")
corr_df = log_returns.corr(method='pearson')

symbols = corr_df.columns.tolist()
rows = []
for i in range(len(symbols)):
    for j in range(i + 1, len(symbols)):
        rho = corr_df.iloc[i, j]
        if np.isnan(rho): continue
        n_pair = log_returns[[symbols[i], symbols[j]]].dropna().shape[0]
        if n_pair < 5000: continue
        t_stat = rho * np.sqrt((n_pair - 2) / max(1.0 - rho**2, 1e-12))
        p_val  = 2 * t_dist.sf(abs(t_stat), df=n_pair - 2)
        if p_val >= 0.05: continue
        rows.append({
            "symbol_a": symbols[i], "symbol_b": symbols[j],
            "pearson_rho": round(rho, 6), "t_stat": round(t_stat, 4),
            "p_value": round(p_val, 8), "n_obs": n_pair,
        })

pairs_df = pd.DataFrame(rows).sort_values("pearson_rho", ascending=False).reset_index(drop=True)
pairs_df["rank"] = pairs_df.index + 1

pairs_df.to_csv("pairs_all.csv", index=False)
pairs_df.head(500).to_csv("pairs_top500.csv", index=False)
print("Saved Stage 1 outputs.")

# Define TOP 500 for Stage 2 & 3 dynamically
top500 = pairs_df.head(500)
TOP_PAIRS = list(zip(top500["symbol_a"], top500["symbol_b"]))
print(f"\\nUsing Top {len(TOP_PAIRS)} Production Pairs for Stage 2 & 3...")
""")

# ── STAGE 2
md("""## Stage 2 — OU Chunked Q Calibration & Chunk Sweep
**Output**: `stage2_ou_calibration.csv`, `stage2_chunk_sweep.csv`, `stage2_stability_summary.csv`
""")
code("""
NUM_CHUNKS = 4
CHUNK_SWEEP = [4, 6, 8, 10]
WARMUP_BARS = 1875

def find_medoid(half_lives):
    hls = np.array(half_lives)
    if len(hls) == 1: return hls[0]
    distances = np.array([np.sum(np.abs(hl - hls)) for hl in hls])
    return hls[np.argmin(distances)]

def extract_ou_distribution(ya, yb, num_chunks):
    chunk_size = len(ya) // num_chunks
    valid_hls = []
    for i in range(num_chunks):
        start = i * chunk_size
        end = (i + 1) * chunk_size if i < num_chunks - 1 else len(ya)
        y_c, x_c = ya[start:end], yb[start:end]
        X_mat = np.column_stack([x_c, np.ones(len(x_c))])
        beta, _, _, _ = np.linalg.lstsq(X_mat, y_c, rcond=None)
        spread = y_c - X_mat @ beta
        X_ar = np.column_stack([spread[:-1], np.ones(len(spread) - 1)])
        phi_res, _, _, _ = np.linalg.lstsq(X_ar, spread[1:], rcond=None)
        phi = phi_res[0]
        if 0 < phi < 1:
            valid_hls.append(-np.log(2) / np.log(phi))
    if not valid_hls: return None
    return {
        "all_hls": valid_hls, "n_valid": len(valid_hls),
        "hl_min": float(np.min(valid_hls)), "hl_max": float(np.max(valid_hls)),
        "hl_medoid": float(find_medoid(valid_hls)), "hl_median": float(np.median(valid_hls)),
        "hl_mean": float(np.mean(valid_hls)), "hl_std": float(np.std(valid_hls)),
    }

def compute_q_from_tau(target_tau, ya_warmup, yb_warmup):
    n = len(ya_warmup)
    X_w = np.column_stack([yb_warmup, np.ones(n)])
    beta0 = np.linalg.lstsq(X_w, ya_warmup, rcond=None)[0]
    res = ya_warmup - X_w @ beta0
    R_est = np.sum(res ** 2) / (n - 2)
    K_factor = 1.0 - np.power(0.5, 1.0 / target_tau)
    lam = (K_factor ** 2) / (1.0 - K_factor)
    Sigma_X_inv = np.linalg.inv(X_w.T @ X_w / n)
    Q = lam * R_est * Sigma_X_inv
    P0 = R_est * np.linalg.inv(X_w.T @ X_w)
    return Q, P0, R_est

results_st2 = []
for pair in TOP_PAIRS:
    sym_a, sym_b = pair
    df_pair = log_prices[[sym_a, sym_b]].dropna(how='any')
    ya, yb = df_pair[sym_a].values, df_pair[sym_b].values
    ou = extract_ou_distribution(ya, yb, NUM_CHUNKS)
    if ou is None: continue
    warmup_n = min(WARMUP_BARS, len(ya) // 10)
    tau_A = ou["hl_max"] * 2.0
    Q_A, _, R_A = compute_q_from_tau(tau_A, ya[:warmup_n], yb[:warmup_n])
    tau_B = ou["hl_medoid"] * 2.0
    Q_B, _, _ = compute_q_from_tau(tau_B, ya[:warmup_n], yb[:warmup_n])
    results_st2.append({
        "pair": f"{sym_a}-{sym_b}", "num_chunks": NUM_CHUNKS,
        "chunk_half_lives": str([round(h, 2) for h in ou["all_hls"]]),
        "hl_max": round(ou["hl_max"], 2), "hl_medoid": round(ou["hl_medoid"], 2),
        "target_tau_worst_case": round(tau_A, 2), "target_tau_dominant": round(tau_B, 2),
        "Q_beta_worst_case": round(Q_A[0, 0], 10), "Q_beta_dominant": round(Q_B[0, 0], 10),
    })

pd.DataFrame(results_st2).to_csv("stage2_ou_calibration.csv", index=False)

sweep_rows = []
for num_c in CHUNK_SWEEP:
    for sym_a, sym_b in TOP_PAIRS:
        df_pair = log_prices[[sym_a, sym_b]].dropna(how='any')
        ou = extract_ou_distribution(df_pair[sym_a].values, df_pair[sym_b].values, num_c)
        if ou: sweep_rows.append({"pair": f"{sym_a}-{sym_b}", "num_chunks": num_c, "hl_max": round(ou["hl_max"], 2), "hl_medoid": round(ou["hl_medoid"], 2), "hl_std": round(ou["hl_std"], 2)})
sweep_df = pd.DataFrame(sweep_rows)
sweep_df.to_csv("stage2_chunk_sweep.csv", index=False)

stability = sweep_df.groupby("pair").agg(hl_max_std=("hl_max", "std"), hl_medoid_std=("hl_medoid", "std")).round(2).reset_index()
stability["regime_stable"] = stability["hl_max_std"] < 20.0
stability.to_csv("stage2_stability_summary.csv", index=False)
print("Saved Stage 2 outputs.")
""")

# ── STAGE 3
md("""## Stage 3 — Execution Engine
**Output**: `production_engine_results.csv`
""")
code("""
ZSCORE_WINDOW = 7500
Z_ENTRY = 2.0
EOD_EXIT_TIME = 1515
BASE_CAPITAL = 10_000.0
LEVERAGE = 5.0
POS_SIZE = BASE_CAPITAL * LEVERAGE
FRICTION_PCT = 0.0005
FIXED_SPEED_LIMIT_TAU = 120.0

def run_kalman_filter(ya, yb, timestamps, Q, P0, R):
    T = len(ya)
    X_full = np.column_stack([yb, np.ones(T)])
    x_upd = np.linalg.lstsq(X_full[:min(100, T)], ya[:min(100, T)], rcond=None)[0]
    P_upd = P0.copy()
    time_int = timestamps.hour * 100 + timestamps.minute
    is_open = (time_int == 915)
    spread = np.zeros(T)
    for t in range(T):
        x_p = x_upd
        P_p = P_upd + Q
        if is_open[t]: P_p *= 2.0
        H_t = X_full[t]
        v_t = ya[t] - H_t @ x_p
        S_t = H_t @ P_p @ H_t + R
        K_t = P_p @ H_t / S_t
        x_upd = x_p + K_t * v_t
        P_upd = P_p - np.outer(K_t, H_t) @ P_p
        spread[t] = v_t
    return spread

def run_backtest(spread, raw_prices, timestamps):
    spread_s = pd.Series(spread)
    roll_mean = spread_s.rolling(ZSCORE_WINDOW).mean()
    roll_std  = spread_s.rolling(ZSCORE_WINDOW).std()
    z_scores  = ((spread_s - roll_mean) / roll_std.replace(0, np.nan)).values
    time_int = timestamps.hour * 100 + timestamps.minute
    is_eod   = (time_int == EOD_EXIT_TIME)
    cash, pos_qty, pos_type, entry_px = BASE_CAPITAL, 0, 0, 0.0
    trade_log = []
    for t in range(ZSCORE_WINDOW, len(spread)):
        z, price = z_scores[t], raw_prices[t]
        if np.isnan(z) or np.isnan(price) or price <= 0: continue
        if pos_qty > 0:
            if is_eod[t] or (pos_type == 1 and z >= 0) or (pos_type == -1 and z <= 0):
                gross = (price - entry_px) * pos_qty if pos_type == 1 else (entry_px - price) * pos_qty
                net = gross - (pos_qty * price) * FRICTION_PCT
                cash += net
                trade_log.append({"net_pnl": net, "reason": "EOD" if is_eod[t] else "MEAN_REV"})
                pos_qty, pos_type = 0, 0
        if pos_qty == 0 and not is_eod[t]:
            if z <= -Z_ENTRY or z >= Z_ENTRY:
                qty = int(POS_SIZE // price)
                if qty > 0:
                    entry_px, pos_qty = price, qty
                    pos_type = 1 if z <= -Z_ENTRY else -1
                    cash -= (qty * price) * FRICTION_PCT
    total_trades = len(trade_log)
    win_rate = sum(1 for tr in trade_log if tr["net_pnl"] > 0) / total_trades if total_trades > 0 else 0.0
    return cash - BASE_CAPITAL, total_trades, win_rate, sum(1 for tr in trade_log if tr["reason"] == "EOD"), sum(1 for tr in trade_log if tr["reason"] == "MEAN_REV")

results_st3 = []
for sym_a, sym_b in TOP_PAIRS:
    df_pair = log_prices[[sym_a, sym_b]].dropna(how='any')
    ya, yb, times = df_pair[sym_a].values, df_pair[sym_b].values, df_pair.index
    raw_px = price_matrix[sym_a].loc[times].values
    warmup_n = min(WARMUP_BARS, len(ya) // 10)
    
    ou = extract_ou_distribution(ya, yb, NUM_CHUNKS)
    if not ou: continue
    
    Q_fsl, P0_fsl, R_fsl = compute_q_from_tau(FIXED_SPEED_LIMIT_TAU, ya[:warmup_n], yb[:warmup_n])
    pnl_fsl, trades_fsl, _, _, _ = run_backtest(run_kalman_filter(ya, yb, times, Q_fsl, P0_fsl, R_fsl), raw_px, times)
    
    Q_wc, P0_wc, R_wc = compute_q_from_tau(ou["hl_max"] * 2.0, ya[:warmup_n], yb[:warmup_n])
    pnl_wc, trades_wc, _, _, _ = run_backtest(run_kalman_filter(ya, yb, times, Q_wc, P0_wc, R_wc), raw_px, times)
    
    Q_dr, P0_dr, R_dr = compute_q_from_tau(ou["hl_medoid"] * 2.0, ya[:warmup_n], yb[:warmup_n])
    pnl_dr, trades_dr, _, _, _ = run_backtest(run_kalman_filter(ya, yb, times, Q_dr, P0_dr, R_dr), raw_px, times)
    
    results_st3.append({
        "pair": f"{sym_a}-{sym_b}",
        "fsl_net_pnl": pnl_fsl, "fsl_trades": trades_fsl,
        "wc_net_pnl": pnl_wc, "wc_trades": trades_wc,
        "dr_net_pnl": pnl_dr, "dr_trades": trades_dr,
    })

res_df = pd.DataFrame(results_st3)
res_df.to_csv("production_engine_results.csv", index=False)
print("Saved Stage 3 outputs.")
display(res_df)
""")

# ── LOAD KAGGLE CREDS ──
try:
    with open(os.path.expanduser('~/.quant_env')) as f:
        env_content = f.read()
    creds = {}
    for line in env_content.splitlines():
        if '=' in line:
            line = line.replace('export ', '')
            key, val = line.split('=', 1)
            creds[key.strip()] = val.strip("'\"")
    k_user = creds.get('KAGGLE_USERNAME', '')
    k_key = creds.get('KAGGLE_KEY', '')
except:
    k_user, k_key = '', ''

# ── PUBLISH TO KAGGLE 
md("""## Publish Output Dataset""")
code(f"""
import json, os, shutil
from kaggle.api.kaggle_api_extended import KaggleApi

os.environ['KAGGLE_USERNAME'] = '{k_user}'
os.environ['KAGGLE_KEY'] = '{k_key}'

api = KaggleApi()
api.authenticate()

export_dir = '/kaggle/working/dataset_export'
os.makedirs(export_dir, exist_ok=True)

for f in ['pairs_all.csv', 'pairs_top500.csv', 'stage2_ou_calibration.csv', 'stage2_chunk_sweep.csv', 'stage2_stability_summary.csv', 'production_engine_results.csv']:
    if os.path.exists(f): shutil.copy(f, f'{{export_dir}}/{{f}}')

meta = {{
    "title"    : "Pairs Trading Production Results v3",
    "id"       : "{k_user}/pairs-trading-production-results-v3",
    "licenses" : [{{"name": "CC0-1.0"}}]
}}
with open(f'{{export_dir}}/dataset-metadata.json', 'w') as f:
    json.dump(meta, f, indent=2)

try:
    api.dataset_create_new(export_dir, dir_mode='zip', quiet=False)
except Exception as e:
    if "already exists" in str(e).lower() or "409" in str(e):
        print("Dataset exists, updating version...")
        api.dataset_create_version(export_dir, "Update", dir_mode='zip', quiet=False)
    else:
        raise e

print("✅ Dataset ready and published.")
""")

notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.10.12"}
    },
    "nbformat": 4, "nbformat_minor": 5
}

kernel_meta = {
    "id": f"{k_user}/pairs-full-pipeline-v3",
    "title": "Pairs Full Pipeline v3",
    "code_file": "full-pipeline.ipynb",
    "language": "python",
    "kernel_type": "notebook",
    "is_private": "true",
    "enable_gpu": "false",
    "enable_internet": "true",
    "dataset_sources": ["utkarshpatelthefirst/master-data-1min-db"],
    "competition_sources": [], "kernel_sources": [], "model_sources": []
}

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kaggle_staging", "full_pipeline")
os.makedirs(OUT_DIR, exist_ok=True)
with open(os.path.join(OUT_DIR, "full-pipeline.ipynb"), "w") as f: json.dump(notebook, f, indent=2)
with open(os.path.join(OUT_DIR, "kernel-metadata.json"), "w") as f: json.dump(kernel_meta, f, indent=2)
print(f"\\n✅ Full pipeline notebook written to: {OUT_DIR}")
