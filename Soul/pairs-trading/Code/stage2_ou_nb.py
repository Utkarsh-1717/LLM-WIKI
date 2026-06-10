"""
Soul/Code/stage2_ou_nb.py
==========================
Builder script: generates a Kaggle .ipynb for Stage 2 OU Chunked Q Calibration.
Produces BOTH calibration methods and runs a chunk sweep for stability analysis.

Usage:
    python stage2_ou_nb.py

Output:
    Soul/pairs-trading/Code/kaggle_staging/stage2_ou/
        stage2-ou-calibration.ipynb
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


# ── TITLE ─────────────────────────────────────────────────────────────────────
md("""# Stage 2 — OU Chunked Q Calibration
**Two Methods**:
- **OU Worst-Case Anchored Q** — Q from max(chunk HLs) × 2.0
- **OU Dominant Regime Q** — Q from medoid(chunk HLs) × 2.0

**Chunk Sweep**: 4, 6, 8, 10 chunks — shows half-life stability across resolution levels.
""")

# ── CONFIG ────────────────────────────────────────────────────────────────────
code("""
# ╔══════════════════════════════════════════╗
# ║           CONFIGURATION BLOCK            ║
# ╚══════════════════════════════════════════╝

# Primary chunk count for main calibration output
NUM_CHUNKS = 4

# Chunk sweep values (for stability analysis — do not change unless exploring)
CHUNK_SWEEP = [4, 6, 8, 10]

# Warmup bars for OLS initialization (5 trading days = 5 × 375 bars)
WARMUP_BARS = 1875

# Top 5 production pairs (fixed — derived from Stage 1)
TOP_PAIRS = [
    ("PFC",       "RECLTD"),
    ("BDL",       "MAZDOCK"),
    ("GRSE",      "MAZDOCK"),
    ("BANKBARODA","CANBK"),
    ("BPCL",      "HINDPETRO"),
]
""")

# ── SETUP ─────────────────────────────────────────────────────────────────────
code("""
import os, glob, gc
import sqlite3
import pandas as pd
import numpy as np

print("=== Detecting SQLite DB ===")
hits = glob.glob('/kaggle/input/**/*.sqlite', recursive=True)
if not hits:
    raise FileNotFoundError("No .sqlite found under /kaggle/input")
DB_PATH = hits[0]
print(f"DB_PATH = {DB_PATH}")

symbols_to_load = list(set([sym for pair in TOP_PAIRS for sym in pair]))

con = sqlite3.connect(DB_PATH)
placeholders = ",".join(["?"] * len(symbols_to_load))
df = pd.read_sql(
    f"SELECT symbol, timestamp, close FROM ohlcv_1min WHERE symbol IN ({placeholders}) ORDER BY timestamp",
    con, params=symbols_to_load
)
con.close()
print(f"Loaded {len(df):,} rows for {df['symbol'].nunique()} symbols")

df['dt'] = pd.to_datetime(df['timestamp'], unit='s', utc=True).dt.tz_convert('Asia/Kolkata')
time_int = df['dt'].dt.hour * 100 + df['dt'].dt.minute
df_trading = df[(time_int >= 915) & (time_int <= 1529)].copy()
del df; gc.collect()

price_matrix = df_trading.pivot(index='dt', columns='symbol', values='close')
del df_trading; gc.collect()

log_prices = np.log(price_matrix)
print(f"Log-price matrix: {log_prices.shape}")
""")

# ── CORE FUNCTIONS ────────────────────────────────────────────────────────────
code("""
# ─────────────────────────────────────────────────────────────────────────────
# CORE FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def find_medoid(half_lives):
    \"\"\"
    Returns the actual observed chunk half-life that is closest to all others.
    = the chunk HL that most other chunks cluster around (the dominant/repeating regime).
    NOT the mean (distorted by outliers) and NOT the median (interpolated, not a real value).
    \"\"\"
    hls = np.array(half_lives)
    if len(hls) == 1:
        return hls[0]
    distances = np.array([np.sum(np.abs(hl - hls)) for hl in hls])
    return hls[np.argmin(distances)]


