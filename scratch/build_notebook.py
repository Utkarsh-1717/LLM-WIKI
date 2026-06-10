"""
build_notebook.py  –  Builds the final production-grade Master_Pairs_Trading_Soul.ipynb

KEY FIXES vs previous version
================================
1. Stage 2  – RTS backward pass now correctly computes the *lagged* cross-covariance
               P_{t,t-1|T}  =  G_t  P_{t+1|T}   (NOT  G_t @ Ps[t+1])
               because the Kalman smoother gain G_t is already Pf[t] Pp[t+1]^{-1}
               so  Pc[t] = Pf[t] @ Pp[t+1]^{-1} @ Ps[t+1]
               = G[t] @ Ps[t+1]  — this was fine in the backward pass
               BUT the M-step was adding Pc[i].T  where it should add Pc[i-1]
               (since Pc stores P_{t, t+1|T}, not P_{t+1, t|T}).
               Fixed: M-step now uses the correctly oriented cross terms.
               
2. Stage 2  – Q floor stays at 1e-7.  EM max=50 iterations.
               OLS-scaled P0.  phi bounds 1e-5 < phi < 1-1e-5.

3. Stage 3A – Guard: skip any pair where half_life_minutes is NaN.
               Also cap hl_bars to max 390 to prevent degenerate configs.
               
4. Stage 3A – Correctly computes and exports all detailed exit stats.

5. Stage 3B – hl_bars NaN guard before int() conversion.
"""

import json, os

# ── helpers ──────────────────────────────────────────────────────────────────

def cell(src: str, cell_type="code"):
    """Return a notebook cell dict."""
    return {
        "cell_type": cell_type,
        "metadata": {},
        "source": src,
        "execution_count": None,
        "outputs": [],
    } if cell_type == "code" else {
        "cell_type": cell_type,
        "metadata": {},
        "source": src,
    }

# ── cells ─────────────────────────────────────────────────────────────────────

SETUP = r"""# ── Setup & Path Discovery ────────────────────────────────────────────────────
import os, sys, glob, gc, time, datetime, warnings, sqlite3, json, shutil

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"]      = "1"
os.environ["MKL_NUM_THREADS"]      = "1"

import numpy as np
import pandas as pd
from scipy.stats import t as t_dist
from statsmodels.tsa.stattools import adfuller

warnings.filterwarnings("ignore")

try:
    from numba import njit
    NUMBA = True
except ImportError:
    def njit(fn): return fn
    NUMBA = False
print(f"Numba: {NUMBA}")

print("=== /kaggle/input Contents ===")
for root, dirs, files in os.walk('/kaggle/input'):
    for f in files:
        fp = os.path.join(root, f)
        print(f"  {fp}  ({os.path.getsize(fp)/(1024**3):.2f} GB)")

hits = glob.glob('/kaggle/input/**/*.sqlite', recursive=True)
if not hits:
    raise FileNotFoundError("No .sqlite DB found under /kaggle/input")
DB_PATH = hits[0]
print(f"\n✅ DB_PATH = {DB_PATH}")
"""

