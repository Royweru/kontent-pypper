"""
KontentPyper - Analytics API Router
Provides per-post metrics, user-level summaries, and AI-powered reflection.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException
from sqlalchemy import select, func, desc

from app.core.deps import CurrentUser, DB
from app.models.post import Post, PostResult
from app.models.analytics import PostAnalytics, UserAnalyticsSummary

router = APIRouter()


# ── User-level summary ────────────────────────────────────────────

@router.get("/summary", summary="Get Analytics Summary")
async def get_analytics_summary(user: CurrentUser, db: DB):
    """
    Returns the user's aggregate analytics: total posts, total views,
    total engagements, and top-performing platform.
    """
    # Check if we have a pre-computed summary
    q = select(UserAnalyticsSummary).where(
        UserAnalyticsSummary.user_id == user.id
    )
    summary = (await db.execute(q)).scalar_one_or_none()

    if summary:
        return {
            "total_posts":       summary.total_posts,
            "total_views":       summary.total_views,
            "total_engagements": summary.total_engagements,
            "top_platform":      summary.top_platform,
            "last_updated":      summary.updated_at,
        }

    # Fallback: compute on-the-fly from PostAnalytics by joining Post
    stats_q = (
        select(
            func.count(PostAnalytics.id).label("total_posts"),
            func.coalesce(func.sum(PostAnalytics.views), 0).label("total_views"),
            func.coalesce(func.sum(PostAnalytics.likes + PostAnalytics.comments + PostAnalytics.shares), 0).label("total_engagements"),
        )
        .join(Post, PostAnalytics.post_id == Post.id)
        .where(Post.user_id == user.id)
    )

    row = (await db.execute(stats_q)).one_or_none()

    return {
        "total_posts":       row.total_posts if row else 0,
        "total_views":       row.total_views if row else 0,
        "total_engagements": row.total_engagements if row else 0,
        "top_platform":      None,
        "last_updated":      None,
    }


# ── Per-post metrics ─────────────────────────────────────────────

@router.get("/posts", summary="Get Per-Post Analytics")
async def get_post_analytics(
    user: CurrentUser,
    db: DB,
    platform: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
):
    """
    Returns analytics for individual posts, optionally filtered by platform.
    """
    q = (
        select(PostAnalytics)
        .join(Post, PostAnalytics.post_id == Post.id)
        .where(Post.user_id == user.id)
        .order_by(desc(PostAnalytics.fetched_at))
        .limit(min(limit, 100))
        .offset(offset)
    )

    if platform:
        q = q.where(PostAnalytics.platform == platform.upper())

    results = (await db.execute(q)).scalars().all()

    return [
        {
            "id":          r.id,
            "post_id":     r.post_id,
            "platform":    r.platform,
            "views":       r.views,
            "likes":       r.likes,
            "comments":    r.comments,
            "shares":      r.shares,
            "clicks":      r.clicks,
            "created_at":  r.created_at,
        }
        for r in results
    ]


# ── AI Reflection Trigger ────────────────────────────────────────

@router.post("/reflect", summary="Trigger AI Reflection")
async def trigger_reflection(user: CurrentUser, db: DB):
    """
    Manually triggers the AI Reflector to analyze recent post performance
    and return strategic insights.
    """
    from app.services.ai.reflector import ReflectorService

    # Gather recent analytics data
    q = (
        select(PostAnalytics)
        .join(Post, PostAnalytics.post_id == Post.id)
        .where(Post.user_id == user.id)
        .order_by(desc(PostAnalytics.fetched_at))
        .limit(50)
    )
    rows = (await db.execute(q)).scalars().all()

    if not rows:
        raise HTTPException(404, "No analytics data available yet. Publish some posts first.")

    # Build a text dump for the LLM
    data_lines = []
    for r in rows:
        data_lines.append(
            f"Platform={r.platform} | Views={r.views} | Likes={r.likes} | "
            f"Comments={r.comments} | Shares={r.shares} | Clicks={r.clicks}"
        )
    dump = "\n".join(data_lines)

    reflector = ReflectorService()
    insight = await reflector.analyze_performance(dump)

    return {
        "what_worked": insight.what_worked,
        "what_failed": insight.what_failed,
        "new_rules":   insight.new_rules,
    }
