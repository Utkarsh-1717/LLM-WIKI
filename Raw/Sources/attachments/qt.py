"""
QT — Quantitative Tick Collector v2.0
Assets : Nifty Future | BankNifty Future | HDFCBANK (LargeCap) | PERSISTENT (MidCap)
Feature: Auto-selects correct futures expiry symbol based on today's date
         Falls back to internal symbol resolution if config update fails
"""

import json
import sqlite3
import time
import os
import requests
import pyotp
import calendar
from datetime import datetime, timedelta, date
from fyers_apiv3 import fyersModel
from fyers_apiv3.FyersWebsocket import data_ws

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = "/sdcard/QT"
CONFIG_PATH = f"{BASE_DIR}/config.json"

# ── Load config ───────────────────────────────────────────────────────────────
with open(CONFIG_PATH) as f:
    cfg = json.load(f)

APP_ID   = cfg["app_id"]
SECRET   = cfg["secret_key"]
TOTP_KEY = cfg["totp_key"]
USERNAME = cfg["username"]
PIN      = cfg["pin"]
REDIRECT = "https://trade.fyers.in/api-login/redirect-uri/index.html"

# ── Date setup ────────────────────────────────────────────────────────────────
TODAY_DT  = datetime.now()
TODAY_STR = TODAY_DT.strftime("%d-%m-%Y")          # dd-mm-yyyy as requested
DATA_DIR  = f"{BASE_DIR}/{TODAY_DT.strftime('%Y-%m-%d')}"
os.makedirs(DATA_DIR, exist_ok=True)

# ══════════════════════════════════════════════════════════════════════════════
#  AUTO EXPIRY RESOLVER
#  Nifty & BankNifty futures expire on the LAST THURSDAY of each month.
#  Fyers symbol format: NSE:NIFTY{YY}{MON}FUT  e.g. NSE:NIFTY26APRFUT
#  Rule:
#    - If today < last Thursday of this month  → use this month
#    - If today >= last Thursday (expiry day)  → roll to next month
# ══════════════════════════════════════════════════════════════════════════════

def last_thursday(year: int, month: int) -> date:
    """Return the last Thursday of the given month."""
    last_day = calendar.monthrange(year, month)[1]
    d = date(year, month, last_day)
    # weekday(): Monday=0 … Thursday=3 … Sunday=6
    offset = (d.weekday() - 3) % 7
    return d - timedelta(days=offset)


def resolve_expiry_month(today: datetime) -> tuple:
    """
    Returns (yy_str, mon_str) for the active futures contract.
    E.g. ('26', 'APR') for April 2026.
    """
    y, m = today.year, today.month
    expiry = last_thursday(y, m)

    if today.date() >= expiry:
        # Roll to next month
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1

    mon_str = datetime(y, m, 1).strftime("%b").upper()   # JAN, FEB … DEC
    yy_str  = str(y)[2:]                                  # '26'
    return yy_str, mon_str


def build_future_symbols() -> dict:
    """
    Builds the 4 trading symbols.
    Tries to update config.json for audit trail; silently falls back if it fails.
    """
    yy, mon = resolve_expiry_month(TODAY_DT)

    nifty_fut     = f"NSE:NIFTY{yy}{mon}FUT"
    banknifty_fut = f"NSE:BANKNIFTY{yy}{mon}FUT"
    largecap_eq   = cfg.get("static_largecap",  "NSE:HDFCBANK-EQ")
    midcap_eq     = cfg.get("static_midcap",    "NSE:PERSISTENT-EQ")

    symbols = {
        "nifty_fut":   nifty_fut,
        "banknifty_fut": banknifty_fut,
        "largecap_eq": largecap_eq,
        "midcap_eq":   midcap_eq,
    }

    # ── Try to write resolved symbols back to config for audit trail ──────────
    try:
        cfg["resolved_symbols"]       = symbols
        cfg["resolved_date"]          = TODAY_STR
        cfg["active_expiry_month"]    = f"{mon}{yy}"
        cfg["next_expiry_date"]       = last_thursday(
            TODAY_DT.year, TODAY_DT.month).strftime("%d-%m-%Y")
        with open(CONFIG_PATH, "w") as f:
            json.dump(cfg, f, indent=2)
        print(f"Config updated with resolved symbols ({TODAY_STR})")
    except Exception as e:
        print(f"Config write skipped (using internal resolution): {e}")

    return symbols