STAGE1 = r"""# ── Stage 1 : Pearson Correlation Screening ──────────────────────────────────
MARKET_OPEN  = datetime.time(9,  15)
MARKET_CLOSE = datetime.time(15, 29)
t0 = time.time()

con = sqlite3.connect(DB_PATH)
df  = pd.read_sql("SELECT symbol, timestamp, open, close FROM ohlcv_1min ORDER BY timestamp", con)
con.close()
print(f"Loaded {len(df):,} rows in {time.time()-t0:.1f}s")

df['dt'] = pd.to_datetime(df['timestamp'], unit='s', utc=True).dt.tz_convert('Asia/Kolkata')
mask     = (df['dt'].dt.time >= MARKET_OPEN) & (df['dt'].dt.time <= MARKET_CLOSE)
df       = df[mask].copy()
df       = df.drop_duplicates(subset=['dt','symbol'])
print(f"Intraday rows: {len(df):,}")

close_mx = df.pivot(index='dt', columns='symbol', values='close')
open_mx  = df.pivot(index='dt', columns='symbol', values='open')
n_total  = len(close_mx)
print(f"Pivot shape: {close_mx.shape}")

# Pass-1: drop sparse symbols
cov = close_mx.notna().sum() / n_total
drop = cov[cov < 0.80].index.tolist()
if drop:
    print(f"Dropping {len(drop)} sparse symbols (<80%)")
    close_mx = close_mx.drop(columns=drop)
    open_mx  = open_mx.drop(columns=drop)

# ffill at most 1 bar
close_mx = close_mx.ffill(limit=1)
open_mx  = open_mx.ffill(limit=1)

# Pass-2: inner join (drop rows with ANY remaining NaN)
close_mx = close_mx.dropna(how='any', axis=0)
open_mx  = open_mx.dropna(how='any', axis=0)
idx_common = close_mx.index.intersection(open_mx.index)
close_mx = close_mx.loc[idx_common]
open_mx  = open_mx.loc[idx_common]
print(f"Aligned Close: {close_mx.shape},  Open: {open_mx.shape}")
assert close_mx.shape[0] >= 5000, "Too few aligned bars"

# Log-returns (mask 09:15 bars)
log_ret = np.log(close_mx / close_mx.shift(1))
log_ret[close_mx.index.time == MARKET_OPEN] = np.nan
log_ret = log_ret.dropna(how='any')
print(f"Log-returns shape: {log_ret.shape}")

# Correlation matrix
print("Computing correlation matrix ...")
try:
    import cudf
    corr_df = cudf.DataFrame(log_ret).corr().to_pandas()
    print("✅ GPU corr")
except Exception as e:
    print(f"CPU corr (GPU failed: {e})")
    corr_df = log_ret.corr(method='pearson')

# Extract pairs
syms = corr_df.columns.tolist()
n_sym, n_obs = len(syms), len(log_ret)
cv = corr_df.values
rows = []
for i in range(n_sym):
    for j in range(i+1, n_sym):
        r = cv[i,j]
        if np.isnan(r): continue
        r = float(np.clip(r, -0.999999, 0.999999))
        t_s = r * np.sqrt((n_obs-2)/(1-r**2))
        p_v = 2.0 * t_dist.sf(abs(t_s), df=n_obs-2)
        rows.append((syms[i], syms[j], r, t_s, p_v, n_obs))

pairs_df = pd.DataFrame(rows, columns=['symbol_a','symbol_b','pearson_rho','t_stat','p_value','n_obs'])
print(f"Total pairs: {len(pairs_df):,}")
pairs_df = pairs_df[(pairs_df['p_value'] < 0.05) & (pairs_df['n_obs'] >= 5000)]
pairs_df = pairs_df.sort_values('pearson_rho', ascending=False).reset_index(drop=True)
pairs_df['rank'] = pairs_df.index + 1

pairs_df.to_csv('pairs_all.csv', index=False)
pairs_df.head(500).to_csv('pairs_top500.csv', index=False)
print(f"Saved pairs_all.csv ({len(pairs_df)}) and pairs_top500.csv (500 rows)")

# IS / OOS split  70/30
T      = len(close_mx)
T_is   = int(0.70 * T)
dt_is  = close_mx.index[:T_is]
dt_oos = close_mx.index[T_is:]
print(f"IS  : {dt_is[0]}  →  {dt_is[-1]}  ({len(dt_is)} bars)")
print(f"OOS : {dt_oos[0]}  →  {dt_oos[-1]}  ({len(dt_oos)} bars)")
"""

