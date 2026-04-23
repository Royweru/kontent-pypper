"""
KontentPyper - Autonomous Campaign API
CRUD endpoints for managing agent-driven content campaigns (Max tier only).
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.campaign import AgentCampaign, AgentCampaignRun
from app.services.credit_service import get_tier_config

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Preset Map (shared with schedule.py) ──────────────────────────────────────

PRESET_MAP = {
    "daily_8am":    {"hour": 8,  "minute": 0,  "dow": "*"},
    "daily_12pm":   {"hour": 12, "minute": 0,  "dow": "*"},
    "daily_6pm":    {"hour": 18, "minute": 0,  "dow": "*"},
    "weekdays_9am": {"hour": 9,  "minute": 0,  "dow": "mon,tue,wed,thu,fri"},
}


# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    niche: str = Field(..., min_length=1, max_length=255)
    topic_instructions: Optional[str] = None
    target_platforms: List[str] = Field(default_factory=list)
    auto_publish: bool = False
    schedule_preset: str = "daily_8am"
    cron_hour: int = Field(default=8, ge=0, le=23)
    cron_minute: int = Field(default=0, ge=0, le=59)
    cron_dow: str = "*"
    max_runs_per_day: int = Field(default=3, ge=1, le=10)
    retry_on_failure: bool = True
    max_retries: int = Field(default=2, ge=0, le=5)


class CampaignUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    niche: Optional[str] = Field(None, min_length=1, max_length=255)
    topic_instructions: Optional[str] = None
    target_platforms: Optional[List[str]] = None
    auto_publish: Optional[bool] = None
    schedule_preset: Optional[str] = None
    cron_hour: Optional[int] = Field(None, ge=0, le=23)
    cron_minute: Optional[int] = Field(None, ge=0, le=59)
    cron_dow: Optional[str] = None
    max_runs_per_day: Optional[int] = Field(None, ge=1, le=10)
    is_active: Optional[bool] = None
    retry_on_failure: Optional[bool] = None
    max_retries: Optional[int] = Field(None, ge=0, le=5)


# ── Tier gate helper ─────────────────────────────────────────────────────────

def _enforce_max_tier(user: User):
    """Raises 403 if the user is not on the Max tier."""
    tier = user.tier_level or "free"
    cfg = get_tier_config(tier)
    if not cfg.get("has_cron", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "tier_restricted",
                "message": "Autonomous campaigns require the Max plan.",
                "current_tier": tier,
                "required_tier": "max",
            },
        )


# ── Serializer ────────────────────────────────────────────────────────────────

def _serialize_campaign(c: AgentCampaign) -> dict:
    """Convert an AgentCampaign ORM instance to a JSON-safe dict."""
    return {
        "id": c.id,
        "name": c.name,
        "description": c.description,
        "niche": c.niche,
        "topic_instructions": c.topic_instructions,
        "target_platforms": c.target_platforms or [],
        "auto_publish": c.auto_publish,
        "schedule_preset": c.schedule_preset,
        "cron_hour": c.cron_hour,
        "cron_minute": c.cron_minute,
        "cron_dow": c.cron_dow,
        "max_runs_per_day": c.max_runs_per_day,
        "retry_on_failure": c.retry_on_failure,
        "max_retries": c.max_retries,
        "status": c.status,
        "is_active": c.is_active,
        "total_runs": c.total_runs or 0,
        "successful_runs": c.successful_runs or 0,
        "failed_runs": c.failed_runs or 0,
        "total_posts_published": c.total_posts_published or 0,
        "total_credits_consumed": c.total_credits_consumed or 0,
        "consecutive_failures": c.consecutive_failures or 0,
        "last_run_at": c.last_run_at.isoformat() if c.last_run_at else None,
        "next_run_at": c.next_run_at.isoformat() if c.next_run_at else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


def _serialize_run(r: AgentCampaignRun) -> dict:
    """Convert an AgentCampaignRun ORM instance to a JSON-safe dict."""
    return {
        "id": r.id,
        "run_id": r.run_id,
        "campaign_id": r.campaign_id,
        "status": r.status,
        "pipeline_node": r.pipeline_node,
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        "duration_seconds": r.duration_seconds,
        "article_title": r.article_title,
        "article_url": r.article_url,
        "auto_published": r.auto_published,
        "platform_results": r.platform_results,
        "credits_consumed": r.credits_consumed or 0,
        "video_model_used": r.video_model_used,
        "error_message": r.error_message,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


# ── APScheduler Helpers ──────────────────────────────────────────────────────

def _register_campaign_cron(campaign_id: int, hour: int, minute: int, dow: str):
    """Registers a per-campaign cron job in the global APScheduler instance."""
    from app.services.scheduler.engine import scheduler
    from app.services.scheduler.campaign_pipeline import run_campaign_pipeline

    job_id = f"campaign_cron_{campaign_id}"
    day_of_week = dow if dow != "*" else None

    scheduler.add_job(
        run_campaign_pipeline,
        trigger="cron",
        hour=hour,
        minute=minute,
        day_of_week=day_of_week,
        args=[campaign_id],
        id=job_id,
        replace_existing=True,
        misfire_grace_time=300,
    )
    logger.info(
        "[Campaign] Registered cron job '%s' at %02d:%02d dow=%s",
        job_id, hour, minute, dow,
    )


def _remove_campaign_cron(campaign_id: int):
    """Removes a per-campaign cron job from APScheduler."""
    from app.services.scheduler.engine import scheduler

    job_id = f"campaign_cron_{campaign_id}"
    try:
        scheduler.remove_job(job_id)
        logger.info("[Campaign] Removed cron job '%s'", job_id)
    except Exception:
        pass  # Job doesn't exist, that's fine


def _resolve_cron(payload) -> tuple:
    """Resolve schedule preset to (hour, minute, dow) tuple."""
    preset = getattr(payload, "schedule_preset", None) or "custom"
    if preset in PRESET_MAP:
        p = PRESET_MAP[preset]
        return p["hour"], p["minute"], p["dow"]
    return payload.cron_hour, payload.cron_minute, payload.cron_dow


# ==============================================================================
# CAMPAIGN CRUD ENDPOINTS
# ==============================================================================


# ── GET /campaigns ────────────────────────────────────────────────────────────

@router.get("")
async def list_campaigns(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    include_archived: bool = Query(False, description="Include archived campaigns"),
):
    """List all campaigns for the authenticated user."""
    _enforce_max_tier(current_user)

    query = select(AgentCampaign).where(
        AgentCampaign.user_id == current_user.id
    )
    if not include_archived:
        query = query.where(AgentCampaign.status != "archived")

    query = query.order_by(AgentCampaign.created_at.desc())
    result = await db.execute(query)
    campaigns = result.scalars().all()

    return {
        "campaigns": [_serialize_campaign(c) for c in campaigns],
        "total": len(campaigns),
    }


# ── GET /campaigns/{id} ──────────────────────────────────────────────────────

@router.get("/{campaign_id}")
async def get_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed campaign info including recent runs."""
    _enforce_max_tier(current_user)

    result = await db.execute(
        select(AgentCampaign).where(
            AgentCampaign.id == campaign_id,
            AgentCampaign.user_id == current_user.id,
        )
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    # Fetch recent runs (last 20)
    runs_result = await db.execute(
        select(AgentCampaignRun)
        .where(AgentCampaignRun.campaign_id == campaign_id)
        .order_by(AgentCampaignRun.started_at.desc())
        .limit(20)
    )
    runs = runs_result.scalars().all()

    return {
        "campaign": _serialize_campaign(campaign),
        "recent_runs": [_serialize_run(r) for r in runs],
    }


# ── POST /campaigns ──────────────────────────────────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_campaign(
    payload: CampaignCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new autonomous campaign and register its cron job."""
    _enforce_max_tier(current_user)

    # Limit total active campaigns per user (prevent abuse)
    count_result = await db.execute(
        select(func.count(AgentCampaign.id)).where(
            AgentCampaign.user_id == current_user.id,
            AgentCampaign.status.in_(["active", "paused"]),
        )
    )
    active_count = count_result.scalar() or 0
    if active_count >= 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum of 5 active campaigns allowed per user.",
        )

    # Validate platforms
    valid_platforms = {"twitter", "linkedin", "tiktok", "facebook", "instagram", "reddit"}
    invalid = set(payload.target_platforms) - valid_platforms
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid platforms: {', '.join(invalid)}",
        )

    # Resolve cron schedule
    hour, minute, dow = _resolve_cron(payload)

    campaign = AgentCampaign(
        user_id=current_user.id,
        name=payload.name,
        description=payload.description,
        niche=payload.niche,
        topic_instructions=payload.topic_instructions,
        target_platforms=payload.target_platforms,
        auto_publish=payload.auto_publish,
        schedule_preset=payload.schedule_preset,
        cron_hour=hour,
        cron_minute=minute,
        cron_dow=dow,
        max_runs_per_day=payload.max_runs_per_day,
        retry_on_failure=payload.retry_on_failure,
        max_retries=payload.max_retries,
        status="active",
        is_active=True,
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)

    # Register the cron job in APScheduler
    _register_campaign_cron(campaign.id, hour, minute, dow)

    logger.info(
        "[Campaign] Created campaign_id=%d for user_id=%d niche='%s' preset=%s",
        campaign.id, current_user.id, payload.niche, payload.schedule_preset,
    )

    return {
        "status": "created",
        "campaign": _serialize_campaign(campaign),
    }


# ── PUT /campaigns/{id} ──────────────────────────────────────────────────────

@router.put("/{campaign_id}")
async def update_campaign(
    campaign_id: int,
    payload: CampaignUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing campaign configuration."""
    _enforce_max_tier(current_user)

    result = await db.execute(
        select(AgentCampaign).where(
            AgentCampaign.id == campaign_id,
            AgentCampaign.user_id == current_user.id,
        )
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    # Apply partial updates
    update_fields = payload.model_dump(exclude_unset=True)

    # Handle schedule preset resolution
    schedule_changed = False
    if "schedule_preset" in update_fields:
        preset = update_fields["schedule_preset"]
        if preset in PRESET_MAP:
            p = PRESET_MAP[preset]
            update_fields["cron_hour"] = p["hour"]
            update_fields["cron_minute"] = p["minute"]
            update_fields["cron_dow"] = p["dow"]
        schedule_changed = True

    if any(k in update_fields for k in ["cron_hour", "cron_minute", "cron_dow"]):
        schedule_changed = True

    for key, value in update_fields.items():
        if hasattr(campaign, key):
            setattr(campaign, key, value)

    # Reset consecutive failures when manually reactivating
    if "is_active" in update_fields and update_fields["is_active"]:
        campaign.consecutive_failures = 0
        if campaign.status == "error_paused":
            campaign.status = "active"

    await db.commit()
    await db.refresh(campaign)

    # Re-register or remove cron job based on active state
    if campaign.is_active:
        _register_campaign_cron(
            campaign.id, campaign.cron_hour, campaign.cron_minute, campaign.cron_dow,
        )
    else:
        _remove_campaign_cron(campaign.id)

    logger.info("[Campaign] Updated campaign_id=%d", campaign.id)

    return {
        "status": "updated",
        "campaign": _serialize_campaign(campaign),
    }


# ── DELETE /campaigns/{id} ────────────────────────────────────────────────────

@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a campaign and its cron job. Run history is cascade-deleted."""
    _enforce_max_tier(current_user)

    result = await db.execute(
        select(AgentCampaign).where(
            AgentCampaign.id == campaign_id,
            AgentCampaign.user_id == current_user.id,
        )
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    _remove_campaign_cron(campaign.id)
    await db.delete(campaign)
    await db.commit()

    logger.info("[Campaign] Deleted campaign_id=%d user_id=%d", campaign_id, current_user.id)

    return {"status": "deleted", "campaign_id": campaign_id}


# ── POST /campaigns/{id}/pause ────────────────────────────────────────────────

@router.post("/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Pause an active campaign without deleting it."""
    _enforce_max_tier(current_user)

    result = await db.execute(
        select(AgentCampaign).where(
            AgentCampaign.id == campaign_id,
            AgentCampaign.user_id == current_user.id,
        )
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    campaign.is_active = False
    campaign.status = "paused"
    _remove_campaign_cron(campaign.id)

    await db.commit()
    await db.refresh(campaign)

    return {"status": "paused", "campaign": _serialize_campaign(campaign)}


# ── POST /campaigns/{id}/resume ───────────────────────────────────────────────

@router.post("/{campaign_id}/resume")
async def resume_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resume a paused campaign."""
    _enforce_max_tier(current_user)

    result = await db.execute(
        select(AgentCampaign).where(
            AgentCampaign.id == campaign_id,
            AgentCampaign.user_id == current_user.id,
        )
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    campaign.is_active = True
    campaign.status = "active"
    campaign.consecutive_failures = 0

    _register_campaign_cron(
        campaign.id, campaign.cron_hour, campaign.cron_minute, campaign.cron_dow,
    )

    await db.commit()
    await db.refresh(campaign)

    return {"status": "resumed", "campaign": _serialize_campaign(campaign)}


# ── GET /campaigns/{id}/runs ──────────────────────────────────────────────────

@router.get("/{campaign_id}/runs")
async def list_campaign_runs(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Paginated list of runs for a specific campaign."""
    _enforce_max_tier(current_user)

    # Verify ownership
    campaign_result = await db.execute(
        select(AgentCampaign.id).where(
            AgentCampaign.id == campaign_id,
            AgentCampaign.user_id == current_user.id,
        )
    )
    if not campaign_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Campaign not found.")

    # Count total
    count_result = await db.execute(
        select(func.count(AgentCampaignRun.id)).where(
            AgentCampaignRun.campaign_id == campaign_id,
        )
    )
    total = count_result.scalar() or 0

    # Fetch page
    runs_result = await db.execute(
        select(AgentCampaignRun)
        .where(AgentCampaignRun.campaign_id == campaign_id)
        .order_by(AgentCampaignRun.started_at.desc())
        .limit(limit)
        .offset(offset)
    )
    runs = runs_result.scalars().all()

    return {
        "runs": [_serialize_run(r) for r in runs],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
