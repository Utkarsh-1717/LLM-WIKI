"""
Soul/Code/build_production_engine.py
=====================================
Builder script: generates the Stage 3 production Kaggle notebook.
Runs ALL THREE Q methods head-to-head for a complete comparison:
  1. Fixed Speed-Limit Q (τ=120 min) — archived benchmark
  2. OU Worst-Case Anchored Q       — max(chunk HLs) × 2.0
  3. OU Dominant Regime Q           — medoid(chunk HLs) × 2.0

Usage:
    python build_production_engine.py

Output:
    Soul/pairs-trading/Code/kaggle_staging/stage3_production/
        production-engine.ipynb
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
md("""# Stage 3 — Production Execution Engine
**Strategy**: NSE Intraday Pairs Trading — Single-Sided Lagger  
**Three Q methods compared head-to-head**:
1. **Fixed Speed-Limit Q** (τ=120 min) — archived benchmark; shows cost of non-OU calibration
2. **OU Worst-Case Anchored Q** — Q from max(chunk HLs) × 2.0 — proven production winner
3. **OU Dominant Regime Q** — Q from medoid(chunk HLs) × 2.0 — new method

**Capital**: ₹10,000 base × 5x MIS = ₹50,000 per pair  
**Friction**: 0.05% per leg  
**Square-off**: 15:15 PM forced EOD
""")

# ── CONFIG ────────────────────────────────────────────────────────────────────
code("""
# ╔══════════════════════════════════════════╗
# ║           CONFIGURATION BLOCK            ║
# ╚══════════════════════════════════════════╝

# Chunk count for OU calibration in this run
NUM_CHUNKS = 4   # change to 6, 8, 10 to match Stage 2 sweep result

# Warmup bars (5 trading days = 5 × 375)
WARMUP_BARS = 1875

# Z-score rolling window (1 trading day = 375 bars)
ZSCORE_WINDOW = 375

# Signal thresholds
Z_ENTRY = 2.0    # |Z| >= Z_ENTRY to enter
# Exit: Z crosses 0, OR time == EOD_EXIT_TIME

# EOD forced square-off time (HHMM format)
EOD_EXIT_TIME = 1515

# Capital & leverage (per pair)
BASE_CAPITAL = 10_000.0
LEVERAGE     = 5.0
POS_SIZE     = BASE_CAPITAL * LEVERAGE   # = 50,000 INR

# Friction per leg (covers brokerage + STT + exchange + slippage)
FRICTION_PCT = 0.0005   # 0.05%

# Fixed Speed-Limit Q target tau (archived benchmark)
FIXED_SPEED_LIMIT_TAU = 120.0   # minutes

# Production pairs
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
    f"SELECT symbol, timestamp, close FROM ohlcv_1min "
    f"WHERE symbol IN ({placeholders}) ORDER BY timestamp",
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
print(f"Price matrix: {price_matrix.shape} | Log-price matrix: {log_prices.shape}")
""")

# ── SHARED UTILITIES ─────────────────────────────────────────────────────────
code("""
# ─────────────────────────────────────────────────────────────────────────────
# SHARED UTILITY FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def find_medoid(half_lives):
    \"\"\"
    The actual observed chunk HL that is closest to all other chunk HLs.
    = the dominant / most-repeating half-life regime of the pair.
    \"\"\"
    hls = np.array(half_lives)
    if len(hls) == 1:
        return hls[0]
    distances = np.array([np.sum(np.abs(hl - hls)) for hl in hls])
    return hls[np.argmin(distances)]


def compute_ou_half_lives(ya, yb, num_chunks):
    \"\"\"
    Splits data into num_chunks temporal windows.
    Returns (hl_max, hl_medoid, all_hls) or (None, None, []) if no valid chunks.
    \"\"\"
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
    if not valid_hls:
        return None, None, []
    return float(np.max(valid_hls)), float(find_medoid(valid_hls)), valid_hls


def compute_q_from_tau(target_tau, ya_warmup, yb_warmup):
    \"\"\"
    Analytically derives Q matrix and P0 from target_tau and warmup OLS.
    \"\"\"
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


def run_kalman_filter(ya, yb, timestamps, Q, P0, R):
    \"\"\"
    Forward-only Kalman filter tracking [beta_t, alpha_t].
    Returns the spread series (Kalman innovation v_t at each bar).
    Applies 09:15 gap protocol: P_pred *= 2 at every session open.
    \"\"\"
    T = len(ya)
    N = 2
    X_full = np.column_stack([yb, np.ones(T)])
    x_upd = P0 @ X_full[0] / (X_full[0] @ P0 @ X_full[0] + R)  # dummy init
    # Proper init: use OLS result from P0 derivation
    x_upd = np.linalg.lstsq(X_full[:min(100, T)], ya[:min(100, T)], rcond=None)[0]
    P_upd = P0.copy()

    time_int = timestamps.hour * 100 + timestamps.minute
    is_open = (time_int == 915)

    spread = np.zeros(T)

    for t in range(T):
        # Predict
        x_p = x_upd
        P_p = P_upd + Q

        # 09:15 Gap Protocol: double prediction uncertainty at session open
        if is_open[t]:
            P_p *= 2.0

        # Update
        H_t = X_full[t]                          # shape (2,)
        v_t = ya[t] - H_t @ x_p                 # innovation = spread
        S_t = H_t @ P_p @ H_t + R               # scalar
        K_t = P_p @ H_t / S_t                   # shape (2,) Kalman gain
        x_upd = x_p + K_t * v_t
        P_upd = P_p - np.outer(K_t, H_t) @ P_p

        spread[t] = v_t

    return spread