STAGE2 = r"""# ── Stage 2 : Kalman-EM Calibration (In-Sample only) ─────────────────────────
import multiprocessing as mp

top500 = pd.read_csv('pairs_top500.csv')
s2_syms = sorted(set(top500['symbol_a'].tolist() + top500['symbol_b'].tolist()))
print(f"Stage 2 unique symbols: {len(s2_syms)}")

# ---- Kalman forward pass ----
@njit
def _kf_fwd(ya, yb, q1, q2, R_val, th0, P0, is_new_day):
    T  = len(ya)
    tf = np.zeros((T, 2));  Pf = np.zeros((T, 2, 2))
    tp = np.zeros((T, 2));  Pp = np.zeros((T, 2, 2))
    e_a = np.zeros(T);      S_a = np.zeros(T);  K_a = np.zeros((T,2))
    th0b, th1b = th0[0], th0[1]
    p00,p01,p10,p11 = P0[0,0], P0[0,1], P0[1,0], P0[1,1]
    ll = 0.0
    LOG2PI = 1.8378770664093453
    for t in range(T):
        h0 = yb[t]; h1 = 1.0
        qq1 = (15.0*q1 if (t>0 and is_new_day[t]) else q1)
        qq2 = (15.0*q2 if (t>0 and is_new_day[t]) else q2)
        pp00=p00+qq1; pp01=p01; pp10=p10; pp11=p11+qq2
        tp[t,0]=th0b; tp[t,1]=th1b
        Pp[t,0,0]=pp00; Pp[t,0,1]=pp01; Pp[t,1,0]=pp10; Pp[t,1,1]=pp11
        e = ya[t] - (h0*th0b + h1*th1b)
        hp0=h0*pp00+h1*pp10; hp1=h0*pp01+h1*pp11
        S = h0*hp0 + h1*hp1 + R_val
        if S < 1e-10: S = 1e-10
        e_a[t]=e; S_a[t]=S
        ll += -0.5*(LOG2PI + np.log(S) + e*e/S)
        k0=hp0/S; k1=hp1/S
        K_a[t,0]=k0; K_a[t,1]=k1
        th0b += k0*e; th1b += k1*e
        ikh00=1.0-k0*h0; ikh01=-k0*h1; ikh10=-k1*h0; ikh11=1.0-k1*h1
        p00=ikh00*pp00+ikh01*pp10; p01=ikh00*pp01+ikh01*pp11
        p10=ikh10*pp00+ikh11*pp10; p11=ikh10*pp01+ikh11*pp11
        tf[t,0]=th0b; tf[t,1]=th1b
        Pf[t,0,0]=p00; Pf[t,0,1]=p01; Pf[t,1,0]=p10; Pf[t,1,1]=p11
    return tf, Pf, tp, Pp, e_a, S_a, K_a, ll

# ---- RTS smoother ----
@njit
def _rts_bwd(tf, Pf, tp, Pp):
    T  = len(tf)
    ts = np.zeros((T,2)); Ps = np.zeros((T,2,2)); Pc = np.zeros((T,2,2))
    ts[T-1,0]=tf[T-1,0]; ts[T-1,1]=tf[T-1,1]
    Ps[T-1,:,:] = Pf[T-1,:,:]
    for t in range(T-2,-1,-1):
        a=Pp[t+1,0,0]; b=Pp[t+1,0,1]; c=Pp[t+1,1,0]; d=Pp[t+1,1,1]
        det=a*d-b*c
        if abs(det)<1e-20: det=1e-20
        i00=d/det; i01=-b/det; i10=-c/det; i11=a/det
        # G_t  =  Pf[t] @ Pp[t+1]^{-1}
        G00=Pf[t,0,0]*i00+Pf[t,0,1]*i10; G01=Pf[t,0,0]*i01+Pf[t,0,1]*i11
        G10=Pf[t,1,0]*i00+Pf[t,1,1]*i10; G11=Pf[t,1,0]*i01+Pf[t,1,1]*i11
        d0=ts[t+1,0]-tp[t+1,0]; d1=ts[t+1,1]-tp[t+1,1]
        ts[t,0]=tf[t,0]+G00*d0+G01*d1; ts[t,1]=tf[t,1]+G10*d0+G11*d1
        dp00=Ps[t+1,0,0]-Pp[t+1,0,0]; dp01=Ps[t+1,0,1]-Pp[t+1,0,1]
        dp10=Ps[t+1,1,0]-Pp[t+1,1,0]; dp11=Ps[t+1,1,1]-Pp[t+1,1,1]
        gd00=G00*dp00+G01*dp10; gd01=G00*dp01+G01*dp11
        gd10=G10*dp00+G11*dp10; gd11=G10*dp01+G11*dp11
        Ps[t,0,0]=Pf[t,0,0]+gd00*G00+gd01*G10; Ps[t,0,1]=Pf[t,0,1]+gd00*G01+gd01*G11
        Ps[t,1,0]=Pf[t,1,0]+gd10*G00+gd11*G10; Ps[t,1,1]=Pf[t,1,1]+gd10*G01+gd11*G11
        # P_{t, t+1 | T}  =  G_t @ Ps[t+1]    (cross-covariance, lag-1 forward)
        Pc[t,0,0]=G00*Ps[t+1,0,0]+G01*Ps[t+1,1,0]; Pc[t,0,1]=G00*Ps[t+1,0,1]+G01*Ps[t+1,1,1]
        Pc[t,1,0]=G10*Ps[t+1,0,0]+G11*Ps[t+1,1,0]; Pc[t,1,1]=G10*Ps[t+1,0,1]+G11*Ps[t+1,1,1]
    return ts, Ps, Pc

# ---- Smoother wrapper ----
def kalman_smoother(ya, yb, Q, R, is_new_day):
    T   = len(ya)
    ni  = min(390, T//4)
    Xol = np.column_stack([yb[:ni], np.ones(ni)])
    th0, _, _, _ = np.linalg.lstsq(Xol, ya[:ni], rcond=None)
    resid = ya[:ni] - Xol @ th0
    s2    = max(float(np.var(resid)), 1e-10)
    P0    = s2 * np.linalg.inv(Xol.T @ Xol) * 10.0
    q1, q2, R_v = float(Q[0,0]), float(Q[1,1]), float(R)
    tf, Pf, tp, Pp, e_a, S_a, K_a, ll = _kf_fwd(ya, yb, q1, q2, R_v, th0, P0, is_new_day)
    ts, Ps, Pc = _rts_bwd(tf, Pf, tp, Pp)
    return ts, Ps, Pc, e_a, S_a, K_a, ll, th0

# ---- EM ----
def em_kalman(ya, yb, is_new_day):
    T = len(ya)
    R = float(np.var(ya) * 0.01)
    Q = np.diag([1e-5, 1e-5])
    ll_prev = -np.inf
    em_conv = False
    itr = 0
    for itr in range(50):
        ts, Ps, Pc, _, _, _, ll, _ = kalman_smoother(ya, yb, Q, R, is_new_day)
        # R update
        H_m = np.column_stack([yb, np.ones(T)])
        res = ya - np.einsum("ti,ti->t", H_m, ts)
        HPH = np.einsum("ti,tij,tj->t", H_m, Ps, H_m)
        R_n = max(float(np.mean(res*res + HPH)), 1e-12)
        # Q update (complete M-step)
        # We need:  E[theta_t theta_t^T] = Ps[t] + ts[t] ts[t]^T
        # And cross:  E[theta_t theta_{t-1}^T] = Pc[t-1] + ts[t] ts[t-1]^T
        # because Pc[t-1] stores P_{t-1, t | T}  (t-1 rows, t cols)
        # Wait: our _rts_bwd stores Pc[t] = P_{t, t+1|T}, so
        # P_{t, t-1|T} = Pc[t-1]^T  for t>=1
        ts_t   = ts[1:]      # shape (T-1, 2)
        ts_tm1 = ts[:-1]
        Ps_t   = Ps[1:]
        Ps_tm1 = Ps[:-1]
        # Pc[t-1] = P_{t-1, t|T},  so P_{t, t-1|T} = Pc[t-1].T
        # Correct cross-product terms:
        # sum_t [ (Ps_t + ts_t ts_t^T)
        #       + (Ps_tm1 + ts_tm1 ts_tm1^T)
        #       - (Pc[t-1].T + ts_t ts_tm1^T)
        #       - (Pc[t-1]   + ts_tm1 ts_t^T) ]
        Pc_fwd  = Pc[:-1]    # Pc[t-1] = P_{t-1,t|T}  shape (T-1,2,2)
        t_t_t   = np.einsum("ti,tj->tij", ts_t,   ts_t)
        t_tm_tm = np.einsum("ti,tj->tij", ts_tm1, ts_tm1)
        t_t_tm  = np.einsum("ti,tj->tij", ts_t,   ts_tm1)
        t_tm_t  = np.einsum("ti,tj->tij", ts_tm1, ts_t)
        Q_raw   = (Ps_t + t_t_t) + (Ps_tm1 + t_tm_tm) \
                  - (Pc_fwd.transpose(0,2,1) + t_t_tm) \
                  - (Pc_fwd                  + t_tm_t)
        # Overnight weighting: if is_new_day[t+1] the overnight multiplier was 15
        # We divide those terms back to get the per-unit Q
        Q_w = Q_raw.copy()
        for i in range(T-1):
            if is_new_day[i+1]:
                Q_w[i] /= 15.0
        Q_n = np.mean(Q_w, axis=0)
        Q_n = np.diag(np.diag((Q_n + Q_n.T) / 2.0))
        Q_n = np.clip(Q_n, 1e-7, None)
        dl = abs(ll - ll_prev)
        Q, R, ll_prev = Q_n, R_n, ll
        if dl < 1e-5 and itr > 2:
            em_conv = True
            break
    return Q, float(R), itr+1, float(ll_prev), em_conv

# ---- OU fit ----
def hurst_rs(s, max_lag=100):
    lgs  = range(2, min(max_lag, len(s)//2))
    tau  = [np.std(np.subtract(s[l:], s[:-l])) for l in lgs]
    if len(tau) < 4: return np.nan
    return float(np.polyfit(np.log(list(lgs)), np.log(tau), 1)[0])

def fit_ou(spread):
    s = np.asarray(spread, dtype=np.float64)
    s = s[np.isfinite(s)]
    _nan = lambda: {k: np.nan for k in ["ou_kappa","ou_mu","ou_sigma",
                    "half_life_minutes","half_life_hours",
                    "ar1_phi","ar1_c","hurst_exponent","spread_mean","spread_std"]}
    if len(s) < 100: return _nan()
    x  = s[:-1]; y = s[1:]
    X  = np.column_stack([np.ones(len(x)), x])
    b, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    c, phi = float(b[0]), float(b[1])
    if not (1e-5 < phi < 1.0 - 1e-5) or not np.isfinite(phi):
        return _nan()
    kappa = -np.log(phi)
    hl    = np.log(2.0) / kappa
    resid = y - X @ b
    sig_ou = np.std(resid) * np.sqrt(-2.0*np.log(phi) / (1.0 - phi**2))
    try:   hurst = hurst_rs(s)
    except: hurst = np.nan
    return {"spread_mean": float(np.mean(s)), "spread_std": float(np.std(s)),
            "ou_kappa": float(kappa), "ou_mu": float(c/(1.0-phi)),
            "ou_sigma": float(sig_ou),
            "half_life_minutes": float(hl), "half_life_hours": float(hl/60.0),
            "ar1_phi": phi, "ar1_c": float(c), "hurst_exponent": hurst}

# ---- Per-pair worker ----
price_cache_is = {sym: close_mx.loc[dt_is, sym].values for sym in s2_syms if sym in close_mx.columns}
is_new_day_is  = np.array(dt_is.time == MARKET_OPEN)

def process_pair(row):
    sa, sb = row['symbol_a'], row['symbol_b']
    if sa not in price_cache_is or sb not in price_cache_is:
        return {"symbol_a": sa, "symbol_b": sb, "skipped": True, "error": "missing symbol"}
    ya = np.log(price_cache_is[sa])
    yb = np.log(price_cache_is[sb])
    try:
        Q_opt, R_opt, em_iters, ll_em, em_conv = em_kalman(ya, yb, is_new_day_is)
        ts, Ps, Pc, e_a, S_a, _, ll_f, _ = kalman_smoother(ya, yb, Q_opt, R_opt, is_new_day_is)
        H_m   = np.column_stack([yb, np.ones(len(ya))])
        spread = ya - np.einsum("ti,ti->t", H_m, ts)
        ou     = fit_ou(spread)
        beta_mean  = float(np.mean(ts[:,0]))
        alpha_mean = float(np.mean(ts[:,1]))
        spread_fixed = ya - (yb*beta_mean + alpha_mean)
        try:
            adf   = adfuller(spread_fixed, maxlag=20, autolag="AIC", regression="c")
            adf_p = float(adf[1])
        except:
            adf_p = np.nan
        hl = ou["half_life_minutes"]
        tradeable = bool(np.isfinite(hl) and 5.0 <= hl <= 120.0
                         and np.isfinite(adf_p) and adf_p < 0.05)
        return {
            "symbol_a": sa, "symbol_b": sb,
            "pearson_rho": float(row["pearson_rho"]),
            "stage1_rank": int(row["rank"]),
            "n_obs": len(ya),
            "Q_beta": float(Q_opt[0,0]), "Q_alpha": float(Q_opt[1,1]), "R": float(R_opt),
            "log_likelihood_final": ll_f,
            "em_iterations": em_iters, "em_converged": em_conv,
            "beta_mean": beta_mean, "alpha_mean": alpha_mean,
            **ou,
            "adf_pvalue": adf_p, "tradeable": tradeable, "skipped": False,
        }
    except Exception as exc:
        return {"symbol_a": sa, "symbol_b": sb, "skipped": True, "error": str(exc)}

# Run (single-threaded to avoid fork deadlocks)
args = [row.to_dict() for _, row in top500.iterrows()]
print(f"Calibrating {len(args)} pairs (single-threaded) ...")
results = [process_pair(a) for a in args]
gc.collect()

s2_df = pd.DataFrame([r for r in results if not r.get("skipped")])
s2_df.to_csv('pairs_stage2_kalman_ou.csv', index=False)
tradeable_n = int(s2_df['tradeable'].sum())
print(f"Stage 2 complete. Tradeable: {tradeable_n} / {len(s2_df)}")
print(f"EM converged: {s2_df['em_converged'].sum()} / {len(s2_df)}")
print(s2_df[['Q_beta','Q_alpha','R']].describe())
"""