# ── Resolve symbols now ───────────────────────────────────────────────────────
SYMBOL_MAP = build_future_symbols()
SYMBOLS    = list(SYMBOL_MAP.values())

print(f"\n{'─'*55}")
print(f"  QT v2.0  |  {TODAY_STR}")
print(f"{'─'*55}")
for k, v in SYMBOL_MAP.items():
    print(f"  {k:<18} →  {v}")
print(f"{'─'*55}\n")


# ══════════════════════════════════════════════════════════════════════════════
#  MARKET WAIT
# ══════════════════════════════════════════════════════════════════════════════

def wait_for_market():
    while True:
        now = datetime.now()
        if now.hour > 9 or (now.hour == 9 and now.minute >= 14):
            print(f"Market ready at {now.strftime('%H:%M:%S')}")
            break
        total_now  = now.hour * 3600 + now.minute * 60 + now.second
        target_sec = (9 * 60 + 14) * 60
        secs       = target_sec - total_now
        if secs > 60:
            print(f"  Waiting {secs // 60}m {secs % 60}s until 09:14 …")
            time.sleep(30)
        else:
            print(f"  Starting in {secs}s …")
            time.sleep(1)


# ══════════════════════════════════════════════════════════════════════════════
#  AUTHENTICATION
# ══════════════════════════════════════════════════════════════════════════════

