from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Dict, Any, Optional

from pydantic import BaseModel
from sqlalchemy import delete

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.content_source import ContentItem
from app.models.user import User
from app.models.content import ContentSource

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AddFeedRequest(BaseModel):
    title: str           # Display name, maps to ContentSource.source_name
    url: str             # RSS feed URL, maps to ContentSource.rss_feed_url
    source_type: str = "rss"   # "rss" | "reddit"
    logo_url: Optional[str] = None
    category: Optional[str] = None
    subreddit_name: Optional[str] = None


# ---------------------------------------------------------------------------
# Public feed endpoint (dashboard article list)
# ---------------------------------------------------------------------------

@router.get("/feed", response_model=List[Dict[str, Any]])
async def get_news_feed(
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns the latest fetched news/content items for dashboard display.
    Ordered by relevance score descending then id descending.
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
            "snippet": item.snippet[:150] + "..." if item.snippet and len(item.snippet) > 150 else (item.snippet or ""),
            "relevance_score": item.relevance_score,
            "is_used": item.is_used,
            "published_date": item.published_date,
        })

    return feed


# ---------------------------------------------------------------------------
# User feed sources (authenticated)
# ---------------------------------------------------------------------------

@router.get("/feed/sources", response_model=List[Dict[str, Any]])
async def get_feed_sources(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns all content sources the current user has added."""
    stmt = select(ContentSource).where(ContentSource.user_id == current_user.id)
    results = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": r.id,
            "title": r.source_name or r.rss_feed_url or r.subreddit_name or "",
            "url": r.rss_feed_url or "",
            "source_type": r.source_type,
            "logo_url": r.logo_url or "",
            "category": r.category or "",
            "subreddit_name": r.subreddit_name or "",
            "is_active": r.is_active,
            "last_fetched": r.last_fetched,
        }
        for r in results
    ]


@router.post("/feed/sources")
async def add_feed_source(
    req: AddFeedRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Adds a content source for the current user.
    Free plan limits:
      - RSS feeds  : max 5
      - Subreddits : max 2
    """
    all_sources = (
        await db.execute(
            select(ContentSource).where(ContentSource.user_id == current_user.id)
        )
    ).scalars().all()

    if current_user.plan == "free":
        rss_count = sum(1 for s in all_sources if s.source_type == "rss")
        reddit_count = sum(1 for s in all_sources if s.source_type == "reddit")

        if req.source_type == "rss" and rss_count >= 5:
            raise HTTPException(
                status_code=400,
                detail="Free plan is limited to 5 RSS feeds. Upgrade to Pro for unlimited sources."
            )
        if req.source_type == "reddit" and reddit_count >= 2:
            raise HTTPException(
                status_code=400,
                detail="Free plan is limited to 2 subreddits. Upgrade to Pro for unlimited sources."
            )

    new_source = ContentSource(
        user_id=current_user.id,
        source_type=req.source_type,
        source_name=req.title,            # Fixed: now maps to valid column
        rss_feed_url=req.url if req.source_type == "rss" else None,
        subreddit_name=req.subreddit_name if req.source_type == "reddit" else None,
        logo_url=req.logo_url,
        category=req.category,
        is_active=True,
    )
    db.add(new_source)
    await db.commit()
    await db.refresh(new_source)
    return {"status": "success", "id": new_source.id}


@router.delete("/feed/sources/{source_id}")
async def remove_feed_source(
    source_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Removes a content source by ID (must belong to current user)."""
    stmt = select(ContentSource).where(
        ContentSource.user_id == current_user.id,
        ContentSource.id == source_id
    )
    result = (await db.execute(stmt)).scalar_one_or_none()
    if not result:
        raise HTTPException(status_code=404, detail="Source not found.")
    await db.delete(result)
    await db.commit()
    return {"status": "success"}