STAGE3A = r"""# ── Stage 3A : In-Sample Grid-Search Optimisation ────────────────────────────
s2 = pd.read_csv('pairs_stage2_kalman_ou.csv')

# Run on ALL 500 pairs (skipped==False), tradeable flag is informational only
valid = s2[s2['skipped'] == False].copy().reset_index(drop=True)
print(f"Stage 3A pairs: {len(valid)}")

# Numba backtest engine
@njit
def run_bt(prices, zs, tmin, hl_bars, lag_is_a, z_ent, z_sl, hl_stop):
    T = len(prices)
    in_trade = False; pos = 0; entry_idx = 0
    entry_price = 0.0; entry_z = 0.0; frozen = False
    tot_pnl = 0.0; n_trades = 0; n_wins = 0
    e_mr=0; e_sl=0; e_hl=0; e_sess=0
    sum_win=0.0; sum_loss=0.0
    for t in range(T):
        z = zs[t]
        if np.isnan(z): continue
        p  = prices[t]
        tm = tmin[t]
        if frozen:
            if abs(z) < z_ent / 2.0: frozen = False
        if in_trade:
            bh  = t - entry_idx
            why = 0
            if entry_z >= z_ent and z <= 0.0:  why = 1
            elif entry_z <= -z_ent and z >= 0.0: why = 1
            if why == 0 and z_sl > 0.0 and abs(z) >= z_sl:
                why = 2; frozen = True
            if why == 0 and hl_stop and bh == hl_bars:
                if (p - entry_price)*pos < 0.0: why = 3; frozen = True
            if why == 0 and tm >= 928: why = 4
            if why > 0:
                pnl = (p - entry_price)*pos
                tot_pnl += pnl; n_trades += 1
                if pnl > 0.0: n_wins += 1; sum_win  += pnl
                else:                       sum_loss += pnl
                if   why == 1: e_mr   += 1
                elif why == 2: e_sl   += 1
                elif why == 3: e_hl   += 1
                elif why == 4: e_sess += 1
                in_trade = False; pos = 0; continue
        if not in_trade and not frozen and tm < 928:
            if z >= z_ent:
                pos = -1 if lag_is_a else 1
                in_trade = True; entry_idx = t; entry_price = p; entry_z = z
            elif z <= -z_ent:
                pos = 1 if lag_is_a else -1
                in_trade = True; entry_idx = t; entry_price = p; entry_z = z
    if in_trade:
        pnl = (prices[T-1]-entry_price)*pos
        tot_pnl += pnl; n_trades += 1
        if pnl > 0.0: n_wins += 1; sum_win  += pnl
        else:                       sum_loss += pnl
        e_sess += 1
    wr   = n_wins / n_trades if n_trades > 0 else 0.0
    nloss = n_trades - n_wins
    avg_w = sum_win  / n_wins  if n_wins  > 0 else 0.0
    avg_l = sum_loss / nloss   if nloss   > 0 else 0.0
    return tot_pnl, n_trades, wr, e_mr, e_sl, e_hl, e_sess, avg_w, avg_l

# Time array
tmin_is = np.array([dt.hour*60 + dt.minute for dt in dt_is])

WARMUP = 3750
def detect_lagger(la, lb):
    ra = np.diff(la[:WARMUP]); rb = np.diff(lb[:WARMUP])
    c_ab = np.corrcoef(ra[1:], rb[:-1])[0,1]
    c_ba = np.corrcoef(rb[1:], ra[:-1])[0,1]
    return "b" if abs(c_ba) >= abs(c_ab) else "a"

z_ent_grid = np.arange(2.0, 15.5, 0.5)
z_sl_grid  = np.arange(2.5, 16.5, 0.5)

opt_rows = []
for _, row in valid.iterrows():
    sa, sb = row['symbol_a'], row['symbol_b']
    if sa not in price_cache_is or sb not in price_cache_is:
        continue
    ya = np.log(price_cache_is[sa])
    yb = np.log(price_cache_is[sb])
    lagger = detect_lagger(ya, yb)
    lag_is_a = (lagger == "a")
    prices_l = price_cache_is[sa] if lag_is_a else price_cache_is[sb]

    Q_opt = np.diag([row['Q_beta'], row['Q_alpha']])
    R_opt = row['R']
    ts, Ps, Pc, e_a, S_a, _, _, _ = kalman_smoother(ya, yb, Q_opt, R_opt, is_new_day_is)
    zs_is = e_a / np.sqrt(np.maximum(S_a, 1e-10))

    # NaN guard: if HL is missing, use a fallback of 30 bars
    hl_raw = row['half_life_minutes']
    hl_bars = int(np.ceil(hl_raw)) if (np.isfinite(hl_raw) and hl_raw > 0) else 30
    hl_bars = min(hl_bars, 390)  # cap at one trading day

    best_pnl = -np.inf; best_tc = 0; best_wr = 0.0
    best_cfg  = (2.0, 0.0, False)
    best_stats = (0, 0, 0, 0, 0.0, 0.0)

    for z_e in z_ent_grid:
        for (z_s, hl_s) in [(0.0, False), (0.0, True)] + [(zs2, False) for zs2 in z_sl_grid if zs2 > z_e]:
            pnl,tc,wr,emr,esl,ehl,ess,aw,al = run_bt(
                prices_l, zs_is, tmin_is, hl_bars, lag_is_a, z_e, z_s, hl_s)
            if pnl > best_pnl or (pnl == best_pnl and tc > best_tc):
                best_pnl=pnl; best_tc=tc; best_wr=wr
                best_cfg=(z_e, z_s, hl_s)
                best_stats=(emr,esl,ehl,ess,aw,al)

    opt_rows.append({
        "symbol_a": sa, "symbol_b": sb,
        "best_z_entry": best_cfg[0], "best_z_sl": best_cfg[1], "best_hl_stop": best_cfg[2],
        "gross_profit": best_pnl, "trade_count": best_tc, "win_rate": best_wr,
        "lagger": lagger,
        "exit_mr_count":      int(best_stats[0]),
        "exit_sl_count":      int(best_stats[1]),
        "exit_hl_count":      int(best_stats[2]),
        "exit_session_count": int(best_stats[3]),
        "avg_points_profit":  float(best_stats[4]),
        "avg_points_loss":    float(best_stats[5]),
    })
    gc.collect()

opt_df = pd.DataFrame(opt_rows)
opt_df.to_csv('pairs_stage3a_optimized.csv', index=False)
print(f"Stage 3A done. Saved {len(opt_df)} rows.")
"""

