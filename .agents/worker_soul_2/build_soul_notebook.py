import json
import os
import uuid

# Define the target path
TARGET_NOTEBOOK_PATH = "/storage/emulated/0/Quant/LLM-WIKI/Soul/Master_Pairs_Trading_Soul.ipynb"

# Ensure the output directory exists
os.makedirs(os.path.dirname(TARGET_NOTEBOOK_PATH), exist_ok=True)

# Helper function to generate cells with random UUIDs for nbformat 4.5 compliance
def md_cell(source_text):
    return {
        "id": str(uuid.uuid4())[:8],
        "cell_type": "markdown",
        "metadata": {},
        "source": source_text.strip().splitlines(keepends=True)
    }

def code_cell(source_code):
    return {
        "id": str(uuid.uuid4())[:8],
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source_code.strip().splitlines(keepends=True)
    }

cells = []

# --- CELL 0: Setup & Path Discovery ---
cells.append(code_cell("""
# --- Setup & Path Discovery ---
import os
import glob
import gc
import time
import datetime
import warnings
import sqlite3
import numpy as np
import pandas as pd
from scipy.stats import t as t_dist
from statsmodels.tsa.stattools import adfuller

# Set thread environment variables before importing numpy
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

warnings.filterwarnings("ignore")

print("=== /kaggle/input Contents ===")
for root, dirs, files in os.walk('/kaggle/input'):
    for f in files:
        fpath = os.path.join(root, f)
        print(f"  {fpath}  ({os.path.getsize(fpath)/(1024**3):.2f} GB)")

# Discover SQLite database
hits = glob.glob('/kaggle/input/**/*.sqlite', recursive=True)
if not hits:
    raise FileNotFoundError("No .sqlite database found under /kaggle/input")
DB_PATH = hits[0]
print(f"\\n✅ DB_PATH = {DB_PATH}")
"""))

# --- CELL 1: Stage 1 Markdown ---
cells.append(md_cell("""
## Stage 1 — Pearson Correlation Screening
**Input:** `Master-Data-1min.sqlite` path.  
**Output:** `pairs_all.csv`, `pairs_top500.csv`.  
**Core Logic:**
1. Load all prices from the database.
2. Filter to NSE trading hours: **09:15 to 15:29 IST** inclusive.
3. Pivot close prices to a `(timestamp x symbol)` matrix.
4. Two-pass smart alignment:
   - Pass 1: Drop symbols with < 80% coverage.
   - Forward-fill remaining price gaps by at most 1 bar.
   - Pass 2: Inner-join on survivors (drop rows with remaining NaNs).
5. Calculate log-returns: $r_t = \\ln(P_t / P_{t-1})$ individually.
6. Mask overnight returns: set 09:15 open bars' return to NaN.
7. Compute the Pearson correlation matrix (GPU if available, else CPU).
8. Compute t-statistic:
   $$t = \\rho \\sqrt{\\frac{n - 2}{1 - \\rho^2}}$$
   and p-value using the t-distribution.
9. Select pairs with p-value < 0.05 and $n\\_obs \\ge 5000$.
10. Rank by correlation, output top 500 pairs and all pairs.
11. Split aligned data into In-Sample (IS - first 70%) and Out-of-Sample (OOS - final 30%).
"""))

