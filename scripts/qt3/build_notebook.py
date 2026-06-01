"""
build_notebook.py — Generates cloud_tick_collector.ipynb
Run locally: python build_notebook.py
"""
import json, os

NOTEBOOK_PATH = os.path.join(os.path.dirname(__file__), "cloud_tick_collector.ipynb")

# ─── Cell helpers ─────────────────────────────────────────────────────────────

def md(text):
    return {"cell_type": "markdown", "metadata": {},
            "source": text.strip().splitlines(keepends=True)}

def code(text):
    return {"cell_type": "code", "execution_count": None,
            "metadata": {}, "outputs": [],
            "source": text.strip().splitlines(keepends=True)}

# ─── Notebook cells ───────────────────────────────────────────────────────────

cells = []

# ── Cell 0 — Title ────────────────────────────────────────────────────────────
cells.append(md("""
# Cloud Tick Collector v1.0 — NSE Futures Tick + Depth Data
**Symbols:** Nifty 50 Futures + Bank Nifty Futures (front-month, auto-rolling)  
**Feeds:** SymbolUpdate (ticks, OI) + DepthUpdate (20-level order book)  
**Storage:** SQLite WAL — `NIFTY_FUT.db` + `BANKNIFTY_FUT.db`  
**Day logic:** 2 states only — `fyers.market_status()` decides. No calendar. No holiday list.
"""))

# ── Cell 1 — Install ──────────────────────────────────────────────────────────
cells.append(md("""
## Stage 1 — Install Dependencies
**Methodology:** Install fyers-apiv3 and pyotp (not in default Kaggle image).  
**Input:** None  
**Output:** Packages available for import  
**Core Logic:** pip install, then verify import.  
**Formula/Equation:** $$ \\text{No formula — package installation} $$
"""))

cells.append(code("""
import subprocess, sys

pkgs = ["fyers-apiv3", "pyotp"]
for pkg in pkgs:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", pkg])

print("✅ Dependencies installed")
"""))

# ── Cell 2 — Imports & Credentials ───────────────────────────────────────────
cells.append(md("""
## Stage 2 — Imports & Credentials
**Methodology:** Load all libraries and hardcode Fyers credentials (Kaggle-standard approach per skill rules).  
**Input:** Hardcoded credential strings  
**Output:** CREDS dict, all modules imported  
**Core Logic:** Import, define constants.  
**Formula/Equation:** $$ \\text{No formula — configuration} $$
"""))

cells.append(code("""
import json, os, sqlite3, struct, sys, threading, time
import calendar, logging
from datetime import datetime, timedelta, date
from urllib.parse import parse_qs, urlparse

import requests
import pyotp
from fyers_apiv3 import fyersModel
from fyers_apiv3.FyersWebsocket import data_ws

# ── Credentials (hardcoded — Kaggle standard per skill) ───────────────────────
CREDS = {
    "app_id":   "G0NX5M08ZG-100",
    "secret":   "D07VJ80FLH",
    "totp_key": "4QXQQACGALLZNFISHC5G7WU76AERBNYC",
    "username": "FAI84454",
    "pin":      "7475",
}
KAGGLE_USERNAME = "utkarshpatelthefirst"
KAGGLE_KEY      = "fbef16329099428205f671dd5de8337b"
REDIRECT_URI    = "https://trade.fyers.in/api-login/redirect-uri/index.html"

# ── Paths & dataset ───────────────────────────────────────────────────────────
WORKING_DIR       = "/kaggle/working"
KAGGLE_DATASET_ID = f"{KAGGLE_USERNAME}/nse-futures-tick-data"

DB_PATHS = {
    "nifty":     os.path.join(WORKING_DIR, "NIFTY_FUT.db"),
    "banknifty": os.path.join(WORKING_DIR, "BANKNIFTY_FUT.db"),
}

# ── Timing (IST = UTC+5:30) ───────────────────────────────────────────────────
IST_OFFSET     = timedelta(hours=5, minutes=30)
MARKET_CHECK   = (9,  5)    # HH, MM IST — call market_status()
SUBSCRIBE_AT   = (9, 12)    # HH, MM IST — connect sockets
SESSION_END    = (15, 31)   # HH, MM IST — close + publish

# ── Commit strategy ───────────────────────────────────────────────────────────
TICK_BUF_ROWS  = 500
TICK_BUF_SECS  = 30
DEPTH_BUF_ROWS = 1000
DEPTH_BUF_SECS = 30

print("✅ Imports and config ready")
"""))

# ── Cell 3 — Time Helpers ─────────────────────────────────────────────────────
cells.append(md("""
## Stage 3 — IST Time Utilities
**Methodology:** All session timing is based on IST (UTC+5:30). Helper functions compute waiting times and IST-aware datetimes.  
**Input:** UTC system clock  
**Output:** IST-corrected datetimes and wait durations  
**Core Logic:** Add 5h30m offset to UTC.  
**Formula/Equation:** $$ t_{IST} = t_{UTC} + 5\\text{h}30\\text{m} $$
"""))

