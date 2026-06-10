---
type: temp-skill
name: kaggle-dual-monitor
version: 2
use_count: 4
created: 2026-06-09
last_used: 2026-06-10
description: Monitors two Kaggle kernels simultaneously in a single background loop. Reports COMPLETE or ERROR for each independently without blocking.
tags: [temp-skill, kaggle, monitoring]
---

# Kaggle Dual Kernel Monitor

## Purpose

When two Kaggle notebooks are pushed simultaneously, monitor both in a single background script without needing two separate pulse-checker invocations.

## Pattern Used (Production-Validated)

This pattern was used successfully in the pairs trading pipeline when running the Kalman pipeline and the OLS pipeline concurrently.

## Template Script

```python
import time, subprocess

def check_status(kernel_id):
    cmd = f"kaggle kernels status {kernel_id}"
    try:
        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode('utf-8').strip()
        if "error" in out.lower():   return "ERROR"
        if "complete" in out.lower(): return "COMPLETE"
        if "running" in out.lower() or "queued" in out.lower(): return "RUNNING"
        return "UNKNOWN"
    except Exception:
        return "NETWORK_ERR"

k1 = "utkarshpatelthefirst/<kernel-slug-1>"
k2 = "utkarshpatelthefirst/<kernel-slug-2>"
k1_done = False
k2_done = False

print("Monitoring Dual Kaggle Kernels...")
t0 = time.time()

while not (k1_done and k2_done):
    if not k1_done:
        st1 = check_status(k1)
        if st1 in ["COMPLETE", "ERROR"]:
            print(f"\n[{int(time.time()-t0)}s] {k1} -> {st1}")
            k1_done = True

    if not k2_done:
        st2 = check_status(k2)
        if st2 in ["COMPLETE", "ERROR"]:
            print(f"\n[{int(time.time()-t0)}s] {k2} -> {st2}")
            k2_done = True

    if not (k1_done and k2_done):
        print(".", end="", flush=True)
        time.sleep(60)

print("\n\nBoth kernels finished!")
```

## Usage

1. Save this as `monitor_dual.py` in the Code directory
2. Fill in the two kernel slugs (from push output URLs)
3. Run as background task:
```bash
export $(cat ~/.quant_env | xargs) && python monitor_dual.py
```

## Notes

- `NETWORK_ERR` is treated as "keep waiting" — never escalates to ERROR
- Phase 2 check interval is 60s (suitable for long-running kernels)
- For single kernel monitoring, use `monitor_stage1b.py` pattern (same logic, one kernel)
- For production-grade error handling and log fetching on crash, use the full `kaggle-pulse-check` skill

## Connections

- [[kaggle-pulse-check]]
- [[kaggle-notebook-run]]
- [[pairs-trading-pipeline]]