# --- CELL 2: Stage 1 Code ---
cells.append(code_cell("""
# --- Stage 1 Ingestion, Alignment & Pearson Screening ---
t0 = time.time()
con = sqlite3.connect(DB_PATH)
df = pd.read_sql("SELECT symbol, timestamp, open, close FROM ohlcv_1min ORDER BY timestamp", con)
con.close()
print(f"Loaded {len(df):,} rows in {time.time()-t0:.2f}s")

# Restrict to NSE trading hours: 09:15 to 15:29 IST inclusive
df['dt'] = pd.to_datetime(df['timestamp'], unit='s', utc=True).dt.tz_convert('Asia/Kolkata')
MARKET_OPEN = datetime.time(9, 15)
MARKET_CLOSE = datetime.time(15, 29)

df_trading = df[(df['dt'].dt.time >= MARKET_OPEN) & (df['dt'].dt.time <= MARKET_CLOSE)].copy()
print(f"Intraday rows: {len(df_trading):,}")

# Drop duplicates to prevent pivot issues
df_trading = df_trading.drop_duplicates(subset=['dt', 'symbol'])

# Pivot close and open prices
price_matrix_close = df_trading.pivot(index='dt', columns='symbol', values='close')
price_matrix_open = df_trading.pivot(index='dt', columns='symbol', values='open')
n_total_bars = len(price_matrix_close)
print(f"Close matrix pivot shape: {price_matrix_close.shape}")

# Pass 1: Drop symbols with < 80% coverage
coverage = price_matrix_close.notna().sum() / n_total_bars
sparse_symbols = coverage[coverage < 0.80].index.tolist()
if sparse_symbols:
    print(f"Dropping {len(sparse_symbols)} sparse symbols (<80% coverage)")
    price_matrix_close = price_matrix_close.drop(columns=sparse_symbols)
    price_matrix_open = price_matrix_open.drop(columns=sparse_symbols)

# Forward-fill remaining close and open price gaps by at most 1 bar
price_matrix_close = price_matrix_close.ffill(limit=1)
price_matrix_open = price_matrix_open.ffill(limit=1)

# Pass 2: Inner join on survivors (drop timestamps missing ANY survivor)
price_matrix_close = price_matrix_close.dropna(how='any', axis=0)
common_idx = price_matrix_close.index
price_matrix_open = price_matrix_open.loc[common_idx]

print(f"Aligned Close Matrix shape: {price_matrix_close.shape}")
print(f"Aligned Open Matrix shape: {price_matrix_open.shape}")
assert price_matrix_close.shape[0] >= 5000, f"Too few aligned bars: {price_matrix_close.shape[0]}"

# Compute log-returns
log_returns_raw = np.log(price_matrix_close / price_matrix_close.shift(1))
# Mask overnight returns: set 09:15 open bars to NaN
session_open_mask = (price_matrix_close.index.time == MARKET_OPEN)
log_returns_raw[session_open_mask] = np.nan
log_returns = log_returns_raw.dropna(how='any')
print(f"Log returns matrix shape: {log_returns.shape}")

# Compute Pearson correlation matrix
print("Computing correlation matrix...")
try:
    import cudf
    lr_gpu = cudf.DataFrame(log_returns)
    corr_df = lr_gpu.corr().to_pandas()
    print("✅ GPU correlation complete")
except Exception as e:
    print(f"GPU path failed ({e}) — using CPU")
    corr_df = log_returns.corr(method='pearson')

# Extract pairs and compute significance
symbols = corr_df.columns.tolist()
n_sym = len(symbols)
n_obs = len(log_returns)
corr_vals = corr_df.values
rows = []

print(f"Processing upper-triangle pairs...")
for i in range(n_sym):
    for j in range(i + 1, n_sym):
        rho = corr_vals[i, j]
        if np.isnan(rho):
            continue
        rho = float(np.clip(rho, -0.999999, 0.999999))
        t_stat = rho * np.sqrt((n_obs - 2) / (1.0 - rho**2))
        p_val = 2.0 * t_dist.sf(abs(t_stat), df=n_obs - 2)
        rows.append((symbols[i], symbols[j], rho, t_stat, p_val, n_obs))

pairs_df = pd.DataFrame(rows, columns=['symbol_a', 'symbol_b', 'pearson_rho', 't_stat', 'p_value', 'n_obs'])
print(f"Total pairs before filter: {len(pairs_df):,}")

# Filter: p-value < 0.05 & n_obs >= 5000
pairs_df = pairs_df[(pairs_df['p_value'] < 0.05) & (pairs_df['n_obs'] >= 5000)].copy()
pairs_df = pairs_df.sort_values('pearson_rho', ascending=False).reset_index(drop=True)
pairs_df['rank'] = pairs_df.index + 1

# Export to CSVs
pairs_df.to_csv('pairs_all.csv', index=False)
pairs_df.head(500).to_csv('pairs_top500.csv', index=False)
print(f"Saved pairs_all.csv ({len(pairs_df)} rows) and pairs_top500.csv (500 rows)")

# Split aligned series into In-Sample (IS - first 70%) and Out-of-Sample (OOS - final 30%)
T = len(price_matrix_close)
T_is = int(0.7 * T)
dt_is = price_matrix_close.index[:T_is]
dt_oos = price_matrix_close.index[T_is:]
print(f"In-Sample period: {dt_is[0]} to {dt_is[-1]} ({len(dt_is)} bars)")
print(f"Out-of-Sample period: {dt_oos[0]} to {dt_oos[-1]} ({len(dt_oos)} bars)")
"""))

# --- CELL 3: Stage 2 Markdown ---
cells.append(md_cell("""
## Stage 2 — Kalman Filter & EM Calibration (In-Sample Only)
**Input:** Top 500 pairs from Stage 1, In-Sample prices.  
**Output:** `pairs_stage2_kalman_ou.csv`.  
**Core Logic:**
1. State vector $\\theta_t = [\\beta_t, \\alpha_t]^\\top$.
2. State covariance $P_0$ is initialized via OLS on the first day (390 bars):
   $$P_{0|0} = 10 \\cdot \\sigma^2 (X_{OLS}^\\top X_{OLS})^{-1}$$
3. Predict Step overnight process noise scaling (15.0x Q at 09:15 open transition):
   $$P_{t|t-1} = P_{t-1|t-1} + Q_{\\text{overnight}}$$
   where $Q_{\\text{overnight}} = 15.0 \\cdot Q$ if $is\\_new\\_day[t]$ else $Q$.
4. Expectation-Maximization (EM) loop to estimate $Q$ and $R$ on In-Sample data.
5. Complete EM M-step $Q$ updates using all cross-covariance terms and scaled overnight transition:
   $$Q_{\\text{correct}, t} = (P_{t|T} + \\hat{\\theta}_{t|T}\\hat{\\theta}_{t|T}^\\top) + (P_{t-1|T} + \\hat{\\theta}_{t-1|T}\\hat{\\theta}_{t-1|T}^\\top) - (P_{t, t-1|T} + \\hat{\\theta}_{t|T}\\hat{\\theta}_{t-1|T}^\\top) - (P_{t, t-1|T}^\\top + \\hat{\\theta}_{t-1|T}\\hat{\\theta}_{t|T}^\\top)$$
   $$Q_{\\text{weighted}, t} = Q_{\\text{correct}, t} / 15.0 \\quad \\text{if } is\\_new\\_day[t], \\quad \\text{else } Q_{\\text{correct}, t}$$
6. Fit smoothed spread to AR(1) model, reject unstable coefficients (require $0 < \\phi < 1$).
7. Run ADF test on spread computed using final fixed $\\beta_{mean}$ and $\\alpha_{mean}$.
8. Keep pairs with ADF p-value < 0.05 and half-life $5.0 \\le t_{1/2} \\le 120.0$.
"""))

