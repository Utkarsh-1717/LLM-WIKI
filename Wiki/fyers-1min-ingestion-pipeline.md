---
title: fyers-1min-ingestion-pipeline
type: concept
tags:
  - "concept"
topics: [pipeline, fyers, kaggle]
---

# Fyers 1-Min Ingestion Pipeline

The Fyers 1-Min Ingestion Pipeline is an automated process designed to fetch historical OHLCV data from the [[fyers-api]] for all Nifty 500 equities.

## Constraints & Solutions

1. **API Rate Limits**: The Fyers API restricts historical data fetching for 1-minute resolution to a maximum of 100 days per request. 
   *Solution*: The pipeline dynamically chunks the requested date range (e.g., 180 calendar days / 120 trading days) into two 90-day intervals.
2. **API Connection Drops**: To prevent getting blocked or facing timeout issues from rapid API requests.
   *Solution*: The loop strictly enforces a 0.5-second `time.sleep()` delay between every single API request.
3. **Local Hardware Limits**: Executing this loop locally violates our `AGENTS.md` rules regarding heavy network IO and compute durations.
   *Solution*: The entire script is packaged into a Jupyter Notebook and pushed to [[kaggle-compute]], taking advantage of Kaggle's infrastructure.
4. **Authentication Handling**: Passing the Fyers TOTP authentication through a headless environment.
   *Solution*: The script is hardcoded with credentials for one-time rapid execution, utilizing the 5-step TOTP flow to independently authenticate from Kaggle's servers.

## Outcome
The result of this pipeline is the [[master-data-1min-dataset]], which is exported and stored directly as a Kaggle dataset for immediate utilization in subsequent backtesting notebooks.

## Connections
- [[master-data-1min-dataset]]
- [[fyers-api]]
- [[kaggle-compute]]
