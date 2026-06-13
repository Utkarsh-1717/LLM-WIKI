"""
Stage 1: Monthly Re-Roll Engine — Kaggle Notebook Builder
Repo: Utkarsh-1717/pairs-trading-prod (private)
Outputs: fixed-filename CSVs pushed to outputs/ in the same private GitHub repo.
Safe Place is robust: files always overwritten, no old data accumulation.
"""
import json, uuid, os

# ── ALL CREDENTIALS ──
FYERS_USERNAME   = "FAI84454"
FYERS_APP_ID     = "G0NX5M08ZG-100"
FYERS_SECRET_KEY = "D07VJ80FLH"
FYERS_TOTP_KEY   = "4QXQQACGALLZNFISHC5G7WU76AERBNYC"
FYERS_PIN        = "7475"
FYERS_REDIRECT   = "https://trade.fyers.in/api-login/redirect-uri/index.html"
KAGGLE_USER      = "utkarshpatelthefirst"
KAGGLE_KEY       = "fbef16329099428205f671dd5de8337b"
GITHUB_TOKEN     = "<YOUR_GITHUB_PAT_REDACTED_BY_GITHUB_PUSH_PROTECTION>"
GITHUB_REPO      = "Utkarsh-1717/pairs-trading-prod"
GITHUB_BRANCH    = "main"

def gen_id():
    return str(uuid.uuid4())[:8]

cells = []

def md(text):
    cells.append({"cell_type": "markdown", "metadata": {}, "id": gen_id(),
                  "source": [l + "\n" for l in text.strip().split("\n")]})

def code(text):
    cells.append({"cell_type": "code", "execution_count": None,
                  "metadata": {}, "id": gen_id(), "outputs": [],
                  "source": [l + "\n" for l in text.strip().split("\n")]})

md("""# NSE Pairs Trading — Stage 1: Monthly Re-Roll Engine
**Safe Place**: `github.com/Utkarsh-1717/pairs-trading-prod/outputs/` (private)
Fixed filenames overwritten each run — no old file accumulation ever.
""")

# ── CELL 0: Thread Lock + Imports ──
md("## Cell 0 — Thread Lock & Imports")
code("""
import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"]      = "1"

import gc, json, time, base64
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse
import urllib.request
from io import StringIO

import pandas as pd
import numpy as np
import numba
from joblib import Parallel, delayed
import pyotp, requests
from fyers_apiv3 import fyersModel
from statsmodels.tsa.stattools import adfuller
from scipy.stats import t as t_dist

RUN_DATE = datetime.now().strftime("%m-%d-%y")
RUN_TS   = datetime.now().isoformat()
print(f"Run Date : {RUN_DATE}")
print(f"Run Time : {RUN_TS}")
""")

# ── CELL 1: Fyers Auth ──
md("## Cell 1 — Fyers TOTP Authentication")
code(f"""
fy_id = "{FYERS_USERNAME}"; app_id_full = "{FYERS_APP_ID}"
secret_key = "{FYERS_SECRET_KEY}"; totp_key = "{FYERS_TOTP_KEY}"
pin = "{FYERS_PIN}"; redirect_uri = "{FYERS_REDIRECT}"

res1 = requests.post("https://api-t2.fyers.in/vagator/v2/send_login_otp",
    json={{"fy_id": fy_id, "app_id": "2"}}).json()
assert "request_key" in res1, f"Step1 failed: {{res1}}"
req_key = res1["request_key"]

res2 = requests.post("https://api-t2.fyers.in/vagator/v2/verify_otp",
    json={{"request_key": req_key, "otp": pyotp.TOTP(totp_key).now()}}).json()
assert "request_key" in res2, f"Step2 failed: {{res2}}"
req_key = res2["request_key"]

res3 = requests.post("https://api-t2.fyers.in/vagator/v2/verify_pin",
    json={{"request_key": req_key, "identity_type": "pin", "identifier": pin}}).json()
assert "data" in res3, f"Step3 failed: {{res3}}"
access_token = res3["data"]["access_token"]

res4 = requests.post("https://api-t1.fyers.in/api/v3/token",
    json={{"fyers_id": fy_id, "app_id": app_id_full[:-4],
           "redirect_uri": redirect_uri, "appType": "100",
           "code_challenge": "", "state": "stage1",
           "scope": "", "nonce": "", "response_type": "code", "create_cookie": True}},
    headers={{"Authorization": f"Bearer {{access_token}}"}}).json()
assert "Url" in res4, f"Step4 failed: {{res4}}"
auth_code = parse_qs(urlparse(res4["Url"]).query)["auth_code"][0]

session = fyersModel.SessionModel(client_id=app_id_full, secret_key=secret_key,
    redirect_uri=redirect_uri, response_type="code", grant_type="authorization_code")
session.set_token(auth_code)
fyers_token = session.generate_token()["access_token"]
fyers = fyersModel.FyersModel(client_id=app_id_full, is_async=False,
    token=fyers_token, log_path="/kaggle/working/")
print("✅ Fyers Authentication Successful")
""")

