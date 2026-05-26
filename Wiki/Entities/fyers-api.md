---
tags:
  - "entity"
topics: [quant, fyers, api]
status: evergreen
created: 2026-05-26
updated: 2026-05-26
sources:
  - Raw/Sources/quant-agent-setup.md
  - Raw/Sources/agents-rules.md
source_count: 2
aliases: [fyers, fyers-broker]
---

# Fyers API

Fyers is an Indian stock broker providing a REST API for live data, historical data, and order management. Used as the primary market data source in the [[quant-agent-system]].

## Credentials

All credentials in `~/.quant_env` — never committed.

| Variable | Purpose |
|---|---|
| `FYERS_APP_ID` | Application ID (e.g. `G0NX5M08ZG-100`) |
| `FYERS_SECRET_KEY` | App secret key |
| `FYERS_TOTP_KEY` | TOTP seed for 2FA |
| `FYERS_USERNAME` | Fyers user ID |
| `FYERS_PIN` | Login PIN |
| `FYERS_REDIRECT` | OAuth redirect URI |

## Authentication

5-step TOTP flow — see fyers-auth skill in [[quant-agent-system]].

Steps:
1. POST `/vagator/v2/send_login_otp`
2. POST `/vagator/v2/verify_otp` (TOTP via pyotp)
3. POST `/vagator/v2/verify_pin`
4. POST `/api/v3/token` → extract auth_code
5. `fyersModel.SessionModel.generate_token()` → access_token

Token format: `APP_ID:access_token` — valid for current session only, never written to file.

## Historical Data API

Endpoint: `GET https://api-t1.fyers.in/api/v3/data/history`

| Param | Value |
|---|---|
| `resolution` | `"1"` (1-minute bars) |
| `date_format` | `1` (Unix timestamp) |
| `cont_flag` | `1` |
| Max range | 100 days per call |

Rule: Always chunk requests to ≤100 days. Sleep 0.5s between calls.

## Output Schema

SQLite table `ohlcv_1min`:
- `id` INTEGER PRIMARY KEY
- `symbol` TEXT
- `timestamp` INTEGER
- `open`, `high`, `low`, `close` REAL
- `volume` INTEGER
- Index on `(symbol, timestamp)`

## Related

- [[quant-agent-system]] — uses Fyers as data source
- [[kaggle-compute]] — where data is uploaded for processing
- [[agent-rules]] — API rate limit rule (0.5s sleep)