# --- CELL 4: Stage 2 Code ---
cells.append(code_cell("""
# --- Stage 2 Kalman Filter & EM Calibration ---
import multiprocessing as mp
from scipy.stats import skew as sp_skew, kurtosis as sp_kurt

# Pre-load price cache for Stage 2
top500 = pd.read_csv('pairs_top500.csv')
s2_syms = sorted(set(top500['symbol_a'].tolist() + top500['symbol_b'].tolist()))
print(f"Stage 2 Unique symbols: {len(s2_syms)}")

# Slice Close prices to In-Sample only
price_cache_is = {sym: price_matrix_close.loc[dt_is, sym].values for sym in s2_syms}
is_new_day_is = (dt_is.time == MARKET_OPEN)

# Numba-optimized Kalman filter functions
try:
    from numba import njit
    NUMBA_AV = True
except ImportError:
    def njit(fn): return fn
    NUMBA_AV = False
print(f"Numba available for JIT: {NUMBA_AV}")

@njit
def _kf_forward_scaled(ya, yb, q1, q2, R_val, th0, P0, is_new_day):
    T = len(ya)
    tf = np.zeros((T, 2))
    Pf = np.zeros((T, 2, 2))
    tp = np.zeros((T, 2))
    Pp = np.zeros((T, 2, 2))
    e_a = np.zeros(T)
    S_a = np.zeros(T)
    K_a = np.zeros((T, 2))
    
    th0b = th0[0]; th1b = th0[1]
    p00 = P0[0, 0]; p01 = P0[0, 1]; p10 = P0[1, 0]; p11 = P0[1, 1]
    ll = 0.0
    LOG2PI = 1.8378770664093453
    
    for t in range(T):
        h0 = yb[t]; h1 = 1.0
        
        # Propagate covariance with overnight process noise scaling
        if t > 0 and is_new_day[t]:
            qq1 = 15.0 * q1
            qq2 = 15.0 * q2
        else:
            qq1 = q1
            qq2 = q2
            
        pp00 = p00 + qq1; pp01 = p01; pp10 = p10; pp11 = p11 + qq2
        
        tp[t, 0] = th0b; tp[t, 1] = th1b
        Pp[t, 0, 0] = pp00; Pp[t, 0, 1] = pp01; Pp[t, 1, 0] = pp10; Pp[t, 1, 1] = pp11
        
        # Innovation
        e = ya[t] - (h0 * th0b + h1 * th1b)
        hp0 = h0 * pp00 + h1 * pp10
        hp1 = h0 * pp01 + h1 * pp11
        S = h0 * hp0 + h1 * hp1 + R_val
        if S < 1e-10: S = 1e-10
        
        e_a[t] = e
        S_a[t] = S
        ll += -0.5 * (LOG2PI + np.log(S) + e * e / S)
        
        k0 = hp0 / S; k1 = hp1 / S
        K_a[t, 0] = k0; K_a[t, 1] = k1
        
        # Update
        th0b = th0b + k0 * e
        th1b = th1b + k1 * e
        
        ikh00 = 1.0 - k0 * h0; ikh01 = -k0 * h1
        ikh10 = -k1 * h0;     ikh11 = 1.0 - k1 * h1
        
        p00 = ikh00 * pp00 + ikh01 * pp10
        p01 = ikh00 * pp01 + ikh01 * pp11
        p10 = ikh10 * pp00 + ikh11 * pp10
        p11 = ikh10 * pp01 + ikh11 * pp11
        
        tf[t, 0] = th0b; tf[t, 1] = th1b
        Pf[t, 0, 0] = p00; Pf[t, 0, 1] = p01; Pf[t, 1, 0] = p10; Pf[t, 1, 1] = p11
        
    return tf, Pf, tp, Pp, e_a, S_a, K_a, ll

@njit
def _rts_backward(tf, Pf, tp, Pp):
    T = len(tf)
    ts = np.zeros((T, 2))
    Ps = np.zeros((T, 2, 2))
    Pc = np.zeros((T, 2, 2))
    
    ts[T-1, 0] = tf[T-1, 0]; ts[T-1, 1] = tf[T-1, 1]
    Ps[T-1, 0, 0] = Pf[T-1, 0, 0]; Ps[T-1, 0, 1] = Pf[T-1, 0, 1]
    Ps[T-1, 1, 0] = Pf[T-1, 1, 0]; Ps[T-1, 1, 1] = Pf[T-1, 1, 1]
    
    for t in range(T-2, -1, -1):
        a = Pp[t+1, 0, 0]; b = Pp[t+1, 0, 1]; c = Pp[t+1, 1, 0]; d = Pp[t+1, 1, 1]
        det = a * d - b * c
        if abs(det) < 1e-20: det = 1e-20
        i00 = d / det; i01 = -b / det; i10 = -c / det; i11 = a / det
        
        G00 = Pf[t, 0, 0] * i00 + Pf[t, 0, 1] * i10
        G01 = Pf[t, 0, 0] * i01 + Pf[t, 0, 1] * i11
        G10 = Pf[t, 1, 0] * i00 + Pf[t, 1, 1] * i10
        G11 = Pf[t, 1, 0] * i01 + Pf[t, 1, 1] * i11
        
        d0 = ts[t+1, 0] - tp[t+1, 0]; d1 = ts[t+1, 1] - tp[t+1, 1]
        ts[t, 0] = tf[t, 0] + G00 * d0 + G01 * d1
        ts[t, 1] = tf[t, 1] + G10 * d0 + G11 * d1
        
        dp00 = Ps[t+1, 0, 0] - Pp[t+1, 0, 0]; dp01 = Ps[t+1, 0, 1] - Pp[t+1, 0, 1]
        dp10 = Ps[t+1, 1, 0] - Pp[t+1, 1, 0]; dp11 = Ps[t+1, 1, 1] - Pp[t+1, 1, 1]
        
        gd00 = G00 * dp00 + G01 * dp10; gd01 = G00 * dp01 + G01 * dp11
        gd10 = G10 * dp00 + G11 * dp10; gd11 = G10 * dp01 + G11 * dp11
        
        Ps[t, 0, 0] = Pf[t, 0, 0] + gd00 * G00 + gd01 * G10
        Ps[t, 0, 1] = Pf[t, 0, 1] + gd00 * G01 + gd01 * G11
        Ps[t, 1, 0] = Pf[t, 1, 0] + gd10 * G00 + gd11 * G10
        Ps[t, 1, 1] = Pf[t, 1, 1] + gd10 * G01 + gd11 * G11
        
        Pc[t, 0, 0] = G00 * Ps[t+1, 0, 0] + G01 * Ps[t+1, 1, 0]
        Pc[t, 0, 1] = G00 * Ps[t+1, 0, 1] + G01 * Ps[t+1, 1, 1]
        Pc[t, 1, 0] = G10 * Ps[t+1, 0, 0] + G11 * Ps[t+1, 1, 0]
        Pc[t, 1, 1] = G10 * Ps[t+1, 0, 1] + G11 * Ps[t+1, 1, 1]
        
    return ts, Ps, Pc

def kalman_smoother_scaled(ya, yb, Q, R, is_new_day):
    T = len(ya)
    # P_0 Initialization: OLS on first 390 bars of In-Sample
    n_i = min(390, T // 4)
    Xols = np.column_stack([yb[:n_i], np.ones(n_i)])
    th0, _, _, _ = np.linalg.lstsq(Xols, ya[:n_i], rcond=None)
    resid = ya[:n_i] - Xols @ th0
    sigma2 = np.var(resid)
    XtX_inv = np.linalg.inv(Xols.T @ Xols)
    P0 = 10.0 * sigma2 * XtX_inv
    
    q1, q2, R_v = float(Q[0, 0]), float(Q[1, 1]), float(R)
    tf, Pf, tp, Pp, e_a, S_a, K_a, ll = _kf_forward_scaled(ya, yb, q1, q2, R_v, th0, P0, is_new_day)
    ts, Ps, Pc = _rts_backward(tf, Pf, tp, Pp)
    return ts, Ps, Pc, e_a, S_a, K_a, ll, th0

def em_kalman_scaled(ya, yb, is_new_day):
    T = len(ya)
    R = float(np.var(ya) * 0.01)
    Q = np.diag([1e-5, 1e-5])
    ll_prev = -np.inf
    em_conv = False
    ll_f = ll_prev
    
    for itr in range(15):  # Max 15 iterations
        ts, Ps, Pc, _, _, _, ll, _ = kalman_smoother_scaled(ya, yb, Q, R, is_new_day)
        
        H_m = np.column_stack([yb, np.ones(T)])
        res = ya - np.einsum("ti,ti->t", H_m, ts)
        HPH = np.einsum("ti,tij,tj->t", H_m, Ps, H_m)
        R_n = max(float(np.mean(res * res + HPH)), 1e-12)
        
        ts_t = ts[1:]
        ts_tm1 = ts[:-1]
        Ps_t = Ps[1:]
        Ps_tm1 = Ps[:-1]
        
        Pc_t_tm1 = np.zeros((T - 1, 2, 2))
        for i in range(T - 1):
            Pc_t_tm1[i] = Pc[i].T
            
        t_t_t = np.einsum("ti,tj->tij", ts_t, ts_t)
        t_tm1_tm1 = np.einsum("ti,tj->tij", ts_tm1, ts_tm1)
        t_t_tm1 = np.einsum("ti,tj->tij", ts_t, ts_tm1)
        t_tm1_t = np.einsum("ti,tj->tij", ts_tm1, ts_t)
        
        # Complete M-step Q update
        Q_correct = (Ps_t + t_t_t) + (Ps_tm1 + t_tm1_tm1) - (Pc_t_tm1 + t_t_tm1) - (Pc[:T-1] + t_tm1_t)
        
        Q_weighted = Q_correct.copy()
        for i in range(T - 1):
            if is_new_day[i + 1]:
                Q_weighted[i] = Q_correct[i] / 15.0
                
        Q_n = np.mean(Q_weighted, axis=0)
        Q_n = np.diag(np.diag((Q_n + Q_n.T) / 2.0))
        Q_n = np.clip(Q_n, 1e-12, None)
        
        dl = abs(ll - ll_prev)
        R = R_n
        Q = Q_n
        ll_prev = ll
        
        if dl < 1e-5 and itr > 2:
            em_conv = True
            ll_f = ll
            break
    else:
        ll_f = ll
        
    return Q, float(R), itr + 1, float(ll_f), em_conv

def hurst_rs(s, max_lag=100):
    lags = range(2, min(max_lag, len(s) // 2))
    tau  = [np.std(np.subtract(s[lag:], s[:-lag])) for lag in lags]
    if len(tau) < 4: return np.nan
    return float(np.polyfit(np.log(list(lags)), np.log(tau), 1)[0])

def fit_ou_scaled(spread):
    s = np.asarray(spread, dtype=np.float64)
    s = s[np.isfinite(s)]
    _nan = lambda: {k: np.nan for k in [
        "ou_kappa","ou_mu","ou_sigma","half_life_minutes","half_life_hours",
        "ar1_phi","ar1_c","hurst_exponent","spread_mean","spread_std"
    ]}
    if len(s) < 100: return _nan()
    
    x = s[:-1]
    y = s[1:]
    X = np.column_stack([np.ones(len(x)), x])
    b, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    c, phi = float(b[0]), float(b[1])
    
    if not (0.0 < phi < 1.0) or not np.isfinite(phi):
        return _nan()
        
    kappa = -np.log(phi)
    hl = np.log(2.0) / kappa
    resid = y - X @ b
    sig_ou = np.std(resid) * np.sqrt(-2.0 * np.log(phi) / (1.0 - phi**2))
    
    try:
        hurst = hurst_rs(s)
    except Exception:
        hurst = np.nan
        
    return {
        "spread_mean": float(np.mean(s)),
        "spread_std": float(np.std(s)),
        "ou_kappa": float(kappa),
        "ou_mu": float(c / (1.0 - phi)),
        "ou_sigma": float(sig_ou),
        "half_life_minutes": float(hl),
        "half_life_hours": float(hl / 60.0),
        "ar1_phi": phi,
        "ar1_c": float(c),
        "hurst_exponent": hurst,
    }

def process_pair(args):
    row = args
    sym_a, sym_b = row['symbol_a'], row['symbol_b']
    
    if sym_a not in price_cache_is or sym_b not in price_cache_is:
        return {"symbol_a": sym_a, "symbol_b": sym_b, "skipped": True}
        
    ya = np.log(price_cache_is[sym_a])
    yb = np.log(price_cache_is[sym_b])
    
    try:
        # Run EM to estimate diagonal Q and scalar R
        Q_opt, R_opt, em_iters, ll_em, em_conv = em_kalman_scaled(ya, yb, is_new_day_is)
        
        # Smoothed spread for OU
        ts, Ps, Pc, _, _, _, ll_f, _ = kalman_smoother_scaled(ya, yb, Q_opt, R_opt, is_new_day_is)
        H_m = np.column_stack([yb, np.ones(len(ya))])
        spread = ya - np.einsum("ti,ti->t", H_m, ts)
        
        ou = fit_ou_scaled(spread)
        
        # ADF Stationarity filter on spread using final fixed mean beta & alpha
        beta_mean = np.mean(ts[:, 0])
        alpha_mean = np.mean(ts[:, 1])
        spread_fixed = ya - (yb * beta_mean + alpha_mean)
        
        try:
            adf = adfuller(spread_fixed, maxlag=20, autolag="AIC", regression="c")
            adf_p = float(adf[1])
        except Exception:
            adf_p = np.nan
            
        hl = ou["half_life_minutes"]
        tradeable = bool(
            np.isfinite(hl) and (5.0 <= hl <= 120.0) and np.isfinite(adf_p) and (adf_p < 0.05)
        )
        
        Q_bb, Q_aa, R_v = float(Q_opt[0, 0]), float(Q_opt[1, 1]), float(R_opt)
        return {
            "symbol_a": sym_a,
            "symbol_b": sym_b,
            "pearson_rho": float(row["pearson_rho"]),
            "stage1_rank": int(row["rank"]),
            "n_obs": len(ya),
            "Q_beta": Q_bb,
            "Q_alpha": Q_aa,
            "R": R_v,
            "log_likelihood_final": ll_f,
            "em_iterations": em_iters,
            "em_converged": em_conv,
            "beta_mean": beta_mean,
            "alpha_mean": alpha_mean,
            **ou,
            "adf_pvalue": adf_p,
            "tradeable": tradeable,
            "skipped": False,
        }
    except Exception as e:
        return {"symbol_a": sym_a, "symbol_b": sym_b, "skipped": True, "error": str(e)}

# Run Stage 2 calibration in parallel using fork context
args_list = [row.to_dict() for _, row in top500.iterrows()]
ctx = mp.get_context("fork")
print(f"Calibrating {len(args_list)} pairs...")

with ctx.Pool(processes=mp.cpu_count()) as pool:
    results = pool.map(process_pair, args_list)

results_df = pd.DataFrame([r for r in results if not r.get("skipped")])
results_df.to_csv('pairs_stage2_kalman_ou.csv', index=False)
tradeable_count = results_df['tradeable'].sum()
print(f"Stage 2 complete. Total tradeable pairs: {tradeable_count} / {len(results_df)}")
"""))

