import time, subprocess, re

KERNEL = "utkarshpatelthefirst/stage-2-kalman-validation-final-v2"
print(f"🔍 Monitoring: {KERNEL}", flush=True)

def check_status(kernel_ref):
    try:
        result = subprocess.run(
            ['bash', '-c',
             f'set -a && source ~/.quant_env && set +a && kaggle kernels status {kernel_ref}'],
            capture_output=True, text=True, timeout=30
        )
        out = (result.stdout + result.stderr).lower()

        if 'complete'        in out: return 'COMPLETE'
        if 'running'         in out: return 'RUNNING'
        if 'queued'          in out: return 'QUEUED'
        if 'cancel'          in out: return 'CANCELLED'
        if 'error' in out and result.returncode == 0:
            return 'KERNEL_ERROR'

        return f"UNKNOWN: {(result.stdout + result.stderr).strip()[:80]}"

    except subprocess.TimeoutExpired:
        return "CONNECTIVITY_LOST (timeout)"
    except Exception as e:
        return f"CONNECTIVITY_LOST ({type(e).__name__})"

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

start               = time.time()
last_status         = None
consecutive_errors  = 0
CONFIRM_THRESHOLD   = 3
FAST_SECS           = 300
FAST_INT            = 10
SLOW_INT            = 120

while True:
    elapsed  = time.time() - start
    interval = FAST_INT if elapsed < FAST_SECS else SLOW_INT
    status   = check_status(KERNEL)

    if status != last_status:
        print(f"[{int(elapsed):>5}s] {status}", flush=True)
        last_status = status

    if status == 'COMPLETE':
        print(f"\n✅ Kernel COMPLETE after {int(elapsed)}s")
        print(f"   URL: https://www.kaggle.com/code/{KERNEL}")
        break

    if status == 'KERNEL_ERROR':
        consecutive_errors += 1
        print(f"   ⚠️  KERNEL_ERROR signal {consecutive_errors}/{CONFIRM_THRESHOLD}", flush=True)
        if consecutive_errors >= CONFIRM_THRESHOLD:
            print(f"\n❌ Kernel FAILED (confirmed {CONFIRM_THRESHOLD}x) after {int(elapsed)}s")
            print("   Fetching error logs...")
            fetch_error_log(KERNEL)
            break
        time.sleep(15)
        continue
    else:
        consecutive_errors = 0

    time.sleep(interval)