cells.append(code("""
def now_ist() -> datetime:
    return datetime.utcnow() + IST_OFFSET

def seconds_until_ist(h: int, m: int) -> float:
    \"\"\"Seconds from now until HH:MM IST today (0 if already past).\"\"\"
    target = now_ist().replace(hour=h, minute=m, second=0, microsecond=0)
    delta  = (target - now_ist()).total_seconds()
    return max(delta, 0.0)

print(f"Current IST: {now_ist().strftime('%Y-%m-%d %H:%M:%S')}")
SESSION_DATE = now_ist().strftime("%Y-%m-%d")
print(f"Session date: {SESSION_DATE}")
"""))

# ── Cell 4 — Expiry Resolver ──────────────────────────────────────────────────
cells.append(md("""
## Stage 4 — Front-Month Symbol Resolver
**Methodology:** NSE futures expire on the last Thursday of each month. If today >= expiry, roll to next month.  
**Input:** Today's IST date  
**Output:** Active Nifty + BankNifty futures symbol strings  
**Core Logic:** Find last Thursday → compare with today → select month → format symbol.  
**Formula/Equation:** $$ \\text{expiry} = \\max\\{d \\in \\text{month} : d.weekday() = \\text{Thursday}\\} $$
"""))

cells.append(code("""
def _last_thursday(year: int, month: int) -> date:
    \"\"\"Last Thursday of the given month — NSE futures expiry date.\"\"\"
    last_day = calendar.monthrange(year, month)[1]
    d = date(year, month, last_day)
    offset = (d.weekday() - 3) % 7   # Thursday = weekday 3
    return d - timedelta(days=offset)

def resolve_symbols() -> dict:
    \"\"\"
    Returns active front-month Nifty and BankNifty symbol strings.
    Rolls to next month if today >= last Thursday of current month.
    \"\"\"
    today = now_ist()
    y, m  = today.year, today.month
    expiry = _last_thursday(y, m)
    if today.date() >= expiry:      # expiry day or past → use next month
        m = m % 12 + 1
        if m == 1:
            y += 1
    mon = datetime(y, m, 1).strftime("%b").upper()   # e.g. JUN, JUL
    yy  = str(y)[2:]                                  # e.g. '26'
    return {
        "nifty":     f"NSE:NIFTY{yy}{mon}FUT",
        "banknifty": f"NSE:BANKNIFTY{yy}{mon}FUT",
    }

resolved = resolve_symbols()
print(f"Active symbols:")
for k, v in resolved.items():
    print(f"  {k:>9} → {v}")
"""))

# ── Cell 5 — Authentication ───────────────────────────────────────────────────
cells.append(md("""
## Stage 5 — Fyers Authentication (5-Step TOTP)
**Methodology:** Automated TOTP-based login. No browser required.  
**Input:** CREDS dict (app_id, secret, totp_key, username, pin)  
**Output:** `full_token` string ('APP_ID:access_token') and `fyers` client object  
**Core Logic:** send_login_otp → verify_otp (TOTP) → verify_pin → get auth_code → exchange for token.  
**Formula/Equation:** $$ \\text{token} = \\text{session.generate\\_token}(\\text{auth\\_code}) $$
"""))

