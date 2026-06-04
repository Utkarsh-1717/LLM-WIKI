---
name: kaggle-pulse-check
trigger: [monitor kaggle, check notebook status, kernel running, watch kaggle, is notebook done]
description: Actively monitors a running Kaggle kernel. Distinguishes true kernel failures from local network outages. Never fires ERROR unless Kaggle API confirms the kernel crashed.
version: 3.0.0
last_updated: 2026-06-03
---

# Kaggle Pulse Check Skill

## Purpose

After pushing any Kaggle kernel, the agent MUST immediately start monitoring it. This skill:
- Detects true kernel failures quickly
- **Never reports ERROR due to local internet loss** — only reports ERROR when Kaggle API explicitly confirms kernel crashed
- Notifies the user the moment the notebook completes or fails
- Survives indefinite connectivity gaps without breaking the loop

---

## ⚠️ CRITICAL: Always Extract the Real Slug from Push Output

Kaggle generates the kernel slug from the **title**, NOT the `id` in `kernel-metadata.json`.

The push output always contains the real URL:
```
Kernel version N successfully pushed. Please check progress at
https://www.kaggle.com/code/utkarshpatelthefirst/<REAL-SLUG-HERE>
```

Always parse this URL to extract the real slug before starting pulse-check.

```python
import re
push_output = """<paste full push stdout here>"""
match = re.search(r'kaggle\.com/code/([^/]+/[^\s]+)', push_output)
if not match:
    raise ValueError("Could not parse kernel slug — check push output manually")
KERNEL = match.group(1).strip()
print(f"Real kernel ref: {KERNEL}")
```

**Never hardcode the slug from kernel-metadata.json.**

---

## State Classification — The Critical Distinction

| What happened | What `check_status()` returns | Meaning |
|---|---|---|
| Kaggle API returned `complete` | `COMPLETE` | ✅ Kernel finished successfully |
| Kaggle API returned `error` | `KERNEL_ERROR` | ❌ Kernel actually crashed |
| API call worked but state unrecognised | `UNKNOWN` | ⚠️ API lag — keep polling |
| subprocess itself failed / timed out | `CONNECTIVITY_LOST` | 📵 Local network issue — keep polling |
| API returned `error` text AND subprocess OK | `KERNEL_ERROR` | ❌ Confirmed kernel crash |

> ⚠️ **Rule**: Only break the monitoring loop on `KERNEL_ERROR` confirmed **3 times in a row**.  
> Never break on `CONNECTIVITY_LOST` or `UNKNOWN` — those are local issues, not Kaggle kernel issues.

---

## Monitoring Protocol

### Phase 1 — High Frequency (first 5 minutes)
Check every 10 seconds. Catches fast failures (syntax errors, auth, missing paths).

### Phase 2 — Low Frequency (after 5 minutes)
Check every 120 seconds. Gentle — avoids hammering the API on long-running jobs.

> **Why 120s in phase 2?** Earlier versions used 60s. But on slow mobile connections,
> successive 60s API calls can overlap or time out and create false `CONNECTIVITY_LOST`
> bursts. 120s gives the connection time to recover between checks.

---

## Full Implementation Script

Run as a background task immediately after push (`WaitMsBeforeAsync=900000`).

