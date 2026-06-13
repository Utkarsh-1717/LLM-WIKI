import csv
import math

file_path = "/storage/emulated/0/Quant/LLM-WIKI/kaggle_final_output_v2/continuous_ols_production_results.csv"

data = []
try:
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                # Need ols_trades >= 5
                trades = int(row["ols_trades"])
                if trades < 5:
                    continue
                
                net_pnl = float(row["ols_net_pnl"])
                spread_vol = float(row["spread_vol"])
                mean_abs_dev = float(row["mean_abs_dev"])
                zero_crossings = int(row["zero_crossings"])
                half_life = float(row["half_life"]) if row["half_life"] else float('nan')
                kalman_q = float(row["kalman_q"]) if row["kalman_q"] else float('nan')
                adf_pval = float(row["adf_pval"]) if row["adf_pval"] else float('nan')
                gross_win_rate = float(row["gross_win_rate"])
                
                if math.isnan(half_life) or math.isnan(kalman_q) or math.isnan(adf_pval):
                    continue
                    
                data.append({
                    "pair": row["pair"],
                    "net_pnl": net_pnl,
                    "spread_vol": spread_vol,
                    "mean_abs_dev": mean_abs_dev,
                    "zero_crossings": zero_crossings,
                    "half_life": half_life,
                    "kalman_q": kalman_q,
                    "adf_pval": adf_pval,
                    "gross_win_rate": gross_win_rate,
                    "trades": trades
                })
            except (ValueError, KeyError) as e:
                pass
except Exception as e:
    print(f"Error reading: {e}")
    exit()

print(f"Total valid pairs loaded: {len(data)}")

# Sort by PnL
data.sort(key=lambda x: x["net_pnl"], reverse=True)

top_50 = data[:50]
bottom_50 = data[-50:]

def print_averages(dataset, title):
    print(f"\\n--- {title} ---")
    n = len(dataset)
    if n == 0: return
    
    avg_pnl = sum(d["net_pnl"] for d in dataset) / n
    avg_trades = sum(d["trades"] for d in dataset) / n
    avg_win = sum(d["gross_win_rate"] for d in dataset) / n
    avg_svol = sum(d["spread_vol"] for d in dataset) / n
    avg_mad = sum(d["mean_abs_dev"] for d in dataset) / n
    avg_zc = sum(d["zero_crossings"] for d in dataset) / n
    avg_hl = sum(d["half_life"] for d in dataset) / n
    avg_kq = sum(d["kalman_q"] for d in dataset) / n
    avg_adf = sum(d["adf_pval"] for d in dataset) / n
    
    print(f"PnL            : {avg_pnl:.2f}")
    print(f"Trades         : {avg_trades:.1f}")
    print(f"Win Rate       : {avg_win:.4f}")
    print(f"Spread Vol     : {avg_svol:.6f}")
    print(f"Mean Abs Dev   : {avg_mad:.6f}")
    print(f"Zero Crossings : {avg_zc:.1f}")
    print(f"Half Life      : {avg_hl:.1f}")
    print(f"Kalman Q       : {avg_kq:.4e}")
    print(f"ADF P-Val      : {avg_adf:.4e}")

print_averages(top_50, "TOP 50 PAIRS (HIGH PROFIT)")
print_averages(bottom_50, "BOTTOM 50 PAIRS (HIGH LOSS)")

# Let's also do Decile Analysis on ADF pval
data.sort(key=lambda x: x["adf_pval"])
decile_size = len(data) // 10

if decile_size > 0:
    print("\\n--- DECILE ANALYSIS (Sorted by ADF p-value, lowest to highest) ---")
    for i in range(10):
        start = i * decile_size
        # Last decile takes the remainder
        end = (i + 1) * decile_size if i < 9 else len(data)
        decile_data = data[start:end]
        
        avg_pval = sum(d["adf_pval"] for d in decile_data) / len(decile_data)
        avg_pnl = sum(d["net_pnl"] for d in decile_data) / len(decile_data)
        avg_trades = sum(d["trades"] for d in decile_data) / len(decile_data)
        
        print(f"Decile {i+1} | P-Val: {avg_pval:.5f} | Avg PnL: {avg_pnl:>8.2f} | Trades: {avg_trades:.1f}")
