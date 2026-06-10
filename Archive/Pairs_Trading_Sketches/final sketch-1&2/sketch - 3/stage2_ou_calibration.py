import sqlite3
import pandas as pd
import numpy as np
import glob
import os

print("=== Stage 2: Ornstein-Uhlenbeck Chunked Calibration ===")

# Find local DB
hits = glob.glob('/storage/emulated/0/Quant/LLM-WIKI/**/*.sqlite', recursive=True)
db_candidates = [h for h in hits if "Master-Data-1min.sqlite" in h]
if not db_candidates:
    raise FileNotFoundError("Master-Data-1min.sqlite not found locally!")
DB_PATH = db_candidates[0]

# The Top 5 pairs extracted from Stage 1
top_pairs = [
    ("PFC", "RECLTD"),
    ("BDL", "MAZDOCK"),
    ("GRSE", "MAZDOCK"),
    ("BANKBARODA", "CANBK"),
    ("BPCL", "HINDPETRO")
]

symbols = list(set([sym for pair in top_pairs for sym in pair]))

con = sqlite3.connect(DB_PATH)
placeholders = ",".join(["?"] * len(symbols))
query = f"SELECT symbol, timestamp, close FROM ohlcv_1min WHERE symbol IN ({placeholders}) ORDER BY timestamp"
df = pd.read_sql(query, con, params=symbols)
con.close()

df['dt'] = pd.to_datetime(df['timestamp'], unit='s', utc=True).dt.tz_convert('Asia/Kolkata')

# Strict intraday filtering
time_int = df['dt'].dt.hour * 100 + df['dt'].dt.minute
df_trading = df[(time_int >= 915) & (time_int <= 1529)].copy()

price_matrix = df_trading.pivot(index='dt', columns='symbol', values='close')
del df, df_trading
import gc; gc.collect()

log_prices = np.log(price_matrix)

def calculate_chunked_half_life(ya, yb, num_chunks=4):
    """
    Splits the data into num_chunks.
    For each chunk, runs OLS to find spread, then AR(1) to find Half-Life.
    Returns the maximum (worst-case) valid half-life.
    """
    chunk_size = len(ya) // num_chunks
    half_lives = []
    
    for i in range(num_chunks):
        start_idx = i * chunk_size
        end_idx = (i + 1) * chunk_size if i < num_chunks - 1 else len(ya)
        
        y_chunk = ya[start_idx:end_idx]
        x_chunk = yb[start_idx:end_idx]
        
        # OLS to find static spread for this chunk
        X_mat = np.column_stack([x_chunk, np.ones(len(x_chunk))])
        beta_hat, _, _, _ = np.linalg.lstsq(X_mat, y_chunk, rcond=None)
        
        spread = y_chunk - (X_mat @ beta_hat)
        
        # AR(1) on spread
        s_t = spread[1:]
        s_t1 = spread[:-1]
        
        X_ar = np.column_stack([s_t1, np.ones(len(s_t1))])
        phi_hat, _, _, _ = np.linalg.lstsq(X_ar, s_t, rcond=None)
        phi = phi_hat[0]
        
        if 0 < phi < 1:
            hl = -np.log(2) / np.log(phi)
            half_lives.append(hl)
        else:
            # Divergent or non-stationary chunk
            pass
            
    if not half_lives:
        return np.inf, []
        
    worst_case_hl = np.max(half_lives)
    return worst_case_hl, half_lives

results = []
print(f"\\nAnalyzing {len(top_pairs)} Pairs across 4 Temporal Chunks...")

for pair in top_pairs:
    sym_a, sym_b = pair
    df_pair = log_prices[[sym_a, sym_b]].dropna()
    ya = df_pair[sym_a].values
    yb = df_pair[sym_b].values
    
    worst_hl, all_hls = calculate_chunked_half_life(ya, yb, num_chunks=4)
    
    formatted_hls = [f"{h:.1f}m" for h in all_hls]
    print(f"\\nPair: {sym_a} vs {sym_b}")
    print(f"Chunk Half-Lives: {formatted_hls}")
    
    if worst_hl != np.inf:
        print(f"Worst-Case Target Kalman Delay: {worst_hl:.1f} minutes")
        
        # Tune Q such that the Kalman Filter inherently lags this reversion speed.
        # If HL = 65, the filter's "window" should be roughly 130+ bars so it tracks the macro mean
        # without destroying the 65-minute localized reversion.
        target_lag = worst_hl * 2
        # Rough Kalman Gain mapping: K ~ 2 / (lag + 1)
        # Q / R scaling can be derived to enforce this K.
    else:
        print("Pair is NOT mean-reverting in any chunk!")
        
    results.append({
        "Symbol_A": sym_a,
        "Symbol_B": sym_b,
        "Worst_Case_HL_Min": worst_hl,
        "Chunk_HLs": formatted_hls
    })

res_df = pd.DataFrame(results)
res_df.to_csv("stage2_ou_chunked_results.csv", index=False)
print("\\nCalibration complete. Results saved to stage2_ou_chunked_results.csv")
