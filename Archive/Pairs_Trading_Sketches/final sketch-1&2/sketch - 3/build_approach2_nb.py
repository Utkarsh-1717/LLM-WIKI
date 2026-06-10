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

add_markdown("# Stage 2 Validation: Approach 2 (The Empirical OU Chunked Fit)")

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
def calculate_chunked_half_life(ya, yb, num_chunks=4):
    chunk_size = len(ya) // num_chunks
    half_lives = []
    variances = []
    
    for i in range(num_chunks):
        start_idx = i * chunk_size
        end_idx = (i + 1) * chunk_size if i < num_chunks - 1 else len(ya)
        
        y_chunk = ya[start_idx:end_idx]
        x_chunk = yb[start_idx:end_idx]
        
        # OLS to find static spread for this chunk
        X_mat = np.column_stack([x_chunk, np.ones(len(x_chunk))])
        beta_hat, _, _, _ = np.linalg.lstsq(X_mat, y_chunk, rcond=None)
        
        spread = y_chunk - (X_mat @ beta_hat)
        
        # AR(1) on spread
        s_t = spread[1:]
        s_t1 = spread[:-1]
        
        X_ar = np.column_stack([s_t1, np.ones(len(s_t1))])
        phi_hat, res, _, _ = np.linalg.lstsq(X_ar, s_t, rcond=None)
        phi = phi_hat[0]
        
        if 0 < phi < 1:
            hl = -np.log(2) / np.log(phi)
            half_lives.append(hl)
            
            if len(res) > 0:
                var = res[0] / (len(s_t) - 2)
                variances.append(var)
            else:
                variances.append(np.var(s_t - X_ar @ phi_hat))
        else:
            # Divergent or non-stationary chunk
            pass
            
    if not half_lives:
        return np.inf, [], []
        
    worst_case_hl = np.max(half_lives)
    return worst_case_hl, half_lives, variances
""")

add_code("""
results = []
print(f"\\nAnalyzing {len(top_pairs)} Pairs across 4 Temporal Chunks...")

for pair in top_pairs:
    sym_a, sym_b = pair
    df_pair = log_prices[[sym_a, sym_b]].dropna()
    ya = df_pair[sym_a].values
    yb = df_pair[sym_b].values
    
    worst_hl, all_hls, all_vars = calculate_chunked_half_life(ya, yb, num_chunks=4)
    
    formatted_hls = [f"{h:.1f}m" for h in all_hls]
    avg_var = np.mean(all_vars) if all_vars else 0.0
    
    results.append({
        "Pair": f"{sym_a}-{sym_b}",
        "Worst_Case_HL_Min": worst_hl,
        "Target_Kalman_Delay_Min": worst_hl * 2.0 if worst_hl != np.inf else np.inf,
        "Avg_OU_Variance": avg_var,
        "Chunk_HLs": str(formatted_hls)
    })

res_df = pd.DataFrame(results)
res_df.to_csv("approach2_ou_results.csv", index=False)
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
with open("kaggle_stage2_run/stage2-approach2-test.ipynb", "w") as f:
    json.dump(nb, f, indent=2)

meta = {
    "id": "utkarshpatelthefirst/stage-2-approach2-ou-fit",
    "title": "Stage 2 Approach 2 OU Fit",
    "code_file": "stage2-approach2-test.ipynb",
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

print("Created notebook for Approach 2 OU Fit!")
