"""
KontentPyper - Posts API Router
Handles fetching post history, details, and filtering.
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, DB
from app.models.post import Post, PostResult

router = APIRouter()

@router.get("", summary="Get Post History")
async def get_posts(
    user: CurrentUser, 
    db: DB, 
    limit: int = Query(10, ge=1, le=100), 
    offset: int = Query(0, ge=0)
):
    """
    Returns a generalized list of posts for the dashboard feed/carousel.
    Combines data to show a unified post with its status across platforms.
    """
    result = await db.execute(
        select(Post)
        .where(Post.user_id == user.id)
        .options(selectinload(Post.post_results))
        .order_by(Post.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    posts = result.scalars().all()
    
    # Format the data for the frontend
    output = []
    for p in posts:
        platforms_list = p.platforms.split(',') if p.platforms else []
        
        output.append({
            "id": p.id,
            "original_content": p.original_content,
            "status": p.status,
            "created_at": p.created_at,
            "scheduled_for": p.scheduled_for,
            "image_urls": p.image_urls,
            "video_urls": p.video_urls,
            "platforms": platforms_list,
            "results": [
                {
                    "platform": r.platform,
                    "status": r.status,
                    "platform_post_url": r.platform_post_url,
                    "error_message": r.error_message
                } for r in p.post_results
            ]
        })
    
    return output

@router.get("/{post_id}", summary="Get Post Details")
async def get_post_detail(
    post_id: int,
    user: CurrentUser,
    db: DB
):
    """Get rich details of a single post."""
    result = await db.execute(
        select(Post)
        .where(Post.user_id == user.id, Post.id == post_id)
        .options(selectinload(Post.post_results), selectinload(Post.analytics))
    )
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
        
    return {
        "id": post.id,
        "original_content": post.original_content,
        "enhanced_content": post.enhanced_content,
        "image_urls": post.image_urls,
        "video_urls": post.video_urls,
        "status": post.status,
        "platforms": post.platforms.split(',') if post.platforms else [],
        "created_at": post.created_at,
        "scheduled_for": post.scheduled_for,
        "results": [
            {
                "platform": r.platform,
                "status": r.status,
                "platform_post_url": r.platform_post_url,
                "error_message": r.error_message
            } for r in post.post_results
        ],
        "analytics": [
            {
                "platform": a.platform,
                "views": a.views,
                "likes": a.likes,
                "comments": a.comments,
                "shares": a.shares
            } for a in post.analytics
        ]
    }
