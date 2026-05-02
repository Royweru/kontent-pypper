"""
Paystack billing API: checkout initialization, verification, and webhook handling.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.verification import require_verified_email
from app.models.billing import PaymentWebhookEvent
from app.models.user import Subscription, User
from app.services.credit_service import reset_monthly_credits

logger = logging.getLogger(__name__)

router = APIRouter()

PAYSTACK_API_BASE = "https://api.paystack.co"


class CheckoutRequest(BaseModel):
    tier: str = Field(..., description="Target paid tier: pro|max")
    callback_url: Optional[str] = None
    amount_subunit: Optional[int] = None
    currency: str = "NGN"


class VerifyPaymentRequest(BaseModel):
    reference: str


class BillingPortalRequest(BaseModel):
    return_url: Optional[str] = None


def _require_paystack() -> str:
    if not settings.FEATURE_PAYSTACK_BILLING:
        raise HTTPException(status_code=503, detail="Billing is temporarily disabled by feature flag.")
    secret = (settings.PAYSTACK_SECRET_KEY or "").strip()
    if not secret:
        raise HTTPException(status_code=503, detail="Paystack is not configured (missing PAYSTACK_SECRET_KEY).")
    return secret


def _headers(secret_key: str) -> dict:
    return {
        "Authorization": f"Bearer {secret_key}",
        "Content-Type": "application/json",
    }


def _tier_to_plan_code(tier: str) -> str:
    t = (tier or "").strip().lower()
    if t == "pro":
        if not settings.PAYSTACK_PLAN_PRO:
            raise HTTPException(status_code=503, detail="PAYSTACK_PLAN_PRO is not configured.")
        return settings.PAYSTACK_PLAN_PRO
    if t == "max":
        if not settings.PAYSTACK_PLAN_MAX:
            raise HTTPException(status_code=503, detail="PAYSTACK_PLAN_MAX is not configured.")
        return settings.PAYSTACK_PLAN_MAX
    raise HTTPException(status_code=400, detail="Tier must be one of: pro, max.")


def _tier_for_plan_code(plan_code: Optional[str]) -> Optional[str]:
    if not plan_code:
        return None
    if settings.PAYSTACK_PLAN_PRO and plan_code == settings.PAYSTACK_PLAN_PRO:
        return "pro"
    if settings.PAYSTACK_PLAN_MAX and plan_code == settings.PAYSTACK_PLAN_MAX:
        return "max"
    return None


def _default_callback_url() -> str:
    if settings.PAYSTACK_CALLBACK_URL:
        return settings.PAYSTACK_CALLBACK_URL
    return f"{settings.FRONTEND_URL.rstrip('/')}/dashboard?billing=success"


def _default_cancel_url() -> str:
    if settings.PAYSTACK_CANCEL_URL:
        return settings.PAYSTACK_CANCEL_URL
    return f"{settings.FRONTEND_URL.rstrip('/')}/dashboard?billing=cancelled"


def _default_manage_url() -> str:
    if settings.PAYSTACK_MANAGE_URL:
        return settings.PAYSTACK_MANAGE_URL
    return f"{settings.FRONTEND_URL.rstrip('/')}/dashboard"


def _normalize_currency(code: Optional[str]) -> str:
    c = (code or "NGN").strip().upper()
    return c if c else "NGN"


def _safe_int(value: object, fallback: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return fallback


def _apply_tier_to_user(user: User, tier: str) -> None:
    normalized = (tier or "free").strip().lower()
    if normalized not in {"free", "pro", "max"}:
        normalized = "free"
    user.tier_level = normalized
    user.plan = normalized


def _build_paystack_reference(user_id: int, tier: str) -> str:
    suffix = secrets.token_hex(8)
    return f"kp_{user_id}_{tier}_{suffix}"


def _extract_plan_code(data_obj: dict) -> Optional[str]:
    plan = data_obj.get("plan")
    if isinstance(plan, dict):
        return plan.get("plan_code")
    if isinstance(plan, str):
        return plan
    plan_object = data_obj.get("plan_object")
    if isinstance(plan_object, dict):
        return plan_object.get("plan_code")
    return None


def _extract_metadata(data_obj: dict) -> dict:
    metadata = data_obj.get("metadata")
    if isinstance(metadata, str):
        try:
            parsed = json.loads(metadata)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    if isinstance(metadata, dict):
        return metadata
    return {}


def _extract_provider_event_id(event_name: str, data_obj: dict) -> str:
    data_id = data_obj.get("id")
    if data_id is not None:
        return f"{event_name}:{data_id}"
    reference = data_obj.get("reference")
    if reference:
        return f"{event_name}:{reference}"
    return f"{event_name}:{secrets.token_hex(8)}"


def _calculate_amount_for_checkout(tier: str, amount_subunit: Optional[int]) -> int:
    if amount_subunit is not None and amount_subunit > 0:
        return int(amount_subunit)
    # Fallback dev-safe defaults; canonical pricing should come from Paystack plan.
    if tier == "pro":
        return 100000  # 10,000.00 in subunit currency
    if tier == "max":
        return 300000
    return 0


async def _upsert_subscription(
    db: AsyncSession,
    *,
    user: User,
    payment_reference: str,
    plan_tier: str,
    status: str,
    amount: int = 0,
    currency: str = "NGN",
    period_end: Optional[datetime] = None,
) -> None:
    existing = (await db.execute(
        select(Subscription).where(Subscription.payment_reference == payment_reference)
    )).scalar_one_or_none()

    now = datetime.utcnow()
    period_end = period_end or (now + timedelta(days=30))
    normalized_currency = _normalize_currency(currency)

    if existing:
        existing.plan = plan_tier
        existing.status = status
        existing.amount = int(amount or existing.amount or 0)
        existing.currency = normalized_currency
        existing.ends_at = period_end
        existing.payment_method = "paystack"
        return

    db.add(
        Subscription(
            user_id=user.id,
            plan=plan_tier,
            status=status,
            amount=int(amount or 0),
            currency=normalized_currency,
            payment_method="paystack",
            payment_reference=payment_reference,
            starts_at=now,
            ends_at=period_end,
        )
    )


async def _record_event(
    db: AsyncSession,
    *,
    provider_event_id: str,
    event_type: str,
) -> Optional[PaymentWebhookEvent]:
    row = PaymentWebhookEvent(
        provider="paystack",
        provider_event_id=provider_event_id,
        event_type=event_type,
        processed=False,
    )
    db.add(row)
    try:
        await db.commit()
        await db.refresh(row)
        return row
    except IntegrityError:
        await db.rollback()
        return None


async def _mark_event_processed(
    db: AsyncSession,
    event_row: PaymentWebhookEvent,
    *,
    error_message: Optional[str] = None,
) -> None:
    event_row.processed = error_message is None
    event_row.error_message = error_message
    event_row.processed_at = datetime.utcnow()
    await db.commit()


async def _find_user_for_transaction(db: AsyncSession, data_obj: dict) -> Optional[User]:
    metadata = _extract_metadata(data_obj)
    user_id = metadata.get("user_id")
    if user_id is not None:
        user = (await db.execute(select(User).where(User.id == int(user_id)))).scalar_one_or_none()
        if user:
            return user

    customer = data_obj.get("customer") or {}
    customer_code = customer.get("customer_code")
    if customer_code:
        user = (await db.execute(
            select(User).where(User.paystack_customer_code == customer_code)
        )).scalar_one_or_none()
        if user:
            return user

    email = customer.get("email")
    if email:
        return (await db.execute(
            select(User).where(User.email == str(email).strip().lower())
        )).scalar_one_or_none()
    return None


async def _apply_successful_payment(
    db: AsyncSession,
    *,
    user: User,
    data_obj: dict,
) -> None:
    metadata = _extract_metadata(data_obj)
    customer = data_obj.get("customer") or {}
    customer_code = customer.get("customer_code")
    if customer_code:
        user.paystack_customer_code = customer_code
        # Backward compatibility for already-migrated schema.
        user.stripe_customer_id = customer_code

    plan_code = _extract_plan_code(data_obj)
    tier = (metadata.get("tier") or "").strip().lower()
    if tier not in {"pro", "max"}:
        tier = _tier_for_plan_code(plan_code) or user.tier_level or "free"

    _apply_tier_to_user(user, tier)
    await reset_monthly_credits(db, user)

    amount = _safe_int(data_obj.get("amount"), fallback=0)
    currency = _normalize_currency(data_obj.get("currency"))
    reference = str(data_obj.get("reference") or f"paystack:{user.id}:{secrets.token_hex(5)}")
    paid_at = data_obj.get("paid_at") or data_obj.get("paidAt")
    period_end = None
    if paid_at:
        period_end = datetime.utcnow() + timedelta(days=30)

    await _upsert_subscription(
        db,
        user=user,
        payment_reference=reference,
        plan_tier=tier,
        status="active",
        amount=amount,
        currency=currency,
        period_end=period_end,
    )
    await db.commit()


def _verify_paystack_signature(raw_body: bytes, signature_header: Optional[str], secret_key: str) -> bool:
    if not signature_header:
        return False
    computed = hmac.new(secret_key.encode("utf-8"), raw_body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(computed, signature_header)


@router.get("/health")
async def billing_health():
    configured = bool(settings.PAYSTACK_SECRET_KEY and (settings.PAYSTACK_PLAN_PRO or settings.PAYSTACK_PLAN_MAX))
    return {
        "provider": "paystack",
        "configured": configured,
        "has_secret_key": bool(settings.PAYSTACK_SECRET_KEY),
        "has_plan_pro": bool(settings.PAYSTACK_PLAN_PRO),
        "has_plan_max": bool(settings.PAYSTACK_PLAN_MAX),
    }


@router.post("/checkout-session")
async def create_checkout_session(
    payload: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_verified_email(current_user)
    secret_key = _require_paystack()

    requested_tier = payload.tier.strip().lower()
    if requested_tier == "free":
        raise HTTPException(status_code=400, detail="Free tier does not require checkout.")

    plan_code = _tier_to_plan_code(requested_tier)
    callback_url = payload.callback_url or _default_callback_url()
    cancel_url = _default_cancel_url()
    amount = _calculate_amount_for_checkout(requested_tier, payload.amount_subunit)
    reference = _build_paystack_reference(current_user.id, requested_tier)

    metadata = {
        "user_id": current_user.id,
        "tier": requested_tier,
        "cancel_action": cancel_url,
    }
    body = {
        "email": current_user.email,
        "amount": str(amount),
        "reference": reference,
        "callback_url": callback_url,
        "currency": _normalize_currency(payload.currency),
        "plan": plan_code,
        "metadata": metadata,
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            f"{PAYSTACK_API_BASE}/transaction/initialize",
            headers=_headers(secret_key),
            json=body,
        )

    if resp.status_code >= 400:
        logger.error("[Billing] Paystack initialize failed (%s): %s", resp.status_code, resp.text[:500])
        raise HTTPException(status_code=502, detail="Paystack checkout initialization failed.")

    payload_resp = resp.json()
    if not payload_resp.get("status"):
        raise HTTPException(status_code=502, detail=str(payload_resp.get("message") or "Paystack initialize failed."))
    data = payload_resp.get("data") or {}

    return {
        "provider": "paystack",
        "checkout_url": data.get("authorization_url"),
        "access_code": data.get("access_code"),
        "reference": data.get("reference") or reference,
        "tier": requested_tier,
    }


@router.post("/verify-transaction")
async def verify_transaction(
    payload: VerifyPaymentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    secret_key = _require_paystack()
    reference = (payload.reference or "").strip()
    if not reference:
        raise HTTPException(status_code=400, detail="Reference is required.")

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(
            f"{PAYSTACK_API_BASE}/transaction/verify/{reference}",
            headers={"Authorization": f"Bearer {secret_key}"},
        )
    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail="Paystack verification request failed.")

    body = resp.json()
    if not body.get("status"):
        raise HTTPException(status_code=400, detail=str(body.get("message") or "Verification failed."))

    data = body.get("data") or {}
    event_id = f"verify:{reference}"
    event_row = await _record_event(db, provider_event_id=event_id, event_type="verify.charge.success")
    if event_row is None:
        # Already processed
        return {"status": "ok", "processed": False, "reason": "duplicate_reference"}

    try:
        if str(data.get("status") or "").lower() != "success":
            await _mark_event_processed(db, event_row, error_message="transaction_not_success")
            raise HTTPException(status_code=400, detail="Transaction is not successful.")

        metadata = _extract_metadata(data)
        metadata_user_id = metadata.get("user_id")
        if metadata_user_id is not None and int(metadata_user_id) != current_user.id:
            await _mark_event_processed(db, event_row, error_message="user_mismatch")
            raise HTTPException(status_code=403, detail="Transaction does not belong to this user.")

        await _apply_successful_payment(db, user=current_user, data_obj=data)
        await _mark_event_processed(db, event_row)
        return {
            "status": "ok",
            "processed": True,
            "reference": reference,
            "tier_level": current_user.tier_level,
            "credits_remaining": current_user.video_credits_remaining or 0,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[Billing] verify-transaction processing failed: %s", exc, exc_info=True)
        await _mark_event_processed(db, event_row, error_message=str(exc))
        raise HTTPException(status_code=500, detail="Could not finalize verified transaction.")


@router.post("/portal-session")
async def create_billing_portal_session(
    payload: BillingPortalRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Paystack does not provide a direct self-serve portal equivalent.
    Return a configured management URL for account-level billing actions.
    """
    base = _default_manage_url()
    return_url = payload.return_url or base
    email = current_user.email
    separator = "&" if "?" in return_url else "?"
    return {"url": f"{return_url}{separator}email={email}"}


