---
title: master-data-1min-dataset
type: entity
tags:
  - "entity"
topics: [dataset, kaggle, fyers]
---

# Master-Data-1min (Kaggle Dataset)

The `Master-Data-1min` dataset is a robust SQLite database stored natively on Kaggle. It contains historical 1-minute OHLCV (Open, High, Low, Close, Volume) data for all equities in the NSE 500 index.

## Specs & Features
- **Data Source**: [[fyers-api]] via `fyers_apiv3` Python library.
- **Universe**: Official Nifty 500 symbol list (fetched dynamically from NSE archives).
- **Timeframe**: 1-minute resolution.
- **Lookback Period**: The most recent 120 trading days (~175 calendar days).
- **Format**: SQLite Database (`Master-Data-1min.sqlite`). Table `ohlcv_1min`.
- **Primary Keys**: Composite index on `symbol` and `timestamp`.

## Confirmed Table Schema — `ohlcv_1min`

| Column | Type | Notes |
|---|---|---|
| `symbol` | TEXT | NSE ticker e.g. `'PFC'` |
| `timestamp` | INTEGER | UNIX epoch **seconds** (UTC) — NOT `ts` |
| `open` | REAL | Opening price |
| `high` | REAL | High price |
| `low` | REAL | Low price |
| `close` | REAL | Closing price |
| `volume` | REAL | Volume |

> ⚠️ **Critical**: Column is `timestamp`, NOT `ts`. Convert with `pd.to_datetime(df['timestamp'], unit='s', utc=True).dt.tz_convert('Asia/Kolkata')` to get IST datetimes.

## Creation Process
This dataset was generated using the [[fyers-1min-ingestion-pipeline]] which ran entirely on [[kaggle-compute]] via a dedicated Notebook, effectively shifting heavy IO operations off local hardware. 

To use this dataset in future Kaggle projects, simply attach the `utkarshpatelthefirst/master-data-1min-db` dataset to your notebook environment.

## Connections
- [[session-2026-06-02b]]
- [[session-2026-05-30]]
- [[fyers-historical-kaggle]]
- [[pearson-correlation-screening]]
- [[log-return-computation]]
- [[index]]
- [[cloud-tick-pipeline]]
- [[fyers-1min-ingestion-pipeline]]
- [[fyers-api]]
- [[kaggle-compute]]
- [[qt-tick-collector]] — tick-level companion dataset (higher resolution than 1-min bars)
- [[higher-level-tick-pipeline]] — planned cloud pipeline producing the tick-level complement to this dataset
- [[pairs-stage1-pearson]] — Stage 1 Pearson correlation output computed from this dataset
- [[pairs-trading-pipeline]] — this dataset feeds all stages of the pairs trading pipeline
- [[session-continuous-returns]] — return computation methodology applied to this data
- [[timeseries-alignment]] — alignment approach used when working with this dataset