# ── CELL 2: NSE 500 ──
md("## Cell 2 — Live NSE 500 Symbol Fetch")
code("""
req = urllib.request.Request(
    "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv",
    headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=30) as resp:
    nse_df = pd.read_csv(StringIO(resp.read().decode("utf-8")))
nse_symbols = nse_df["Symbol"].dropna().str.strip().tolist()
print(f"✅ NSE 500: {len(nse_symbols)} symbols")
pd.DataFrame({"symbol": nse_symbols, "run_date": RUN_DATE}).to_csv(
    "/kaggle/working/NSE-500.csv", index=False)
""")

# ── CELL 3: Download 120 Days ──
md("## Cell 3 — Download 120 Exact Trading Days")
code("""
REQUIRED_TRADING_DAYS = 120
SESSION_BARS = 375

today = datetime.now()
c1_end = today; c1_start = today - timedelta(days=90)
c2_end = c1_start - timedelta(days=1); c2_start = c2_end - timedelta(days=90)
chunks = [
    (c2_start.strftime("%Y-%m-%d"), c2_end.strftime("%Y-%m-%d")),
    (c1_start.strftime("%Y-%m-%d"), c1_end.strftime("%Y-%m-%d")),
]
print(f"Chunk 1: {chunks[0][0]} to {chunks[0][1]}")
print(f"Chunk 2: {chunks[1][0]} to {chunks[1][1]}")

all_data = {}; errors_fetch = {}
for idx, sym in enumerate(nse_symbols):
    fyers_sym = f"NSE:{sym}-EQ"; sym_rows = []
    for (s, e) in chunks:
        try:
            resp = fyers.history(data={"symbol": fyers_sym, "resolution": "1",
                "date_format": "1", "range_from": s, "range_to": e, "cont_flag": "1"})
            if resp.get("s") == "ok" and resp.get("candles"):
                for c in resp["candles"]: sym_rows.append([int(c[0]), float(c[4])])
            else: errors_fetch.setdefault(sym, []).append(resp.get("message", "empty"))
        except Exception as e: errors_fetch.setdefault(sym, []).append(str(e))
        time.sleep(0.5)
    if sym_rows: all_data[sym] = sorted(sym_rows, key=lambda x: x[0])
    if (idx+1) % 50 == 0: print(f"  {idx+1}/{len(nse_symbols)} done...")
print(f"\\n✅ {len(all_data)} symbols with data, {len(errors_fetch)} errors")
""")

# ── CELL 4: Trim to 120 days ──
md("## Cell 4 — Trim to Exactly 120 Unique Trading Dates & Build Price Matrix")
code("""
all_dates = set()
for sym, rows in all_data.items():
    for ts, _ in rows:
        all_dates.add((datetime.utcfromtimestamp(ts) + timedelta(hours=5, minutes=30)).date())

sorted_dates = sorted(all_dates)
if len(sorted_dates) < REQUIRED_TRADING_DAYS:
    raise RuntimeError(f"Only {len(sorted_dates)} trading dates — need {REQUIRED_TRADING_DAYS}")

keep_dates = set(sorted_dates[-REQUIRED_TRADING_DAYS:])
print(f"Available: {len(sorted_dates)} | Using: {REQUIRED_TRADING_DAYS} | Range: {min(keep_dates)} → {max(keep_dates)}")

recs = []
for sym, rows in all_data.items():
    for ts, close in rows:
        ist = datetime.utcfromtimestamp(ts) + timedelta(hours=5, minutes=30)
        if ist.date() not in keep_dates: continue
        ti = ist.hour * 100 + ist.minute
        if ti < 915 or ti > 1529: continue
        recs.append({"symbol": sym, "ts": ist, "close": close})

del all_data; gc.collect()
raw = pd.DataFrame(recs); del recs; gc.collect()
price_matrix = raw.pivot(index="ts", columns="symbol", values="close")
del raw; gc.collect()
log_prices = np.log(price_matrix)
print(f"Price matrix: {price_matrix.shape}")
""")