cells.append(code("""
def get_token(max_retries: int = 3) -> str:
    \"\"\"Run 5-step TOTP auth. Returns 'APP_ID:access_token' or raises on failure.\"\"\"
    for attempt in range(1, max_retries + 1):
        print(f"  Auth attempt {attempt}/{max_retries}")
        try:
            totp = pyotp.TOTP(CREDS["totp_key"]).now()

            # Step 1 — Send login OTP
            r1 = requests.post(
                "https://api-t2.fyers.in/vagator/v2/send_login_otp",
                json={"fy_id": CREDS["username"], "app_id": "2"}, timeout=15)
            r1.raise_for_status()
            if r1.json().get("s") != "ok":
                raise RuntimeError(f"Step 1 failed: {r1.json()}")
            rk = r1.json()["request_key"]
            print(f"    Step 1 ✓  request_key={rk[:12]}…")

            # Step 2 — Verify TOTP
            r2 = requests.post(
                "https://api-t2.fyers.in/vagator/v2/verify_otp",
                json={"request_key": rk, "otp": totp}, timeout=15)
            r2.raise_for_status()
            if r2.json().get("s") != "ok":
                raise RuntimeError(f"Step 2 failed: {r2.json()}")
            rk = r2.json()["request_key"]
            print("    Step 2 ✓  TOTP verified")

            # Step 3 — Verify PIN
            r3 = requests.post(
                "https://api-t2.fyers.in/vagator/v2/verify_pin",
                json={"request_key": rk,
                      "identity_type": "pin",
                      "identifier": str(CREDS["pin"])}, timeout=15)
            r3.raise_for_status()
            if r3.json().get("s") != "ok":
                raise RuntimeError(f"Step 3 failed: {r3.json()}")
            temp_token = r3.json()["data"]["access_token"]
            print("    Step 3 ✓  PIN verified")

            # Step 4 — Get auth code
            r4 = requests.post(
                "https://api-t1.fyers.in/api/v3/token",
                headers={"Authorization": f"Bearer {temp_token}"},
                json={"fyers_id": CREDS["username"],
                      "app_id":   CREDS["app_id"].split("-")[0],
                      "redirect_uri": REDIRECT_URI,
                      "appType": "100", "code_challenge": "",
                      "state": "x", "scope": "", "nonce": "",
                      "response_type": "code", "create_cookie": True},
                timeout=15)
            r4.raise_for_status()
            url = r4.json().get("Url", "")
            if "auth_code=" not in url:
                raise RuntimeError(f"Step 4: auth_code missing — {r4.json()}")
            auth_code = parse_qs(urlparse(url).query)["auth_code"][0]
            print("    Step 4 ✓  Auth code obtained")

            # Step 5 — Exchange for access token
            sess = fyersModel.SessionModel(
                client_id=CREDS["app_id"], secret_key=CREDS["secret"],
                redirect_uri=REDIRECT_URI, response_type="code",
                grant_type="authorization_code")
            sess.set_token(auth_code)
            resp = sess.generate_token()
            if not resp.get("access_token"):
                raise RuntimeError(f"Step 5 failed: {resp}")
            print("    Step 5 ✓  Access token received")

            full_token = f"{CREDS['app_id']}:{resp['access_token']}"
            print(f"\\n✅ Authentication successful")
            return full_token

        except Exception as e:
            print(f"  ✗ Attempt {attempt} error: {e}")
            if attempt < max_retries:
                print(f"  Retrying in 60s …")
                time.sleep(60)

    raise RuntimeError("Authentication failed after all retries")

# Run auth immediately
full_token = get_token()
fyers_client = fyersModel.FyersModel(
    client_id=CREDS["app_id"], token=full_token.split(":")[1],
    is_async=False, log_path="")
print(f"  Fyers client ready")
"""))

# ── Cell 6 — Market Status Check ─────────────────────────────────────────────
cells.append(md("""
## Stage 6 — Market Status Check (2-State Logic)
**Methodology:** Query Fyers market status API. NSE Derivative == 'OPEN' → trading day. Anything else → exit.  
**Input:** Authenticated `fyers_client`  
**Output:** Boolean `is_trading` — halts notebook if False  
**Core Logic:** Single API call → check NSE Derivative segment status.  
**Formula/Equation:** $$ \\text{trading} = [\\text{NSE Derivative.status} = \\texttt{OPEN}] $$
"""))

cells.append(code("""
def check_trading_day(client, max_retries: int = 3) -> bool:
    \"\"\"
    Returns True only if NSE Derivative segment is OPEN.
    No calendar. No holiday list. API is the single source of truth.
    \"\"\"
    for attempt in range(1, max_retries + 1):
        try:
            resp = client.market_status()
            print(f"  market_status() raw: {json.dumps(resp, indent=2)[:300]}")
            for seg in resp.get("marketStatus", []):
                if (seg.get("exchange") == "NSE"
                        and seg.get("segment") == "Derivative"):
                    status = seg.get("status")
                    return status == "OPEN"
            print("  NSE Derivative segment not found in response")
            return False
        except Exception as e:
            print(f"  market_status() attempt {attempt} error: {e}")
            if attempt < max_retries:
                time.sleep(60)
    return False

# Wait until market check time if needed
wait = seconds_until_ist(*MARKET_CHECK)
if wait > 0:
    print(f"Waiting {wait:.0f}s until {MARKET_CHECK[0]:02d}:{MARKET_CHECK[1]:02d} IST …")
    time.sleep(wait)

is_trading = check_trading_day(fyers_client)
print(f"\\nIs trading day: {is_trading}")

if not is_trading:
    print("\\n⛔ Non-trading day detected — exiting cleanly.")
    raise SystemExit(0)

print("✅ Trading day confirmed — proceeding with data collection")
"""))

# ── Cell 7 — Prev Close from REST ────────────────────────────────────────────
cells.append(md("""
## Stage 7 — Fetch prev_close from REST Quotes API
**Methodology:** One REST call at session start to get yesterday's close for session_meta. Not stored per tick.  
**Input:** Resolved symbol strings, authenticated client  
**Output:** `prev_closes` dict {key: float}  
**Core Logic:** `fyers.quotes()` → extract `prev_close_price`.  
**Formula/Equation:** $$ \\text{No formula — REST API call} $$
"""))

