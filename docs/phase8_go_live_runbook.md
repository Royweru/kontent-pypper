# Phase 8 Go-Live Runbook

## 1) Preflight Validation
- Run env/flag checks:
  - `venv\Scripts\python.exe scripts\check_release_readiness.py --mode preflight`
- Run strict go-live gate:
  - `venv\Scripts\python.exe scripts\check_release_readiness.py --mode go-live`
- Run critical reliability tests:
  - `venv\Scripts\python.exe -m pytest tests\test_phase1_4_guardrails.py tests\test_phase2_4_delivery.py tests\test_phase5_ai_enhancer.py tests\test_phase6_billing_reliability.py tests\test_platform_rules.py tests\test_phase5_security.py`

## 2) Database Migration Gate
- Check current revision:
  - `venv\Scripts\alembic.exe current`
- Apply latest migrations:
  - `venv\Scripts\alembic.exe upgrade head`
- Verify `paystack_customer_code` exists on `users` and `payment_webhook_events` table exists.

## 3) Service Smoke Checks
- Start the app in the target environment.
- Run:
  - `powershell -ExecutionPolicy Bypass -File scripts\smoke_phase8.ps1 -BaseUrl https://<your-app-domain>`
- Confirm:
  - `/health` returns `status=ok`
  - `/api/v1/system/readiness` returns expected feature flags
  - `/api/v1/billing/health` shows `provider=paystack`

## 4) Canary Rollout
- Set:
  - `FEATURE_REAL_VIDEO_PIPELINE=true`
  - `FEATURE_PAYSTACK_BILLING=true`
  - `FEATURE_AI_ENHANCER_GUARDRAILS=true`
- Rollout progression:
  - `ROLLOUT_CANARY_PERCENT=10` for 24h
  - `ROLLOUT_CANARY_PERCENT=25` for 24h
  - `ROLLOUT_CANARY_PERCENT=50` for 24h
  - `ROLLOUT_CANARY_PERCENT=100` after stability

## 5) Billing Flow Validation (Paystack)
- Initiate checkout from dashboard upgrade button.
- Confirm callback includes reference (`reference` or `trxref`) and verify endpoint processes it.
- Confirm user tier changes (`free -> pro/max`) and credits reset for paid tier.
- Confirm duplicate webhook events do not double-apply entitlements.

## 6) Rollback Controls
- Pause billing writes:
  - `FEATURE_PAYSTACK_BILLING=false`
- Pause real video generation:
  - `FEATURE_REAL_VIDEO_PIPELINE=false`
  - or set `ROLLOUT_CANARY_PERCENT=0`
- Keep core drafting/review APIs online while mitigating incidents.
