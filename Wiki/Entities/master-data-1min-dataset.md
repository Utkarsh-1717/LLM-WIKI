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

## Creation Process
This dataset was generated using the [[fyers-1min-ingestion-pipeline]] which ran entirely on [[kaggle-compute]] via a dedicated Notebook, effectively shifting heavy IO operations off local hardware. 

To use this dataset in future Kaggle projects, simply attach the `utkarshpatelthefirst/master-data-1min-db` dataset to your notebook environment.

## Connections
- [[fyers-1min-ingestion-pipeline]]
- [[fyers-api]]
- [[kaggle-compute]]
