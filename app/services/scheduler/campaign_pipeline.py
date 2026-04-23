"""
KontentPyper - Autonomous Campaign Pipeline Runner
Executes the LangGraph agent for a specific campaign, then either
auto-publishes or stores content for manual HITL review.

Called by APScheduler cron job: run_campaign_pipeline(campaign_id)
"""

import logging
import uuid
import traceback
from datetime import datetime

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.content import AssetLibrary
from app.models.campaign import AgentCampaign, AgentCampaignRun
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

# Maximum consecutive failures before auto-pausing a campaign
MAX_CONSECUTIVE_FAILURES = 5


async def run_campaign_pipeline(campaign_id: int):
    """
    Master entry point for autonomous campaign execution.

    This function is invoked by APScheduler at the configured cron schedule.
    It performs:
      1. Load campaign config + verify user/tier/credits
      2. Check rate limits (runs_today vs max_runs_per_day)
      3. Create an AgentCampaignRun tracking record
      4. Execute the LangGraph pipeline with campaign-specific inputs
      5. Either auto-publish or save to AssetLibrary for review
      6. Update campaign counters and run status
      7. Handle retries and auto-pause on repeated failures
    """
    run_uuid = str(uuid.uuid4())[:8]
    logger.info(
        "[CampaignPipeline] Starting campaign_id=%d run_id=%s",
        campaign_id, run_uuid,
    )

    async with AsyncSessionLocal() as db:
        # ── 1. Load campaign ──────────────────────────────────────────
        result = await db.execute(
            select(AgentCampaign).where(AgentCampaign.id == campaign_id)
        )
        campaign = result.scalar_one_or_none()

        if not campaign:
            logger.error(
                "[CampaignPipeline] campaign_id=%d not found.", campaign_id
            )
            return

        if not campaign.is_active or campaign.status not in ("active",):
            logger.info(
                "[CampaignPipeline] campaign_id=%d is inactive (status=%s). Skipping.",
                campaign_id, campaign.status,
            )
            return

        # ── Load user ─────────────────────────────────────────────────
        user_result = await db.execute(
            select(User).where(User.id == campaign.user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user or not user.is_active:
            logger.warning(
                "[CampaignPipeline] user_id=%d not found or inactive.",
                campaign.user_id,
            )
            return

        tier = user.tier_level or "free"

        # ── 2. Rate limit check ───────────────────────────────────────
        # Reset daily counter if needed
        now = datetime.utcnow()
        if campaign.runs_reset_date is None or now.date() > campaign.runs_reset_date.date():
            campaign.runs_today = 0
            campaign.runs_reset_date = now

        if campaign.runs_today >= campaign.max_runs_per_day:
            logger.info(
                "[CampaignPipeline] campaign_id=%d hit daily limit (%d/%d). Skipping.",
                campaign_id, campaign.runs_today, campaign.max_runs_per_day,
            )
            await db.commit()
            return

        # ── Check global workflow run limits ──────────────────────────
        try:
            await check_workflow_run_allowed(db, user)
        except DailyRunLimitError:
            logger.warning(
                "[CampaignPipeline] user_id=%d hit global daily run limit.",
                campaign.user_id,
            )
            return

        # ── 3. Create run record ──────────────────────────────────────
        run = AgentCampaignRun(
            campaign_id=campaign_id,
            run_id=run_uuid,
            status="running",
            pipeline_node="init",
            started_at=now,
        )
        db.add(run)

        # Increment daily counters
        campaign.runs_today += 1
        campaign.total_runs = (campaign.total_runs or 0) + 1
        campaign.last_run_at = now

        await db.commit()
        await db.refresh(run)

        # ── 4. Determine video model ──────────────────────────────────
        video_model = get_video_model_for_tier(tier)
        if video_model != "stock":
            try:
                await check_video_credits(db, user, model=video_model)
            except InsufficientCreditsError:
                logger.warning(
                    "[CampaignPipeline] user_id=%d no credits. Falling back to stock.",
                    campaign.user_id,
                )
                video_model = "stock"

        # Increment user daily run counter
        await increment_daily_runs(db, user)

        # ── 5. Execute LangGraph pipeline ─────────────────────────────
        initial_state = {
            "user_id": campaign.user_id,
            "niche": campaign.niche,
            "tier_level": tier,
            "video_model": video_model,
            "articles": [],
            "selected_article": None,
            "scripts": {},
            "video_asset": None,
            "video_source": None,
            "video_script": None,
            "credits_consumed": 0,
            "status": f"Campaign pipeline [{campaign.name}]...",
            # Campaign-specific context for agent
            "topic_instructions": campaign.topic_instructions or "",
            "target_platforms": campaign.target_platforms or [],
        }

        final_state = initial_state.copy()

        try:
            async for state_update in langgraph_pipeline.astream(initial_state):
                for node_name, updated_state in state_update.items():
                    logger.info(
                        "[CampaignPipeline] run_id=%s finished node: %s",
                        run_uuid, node_name,
                    )
                    run.pipeline_node = node_name
                    final_state.update(updated_state)
                    await db.commit()

        except Exception as exc:
            logger.error(
                "[CampaignPipeline] Pipeline error run_id=%s: %s",
                run_uuid, exc, exc_info=True,
            )
            await _finalize_run_error(
                db, campaign, run, str(exc), traceback.format_exc(),
            )
            return

        # ── 6. Consume credits ────────────────────────────────────────
        credits_used = final_state.get("credits_consumed", 0)
        if credits_used > 0:
            try:
                fresh_user_result = await db.execute(
                    select(User).where(User.id == campaign.user_id)
                )
                fresh_user = fresh_user_result.scalar_one_or_none()
                if fresh_user:
                    await consume_credits(
                        db=db,
                        user=fresh_user,
                        credits=credits_used,
                        action_type="campaign_run",
                        model_used=final_state.get("video_source", video_model),
                        description=f"Campaign '{campaign.name}' run: {run_uuid}",
                    )
            except Exception as exc:
                logger.error(
                    "[CampaignPipeline] Credit consumption failed: %s", exc
                )

        # ── 7. Extract generated content ──────────────────────────────
        article = final_state.get("selected_article") or {}
        scripts = final_state.get("scripts", {})
        video_url = final_state.get("video_asset")
        video_script = final_state.get("video_script")

        # ── 8. Store in AssetLibrary ──────────────────────────────────
        asset_status = "pending_review"  # Default: HITL review
        if campaign.auto_publish:
            asset_status = "auto_publishing"

        asset = AssetLibrary(
            user_id=campaign.user_id,
            asset_type="bundle",
            title=article.get("title", f"Campaign: {campaign.name} ({run_uuid})"),
            content_url=video_url,
            text_content=scripts.get("twitter") or scripts.get("linkedin") or "",
            status=asset_status,
            platform_drafts=scripts,
            video_script_data=video_script,
            source_article_title=article.get("title"),
            source_article_url=article.get("url"),
            video_model_used=final_state.get("video_source", video_model),
            credits_consumed=credits_used,
            workflow_run_id=run_uuid,
            platforms_used=list(scripts.keys()) if scripts else [],
        )
        db.add(asset)
        await db.commit()
        await db.refresh(asset)

        # ── 9. Auto-publish if enabled ────────────────────────────────
        platform_results = []
        auto_published = False

        if campaign.auto_publish and scripts:
            run.status = "publishing"
            run.pipeline_node = "auto_publish"
            await db.commit()

            try:
                from app.services.social_service import SocialService

                # Filter scripts to only target campaign's platforms
                content_map = {}
                for platform in (campaign.target_platforms or []):
                    platform_key = platform.lower()
                    if platform_key in scripts:
                        content_map[platform_key] = scripts[platform_key]

                if content_map:
                    image_urls = []
                    video_urls = [video_url] if video_url else []

                    results = await SocialService.publish_post(
                        db=db,
                        user_id=campaign.user_id,
                        content_map=content_map,
                        image_urls=image_urls or None,
                        video_urls=video_urls or None,
                    )

                    for r in results:
                        platform_results.append({
                            "platform": r.platform if hasattr(r, "platform") else "unknown",
                            "success": r.success if hasattr(r, "success") else False,
                            "post_url": r.post_url if hasattr(r, "post_url") else None,
                            "error": r.error if hasattr(r, "error") else None,
                        })

                    auto_published = True
                    asset.status = "published"
                    asset.published_at = datetime.utcnow()
                    await db.commit()

                    logger.info(
                        "[CampaignPipeline] Auto-published run_id=%s to %s",
                        run_uuid, list(content_map.keys()),
                    )

            except Exception as exc:
                logger.error(
                    "[CampaignPipeline] Auto-publish failed run_id=%s: %s",
                    run_uuid, exc, exc_info=True,
                )
                platform_results.append({
                    "platform": "system",
                    "success": False,
                    "error": str(exc),
                })
                asset.status = "pending_review"
                await db.commit()

        # ── 10. Finalize run ──────────────────────────────────────────
        completed_at = datetime.utcnow()
        run.status = "published" if auto_published else "success"
        run.completed_at = completed_at
        run.duration_seconds = (completed_at - run.started_at).total_seconds()
        run.article_title = article.get("title")
        run.article_url = article.get("url")
        run.platform_drafts = scripts
        run.video_url = video_url
        run.asset_id = asset.id
        run.auto_published = auto_published
        run.platform_results = platform_results or None
        run.credits_consumed = credits_used
        run.video_model_used = final_state.get("video_source", video_model)

        # Update campaign counters
        campaign.successful_runs = (campaign.successful_runs or 0) + 1
        campaign.consecutive_failures = 0
        campaign.total_credits_consumed = (
            (campaign.total_credits_consumed or 0) + credits_used
        )
        if auto_published:
            published_count = sum(
                1 for pr in platform_results if pr.get("success")
            )
            campaign.total_posts_published = (
                (campaign.total_posts_published or 0) + published_count
            )

        await db.commit()

        # ── 11. Send Telegram notification (optional) ─────────────────
        await _send_telegram_notification(db, user, campaign, run, auto_published)

        logger.info(
            "[CampaignPipeline] run_id=%s complete. status=%s auto_published=%s asset_id=%d",
            run_uuid, run.status, auto_published, asset.id,
        )


async def _finalize_run_error(
    db, campaign: AgentCampaign, run: AgentCampaignRun,
    error_msg: str, tb: str,
):
    """Handles pipeline failure: updates run, increments failure counters,
    and auto-pauses campaign if failures exceed threshold."""
    completed_at = datetime.utcnow()

    run.status = "failed"
    run.completed_at = completed_at
    run.duration_seconds = (completed_at - run.started_at).total_seconds()
    run.error_message = error_msg
    run.error_details = {
        "node": run.pipeline_node,
        "traceback": tb[:2000],  # Truncate to avoid bloating the DB
        "retry_count": campaign.consecutive_failures or 0,
    }

    campaign.failed_runs = (campaign.failed_runs or 0) + 1
    campaign.consecutive_failures = (campaign.consecutive_failures or 0) + 1

    # Auto-pause after N consecutive failures
    if campaign.consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
        campaign.is_active = False
        campaign.status = "error_paused"
        logger.warning(
            "[CampaignPipeline] Auto-paused campaign_id=%d after %d consecutive failures.",
            campaign.id, campaign.consecutive_failures,
        )
        # Remove the APScheduler job
        try:
            from app.services.scheduler.engine import scheduler
            job_id = f"campaign_cron_{campaign.id}"
            scheduler.remove_job(job_id)
        except Exception:
            pass

    await db.commit()


async def _send_telegram_notification(
    db, user: User, campaign: AgentCampaign,
    run: AgentCampaignRun, auto_published: bool,
):
    """Sends a Telegram notification to the user if they have Telegram linked."""
    try:
        telegram_chat_id = getattr(user, "telegram_chat_id", None)
        if not telegram_chat_id:
            return

        from app.services.telegram_service import send_telegram_message

        if auto_published:
            msg = (
                f"[Campaign: {campaign.name}]\n"
                f"Auto-published content to {', '.join(campaign.target_platforms or [])}.\n"
                f"Article: {run.article_title or 'N/A'}\n"
                f"Duration: {run.duration_seconds:.1f}s"
            )
        else:
            msg = (
                f"[Campaign: {campaign.name}]\n"
                f"New content ready for review.\n"
                f"Article: {run.article_title or 'N/A'}\n"
                f"Duration: {run.duration_seconds:.1f}s"
            )

        await send_telegram_message(telegram_chat_id, msg)

    except Exception as exc:
        # Telegram notifications are best-effort, never block the pipeline
        logger.debug(
            "[CampaignPipeline] Telegram notification failed: %s", exc
        )
