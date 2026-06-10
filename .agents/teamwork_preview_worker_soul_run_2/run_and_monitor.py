import os
import re
import time
import subprocess
import json

def load_env():
    env_path = os.path.expanduser('~/.quant_env')
    if not os.path.exists(env_path):
        raise FileNotFoundError(f"Credentials file {env_path} not found.")
    
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if 'export ' in line:
                line = line.replace('export ', '')
            if '=' in line:
                k, v = line.split('=', 1)
                os.environ[k.strip()] = v.strip().strip('"').strip("'")
    print("✅ Environment credentials loaded from ~/.quant_env")

def push_kernel():
    soul_dir = "/storage/emulated/0/Quant/LLM-WIKI/Soul"
    print(f"Pushing kernel from {soul_dir}...")
    
    result = subprocess.run(
        ['kaggle', 'kernels', 'push', '-p', soul_dir],
        capture_output=True, text=True
    )
    print("=== Push Output ===")
    print(result.stdout)
    print(result.stderr)
    
    if result.returncode != 0:
        raise RuntimeError("Failed to push kernel to Kaggle")
        
    match = re.search(r'kaggle\.com/code/([^/]+/[^\s]+)', result.stdout + result.stderr)
    if not match:
         # Fallback to standard slug if matching fails
         slug = "utkarshpatelthefirst/master-pairs-trading-soul"
    else:
         slug = match.group(1).strip()
    
    print(f"🔍 Successfully pushed. Kernel slug: {slug}")
    return slug

def check_status(kernel_ref):
    try:
        result = subprocess.run(
            ['kaggle', 'kernels', 'status', kernel_ref],
            capture_output=True, text=True, timeout=30
        )
        out = (result.stdout + result.stderr).lower()
        if 'complete' in out: return 'COMPLETE'
        if 'running' in out: return 'RUNNING'
        if 'queued' in out: return 'QUEUED'
        if 'cancel' in out: return 'CANCELLED'
        if 'error' in out and result.returncode == 0:
            return 'KERNEL_ERROR'
        return f"UNKNOWN: {(result.stdout + result.stderr).strip()[:80]}"
    except subprocess.TimeoutExpired:
        return "CONNECTIVITY_LOST (timeout)"
    except Exception as e:
        return f"CONNECTIVITY_LOST ({type(e).__name__})"

def fetch_error_log(kernel_ref):
    log_dir = "/storage/emulated/0/Quant/_kernel_logs"
    os.makedirs(log_dir, exist_ok=True)
    subprocess.run(
        ['kaggle', 'kernels', 'output', kernel_ref, '-p', log_dir, '--force'],
        capture_output=True, timeout=120
    )
    slug = kernel_ref.split("/")[-1]
    log_path = f"{log_dir}/{slug}.log"
    if not os.path.exists(log_path):
        print("  Log file not found — check Kaggle web UI")
        return
    with open(log_path) as f:
        try:
            data = json.load(f)
            lines = [e['data'] for e in data if isinstance(e, dict) and 'data' in e]
            print("\n".join(''.join(lines).splitlines()[-80:]))
        except Exception as e:
            print(f"Error parsing log file: {e}")

def monitor_kernel(kernel_ref):
    print(f"Starting pulse check for: {kernel_ref}")
    start = time.time()
    last_status = None
    consecutive_errors = 0
    CONFIRM_THRESHOLD = 3
    FAST_SECS = 300
    FAST_INT = 10
    SLOW_INT = 120
    
    while True:
        elapsed = time.time() - start
        interval = FAST_INT if elapsed < FAST_SECS else SLOW_INT
        status = check_status(kernel_ref)
        
        if status != last_status:
            print(f"[{int(elapsed):>5}s] Status change: {status}", flush=True)
            last_status = status
            
        if status == 'COMPLETE':
            print(f"\n✅ Kernel COMPLETE after {int(elapsed)}s")
            print(f"   URL: https://www.kaggle.com/code/{kernel_ref}")
            break
            
        if status == 'KERNEL_ERROR':
            consecutive_errors += 1
            print(f"   ⚠️ KERNEL_ERROR signal {consecutive_errors}/{CONFIRM_THRESHOLD}", flush=True)
            if consecutive_errors >= CONFIRM_THRESHOLD:
                print(f"\n❌ Kernel FAILED (confirmed {CONFIRM_THRESHOLD}x) after {int(elapsed)}s")
                print("   Fetching error logs...")
                fetch_error_log(kernel_ref)
                break
            time.sleep(15)
            continue
        else:
            consecutive_errors = 0
            
        time.sleep(interval)

if __name__ == "__main__":
    try:
        load_env()
        slug = push_kernel()
        monitor_kernel(slug)
    except Exception as e:
        print(f"❌ Error: {e}")
