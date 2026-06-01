---
Title: QT — Quantitative Tick Collector v2.0
Reference: qt.py
format: python
source_file: Raw/Sources/attachments/qt.py
Created: 2026-05-30
updated: 2026-05-30
Processed: true
tags:
  - source
sources:
  - Raw/Sources/attachments/qt.py
source_count: 1
---

## Section 1 — Overview

**Script name:** `qt.py` — QT (Quantitative Tick Collector) v2.0
**Purpose:** Automated intraday tick data collector for Indian equity and futures markets, running on a local Android device (Termux/Android). Subscribes to the Fyers WebSocket feed and stores every tick into per-symbol SQLite databases.

**Key dependencies:**
- `fyers_apiv3` — Fyers Python SDK (REST + WebSocket)
- `pyotp` — TOTP-based authentication
- `sqlite3` — local database storage
- `requests` — HTTP for auth flow
- `json`, `time`, `os`, `calendar`, `datetime`

**Entry point:** `if __name__ == "__main__"` block at line 478.

---

## Section 2 — Function Inventory

| Function | Signature | Purpose |
|---|---|---|
| `last_thursday` | `(year: int, month: int) -> date` | Returns the last Thursday of a given month (used for NSE futures expiry) |
| `resolve_expiry_month` | `(today: datetime) -> tuple` | Returns `(yy_str, mon_str)` for the active futures contract; rolls to next month on/after expiry date |
| `build_future_symbols` | `() -> dict` | Builds the 4 trading symbol strings; tries to persist resolved symbols back to `config.json` |
| `wait_for_market` | `() -> None` | Busy-waits until 09:14 IST (1 minute before NSE open), printing countdown every 30s |
| `get_token` | `() -> str \| None` | Runs the 5-step Fyers TOTP authentication flow; returns `APP_ID:access_token` or `None` on failure |
| `setup_db` | `(path: str) -> sqlite3.Connection` | Creates a SQLite DB with the `ticks` table and 3 indexes; configured for Android (`journal_mode=DELETE`) |
| `extract_oi` | `(t: dict) -> Any` | Tries all known Fyers OI field name variants (`open_interest`, `oi`, `OI`, `openInterest`) |
| `on_tick` | `(msg) -> None` | WebSocket callback; parses each tick dict and inserts into the correct symbol's DB; commits every 200 ticks or 15 seconds |
| `on_error` | `(msg) -> None` | WebSocket error callback; prints error message |
| `on_close` | `(msg) -> None` | WebSocket close callback; commits and closes all DB connections, prints session summary |
| `on_open` | `() -> None` | WebSocket open callback; subscribes to all 4 symbols via `SymbolUpdate` data type |

---

## Section 3 — Core Logic Summary

1. **Config load:** Reads `APP_ID`, `SECRET`, `TOTP_KEY`, `USERNAME`, `PIN` from `/sdcard/QT/config.json`.
2. **Expiry resolution:** Calculates the last Thursday of the current month. If today is on or after expiry, rolls the contract to next month. Builds Fyers symbol strings (e.g., `NSE:NIFTY26JUNFUT`).
3. **DB setup:** Creates one SQLite database per symbol in a dated subdirectory (`/sdcard/QT/YYYY-MM-DD/<SYMBOL>.db`).
4. **Market wait:** Sleeps until 09:14 IST before attempting auth.
5. **Authentication:** Runs the full 5-step Fyers TOTP flow (send OTP → verify OTP → verify PIN → get auth code → exchange for access token).
6. **WebSocket streaming:** Connects to Fyers DataSocket in full mode (`litemode=False`), subscribes to `SymbolUpdate` for all 4 symbols. Every incoming tick is inserted into the matching symbol's DB.
7. **Commit strategy:** Commits every 200 ticks or every 15 seconds, whichever comes first — balancing data safety against write overhead on Android.
8. **Session end:** On WebSocket close, all connections are committed and closed cleanly.

---

## Section 4 — Data Flow

```
config.json
    ↓
Expiry resolution → SYMBOL_MAP (4 symbols)
    ↓
SQLite DBs created (one per symbol)
    ↓
[wait for 09:14 IST]
    ↓
Fyers TOTP Auth (5 steps via HTTP) → access_token
    ↓
Fyers WebSocket (SymbolUpdate, full mode)
    ↓ on_tick callback
INSERT INTO ticks (28 fields + raw_json)
    ↓ every 200 ticks or 15s
COMMIT
    ↓ on_close
Final COMMIT + CLOSE
    ↓
/sdcard/QT/YYYY-MM-DD/<SYMBOL>.db
```

**Tick schema (28 fields):**
- Timestamps: `recv_ts`, `exch_ts`, `trade_ts` (all milliseconds)
- Price & trade: `ltp`, `ltq`, `avg_trade_price`
- Volume (CVD-ready): `tot_buy_qty`, `tot_sell_qty`, `vol_traded_today`
- Best bid/ask: `bid_price`, `bid_size`, `ask_price`, `ask_size`
- OHLC: `open_price`, `high_price`, `low_price`, `prev_close_price`
- Change: `ch`, `chp`
- Open interest (futures): `open_interest`, `oi_day_high`, `oi_day_low`
- Circuit & 52-week: `upper_circuit`, `lower_circuit`, `week52_high`, `week52_low`
- Full raw payload: `raw_json` (TEXT)

---

## Section 5 — Usage

```bash
# 1. Ensure /sdcard/QT/config.json exists with credentials
# 2. Run from Termux on Android
python3 qt.py
```

**config.json required keys:**
```json
{
  "app_id": "...",
  "secret_key": "...",
  "totp_key": "...",
  "username": "...",
  "pin": "...",
  "static_largecap": "NSE:HDFCBANK-EQ",
  "static_midcap": "NSE:PERSISTENT-EQ"
}
```

Script starts collecting from 09:14 IST and runs until the WebSocket session closes (typically 15:30 IST market end or manual interrupt).

---

## Section 6 — Connections

| External Service | Usage |
|---|---|
| Fyers REST API (api-t2.fyers.in, api-t1.fyers.in) | 5-step TOTP authentication |
| Fyers WebSocket (DataSocket) | SymbolUpdate tick feed |
| SQLite (local Android storage) | Per-symbol tick databases |
| NSE calendar logic | Futures expiry calculation (last Thursday) |

**Symbols tracked:**
1. `NSE:NIFTY{YY}{MON}FUT` — Nifty 50 Futures (auto-rolling)
2. `NSE:BANKNIFTY{YY}{MON}FUT` — Bank Nifty Futures (auto-rolling)
3. `NSE:HDFCBANK-EQ` — Large-cap equity (static, configurable)
4. `NSE:PERSISTENT-EQ` — Mid-cap equity (static, configurable)