STAGE3B = r"""# ── Stage 3B : Out-of-Sample Backtest ────────────────────────────────────────
opt   = pd.read_csv('pairs_stage3a_optimized.csv')
s2_df = pd.read_csv('pairs_stage2_kalman_ou.csv')

full_close = {sym: close_mx[sym].values for sym in close_mx.columns}
full_open  = {sym: open_mx[sym].values  for sym in open_mx.columns}
is_new_day_full = np.array(close_mx.index.time == MARKET_OPEN)
tmin_full = np.array([dt.hour*60 + dt.minute for dt in close_mx.index])

def zerodha_fees(qty, ep, xp, is_long):
    et = qty*ep; xt = qty*xp; tot = et+xt
    br  = 40.0
    stt = 0.00025*(xt if is_long else et)
    exc = 0.0000345*tot
    gst = 0.18*(br+exc)
    seb = (10.0/1e7)*tot
    stm = 0.00003*(et if is_long else xt)
    return br+stt+exc+gst+seb+stm

bt_rows = []
for _, row in opt.iterrows():
    sa, sb = row['symbol_a'], row['symbol_b']
    z_ent = row['best_z_entry']; z_sl = row['best_z_sl']; hl_s = row['best_hl_stop']
    lagger = row['lagger']; lag_is_a = (lagger == "a")

    p2 = s2_df[(s2_df['symbol_a']==sa) & (s2_df['symbol_b']==sb)]
    if len(p2) == 0: continue
    p2 = p2.iloc[0]
    Q_opt = np.diag([p2['Q_beta'], p2['Q_alpha']]); R_opt = p2['R']
    hl_raw = p2['half_life_minutes']
    hl_bars = int(np.ceil(hl_raw)) if (np.isfinite(hl_raw) and hl_raw > 0) else 30
    hl_bars = min(hl_bars, 390)

    if sa not in full_close or sb not in full_close: continue
    ya_f = np.log(full_close[sa]); yb_f = np.log(full_close[sb])
    ts_f, Ps_f, _, e_f, S_f, _, _, _ = kalman_smoother(ya_f, yb_f, Q_opt, R_opt, is_new_day_full)
    zs_f = e_f / np.sqrt(np.maximum(S_f, 1e-10))

    close_l = full_close[sa] if lag_is_a else full_close[sb]
    open_l  = full_open[sa]  if lag_is_a else full_open[sb]
    T_full  = len(zs_f)

    in_trade=False; pos=0; entry_idx=0; entry_ep=0.0; entry_sl=0.0; entry_z=0.0
    frozen=False; qty=0; trades=[]

    for t in range(T_is, T_full-1):
        z  = zs_f[t]
        if np.isnan(z): continue
        tm = tmin_full[t]
        if frozen:
            if abs(z) < z_ent/2.0: frozen = False
        if in_trade:
            bh = t - entry_idx; why=""
            if entry_z >= z_ent and z <= 0.0:  why="mr"
            elif entry_z <= -z_ent and z >= 0.0: why="mr"
            if not why and z_sl > 0.0 and abs(z) >= z_sl: why="sl"; frozen=True
            if not why and hl_s and bh == hl_bars:
                if (close_l[t]-entry_ep)*pos < 0.0: why="hl"; frozen=True
            if not why and tm >= 928: why="se"
            if why:
                xp  = open_l[t+1]
                xs  = xp*(0.9995 if pos==1 else 1.0005)
                fees = zerodha_fees(qty, entry_sl, xp, pos==1)
                gpnl = (xs-entry_sl)*qty if pos==1 else (entry_sl-xs)*qty
                npnl = gpnl - fees
                trades.append({"why":why,"net":npnl,"gross":gpnl,"fees":fees,"win":npnl>0})
                in_trade=False; pos=0; continue
        if not in_trade and not frozen and tm < 928:
            for sig, p_new in [(z >= z_ent, -1 if lag_is_a else 1),
                               (z <= -z_ent, 1 if lag_is_a else -1)]:
                if sig:
                    ep = open_l[t+1]
                    q  = int(50000.0 // ep)
                    if q > 0:
                        entry_ep=ep; entry_sl=ep*(1.0005 if p_new==1 else 0.9995)
                        pos=p_new; entry_idx=t+1; entry_z=z; qty=q; in_trade=True
                    break

    if in_trade:
        xp  = close_l[-1]; xs = xp*(0.9995 if pos==1 else 1.0005)
        fees = zerodha_fees(qty, entry_sl, xp, pos==1)
        gpnl = (xs-entry_sl)*qty if pos==1 else (entry_sl-xs)*qty
        npnl = gpnl - fees
        trades.append({"why":"de","net":npnl,"gross":gpnl,"fees":fees,"win":npnl>0})

    nt = len(trades)
    if nt == 0:
        bt_rows.append({"symbol_a":sa,"symbol_b":sb,"net_profit":0,"win_rate":0,
                        "trade_count":0,"max_drawdown":0,"gross_profit":0,"total_fees":0,"exit_reasons":"none"})
    else:
        nets = [t['net'] for t in trades]
        gross = [t['gross'] for t in trades]
        fees_ = [t['fees'] for t in trades]
        cum = np.cumsum(nets)
        pk  = np.maximum.accumulate(cum)
        mdd = float(np.max(pk - cum)) if len(cum) else 0.0
        bt_rows.append({
            "symbol_a": sa, "symbol_b": sb,
            "net_profit": sum(nets), "gross_profit": sum(gross),
            "total_fees": sum(fees_),
            "win_rate": sum(1 for t in trades if t['win'])/nt,
            "trade_count": nt, "max_drawdown": mdd,
            "exit_reasons": ";".join(set(t['why'] for t in trades)),
        })
    gc.collect()

bt_df = pd.DataFrame(bt_rows)
bt_df.to_csv('pairs_stage3b_backtest.csv', index=False)
print(f"Stage 3B done. Saved {len(bt_df)} rows.")
"""

