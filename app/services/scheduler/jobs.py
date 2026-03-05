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
    logger.info("Registered 'sync_platform_analytics' job to run every 60 minutes.")
    
    # 2. AI Reflection (Once every 7 days)
    # Using a 7-day interval for the prototype; in prod, might use a specific day of week cron.
    scheduler.add_job(
        scheduled_ai_reflection,
        'interval',
        days=7,
        id="scheduled_ai_reflection_job",
        replace_existing=True
    )
    logger.info("Registered 'scheduled_ai_reflection' job to run every 7 days.")
