import time, subprocess
def check():
    out = subprocess.check_output("kaggle kernels status utkarshpatelthefirst/pairs-continuous-ols-pipeline-v1", shell=True).decode('utf-8')
    if "complete" in out.lower(): return "COMPLETE"
    if "error" in out.lower(): return "ERROR"
    return "RUNNING"
while True:
    st = check()
    if st in ["COMPLETE", "ERROR"]:
        print(f"DONE: {st}")
        subprocess.run("kaggle kernels output utkarshpatelthefirst/pairs-continuous-ols-pipeline-v1 -p /storage/emulated/0/Quant/LLM-WIKI/kaggle_final_output", shell=True)
        break
    time.sleep(300)