# --- CELL 5: Stage 3A Markdown ---
cells.append(md_cell("""
## Stage 3A — In-Sample Optimization Grid Search
**Input:** Validated pairs from Stage 2 (`pairs_stage2_kalman_ou.csv`), In-Sample prices.  
**Output:** `pairs_stage3a_optimized.csv`.  
**Core Logic:**
1. Pre-compute the Kalman Z-score series $z_t = e_t / \\sqrt{S_t}$ over the IS period.
2. Run a grid search sweep:
   - $Z$-entry trigger: $2.0, 2.5, 3.0, ..., 15.0$ (step 0.5)
   - Stop Loss: (a) Half-life time negative exit (at exactly $\\text{ceil}(t_{1/2})$ bars since entry, exit if gross PnL is negative), (b) $Z_{sl} = 2.5, 3.0, 3.5, ..., 16.0$ (step 0.5, with $Z_{sl} > Z_{\\text{entry}}$), or (c) no stop loss.
   - Post-SL Freeze logic: If stopped out by SL, suspend further entries until $|Z| < Z_{\\text{entry}} / 2$.
   - Mean reversion exit: Exit when Z crosses 0.0.
   - Force exit at 15:28 IST.
   - Maximize gross points profit on the lagging asset (trading lagger only, no fees).
3. Optimized via Numba JIT.
4. Output the single best configuration per pair.
"""))

