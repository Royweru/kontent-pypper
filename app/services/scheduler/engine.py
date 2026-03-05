"""
KontentPyper - APScheduler Engine
Initializes and manages the async cron daemon.
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.scheduler.jobs import setup_jobs

logger = logging.getLogger(__name__)

# ==============================================================================
# FUTURE ARCHITECTURE NOTE (10x Developer Roadmap):
# Currently using APScheduler (AsyncIOScheduler) running in-process with FastAPI
# for the MVP to handle simple scheduled posts and periodic analytics fetching. 
# 
# For production scale, long-running tasks, and true distributed queuing, 
# this entire engine will be swapped out for CELERY + REDIS.
# ==============================================================================

# Global singleton so we can access or modify jobs anywhere
scheduler = AsyncIOScheduler()

def start_scheduler():
    """Boots up the background cron daemon and registers jobs."""
    if not scheduler.running:
        setup_jobs(scheduler)
        scheduler.start()
        logger.info("APScheduler background daemon started.")

def stop_scheduler():
    """Gracefully shuts down the background cron daemon."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler background daemon stopped.")