# ── CELL 5: Coverage Filter ──
md("## Cell 5 — 70% Coverage Filter")
code("""
MIN_BARS = int(REQUIRED_TRADING_DAYS * SESSION_BARS * 0.70)
counts = price_matrix.count()
low_coverage = counts[counts < MIN_BARS].index.tolist()
good_symbols = counts[counts >= MIN_BARS].index.tolist()
print(f"In matrix: {len(counts)} | ≥70%: {len(good_symbols)} | <70% excluded: {len(low_coverage)}")
pd.DataFrame({"symbol": low_coverage, "run_date": RUN_DATE,
              "bars": [int(counts[s]) for s in low_coverage]}).to_csv(
    "/kaggle/working/le_70_coverage.csv", index=False)
price_matrix = price_matrix[good_symbols]
log_prices   = np.log(price_matrix)
print(f"Final matrix: {price_matrix.shape}")
""")

# ── CELL 6: Pearson Screening ──
md("## Cell 6 — Pearson Correlation Screening")
code("""
dates_arr    = np.array(price_matrix.index.date)
sess_open    = np.concatenate([[True], dates_arr[1:] != dates_arr[:-1]])
log_ret      = log_prices - log_prices.shift(1)
log_ret.iloc[sess_open] = np.nan
print("Computing Pearson correlation...")
corr_df = log_ret.corr(method="pearson")
syms = corr_df.columns.tolist(); rows = []
for i in range(len(syms)):
    for j in range(i+1, len(syms)):
        rho = corr_df.iloc[i, j]
        if np.isnan(rho): continue
        n_p = log_ret[[syms[i], syms[j]]].dropna().shape[0]
        if n_p < 5000: continue
        t_s = rho * np.sqrt((n_p-2) / max(1.0 - rho**2, 1e-12))
        p_v = 2 * t_dist.sf(abs(t_s), df=n_p-2)
        rows.append({"symbol_a": syms[i], "symbol_b": syms[j], "pearson_rho": round(rho, 6)})
pairs_df  = pd.DataFrame(rows).sort_values("pearson_rho", ascending=False).reset_index(drop=True)
TOP_PAIRS = list(zip(pairs_df["symbol_a"], pairs_df["symbol_b"]))
print(f"✅ {len(TOP_PAIRS)} pairs for execution")
""")