# --- CELL 6: Stage 3A Code ---
cells.append(code_cell("""
# --- Stage 3A In-Sample Grid Search Optimization ---

# Load valid tradeable pairs from Stage 2
s2_results = pd.read_csv('pairs_stage2_kalman_ou.csv')
valid_pairs = s2_results[s2_results['tradeable'] == True].copy().reset_index(drop=True)
print(f"Stage 3A Tradeable Pairs: {len(valid_pairs)}")

@njit
def run_backtest_numba(prices, z_scores, times_in_min, half_life_bars, lagger_is_a, z_entry, z_sl, hl_stop):
    T = len(prices)
    in_trade = False
    pos = 0 # 1: Long, -1: Short
    entry_idx = 0
    entry_price = 0.0
    entry_z = 0.0
    frozen = False
    
    total_profit = 0.0
    trade_count = 0
    win_count = 0
    
    for t in range(T):
        z = z_scores[t]
        if np.isnan(z):
            continue
            
        p = prices[t]
        tm = times_in_min[t]
        
        # Post-SL Freeze logic
        if frozen:
            if abs(z) < z_entry / 2.0:
                frozen = False
                
        # Exit logic
        if in_trade:
            bars_held = t - entry_idx
            exit_reason = 0
            
            # 1. Mean Reversion Exit
            if entry_z >= z_entry and z <= 0.0:
                exit_reason = 1
            elif entry_z <= -z_entry and z >= 0.0:
                exit_reason = 1
                
            # 2. Stop Loss (Z_sl)
            if exit_reason == 0 and z_sl > 0.0 and abs(z) >= z_sl:
                exit_reason = 2
                frozen = True
                
            # 3. Half-life timeout
            if exit_reason == 0 and hl_stop and bars_held == half_life_bars:
                pnl = (p - entry_price) * pos
                if pnl < 0.0:
                    exit_reason = 3
                    frozen = True
                    
            # 4. Force exit at 15:28 IST
            if exit_reason == 0 and tm >= 928:
                exit_reason = 4
                
            if exit_reason > 0:
                pnl = (p - entry_price) * pos
                total_profit += pnl
                trade_count += 1
                if pnl > 0.0:
                    win_count += 1
                in_trade = False
                pos = 0
                continue
                
        # Entry logic
        if not in_trade and not frozen and tm < 928:
            if z >= z_entry:
                pos = -1 if lagger_is_a else 1
                in_trade = True
                entry_idx = t
                entry_price = p
                entry_z = z
            elif z <= -z_entry:
                pos = 1 if lagger_is_a else -1
                in_trade = True
                entry_idx = t
                entry_price = p
                entry_z = z
                
    # Force close at end of series
    if in_trade:
        pnl = (prices[T-1] - entry_price) * pos
        total_profit += pnl
        trade_count += 1
        if pnl > 0.0:
            win_count += 1
            
    win_rate = win_count / trade_count if trade_count > 0 else 0.0
    return total_profit, trade_count, win_rate

# Time of day in minutes for fast Numba checks
times_in_min_is = np.array([dt.hour * 60 + dt.minute for dt in dt_is])

# Leader/Lagger detection using 1-bar lagged correlation on log-returns over the warmup window (3750 bars)
WARMUP_BARS = 3750

def detect_lagger(ln_a, ln_b):
    ret_a = np.diff(ln_a[:WARMUP_BARS])
    ret_b = np.diff(ln_b[:WARMUP_BARS])
    corr_a_lags = np.corrcoef(ret_a[1:], ret_b[:-1])[0, 1]
    corr_b_lags = np.corrcoef(ret_b[1:], ret_a[:-1])[0, 1]
    if abs(corr_b_lags) >= abs(corr_a_lags):
        return "b"
    return "a"

optimized_rows = []

for idx, row in valid_pairs.iterrows():
    sym_a, sym_b = row['symbol_a'], row['symbol_b']
    ya = np.log(price_cache_is[sym_a])
    yb = np.log(price_cache_is[sym_b])
    
    lagger = detect_lagger(ya, yb)
    lagger_is_a = (lagger == "a")
    prices_lagger = price_cache_is[sym_a] if lagger_is_a else price_cache_is[sym_b]
    
    # Pre-compute Kalman Filter Z-scores over IS
    Q_opt = np.diag([row['Q_beta'], row['Q_alpha']])
    R_opt = row['R']
    
    ts, Ps, Pc, e_a, S_a, _, _, _ = kalman_smoother_scaled(ya, yb, Q_opt, R_opt, is_new_day_is)
    z_scores_is = e_a / np.sqrt(S_a)
    
    hl_bars = int(np.ceil(row['half_life_minutes']))
    
    # Run Grid Search
    best_profit = -np.inf
    best_config = (2.0, 0.0, False) # (z_entry, z_sl, hl_stop)
    best_trade_count = 0
    best_win_rate = 0.0
    
    # Grid parameters
    z_entry_vals = np.arange(2.0, 15.5, 0.5)
    
    for z_ent in z_entry_vals:
        # Stop loss sweep
        # 1. No Stop Loss
        prof, trades, wr = run_backtest_numba(prices_lagger, z_scores_is, times_in_min_is, hl_bars, lagger_is_a, z_ent, 0.0, False)
        if prof > best_profit or (prof == best_profit and trades > best_trade_count):
            best_profit = prof
            best_trade_count = trades
            best_win_rate = wr
            best_config = (z_ent, 0.0, False)
            
        # 2. Half-life negative exit
        prof, trades, wr = run_backtest_numba(prices_lagger, z_scores_is, times_in_min_is, hl_bars, lagger_is_a, z_ent, 0.0, True)
        if prof > best_profit or (prof == best_profit and trades > best_trade_count):
            best_profit = prof
            best_trade_count = trades
            best_win_rate = wr
            best_config = (z_ent, 0.0, True)
            
        # 3. Z_sl exit
        z_sl_vals = np.arange(2.5, 16.5, 0.5)
        for z_s in z_sl_vals:
            if z_s <= z_ent:
                continue
            prof, trades, wr = run_backtest_numba(prices_lagger, z_scores_is, times_in_min_is, hl_bars, lagger_is_a, z_ent, z_s, False)
            if prof > best_profit or (prof == best_profit and trades > best_trade_count):
                best_profit = prof
                best_trade_count = trades
                best_win_rate = wr
                best_config = (z_ent, z_s, False)
                
    optimized_rows.append({
        "symbol_a": sym_a,
        "symbol_b": sym_b,
        "best_z_entry": best_config[0],
        "best_z_sl": best_config[1],
        "best_hl_stop": best_config[2],
        "gross_profit": best_profit,
        "trade_count": best_trade_count,
        "win_rate": best_win_rate,
        "lagger": lagger,
    })

opt_df = pd.DataFrame(optimized_rows)
opt_df.to_csv('pairs_stage3a_optimized.csv', index=False)
print(f"Stage 3A Optimization completed. Saved {len(opt_df)} optimized pairs.")
"""))

