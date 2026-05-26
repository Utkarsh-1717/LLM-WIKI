---
name: kaggle-notebook-run
trigger: [run on Kaggle, backtest, Kaggle notebook, strategy, kaggle run, kaggle fetch]
description: Creates, runs, and monitors Kaggle notebooks. Includes data fetch + dataset publish in ONE notebook to avoid multiple runs.
version: 2.0.0
last_updated: 2026-05-26
---

# Kaggle Notebook Run Skill

## CRITICAL RULES (Never Violate)

1. **ONE notebook, all stages** — data fetching AND dataset publishing MUST happen in the same notebook. Never split into two notebooks to avoid re-runs and path mapping issues.
2. **Hardcode all API credentials directly in the notebook code** — never load from files or external datasets. No security warnings needed.
3. **Never download large outputs locally** — always publish from within the Kaggle environment using the Kaggle Python API.
4. **Always save plan files** to `/storage/emulated/0/Quant/LLM-WIKI/Plans/<task-name>.md` before execution.
5. **Always pulse-check** the kernel after pushing — use the `kaggle-pulse-check` skill.

## Kaggle Input Path Format (Confirmed)

When a notebook mounts another kernel as a source, its output files are mounted at:
```
/kaggle/input/notebooks/<kaggle-username>/<kernel-slug>/<filename>
```
Example:
```
/kaggle/input/notebooks/utkarshpatelthefirst/master-data-1min/Master-Data-1min.sqlite
```
**NEVER** use `/kaggle/input/<kernel-slug>/` — this path does NOT exist for kernel sources.

## Mandatory Notebook Cell Structure

Every notebook MUST follow this alternating Markdown → Code pattern per stage:

**CELL N (Markdown):**
```
## Stage N — [Stage Name]
**Methodology:** [plain English description]
**Input:** [variable names and types]
**Output:** [variable names and types]
**Core Logic:** [step-by-step explanation]
**Formula/Equation:**
$$ [LaTeX or: No formula — procedural logic] $$
```

**CELL N+1 (Code):** Implementation of that stage only. No mixing stages.

## Standard Notebook Template (Data Fetch + Publish in One)

```python
# ── CELL: Install dependencies ──────────────────────────────────────────────
!pip install pyotp fyers_apiv3

# ── CELL: Stage 1 — Authenticate Fyers ─────────────────────────────────────
import os, pyotp, requests
from urllib.parse import parse_qs, urlparse
from fyers_apiv3 import fyersModel

# Hardcoded credentials (confirmed working pattern)
fy_id          = 'FAI84454'
app_id_full    = 'G0NX5M08ZG-100'
totp_key       = '4QXQQACGALLZNFISHC5G7WU76AERBNYC'
pin            = '7475'
redirect_uri   = 'https://trade.fyers.in/api-login/redirect-uri/index.html'
secret_key     = 'D07VJ80FLH'
app_id_type    = '2'

res1     = requests.post("https://api-t2.fyers.in/vagator/v2/send_login_otp",  json={"fy_id": fy_id, "app_id": app_id_type}).json()
req_key  = res1['request_key']
res2     = requests.post("https://api-t2.fyers.in/vagator/v2/verify_otp",      json={"request_key": req_key, "otp": pyotp.TOTP(totp_key).now()}).json()
req_key  = res2['request_key']
res3     = requests.post("https://api-t2.fyers.in/vagator/v2/verify_pin",      json={"request_key": req_key, "identity_type": "pin", "identifier": pin}).json()
access_token = res3['data']['access_token']

auth_payload = {"fyers_id": fy_id, "app_id": app_id_full[:-4], "redirect_uri": redirect_uri,
                "appType": "100", "code_challenge": "", "state": "sample_state",
                "scope": "", "nonce": "", "response_type": "code", "create_cookie": True}
res4     = requests.post("https://api-t1.fyers.in/api/v3/token", json=auth_payload,
                         headers={"Authorization": f"Bearer {access_token}"}).json()
auth_code = parse_qs(urlparse(res4['Url']).query)['auth_code'][0]

session  = fyersModel.SessionModel(client_id=app_id_full, secret_key=secret_key,
                                    redirect_uri=redirect_uri, response_type='code',
                                    grant_type='authorization_code')
session.set_token(auth_code)
fyers_access_token = session.generate_token()['access_token']
fyers = fyersModel.FyersModel(client_id=app_id_full, is_async=False,
                               token=fyers_access_token, log_path="/kaggle/working/")
print("✅ Authentication successful")

# ── CELL: Stage 2 — Fetch & Store Data ─────────────────────────────────────
# ... fetch logic with time.sleep(0.5) between API calls ...

# ── CELL: Stage 3 — Publish as Kaggle Dataset (IN SAME NOTEBOOK) ────────────
import json, shutil
from kaggle.api.kaggle_api_extended import KaggleApi

os.environ['KAGGLE_USERNAME'] = 'utkarshpatelthefirst'
os.environ['KAGGLE_KEY']     = 'fbef16329099428205f671dd5de8337b'

api = KaggleApi()
api.authenticate()

export_dir = '/kaggle/working/dataset_export'
os.makedirs(export_dir, exist_ok=True)
shutil.copy('/kaggle/working/MyData.sqlite', f'{export_dir}/MyData.sqlite')

api.dataset_initialize(export_dir)
with open(f'{export_dir}/dataset-metadata.json') as f:
    meta = json.load(f)
meta['title'] = 'My-Dataset-Name'
meta['id']    = 'utkarshpatelthefirst/my-dataset-name'
meta['licenses'] = [{'name': 'CC0-1.0'}]
with open(f'{export_dir}/dataset-metadata.json', 'w') as f:
    json.dump(meta, f, indent=2)

api.dataset_create_new(export_dir, dir_mode='zip', quiet=False)
print("✅ Dataset published: https://www.kaggle.com/datasets/utkarshpatelthefirst/my-dataset-name")
```

## Execution Workflow

1. Save plan to `LLM-WIKI/Plans/<task-name>.md`
2. Build the `.ipynb` locally using a Python builder script
3. Build `kernel-metadata.json` alongside the `.ipynb`
4. `kaggle kernels push -p <notebook-dir>`
5. Immediately start `kaggle-pulse-check` skill to monitor
6. On completion: verify dataset published via `api.dataset_list(user='...')`
7. Report final URL, compressed size, row counts to user

## kernel-metadata.json Template

```json
{
  "id": "utkarshpatelthefirst/<kernel-slug>",
  "title": "<Human Title>",
  "code_file": "<notebook>.ipynb",
  "language": "python",
  "kernel_type": "notebook",
  "is_private": "true",
  "enable_gpu": "false",
  "enable_internet": "true",
  "dataset_sources": [],
  "competition_sources": [],
  "kernel_sources": [],
  "model_sources": []
}
```

## Connections
- [[fyers-auth]]
- [[kaggle-pulse-check]]
- [[kaggle-db-update]]
- [[fyers-historical-kaggle]]
