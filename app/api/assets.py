from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.deps import get_current_user
from app.core.database import get_db
from app.models.content import AssetLibrary
from app.models.user import User

router = APIRouter()

@router.post("/assets", tags=["Media & Assets"])
async def save_asset(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Saves workflow output assets (video, text) to the central Asset Library."""
    
    asset = AssetLibrary(
        user_id=current_user.id,
        asset_type=payload.get("asset_type", "video"),
        title=payload.get("title", "Untitled Asset"),
        content_url=payload.get("content_url"),
        text_content=payload.get("text_content"),
        platforms_used=payload.get("platforms_used", [])
    )
    
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    
    return {"status": "success", "asset_id": asset.id}

@router.get("/assets", tags=["Media & Assets"])
async def get_assets(
    limit: int = 50,
    offset: int = 0,
    asset_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves all saved assets for the user."""
    query = select(AssetLibrary).where(AssetLibrary.user_id == current_user.id)
    
    if asset_type:
        query = query.where(AssetLibrary.asset_type == asset_type)
        
    query = query.order_by(AssetLibrary.created_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    assets = result.scalars().all()
    
    return assets