# --- CELL 7: Stage 3B Markdown ---
cells.append(md_cell("""
## Stage 3B — Out-of-Sample Backtesting
**Input:** Optimized parameters from Stage 3A (`pairs_stage3a_optimized.csv`), Full price series.  
**Output:** `pairs_stage3b_backtest.csv`.  
**Core Logic:**
1. Run the online Kalman Filter continuously from 0 to $T$ to get the Z-scores $z_t = e_t / \\sqrt{S_t}$ for the entire series.
2. Backtest is evaluated strictly on the OOS period ($T_{is}$ to $T$).
3. **Execution Delay**: Entry/exit delayed by 1 bar (trade on the open price of the bar following the signal).
4. **Position Sizing**: Position size is ₹50,000 using the open price of the execution bar.
5. **Transaction Costs & Slippage**:
   - 0.05% slippage on entry and exit execution prices.
   - Zerodha MIS fees: Brokerage (flat ₹20/order leg), STT (0.025% on sell), Exchange charges (0.00345%), GST (18%), SEBI (Rs 10/crore), Stamp duty (0.003% buy).
6. **Strict single-sided lagger trading**: trade only the lagging asset.
"""))

# --- CELL 8: Stage 3B Code ---
cells.append(code_cell("""
# --- Stage 3B Out-of-Sample Backtesting ---

opt_pairs = pd.read_csv('pairs_stage3a_optimized.csv')
s2_full = pd.read_csv('pairs_stage2_kalman_ou.csv')

# Pre-load full prices for the optimized pairs
full_close_cache = {sym: price_matrix_close[sym].values for sym in price_matrix_close.columns}
full_open_cache = {sym: price_matrix_open[sym].values for sym in price_matrix_open.columns}
is_new_day_full = (price_matrix_close.index.time == MARKET_OPEN)

def calc_zerodha_mis_fees(qty, entry_price, exit_price, is_long):
    entry_turnover = qty * entry_price
    exit_turnover  = qty * exit_price
    total_turnover = entry_turnover + exit_turnover
    
    brokerage = 40.0 # 20 flat per order leg
    stt = 0.00025 * (exit_turnover if is_long else entry_turnover)
    exchange_charge = 0.0000345 * total_turnover
    gst = 0.18 * (brokerage + exchange_charge)
    sebi = (10.0 / 1e7) * total_turnover
    stamp = 0.00003 * (entry_turnover if is_long else exit_turnover)
    
    return brokerage + stt + exchange_charge + gst + sebi + stamp

backtest_results = []

for idx, row in opt_pairs.iterrows():
    sym_a, sym_b = row['symbol_a'], row['symbol_b']
    z_entry = row['best_z_entry']
    z_sl = row['best_z_sl']
    hl_stop = row['best_hl_stop']
    lagger = row['lagger']
    lagger_is_a = (lagger == "a")
    
    close_prices = full_close_cache[sym_a] if lagger_is_a else full_close_cache[sym_b]
    open_prices = full_open_cache[sym_a] if lagger_is_a else full_open_cache[sym_b]
    
    # Get parameters from Stage 2
    p_info = s2_full[(s2_full['symbol_a'] == sym_a) & (s2_full['symbol_b'] == sym_b)].iloc[0]
    Q_opt = np.diag([p_info['Q_beta'], p_info['Q_alpha']])
    R_opt = p_info['R']
    hl_bars = int(np.ceil(p_info['half_life_minutes']))
    
    ya_full = np.log(full_close_cache[sym_a])
    yb_full = np.log(full_close_cache[sym_b])
    
    # Run Kalman Filter over full series to avoid boundary issues
    ts, Ps, Pc, e_a, S_a, _, _, _ = kalman_smoother_scaled(ya_full, yb_full, Q_opt, R_opt, is_new_day_full)
    z_scores_full = e_a / np.sqrt(S_a)
    
    # Backtest strictly on OOS index range
    # T_is is the start index of OOS
    T_full = len(z_scores_full)
    
    in_trade = False
    pos = 0 # 1: Long, -1: Short
    entry_idx = 0
    entry_execution_price = 0.0
    entry_z = 0.0
    frozen = False
    
    trades = []
    
    for t in range(T_is, T_full - 1): # We run up to T_full-1 because entry/exit occurs at t+1
        z = z_scores_full[t]
        if np.isnan(z):
            continue
            
        tm = price_matrix_close.index[t].time()
        time_mins = tm.hour * 60 + tm.minute
        
        if frozen:
            if abs(z) < z_entry / 2.0:
                frozen = False
                
        # Exit logic checked at close of bar t, executes at open of t+1
        if in_trade:
            bars_held = t - entry_idx
            exit_reason = ""
            
            if entry_z >= z_entry and z <= 0.0:
                exit_reason = "mean_reversion"
            elif entry_z <= -z_entry and z >= 0.0:
                exit_reason = "mean_reversion"
                
            if not exit_reason and z_sl > 0.0 and abs(z) >= z_sl:
                exit_reason = "stop_loss"
                frozen = True
                
            if not exit_reason and hl_stop and bars_held == hl_bars:
                # check gross pnl at close of bar t (using close_prices[t])
                pnl_temp = (close_prices[t] - entry_execution_price) * pos
                if pnl_temp < 0.0:
                    exit_reason = "halflife_timeout"
                    frozen = True
                    
            if not exit_reason and time_mins >= 928: # 15:28 force close
                exit_reason = "session_end"
                
            if exit_reason:
                # Execute exit at open of t+1
                exec_exit_price = open_prices[t + 1]
                # Apply 0.05% slippage on exit
                exit_price_with_slippage = exec_exit_price * (0.9995 if pos == 1 else 1.0005)
                
                # Fees & PnL
                fees = calc_zerodha_mis_fees(qty, entry_execution_price, exec_exit_price, pos == 1)
                gross_pnl = (exit_price_with_slippage - entry_price_with_slippage) * qty if pos == 1 else (entry_price_with_slippage - exit_price_with_slippage) * qty
                net_pnl = gross_pnl - fees
                
                trades.append({
                    "entry_bar": entry_idx,
                    "exit_bar": t + 1,
                    "exit_reason": exit_reason,
                    "net_pnl": net_pnl,
                    "gross_pnl": gross_pnl,
                    "fees": fees,
                    "win": (net_pnl > 0.0)
                })
                in_trade = False
                pos = 0
                continue
                
        # Entry logic checked at close of bar t, executes at open of t+1
        if not in_trade and not frozen and time_mins < 928:
            if z >= z_entry:
                pos = -1 if lagger_is_a else 1
                entry_idx = t + 1
                entry_execution_price = open_prices[t + 1]
                qty = int(50000.0 // entry_execution_price)
                if qty > 0:
                    # Apply 0.05% slippage on entry
                    entry_price_with_slippage = entry_execution_price * (1.0005 if pos == 1 else 0.9995)
                    entry_z = z
                    in_trade = True
            elif z <= -z_entry:
                pos = 1 if lagger_is_a else -1
                entry_idx = t + 1
                entry_execution_price = open_prices[t + 1]
                qty = int(50000.0 // entry_execution_price)
                if qty > 0:
                    # Apply 0.05% slippage on entry
                    entry_price_with_slippage = entry_execution_price * (1.0005 if pos == 1 else 0.9995)
                    entry_z = z
                    in_trade = True
                    
    # Force close if still open at the very end
    if in_trade:
        exec_exit_price = close_prices[-1]
        exit_price_with_slippage = exec_exit_price * (0.9995 if pos == 1 else 1.0005)
        fees = calc_zerodha_mis_fees(qty, entry_execution_price, exec_exit_price, pos == 1)
        gross_pnl = (exit_price_with_slippage - entry_price_with_slippage) * qty if pos == 1 else (entry_price_with_slippage - exit_price_with_slippage) * qty
        net_pnl = gross_pnl - fees
        trades.append({
            "entry_bar": entry_idx,
            "exit_bar": T_full - 1,
            "exit_reason": "data_end",
            "net_pnl": net_pnl,
            "gross_pnl": gross_pnl,
            "fees": fees,
            "win": (net_pnl > 0.0)
        })
        
    # Compile performance metrics
    n_trades = len(trades)
    if n_trades == 0:
        net_profit = 0.0
        win_rate = 0.0
        max_dd = 0.0
        exit_reasons = "none"
    else:
        net_pnls = [t['net_pnl'] for t in trades]
        net_profit = sum(net_pnls)
        win_rate = sum(1 for t in trades if t['win']) / n_trades
        
        cum_pnl = np.cumsum(net_pnls)
        peak = np.maximum.accumulate(cum_pnl)
        dd = peak - cum_pnl
        max_dd = float(np.max(dd)) if len(dd) > 0 else 0.0
        
        exit_reasons = ";".join(list(set([t['exit_reason'] for t in trades])))
        
    backtest_results.append({
        "symbol_a": sym_a,
        "symbol_b": sym_b,
        "net_profit": net_profit,
        "win_rate": win_rate,
        "trade_count": n_trades,
        "max_drawdown": max_dd,
        "exit_reasons": exit_reasons
    })

bt_df = pd.DataFrame(backtest_results)
bt_df.to_csv('pairs_stage3b_backtest.csv', index=False)
print(f"Stage 3B Out-of-Sample Backtest completed. Saved {len(bt_df)} results.")
"""))

