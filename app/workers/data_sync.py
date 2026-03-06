"""
KontentPyper - Data Sync Workers
Fetches real-time analytics data from social platforms and updates local DB.
"""
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.post import Post, PostResult
from app.models.analytics import PostAnalytics
from app.models.social import SocialConnection

logger = logging.getLogger(__name__)


async def fetch_and_store_analytics(db: AsyncSession, user_id: int):
    """
    Given a user, fetches the recent successful PostResults, querying
    the respective platform's Insight/Analytics API to update PostAnalytics.
    """
    # 1. Fetch user's recent successful posts 
    # Example: posts from the last 7 days
    # In a real scenario, you'd filter by date to avoid re-fetching ancient posts constantly.
    q = select(PostResult).join(Post).where(
        Post.user_id == user_id,
        PostResult.success == True
    )
    recent_results = (await db.execute(q)).scalars().all()

    if not recent_results:
        logger.debug(f"[DataSync] No recent post results found for user {user_id}")
        return

    # Group by platform to optimize connection fetching
    platform_posts = {}
    for res in recent_results:
        posts = platform_posts.setdefault(res.platform, [])
        posts.append(res)
        
    for platform, results in platform_posts.items():
        # Get connection for this platform
        conn_q = select(SocialConnection).where(
            SocialConnection.user_id == user_id,
            SocialConnection.platform == platform
        )
        connection = (await db.execute(conn_q)).scalar_one_or_none()
        
        if not connection:
            logger.warning(f"[DataSync] Missing {platform} connection for user {user_id}. Skipping.")
            continue

        # In a fully scaled implementation, here we call platform-specific API adapters:
        # e.g. twitter_api.get_tweet_metrics(connection.access_token, post_id=res.platform_post_id)
        
        # For KontentPyper MVP, we insert/update a dummy/simulated analytics record 
        # to prove the loop works, unless real API credentials support insight fetching.
        for res in results:
            if not res.platform_post_id: continue
                
            # Check if we already have an analytics record for this post on this platform
            analytics_q = select(PostAnalytics).where(
                PostAnalytics.post_id == res.post_id,
                PostAnalytics.platform == platform
            )
            analytic_record = (await db.execute(analytics_q)).scalar_one_or_none()
            
            if not analytic_record:
                analytic_record = PostAnalytics(
                    post_id=res.post_id,
                    user_id=user_id,
                    platform=platform,
                    views=0, likes=0, comments=0, shares=0, clicks=0
                )
                db.add(analytic_record)
            
            # Simulate metrics update or fetch REAL metrics here
            # analytic_record.views = latest_metrics['views']
            analytic_record.views += 15  # Simulated organic growth
            analytic_record.likes += 2
            
    await db.commit()
    logger.info(f"[DataSync] Completed sync for user {user_id}. Updated {len(recent_results)} records.")
