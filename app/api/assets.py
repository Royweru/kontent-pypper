from typing import Optional, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.database import get_db
from app.models.content import AssetLibrary
from app.models.user import User

router = APIRouter()


class AssetCreate(BaseModel):
    asset_type: str = "video"
    title: Optional[str] = "Untitled Asset"
    content_url: Optional[str] = None
    text_content: Optional[str] = None
    platforms_used: List[str] = Field(default_factory=list)
    status: Optional[str] = None
    platform_drafts: Optional[dict] = None
    video_script_data: Optional[dict] = None
    source_article_title: Optional[str] = None
    source_article_url: Optional[str] = None
    video_model_used: Optional[str] = None
    credits_consumed: Optional[int] = 0
    workflow_run_id: Optional[str] = None


def _serialize_asset(asset: AssetLibrary) -> dict:
    return {
        "id": asset.id,
        "asset_type": asset.asset_type,
        "title": asset.title,
        "content_url": asset.content_url,
        "text_content": asset.text_content,
        "status": asset.status,
        "platforms_used": asset.platforms_used or [],
        "platform_drafts": asset.platform_drafts or {},
        "video_script_data": asset.video_script_data,
        "source_article_title": asset.source_article_title,
        "source_article_url": asset.source_article_url,
        "video_model_used": asset.video_model_used,
        "credits_consumed": asset.credits_consumed or 0,
        "workflow_run_id": asset.workflow_run_id,
        "is_favorite": bool(asset.is_favorite),
        "scheduled_publish_at": (
            asset.scheduled_publish_at.isoformat() if asset.scheduled_publish_at else None
        ),
        "published_at": asset.published_at.isoformat() if asset.published_at else None,
        "rejected_at": asset.rejected_at.isoformat() if asset.rejected_at else None,
        "created_at": asset.created_at.isoformat() if asset.created_at else None,
        "updated_at": asset.updated_at.isoformat() if asset.updated_at else None,
    }


@router.post("", tags=["Media & Assets"])
@router.post("/assets", tags=["Media & Assets"])
async def save_asset(
    payload: AssetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Saves workflow output assets (video, text) to the central Asset Library."""
    status = payload.status or "pending_review"
    asset = AssetLibrary(
        user_id=current_user.id,
        asset_type=payload.asset_type,
        title=payload.title,
        content_url=payload.content_url,
        text_content=payload.text_content,
        platforms_used=payload.platforms_used,
        status=status,
        platform_drafts=payload.platform_drafts,
        video_script_data=payload.video_script_data,
        source_article_title=payload.source_article_title,
        source_article_url=payload.source_article_url,
        video_model_used=payload.video_model_used,
        credits_consumed=payload.credits_consumed or 0,
        workflow_run_id=payload.workflow_run_id,
    )

    db.add(asset)
    await db.commit()
    await db.refresh(asset)

    return {
        "status": "success",
        "asset_id": asset.id,
        "asset": _serialize_asset(asset),
    }


@router.get("", tags=["Media & Assets"])
@router.get("/assets", tags=["Media & Assets"])
async def get_assets(
    limit: int = 50,
    offset: int = 0,
    asset_type: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves all saved assets for the user."""
    query = select(AssetLibrary).where(AssetLibrary.user_id == current_user.id)

    if asset_type:
        query = query.where(AssetLibrary.asset_type == asset_type)
    if status:
        query = query.where(AssetLibrary.status == status)

    query = query.order_by(desc(AssetLibrary.created_at)).limit(limit).offset(offset)
    result = await db.execute(query)
    assets = result.scalars().all()

    return [_serialize_asset(asset) for asset in assets]
