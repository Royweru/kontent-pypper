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
