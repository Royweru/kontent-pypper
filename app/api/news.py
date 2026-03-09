from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Dict, Any

from app.core.database import get_db
from app.models.content_source import ContentItem

router = APIRouter()

@router.get("/feed", response_model=List[Dict[str, Any]])
async def get_news_feed(
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns the latest fetched news/content items for dashboard display.
    Ordered by relevance score and ID.
    """
    stmt = (
        select(ContentItem)
        .order_by(ContentItem.relevance_score.desc(), ContentItem.id.desc())
        .limit(limit)
    )
    
    results = (await db.execute(stmt)).scalars().all()
    
    feed = []
    for item in results:
        feed.append({
            "id": item.id,
            "title": item.title,
            "url": item.url,
            "source_name": item.source_name,
            "source_type": item.source_type,
            "snippet": item.snippet[:150] + "..." if item.snippet else "",
            "relevance_score": item.relevance_score,
            "is_used": item.is_used,
            "published_date": item.published_date
        })
        
    return feed

from pydantic import BaseModel
from sqlalchemy import delete
from app.api.deps import get_current_user
from app.models.user import User
from app.models.content import ContentSource

class AddFeedRequest(BaseModel):
    title: str
    url: str

@router.get("/feed/sources", response_model=List[Dict[str, Any]])
async def get_feed_sources(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(ContentSource).where(ContentSource.user_id == current_user.id)
    results = (await db.execute(stmt)).scalars().all()
    return [{"id": r.id, "title": r.source_name, "url": r.rss_feed_url} for r in results]

@router.post("/feed/sources")
async def add_feed_source(
    req: AddFeedRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(ContentSource).where(ContentSource.user_id == current_user.id)
    results = (await db.execute(stmt)).scalars().all()
    
    if current_user.plan == "free" and len(results) >= 5:
        raise HTTPException(status_code=400, detail="Free plan limited to 5 feeds. Please upgrade to Pro.")
        
    new_source = ContentSource(
        user_id=current_user.id,
        source_type="rss",
        source_name=req.title,
        rss_feed_url=req.url
    )
    db.add(new_source)
    await db.commit()
    return {"status": "success"}

@router.delete("/feed/sources")
async def remove_feed_source(
    url: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(ContentSource).where(
        ContentSource.user_id == current_user.id,
        ContentSource.rss_feed_url == url
    )
    results = (await db.execute(stmt)).scalars().all()
    for result in results:
        await db.delete(result)
    await db.commit()
    return {"status": "success"}
