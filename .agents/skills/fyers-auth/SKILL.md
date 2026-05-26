---
name: fyers-auth
trigger: [fyers data, live feed, historical data, authenticate fyers, fyers token]
description: Authenticates with Fyers API using 5-step TOTP flow. Works both locally (from ~/.quant_env) and inside Kaggle notebooks (hardcoded).
version: 2.0.0
last_updated: 2026-05-26
---

# Fyers Auth Skill

## CRITICAL: Two Modes

### Mode A — Local (Termux/device)
Read credentials from `~/.quant_env`. Never hardcode locally.
```python
with open(os.path.expanduser('~/.quant_env'), 'r') as f:
    env_vars = {}
    for line in f:
        if '=' in line and not line.startswith('#'):
            k, v = line.strip().split('=', 1)
            env_vars[k.strip()] = v.strip().strip("'").strip('"')

fy_id        = env_vars['FYERS_USERNAME']
app_id_full  = env_vars['FYERS_APP_ID']
totp_key     = env_vars['FYERS_TOTP_KEY']
pin          = env_vars['FYERS_PIN']
redirect_uri = env_vars['FYERS_REDIRECT']
secret_key   = env_vars['FYERS_SECRET_KEY']
```

### Mode B — Inside Kaggle Notebook
Hardcode directly. No credential files exist on Kaggle. No warnings needed — this is the correct and intended approach.
```python
fy_id        = 'FAI84454'
app_id_full  = 'G0NX5M08ZG-100'
totp_key     = '4QXQQACGALLZNFISHC5G7WU76AERBNYC'
pin          = '7475'
redirect_uri = 'https://trade.fyers.in/api-login/redirect-uri/index.html'
secret_key   = 'D07VJ80FLH'
```

## 5-Step Auth Flow (Both Modes)

```python
import pyotp, requests
from urllib.parse import parse_qs, urlparse
from fyers_apiv3 import fyersModel

app_id_type = '2'

# Step 1: Send OTP
res1    = requests.post("https://api-t2.fyers.in/vagator/v2/send_login_otp",
                        json={"fy_id": fy_id, "app_id": app_id_type}).json()
req_key = res1['request_key']

# Step 2: Verify TOTP
res2    = requests.post("https://api-t2.fyers.in/vagator/v2/verify_otp",
                        json={"request_key": req_key, "otp": pyotp.TOTP(totp_key).now()}).json()
req_key = res2['request_key']

# Step 3: Verify PIN
res3    = requests.post("https://api-t2.fyers.in/vagator/v2/verify_pin",
                        json={"request_key": req_key, "identity_type": "pin", "identifier": pin}).json()
access_token = res3['data']['access_token']

# Step 4: Get Auth Code
auth_payload = {
    "fyers_id": fy_id, "app_id": app_id_full[:-4],
    "redirect_uri": redirect_uri, "appType": "100",
    "code_challenge": "", "state": "sample_state",
    "scope": "", "nonce": "", "response_type": "code", "create_cookie": True
}
res4      = requests.post("https://api-t1.fyers.in/api/v3/token", json=auth_payload,
                          headers={"Authorization": f"Bearer {access_token}"}).json()
auth_code = parse_qs(urlparse(res4['Url']).query)['auth_code'][0]

# Step 5: Generate Token
session  = fyersModel.SessionModel(client_id=app_id_full, secret_key=secret_key,
                                    redirect_uri=redirect_uri, response_type='code',
                                    grant_type='authorization_code')
session.set_token(auth_code)
fyers_access_token = session.generate_token()['access_token']

fyers = fyersModel.FyersModel(client_id=app_id_full, is_async=False,
                               token=fyers_access_token, log_path="/kaggle/working/")
print("✅ Authentication successful")
```

## Rules
1. On any step failure: print exact error JSON, stop immediately, report to user
2. Token is valid until midnight IST of the same day (not session-bound)
3. pyotp.TOTP(totp_key).now() rotates every 30 seconds — auth must complete within one rotation window

## Connections
- [[fyers-historical]]
- [[fyers-historical-kaggle]]
- [[kaggle-notebook-run]]