```python
import time, subprocess, re

# ── STEP 1: Parse real slug ───────────────────────────────────────────────────
push_output = """<paste full push stdout here>"""
match = re.search(r'kaggle\.com/code/([^/]+/[^\s]+)', push_output)
if not match:
    raise ValueError("Could not parse kernel slug from push output")
KERNEL = match.group(1).strip()
print(f"🔍 Monitoring: {KERNEL}", flush=True)

# ── STEP 2: Status checker — NEVER raises exception ──────────────────────────
def check_status(kernel_ref):
    """
    Returns one of:
      COMPLETE          — kernel finished OK (Kaggle confirmed)
      KERNEL_ERROR      — kernel crashed    (Kaggle confirmed)
      QUEUED/RUNNING    — kernel in progress (Kaggle confirmed)
      UNKNOWN           — API responded but state not recognised
      CONNECTIVITY_LOST — subprocess failed (network issue on THIS device)
    """
    try:
        result = subprocess.run(
            ['bash', '-c',
             f'set -a && source ~/.quant_env && set +a && kaggle kernels status {kernel_ref}'],
            capture_output=True, text=True, timeout=30
        )
        out = (result.stdout + result.stderr).lower()

        # Map Kaggle API states — ordered most-specific first
        if 'complete'        in out: return 'COMPLETE'
        if 'running'         in out: return 'RUNNING'
        if 'queued'          in out: return 'QUEUED'
        if 'cancel'          in out: return 'CANCELLED'
        # Only return KERNEL_ERROR if Kaggle API explicitly says 'error'
        # AND the subprocess itself succeeded (returncode 0 means API was reached)
        if 'error' in out and result.returncode == 0:
            return 'KERNEL_ERROR'

        return f"UNKNOWN: {(result.stdout + result.stderr).strip()[:80]}"

    except subprocess.TimeoutExpired:
        return "CONNECTIVITY_LOST (timeout)"
    except Exception as e:
        return f"CONNECTIVITY_LOST ({type(e).__name__})"

# ── STEP 3: On-error log fetcher ─────────────────────────────────────────────
def fetch_error_log(kernel_ref):
    import json, os
    log_dir = "/storage/emulated/0/Quant/_kernel_logs"
    os.makedirs(log_dir, exist_ok=True)
    subprocess.run(
        ['bash', '-c',
         f'set -a && source ~/.quant_env && set +a && '
         f'kaggle kernels output {kernel_ref} -p {log_dir} --force'],
        capture_output=True, timeout=120
    )
    slug     = kernel_ref.split("/")[-1]
    log_path = f"{log_dir}/{slug}.log"
    if not os.path.exists(log_path):
        print("  Log file not found — check Kaggle web UI")
        return
    with open(log_path) as f:
        data = json.load(f)
    lines = [e['data'] for e in data if isinstance(e, dict) and 'data' in e]
    print("\n".join(''.join(lines).splitlines()[-80:]))

# ── STEP 4: Pulse loop ────────────────────────────────────────────────────────
start               = time.time()
last_status         = None
consecutive_errors  = 0          # KERNEL_ERROR must be confirmed this many times
CONFIRM_THRESHOLD   = 3          # avoids false positives from transient API glitches
FAST_SECS           = 300        # 5 minutes of fast checks
FAST_INT            = 10         # phase 1 interval
SLOW_INT            = 120        # phase 2 interval — gentler on mobile connections

while True:
    elapsed  = time.time() - start
    interval = FAST_INT if elapsed < FAST_SECS else SLOW_INT
    status   = check_status(KERNEL)

    if status != last_status:
        print(f"[{int(elapsed):>5}s] {status}", flush=True)
        last_status = status

    # ── Terminal state: SUCCESS ───────────────────────────────────────────────
    if status == 'COMPLETE':
        print(f"\n✅ Kernel COMPLETE after {int(elapsed)}s")
        print(f"   URL: https://www.kaggle.com/code/{KERNEL}")
        break

    # ── Terminal state: KERNEL CRASH — require 3 confirmations ───────────────
    if status == 'KERNEL_ERROR':
        consecutive_errors += 1
        print(f"   ⚠️  KERNEL_ERROR signal {consecutive_errors}/{CONFIRM_THRESHOLD}", flush=True)
        if consecutive_errors >= CONFIRM_THRESHOLD:
            print(f"\n❌ Kernel FAILED (confirmed {CONFIRM_THRESHOLD}x) after {int(elapsed)}s")
            print("   Fetching error logs...")
            fetch_error_log(KERNEL)
            break
        # Not yet confirmed — wait and re-check immediately
        time.sleep(15)
        continue
    else:
        # Any non-ERROR status resets the confirmation counter
        consecutive_errors = 0

    # ── Non-terminal states: keep polling ─────────────────────────────────────
    # CONNECTIVITY_LOST, UNKNOWN, RUNNING, QUEUED — all treated the same:
    # log if changed, sleep, retry. Never break the loop.
    time.sleep(interval)
```

---

## Key Rules (v3 — permanent)

1. **Always extract slug from push output URL** — never from `kernel-metadata.json`
2. **`check_status()` must never raise** — catch `TimeoutExpired` and all exceptions → return `CONNECTIVITY_LOST`
3. **`CONNECTIVITY_LOST` or `UNKNOWN` → continue polling.** Never break. Never report ERROR to user.
4. **`KERNEL_ERROR` requires 3 consecutive confirmations** before breaking loop and fetching logs
5. **Phase 2 interval = 120s** (not 60s) — more robust on slow/mobile connections
6. **Do NOT call `kaggle kernels output`** during `RUNNING` phase — it triggers large data download
7. **On `COMPLETE`** → report URL to user immediately; do NOT auto-download outputs unless requested

---

## Why These Rules Exist (Lessons Learned)

| Incident | Root Cause | Fix Applied |
|---|---|---|
| False ERROR on mobile connectivity loss | `subprocess.run()` raised exception → caught as `error` in output | `try/except` with `CONNECTIVITY_LOST` return |
| False ERROR from API lag after push | Single `error` in Kaggle API response during state transition | 3-confirmation threshold before treating as real crash |
| Pulse-checker reported wrong slug | Used `id` from `kernel-metadata.json` not push URL | Always parse real slug from push output URL |
| Missed completion on slow connections | 60s interval too fast → overlapping API calls on mobile | Phase 2 interval raised to 120s |

---

## Connections
- [[kaggle-notebook-run]]
- [[kaggle-db-update]]
