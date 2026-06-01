---
tags:
  - "entity"
topics: [skill, fyers, kaggle, data-pipeline]
status: active
---

# Fyers Historical Kaggle Skill

The [[fyers-historical-kaggle]] skill orchestrates the entire bulk 1-minute data ingestion pipeline for the NSE 500 index. It merges the capabilities of [[fyers-api]] fetching with [[kaggle-compute]] infrastructure, allowing agents to reliably generate a multi-gigabyte historical database without downloading files to the local device.

## Connections
- [[master-data-1min-dataset]]
- [[fyers-1min-ingestion-pipeline]]
- [[fyers-api]]
- [[kaggle-compute]]
- [[qt-tick-collector]] — this skill handles 1-min OHLCV; qt-tick-collector handles real-time tick collection
- [[higher-level-tick-pipeline]] — the planned tick pipeline that will use similar Kaggle publish patterns
