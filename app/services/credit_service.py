"""
KontentPyper - Credit Service
=============================
Central business-logic layer for all credit and tier operations.

Tier Reference:
  - free : 0 video credits, 1 workflow run/day
  - pro  : 20 video credits/month, unlimited runs/day
  - max  : 50 video credits/month, unlimited runs/day + cron

Credit Costs:
  - Stock video (Pexels):  0 credits
  - Kling AI video:        1 credit
  - Runway Gen-4 / Sora-2: 3 credits
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.credit import CreditTransaction

logger = logging.getLogger(__name__)


# ── Tier Configuration ────────────────────────────────────────────────────────

TIER_CONFIG = {
    "free": {
        "monthly_video_credits": 0,
        "max_runs_per_day": 1,
        "max_feeds": 3,
        "max_niches": 1,
        "max_platforms_per_run": 1,
        "video_quality": "stock",       # Pexels + MoviePy only
        "has_scheduling": False,
        "has_cron": False,
        "has_telegram_hitl": False,
    },
    "pro": {
        "monthly_video_credits": 20,
        "max_runs_per_day": None,        # Unlimited
        "max_feeds": None,               # Unlimited
        "max_niches": 3,
        "max_platforms_per_run": None,    # All platforms
        "video_quality": "cinematic",    # Kling AI via Fal.ai
        "has_scheduling": True,
        "has_cron": False,
        "has_telegram_hitl": True,
    },
    "max": {
        "monthly_video_credits": 50,
        "max_runs_per_day": None,
        "max_feeds": None,
        "max_niches": None,
        "max_platforms_per_run": None,
        "video_quality": "premium",      # Runway Gen-4 / Sora-2
        "has_scheduling": True,
        "has_cron": True,
        "has_telegram_hitl": True,
    },
}

# Cost per video generation by model
VIDEO_CREDIT_COSTS = {
    "stock": 0,        # Pexels + MoviePy
    "kling": 1,        # Kling AI via Fal.ai
    "runway": 3,       # Runway Gen-4
    "sora": 3,         # Sora-2
}


# ── Exceptions ────────────────────────────────────────────────────────────────

class InsufficientCreditsError(Exception):
    """Raised when a user does not have enough video credits."""
    def __init__(self, required: int, available: int, tier: str):
        self.required = required
        self.available = available
        self.tier = tier
        super().__init__(
            f"Insufficient credits: need {required}, have {available} (tier={tier})"
        )


class DailyRunLimitError(Exception):
    """Raised when a free-tier user exceeds their daily run limit."""
    def __init__(self, max_runs: int):
        self.max_runs = max_runs
        super().__init__(f"Daily run limit reached: max {max_runs} runs/day on free tier")


# ── Core Service Functions ────────────────────────────────────────────────────

def get_tier_config(tier: str) -> dict:
    """Returns the configuration dict for a given tier level."""
    return TIER_CONFIG.get(tier, TIER_CONFIG["free"])


async def get_user_credits(db: AsyncSession, user_id: int) -> dict:
    """
    Returns the current credit status for a user.
    Used by the dashboard to render the credits widget.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        return {"error": "User not found"}

    tier = user.tier_level or "free"
    cfg = get_tier_config(tier)

    return {
        "tier": tier,
        "video_credits_remaining": user.video_credits_remaining or 0,
        "video_credits_used_this_month": user.video_credits_used_this_month or 0,
        "monthly_allocation": cfg["monthly_video_credits"],
        "workflow_runs_today": user.workflow_runs_today or 0,
        "max_runs_per_day": cfg["max_runs_per_day"],
        "credits_reset_date": user.credits_reset_date.isoformat() if user.credits_reset_date else None,
        "runs_reset_date": user.workflow_runs_reset_date.isoformat() if user.workflow_runs_reset_date else None,
        "video_quality": cfg["video_quality"],
        "has_scheduling": cfg["has_scheduling"],
        "has_cron": cfg["has_cron"],
        "has_telegram_hitl": cfg["has_telegram_hitl"],
    }


async def check_workflow_run_allowed(db: AsyncSession, user: User) -> None:
    """
    Verifies the user has permission to start a workflow run.
    For free tier: enforces 1 run/day limit.
    For pro/max: always allowed (unlimited runs).

    Raises DailyRunLimitError if blocked.
    """
    tier = user.tier_level or "free"
    cfg = get_tier_config(tier)
    max_runs = cfg["max_runs_per_day"]

    # Pro and Max have unlimited runs
    if max_runs is None:
        return

    # Check if we need to reset the daily counter
    now = datetime.utcnow()
    reset_date = user.workflow_runs_reset_date

    if reset_date is None or now >= reset_date:
        # Reset the counter -- new day
        user.workflow_runs_today = 0
        user.workflow_runs_reset_date = now.replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)
        await db.commit()

    current_runs = user.workflow_runs_today or 0
    if current_runs >= max_runs:
        raise DailyRunLimitError(max_runs)


