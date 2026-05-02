import asyncio
import ipaddress
import re
import socket
import time
from collections import defaultdict, deque
from datetime import datetime
from time import mktime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import feedparser
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from pydantic import BaseModel
from sqlalchemy import delete

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.content_source import ContentItem
from app.models.user import User
from app.models.content import ContentSource
from app.services.credit_service import get_tier_config
from sqlalchemy import or_

router = APIRouter()


PREVIEW_MAX_REQUESTS_PER_MINUTE = 45
PREVIEW_RATE_WINDOW_SECONDS = 60
PREVIEW_MAX_REDIRECTS = 3
PREVIEW_MAX_BYTES = 2 * 1024 * 1024  # 2 MB
PREVIEW_TIMEOUT = httpx.Timeout(8.0, connect=3.0)

_preview_rate_buckets: dict[str, deque[float]] = defaultdict(deque)

_BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "0.0.0.0",
    "::",
    "::1",
}
_BLOCKED_HOST_SUFFIXES = (
    ".local",
    ".internal",
    ".lan",
    ".home",
)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _enforce_preview_rate_limit(request: Request) -> None:
    now = time.monotonic()
    bucket = _preview_rate_buckets[_client_ip(request)]
    cutoff = now - PREVIEW_RATE_WINDOW_SECONDS
    while bucket and bucket[0] < cutoff:
        bucket.popleft()
    if len(bucket) >= PREVIEW_MAX_REQUESTS_PER_MINUTE:
        raise HTTPException(
            status_code=429,
            detail="Too many preview requests. Please retry shortly.",
        )
    bucket.append(now)


def _is_disallowed_ip(ip_value: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_value)
    except ValueError:
        return True
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _validate_preview_url_shape(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="Only http/https feed URLs are allowed.")
    if not parsed.hostname:
        raise HTTPException(status_code=400, detail="Feed URL is missing a hostname.")

    host = parsed.hostname.lower().strip(".")
    if host in _BLOCKED_HOSTNAMES or any(host.endswith(suffix) for suffix in _BLOCKED_HOST_SUFFIXES):
        raise HTTPException(status_code=400, detail="Host is not allowed for preview.")
    return host


async def _resolve_public_host(host: str) -> None:
    try:
        infos = await asyncio.to_thread(socket.getaddrinfo, host, None)
    except socket.gaierror as exc:
        raise HTTPException(status_code=400, detail=f"Could not resolve host '{host}'.") from exc

    addresses = {info[4][0] for info in infos if info and len(info) >= 5 and info[4]}
    if not addresses:
        raise HTTPException(status_code=400, detail="Host did not resolve to any address.")

    for ip_value in addresses:
        if _is_disallowed_ip(ip_value):
            raise HTTPException(status_code=400, detail="Preview URL resolved to a non-public address.")


async def _guard_preview_url(url: str) -> None:
    host = _validate_preview_url_shape(url)
    await _resolve_public_host(host)


async def _fetch_feed_document(url: str) -> tuple[bytes, str]:
    current_url = url
    headers = {"User-Agent": "KontentPyper/1.0 (+feed-preview)"}

    async with httpx.AsyncClient(timeout=PREVIEW_TIMEOUT, follow_redirects=False) as client:
        for _ in range(PREVIEW_MAX_REDIRECTS + 1):
            await _guard_preview_url(current_url)
            try:
                async with client.stream("GET", current_url, headers=headers) as resp:
                    status = resp.status_code
                    if 300 <= status < 400:
                        location = resp.headers.get("location")
                        if not location:
                            raise HTTPException(status_code=502, detail="Feed provider returned an invalid redirect.")
                        current_url = urljoin(current_url, location)
                        continue
                    if status >= 400:
                        raise HTTPException(
                            status_code=502,
                            detail=f"Feed provider returned HTTP {status}.",
                        )

                    body_chunks: list[bytes] = []
                    total = 0
                    async for chunk in resp.aiter_bytes():
                        total += len(chunk)
                        if total > PREVIEW_MAX_BYTES:
                            raise HTTPException(
                                status_code=413,
                                detail="Feed preview payload is too large.",
                            )
                        body_chunks.append(chunk)
                    return b"".join(body_chunks), current_url
            except HTTPException:
                raise
            except httpx.TimeoutException as exc:
                raise HTTPException(status_code=504, detail="Feed preview request timed out.") from exc
            except httpx.HTTPError as exc:
                raise HTTPException(status_code=502, detail=f"Failed to fetch feed: {exc}") from exc

    raise HTTPException(status_code=400, detail="Too many redirects while fetching feed preview.")


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

class ContentItemUpdate(BaseModel):
    is_used: bool



# ---------------------------------------------------------------------------
# Public feed endpoint (dashboard article list)
# ---------------------------------------------------------------------------

