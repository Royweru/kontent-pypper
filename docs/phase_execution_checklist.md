# Phase Execution Checklist

## Phase 0 - Guardrails and Rollout Control
- [x] Add feature flags for video pipeline, billing provider, and AI enhancer guardrails.
- [x] Add canary rollout percentage control.
- [x] Add readiness API endpoint (`/api/v1/system/readiness`).
- [x] Add rollout playbook and fallback procedure.

## Phase 1 - Free Tier Trial Upgrade
- [x] Set free tier defaults to `5` starter video credits.
- [x] Set free tier daily run cap to `3` runs/day.
- [x] Allow all supported platforms per run for free tier.
- [x] Backfill legacy users at login/Google-auth to free-tier starter entitlements.

## Phase 2 - Real Stock Video Pipeline
- [x] Replace placeholder video URL flow with real generation path.
- [x] Wire Pexels fetch -> MoviePy compose -> storage upload flow.
- [x] Add local fallback path if cloud storage is not configured.
- [x] Add placeholder-suppression billing guardrails.

## Phase 3 - Billing Provider Integration (Paystack)
- [x] Implement checkout initialization API (`/api/v1/billing/checkout-session`).
- [x] Implement transaction verification API (`/api/v1/billing/verify-transaction`).
- [x] Implement signed webhook ingestion with idempotency (`/api/v1/billing/webhook`).
- [x] Add Paystack settings and plan-code mapping.
- [x] Persist payment webhook events for audit/idempotency.
- [x] Add DB migration for `paystack_customer_code`.

## Phase 4 - Frontend Billing Activation
- [x] Replace "Upgrade flow coming soon" UI stubs with real checkout trigger.
- [x] Handle Paystack callback query params (`billing`, `reference`, `trxref`).
- [x] Verify successful transactions from dashboard boot flow.
- [x] Refresh current user state after successful verification.

## Phase 5 - AI Enhancer Hard Tests
- [x] Add AI enhancer tests for schema mapping and failure propagation.
- [x] Validate prompt context pass-through for user input.

## Phase 6 - Billing and Pipeline Reliability Tests
- [x] Add Paystack signature verification tests.
- [x] Add event-id extraction and metadata parsing tests.
- [x] Add free-tier policy and placeholder-video regression tests.

## Phase 7 - Release Readiness Automation
- [x] Add release-readiness script for required env var checks.
- [x] Add billing and system health endpoints for operations.
- [x] Document staged rollout procedure (10 -> 25 -> 50 -> 100).

## Phase 8 - Production Launch Gates
- [ ] Apply all required production secrets (Paystack, Pexels, R2).
- [ ] Run Alembic migrations in production.
- [ ] Enable flags progressively per rollout plan.
- [ ] Monitor error rates and conversion metrics through final ramp to 100%.
