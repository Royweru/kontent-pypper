"""
KontentPyper - Headless Pipeline Runner
Runs the LangGraph pipeline without SSE streaming.
Stores results directly in AssetLibrary as pending_review items.
Used by the cron scheduler for background autonomous runs.
"""

import logging
import uuid
from datetime import datetime

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.content import AssetLibrary
from app.models.schedule import ScheduledJob
from app.services.workflow.langgraph_pipeline import langgraph_pipeline
from app.services.credit_service import (
    check_workflow_run_allowed,
    increment_daily_runs,
    check_video_credits,
    consume_credits,
    get_video_model_for_tier,
    DailyRunLimitError,
    InsufficientCreditsError,
)

logger = logging.getLogger(__name__)


async def run_headless_pipeline(user_id: int):
    """
    Executes the LangGraph pipeline headlessly (no SSE).
    Called by APScheduler cron job.

    Steps:
      1. Load user + check credits/limits
      2. Run full pipeline
      3. Store results in AssetLibrary with status=pending_review
      4. Update the ScheduledJob tracking fields
    """
    run_id = str(uuid.uuid4())[:8]
    logger.info("[HeadlessPipeline] Starting run_id=%s for user_id=%d", run_id, user_id)

    async with AsyncSessionLocal() as db:
        # ── Load user ─────────────────────────────────────────────────
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            logger.warning("[HeadlessPipeline] user_id=%d not found or inactive.", user_id)
            return

        tier = user.tier_level or "free"

        # ── Check daily run limit ─────────────────────────────────────
        try:
            await check_workflow_run_allowed(db, user)
        except DailyRunLimitError:
            logger.warning("[HeadlessPipeline] user_id=%d hit daily run limit.", user_id)
            await _update_job_status(db, user_id, "error")
            return

        # ── Determine video model ─────────────────────────────────────
        video_model = get_video_model_for_tier(tier)

        if video_model != "stock":
            try:
                await check_video_credits(db, user, model=video_model)
            except InsufficientCreditsError:
                logger.warning("[HeadlessPipeline] user_id=%d no credits. Falling back to stock.", user_id)
                video_model = "stock"

        # ── Increment daily counter ───────────────────────────────────
        await increment_daily_runs(db, user)

        # ── Run pipeline ──────────────────────────────────────────────
        initial_state = {
            "user_id": user_id,
            "niche": user.active_niche or user.niche or "Technology and AI",
            "tier_level": tier,
            "video_model": video_model,
            "articles": [],
            "selected_article": None,
            "scripts": {},
            "video_asset": None,
            "video_source": None,
            "video_script": None,
            "credits_consumed": 0,
            "status": "Starting headless pipeline...",
        }

        final_state = initial_state.copy()

        try:
            async for state_update in langgraph_pipeline.astream(initial_state):
                for node_name, updated_state in state_update.items():
                    logger.info("[HeadlessPipeline] run_id=%s finished node: %s", run_id, node_name)
                    final_state.update(updated_state)
        except Exception as exc:
            logger.error("[HeadlessPipeline] Pipeline error run_id=%s: %s", run_id, exc, exc_info=True)
            await _update_job_status(db, user_id, "error")
            return

        # ── Consume credits ───────────────────────────────────────────
        credits_used = final_state.get("credits_consumed", 0)
        if credits_used > 0:
            try:
                result = await db.execute(select(User).where(User.id == user_id))
                fresh_user = result.scalar_one_or_none()
                if fresh_user:
                    await consume_credits(
                        db=db,
                        user=fresh_user,
                        credits=credits_used,
                        action_type="workflow_run",
                        model_used=final_state.get("video_source", video_model),
                        description=f"Headless cron run: {run_id}",
                    )
            except Exception as exc:
                logger.error("[HeadlessPipeline] Credit consumption failed: %s", exc)

        # ── Store in AssetLibrary as pending_review ────────────────────
        article = final_state.get("selected_article") or {}
        scripts = final_state.get("scripts", {})
        video_url = final_state.get("video_asset")
        video_script = final_state.get("video_script")

        asset = AssetLibrary(
            user_id=user_id,
            asset_type="bundle",
            title=article.get("title", f"Auto-generated content ({run_id})"),
            content_url=video_url,
            text_content=scripts.get("twitter") or scripts.get("linkedin") or "",
            status="pending_review",
            platform_drafts=scripts,
            video_script_data=video_script,
            source_article_title=article.get("title"),
            source_article_url=article.get("url"),
            video_model_used=final_state.get("video_source", video_model),
            credits_consumed=credits_used,
            workflow_run_id=run_id,
            platforms_used=list(scripts.keys()) if scripts else [],
        )
        db.add(asset)
        await db.commit()

        logger.info(
            "[HeadlessPipeline] run_id=%s complete. Asset saved as pending_review (asset_id=%d).",
            run_id, asset.id,
        )

        # ── Update scheduled job tracking ─────────────────────────────
        await _update_job_status(db, user_id, "pending_review")


async def _update_job_status(db, user_id: int, status: str):
    """Updates the ScheduledJob tracking fields after a run."""
    result = await db.execute(
        select(ScheduledJob).where(ScheduledJob.user_id == user_id)
    )
    job = result.scalar_one_or_none()

    if job:
        job.last_run_at = datetime.utcnow()
        job.last_run_status = status
        job.total_runs = (job.total_runs or 0) + 1
        await db.commit()
