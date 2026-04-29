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
from app.core.verification import require_verified_email
from app.models.user import User
from app.models.content import AssetLibrary
from app.models.post import Post, PostResult
from app.services.social_service import SocialService

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
        require_verified_email(current_user)
        if asset.status == "published":
            raise HTTPException(status_code=409, detail="Asset is already published.")
        if asset.status == "scheduled":
            raise HTTPException(status_code=409, detail="Asset is scheduled and cannot be approved directly.")

        requested_platforms = payload.platforms or asset.platforms_used or []
        normalized_platforms: list[str] = []
        for platform in requested_platforms:
            key = str(platform or "").strip().lower()
            if key and key not in normalized_platforms:
                normalized_platforms.append(key)

        drafts = asset.platform_drafts or {}
        normalized_drafts = {
            str(platform).strip().lower(): text
            for platform, text in drafts.items()
            if str(platform).strip()
        }

        # If no explicit platform list was supplied, infer from draft keys.
        if not normalized_platforms:
            normalized_platforms = [p for p in normalized_drafts.keys() if p]

        if not normalized_platforms:
            raise HTTPException(
                status_code=400,
                detail="No platforms selected for approval/publish.",
            )

        content_fallback = (asset.text_content or "").strip()
        content_map: dict[str, str] = {}
        for platform in normalized_platforms:
            text = (normalized_drafts.get(platform) or "").strip()
            if not text:
                text = content_fallback
            if not text:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing draft content for platform '{platform}'.",
                )
            content_map[platform] = text

        video_urls = (
            [asset.content_url]
            if asset.content_url and asset.asset_type in ("video", "bundle")
            else None
        )

        post = Post(
            user_id=current_user.id,
            original_content=content_fallback or "Review queue publish",
            enhanced_content=normalized_drafts or None,
            platform_specific_content=content_map,
            video_urls=",".join(video_urls) if video_urls else None,
            platforms=",".join(normalized_platforms),
            status="published",
        )
        db.add(post)
        await db.flush()

        results = await SocialService.publish_post(
            db=db,
            user_id=current_user.id,
            content_map=content_map,
            video_urls=video_urls,
        )

        successful = 0
        details = []
        for result_item in results:
            if result_item.success:
                successful += 1

            db.add(
                PostResult(
                    post_id=post.id,
                    platform=result_item.platform,
                    status="published" if result_item.success else "failed",
                    platform_post_id=result_item.post_id,
                    platform_post_url=result_item.post_url,
                    content_used=content_map.get(result_item.platform.lower()),
                    error_message=result_item.error,
                )
            )
            details.append(result_item.to_dict())

        if successful > 0:
            asset.status = "published"
            asset.published_at = datetime.utcnow()
        else:
            asset.status = "failed"
            post.status = "failed"

        asset.platforms_used = normalized_platforms

        logger.info(
            "[ReviewQueue] asset_id=%d APPROVED by user_id=%d success=%d/%d",
            asset_id,
            current_user.id,
            successful,
            len(results),
        )
        await db.commit()
        await db.refresh(asset)
        return {
            **_serialize_asset(asset),
            "publish_results": details,
            "published_successful": successful,
            "published_failed": len(results) - successful,
            "post_id": post.id,
        }

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