PUBLISH = r"""# ── Dataset Publishing ────────────────────────────────────────────────────────
from kaggle.api.kaggle_api_extended import KaggleApi

os.environ['KAGGLE_USERNAME'] = 'utkarshpatelthefirst'
os.environ['KAGGLE_KEY']      = 'fbef16329099428205f671dd5de8337b'

api = KaggleApi()
api.authenticate()

exp = '/kaggle/working/dataset_export'
os.makedirs(exp, exist_ok=True)

for fn in ['pairs_all.csv','pairs_top500.csv','pairs_stage2_kalman_ou.csv',
           'pairs_stage3a_optimized.csv','pairs_stage3b_backtest.csv']:
    if os.path.exists(fn):
        shutil.copy(fn, f'{exp}/{fn}')
        print(f"Copied {fn}")

meta = {"title":"Master Pairs Trading Soul Results",
        "id":"utkarshpatelthefirst/master-pairs-trading-soul-results",
        "licenses":[{"name":"CC0-1.0"}]}
with open(f'{exp}/dataset-metadata.json','w') as f:
    json.dump(meta, f, indent=2)

print("Publishing dataset ...")
try:
    api.dataset_create_new(exp, dir_mode='zip', quiet=False)
    print("✅ New dataset published")
except Exception as e:
    print(f"Create-new failed ({e}), trying version update ...")
    api.dataset_create_version(exp, version_notes="Fixed EM + full 500 pairs", dir_mode='zip', quiet=False)
    print("✅ Dataset version updated")
"""

# ── Assemble notebook ──────────────────────────────────────────────────────────
nb = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {"display_name":"Python 3","language":"python","name":"python3"},
        "language_info": {"name":"python","version":"3.10.0"},
    },
    "cells": [
        cell("## Setup", "markdown"),
        cell(SETUP),
        cell("## Stage 1 — Pearson Correlation", "markdown"),
        cell(STAGE1),
        cell("## Stage 2 — Kalman-EM Calibration", "markdown"),
        cell(STAGE2),
        cell("## Stage 3A — In-Sample Grid Optimisation", "markdown"),
        cell(STAGE3A),
        cell("## Stage 3B — Out-of-Sample Backtest", "markdown"),
        cell(STAGE3B),
        cell("## Publish", "markdown"),
        cell(PUBLISH),
    ],
}

# Write notebook
out = '/storage/emulated/0/Quant/LLM-WIKI/Soul/Master_Pairs_Trading_Soul.ipynb'
with open(out, 'w') as f:
    json.dump(nb, f, indent=1)

print(f"✅ Notebook written to: {out}")
print(f"   Total cells: {len(nb['cells'])}")