async def increment_daily_runs(db: AsyncSession, user: User) -> None:
    """Increments the daily workflow run counter after a successful run start."""
    user.workflow_runs_today = (user.workflow_runs_today or 0) + 1
    await db.commit()


async def check_video_credits(db: AsyncSession, user: User, model: str = "stock") -> int:
    """
    Checks if user has enough credits for a video generation.
    Returns the credit cost.
    Raises InsufficientCreditsError if not enough credits.
    """
    cost = VIDEO_CREDIT_COSTS.get(model, 1)

    # Stock video is always free
    if cost == 0:
        return 0

    tier = user.tier_level or "free"
    available = user.video_credits_remaining or 0

    if available < cost:
        raise InsufficientCreditsError(
            required=cost,
            available=available,
            tier=tier,
        )

    return cost


async def consume_credits(
    db: AsyncSession,
    user: User,
    credits: int,
    action_type: str,
    model_used: str = None,
    description: str = None,
) -> CreditTransaction:
    """
    Atomically deducts credits from the user and logs the transaction.

    Args:
        db: Async database session
        user: User ORM object
        credits: Number of credits to consume (positive integer)
        action_type: Type of action (workflow_run, regenerate, etc.)
        model_used: AI model identifier (kling, runway, sora)
        description: Human-readable context

    Returns:
        The CreditTransaction record
    """
    if credits <= 0:
        return None

    before = user.video_credits_remaining or 0
    after = max(0, before - credits)

    # Update user balance
    user.video_credits_remaining = after
    user.video_credits_used_this_month = (user.video_credits_used_this_month or 0) + credits

    # Create audit log
    tx = CreditTransaction(
        user_id=user.id,
        action_type=action_type,
        credits_delta=-credits,
        credits_before=before,
        credits_after=after,
        model_used=model_used,
        description=description,
    )
    db.add(tx)
    await db.commit()

    logger.info(
        "[CreditService] user_id=%d consumed %d credits (%s). %d -> %d remaining.",
        user.id, credits, action_type, before, after,
    )

    return tx


async def add_credits(
    db: AsyncSession,
    user: User,
    credits: int,
    action_type: str = "topup",
    description: str = None,
) -> CreditTransaction:
    """
    Adds credits to a user (top-up or monthly reset).
    """
    before = user.video_credits_remaining or 0
    after = before + credits

    user.video_credits_remaining = after

    tx = CreditTransaction(
        user_id=user.id,
        action_type=action_type,
        credits_delta=credits,
        credits_before=before,
        credits_after=after,
        description=description,
    )
    db.add(tx)
    await db.commit()

    logger.info(
        "[CreditService] user_id=%d added %d credits (%s). %d -> %d remaining.",
        user.id, credits, action_type, before, after,
    )

    return tx


async def reset_monthly_credits(db: AsyncSession, user: User) -> None:
    """
    Called at subscription renewal. Resets credit balance to tier allocation.
    Does NOT roll over unused credits.
    """
    tier = user.tier_level or "free"
    cfg = get_tier_config(tier)
    allocation = cfg["monthly_video_credits"]

    before = user.video_credits_remaining or 0

    user.video_credits_remaining = allocation
    user.video_credits_used_this_month = 0
    user.credits_reset_date = datetime.utcnow() + timedelta(days=30)

    tx = CreditTransaction(
        user_id=user.id,
        action_type="monthly_reset",
        credits_delta=allocation - before,
        credits_before=before,
        credits_after=allocation,
        description=f"Monthly reset for {tier} tier ({allocation} credits)",
    )
    db.add(tx)
    await db.commit()

    logger.info(
        "[CreditService] user_id=%d monthly reset: %d -> %d credits (tier=%s).",
        user.id, before, allocation, tier,
    )


async def reset_daily_runs(db: AsyncSession, user: User) -> None:
    """Resets the daily workflow run counter. Called by cron or on new-day check."""
    user.workflow_runs_today = 0
    user.workflow_runs_reset_date = datetime.utcnow().replace(
        hour=0, minute=0, second=0, microsecond=0
    ) + timedelta(days=1)

    tx = CreditTransaction(
        user_id=user.id,
        action_type="daily_reset",
        credits_delta=0,
        credits_before=user.video_credits_remaining or 0,
        credits_after=user.video_credits_remaining or 0,
        description="Daily run counter reset",
    )
    db.add(tx)
    await db.commit()


def get_video_model_for_tier(tier: str) -> str:
    """
    Returns the appropriate video generation model based on tier.

    free -> 'stock'  (Pexels + MoviePy)
    pro  -> 'kling'  (Kling AI via Fal.ai)
    max  -> 'runway' (Runway Gen-4 Turbo)
    """
    mapping = {
        "free": "stock",
        "pro": "kling",
        "max": "runway",
    }
    return mapping.get(tier, "stock")
