"""
KontentPyper - Schedule API
CRUD endpoints for managing user automation schedules (Max tier only).
"""

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.schedule import ScheduledJob
from app.services.credit_service import get_tier_config

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class ScheduleUpdate(BaseModel):
    schedule_preset: str = "daily_8am"  # daily_8am | daily_12pm | daily_6pm | weekdays_9am | custom
    cron_hour: int = 8
    cron_minute: int = 0
    cron_dow: str = "*"
    is_active: bool = False


PRESET_MAP = {
    "daily_8am":    {"hour": 8,  "minute": 0, "dow": "*"},
    "daily_12pm":   {"hour": 12, "minute": 0, "dow": "*"},
    "daily_6pm":    {"hour": 18, "minute": 0, "dow": "*"},
    "weekdays_9am": {"hour": 9,  "minute": 0, "dow": "mon,tue,wed,thu,fri"},
}


# ── GET /schedule ─────────────────────────────────────────────────────────────

@router.get("")
async def get_schedule(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns the user's current schedule configuration."""
    result = await db.execute(
        select(ScheduledJob).where(ScheduledJob.user_id == current_user.id)
    )
    job = result.scalar_one_or_none()

    tier = current_user.tier_level or "free"
    cfg = get_tier_config(tier)

    if not job:
        return {
            "has_schedule": False,
            "is_active": False,
            "schedule_preset": "daily_8am",
            "cron_hour": 8,
            "cron_minute": 0,
            "cron_dow": "*",
            "last_run_at": None,
            "next_run_at": None,
            "total_runs": 0,
            "last_run_status": None,
            "tier": tier,
            "cron_allowed": cfg.get("has_cron", False),
        }

    return {
        "has_schedule": True,
        "is_active": job.is_active,
        "schedule_preset": job.schedule_preset or "daily_8am",
        "cron_hour": job.cron_hour,
        "cron_minute": job.cron_minute,
        "cron_dow": job.cron_dow,
        "last_run_at": job.last_run_at.isoformat() if job.last_run_at else None,
        "next_run_at": job.next_run_at.isoformat() if job.next_run_at else None,
        "total_runs": job.total_runs or 0,
        "last_run_status": job.last_run_status,
        "tier": tier,
        "cron_allowed": cfg.get("has_cron", False),
    }


# ── PUT /schedule ─────────────────────────────────────────────────────────────

@router.put("")
async def update_schedule(
    payload: ScheduleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Creates or updates the user's automation schedule. Max tier only."""
    tier = current_user.tier_level or "free"
    cfg = get_tier_config(tier)

    if not cfg.get("has_cron", False):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "tier_restricted",
                "message": "Scheduled automation requires the Max plan.",
                "current_tier": tier,
                "required_tier": "max",
            },
        )

    # Resolve preset to cron values
    preset = payload.schedule_preset
    if preset in PRESET_MAP:
        cron_vals = PRESET_MAP[preset]
        hour = cron_vals["hour"]
        minute = cron_vals["minute"]
        dow = cron_vals["dow"]
    else:
        hour = payload.cron_hour
        minute = payload.cron_minute
        dow = payload.cron_dow

    # Upsert the schedule
    result = await db.execute(
        select(ScheduledJob).where(ScheduledJob.user_id == current_user.id)
    )
    job = result.scalar_one_or_none()

    if not job:
        job = ScheduledJob(user_id=current_user.id)
        db.add(job)

    job.schedule_preset = preset
    job.cron_hour = hour
    job.cron_minute = minute
    job.cron_dow = dow
    job.is_active = payload.is_active

    await db.commit()
    await db.refresh(job)

    # Re-register APScheduler job if active
    if job.is_active:
        _register_user_cron(current_user.id, hour, minute, dow)
    else:
        _remove_user_cron(current_user.id)

    logger.info(
        "[Schedule] user_id=%d updated schedule: preset=%s, active=%s",
        current_user.id, preset, job.is_active,
    )

    return {
        "status": "ok",
        "is_active": job.is_active,
        "schedule_preset": job.schedule_preset,
        "cron_hour": job.cron_hour,
        "cron_minute": job.cron_minute,
        "cron_dow": job.cron_dow,
    }


# ── DELETE /schedule ──────────────────────────────────────────────────────────

@router.delete("")
async def delete_schedule(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Removes the user's automation schedule entirely."""
    result = await db.execute(
        select(ScheduledJob).where(ScheduledJob.user_id == current_user.id)
    )
    job = result.scalar_one_or_none()

    if job:
        _remove_user_cron(current_user.id)
        await db.delete(job)
        await db.commit()

    return {"status": "ok", "message": "Schedule removed."}


# ── APScheduler Helpers ───────────────────────────────────────────────────────

def _register_user_cron(user_id: int, hour: int, minute: int, dow: str):
    """Registers a per-user cron job in the global APScheduler instance."""
    from app.services.scheduler.engine import scheduler
    from app.services.scheduler.headless_pipeline import run_headless_pipeline

    job_id = f"user_cron_{user_id}"

    # Convert dow string to APScheduler format
    day_of_week = dow if dow != "*" else None

    scheduler.add_job(
        run_headless_pipeline,
        trigger="cron",
        hour=hour,
        minute=minute,
        day_of_week=day_of_week,
        args=[user_id],
        id=job_id,
        replace_existing=True,
        misfire_grace_time=300,
    )
    logger.info("[Schedule] Registered cron job '%s' at %02d:%02d dow=%s", job_id, hour, minute, dow)


def _remove_user_cron(user_id: int):
    """Removes a per-user cron job from APScheduler."""
    from app.services.scheduler.engine import scheduler

    job_id = f"user_cron_{user_id}"
    try:
        scheduler.remove_job(job_id)
        logger.info("[Schedule] Removed cron job '%s'", job_id)
    except Exception:
        pass  # Job doesn't exist, that's fine