cells.append(code("""
sym_list   = list(resolved.values())
sym_to_key = {v: k for k, v in resolved.items()}

prev_closes = {}
try:
    resp = fyers_client.quotes({"symbols": ",".join(sym_list)})
    for q in resp.get("d", []):
        v = q.get("v", {})
        fsym = v.get("symbol", "")
        pc   = (v.get("prev_close_price")
             or v.get("prevClosePrice")
             or v.get("close_price"))
        key  = sym_to_key.get(fsym)
        if key and pc:
            prev_closes[key] = float(pc)
            print(f"  {key:>9} prev_close = {pc}")
except Exception as e:
    print(f"  Quotes API failed: {e} — prev_close will be NULL in session_meta")

print(f"\\n✅ prev_close fetched: {prev_closes}")
"""))

# ── Cell 8 — Database Setup ───────────────────────────────────────────────────
cells.append(md("""
## Stage 8 — Database Setup (SQLite WAL)
**Methodology:** Open one SQLite file per symbol. Apply WAL PRAGMAs. Create schema if not exists (appends on repeated runs).  
**Input:** DB_PATHS dict  
**Output:** `connections` dict, `db_locks` dict, all tables verified  
**Core Logic:** PRAGMA WAL → CREATE TABLE IF NOT EXISTS → CREATE INDEX.  
**Formula/Equation:** $$ \\text{No formula — DDL setup} $$
"""))

cells.append(code("""
# ── Schema SQL ─────────────────────────────────────────────────────────────────
DDL_TICKS = \"\"\"
CREATE TABLE IF NOT EXISTS ticks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    recv_ts      INTEGER NOT NULL,
    exch_ts      INTEGER NOT NULL,
    trade_ts     INTEGER NOT NULL,
    ltp          REAL    NOT NULL,
    ltq          INTEGER NOT NULL,
    tot_buy_qty  INTEGER NOT NULL,
    tot_sell_qty INTEGER NOT NULL,
    oi           REAL,
    raw_json     TEXT    NOT NULL
);
\"\"\"

DDL_DEPTH = \"\"\"
CREATE TABLE IF NOT EXISTS depth (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    recv_ts  INTEGER NOT NULL,
    bids     BLOB    NOT NULL,
    asks     BLOB    NOT NULL
);
\"\"\"

DDL_META = \"\"\"
CREATE TABLE IF NOT EXISTS session_meta (
    session_date      TEXT PRIMARY KEY,
    symbol            TEXT NOT NULL,
    prev_close        REAL,
    open_price        REAL,
    session_start_ts  INTEGER,
    session_end_ts    INTEGER,
    tick_count        INTEGER,
    depth_count       INTEGER,
    status            TEXT
);
\"\"\"

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_ticks_exch ON ticks(exch_ts);",
    "CREATE INDEX IF NOT EXISTS idx_ticks_recv ON ticks(recv_ts);",
    "CREATE INDEX IF NOT EXISTS idx_depth_recv ON depth(recv_ts);",
]

PRAGMAS = [
    "PRAGMA journal_mode = WAL;",
    "PRAGMA synchronous  = NORMAL;",
    "PRAGMA cache_size   = -32000;",
    "PRAGMA mmap_size    = 134217728;",
]

def setup_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    for p in PRAGMAS:  conn.execute(p)
    conn.execute(DDL_TICKS)
    conn.execute(DDL_DEPTH)
    conn.execute(DDL_META)
    for idx in INDEXES: conn.execute(idx)
    conn.commit()
    return conn

# ── Insert SQL ─────────────────────────────────────────────────────────────────
INS_TICK = \"\"\"
INSERT INTO ticks
  (recv_ts, exch_ts, trade_ts, ltp, ltq, tot_buy_qty, tot_sell_qty, oi, raw_json)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
\"\"\"

INS_DEPTH = "INSERT INTO depth (recv_ts, bids, asks) VALUES (?, ?, ?)"

INS_META  = \"\"\"
INSERT OR REPLACE INTO session_meta
  (session_date, symbol, prev_close, open_price,
   session_start_ts, session_end_ts, tick_count, depth_count, status)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
\"\"\"

# ── Open connections ───────────────────────────────────────────────────────────
connections   = {}
db_locks      = {}
tick_bufs     = {}
depth_bufs    = {}
last_commit_t = {}
session_info  = {}
start_ts      = int(time.time() * 1000)

for key, path in DB_PATHS.items():
    connections[key]   = setup_db(path)
    db_locks[key]      = threading.Lock()
    tick_bufs[key]     = []
    depth_bufs[key]    = []
    last_commit_t[f"tick_{key}"]  = time.time()
    last_commit_t[f"depth_{key}"] = time.time()
    session_info[key]  = {
        "prev_close": prev_closes.get(key),
        "open_price": None,
        "start_ts":   start_ts,
    }
    sz = os.path.getsize(path) / 1024**2 if os.path.exists(path) else 0
    print(f"  {key:>9}.db  ready  ({sz:.2f} MB existing data)")

print("\\n✅ Databases ready (WAL mode)")
"""))