# --- CELL 9: Dataset Publishing Markdown ---
cells.append(md_cell("""
## Dataset Publishing
**Input:** Output CSV files in `/kaggle/working/`.  
**Output:** Published Kaggle dataset.  
**Core Logic:**
- Generate dataset metadata.
- Authenticate with Kaggle Python API.
- Create or update the dataset `utkarshpatelthefirst/master-pairs-trading-soul-results`.
"""))

# --- CELL 10: Dataset Publishing Code ---
cells.append(code_cell("""
# --- Dataset Publishing ---
import json
import shutil
from kaggle.api.kaggle_api_extended import KaggleApi

# Hardcoded credentials for Kaggle environment
os.environ['KAGGLE_USERNAME'] = 'utkarshpatelthefirst'
os.environ['KAGGLE_KEY']      = 'fbef16329099428205f671dd5de8337b'

api = KaggleApi()
api.authenticate()

export_dir = '/kaggle/working/dataset_export'
os.makedirs(export_dir, exist_ok=True)

# Copy all required outputs
output_files = [
    'pairs_all.csv',
    'pairs_top500.csv',
    'pairs_stage2_kalman_ou.csv',
    'pairs_stage3a_optimized.csv',
    'pairs_stage3b_backtest.csv'
]

for f in output_files:
    if os.path.exists(f):
        shutil.copy(f, f'{export_dir}/{f}')
        print(f"Copied {f} to export directory")

meta = {
    "title"    : "Master Pairs Trading Soul Results",
    "id"       : "utkarshpatelthefirst/master-pairs-trading-soul-results",
    "licenses" : [{"name": "CC0-1.0"}]
}
with open(f'{export_dir}/dataset-metadata.json', 'w') as f:
    json.dump(meta, f, indent=2)

print("Publishing dataset to Kaggle...")
try:
    api.dataset_create_new(export_dir, dir_mode='zip', quiet=False)
    print("✅ Successfully published NEW dataset")
except Exception as e:
    print(f"Dataset create new failed ({e}), trying version update...")
    api.dataset_create_version(export_dir, version_notes="Consolidated pipeline update", dir_mode='zip', quiet=False)
    print("✅ Successfully published new dataset version")
"""))

# Construct the notebook dictionary structure
notebook = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.10.0"},
    },
    "cells": cells
}

# Write the notebook file
with open(TARGET_NOTEBOOK_PATH, "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=1, ensure_ascii=False)

print(f"✅ Master_Pairs_Trading_Soul.ipynb successfully written to {TARGET_NOTEBOOK_PATH}!")
print(f"Total cells: {len(cells)}")