def run_backtest(spread, raw_prices, timestamps, pair_label=""):
    \"\"\"
    Single-Sided Lagger backtest on a precomputed spread series.
    Z-score from rolling ZSCORE_WINDOW window.
    Entry: |Z| >= Z_ENTRY. Exit: Z crosses 0 OR time == EOD_EXIT_TIME.
    Returns: (net_pnl, total_trades, win_rate, n_eod_exits, n_mean_rev_exits)
    \"\"\"
    spread_s = pd.Series(spread)
    roll_mean = spread_s.rolling(ZSCORE_WINDOW).mean()
    roll_std  = spread_s.rolling(ZSCORE_WINDOW).std()
    z_scores  = ((spread_s - roll_mean) / roll_std.replace(0, np.nan)).values

    time_int = timestamps.hour * 100 + timestamps.minute
    is_eod   = (time_int == EOD_EXIT_TIME)

    cash      = BASE_CAPITAL
    pos_qty   = 0
    pos_type  = 0          # 1=LONG lagger, -1=SHORT lagger
    entry_px  = 0.0
    trade_log = []

    for t in range(ZSCORE_WINDOW, len(spread)):
        z     = z_scores[t]
        price = raw_prices[t]

        if np.isnan(z) or np.isnan(price) or price <= 0:
            continue

        # ── EXIT ──
        if pos_qty > 0:
            exit_now = (
                is_eod[t]
                or (pos_type ==  1 and z >= 0)   # long: exit when Z >= 0
                or (pos_type == -1 and z <= 0)   # short: exit when Z <= 0
            )
            if exit_now:
                if pos_type == 1:
                    gross = (price - entry_px) * pos_qty
                else:
                    gross = (entry_px - price) * pos_qty
                friction_exit = (pos_qty * price) * FRICTION_PCT
                net = gross - friction_exit
                cash += net
                trade_log.append({
                    "net_pnl": net,
                    "reason":  "EOD" if is_eod[t] else "MEAN_REV"
                })
                pos_qty  = 0
                pos_type = 0

        # ── ENTRY ──
        if pos_qty == 0 and not is_eod[t]:
            if z <= -Z_ENTRY:    # lagger is underpriced → LONG
                qty = int(POS_SIZE // price)
                if qty > 0:
                    entry_px  = price
                    pos_qty   = qty
                    pos_type  = 1
                    cash -= (qty * price) * FRICTION_PCT
            elif z >= Z_ENTRY:   # lagger is overpriced → SHORT
                qty = int(POS_SIZE // price)
                if qty > 0:
                    entry_px  = price
                    pos_qty   = qty
                    pos_type  = -1
                    cash -= (qty * price) * FRICTION_PCT

    total_trades  = len(trade_log)
    win_rate      = (sum(1 for tr in trade_log if tr["net_pnl"] > 0) / total_trades
                     if total_trades > 0 else 0.0)
    n_eod         = sum(1 for tr in trade_log if tr["reason"] == "EOD")
    n_mean_rev    = sum(1 for tr in trade_log if tr["reason"] == "MEAN_REV")
    net_pnl       = cash - BASE_CAPITAL

    return net_pnl, total_trades, win_rate, n_eod, n_mean_rev
""")

# ── MAIN ENGINE ───────────────────────────────────────────────────────────────
code("""
# ─────────────────────────────────────────────────────────────────────────────
# PRODUCTION ENGINE — All 3 Q methods head-to-head
# ─────────────────────────────────────────────────────────────────────────────
print(f"\\n=== Production Engine | NUM_CHUNKS = {NUM_CHUNKS} ===")
print(f"Methods: Fixed Speed-Limit (τ={FIXED_SPEED_LIMIT_TAU}m) | "
      f"OU Worst-Case | OU Dominant Regime\\n")

results = []

for pair in TOP_PAIRS:
    sym_a, sym_b = pair
    df_pair = log_prices[[sym_a, sym_b]].dropna(how='any')
    ya      = df_pair[sym_a].values
    yb      = df_pair[sym_b].values
    times   = df_pair.index
    raw_px  = price_matrix[sym_a].loc[times].values   # lagger = sym_a
    warmup_n = min(WARMUP_BARS, len(ya) // 10)

    print(f"Processing {sym_a}-{sym_b} | {len(ya):,} bars | warmup={warmup_n}")

    # ── OU calibration ──
    hl_max, hl_medoid, all_hls = compute_ou_half_lives(ya, yb, NUM_CHUNKS)

    if hl_max is None:
        print(f"  ⚠ SKIP — no valid OU half-lives")
        continue

    print(f"  Chunk HLs: {[round(h,1) for h in all_hls]} | "
          f"Worst-Case tau={hl_max*2:.1f}m | Dominant tau={hl_medoid*2:.1f}m")

    # ── Method 1: Fixed Speed-Limit Q ──
    Q_fsl, P0_fsl, R_fsl = compute_q_from_tau(FIXED_SPEED_LIMIT_TAU,
                                                ya[:warmup_n], yb[:warmup_n])
    spread_fsl = run_kalman_filter(ya, yb, times, Q_fsl, P0_fsl, R_fsl)
    pnl_fsl, trades_fsl, wr_fsl, eod_fsl, mr_fsl = run_backtest(
        spread_fsl, raw_px, times)

    # ── Method 2: OU Worst-Case Anchored Q ──
    tau_wc = hl_max * 2.0
    Q_wc, P0_wc, R_wc = compute_q_from_tau(tau_wc, ya[:warmup_n], yb[:warmup_n])
    spread_wc = run_kalman_filter(ya, yb, times, Q_wc, P0_wc, R_wc)
    pnl_wc, trades_wc, wr_wc, eod_wc, mr_wc = run_backtest(
        spread_wc, raw_px, times)

    # ── Method 3: OU Dominant Regime Q ──
    tau_dr = hl_medoid * 2.0
    Q_dr, P0_dr, R_dr = compute_q_from_tau(tau_dr, ya[:warmup_n], yb[:warmup_n])
    spread_dr = run_kalman_filter(ya, yb, times, Q_dr, P0_dr, R_dr)
    pnl_dr, trades_dr, wr_dr, eod_dr, mr_dr = run_backtest(
        spread_dr, raw_px, times)

    print(f"  Fixed Speed-Limit:    PnL=₹{pnl_fsl:+.0f} | Trades={trades_fsl}")
    print(f"  OU Worst-Case:        PnL=₹{pnl_wc:+.0f}  | Trades={trades_wc}")
    print(f"  OU Dominant Regime:   PnL=₹{pnl_dr:+.0f}  | Trades={trades_dr}")

    results.append({
        "pair":                       f"{sym_a}-{sym_b}",
        "num_chunks":                 NUM_CHUNKS,
        "chunk_half_lives":           str([round(h, 1) for h in all_hls]),
        "hl_max_min":                 round(hl_max, 2),
        "hl_medoid_min":              round(hl_medoid, 2),
        # Fixed Speed-Limit
        "fsl_tau":                    FIXED_SPEED_LIMIT_TAU,
        "fsl_net_pnl":                round(pnl_fsl, 2),
        "fsl_trades":                 trades_fsl,
        "fsl_win_rate_pct":           round(wr_fsl * 100, 1),
        "fsl_eod_exits":              eod_fsl,
        "fsl_mean_rev_exits":         mr_fsl,
        # OU Worst-Case Anchored Q
        "wc_tau":                     round(tau_wc, 2),
        "wc_net_pnl":                 round(pnl_wc, 2),
        "wc_trades":                  trades_wc,
        "wc_win_rate_pct":            round(wr_wc * 100, 1),
        "wc_eod_exits":               eod_wc,
        "wc_mean_rev_exits":          mr_wc,
        # OU Dominant Regime Q
        "dr_tau":                     round(tau_dr, 2),
        "dr_net_pnl":                 round(pnl_dr, 2),
        "dr_trades":                  trades_dr,
        "dr_win_rate_pct":            round(wr_dr * 100, 1),
        "dr_eod_exits":               eod_dr,
        "dr_mean_rev_exits":          mr_dr,
    })

results_df = pd.DataFrame(results)
results_df.to_csv("production_engine_results.csv", index=False)

print("\\n" + "="*70)
print("PRODUCTION ENGINE SUMMARY")
print("="*70)
display(results_df[[
    "pair",
    "fsl_net_pnl",   "fsl_trades",
    "wc_net_pnl",    "wc_trades",
    "dr_net_pnl",    "dr_trades",
]])
print(f"\\nTotal FSL Net PnL:             ₹{results_df['fsl_net_pnl'].sum():+.2f}")
print(f"Total OU Worst-Case Net PnL:   ₹{results_df['wc_net_pnl'].sum():+.2f}")
print(f"Total OU Dominant Regime PnL:  ₹{results_df['dr_net_pnl'].sum():+.2f}")
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
    "id": "utkarshpatelthefirst/pairs-production-engine-v3",
    "title": "Pairs Production Engine v3 — All 3 Q Methods",
    "code_file": "production-engine.ipynb",
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

# Write to staging dir (NOT to this file's own location)
OUT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "kaggle_staging", "stage3_production"
)
os.makedirs(OUT_DIR, exist_ok=True)

with open(os.path.join(OUT_DIR, "production-engine.ipynb"), "w") as f:
    json.dump(notebook, f, indent=2)
with open(os.path.join(OUT_DIR, "kernel-metadata.json"), "w") as f:
    json.dump(kernel_meta, f, indent=2)

print(f"\n✅ Production engine notebook written to: {OUT_DIR}")
print("Push to Kaggle with: kaggle kernels push -p <output_dir>")