# ── CELL 7: Numba Engine ──
md("## Cell 7 — Numba Execution Engine (Identical to Reference Code)")
code("""
ROLLING_WINDOW = 7500; ZSCORE_WINDOW = 7500; Z_ENTRY = 2.0
EOD_EXIT_TIME = 1515; BASE_CAPITAL = 10_000.0; LEVERAGE = 5.0
POS_SIZE = BASE_CAPITAL * LEVERAGE

@numba.njit
def calc_zerodha_friction(price, qty, is_buy):
    val = price * qty
    brokerage = min(val * 0.0003, 20.0)
    stt   = 0.0 if is_buy else val * 0.00025
    exc   = val * 0.0000325
    gst   = (brokerage + exc) * 0.18
    sebi  = val * 0.000001
    stamp = val * 0.00003 if is_buy else 0.0
    return brokerage + stt + exc + gst + sebi + stamp

@numba.njit
def _numba_backtest_loop(z_scores, raw_prices, is_eod, z_window, z_entry,
                          base_cap, pos_size, lagger_is_a):
    cash = base_cap; pos_qty = 0; pos_type = 0; entry_px = 0.0
    entry_z_sign = 0.0; is_locked_out = False
    total_trades = 0; winning_trades = 0; gross_pnl = 0.0
    total_fees = 0.0; mean_rev_exits = 0; eod_exits = 0
    gross_wins = 0; sum_price_captured = 0.0
    n = len(z_scores)
    for t in range(z_window, n):
        z = z_scores[t]; price = raw_prices[t]
        if np.isnan(z) or np.isnan(price) or price <= 0: continue
        if is_locked_out and (-1.0 < z < 1.0): is_locked_out = False
        if pos_qty > 0:
            exit_now = False; is_eod_exit = False
            if is_eod[t]:                          exit_now = True; is_eod_exit = True
            elif entry_z_sign >= 1.0 and z <= 0:   exit_now = True
            elif entry_z_sign <= -1.0 and z >= 0:  exit_now = True
            if exit_now:
                if pos_type == 1:
                    gross = (price - entry_px) * pos_qty
                    fe = calc_zerodha_friction(price, pos_qty, False)
                    fn = calc_zerodha_friction(entry_px, pos_qty, True)
                else:
                    gross = (entry_px - price) * pos_qty
                    fe = calc_zerodha_friction(price, pos_qty, True)
                    fn = calc_zerodha_friction(entry_px, pos_qty, False)
                total_fees += (fn + fe); net = gross - fe
                cash += net; gross_pnl += gross; total_trades += 1
                if net > 0: winning_trades += 1
                if gross > 0: gross_wins += 1
                sum_price_captured += (abs(price-entry_px) if gross > 0 else -abs(price-entry_px))
                if is_eod_exit: eod_exits += 1; is_locked_out = True
                else: mean_rev_exits += 1
                pos_qty = 0; pos_type = 0
        if pos_qty == 0 and not is_eod[t] and not is_locked_out:
            if z <= -z_entry or z >= z_entry:
                qty = int(pos_size // price)
                if qty > 0:
                    entry_px = price; pos_qty = qty
                    entry_z_sign = 1.0 if z >= z_entry else -1.0
                    if z >= z_entry: pos_type = -1 if lagger_is_a else 1
                    else:            pos_type =  1 if lagger_is_a else -1
                    cash -= calc_zerodha_friction(price, qty, pos_type == 1)
    return (cash - base_cap, gross_pnl, total_trades, winning_trades,
            gross_wins, mean_rev_exits, eod_exits, sum_price_captured, total_fees)

def run_backtest_numba(spread, raw_prices, timestamps, lagger_is_a):
    sp = pd.Series(spread)
    rm = sp.rolling(ZSCORE_WINDOW).mean(); rs = sp.rolling(ZSCORE_WINDOW).std()
    z  = ((sp - rm) / rs.replace(0, np.nan)).to_numpy()
    ti = timestamps.hour * 100 + timestamps.minute
    ie = np.asarray(ti == EOD_EXIT_TIME)
    (net_pnl, gp, tr, wt, gw, mr, ed, spc, tf) = _numba_backtest_loop(
        z, raw_prices, ie, ZSCORE_WINDOW, Z_ENTRY, BASE_CAPITAL, POS_SIZE, lagger_is_a)
    nwr = wt/tr if tr > 0 else 0.0; gwr = gw/tr if tr > 0 else 0.0
    apc = spc/tr if tr > 0 else 0.0; afd = tf/tr if tr > 0 else 0.0
    cl = spread[~np.isnan(spread)]
    sv = np.std(cl) if len(cl) > 0 else 0.0
    md = np.mean(np.abs(cl)) if len(cl) > 0 else 0.0
    sg = np.sign(cl); zc = np.sum(sg[:-1] != sg[1:]) if len(cl) > 1 else 0
    hl = qv = np.nan
    if len(cl) > 2:
        cm = np.cov(cl[:-1], cl[1:])
        if cm[0,0] > 0:
            b = cm[0,1]/cm[0,0]
            if 0 < b < 1:
                hl = -np.log(2)/np.log(b)
                qv = sv**2 * (1 - np.exp(-2 * np.log(2) / hl))
    return net_pnl, gp, tr, nwr, gwr, mr, ed, apc, afd, sv, md, zc, hl, qv

def detect_lagger(ya, yb, timestamps, warmup=7500):
    if len(ya) < warmup + 2: return "a"
    ra = np.diff(ya[:warmup]); rb = np.diff(yb[:warmup])
    ti = timestamps[:warmup].hour * 100 + timestamps[:warmup].minute
    nn = (ti[1:] != 915)
    ra = np.where(nn, ra, 0.0); rb = np.where(nn, rb, 0.0)
    c_ab = np.corrcoef(ra[1:], rb[:-1])[0,1]; c_ba = np.corrcoef(rb[1:], ra[:-1])[0,1]
    c_ab = 0.0 if np.isnan(c_ab) else c_ab; c_ba = 0.0 if np.isnan(c_ba) else c_ba
    return "b" if abs(c_ba) >= abs(c_ab) else "a"

def process_pair(pair):
    sa, sb = pair
    if sa not in log_prices.columns or sb not in log_prices.columns: return None
    dp = log_prices[[sa, sb]].dropna(how="any")
    ya, yb, times = dp[sa], dp[sb], dp.index
    if len(ya) <= ZSCORE_WINDOW: return None
    ls = detect_lagger(ya.values, yb.values, times, ROLLING_WINDOW)
    la = (ls == "a"); lsym = sa if la else sb
    rpx = price_matrix[lsym].loc[times].to_numpy()
    rc = ya.rolling(ROLLING_WINDOW).cov(yb); rv = yb.rolling(ROLLING_WINDOW).var()
    beta = rc/rv
    alpha = ya.rolling(ROLLING_WINDOW).mean() - beta * yb.rolling(ROLLING_WINDOW).mean()
    spread = ya - (alpha + beta * yb)
    (np_, gp, tr, nwr, gwr, mr, ed, apc, afd, sv, mad, zc, hl, qv) = run_backtest_numba(
        spread.to_numpy(), rpx, times, la)
    adf_s = pv = np.nan
    cs = spread.dropna()
    if len(cs) > 100:
        try: res = adfuller(cs, maxlag=1); adf_s, pv = res[0], res[1]
        except: pass
    return {
        "pair": f"{sa}-{sb}", "lagger_asset": lsym, "run_date": RUN_DATE,
        "ols_gross_pnl": round(gp,2), "ols_net_pnl": round(np_,2),
        "ols_trades": tr,
        "gross_win_rate": round(gwr,4), "net_win_rate": round(nwr,4),
        "mean_rev_exits": mr, "eod_exits": ed,
        "avg_price_captured": round(apc,4), "avg_fee_drag": round(afd,4),
        "spread_vol": round(sv,6), "mean_abs_dev": round(mad,6),
        "zero_crossings": zc,
        "half_life": round(hl,2) if not np.isnan(hl) else "",
        "kalman_q":  round(qv,8) if not np.isnan(qv) else "",
        "adf_stat":  round(adf_s,4) if not np.isnan(adf_s) else "",
        "adf_pval":  round(pv,6) if not np.isnan(pv) else "",
    }

print("Compiling Numba JIT...")
_w = _numba_backtest_loop(np.array([1.0]*8000), np.array([100.0]*8000),
    np.array([False]*8000), ZSCORE_WINDOW, Z_ENTRY, BASE_CAPITAL, POS_SIZE, True)
print("✅ Numba compiled")
""")