@router.post("/webhook")
async def paystack_webhook(
    request: Request,
    x_paystack_signature: Optional[str] = Header(default=None, alias="x-paystack-signature"),
    db: AsyncSession = Depends(get_db),
):
    secret_key = _require_paystack()
    raw_body = await request.body()

    if not _verify_paystack_signature(raw_body, x_paystack_signature, secret_key):
        raise HTTPException(status_code=400, detail="Invalid Paystack webhook signature.")

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid webhook payload: {exc}")

    event_type = str(payload.get("event") or "")
    data_obj = payload.get("data") or {}
    provider_event_id = _extract_provider_event_id(event_type, data_obj)
    if not event_type:
        raise HTTPException(status_code=400, detail="Missing event type.")

    event_row = await _record_event(
        db,
        provider_event_id=provider_event_id,
        event_type=event_type,
    )
    if event_row is None:
        return {"status": "ignored", "reason": "duplicate_event"}

    try:
        if event_type == "charge.success":
            user = await _find_user_for_transaction(db, data_obj)
            if not user:
                logger.warning("[Billing] webhook charge.success user not found.")
            else:
                await _apply_successful_payment(db, user=user, data_obj=data_obj)
        elif event_type in {"subscription.not_renew", "subscription.disable"}:
            user = await _find_user_for_transaction(db, data_obj)
            if user:
                _apply_tier_to_user(user, "free")
                await db.commit()

        await _mark_event_processed(db, event_row)
        return {"status": "ok"}
    except Exception as exc:
        logger.error("[Billing] paystack webhook failed (%s): %s", event_type, exc, exc_info=True)
        await _mark_event_processed(db, event_row, error_message=str(exc))
        raise HTTPException(status_code=500, detail="Webhook processing failed.")
