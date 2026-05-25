---
name: fyers-historical
trigger: [download historical, fetch 1-min, OHLCV, historical data, stock database]
description: Downloads historical 1-min OHLCV data via Fyers REST API into SQLite
---

## Rules

1. Always execute fyers-auth skill first to get token
2. API endpoint: GET https://api-t1.fyers.in/api/v3/data/history
   Params: symbol, resolution:"1", date_format:1, range_from, range_to, cont_flag:1
3. Chunk requests: max 100 days per call — loop until full range covered
4. Sleep 0.5s between every API call — no exceptions
5. Output: SQLite database
   - Table: ohlcv_1min
   - Columns: id INTEGER PRIMARY KEY, symbol TEXT, timestamp INTEGER,
     open REAL, high REAL, low REAL, close REAL, volume INTEGER
   - Index on (symbol, timestamp)
   - PRAGMA journal_mode=DELETE (Android compatibility)
   - PRAGMA synchronous=NORMAL
6. Single-threaded only — HARDWARE CONSTRAINT
7. On completion report: symbol, date range, total rows, file path, file size
8. If file already exists: append only new rows (check last timestamp first)
