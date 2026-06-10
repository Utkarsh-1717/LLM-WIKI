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
2. Intraday Engle-Granger Cointegration (ADF Test on Smooth Spread)
3. Z-Score Mean Reversion Backtest
""")

# ── IMPORTS & PATH DISCOVERY
code("""
import os, glob, gc, json, shutil
import sqlite3
import pandas as pd
import numpy as np
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
**Output**: `pairs_top500.csv`
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
pairs_df.head(500).to_csv("pairs_top500.csv", index=False)
print("Saved Stage 1 outputs.")

top500 = pairs_df.head(500)
TOP_PAIRS = list(zip(top500["symbol_a"], top500["symbol_b"]))
print(f"\\nUsing Top {len(TOP_PAIRS)} Production Pairs for Execution...")
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
FRICTION_PCT = 0.0005

results_st3 = []

def run_backtest_ols(spread, raw_prices, timestamps):
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
    return cash - BASE_CAPITAL, total_trades, win_rate

for sym_a, sym_b in TOP_PAIRS:
    df_pair = log_prices[[sym_a, sym_b]].dropna(how='any')
    ya, yb = df_pair[sym_a], df_pair[sym_b]
    times = df_pair.index
    raw_px = price_matrix[sym_a].loc[times].values
    
    # 1. Vectorized Continuous Rolling OLS (Minute-by-Minute)
    roll_cov = ya.rolling(window=ROLLING_WINDOW).cov(yb)
    roll_var = yb.rolling(window=ROLLING_WINDOW).var()
    beta = roll_cov / roll_var
    alpha = ya.rolling(window=ROLLING_WINDOW).mean() - beta * yb.rolling(window=ROLLING_WINDOW).mean()
    spread = ya - (alpha + beta * yb)
    
    # 2. Intraday Cointegration Test (Stage 1B Equivalent)
    clean_spread = spread.dropna()
    adf_stat, pval = np.nan, np.nan
    if len(clean_spread) > 100:
        try:
            res = adfuller(clean_spread, maxlag=1)
            adf_stat, pval = res[0], res[1]
        except:
            pass

    # 3. Execution Engine Backtest
    pnl, trades, win_rate = run_backtest_ols(spread.values, raw_px, times)
    
    results_st3.append({
        "pair": f"{sym_a}-{sym_b}",
        "ols_net_pnl": pnl,
        "ols_trades": trades,
        "ols_win_rate": round(win_rate, 4),
        "adf_stat": round(adf_stat, 4) if not np.isnan(adf_stat) else "",
        "adf_pval": round(pval, 6) if not np.isnan(pval) else "",
    })

res_df = pd.DataFrame(results_st3)
res_df.to_csv("continuous_ols_production_results.csv", index=False)
print("Saved Continuous OLS outputs.")
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

for f in ['pairs_top500.csv', 'continuous_ols_production_results.csv']:
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
