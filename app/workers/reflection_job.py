"""
KontentPyper - Automated AI Reflection
Runs periodically (e.g. weekly) to analyze the past week's analytics 
and update the system strategy.
"""
import logging
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.analytics import PostAnalytics
from app.services.ai.reflector import ReflectorService

logger = logging.getLogger(__name__)

async def run_weekly_reflection(db: AsyncSession, user_id: int):
    """
    Fetches the latest analytics for a user and runs the Reflector service.
    In a full pipeline, these insights are saved directly to a `StrategyRule`
    table or injected back into the Enhancer's system prompt automatically.
    """
    logger.info(f"[ReflectionJob] Starting weekly AI reflection for user {user_id}")
    
    q = (
        select(PostAnalytics)
        .where(PostAnalytics.user_id == user_id)
        .order_by(desc(PostAnalytics.created_at))
        .limit(100)  # Grab the last 100 engagements
    )
    rows = (await db.execute(q)).scalars().all()
    
    if not rows:
        logger.info(f"[ReflectionJob] Not enough data to reflect for user {user_id}")
        return

    data_lines = [
        f"Platform={r.platform} | Views={r.views} | Likes={r.likes} | Comments={r.comments} | Shares={r.shares}"
        for r in rows
    ]
    dump = "\n".join(data_lines)
    
    reflector = ReflectorService()
    try:
        insight = await reflector.analyze_performance(dump)
        
        # Here we log the insights. 
        # Future 10x scale: Persist `insight.new_rules` to DB and automatically
        # prepend to the Enhancer's system instructions.
        logger.info(f"[ReflectionJob] SUCCESS. What worked: {insight.what_worked[:50]}...")
        logger.info(f"[ReflectionJob] NEW RULES Generated: {insight.new_rules}")
        
    except Exception as e:
        logger.error(f"[ReflectionJob] AI Reflection failed: {str(e)}")
