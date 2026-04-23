"""
KontentPyper - Review Queue API
Endpoints for the web-first Human-in-the-Loop approval system.
Lists, approves, rejects, and schedules pipeline-generated content.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.content import AssetLibrary

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class ReviewAction(BaseModel):
    action: str  # approve | reject | schedule
    platforms: Optional[List[str]] = None  # Which platforms to publish to
    scheduled_at: Optional[str] = None     # ISO datetime for scheduling
    rejection_reason: Optional[str] = None


class DraftUpdate(BaseModel):
    platform: str
    text: str


# ── GET /review/queue ─────────────────────────────────────────────────────────

@router.get("/queue")
async def get_review_queue(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    status_filter: str = "pending_review",
):
    """
    Returns all assets awaiting review for the authenticated user.
    Supports filtering by status: pending_review, approved, published, rejected, scheduled
    """
    query = (
        select(AssetLibrary)
        .where(
            AssetLibrary.user_id == current_user.id,
            AssetLibrary.status == status_filter,
        )
        .order_by(desc(AssetLibrary.created_at))
    )

    result = await db.execute(query)
    assets = result.scalars().all()

    return [_serialize_asset(a) for a in assets]


# ── GET /review/queue/count ───────────────────────────────────────────────────

@router.get("/queue/count")
async def get_review_queue_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns count of pending_review items (for badge notification)."""
    from sqlalchemy import func

    result = await db.execute(
        select(func.count(AssetLibrary.id)).where(
            AssetLibrary.user_id == current_user.id,
            AssetLibrary.status == "pending_review",
        )
    )
    count = result.scalar() or 0

    return {"pending_count": count}


# ── GET /review/{asset_id} ────────────────────────────────────────────────────

@router.get("/{asset_id}")
async def get_review_detail(
    asset_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns full detail of a single asset for the review page."""
    result = await db.execute(
        select(AssetLibrary).where(
            AssetLibrary.id == asset_id,
            AssetLibrary.user_id == current_user.id,
        )
    )
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found.")

    return _serialize_asset(asset)


# ── POST /review/{asset_id}/action ────────────────────────────────────────────

@router.post("/{asset_id}/action")
async def perform_review_action(
    asset_id: int,
    payload: ReviewAction,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Performs an action on a review queue item:
      - approve:  Mark as approved, set platforms, trigger publish
      - reject:   Mark as rejected with optional reason
      - schedule: Mark as scheduled with a publish datetime
    """
    result = await db.execute(
        select(AssetLibrary).where(
            AssetLibrary.id == asset_id,
            AssetLibrary.user_id == current_user.id,
        )
    )
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found.")

    action = payload.action.lower()

    if action == "approve":
        asset.status = "approved"
        if payload.platforms:
            asset.platforms_used = payload.platforms
        asset.published_at = datetime.utcnow()

        # TODO: Trigger actual platform publishing via SocialService
        # For now, mark as published immediately
        asset.status = "published"

        logger.info("[ReviewQueue] asset_id=%d APPROVED by user_id=%d", asset_id, current_user.id)

    elif action == "reject":
        asset.status = "rejected"
        asset.rejected_at = datetime.utcnow()
        asset.rejection_reason = payload.rejection_reason or "Rejected by user"

        logger.info("[ReviewQueue] asset_id=%d REJECTED by user_id=%d", asset_id, current_user.id)

    elif action == "schedule":
        if not payload.scheduled_at:
            raise HTTPException(status_code=400, detail="scheduled_at is required for scheduling.")

        try:
            scheduled_dt = datetime.fromisoformat(payload.scheduled_at.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid datetime format. Use ISO 8601.")

        asset.status = "scheduled"
        asset.scheduled_publish_at = scheduled_dt
        asset.platforms_used = payload.platforms or asset.platforms_used

        logger.info(
            "[ReviewQueue] asset_id=%d SCHEDULED for %s by user_id=%d",
            asset_id, scheduled_dt.isoformat(), current_user.id,
        )

    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

    await db.commit()
    await db.refresh(asset)

    return _serialize_asset(asset)


# ── PUT /review/{asset_id}/draft ──────────────────────────────────────────────

@router.put("/{asset_id}/draft")
async def update_draft_text(
    asset_id: int,
    payload: DraftUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Updates the draft text for a specific platform in the review item."""
    result = await db.execute(
        select(AssetLibrary).where(
            AssetLibrary.id == asset_id,
            AssetLibrary.user_id == current_user.id,
        )
    )
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found.")

    drafts = asset.platform_drafts or {}
    drafts[payload.platform] = payload.text
    asset.platform_drafts = drafts

    # Force SQLAlchemy to detect JSON mutation
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(asset, "platform_drafts")

    await db.commit()

    return {"status": "ok", "platform": payload.platform}


# ── Serializer ────────────────────────────────────────────────────────────────

def _serialize_asset(a: AssetLibrary) -> dict:
    """Converts an AssetLibrary ORM object to a JSON-safe dict."""
    return {
        "id": a.id,
        "asset_type": a.asset_type,
        "title": a.title,
        "content_url": a.content_url,
        "text_content": a.text_content,
        "status": a.status,
        "platform_drafts": a.platform_drafts,
        "video_script_data": a.video_script_data,
        "source_article_title": a.source_article_title,
        "source_article_url": a.source_article_url,
        "video_model_used": a.video_model_used,
        "credits_consumed": a.credits_consumed,
        "platforms_used": a.platforms_used,
        "scheduled_publish_at": a.scheduled_publish_at.isoformat() if a.scheduled_publish_at else None,
        "published_at": a.published_at.isoformat() if a.published_at else None,
        "rejected_at": a.rejected_at.isoformat() if a.rejected_at else None,
        "rejection_reason": a.rejection_reason,
        "workflow_run_id": a.workflow_run_id,
        "is_favorite": a.is_favorite,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }
