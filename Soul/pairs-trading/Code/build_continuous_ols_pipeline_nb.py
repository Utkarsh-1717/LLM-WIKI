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
md("""# Full Pipeline: Continuous Vectorized OLS & Intraday Cointegration
**Strategy**: NSE Intraday Pairs Trading  
**Features**:
1. Minute-by-Minute 7500-Bar Rolling OLS (Vectorized)
2. Intraday Engle-Granger Cointegration (Lazy ADF Test only on profitable pairs)
3. Z-Score Mean Reversion Backtest (C++ Speed via Numba + Joblib)
""")

# ── IMPORTS & PATH DISCOVERY
code("""
import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import os, glob, gc, json, shutil
import sqlite3
import pandas as pd
import numpy as np
import numba
from joblib import Parallel, delayed
from scipy.stats import t as t_dist
from statsmodels.tsa.stattools import adfuller

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
**Output**: `pairs_all.csv`
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
            "pearson_rho": round(rho, 6)
        })

pairs_df = pd.DataFrame(rows).sort_values("pearson_rho", ascending=False).reset_index(drop=True)
pairs_df.to_csv("pairs_all.csv", index=False)
print("Saved Stage 1 outputs.")

TOP_PAIRS = list(zip(pairs_df["symbol_a"], pairs_df["symbol_b"]))
print(f"\\nUsing ALL {len(TOP_PAIRS)} Production Pairs for Execution...")
""")

# ── STAGE 3
md("""## Stage 3 — Continuous Vectorized OLS & Execution Engine
**Output**: `continuous_ols_production_results.csv`
""")
code("""
ROLLING_WINDOW = 7500
ZSCORE_WINDOW = 7500
Z_ENTRY = 2.0
EOD_EXIT_TIME = 1515
BASE_CAPITAL = 10_000.0
LEVERAGE = 5.0
POS_SIZE = BASE_CAPITAL * LEVERAGE

@numba.njit
def calc_zerodha_friction(price, qty, is_buy):
    val = price * qty
    brokerage = min(val * 0.0003, 20.0)
    stt = 0.0 if is_buy else val * 0.00025
    exc = val * 0.0000325
    gst = (brokerage + exc) * 0.18
    sebi = val * 0.000001
    stamp = val * 0.00003 if is_buy else 0.0
    return brokerage + stt + exc + gst + sebi + stamp

@numba.njit
def _numba_backtest_loop(z_scores, raw_prices, is_eod, z_window, z_entry, base_cap, pos_size, lagger_is_a):
    cash = base_cap
    pos_qty = 0
    pos_type = 0
    entry_px = 0.0
    entry_z_sign = 0.0
    is_locked_out = False
    
    total_trades = 0
    winning_trades = 0
    gross_pnl = 0.0
    total_fees = 0.0
    mean_rev_exits = 0
    eod_exits = 0
    gross_wins = 0
    sum_price_captured = 0.0
    
    n = len(z_scores)
    for t in range(z_window, n):
        z = z_scores[t]
        price = raw_prices[t]
        
        if np.isnan(z) or np.isnan(price) or price <= 0:
            continue
            
        if is_locked_out and (-1.0 < z < 1.0):
            is_locked_out = False
            
        if pos_qty > 0:
            exit_now = False
            is_eod_exit = False
            if is_eod[t]:
                exit_now = True
                is_eod_exit = True
            elif entry_z_sign >= 1.0 and z <= 0:
                exit_now = True
            elif entry_z_sign <= -1.0 and z >= 0:
                exit_now = True
                
            if exit_now:
                if pos_type == 1:
                    gross = (price - entry_px) * pos_qty
                    friction_exit = calc_zerodha_friction(price, pos_qty, False)
                    friction_entry = calc_zerodha_friction(entry_px, pos_qty, True)
                else:
                    gross = (entry_px - price) * pos_qty
                    friction_exit = calc_zerodha_friction(price, pos_qty, True)
                    friction_entry = calc_zerodha_friction(entry_px, pos_qty, False)
                
                total_fees += (friction_entry + friction_exit)
                net = gross - friction_exit
                cash += net
                gross_pnl += gross
                
                total_trades += 1
                if net > 0:
                    winning_trades += 1
                if gross > 0:
                    gross_wins += 1
                    
                sum_price_captured += (abs(price - entry_px) if gross > 0 else -abs(price - entry_px))
                
                if is_eod_exit:
                    eod_exits += 1
                    is_locked_out = True
                else:
                    mean_rev_exits += 1
                    
                pos_qty = 0
                pos_type = 0
                
        if pos_qty == 0 and not is_eod[t] and not is_locked_out:
            if z <= -z_entry or z >= z_entry:
                qty = int(pos_size // price)
                if qty > 0:
                    entry_px = price
                    pos_qty = qty
                    entry_z_sign = 1.0 if z >= z_entry else -1.0
                    
                    if z >= z_entry:
                        pos_type = -1 if lagger_is_a else 1
                    else:
                        pos_type = 1 if lagger_is_a else -1
                        
                    is_buy_entry = (pos_type == 1)
                    cash -= calc_zerodha_friction(price, qty, is_buy_entry)
                    
    return cash - base_cap, gross_pnl, total_trades, winning_trades, gross_wins, mean_rev_exits, eod_exits, sum_price_captured, total_fees

def run_backtest_numba(spread, raw_prices, timestamps, lagger_is_a):
    spread_s = pd.Series(spread)
    roll_mean = spread_s.rolling(ZSCORE_WINDOW).mean()
    roll_std  = spread_s.rolling(ZSCORE_WINDOW).std()
    z_scores  = ((spread_s - roll_mean) / roll_std.replace(0, np.nan)).to_numpy()
    
    time_int = timestamps.hour * 100 + timestamps.minute
    is_eod   = np.asarray(time_int == EOD_EXIT_TIME)
    
    net_pnl, gross_pnl, total_trades, winning_trades, gross_wins, mean_rev_exits, eod_exits, sum_price_captured, total_fees = _numba_backtest_loop(
        z_scores, raw_prices, is_eod, 
        ZSCORE_WINDOW, Z_ENTRY, BASE_CAPITAL, POS_SIZE, lagger_is_a
    )
    
    net_win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
    gross_win_rate = gross_wins / total_trades if total_trades > 0 else 0.0
    avg_price_captured = sum_price_captured / total_trades if total_trades > 0 else 0.0
    avg_fee_drag = total_fees / total_trades if total_trades > 0 else 0.0
    
    # --- Physical Parameter Extraction ---
    clean_spread = spread[~np.isnan(spread)]
    spread_vol = np.std(clean_spread) if len(clean_spread) > 0 else 0.0
    mean_abs_dev = np.mean(np.abs(clean_spread)) if len(clean_spread) > 0 else 0.0
    
    signs = np.sign(clean_spread)
    zero_crossings = np.sum(signs[:-1] != signs[1:]) if len(clean_spread) > 1 else 0
    
    half_life = np.nan
    q_val = np.nan
    if len(clean_spread) > 2:
        y_t = clean_spread[1:]
        y_t_1 = clean_spread[:-1]
        cov_matrix = np.cov(y_t_1, y_t)
        if cov_matrix[0,0] > 0:
            beta_ou = cov_matrix[0,1] / cov_matrix[0,0]
            if 0 < beta_ou < 1:
                half_life = -np.log(2) / np.log(beta_ou)
                q_val = spread_vol * spread_vol * (1 - np.exp(-2 * np.log(2) / half_life))
                
    return net_pnl, gross_pnl, total_trades, net_win_rate, gross_win_rate, mean_rev_exits, eod_exits, avg_price_captured, avg_fee_drag, spread_vol, mean_abs_dev, zero_crossings, half_life, q_val

print("Compiling Numba engine...")
_ = _numba_backtest_loop(np.array([1.0]*8000), np.array([100.0]*8000), np.array([False]*8000), ZSCORE_WINDOW, Z_ENTRY, BASE_CAPITAL, POS_SIZE, True)

def detect_lagger(ya, yb, timestamps, warmup_bars=7500):
    if len(ya) < warmup_bars + 2: return "a"
    ret_a = np.diff(ya[:warmup_bars])
    ret_b = np.diff(yb[:warmup_bars])
    time_ints = timestamps[:warmup_bars].hour * 100 + timestamps[:warmup_bars].minute
    is_not_915 = (time_ints[1:] != 915)
    ret_a = np.where(is_not_915, ret_a, 0.0)
    ret_b = np.where(is_not_915, ret_b, 0.0)
    c_mat_ab = np.corrcoef(ret_a[1:], ret_b[:-1])
    c_mat_ba = np.corrcoef(ret_b[1:], ret_a[:-1])
    c_ab = c_mat_ab[0, 1] if c_mat_ab.shape == (2, 2) else 0.0
    c_ba = c_mat_ba[0, 1] if c_mat_ba.shape == (2, 2) else 0.0
    c_ab = 0.0 if np.isnan(c_ab) else c_ab
    c_ba = 0.0 if np.isnan(c_ba) else c_ba
    return "b" if abs(c_ba) >= abs(c_ab) else "a"

def process_pair(pair):
    sym_a, sym_b = pair
    if sym_a not in log_prices.columns or sym_b not in log_prices.columns:
        return None
        
    df_pair = log_prices[[sym_a, sym_b]].dropna(how='any')
    ya, yb = df_pair[sym_a], df_pair[sym_b]
    times = df_pair.index
    
    lagger_side = detect_lagger(ya.values, yb.values, times, ROLLING_WINDOW)
    lagger_is_a = (lagger_side == "a")
    lagger_sym = sym_a if lagger_is_a else sym_b
    raw_px = price_matrix[lagger_sym].loc[times].to_numpy()
    
    if len(ya) <= ZSCORE_WINDOW:
        return None
        
    # 1. Vectorized Continuous Rolling OLS (Minute-by-Minute)
    roll_cov = ya.rolling(window=ROLLING_WINDOW).cov(yb)
    roll_var = yb.rolling(window=ROLLING_WINDOW).var()
    beta = roll_cov / roll_var
    alpha = ya.rolling(window=ROLLING_WINDOW).mean() - beta * yb.rolling(window=ROLLING_WINDOW).mean()
    spread = ya - (alpha + beta * yb)
    
    # 2. Execution Engine Backtest
    net_pnl, gross_pnl, trades, net_win_rate, gross_win_rate, mean_rev_exits, eod_exits, avg_price_captured, avg_fee_drag, spread_vol, mean_abs_dev, zero_cross, half_life, q_val = run_backtest_numba(spread.to_numpy(), raw_px, times, lagger_is_a)
    
    # 3. Intraday Cointegration Test (Lazy - ONLY if profitable)
    adf_stat, pval = np.nan, np.nan
    if net_pnl > 0:
        clean_spread = spread.dropna()
        if len(clean_spread) > 100:
            try:
                res = adfuller(clean_spread, maxlag=1)
                adf_stat, pval = res[0], res[1]
            except:
                pass
                
    return {
        "pair": f"{sym_a}-{sym_b}",
        "lagger_asset": lagger_sym,
        "ols_gross_pnl": round(gross_pnl, 2),
        "ols_net_pnl": round(net_pnl, 2),
        "ols_trades": trades,
        "gross_win_rate": round(gross_win_rate, 4),
        "net_win_rate": round(net_win_rate, 4),
        "mean_rev_exits": mean_rev_exits,
        "eod_exits": eod_exits,
        "avg_price_captured": round(avg_price_captured, 4),
        "avg_fee_drag": round(avg_fee_drag, 4),
        "spread_vol": round(spread_vol, 6),
        "mean_abs_dev": round(mean_abs_dev, 6),
        "zero_crossings": zero_cross,
        "half_life": round(half_life, 2) if not np.isnan(half_life) else "",
        "kalman_q": round(q_val, 8) if not np.isnan(q_val) else "",
        "adf_stat": round(adf_stat, 4) if not np.isnan(adf_stat) else "",
        "adf_pval": round(pval, 6) if not np.isnan(pval) else "",
    }

print(f"Executing massive Joblib parallel sweep across {len(TOP_PAIRS)} pairs on 4 CPUs...")
results_st3 = Parallel(n_jobs=-1, batch_size='auto')(delayed(process_pair)(pair) for pair in TOP_PAIRS)
results_st3 = [r for r in results_st3 if r is not None]

res_df = pd.DataFrame(results_st3).sort_values("ols_net_pnl", ascending=False)
res_df.to_csv("continuous_ols_production_results.csv", index=False)
print("Saved Continuous OLS outputs.")
display(res_df.head(50))
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

for f in ['pairs_all.csv', 'continuous_ols_production_results.csv']:
    if os.path.exists(f): shutil.copy(f, f'{{export_dir}}/{{f}}')

meta = {{
    "title"    : "Pairs Continuous OLS Production Results v1",
    "id"       : "{k_user}/pairs-continuous-ols-production-v1",
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
    "id": f"{k_user}/pairs-continuous-ols-pipeline-v1",
    "title": "Pairs Continuous OLS Pipeline v1",
    "code_file": "continuous-ols-pipeline.ipynb",
    "language": "python",
    "kernel_type": "notebook",
    "is_private": "true",
    "enable_gpu": "false",
    "enable_internet": "true",
    "dataset_sources": ["utkarshpatelthefirst/master-data-1min-db"],
    "competition_sources": [], "kernel_sources": [], "model_sources": []
}

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kaggle_staging", "continuous_ols_pipeline")
os.makedirs(OUT_DIR, exist_ok=True)
with open(os.path.join(OUT_DIR, "continuous-ols-pipeline.ipynb"), "w") as f: json.dump(notebook, f, indent=2)
with open(os.path.join(OUT_DIR, "kernel-metadata.json"), "w") as f: json.dump(kernel_meta, f, indent=2)
print(f"\\n✅ Continuous OLS pipeline notebook written to: {OUT_DIR}")
