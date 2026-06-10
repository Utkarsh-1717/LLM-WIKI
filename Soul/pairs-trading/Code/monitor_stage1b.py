import time, subprocess, sys

def check_status(kernel_id):
    cmd = f"kaggle kernels status {kernel_id}"
    try:
        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode('utf-8').strip()
        if "error" in out.lower():
            return "ERROR"
        if "complete" in out.lower():
            return "COMPLETE"
        if "running" in out.lower() or "queued" in out.lower():
            return "RUNNING"
        return "UNKNOWN"
    except Exception as e:
        return "NETWORK_ERR"

k1 = "utkarshpatelthefirst/pairs-stage1b-cointegration-v1"
k1_done = False

print(f"Monitoring Stage 1B Kaggle Kernel...")
t0 = time.time()

while not k1_done:
    st1 = check_status(k1)
    if st1 in ["COMPLETE", "ERROR"]:
        print(f"\\n[{int(time.time()-t0)}s] {k1} -> {st1}")
        k1_done = True
            
    if not k1_done:
        print(".", end="", flush=True)
        time.sleep(60)

print(f"\\n\\nKernel finished!")
