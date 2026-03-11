"""
KontentPyper - Scheduled Jobs
Background workers that run periodically (e.g. cron) to fetch analytics.
"""

import logging
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.social import SocialConnection
from app.models.analytics import PostAnalytics

logger = logging.getLogger(__name__)

# ==============================================================================
# FUTURE ARCHITECTURE NOTE:
# These functions are currently registered as APScheduler cron jobs.
# In V2, these will become `@celery.task` functions dispatched to a Redis queue.
# ==============================================================================

from app.models.user import User
from app.models.content import ContentSource


async def sync_platform_analytics():
    """
    Cron Job: Pulls fresh metrics (views, likes, etc) from Social Platforms.
    """
    logger.info("[Scheduler] Starting background analytics sync...")
    
    from app.workers.data_sync import fetch_and_store_analytics
    
    async with AsyncSessionLocal() as db:
        try:
            # Fetch all active users
            q = select(User.id).where(User.is_active == True)
            user_ids = (await db.execute(q)).scalars().all()
            
            for uid in user_ids:
                await fetch_and_store_analytics(db, uid)
                
        except Exception as e:
            logger.error(f"[Scheduler] Error during analytics sync: {e}")

    logger.info("[Scheduler] Finished background analytics sync.")


async def scheduled_ai_reflection():
    """
    Cron Job: Runs the AI Reflector to dynamically adjust strategy.
    """
    logger.info("[Scheduler] Starting background AI Reflection...")
    
    from app.workers.reflection_job import run_weekly_reflection
    
    async with AsyncSessionLocal() as db:
        try:
            # Fetch all active users
            q = select(User.id).where(User.is_active == True)
            user_ids = (await db.execute(q)).scalars().all()
            
            for uid in user_ids:
                await run_weekly_reflection(db, uid)
                
        except Exception as e:
            logger.error(f"[Scheduler] Error during AI Reflection: {e}")

    logger.info("[Scheduler] Finished background AI Reflection.")



async def personalized_ingest_job():
    """
    Cron Job: Fetches content from each user's saved ContentSource rows.

    For each active user, this job:
      1. Queries active RSS / Reddit sources owned by that user.
      2. Calls the appropriate fetcher (fetch_user_rss / fetch_user_reddit).
      3. Runs the scorer to persist new items tagged with user_id + source_id.
      4. Updates last_fetched timestamp on each source.

    This decouples the global background feed from personalized user feeds.
    """
    from datetime import datetime
    from app.services.ingest.rss_fetcher import fetch_user_rss
    from app.services.ingest.reddit_fetcher import fetch_user_reddit
    from app.services.ingest.scorer import score_and_store_items

    logger.info("[IngestJob] Starting personalized ingest job...")

    async with AsyncSessionLocal() as db:
        # Load all active users
        user_ids = (await db.execute(
            select(User.id).where(User.is_active == True)
        )).scalars().all()

        for uid in user_ids:
            try:
                # Load all active sources for this user
                sources = (await db.execute(
                    select(ContentSource).where(
                        ContentSource.user_id == uid,
                        ContentSource.is_active == True,
                    )
                )).scalars().all()

                if not sources:
                    continue

                rss_sources = [s for s in sources if s.source_type == "rss"]
                reddit_sources = [s for s in sources if s.source_type == "reddit"]

                raw_items = []
                if rss_sources:
                    raw_items.extend(fetch_user_rss(rss_sources))
                if reddit_sources:
                    raw_items.extend(fetch_user_reddit(reddit_sources))

                if raw_items:
                    added = await score_and_store_items(db, raw_items)
                    logger.info("[IngestJob] user_id=%d: saved %d new items.", uid, added)

                # Update last_fetched on all processed sources
                now = datetime.utcnow()
                for src in sources:
                    src.last_fetched = now
                await db.commit()

            except Exception as exc:
                logger.error("[IngestJob] Error ingesting for user_id=%d: %s", uid, exc, exc_info=True)

    logger.info("[IngestJob] Personalized ingest job complete.")


def setup_jobs(scheduler):
    """
    Registers all automated background tasks to the APScheduler instance.
    """
    # 1. Analytics Sync (Every 60 minutes)
    scheduler.add_job(
        sync_platform_analytics,
        'interval',
        minutes=60,
        id="sync_platform_analytics_job",
        replace_existing=True
    )
    logger.info("Registered 'sync_platform_analytics' job — every 60 minutes.")

    # 2. AI Reflection (Once every 7 days)
    scheduler.add_job(
        scheduled_ai_reflection,
        'interval',
        days=7,
        id="scheduled_ai_reflection_job",
        replace_existing=True
    )
    logger.info("Registered 'scheduled_ai_reflection' job — every 7 days.")

    # 3. Daily Content Pipeline + Telegram HITL (08:00 daily)
    from app.services.scheduler.daily_pipeline import orchestrate_all_users
    scheduler.add_job(
        orchestrate_all_users,
        'cron',
        hour=8,
        minute=0,
        id="daily_content_pipeline_job",
        replace_existing=True,
    )
    logger.info("Registered 'daily_content_pipeline_job' — daily at 08:00.")

    # 4. Personalized Feed Ingest (Every 6 hours)
    scheduler.add_job(
        personalized_ingest_job,
        'interval',
        hours=6,
        id="personalized_ingest_job",
        replace_existing=True,
    )
    logger.info("Registered 'personalized_ingest_job' — every 6 hours.")