# ── Cell 9 — BLOB Depth Packing ───────────────────────────────────────────────
cells.append(md("""
## Stage 9 — BLOB Depth Packing
**Methodology:** Pack 20 order book levels per side into fixed 280-byte binary BLOBs. Saves ~40% vs JSON.  
**Input:** List of {price, quantity, orders} dicts from Fyers DepthUpdate  
**Output:** 280-byte `bytes` object per side  
**Core Logic:** `struct.pack_into('<dih', ...)` — little-endian f64 price, i32 qty, i16 orders.  
**Formula/Equation:** $$ \\text{size} = 20 \\times (8 + 4 + 2) = 280 \\text{ bytes/side} $$
"""))

cells.append(code("""
LEVEL_FMT  = '<dih'                        # little-endian: f64, i32, i16
LEVEL_SIZE = struct.calcsize(LEVEL_FMT)    # = 14 bytes
N_LEVELS   = 20                            # 20 levels per side

def pack_side(levels: list) -> bytes:
    \"\"\"
    Pack up to 20 order book levels into 280-byte BLOB.
    Missing levels are zero-padded.
    Unpack: struct.unpack_from('<dih', blob, i*14) for i in range(20)
    \"\"\"
    buf = bytearray(N_LEVELS * LEVEL_SIZE)
    for i, lvl in enumerate(levels[:N_LEVELS]):
        struct.pack_into(LEVEL_FMT, buf, i * LEVEL_SIZE,
                         float(lvl.get("price",    0.0)),
                         int(  lvl.get("quantity", 0)),
                         int(  lvl.get("orders",   0)))
    return bytes(buf)

# Self-test
_test = [{"price": 24500.25, "quantity": 150, "orders": 3}]
_blob = pack_side(_test)
_p, _q, _o = struct.unpack_from(LEVEL_FMT, _blob, 0)
assert abs(_p - 24500.25) < 0.001 and _q == 150 and _o == 3
print(f"✅ BLOB pack/unpack verified — {N_LEVELS} levels × {LEVEL_SIZE} bytes = {N_LEVELS*LEVEL_SIZE} bytes/side")
"""))

# ── Cell 10 — Shared state & counters ─────────────────────────────────────────
cells.append(md("""
## Stage 10 — Shared State & Counters
**Methodology:** Global thread-safe counters and a shutdown Event used by all threads.  
**Input:** None  
**Output:** Global mutable state for tick/depth handlers and timer thread  
**Core Logic:** `threading.Event` for clean shutdown signalling.  
**Formula/Equation:** $$ \\text{No formula — concurrency primitives} $$
"""))

cells.append(code("""
tick_total  = 0
depth_total = 0
shutdown_ev = threading.Event()

# Mutable references to socket objects (set during Stage 12)
ws_a_ref = [None]
ws_b_ref = [None]

print("✅ Shared state initialised")
"""))

# ── Cell 11 — Tick Handler (Socket A) ────────────────────────────────────────
cells.append(md("""
## Stage 11 — Tick Handler (SymbolUpdate Callback)
**Methodology:** Called by Socket A on every tick. Extracts independent fields only. Buffers rows for batch commit.  
**Input:** Raw dict from Fyers SymbolUpdate  
**Output:** Row appended to `tick_bufs[key]`. Flush when buffer full or time elapsed.  
**Core Logic:** Extract 7 independent fields + raw_json. Capture open_price once per session.  
**Formula/Equation:** $$ \\text{recv\\_ts} = \\lfloor t_{\\text{wall}} \\times 1000 \\rfloor \\text{ ms} $$
"""))