# ── CELL 8: Parallel Sweep ──
md("## Cell 8 — Massive Joblib Parallel Sweep")
code("""
print(f"Sweeping {len(TOP_PAIRS)} pairs on 4 CPUs...")
results = Parallel(n_jobs=-1, batch_size="auto")(delayed(process_pair)(p) for p in TOP_PAIRS)
results = [r for r in results if r is not None]
ranked_df = pd.DataFrame(results).sort_values("ols_net_pnl", ascending=False).reset_index(drop=True)
ranked_df.to_csv("/kaggle/working/Ranked_Profit_All.csv", index=False)
print(f"✅ Ranked_Profit_All.csv: {len(ranked_df)} pairs")
display(ranked_df.head(20))
""")

# ── CELL 9: Physics Filter ──
md("## Cell 9 — Walk-Forward Physics Filter → Top 50 Pure")
code("""
def safe_float(v):
    try: return float(v)
    except: return float("nan")

mask = (
    (ranked_df["adf_pval"].apply(safe_float)  < 0.005) &
    (ranked_df["spread_vol"].apply(safe_float) > 0.045) &
    (ranked_df["half_life"].apply(safe_float)  < 1000.0) &
    (ranked_df["kalman_q"].apply(safe_float)   > 3.0e-06)
)
top50_df = ranked_df[mask].head(50).reset_index(drop=True)
top50_df.to_csv("/kaggle/working/Top_50_Pure.csv", index=False)
print(f"✅ Top_50_Pure.csv: {len(top50_df)} pairs | {mask.sum()} qualified of {len(ranked_df)}")
display(top50_df)
""")