def get_token() -> str | None:
    print("Authenticating …")
    try:
        totp = pyotp.TOTP(TOTP_KEY).now()

        # Step 1 – Send login OTP
        r = requests.post(
            "https://api-t2.fyers.in/vagator/v2/send_login_otp",
            json={"fy_id": USERNAME, "app_id": "2"}, timeout=10)
        s1 = r.json().get("s")
        print(f"  Step1 (send OTP):   {s1}")
        if s1 != "ok":
            print(f"  ERROR: {r.json()}")
            return None
        rk = r.json()["request_key"]

        # Step 2 – Verify TOTP
        r = requests.post(
            "https://api-t2.fyers.in/vagator/v2/verify_otp",
            json={"request_key": rk, "otp": totp}, timeout=10)
        s2 = r.json().get("s")
        print(f"  Step2 (verify OTP): {s2}")
        if s2 != "ok":
            print(f"  ERROR: {r.json()}")
            return None
        rk = r.json()["request_key"]

        # Step 3 – Verify PIN
        r = requests.post(
            "https://api-t2.fyers.in/vagator/v2/verify_pin",
            json={"request_key": rk,
                  "identity_type": "pin",
                  "identifier":    str(PIN)}, timeout=10)
        s3 = r.json().get("s")
        print(f"  Step3 (verify PIN): {s3}")
        if s3 != "ok":
            print(f"  ERROR: {r.json()}")
            return None
        temp_token = r.json()["data"]["access_token"]

        # Step 4 – Get auth code
        r = requests.post(
            "https://api-t1.fyers.in/api/v3/token",
            headers={"Authorization": f"Bearer {temp_token}"},
            json={
                "fyers_id":      USERNAME,
                "app_id":        APP_ID.split("-")[0],
                "redirect_uri":  REDIRECT,
                "appType":       "100",
                "code_challenge": "",
                "state":         "x",
                "scope":         "",
                "nonce":         "",
                "response_type": "code",
                "create_cookie": True,
            }, timeout=10)
        s4 = r.json().get("s")
        print(f"  Step4 (auth code):  {s4}")
        url = r.json().get("Url", "")
        if "auth_code=" not in url:
            print(f"  ERROR: URL missing auth_code — {url}")
            return None
        auth_code = url.split("auth_code=")[1].split("&")[0]

        # Step 5 – Exchange auth code for access token
        session = fyersModel.SessionModel(
            client_id=APP_ID, secret_key=SECRET,
            redirect_uri=REDIRECT, response_type="code",
            grant_type="authorization_code")
        session.set_token(auth_code)
        resp = session.generate_token()
        s5   = resp.get("s")
        print(f"  Step5 (token):      {s5}")
        token = resp.get("access_token")
        if not token:
            print(f"  ERROR: {resp}")
            return None

        print("  ✓ Token OK\n")
        return f"{APP_ID}:{token}"

    except Exception as e:
        print(f"  Auth error: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  DATABASE SETUP
#  One SQLite DB per symbol.
#  Schema captures EVERY field the Fyers SymbolUpdate feed provides.
#  Futures fields (OI, OI day high/low) are NULL for equities — that is fine.
# ══════════════════════════════════════════════════════════════════════════════

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS ticks (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Timestamps (milliseconds)
    recv_ts             INTEGER,    -- wall-clock time this row was written
    exch_ts             INTEGER,    -- exchange feed timestamp  (exch_feed_time × 1000)
    trade_ts            INTEGER,    -- last trade timestamp     (last_traded_time × 1000)

    -- Price & Trade fields
    ltp                 REAL,       -- last traded price
    ltq                 INTEGER,    -- last traded quantity
    avg_trade_price     REAL,       -- volume-weighted average price today

    -- Volume (BUY / SELL split — your core CVD data)
    tot_buy_qty         INTEGER,    -- cumulative aggressive BUY quantity today
    tot_sell_qty        INTEGER,    -- cumulative aggressive SELL quantity today
    vol_traded_today    INTEGER,    -- total volume today

    -- Best Bid / Ask (Level-1 depth)
    bid_price           REAL,
    bid_size            INTEGER,
    ask_price           REAL,
    ask_size            INTEGER,

    -- OHLC
    open_price          REAL,
    high_price          REAL,
    low_price           REAL,
    prev_close_price    REAL,

    -- Change
    ch                  REAL,       -- absolute change from prev close
    chp                 REAL,       -- percentage change from prev close

    -- Open Interest (futures only; NULL for equities)
    open_interest       REAL,
    oi_day_high         REAL,       -- OI intraday high
    oi_day_low          REAL,       -- OI intraday low

    -- Circuit limits & 52-week range (equities; may be NULL for futures)
    upper_circuit       REAL,
    lower_circuit       REAL,
    week52_high         REAL,
    week52_low          REAL,

    -- Full raw JSON for any future fields added by Fyers
    raw_json            TEXT
)
"""

INDEX_SQL = """
    CREATE INDEX IF NOT EXISTS idx_exch_ts  ON ticks(exch_ts);
    CREATE INDEX IF NOT EXISTS idx_trade_ts ON ticks(trade_ts);
    CREATE INDEX IF NOT EXISTS idx_ltp      ON ticks(ltp);
"""


def setup_db(path: str):
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=DELETE")   # no .wal / .shm on Android
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=8000")
    conn.execute(CREATE_SQL)
    for stmt in INDEX_SQL.strip().split(";"):
        s = stmt.strip()
        if s:
            conn.execute(s)
    conn.commit()
    return conn


# ── Open one DB per symbol ────────────────────────────────────────────────────
dbs = {}
for sym in SYMBOLS:
    # Sanitise symbol string to a filesystem-safe name
    name = (sym.replace("NSE:", "")
               .replace("BSE:", "")
               .replace("-EQ", "")
               .replace("-", "_"))
    path      = f"{DATA_DIR}/{name}.db"
    dbs[sym]  = setup_db(path)
    print(f"  DB ready: {path}")
print()

tick_count = 0
last_commit_time = time.time()
COMMIT_INTERVAL_SEC = 15    # commit every 15 s regardless of tick count
COMMIT_EVERY_N_TICKS = 200  # or every 200 ticks, whichever comes first


# ══════════════════════════════════════════════════════════════════════════════
#  WEBSOCKET CALLBACKS
# ══════════════════════════════════════════════════════════════════════════════

INSERT_SQL = """
    INSERT INTO ticks VALUES (
        NULL,
        ?,?,?,   -- recv_ts, exch_ts, trade_ts
        ?,?,?,   -- ltp, ltq, avg_trade_price
        ?,?,?,   -- tot_buy_qty, tot_sell_qty, vol_traded_today
        ?,?,?,?, -- bid_price, bid_size, ask_price, ask_size
        ?,?,?,?, -- open, high, low, prev_close
        ?,?,     -- ch, chp
        ?,?,?,   -- oi, oi_day_high, oi_day_low
        ?,?,?,?, -- upper_circuit, lower_circuit, 52w_high, 52w_low
        ?        -- raw_json
    )
"""


def extract_oi(t: dict):
    """Fyers uses inconsistent OI field names — try all."""
    for key in ("open_interest", "oi", "OI", "openInterest"):
        v = t.get(key)
        if v is not None:
            return v
    return None


def on_tick(msg):
    global tick_count, last_commit_time
    try:
        ticks = msg if isinstance(msg, list) else [msg]
        for t in ticks:
            sym = t.get("symbol", "")
            if sym not in dbs:
                continue

            conn     = dbs[sym]
            recv_ts  = int(time.time() * 1000)
            exch_ts  = (t.get("exch_feed_time",  0) or 0) * 1000
            trade_ts = (t.get("last_traded_time", 0) or 0) * 1000

            conn.execute(INSERT_SQL, (
                # Timestamps
                recv_ts, exch_ts, trade_ts,

                # Price & trade
                t.get("ltp"),
                t.get("last_traded_qty"),
                t.get("avg_trade_price"),

                # Volume — BUY / SELL (core CVD data)
                t.get("tot_buy_qty"),
                t.get("tot_sell_qty"),
                t.get("vol_traded_today"),

                # Bid / Ask
                t.get("bid_price"),
                t.get("bid_size"),
                t.get("ask_price"),
                t.get("ask_size"),

                # OHLC
                t.get("open_price"),
                t.get("high_price"),
                t.get("low_price"),
                t.get("prev_close_price"),

                # Change
                t.get("ch"),
                t.get("chp"),

                # Open interest (futures)
                extract_oi(t),
                t.get("oi_day_high"),
                t.get("oi_day_low"),

                # Circuit & 52-week (equities)
                t.get("upper_circuit_limit") or t.get("upper_circuit"),
                t.get("lower_circuit_limit") or t.get("lower_circuit"),
                t.get("week_52_high") or t.get("52w_high"),
                t.get("week_52_low")  or t.get("52w_low"),

                # Full raw tick
                json.dumps(t),
            ))

            tick_count += 1

        # ── Commit logic: time-based OR count-based ───────────────────────────
        now = time.time()
        do_commit = (
            tick_count % COMMIT_EVERY_N_TICKS == 0
            or (now - last_commit_time) >= COMMIT_INTERVAL_SEC
        )
        if do_commit:
            for c in dbs.values():
                c.commit()
            last_commit_time = now
            ts = datetime.now().strftime("%H:%M:%S")
            last_sym = ticks[-1].get("symbol", "?").split(":")[1] if ticks else "?"
            last_ltp = ticks[-1].get("ltp", "?") if ticks else "?"
            print(f"  {ts}  ticks={tick_count:>8,}  "
                  f"last={last_sym}  ltp={last_ltp}")

    except Exception as e:
        print(f"  Tick error: {e}  |  raw={str(msg)[:120]}")


def on_error(msg):
    print(f"  WS Error: {msg}")


def on_close(msg):
    print(f"\n  WS Close: {msg}")
    print("  Final commit …")
    for c in dbs.values():
        try:
            c.commit()
            c.close()
        except Exception as e:
            print(f"  Close error: {e}")
    print(f"\n  ✓ Session complete")
    print(f"  Data folder : {DATA_DIR}")
    print(f"  Total ticks : {tick_count:,}")
    print(f"  Symbols     : {', '.join(SYMBOLS)}")


fyers_ws = None


def on_open():
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"\n  WS Connected at {ts}")
    fyers_ws.subscribe(symbols=SYMBOLS, data_type="SymbolUpdate")
    print(f"  Subscribed: {SYMBOLS}")
    print(f"  Recording to: {DATA_DIR}\n")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print(f"\nQT v2.0  started  {TODAY_STR}  {TODAY_DT.strftime('%H:%M:%S')}")

    wait_for_market()

    token = get_token()
    if not token:
        print("Authentication failed. Exiting.")
        exit(1)

    fyers_ws = data_ws.FyersDataSocket(
        access_token  = token,
        log_path      = "",
        litemode      = False,        # Full mode — all fields
        write_to_file = False,
        reconnect     = True,
        on_connect    = on_open,
        on_close      = on_close,
        on_error      = on_error,
        on_message    = on_tick,
    )

    fyers_ws.connect()
    fyers_ws.keep_running()