cells.append(code("""
def _flush_ticks(key: str):
    buf = tick_bufs[key]
    if not buf:
        return
    rows = list(buf)
    buf.clear()
    with db_locks[key]:
        try:
            connections[key].executemany(INS_TICK, rows)
            connections[key].commit()
            last_commit_t[f"tick_{key}"] = time.time()
            ts_str = now_ist().strftime("%H:%M:%S")
            print(f"  [{ts_str} IST] {key:>9} ticks_total={tick_total:>10,}  "
                  f"flushed={len(rows)}", flush=True)
        except Exception as e:
            print(f"  [DB-TICK-ERR] {key}: {e}", flush=True)


def on_tick(msg):
    global tick_total
    try:
        items = msg if isinstance(msg, list) else [msg]
        now_ms = int(time.time() * 1000)

        for t in items:
            sym = t.get("symbol", "")
            key = sym_to_key.get(sym)
            if key is None:
                continue

            # ── 3 independent timestamps ──────────────────────────────────
            recv_ts  = now_ms
            exch_ts  = int(t.get("exch_feed_time",  0) or 0) * 1000
            trade_ts = int(t.get("last_traded_time", 0) or 0) * 1000

            # ── Atomic trade event ────────────────────────────────────────
            ltp = t.get("ltp")
            if ltp is None:
                continue                    # skip non-price messages
            ltq = int(t.get("last_traded_qty") or t.get("ltq") or 0)

            # ── Exchange-classified order flow ────────────────────────────
            tot_buy  = int(t.get("tot_buy_qty",  0) or 0)
            tot_sell = int(t.get("tot_sell_qty", 0) or 0)

            # ── Open interest (futures) ───────────────────────────────────
            oi = (t.get("open_interest")
               or t.get("oi")
               or t.get("OI")
               or t.get("openInterest"))

            # ── Capture open_price once (first tick of session) ──────────
            if session_info[key]["open_price"] is None:
                session_info[key]["open_price"] = float(ltp)

            row = (recv_ts, exch_ts, trade_ts,
                   float(ltp), ltq,
                   tot_buy, tot_sell,
                   float(oi) if oi is not None else None,
                   json.dumps(t, separators=(",", ":")))

            tick_bufs[key].append(row)
            tick_total += 1

            # ── Flush condition ───────────────────────────────────────────
            if (len(tick_bufs[key]) >= TICK_BUF_ROWS
                    or time.time() - last_commit_t[f"tick_{key}"] >= TICK_BUF_SECS):
                _flush_ticks(key)

    except Exception as e:
        print(f"  [ON_TICK ERR] {e}", flush=True)


def on_open_a():
    ws_a = ws_a_ref[0]
    ts   = now_ist().strftime("%H:%M:%S")
    print(f"  [{ts} IST] Socket A (SymbolUpdate) connected", flush=True)
    ws_a.subscribe(symbols=sym_list, data_type="SymbolUpdate")
    print(f"  Subscribed SymbolUpdate: {sym_list}", flush=True)


def on_error_a(msg):
    print(f"  [WS-A ERR] {msg}", flush=True)


def on_close_a(msg):
    ts = now_ist().strftime("%H:%M:%S")
    print(f"  [{ts} IST] Socket A closed: {msg}", flush=True)


print("✅ Tick handlers defined")
"""))

# ── Cell 12 — Depth Handler (Socket B) ───────────────────────────────────────
cells.append(md("""
## Stage 12 — Depth Handler (DepthUpdate Callback)
**Methodology:** Called by Socket B on every order book change. Packs 20+20 levels into BLOBs. Buffers for batch commit.  
**Input:** Raw dict from Fyers DepthUpdate  
**Output:** Row appended to `depth_bufs[key]`. Flush when buffer full or time elapsed.  
**Core Logic:** pack_side(bids) + pack_side(asks) → BLOB row → buffer → SQLite.  
**Formula/Equation:** $$ \\text{row size} = 280 + 280 + 8 = 568 \\text{ bytes (bids + asks + ts)} $$
"""))

cells.append(code("""
def _flush_depth(key: str):
    buf = depth_bufs[key]
    if not buf:
        return
    rows = list(buf)
    buf.clear()
    with db_locks[key]:
        try:
            connections[key].executemany(INS_DEPTH, rows)
            connections[key].commit()
            last_commit_t[f"depth_{key}"] = time.time()
        except Exception as e:
            print(f"  [DB-DEPTH-ERR] {key}: {e}", flush=True)


def on_depth(msg):
    global depth_total
    try:
        items = msg if isinstance(msg, list) else [msg]
        now_ms = int(time.time() * 1000)

        for d in items:
            sym = d.get("symbol", "")
            key = sym_to_key.get(sym)
            if key is None:
                continue

            bids_blob = pack_side(d.get("bids", []) or [])
            asks_blob = pack_side(d.get("asks", []) or [])

            depth_bufs[key].append((now_ms, bids_blob, asks_blob))
            depth_total += 1

            if (len(depth_bufs[key]) >= DEPTH_BUF_ROWS
                    or time.time() - last_commit_t[f"depth_{key}"] >= DEPTH_BUF_SECS):
                _flush_depth(key)

    except Exception as e:
        print(f"  [ON_DEPTH ERR] {e}", flush=True)


def on_open_b():
    ws_b = ws_b_ref[0]
    ts   = now_ist().strftime("%H:%M:%S")
    print(f"  [{ts} IST] Socket B (DepthUpdate) connected", flush=True)
    ws_b.subscribe(symbols=sym_list, data_type="DepthUpdate")
    print(f"  Subscribed DepthUpdate: {sym_list}", flush=True)


def on_error_b(msg):
    print(f"  [WS-B ERR] {msg}", flush=True)


def on_close_b(msg):
    ts = now_ist().strftime("%H:%M:%S")
    print(f"  [{ts} IST] Socket B closed: {msg}", flush=True)


print("✅ Depth handlers defined")
"""))