@router.get("/feed", response_model=List[Dict[str, Any]])
async def get_news_feed(
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns the latest fetched news/content items for dashboard display.
    Ordered by relevance score descending then id descending.
    """
    stmt = (
        select(ContentItem)
        .where(ContentItem.is_used == False)
        .where(or_(ContentItem.user_id == current_user.id, ContentItem.user_id.is_(None)))
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


@router.patch("/feed/items/{item_id}")
async def update_content_item(
    item_id: int,
    req: ContentItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Marks a content item as used (or unused)."""
    stmt = select(ContentItem).where(
        ContentItem.id == item_id,
        or_(ContentItem.user_id == current_user.id, ContentItem.user_id.is_(None))
    )
    item = (await db.execute(stmt)).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    item.is_used = req.is_used
    await db.commit()
    return {"status": "success", "is_used": item.is_used}



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
    Free tier limits:
      - RSS feeds  : max 5
      - Subreddits : max 2
    """
    all_sources = (
        await db.execute(
            select(ContentSource).where(ContentSource.user_id == current_user.id)
        )
    ).scalars().all()

    tier = (current_user.tier_level or "free").lower()
    cfg = get_tier_config(tier)
    if tier == "free":
        rss_count = sum(1 for s in all_sources if s.source_type == "rss")
        reddit_count = sum(1 for s in all_sources if s.source_type == "reddit")
        max_rss = cfg.get("max_feeds") or 5
        max_reddit = 2

        if req.source_type == "rss" and rss_count >= max_rss:
            raise HTTPException(
                status_code=400,
                detail=f"Free tier is limited to {max_rss} RSS feeds. Upgrade to Pro for unlimited sources."
            )
        if req.source_type == "reddit" and reddit_count >= max_reddit:
            raise HTTPException(
                status_code=400,
                detail=f"Free tier is limited to {max_reddit} subreddits. Upgrade to Pro for unlimited sources."
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


# ---------------------------------------------------------------------------
# Phase 3 — Curated Catalogue & Live Previews
# ---------------------------------------------------------------------------

@router.get("/catalogue")
async def get_feed_catalogue(
    category: Optional[str] = Query(None, description="Filter by category slug (tech, business, news, entertainment, real_estate, science, art_media)"),
):
    """
    Returns the curated feed catalogue for the Explore Feeds modal.

    No authentication required — used to populate the discover UI.

    Query params:
      category (optional): one of tech | business | news | entertainment | real_estate | science | art_media
                           If omitted, returns all categories + all feeds.

    Response shape:
      {
        "categories": [{slug, label, icon}, ...],
        "rss":        [{name, url, logo_url, category, description, source_type}, ...],
        "subreddits": [{name, subreddit, logo_url, category, description, source_type}, ...]
      }

    Pipeline integration (Phase 6):
      The 10x Pipeline will call this endpoint to offer users a source picker
      before auto-fetching and scoring content for batch generation.
    """
    from app.data.feed_catalogue import get_full_catalogue, get_catalogue_by_category
    if category:
        return get_catalogue_by_category(category)
    return get_full_catalogue()


@router.get("/feed/preview")
async def preview_rss_feed(
    request: Request,
    url: str = Query(..., description="RSS feed URL to preview"),
):
    """
    Live proxy: fetches up to 10 articles from any RSS URL and returns
    normalized cards (thumbnail, title, snippet, pubDate, source_url).

    No authentication required.

    Used by:
      - Explore Feeds modal: show sample articles before user adds a feed.
      - Autonomous pipeline (Phase 6): seed test articles for a new source.

    Returns a list of article cards:
      [{title, url, snippet, image_url, published_date, source_url}]
    """
    _enforce_preview_rate_limit(request)
    feed_bytes, resolved_url = await _fetch_feed_document(url)
    feed = feedparser.parse(feed_bytes)

    if not feed.entries:
        return []

    articles = []
    for entry in feed.entries[:10]:
        pub_date = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            pub_date = datetime.fromtimestamp(mktime(entry.published_parsed)).isoformat()

        snippet = ""
        if hasattr(entry, "summary"):
            snippet = re.sub(r"<[^>]+>", "", entry.summary)[:300]

        image_url = None
        if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
            image_url = entry.media_thumbnail[0].get("url")
        elif hasattr(entry, "media_content") and entry.media_content:
            image_url = entry.media_content[0].get("url")

        articles.append({
            "title":          entry.title,
            "url":            entry.link,
            "snippet":        snippet,
            "image_url":      image_url,
            "published_date": pub_date,
            "source_url":     resolved_url,
        })

    return articles


@router.get("/subreddit/preview")
async def preview_subreddit(
    request: Request,
    sub: str = Query(..., description="Subreddit name WITHOUT r/ prefix"),
    limit: int = Query(10, ge=1, le=25),
):
    """
    Returns hot posts from any public subreddit.

    No authentication required.

    Used by:
      - Explore Feeds modal Reddit tab: preview posts before adding a subreddit.
      - Autonomous pipeline (Phase 6): live source picker for content generation.

    Returns a list of post cards:
      [{title, url, snippet, image_url, published_date, score, subreddit}]
    """
    from app.services.ingest.reddit_fetcher import get_reddit_client
    _enforce_preview_rate_limit(request)

    reddit = get_reddit_client()
    if not reddit:
        raise HTTPException(
            status_code=503,
            detail="Reddit integration is not configured on this server.",
        )

    posts = []
    try:
        subreddit = reddit.subreddit(sub)
        for submission in subreddit.hot(limit=limit):
            if submission.stickied:
                continue

            image_url = None
            thumb = getattr(submission, "thumbnail", "")
            if thumb and thumb.startswith("http"):
                image_url = thumb

            posts.append({
                "title":          submission.title,
                "url":            submission.url,
                "snippet":        (submission.selftext[:300] if submission.selftext else ""),
                "image_url":      image_url,
                "published_date": datetime.fromtimestamp(submission.created_utc).isoformat(),
                "score":          submission.score,
                "subreddit":      submission.subreddit.display_name,
            })
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch r/{sub}: {exc}")

    return posts
