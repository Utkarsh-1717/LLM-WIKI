"""
patch_stage3_zscores.py
Fixes Stage 3A and 3B to use the correct OU-based Z-score:
  Z_t = (spread_t - ou_mu) / ou_sigma
instead of the wrong Kalman innovation Z:
  Z_t = e_t / sqrt(S_t)
"""
import json, re

nb_path = '/storage/emulated/0/Quant/LLM-WIKI/Soul/Master_Pairs_Trading_Soul.ipynb'
with open(nb_path) as f:
    nb = json.load(f)

# ── Find the Stage 3A cell ────────────────────────────────────────────────────
# It's the cell containing "Stage 3A" in the source

NEW_STAGE3A = r"""# ── Stage 3A : In-Sample Grid-Search Optimisation ────────────────────────────
s2 = pd.read_csv('pairs_stage2_kalman_ou.csv')

# Run on ALL non-skipped pairs (tradeable flag is informational only)
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

    # Compute Kalman-smoothed beta/alpha path over IS
    ts, Ps, Pc, e_a, S_a, _, _, _ = kalman_smoother(ya, yb, Q_opt, R_opt, is_new_day_is)

    # ── CORRECT Z-SCORE: spread normalised by OU sigma ─────────────────────
    # spread_t = log(A_t) - beta_t * log(B_t) - alpha_t
    H_m    = np.column_stack([yb, np.ones(len(ya))])
    spread = ya - np.einsum("ti,ti->t", H_m, ts)

    ou_sigma = row['ou_sigma']
    ou_mu    = row['spread_mean']   # OU long-run mean (≈0 for log-price spread)

    # Fall back to empirical std if OU params are NaN
    if not np.isfinite(ou_sigma) or ou_sigma <= 0:
        ou_sigma = float(np.nanstd(spread))
    if not np.isfinite(ou_mu):
        ou_mu = float(np.nanmean(spread))
    if ou_sigma <= 1e-10:
        ou_sigma = 1e-10

    zs_is = (spread - ou_mu) / ou_sigma
    zs_is = np.where(np.isfinite(zs_is), zs_is, 0.0)
    # ────────────────────────────────────────────────────────────────────────

    # NaN guard on half-life
    hl_raw  = row['half_life_minutes']
    hl_bars = int(np.ceil(hl_raw)) if (np.isfinite(hl_raw) and hl_raw > 0) else 30
    hl_bars = min(hl_bars, 390)

    best_pnl  = -np.inf; best_tc = 0; best_wr = 0.0
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
        "ou_sigma": ou_sigma, "ou_mu": ou_mu,
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
print(f"Non-zero trade pairs: {(opt_df['trade_count']>0).sum()}")
"""

NEW_STAGE3B = r"""# ── Stage 3B : Out-of-Sample Backtest ────────────────────────────────────────
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
    z_ent = row['best_z_entry']; z_sl = row['best_z_sl']; hl_s = bool(row['best_hl_stop'])
    lagger = row['lagger']; lag_is_a = (lagger == "a")
    # ou params for Z-score normalisation (saved from Stage 3A)
    ou_sigma = float(row['ou_sigma']); ou_mu = float(row['ou_mu'])

    p2 = s2_df[(s2_df['symbol_a']==sa) & (s2_df['symbol_b']==sb)]
    if len(p2) == 0: continue
    p2 = p2.iloc[0]
    Q_opt = np.diag([p2['Q_beta'], p2['Q_alpha']]); R_opt = p2['R']
    hl_raw  = p2['half_life_minutes']
    hl_bars = int(np.ceil(hl_raw)) if (np.isfinite(hl_raw) and hl_raw > 0) else 30
    hl_bars = min(hl_bars, 390)

    if sa not in full_close or sb not in full_close: continue
    ya_f = np.log(full_close[sa]); yb_f = np.log(full_close[sb])
    ts_f, Ps_f, _, e_f, S_f, _, _, _ = kalman_smoother(ya_f, yb_f, Q_opt, R_opt, is_new_day_full)

    # OU Z-score on full series
    H_f    = np.column_stack([yb_f, np.ones(len(ya_f))])
    spread_f = ya_f - np.einsum("ti,ti->t", H_f, ts_f)
    if ou_sigma <= 1e-10: ou_sigma = max(float(np.nanstd(spread_f)), 1e-10)
    zs_f = (spread_f - ou_mu) / ou_sigma
    zs_f = np.where(np.isfinite(zs_f), zs_f, 0.0)

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
        nets  = [t['net'] for t in trades]
        gross = [t['gross'] for t in trades]
        fees_ = [t['fees'] for t in trades]
        cum   = np.cumsum(nets); pk = np.maximum.accumulate(cum)
        mdd   = float(np.max(pk-cum)) if len(cum) else 0.0
        bt_rows.append({
            "symbol_a": sa, "symbol_b": sb,
            "net_profit": sum(nets), "gross_profit": sum(gross), "total_fees": sum(fees_),
            "win_rate": sum(1 for t in trades if t['win'])/nt,
            "trade_count": nt, "max_drawdown": mdd,
            "exit_reasons": ";".join(set(t['why'] for t in trades)),
        })
    gc.collect()

bt_df = pd.DataFrame(bt_rows)
bt_df.to_csv('pairs_stage3b_backtest.csv', index=False)
print(f"Stage 3B done. Saved {len(bt_df)} rows.")
print(f"Pairs with trades: {(bt_df['trade_count']>0).sum()}")
print(f"Total net profit: {bt_df['net_profit'].sum():.2f}")
"""

# ── Inject patched cells into notebook ───────────────────────────────────────
for i, c in enumerate(nb['cells']):
    src = c.get('source', '')
    if isinstance(src, list): src = ''.join(src)
    if 'Stage 3A' in src and 'zs_is = e_a / np.sqrt' in src:
        nb['cells'][i]['source'] = NEW_STAGE3A
        print(f"Patched Stage 3A cell (index {i})")
    elif 'Stage 3B' in src and 'zerodha_fees' in src:
        nb['cells'][i]['source'] = NEW_STAGE3B
        print(f"Patched Stage 3B cell (index {i})")

with open(nb_path, 'w') as f:
    json.dump(nb, f, indent=1)
print("✅ Notebook patched with correct OU Z-score in Stage 3A and 3B")