# ── Cell 13 — Session Timer ───────────────────────────────────────────────────
cells.append(md("""
## Stage 13 — Session End Timer Thread
**Methodology:** Daemon thread sleeps until 15:31 IST then flushes all buffers, writes session_meta, and triggers publish.  
**Input:** SESSION_END tuple, socket references  
**Output:** All data committed, session_meta written, publish triggered  
**Core Logic:** `time.sleep(seconds_until_ist(15,31))` → final flush → session_meta → Kaggle publish.  
**Formula/Equation:** $$ \\text{wait} = t_{15:31\\text{ IST}} - t_{\\text{now}} $$
"""))

cells.append(code("""
def _write_session_meta(key: str, status: str):
    \"\"\"Write one session_meta row for this key.\"\"\"
    end_ts = int(time.time() * 1000)
    with db_locks[key]:
        try:
            tc = connections[key].execute("SELECT COUNT(*) FROM ticks").fetchone()[0]
            dc = connections[key].execute("SELECT COUNT(*) FROM depth").fetchone()[0]
            connections[key].execute(INS_META, (
                SESSION_DATE, resolved[key],
                session_info[key]["prev_close"],
                session_info[key]["open_price"],
                session_info[key]["start_ts"], end_ts,
                tc, dc, status))
            connections[key].commit()
            print(f"  session_meta [{key}]: ticks={tc:,}  depth={dc:,}  status={status}")
        except Exception as e:
            print(f"  [META ERR] {key}: {e}")


def session_timer():
    \"\"\"Fires at SESSION_END IST. Shuts down everything cleanly.\"\"\"
    wait = seconds_until_ist(*SESSION_END)
    h, m = SESSION_END
    print(f"  [TIMER] Session ends at {h:02d}:{m:02d} IST ({wait/3600:.2f}h from now)")
    time.sleep(wait)

    print(f"\\n{'='*55}")
    print(f"  [TIMER] Session end — {now_ist().strftime('%H:%M:%S IST')}")
    print(f"{'='*55}")
    shutdown_ev.set()

    # Close both sockets
    for name, ws_ref in [("A", ws_a_ref), ("B", ws_b_ref)]:
        ws = ws_ref[0]
        try:
            if ws:
                ws.close_connection()
                print(f"  Socket {name} closed")
        except Exception as e:
            print(f"  Socket {name} close error: {e}")

    # Final flush of all buffers
    for key in connections:
        _flush_ticks(key)
        _flush_depth(key)

    # Write session_meta
    for key in connections:
        _write_session_meta(key, "COMPLETE")

    # Print summary
    print(f"\\n  ── Collection Summary ──")
    print(f"  Ticks  collected : {tick_total:>10,}")
    print(f"  Depth  snapshots : {depth_total:>10,}")
    for key, path in DB_PATHS.items():
        sz = os.path.getsize(path) / 1024**2 if os.path.exists(path) else 0
        print(f"  {key:>9}.db : {sz:.2f} MB")

    # Close DB connections
    for key, conn in connections.items():
        try:
            conn.close()
        except Exception:
            pass

    # Publish to Kaggle
    publish_to_kaggle()


print("✅ Session timer defined")
"""))

# ── Cell 14 — Kaggle Publish ──────────────────────────────────────────────────
cells.append(md("""
## Stage 14 — Kaggle Dataset Publish
**Methodology:** After session close, publish both .db files as a new version of the Kaggle dataset. Creates dataset on first run.  
**Input:** DB files in /kaggle/working/, KAGGLE credentials  
**Output:** New dataset version at kaggle.com/datasets/utkarshpatelthefirst/nse-futures-tick-data  
**Core Logic:** Set env vars → init API → try create_version → fallback to create_new on first run.  
**Formula/Equation:** $$ \\text{No formula — API call} $$
"""))

