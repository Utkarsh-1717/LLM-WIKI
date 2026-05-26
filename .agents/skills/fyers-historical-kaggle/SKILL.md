---
name: fyers-historical-kaggle
trigger: [nse 500 data, fetch all stocks, 1min kaggle, historical kaggle, bulk historical]
description: Fetches historical 1-min OHLCV data for NSE 500 (or any bulk list) from Fyers API AND publishes it as a Kaggle dataset — all inside ONE Kaggle notebook. No local downloads.
version: 1.0.0
last_updated: 2026-05-26
---

# Fyers Historical Data — Kaggle Pipeline Skill

## Key Design Decisions (Learned from Production Run)

1. **One notebook = fetch + publish**. Never split into two notebooks. The second notebook cannot reliably read the first notebook's output SQLite file when that file is large (2+ GB).
2. **Hardcode credentials directly in the notebook**. No credential datasets, no file loading. The TOTP regenerates fresh every 30 seconds so hardcoding is safe for notebook runs.
3. **Fyers API limit**: 1-minute resolution allows max **100 days per request**. Always chunk date ranges into ≤90-day windows with 0.5s sleep between each call.
4. **NSE Symbol format**: `NSE:<SYMBOL>-EQ` (e.g. `NSE:RELIANCE-EQ`)
5. **Output path in Kaggle**: SQLite always saved to `/kaggle/working/<filename>.sqlite`

## Fyers API Chunking Formula

To cover ~120 trading days (≈175 calendar days):
```python
end_date   = datetime.now()
start_date = end_date - timedelta(days=175)

chunks = [
    (start_date.strftime("%Y-%m-%d"),                    (start_date + timedelta(days=90)).strftime("%Y-%m-%d")),
    ((start_date + timedelta(days=91)).strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
]
```
This produces exactly 2 API calls per symbol. With 500 symbols × 2 calls × 0.5s sleep = ~8.5 minutes of pure sleep time. Total runtime ≈ 15–20 minutes on Kaggle.

## NSE 500 Symbol List

Always fetch dynamically from NSE archives (never hardcode the list):
```python
import urllib.request, pandas as pd
from io import StringIO

req = urllib.request.Request(
    'https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv',
    headers={'User-Agent': 'Mozilla/5.0'}
)
with urllib.request.urlopen(req) as response:
    df = pd.read_csv(StringIO(response.read().decode('utf-8')))
symbols = df['Symbol'].tolist()  # plain symbol e.g. 'RELIANCE'
# Convert: fyers_sym = f"NSE:{sym}-EQ"
```

## SQLite Schema

```sql
CREATE TABLE IF NOT EXISTS ohlcv_1min (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol    TEXT,
    timestamp INTEGER,
    open      REAL,
    high      REAL,
    low       REAL,
    close     REAL,
    volume    INTEGER,
    UNIQUE(symbol, timestamp)
);
CREATE INDEX IF NOT EXISTS idx_sym_ts ON ohlcv_1min(symbol, timestamp);
PRAGMA journal_mode=DELETE;
PRAGMA synchronous=NORMAL;
```

## Error Handling Pattern

```python
errors = {}
for sym in symbols:
    try:
        response = fyers.history(data=data)
        if response.get("s") == "ok" and response.get("candles"):
            # insert rows...
        else:
            errors.setdefault(sym, []).append(response.get("message", "Unknown"))
    except Exception as e:
        errors.setdefault(sym, []).append(str(e))
    time.sleep(0.5)
```
Errors (delisted symbols, API timeouts) are collected silently and printed in a final summary — never raise exceptions that stop the loop.

## Dataset Publishing (Same Notebook, Final Stage)

```python
import json, shutil
from kaggle.api.kaggle_api_extended import KaggleApi

os.environ['KAGGLE_USERNAME'] = 'utkarshpatelthefirst'
os.environ['KAGGLE_KEY']      = 'fbef16329099428205f671dd5de8337b'

api = KaggleApi()
api.authenticate()

export_dir = '/kaggle/working/dataset_export'
os.makedirs(export_dir, exist_ok=True)
shutil.copy('/kaggle/working/Master-Data-1min.sqlite', f'{export_dir}/Master-Data-1min.sqlite')

api.dataset_initialize(export_dir)
with open(f'{export_dir}/dataset-metadata.json') as f:
    meta = json.load(f)
meta['title']    = 'Master-Data-1min'
meta['id']       = 'utkarshpatelthefirst/master-data-1min-db'
meta['licenses'] = [{'name': 'CC0-1.0'}]
with open(f'{export_dir}/dataset-metadata.json', 'w') as f:
    json.dump(meta, f, indent=2)

# Use dataset_create_new for first time, dataset_create_version for updates
api.dataset_create_new(export_dir, dir_mode='zip', quiet=False)
# OR for updates:
# api.dataset_create_version(export_dir, version_notes="update-YYYY-MM-DD", dir_mode='zip')
print("✅ Dataset published!")
```

## Verification Query (Final Stage)

```python
df_summary = pd.read_sql_query("""
SELECT symbol,
       COUNT(*) AS total_rows,
       MIN(datetime(timestamp, 'unixepoch')) AS from_date,
       MAX(datetime(timestamp, 'unixepoch')) AS to_date,
       COUNT(DISTINCT date(timestamp, 'unixepoch')) AS trading_days
FROM ohlcv_1min
GROUP BY symbol
""", conn)

print(f"Total Equities: {len(df_summary)}")
print(f"Total Rows: {df_summary['total_rows'].sum():,}")
print(f"Avg Trading Days: {df_summary['trading_days'].mean():.1f}")
print(f"DB Size: {os.path.getsize(db_path)/(1024*1024):.1f} MB")
```

## Connections
- [[kaggle-notebook-run]]
- [[fyers-auth]]
- [[kaggle-pulse-check]]
- [[master-data-1min-dataset]]
