---
name: kaggle-pulse-check
trigger: [monitor kaggle, check notebook status, kernel running, watch kaggle, is notebook done]
description: Actively monitors a running Kaggle kernel every 10 seconds for the first 5 minutes, then every 60 seconds until completion or failure. Reports immediately on any state change.
version: 1.0.0
last_updated: 2026-05-26
---

# Kaggle Pulse Check Skill

## Purpose

After pushing any Kaggle kernel, the agent MUST immediately start monitoring it. This skill:
- Detects failures within seconds of occurrence
- Notifies the user the moment the notebook completes
- Avoids blind waiting or "should be done in ~20 mins" estimates

## When to Activate

Trigger this skill immediately after every `kaggle kernels push` command. Never wait passively.

## Monitoring Protocol

### Phase 1 — High Frequency (first 5 minutes)
Check every 10 seconds. Reason: most failures happen during environment setup (pip install, auth steps).

### Phase 2 — Low Frequency (after 5 minutes)
Check every 60 seconds until `COMPLETE` or `ERROR`.

## Implementation Script

Run this locally (it is lightweight — just API calls, no data transfer):

```python
import time, os, subprocess

def check_kernel_status(kernel_ref):
    """Returns: RUNNING, COMPLETE, ERROR, QUEUED, or CANCEL_REQUESTED"""
    result = subprocess.run(
        ['bash', '-c', f'set -a && source ~/.quant_env && set +a && kaggle kernels status {kernel_ref}'],
        capture_output=True, text=True
    )
    output = result.stdout + result.stderr
    if 'COMPLETE' in output:   return 'COMPLETE'
    if 'ERROR' in output:      return 'ERROR'
    if 'RUNNING' in output:    return 'RUNNING'
    if 'QUEUED' in output:     return 'QUEUED'
    return 'UNKNOWN'

def pulse_check(kernel_ref, fast_phase_seconds=300, fast_interval=10, slow_interval=60):
    """
    kernel_ref: e.g. 'utkarshpatelthefirst/master-data-1min'
    """
    print(f"🔍 Starting pulse check for: {kernel_ref}")
    start = time.time()
    last_status = None

    while True:
        elapsed = time.time() - start
        interval = fast_interval if elapsed < fast_phase_seconds else slow_interval

        status = check_kernel_status(kernel_ref)

        if status != last_status:
            print(f"[{int(elapsed):>4}s] Status changed: {last_status} → {status}")
            last_status = status

        if status == 'COMPLETE':
            print(f"✅ Kernel COMPLETE after {int(elapsed)}s")
            return 'COMPLETE'

        if status == 'ERROR':
            print(f"❌ Kernel FAILED after {int(elapsed)}s — fetching error logs...")
            # Fetch only the log file (not output data) to diagnose
            subprocess.run(['bash', '-c',
                f'mkdir -p /storage/emulated/0/Quant/_kernel_logs && '
                f'set -a && source ~/.quant_env && set +a && '
                f'kaggle kernels output {kernel_ref} -p /storage/emulated/0/Quant/_kernel_logs --force'
            ])
            return 'ERROR'

        time.sleep(interval)

# Usage:
# pulse_check('utkarshpatelthefirst/master-data-1min')
```

## Usage Rules

1. Always call after `kaggle kernels push`
2. Run as a background process so it does not block other work
3. On ERROR: automatically fetch logs and print the last stderr entry
4. On COMPLETE: report to user with the Kaggle notebook URL
5. Never call `kaggle kernels output` during the RUNNING phase — it may download output files locally
6. Log fetching (text-only log file) is safe: it is only a few KB

## On Failure: Auto-Diagnose

When ERROR is detected, run this parser to extract just the relevant error:

```python
import json

def extract_error_from_log(log_path):
    with open(log_path) as f:
        data = json.load(f)
    stderr_lines = [e['data'] for e in data if e.get('stream_name') == 'stderr']
    # Print last 20 lines of stderr — where error is always located
    print(''.join(stderr_lines[-20:]))
```

## Connections
- [[kaggle-notebook-run]]
- [[kaggle-db-update]]
