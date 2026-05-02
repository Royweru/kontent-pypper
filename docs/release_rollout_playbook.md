# KontentPyper Rollout Playbook (Phases 7-8)

## Objective
Ship real video generation and Paystack billing safely with measurable rollout gates.

## Rollout Flags
- `FEATURE_REAL_VIDEO_PIPELINE`
- `FEATURE_PAYSTACK_BILLING`
- `FEATURE_AI_ENHANCER_GUARDRAILS`
- `ROLLOUT_CANARY_PERCENT`

## Recommended Rollout Steps
1. Set all feature flags to `false` except dashboards and non-critical APIs.
2. Enable `FEATURE_REAL_VIDEO_PIPELINE=true` with `ROLLOUT_CANARY_PERCENT=10`.
3. Monitor run failures, media generation latency, and review-queue quality for 24 hours.
4. Increase canary to `25`, `50`, then `100` once failure rate stays below target.
5. Enable `FEATURE_PAYSTACK_BILLING=true` in test mode and verify checkout + webhook idempotency.
6. Switch Paystack to live mode and monitor conversion and subscription event processing.

## Acceptance Gates
- Real video generation success rate >= 95% over rolling 24h.
- Billing webhook processing success rate >= 99%.
- Duplicate webhook events produce no duplicate entitlement updates.
- Free-tier users can run 3 times/day and receive 5 starter video credits.

## Operational Checks
Use:
- `GET /api/v1/system/readiness`
- `GET /api/v1/billing/health`

## Incident Fallback
1. Set `FEATURE_PAYSTACK_BILLING=false` to pause payment writes.
2. Set `ROLLOUT_CANARY_PERCENT=0` or `FEATURE_REAL_VIDEO_PIPELINE=false` to pause generation.
3. Keep workflow text generation + review queue active while incident is mitigated.