def extract_ou_distribution(ya, yb, num_chunks):
    \"\"\"
    Splits data into num_chunks temporal windows.
    For each chunk: OLS to get spread, AR(1) to get phi, compute half-life.
    Returns dict with full HL distribution stats, or None if no valid chunks.
    \"\"\"
    chunk_size = len(ya) // num_chunks
    valid_hls = []

    for i in range(num_chunks):
        start = i * chunk_size
        end = (i + 1) * chunk_size if i < num_chunks - 1 else len(ya)
        y_c, x_c = ya[start:end], yb[start:end]

        # OLS: y = beta*x + alpha
        X_mat = np.column_stack([x_c, np.ones(len(x_c))])
        beta, _, _, _ = np.linalg.lstsq(X_mat, y_c, rcond=None)
        spread = y_c - X_mat @ beta

        # AR(1): S_t = phi * S_{t-1} + c
        X_ar = np.column_stack([spread[:-1], np.ones(len(spread) - 1)])
        phi_res, _, _, _ = np.linalg.lstsq(X_ar, spread[1:], rcond=None)
        phi = phi_res[0]

        if 0 < phi < 1:
            hl = -np.log(2) / np.log(phi)   # half-life in minutes
            valid_hls.append(hl)

    if not valid_hls:
        return None  # pair is not mean-reverting in any chunk

    return {
        "all_hls":    valid_hls,
        "n_valid":    len(valid_hls),
        "hl_min":     float(np.min(valid_hls)),
        "hl_max":     float(np.max(valid_hls)),        # → Method A
        "hl_medoid":  float(find_medoid(valid_hls)),   # → Method B
        "hl_median":  float(np.median(valid_hls)),     # reference only
        "hl_mean":    float(np.mean(valid_hls)),       # reference only
        "hl_std":     float(np.std(valid_hls)),
    }


def compute_q_from_tau(target_tau, ya_warmup, yb_warmup):
    \"\"\"
    Analytically computes Q matrix and P0 for a given target_tau.
    Same formula for both OU methods — only target_tau differs.
    \"\"\"
    n = len(ya_warmup)
    X_w = np.column_stack([yb_warmup, np.ones(n)])
    beta0 = np.linalg.lstsq(X_w, ya_warmup, rcond=None)[0]
    residuals = ya_warmup - X_w @ beta0
    R_est = np.sum(residuals ** 2) / (n - 2)

    # Lambda: Kalman gain decay mapping for target half-life tau
    K_factor = 1.0 - np.power(0.5, 1.0 / target_tau)
    lam = (K_factor ** 2) / (1.0 - K_factor)

    # Q = lambda * sigma^2_OLS * Sigma_X_inv
    Sigma_X_inv = np.linalg.inv(X_w.T @ X_w / n)
    Q = lam * R_est * Sigma_X_inv

    # P0 via OLS parameter covariance (NOT sample cov of X — that locks intercept)
    P0 = R_est * np.linalg.inv(X_w.T @ X_w)

    return Q, P0, R_est
""")

# ── MAIN CALIBRATION (NUM_CHUNKS) ─────────────────────────────────────────────
code("""
# ─────────────────────────────────────────────────────────────────────────────
# MAIN CALIBRATION — Primary chunk count (NUM_CHUNKS)
# ─────────────────────────────────────────────────────────────────────────────
print(f"\\n=== Stage 2 OU Calibration | NUM_CHUNKS = {NUM_CHUNKS} ===")

results = []