# ── CELL 10: Push to GitHub ──
md("## Cell 10 — Push Outputs to Private GitHub Repo (Safe Place)")
code(f"""
import json, base64, requests

GH_TOKEN  = "{GITHUB_TOKEN}"
GH_REPO   = "{GITHUB_REPO}"
GH_BRANCH = "{GITHUB_BRANCH}"

def github_push(local_path, repo_path, msg):
    with open(local_path, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode()
    headers = {{"Authorization": f"token {{GH_TOKEN}}",
                "Accept": "application/vnd.github.v3+json"}}
    url = f"https://api.github.com/repos/{{GH_REPO}}/contents/{{repo_path}}"
    get_r = requests.get(url, headers=headers, params={{"ref": GH_BRANCH}})
    sha   = get_r.json().get("sha") if get_r.status_code == 200 else None
    payload = {{"message": msg, "content": content_b64, "branch": GH_BRANCH}}
    if sha: payload["sha"] = sha
    put_r = requests.put(url, headers=headers, json=payload)
    if put_r.status_code not in (200, 201):
        raise RuntimeError(f"GitHub push failed {{repo_path}}: {{put_r.status_code}} {{put_r.text[:300]}}")
    print(f"  ✅ {{'Updated' if sha else 'Created'}}: {{repo_path}}")

manifest = {{
    "run_date": RUN_DATE, "run_timestamp": RUN_TS,
    "total_pairs_run": len(ranked_df), "top50_count": len(top50_df),
    "date_range": f"{{str(min(keep_dates))}} to {{str(max(keep_dates))}}",
    "symbols_used": len(good_symbols), "symbols_excluded": len(low_coverage),
}}
with open("/kaggle/working/run_manifest.json", "w") as f:
    json.dump(manifest, f, indent=2)
print(f"Manifest: {{manifest}}")

commit_msg = f"Stage1 {{RUN_DATE}}: {{len(top50_df)}} elite pairs"
for lp, rp in [
    ("/kaggle/working/NSE-500.csv",           "outputs/NSE-500.csv"),
    ("/kaggle/working/le_70_coverage.csv",    "outputs/le_70_coverage.csv"),
    ("/kaggle/working/Ranked_Profit_All.csv", "outputs/Ranked_Profit_All.csv"),
    ("/kaggle/working/Top_50_Pure.csv",       "outputs/Top_50_Pure.csv"),
    ("/kaggle/working/run_manifest.json",     "outputs/run_manifest.json"),
]:
    github_push(lp, rp, commit_msg)

print(f"\\n✅ All outputs pushed to https://github.com/{{GH_REPO}}/tree/main/outputs/")
print("   Previous files overwritten — zero old data accumulation guaranteed.")
""")

# ── BUILD NOTEBOOK ──
notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.10.12"}
    },
    "nbformat": 4, "nbformat_minor": 5
}

kernel_meta = {
    "id": f"{KAGGLE_USER}/pairs-trading-stage1-monthly",
    "title": "Pairs Trading Stage 1 Monthly Re-Roll",
    "code_file": "pair_trading_stage1.ipynb",
    "language": "python",
    "kernel_type": "notebook",
    "is_private": "true",
    "enable_gpu": "false",
    "enable_internet": "true",
    "dataset_sources": [],
    "competition_sources": [], "kernel_sources": [], "model_sources": []
}

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kaggle_staging")
os.makedirs(OUT_DIR, exist_ok=True)
with open(os.path.join(OUT_DIR, "pair_trading_stage1.ipynb"), "w") as f:
    json.dump(notebook, f, indent=2)
with open(os.path.join(OUT_DIR, "kernel-metadata.json"), "w") as f:
    json.dump(kernel_meta, f, indent=2)
print(f"\n✅ Stage 1 notebook written → {OUT_DIR}")