cells.append(code("""
DATASET_META_CONTENT = {
    "title":    "NSE Futures Tick Data",
    "id":       KAGGLE_DATASET_ID,
    "licenses": [{"name": "Other (specified in description)"}],
}

def publish_to_kaggle():
    \"\"\"Write dataset-metadata.json and publish/version the Kaggle dataset.\"\"\"
    # Write metadata file into working dir
    meta_path = os.path.join(WORKING_DIR, "dataset-metadata.json")
    with open(meta_path, "w") as f:
        json.dump(DATASET_META_CONTENT, f, indent=2)

    # Set Kaggle credentials
    os.environ["KAGGLE_USERNAME"] = KAGGLE_USERNAME
    os.environ["KAGGLE_KEY"]      = KAGGLE_KEY

    print("\\n  [PUBLISH] Authenticating Kaggle API …")
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
        api = KaggleApi()
        api.authenticate()

        notes = (f"Tick session {SESSION_DATE} | "
                 f"ticks={tick_total:,} depth={depth_total:,} | "
                 f"symbols={list(resolved.values())}")
        try:
            api.dataset_create_version(
                folder=WORKING_DIR,
                version_notes=notes,
                quiet=False,
                convert_to_csv=False,
                delete_old_versions=False)
            print(f"  [PUBLISH] ✅ New version: "
                  f"https://www.kaggle.com/datasets/{KAGGLE_DATASET_ID}")
        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                print("  [PUBLISH] Dataset not found — creating for first time …")
                api.dataset_create_new(
                    folder=WORKING_DIR,
                    public=False,
                    quiet=False,
                    dir_mode="zip")
                print(f"  [PUBLISH] ✅ Dataset created: "
                      f"https://www.kaggle.com/datasets/{KAGGLE_DATASET_ID}")
            else:
                raise

    except Exception as e:
        print(f"  [PUBLISH] ✗ Error: {e}")
        print(f"  [PUBLISH]   DB files safe in {WORKING_DIR} as Kaggle Output")


print("✅ Publish function defined")
"""))

# ── Cell 15 — Launch Dual Sockets ─────────────────────────────────────────────
cells.append(md("""
## Stage 15 — Launch Dual WebSocket Collection
**Methodology:** Wait until 09:12 IST, then connect both sockets concurrently. Socket B (DepthUpdate) runs in a daemon thread. Socket A (SymbolUpdate) blocks the main thread. Session timer is a third daemon thread.  
**Input:** `full_token`, `sym_list`, all handlers defined above  
**Output:** Continuous data collection until 15:31 IST  
**Core Logic:** Thread(Socket B) + Thread(timer) + main → Socket A.keep_running()  
**Formula/Equation:** $$ \\text{No formula — concurrent I/O} $$
"""))

cells.append(code("""
# ── Wait until subscribe time ──────────────────────────────────────────────────
wait = seconds_until_ist(*SUBSCRIBE_AT)
if wait > 0:
    print(f"Waiting {wait:.0f}s until {SUBSCRIBE_AT[0]:02d}:{SUBSCRIBE_AT[1]:02d} IST "
          f"to connect sockets …")
    time.sleep(wait)

print(f"\\n{'='*55}")
print(f"  Connecting sockets at {now_ist().strftime('%H:%M:%S IST')}")
print(f"  Symbols: {sym_list}")
print(f"  Session ends at {SESSION_END[0]:02d}:{SESSION_END[1]:02d} IST")
print(f"{'='*55}\\n")

# ── Build Socket A (SymbolUpdate) ─────────────────────────────────────────────
ws_a = data_ws.FyersDataSocket(
    access_token=full_token,
    log_path="",
    litemode=False,
    write_to_file=False,
    reconnect=True,
    on_connect=on_open_a,
    on_close=on_close_a,
    on_error=on_error_a,
    on_message=on_tick,
)
ws_a_ref[0] = ws_a

# ── Build Socket B (DepthUpdate) ──────────────────────────────────────────────
ws_b = data_ws.FyersDataSocket(
    access_token=full_token,
    log_path="",
    litemode=False,
    write_to_file=False,
    reconnect=True,
    on_connect=on_open_b,
    on_close=on_close_b,
    on_error=on_error_b,
    on_message=on_depth,
)
ws_b_ref[0] = ws_b

# ── Start session timer daemon ────────────────────────────────────────────────
t_timer = threading.Thread(target=session_timer, daemon=True, name="SessionTimer")
t_timer.start()

# ── Start Socket B in daemon thread ───────────────────────────────────────────
def _run_socket_b():
    ws_b.connect()
    ws_b.keep_running()

t_depth = threading.Thread(target=_run_socket_b, daemon=True, name="DepthSocket")
t_depth.start()
time.sleep(1.5)     # small stagger so both don't auth simultaneously

# ── Socket A blocks main thread (until session_timer calls ws_a.close_connection) ──
print("  Starting SymbolUpdate feed (main thread — runs until 15:31 IST) …\\n")
ws_a.connect()
ws_a.keep_running()

# ── After keep_running() returns (socket closed by timer) ─────────────────────
print("\\n  Main socket loop exited. Waiting for timer thread to finish …")
t_timer.join(timeout=180)
print("\\n✅ Collection complete. Check Kaggle output for DB files.")
"""))

# ─── Build and write notebook ─────────────────────────────────────────────────

notebook = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.10.0"},
    },
    "cells": cells,
}

with open(NOTEBOOK_PATH, "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=1, ensure_ascii=False)

print(f"✅ Notebook written: {NOTEBOOK_PATH}")
print(f"   Cells: {len(cells)} ({sum(1 for c in cells if c['cell_type']=='code')} code + "
      f"{sum(1 for c in cells if c['cell_type']=='markdown')} markdown)")
