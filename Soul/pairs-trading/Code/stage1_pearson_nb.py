"""
Soul/Code/stage1_pearson_nb.py
================================
Builder script: generates a Kaggle .ipynb for Stage 1 Pearson Correlation Screening.
Run this locally to produce the notebook, then push to Kaggle with kaggle-notebook-run skill.

Usage:
    python stage1_pearson_nb.py

Output:
    Soul/pairs-trading/Code/kaggle_staging/stage1_pearson/
        stage1-pearson-correlation.ipynb
        kernel-metadata.json
"""

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


# ── CELL 1: Title ─────────────────────────────────────────────────────────────
md("""# Stage 1 — Pearson Correlation Screening
**Strategy**: NSE Intraday Pairs Trading  
**Purpose**: Rank all ~500 NSE equities by Pearson correlation of log-returns.  
**Outputs**: `pairs_all.csv`, `pairs_top500.csv`
""")

# ── CELL 2: Setup & DB Detection ──────────────────────────────────────────────
code("""
import os, glob, gc
import sqlite3
import pandas as pd
import numpy as np
from scipy.stats import t as t_dist

print("=== Detecting SQLite DB ===")
hits = glob.glob('/kaggle/input/**/*.sqlite', recursive=True)
if not hits:
    raise FileNotFoundError("No .sqlite found under /kaggle/input")
DB_PATH = hits[0]
print(f"DB_PATH = {DB_PATH}")
""")

# ── CELL 3: Load & NSE Hours Filter ───────────────────────────────────────────
code("""
# --- Load all close prices ---
con = sqlite3.connect(DB_PATH)
df = pd.read_sql(
    "SELECT symbol, timestamp, close FROM ohlcv_1min ORDER BY timestamp", con
)
con.close()
print(f"Raw rows: {len(df):,} | Symbols: {df['symbol'].nunique()}")

df['dt'] = pd.to_datetime(df['timestamp'], unit='s', utc=True).dt.tz_convert('Asia/Kolkata')

# --- NSE hours filter (vectorized, no Python datetime objects) ---
time_int = df['dt'].dt.hour * 100 + df['dt'].dt.minute
df_trading = df[(time_int >= 915) & (time_int <= 1529)].copy()
del df; gc.collect()
print(f"After NSE hours filter: {len(df_trading):,} rows")
""")

# ── CELL 4: Pivot & Log-Returns ───────────────────────────────────────────────
code("""
# --- Pivot to price matrix ---
price_matrix = df_trading.pivot(index='dt', columns='symbol', values='close')
del df_trading; gc.collect()
print(f"Price matrix shape: {price_matrix.shape}")

# --- Log-returns ---
log_returns = np.log(price_matrix / price_matrix.shift(1))

# --- Annihilate overnight gap returns (dynamic date-boundary detection) ---
# NOT a static time==09:15 mask — that fails if first bar of the day is 09:16, 09:17, etc.
dates_arr = np.array(price_matrix.index.date)
session_open_mask = np.concatenate([[True], dates_arr[1:] != dates_arr[:-1]])
log_returns.iloc[session_open_mask] = np.nan

print(f"Log-return matrix shape: {log_returns.shape}")
print(f"Session opens masked (overnight gap removed): {session_open_mask.sum()} rows")
""")

# ── CELL 5: Pairwise Pearson Correlation ──────────────────────────────────────
code("""
# --- Pairwise Pearson Correlation ---
# pandas .corr() computes pairwise by default — NaN rows dropped per pair.
# This is the CORRECT approach. Do NOT use global dropna before this step.
print("Computing pairwise Pearson correlation matrix...")
corr_df = log_returns.corr(method='pearson')
print(f"Correlation matrix: {corr_df.shape}")
""")

# ── CELL 6: Extract Pairs with t-stat Filter ──────────────────────────────────
code("""
# --- Extract upper triangle with statistical filters ---
symbols = corr_df.columns.tolist()
print(f"Extracting pairs from {len(symbols)} symbols...")

rows = []
for i in range(len(symbols)):
    for j in range(i + 1, len(symbols)):
        rho = corr_df.iloc[i, j]
        if np.isnan(rho):
            continue
        # Pairwise n: count rows where BOTH are non-NaN
        n_pair = log_returns[[symbols[i], symbols[j]]].dropna().shape[0]
        if n_pair < 5000:
            continue  # insufficient overlap
        # t-statistic for H0: rho == 0
        t_stat = rho * np.sqrt((n_pair - 2) / max(1.0 - rho**2, 1e-12))
        p_val  = 2 * t_dist.sf(abs(t_stat), df=n_pair - 2)
        if p_val >= 0.05:
            continue  # not statistically significant
        rows.append({
            "symbol_a":   symbols[i],
            "symbol_b":   symbols[j],
            "pearson_rho": round(rho, 6),
            "t_stat":      round(t_stat, 4),
            "p_value":     round(p_val, 8),
            "n_obs":       n_pair,
        })

pairs_df = (
    pd.DataFrame(rows)
    .sort_values("pearson_rho", ascending=False)
    .reset_index(drop=True)
)
pairs_df["rank"] = pairs_df.index + 1

print(f"\\nTotal valid pairs: {len(pairs_df):,}")
print(f"Top pair: {pairs_df.iloc[0]['symbol_a']}/{pairs_df.iloc[0]['symbol_b']} "
      f"rho={pairs_df.iloc[0]['pearson_rho']:.4f}")
if len(pairs_df) >= 500:
    print(f"Rank-500 cutoff rho: {pairs_df.iloc[499]['pearson_rho']:.4f}")
""")

# ── CELL 7: Save Outputs ──────────────────────────────────────────────────────
code("""
# --- Save outputs ---
pairs_df.to_csv("pairs_all.csv", index=False)
pairs_df.head(500).to_csv("pairs_top500.csv", index=False)
print("Saved: pairs_all.csv, pairs_top500.csv")
print("\\nTop 10 pairs:")
display(pairs_df.head(10)[['rank', 'symbol_a', 'symbol_b', 'pearson_rho', 'n_obs', 'p_value']])
""")


# ── Build notebook JSON ────────────────────────────────────────────────────────
notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {
            "codemirror_mode": {"name": "ipython", "version": 3},
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "version": "3.10.12"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 5
}

kernel_meta = {
    "id": "utkarshpatelthefirst/pairs-stage1-pearson-v2",
    "title": "Pairs Stage 1: Pearson Correlation v2",
    "code_file": "stage1-pearson-correlation.ipynb",
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

# ── Write output ───────────────────────────────────────────────────────────────
OUT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "kaggle_staging", "stage1_pearson"
)
os.makedirs(OUT_DIR, exist_ok=True)

with open(os.path.join(OUT_DIR, "stage1-pearson-correlation.ipynb"), "w") as f:
    json.dump(notebook, f, indent=2)
with open(os.path.join(OUT_DIR, "kernel-metadata.json"), "w") as f:
    json.dump(kernel_meta, f, indent=2)

print(f"\\n✅ Stage 1 notebook written to: {OUT_DIR}")
print("Push to Kaggle with: kaggle kernels push -p <output_dir>")
