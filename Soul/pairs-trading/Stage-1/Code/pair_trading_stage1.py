"""
Stage 1: Monthly Re-Roll Engine — Kaggle Notebook Builder
Builds: pair_trading_stage1.ipynb + kernel-metadata.json

Core execution logic is IDENTICAL to build_continuous_ols_pipeline_nb.py.
Only additions: live data fetch (Steps 0-4) and physics filter export (Step 5-6).
"""
import json, uuid, os

# ── Hardcoded Credentials (Private Kaggle notebook / Private GitHub repo) ──
FYERS_USERNAME   = "FAI84454"
FYERS_APP_ID     = "G0NX5M08ZG-100"
FYERS_SECRET_KEY = "D07VJ80FLH"
FYERS_TOTP_KEY   = "4QXQQACGALLZNFISHC5G7WU76AERBNYC"
FYERS_PIN        = "7475"
FYERS_REDIRECT   = "https://trade.fyers.in/api-login/redirect-uri/index.html"
KAGGLE_USER      = "utkarshpatelthefirst"
KAGGLE_KEY       = "fbef16329099428205f671dd5de8337b"

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

# ─────────────────────────────────────────────────────────────────────────────
md("""# NSE Pairs Trading — Stage 1: Monthly Re-Roll Engine
**Strategy**: Identify Top 50 cointegrated NSE pairs for the coming month.
**Steps**:
1. Fetch live NSE 500 list
2. Download exactly 120 trading days @ 1-min from Fyers API
3. 70% coverage filter
4. Continuous Vectorized OLS + Numba Backtest (identical execution engine)
5. Walk-Forward Physics Filter → Top 50 Pure pairs
6. Publish 4 CSVs to private Kaggle dataset
""")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 0: THREAD LOCK + IMPORTS
# ─────────────────────────────────────────────────────────────────────────────
md("## Step 0: Environment Setup & Imports")
code("""
import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import gc, json, time, sqlite3, shutil, re
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
from kaggle.api.kaggle_api_extended import KaggleApi

# Run date suffix used for all output filenames
RUN_DATE = datetime.now().strftime("%m-%d-%y")
print(f"Run Date Suffix: {RUN_DATE}")
print(f"Run Timestamp: {datetime.now().isoformat()}")
""")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: FYERS TOTP AUTHENTICATION
# ─────────────────────────────────────────────────────────────────────────────
md("## Step 1: Fyers API Authentication (5-Step TOTP)")
code(f"""
fy_id        = "{FYERS_USERNAME}"
app_id_full  = "{FYERS_APP_ID}"
secret_key   = "{FYERS_SECRET_KEY}"
totp_key     = "{FYERS_TOTP_KEY}"
pin          = "{FYERS_PIN}"
redirect_uri = "{FYERS_REDIRECT}"

# Step 1: Send OTP
res1 = requests.post("https://api-t2.fyers.in/vagator/v2/send_login_otp",
                     json={{"fy_id": fy_id, "app_id": "2"}}).json()
assert "request_key" in res1, f"Step 1 failed: {{res1}}"
req_key = res1["request_key"]

# Step 2: Verify TOTP
res2 = requests.post("https://api-t2.fyers.in/vagator/v2/verify_otp",
                     json={{"request_key": req_key,
                            "otp": pyotp.TOTP(totp_key).now()}}).json()
assert "request_key" in res2, f"Step 2 failed: {{res2}}"
req_key = res2["request_key"]

# Step 3: Verify PIN
res3 = requests.post("https://api-t2.fyers.in/vagator/v2/verify_pin",
                     json={{"request_key": req_key,
                            "identity_type": "pin",
                            "identifier": pin}}).json()
assert "data" in res3, f"Step 3 failed: {{res3}}"
access_token = res3["data"]["access_token"]

# Step 4: Get Auth Code
auth_payload = {{
    "fyers_id": fy_id, "app_id": app_id_full[:-4],
    "redirect_uri": redirect_uri, "appType": "100",
    "code_challenge": "", "state": "stage1",
    "scope": "", "nonce": "", "response_type": "code", "create_cookie": True
}}
res4 = requests.post("https://api-t1.fyers.in/api/v3/token", json=auth_payload,
                     headers={{"Authorization": f"Bearer {{access_token}}"}}).json()
assert "Url" in res4, f"Step 4 failed: {{res4}}"
auth_code = parse_qs(urlparse(res4["Url"]).query)["auth_code"][0]

# Step 5: Generate Token
session = fyersModel.SessionModel(client_id=app_id_full, secret_key=secret_key,
                                   redirect_uri=redirect_uri, response_type="code",
                                   grant_type="authorization_code")
session.set_token(auth_code)
fyers_token = session.generate_token()["access_token"]

fyers = fyersModel.FyersModel(client_id=app_id_full, is_async=False,
                               token=fyers_token, log_path="/kaggle/working/")
print("✅ Fyers Authentication Successful")
""")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: LIVE NSE 500 LIST
# ─────────────────────────────────────────────────────────────────────────────
md("## Step 2: Live NSE 500 Symbol Fetch")
code("""
req = urllib.request.Request(
    "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv",
    headers={"User-Agent": "Mozilla/5.0"}
)
with urllib.request.urlopen(req, timeout=30) as resp:
    nse_df = pd.read_csv(StringIO(resp.read().decode("utf-8")))

nse_symbols = nse_df["Symbol"].dropna().str.strip().tolist()
print(f"✅ NSE 500 list fetched: {len(nse_symbols)} symbols")

# Save NSE-500 file
nse_out = f"NSE-500_{RUN_DATE}.csv"
pd.DataFrame({"symbol": nse_symbols}).to_csv(nse_out, index=False)
print(f"Saved: {nse_out}")
""")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: DOWNLOAD EXACTLY 120 TRADING DAYS @ 1-MIN FROM FYERS
# ─────────────────────────────────────────────────────────────────────────────
md("## Step 3: Download 120 Exact Trading Days (1-min close) from Fyers")
code("""
# Download 2 chunks of ≤90 calendar days each (covers 180 cal days = well over 120 trading days)
today = datetime.now()
chunk_end_1   = today
chunk_start_1 = today - timedelta(days=90)
chunk_end_2   = chunk_start_1 - timedelta(days=1)
chunk_start_2 = chunk_end_2 - timedelta(days=90)

date_fmt = "%Y-%m-%d"
chunks = [
    (chunk_start_2.strftime(date_fmt), chunk_end_2.strftime(date_fmt)),
    (chunk_start_1.strftime(date_fmt), chunk_end_1.strftime(date_fmt)),
]
print(f"Chunk 1: {chunks[0][0]} to {chunks[0][1]}")
print(f"Chunk 2: {chunks[1][0]} to {chunks[1][1]}")

all_data = {}   # {symbol: list of [timestamp_int, close_float]}
errors_fetch = {}

REQUIRED_TRADING_DAYS = 120
SESSION_BARS = 375
MIN_REQUIRED_BARS = int(REQUIRED_TRADING_DAYS * SESSION_BARS * 0.70)  # 70% coverage threshold

total = len(nse_symbols)
for idx, sym in enumerate(nse_symbols):
    fyers_sym = f"NSE:{sym}-EQ"
    sym_rows = []
    for (s_date, e_date) in chunks:
        payload = {
            "symbol": fyers_sym, "resolution": "1",
            "date_format": "1",
            "range_from": s_date, "range_to": e_date,
            "cont_flag": "1"
        }
        try:
            resp = fyers.history(data=payload)
            if resp.get("s") == "ok" and resp.get("candles"):
                for candle in resp["candles"]:
                    sym_rows.append([int(candle[0]), float(candle[4])])  # [timestamp, close]
            else:
                errors_fetch.setdefault(sym, []).append(resp.get("message", "empty"))
        except Exception as e:
            errors_fetch.setdefault(sym, []).append(str(e))
        time.sleep(0.5)
    
    if sym_rows:
        all_data[sym] = sorted(sym_rows, key=lambda x: x[0])
    
    if (idx + 1) % 50 == 0:
        print(f"  Downloaded {idx+1}/{total} symbols...")

print(f"\\n✅ Raw fetch complete: {len(all_data)} symbols with data")
print(f"   Fetch errors: {len(errors_fetch)} symbols")
""")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: EXACT 120 TRADING DAY TRIM + CONTINUOUS PRICE MATRIX
# ─────────────────────────────────────────────────────────────────────────────
md("## Step 4: Trim to Exactly 120 Trading Days & Build Price Matrix")
code("""
# Identify the exact 120 most recent unique trading dates across all symbols
# (Self-validating: we use actual data dates, no holiday calendar dependency)
all_dates = set()
for sym, rows in all_data.items():
    for ts, close in rows:
        dt = datetime.utcfromtimestamp(ts) + timedelta(hours=5, minutes=30)  # UTC → IST
        all_dates.add(dt.date())

sorted_dates = sorted(all_dates)
if len(sorted_dates) < REQUIRED_TRADING_DAYS:
    raise RuntimeError(f"Only {len(sorted_dates)} trading dates found, need {REQUIRED_TRADING_DAYS}")

keep_dates = set(sorted_dates[-REQUIRED_TRADING_DAYS:])
date_min = min(keep_dates)
date_max = max(keep_dates)
print(f"Keeping exactly {REQUIRED_TRADING_DAYS} trading dates: {date_min} → {date_max}")

# Build price records filtered to those 120 dates, IST trading hours 9:15–15:29
price_records = []
for sym, rows in all_data.items():
    for ts, close in rows:
        ist_dt = datetime.utcfromtimestamp(ts) + timedelta(hours=5, minutes=30)
        if ist_dt.date() not in keep_dates:
            continue
        time_int = ist_dt.hour * 100 + ist_dt.minute
        if time_int < 915 or time_int > 1529:
            continue
        price_records.append({"symbol": sym, "ts": ist_dt, "close": close})

print(f"Total 1-min bars after trim: {len(price_records):,}")

price_df_raw = pd.DataFrame(price_records)
price_matrix = price_df_raw.pivot(index="ts", columns="symbol", values="close")
del price_df_raw; gc.collect()

print(f"Price matrix shape: {price_matrix.shape}")
""")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5: 70% COVERAGE FILTER
# ─────────────────────────────────────────────────────────────────────────────
md("## Step 5: 70% Coverage Filter")
code("""
TOTAL_EXPECTED_BARS = REQUIRED_TRADING_DAYS * SESSION_BARS  # 120 × 375 = 45,000
MIN_BARS = int(TOTAL_EXPECTED_BARS * 0.70)  # 31,500

coverage_counts = price_matrix.count()
low_coverage = coverage_counts[coverage_counts < MIN_BARS].index.tolist()
good_symbols  = coverage_counts[coverage_counts >= MIN_BARS].index.tolist()

print(f"Total symbols in matrix : {len(coverage_counts)}")
print(f"Symbols ≥70% coverage   : {len(good_symbols)}")
print(f"Symbols <70% (excluded) : {len(low_coverage)}")

# Save low-coverage list (usually empty for established NSE 500 stocks)
le70_out = f"le_70_coverage_{RUN_DATE}.csv"
pd.DataFrame({"symbol": low_coverage}).to_csv(le70_out, index=False)
print(f"Saved: {le70_out}")

# Filter matrix to good symbols only
price_matrix = price_matrix[good_symbols]
log_prices = np.log(price_matrix)
print(f"Final price matrix: {price_matrix.shape}")
""")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 6: PEARSON SCREENING (identical to reference)
# ─────────────────────────────────────────────────────────────────────────────
md("## Step 6: Pairwise Pearson Correlation Screening")
code("""
dates_arr = np.array(price_matrix.index.date)
session_open_mask = np.concatenate([[True], dates_arr[1:] != dates_arr[:-1]])

log_returns = log_prices - log_prices.shift(1)
log_returns_arr = log_returns.copy()
log_returns_arr.iloc[session_open_mask] = np.nan

print("Computing pairwise Pearson correlation...")
corr_df = log_returns_arr.corr(method="pearson")

symbols = corr_df.columns.tolist()
rows = []
for i in range(len(symbols)):
    for j in range(i + 1, len(symbols)):
        rho = corr_df.iloc[i, j]
        if np.isnan(rho): continue
        n_pair = log_returns_arr[[symbols[i], symbols[j]]].dropna().shape[0]
        if n_pair < 5000: continue
        t_stat = rho * np.sqrt((n_pair - 2) / max(1.0 - rho**2, 1e-12))
        p_val  = 2 * t_dist.sf(abs(t_stat), df=n_pair - 2)
        if p_val >= 0.05: continue
        rows.append({"symbol_a": symbols[i], "symbol_b": symbols[j],
                     "pearson_rho": round(rho, 6)})

pairs_df = pd.DataFrame(rows).sort_values("pearson_rho", ascending=False).reset_index(drop=True)
TOP_PAIRS = list(zip(pairs_df["symbol_a"], pairs_df["symbol_b"]))
print(f"\\n✅ {len(TOP_PAIRS)} production pairs for execution")
""")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 7: NUMBA ENGINE (IDENTICAL to build_continuous_ols_pipeline_nb.py)
# ─────────────────────────────────────────────────────────────────────────────
md("## Step 7: Numba Execution Engine (Continuous Vectorized OLS)")
code("""
ROLLING_WINDOW = 7500   # 20 trading days × 375 bars
ZSCORE_WINDOW  = 7500
Z_ENTRY        = 2.0
EOD_EXIT_TIME  = 1515
BASE_CAPITAL   = 10_000.0
LEVERAGE       = 5.0
POS_SIZE       = BASE_CAPITAL * LEVERAGE

@numba.njit
def calc_zerodha_friction(price, qty, is_buy):
    val      = price * qty
    brokerage = min(val * 0.0003, 20.0)
    stt      = 0.0 if is_buy else val * 0.00025
    exc      = val * 0.0000325
    gst      = (brokerage + exc) * 0.18
    sebi     = val * 0.000001
    stamp    = val * 0.00003 if is_buy else 0.0
    return brokerage + stt + exc + gst + sebi + stamp

@numba.njit
def _numba_backtest_loop(z_scores, raw_prices, is_eod, z_window, z_entry,
                          base_cap, pos_size, lagger_is_a):
    cash         = base_cap
    pos_qty      = 0
    pos_type     = 0
    entry_px     = 0.0
    entry_z_sign = 0.0
    is_locked_out = False

    total_trades    = 0
    winning_trades  = 0
    gross_pnl       = 0.0
    total_fees      = 0.0
    mean_rev_exits  = 0
    eod_exits       = 0
    gross_wins      = 0
    sum_price_captured = 0.0

    n = len(z_scores)
    for t in range(z_window, n):
        z     = z_scores[t]
        price = raw_prices[t]

        if np.isnan(z) or np.isnan(price) or price <= 0:
            continue

        # Unlock after forced EOD exit once Z-Score decays back toward 0
        if is_locked_out and (-1.0 < z < 1.0):
            is_locked_out = False

        if pos_qty > 0:
            exit_now    = False
            is_eod_exit = False
            if is_eod[t]:
                exit_now    = True
                is_eod_exit = True
            elif entry_z_sign >= 1.0 and z <= 0:
                exit_now = True
            elif entry_z_sign <= -1.0 and z >= 0:
                exit_now = True

            if exit_now:
                if pos_type == 1:
                    gross         = (price - entry_px) * pos_qty
                    friction_exit = calc_zerodha_friction(price, pos_qty, False)
                    friction_entry = calc_zerodha_friction(entry_px, pos_qty, True)
                else:
                    gross         = (entry_px - price) * pos_qty
                    friction_exit = calc_zerodha_friction(price, pos_qty, True)
                    friction_entry = calc_zerodha_friction(entry_px, pos_qty, False)

                total_fees += (friction_entry + friction_exit)
                net         = gross - friction_exit
                cash       += net
                gross_pnl  += gross

                total_trades += 1
                if net > 0:
                    winning_trades += 1
                if gross > 0:
                    gross_wins += 1

                sum_price_captured += (abs(price - entry_px) if gross > 0
                                       else -abs(price - entry_px))

                if is_eod_exit:
                    eod_exits    += 1
                    is_locked_out = True
                else:
                    mean_rev_exits += 1

                pos_qty  = 0
                pos_type = 0

        if pos_qty == 0 and not is_eod[t] and not is_locked_out:
            if z <= -z_entry or z >= z_entry:
                qty = int(pos_size // price)
                if qty > 0:
                    entry_px     = price
                    pos_qty      = qty
                    entry_z_sign = 1.0 if z >= z_entry else -1.0

                    if z >= z_entry:
                        pos_type = -1 if lagger_is_a else 1
                    else:
                        pos_type = 1 if lagger_is_a else -1

                    is_buy_entry = (pos_type == 1)
                    cash -= calc_zerodha_friction(price, qty, is_buy_entry)

    return (cash - base_cap, gross_pnl, total_trades, winning_trades,
            gross_wins, mean_rev_exits, eod_exits, sum_price_captured, total_fees)

def run_backtest_numba(spread, raw_prices, timestamps, lagger_is_a):
    spread_s  = pd.Series(spread)
    roll_mean = spread_s.rolling(ZSCORE_WINDOW).mean()
    roll_std  = spread_s.rolling(ZSCORE_WINDOW).std()
    z_scores  = ((spread_s - roll_mean) / roll_std.replace(0, np.nan)).to_numpy()

    time_int = timestamps.hour * 100 + timestamps.minute
    is_eod   = np.asarray(time_int == EOD_EXIT_TIME)

    (net_pnl, gross_pnl, total_trades, winning_trades, gross_wins,
     mean_rev_exits, eod_exits, sum_price_captured, total_fees) = _numba_backtest_loop(
        z_scores, raw_prices, is_eod,
        ZSCORE_WINDOW, Z_ENTRY, BASE_CAPITAL, POS_SIZE, lagger_is_a
    )

    net_win_rate       = winning_trades / total_trades if total_trades > 0 else 0.0
    gross_win_rate     = gross_wins / total_trades if total_trades > 0 else 0.0
    avg_price_captured = sum_price_captured / total_trades if total_trades > 0 else 0.0
    avg_fee_drag       = total_fees / total_trades if total_trades > 0 else 0.0

    # ── Physical Parameter Extraction ──
    clean_spread  = spread[~np.isnan(spread)]
    spread_vol    = np.std(clean_spread) if len(clean_spread) > 0 else 0.0
    mean_abs_dev  = np.mean(np.abs(clean_spread)) if len(clean_spread) > 0 else 0.0

    signs          = np.sign(clean_spread)
    zero_crossings = np.sum(signs[:-1] != signs[1:]) if len(clean_spread) > 1 else 0

    half_life = np.nan
    q_val     = np.nan
    if len(clean_spread) > 2:
        y_t   = clean_spread[1:]
        y_t_1 = clean_spread[:-1]
        cov_m = np.cov(y_t_1, y_t)
        if cov_m[0, 0] > 0:
            beta_ou = cov_m[0, 1] / cov_m[0, 0]
            if 0 < beta_ou < 1:
                half_life = -np.log(2) / np.log(beta_ou)
                q_val     = spread_vol**2 * (1 - np.exp(-2 * np.log(2) / half_life))

    return (net_pnl, gross_pnl, total_trades, net_win_rate, gross_win_rate,
            mean_rev_exits, eod_exits, avg_price_captured, avg_fee_drag,
            spread_vol, mean_abs_dev, zero_crossings, half_life, q_val)

def detect_lagger(ya, yb, timestamps, warmup_bars=7500):
    if len(ya) < warmup_bars + 2:
        return "a"
    ret_a    = np.diff(ya[:warmup_bars])
    ret_b    = np.diff(yb[:warmup_bars])
    time_ints = timestamps[:warmup_bars].hour * 100 + timestamps[:warmup_bars].minute
    is_not_915 = (time_ints[1:] != 915)
    ret_a    = np.where(is_not_915, ret_a, 0.0)
    ret_b    = np.where(is_not_915, ret_b, 0.0)
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

    df_pair = log_prices[[sym_a, sym_b]].dropna(how="any")
    ya, yb  = df_pair[sym_a], df_pair[sym_b]
    times   = df_pair.index

    if len(ya) <= ZSCORE_WINDOW:
        return None

    lagger_side  = detect_lagger(ya.values, yb.values, times, ROLLING_WINDOW)
    lagger_is_a  = (lagger_side == "a")
    lagger_sym   = sym_a if lagger_is_a else sym_b
    raw_px       = price_matrix[lagger_sym].loc[times].to_numpy()

    # Vectorized Continuous Rolling OLS
    roll_cov = ya.rolling(window=ROLLING_WINDOW).cov(yb)
    roll_var = yb.rolling(window=ROLLING_WINDOW).var()
    beta     = roll_cov / roll_var
    alpha    = (ya.rolling(window=ROLLING_WINDOW).mean()
                - beta * yb.rolling(window=ROLLING_WINDOW).mean())
    spread   = ya - (alpha + beta * yb)

    # Execution Engine Backtest
    (net_pnl, gross_pnl, trades, net_win_rate, gross_win_rate,
     mean_rev_exits, eod_exits, avg_price_captured, avg_fee_drag,
     spread_vol, mean_abs_dev, zero_cross, half_life, q_val) = run_backtest_numba(
        spread.to_numpy(), raw_px, times, lagger_is_a
    )

    # Lazy ADF — only run if mathematically profitable
    adf_stat, pval = np.nan, np.nan
    if net_pnl > 0:
        clean_spread = spread.dropna()
        if len(clean_spread) > 100:
            try:
                res      = adfuller(clean_spread, maxlag=1)
                adf_stat = res[0]
                pval     = res[1]
            except Exception:
                pass

    return {
        "pair"               : f"{sym_a}-{sym_b}",
        "lagger_asset"       : lagger_sym,
        "ols_gross_pnl"      : round(gross_pnl, 2),
        "ols_net_pnl"        : round(net_pnl, 2),
        "ols_trades"         : trades,
        "gross_win_rate"     : round(gross_win_rate, 4),
        "net_win_rate"       : round(net_win_rate, 4),
        "mean_rev_exits"     : mean_rev_exits,
        "eod_exits"          : eod_exits,
        "avg_price_captured" : round(avg_price_captured, 4),
        "avg_fee_drag"       : round(avg_fee_drag, 4),
        "spread_vol"         : round(spread_vol, 6),
        "mean_abs_dev"       : round(mean_abs_dev, 6),
        "zero_crossings"     : zero_cross,
        "half_life"          : round(half_life, 2) if not np.isnan(half_life) else "",
        "kalman_q"           : round(q_val, 8) if not np.isnan(q_val) else "",
        "adf_stat"           : round(adf_stat, 4) if not np.isnan(adf_stat) else "",
        "adf_pval"           : round(pval, 6) if not np.isnan(pval) else "",
    }

# Warm-up compile (avoids first-call JIT overhead inside joblib workers)
print("Compiling Numba engine...")
_dummy = _numba_backtest_loop(
    np.array([1.0]*8000), np.array([100.0]*8000), np.array([False]*8000),
    ZSCORE_WINDOW, Z_ENTRY, BASE_CAPITAL, POS_SIZE, True
)
print("✅ Numba JIT compiled")
""")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 8: MASSIVE JOBLIB PARALLEL SWEEP
# ─────────────────────────────────────────────────────────────────────────────
md("## Step 8: Massive Parallel Sweep — All Pairs")
code("""
print(f"Executing Joblib parallel sweep across {len(TOP_PAIRS)} pairs (4 CPUs)...")
results_st3 = Parallel(n_jobs=-1, batch_size="auto")(
    delayed(process_pair)(pair) for pair in TOP_PAIRS
)
results_st3 = [r for r in results_st3 if r is not None]

ranked_df = pd.DataFrame(results_st3).sort_values("ols_net_pnl", ascending=False).reset_index(drop=True)

ranked_out = f"Ranked_Profit_All_{RUN_DATE}.csv"
ranked_df.to_csv(ranked_out, index=False)
print(f"✅ Saved: {ranked_out}  ({len(ranked_df)} pairs)")
display(ranked_df.head(20))
""")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 9: WALK-FORWARD PHYSICS FILTER → TOP 50 PURE
# ─────────────────────────────────────────────────────────────────────────────
md("## Step 9: Walk-Forward Physics Filter — Top 50 Pure Pairs")
code("""
# Physics bounds derived from the 124,750-pair sweep analysis (2026-06-13)
ADF_PVAL_LIMIT    = 0.005    # p < 0.005 → 99.5% cointegration confidence
SPREAD_VOL_LIMIT  = 0.045    # spread_vol > 0.045 → wide enough to beat fees
HALF_LIFE_LIMIT   = 1000.0   # half_life < 1000 bars (~2.7 trading days)
KALMAN_Q_LIMIT    = 3.0e-06  # kalman_q > 3e-06 → enough elasticity for entries

def parse_float(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return float("nan")

mask = (
    (ranked_df["adf_pval"].apply(parse_float) < ADF_PVAL_LIMIT) &
    (ranked_df["spread_vol"].apply(parse_float) > SPREAD_VOL_LIMIT) &
    (ranked_df["half_life"].apply(parse_float) < HALF_LIFE_LIMIT) &
    (ranked_df["kalman_q"].apply(parse_float) > KALMAN_Q_LIMIT)
)

top50_df = ranked_df[mask].head(50).reset_index(drop=True)

top50_out = f"Top_50_Pure_{RUN_DATE}.csv"
top50_df.to_csv(top50_out, index=False)
print(f"✅ Saved: {top50_out}  ({len(top50_df)} pairs passed physics filter)")
print(f"   Filter rejection rate: {100*(1 - len(top50_df)/max(1,mask.sum())):.1f}%")
display(top50_df)
""")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 10: PUBLISH ALL 4 CSVs TO PRIVATE KAGGLE DATASET
# ─────────────────────────────────────────────────────────────────────────────
md("## Step 10: Publish Outputs to Private Kaggle Dataset")
code(f"""
import json, shutil
from kaggle.api.kaggle_api_extended import KaggleApi

os.environ["KAGGLE_USERNAME"] = "{KAGGLE_USER}"
os.environ["KAGGLE_KEY"]      = "{KAGGLE_KEY}"

api = KaggleApi()
api.authenticate()

export_dir = "/kaggle/working/stage1_export"
os.makedirs(export_dir, exist_ok=True)

output_files = [
    f"NSE-500_{{RUN_DATE}}.csv",
    f"le_70_coverage_{{RUN_DATE}}.csv",
    f"Ranked_Profit_All_{{RUN_DATE}}.csv",
    f"Top_50_Pure_{{RUN_DATE}}.csv",
]
for fname in output_files:
    if os.path.exists(fname):
        shutil.copy(fname, f"{{export_dir}}/{{fname}}")
        print(f"  Staged: {{fname}}")

meta = {{
    "title"    : "Pairs Trading Stage 1 Outputs",
    "id"       : "{KAGGLE_USER}/pairs-stage1-outputs",
    "licenses" : [{{"name": "CC0-1.0"}}],
    "isPrivate": True
}}
with open(f"{{export_dir}}/dataset-metadata.json", "w") as f:
    json.dump(meta, f, indent=2)

try:
    api.dataset_create_new(export_dir, dir_mode="zip", quiet=False)
    print("✅ Dataset created (first run)")
except Exception as e:
    if "already exists" in str(e).lower() or "409" in str(e):
        api.dataset_create_version(
            export_dir, f"Stage1-Run-{{RUN_DATE}}", dir_mode="zip", quiet=False
        )
        print(f"✅ Dataset updated: Stage1-Run-{{RUN_DATE}}")
    else:
        raise e

print("\\n✅ All 4 Stage 1 output files published to private Kaggle dataset.")
print(f"   Dataset: https://www.kaggle.com/datasets/{KAGGLE_USER}/pairs-stage1-outputs")
""")

# ─────────────────────────────────────────────────────────────────────────────
# BUILD NOTEBOOK + KERNEL METADATA
# ─────────────────────────────────────────────────────────────────────────────
notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.10.12"}
    },
    "nbformat": 4, "nbformat_minor": 5
}

kernel_meta = {
    "id"          : f"{KAGGLE_USER}/pairs-trading-stage1-monthly",
    "title"       : "Pairs Trading Stage 1 Monthly Re-Roll",
    "code_file"   : "pair_trading_stage1.ipynb",
    "language"    : "python",
    "kernel_type" : "notebook",
    "is_private"  : "true",
    "enable_gpu"  : "false",
    "enable_internet": "true",
    "dataset_sources": [],
    "competition_sources": [], "kernel_sources": [], "model_sources": []
}

OUT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "kaggle_staging", "stage1_monthly"
)
os.makedirs(OUT_DIR, exist_ok=True)
with open(os.path.join(OUT_DIR, "pair_trading_stage1.ipynb"), "w") as f:
    json.dump(notebook, f, indent=2)
with open(os.path.join(OUT_DIR, "kernel-metadata.json"), "w") as f:
    json.dump(kernel_meta, f, indent=2)

print(f"\n✅ Stage 1 notebook written to: {OUT_DIR}")
