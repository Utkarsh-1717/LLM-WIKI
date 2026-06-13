import time, subprocess

kernel_id = "utkarshpatelthefirst/pairs-continuous-ols-pipeline-v1"
output_dir = "/storage/emulated/0/Quant/LLM-WIKI/kaggle_final_output_v2"

def check():
    try:
        out = subprocess.check_output(f"kaggle kernels status {kernel_id}", shell=True).decode('utf-8')
        if "complete" in out.lower(): return "COMPLETE"
        if "error" in out.lower(): return "ERROR"
        return "RUNNING"
    except Exception as e:
        return "RUNNING"

print(f"Monitoring {kernel_id}...")
while True:
    st = check()
    if st in ["COMPLETE", "ERROR"]:
        print(f"DONE: {st}")
        subprocess.run(f"kaggle kernels output {kernel_id} -p {output_dir}", shell=True)
        break
    time.sleep(300)
