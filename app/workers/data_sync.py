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
        PostResult.status == 'published'
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

        # Instantiate platform adapter
        adapter = None
        if platform == 'twitter':
            from app.services.platforms.twitter import TwitterService
            from app.core.config import settings
            adapter = TwitterService(api_key=settings.TWITTER_API_KEY, api_secret=settings.TWITTER_API_SECRET)
        elif platform == 'youtube':
            from app.services.platforms.youtube import YouTubeService
            adapter = YouTubeService()
        elif platform == 'linkedin':
            from app.services.platforms.linkedin import LinkedInService
            adapter = LinkedInService()
        elif platform == 'tiktok':
            from app.services.platforms.tiktok import TikTokService
            adapter = TikTokService()

        if not adapter:
            logger.warning(f"[DataSync] No adapter available for {platform}. Skipping.")
            continue

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
            
            # Fetch REAL metrics using the integrated platform adapters
            metrics = await adapter.fetch_analytics(
                access_token=connection.access_token, 
                platform_post_id=res.platform_post_id,
                token_secret=connection.oauth_token_secret if platform == 'twitter' else ""
            )
            
            if metrics:
                # We always trust the latest counts from the platform over our own DB state
                # because social platforms dictate the exact number of likes/views.
                analytic_record.views = metrics.get('views', analytic_record.views)
                analytic_record.likes = metrics.get('likes', analytic_record.likes)
                analytic_record.comments = metrics.get('comments', analytic_record.comments)
                analytic_record.shares = metrics.get('shares', analytic_record.shares)
                analytic_record.clicks = metrics.get('clicks', analytic_record.clicks)
            
    await db.commit()
    logger.info(f"[DataSync] Completed sync for user {user_id}. Updated {len(recent_results)} post metrics.")