for pair in TOP_PAIRS:
    sym_a, sym_b = pair
    df_pair = log_prices[[sym_a, sym_b]].dropna(how='any')
    ya = df_pair[sym_a].values
    yb = df_pair[sym_b].values
    print(f"\\nPair: {sym_a}-{sym_b} | Valid bars: {len(ya):,}")

    ou = extract_ou_distribution(ya, yb, NUM_CHUNKS)
    if ou is None:
        print(f"  ⚠ SKIP — no mean-reverting chunks (all phi >= 1 or <= 0)")
        continue

    warmup_n = min(WARMUP_BARS, len(ya) // 10)

    # Method A: OU Worst-Case Anchored Q
    tau_A = ou["hl_max"] * 2.0
    Q_A, P0_A, R_A = compute_q_from_tau(tau_A, ya[:warmup_n], yb[:warmup_n])

    # Method B: OU Dominant Regime Q (medoid)
    tau_B = ou["hl_medoid"] * 2.0
    Q_B, P0_B, R_B = compute_q_from_tau(tau_B, ya[:warmup_n], yb[:warmup_n])

    print(f"  Chunk HLs: {[round(h,1) for h in ou['all_hls']]} min")
    print(f"  Method A (Worst-Case):     tau={tau_A:.1f} min | Q_beta={Q_A[0,0]:.2e}")
    print(f"  Method B (Dominant/Medoid):tau={tau_B:.1f} min | Q_beta={Q_B[0,0]:.2e}")

    results.append({
        "pair":                   f"{sym_a}-{sym_b}",
        "num_chunks":             NUM_CHUNKS,
        "chunk_half_lives":       str([round(h, 2) for h in ou["all_hls"]]),
        "n_valid_chunks":         ou["n_valid"],
        "hl_min":                 round(ou["hl_min"],    2),
        "hl_max":                 round(ou["hl_max"],    2),
        "hl_medoid":              round(ou["hl_medoid"], 2),
        "hl_median":              round(ou["hl_median"], 2),
        "hl_mean":                round(ou["hl_mean"],   2),
        "hl_std":                 round(ou["hl_std"],    2),
        "target_tau_worst_case":  round(tau_A, 2),
        "target_tau_dominant":    round(tau_B, 2),
        "Q_beta_worst_case":      round(Q_A[0, 0], 10),
        "Q_alpha_worst_case":     round(Q_A[1, 1], 10),
        "Q_beta_dominant":        round(Q_B[0, 0], 10),
        "Q_alpha_dominant":       round(Q_B[1, 1], 10),
        "R_est":                  round(R_A, 10),
    })

results_df = pd.DataFrame(results)
results_df.to_csv("stage2_ou_calibration.csv", index=False)
print("\\n✅ Main calibration complete:")
display(results_df)
""")

# ── CHUNK SWEEP ───────────────────────────────────────────────────────────────
code("""
# ─────────────────────────────────────────────────────────────────────────────
# CHUNK SWEEP — HL stability across resolution levels
# Regime-stable pairs: HL estimates consistent across 4/6/8/10 chunks (trustworthy)
# Regime-volatile pairs: HL estimates vary widely (fragile, trade with caution)
# ─────────────────────────────────────────────────────────────────────────────
print(f"\\n=== Chunk Sweep: {CHUNK_SWEEP} ===")

sweep_rows = []
for num_c in CHUNK_SWEEP:
    for pair in TOP_PAIRS:
        sym_a, sym_b = pair
        df_pair = log_prices[[sym_a, sym_b]].dropna(how='any')
        ya = df_pair[sym_a].values
        yb = df_pair[sym_b].values
        ou = extract_ou_distribution(ya, yb, num_c)
        if ou is None:
            continue
        sweep_rows.append({
            "pair":        f"{sym_a}-{sym_b}",
            "num_chunks":  num_c,
            "n_valid":     ou["n_valid"],
            "hl_max":      round(ou["hl_max"],    2),
            "hl_medoid":   round(ou["hl_medoid"], 2),
            "hl_median":   round(ou["hl_median"], 2),
            "hl_mean":     round(ou["hl_mean"],   2),
            "hl_std":      round(ou["hl_std"],    2),
        })

sweep_df = pd.DataFrame(sweep_rows)
sweep_df.to_csv("stage2_chunk_sweep.csv", index=False)
print("\\n✅ Chunk sweep complete:")
display(sweep_df.sort_values(["pair", "num_chunks"]))
""")

# ── STABILITY SUMMARY ─────────────────────────────────────────────────────────
code("""
# --- Stability summary: std of hl_max and hl_medoid across chunk counts per pair ---
stability = (
    sweep_df.groupby("pair")
    .agg(
        hl_max_mean   =("hl_max",    "mean"),
        hl_max_std    =("hl_max",    "std"),
        hl_medoid_mean=("hl_medoid", "mean"),
        hl_medoid_std =("hl_medoid", "std"),
    )
    .round(2)
    .reset_index()
)
stability["regime_stable"] = stability["hl_max_std"] < 20.0  # < 20 min spread = stable
stability.to_csv("stage2_stability_summary.csv", index=False)
print("\\n✅ Stability Summary (lower hl_max_std = more regime-stable pair):")
display(stability)
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
    "id": "utkarshpatelthefirst/pairs-stage2-ou-calibration",
    "title": "Pairs Stage 2: OU Chunked Q Calibration",
    "code_file": "stage2-ou-calibration.ipynb",
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

OUT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "kaggle_staging", "stage2_ou"
)
os.makedirs(OUT_DIR, exist_ok=True)

with open(os.path.join(OUT_DIR, "stage2-ou-calibration.ipynb"), "w") as f:
    json.dump(notebook, f, indent=2)
with open(os.path.join(OUT_DIR, "kernel-metadata.json"), "w") as f:
    json.dump(kernel_meta, f, indent=2)

print(f"\\n✅ Stage 2 notebook written to: {OUT_DIR}")
print("Push to Kaggle with: kaggle kernels push -p <output_dir>")
