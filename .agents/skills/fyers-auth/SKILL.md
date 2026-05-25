---
name: fyers-auth
trigger: [fyers data, live feed, historical data, authenticate fyers, fyers token]
description: Authenticates with Fyers API using 5-step TOTP flow
---

## Rules

1. Source credentials from ~/.quant_env — never hardcode
2. Execute auth in exact order:
   - Step 1: POST https://api-t2.fyers.in/vagator/v2/send_login_otp — body: {fy_id, app_id:"2"}
   - Step 2: POST https://api-t2.fyers.in/vagator/v2/verify_otp — body: {request_key, otp: pyotp.TOTP(TOTP_KEY).now()}
   - Step 3: POST https://api-t2.fyers.in/vagator/v2/verify_pin — body: {request_key, identity_type:"pin", identifier:PIN}
   - Step 4: POST https://api-t1.fyers.in/api/v3/token — extract auth_code from response URL
   - Step 5: fyersModel.SessionModel — generate_token() → extract access_token
3. Return token as string: APP_ID:access_token
4. On any step failure: print exact error JSON, stop immediately, report to user
5. Never write token to any file
6. Token valid for current session only
