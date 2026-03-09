"""
KontentPyper - Daily Content Pipeline  (Phase 6)
==================================================
The master orchestrator that runs daily at 08:00 via APScheduler.

Flow for each active user:
  1. Query `story_contents` for the highest-scoring unused story.
  2. Feed the story into the AI Enhancer to generate platform-specific drafts.
  3. Send a preview card to the user's Telegram bot (Phase 5 HITL).
  4. Wait for /approve or /reject (async future, 30 min timeout).
  5. If approved, call SocialService.publish_post() across all connected platforms.
  6. Send a completion notification via Telegram.

This ties Phase 1 (Ingestion), Phase 2 (AI), and Phase 5 (Telegram HITL) together.
"""

import logging
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.social import SocialConnection
from app.models.content import StoryContent
from app.services.social_service import SocialService
from app.services.ai.enhancer import EnhancerService
from app.services.notifications.telegram_hitl import send_preview_and_wait, send_message

logger = logging.getLogger(__name__)

# Module-level singleton so we don't re-init the LLM client on every run
_enhancer = EnhancerService()


async def run_daily_pipeline(user_id: int):
    """
    Executes the full daily content pipeline for a single user.
    """
    logger.info("[DailyPipeline] Starting pipeline for user_id=%s", user_id)

    async with AsyncSessionLocal() as db:
        # ── 0. Load user ──────────────────────────────────────────────
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            logger.warning("[DailyPipeline] user_id=%s not found or inactive. Skipping.", user_id)
            return

        bot_token = user.telegram_bot_token
        chat_id   = user.telegram_chat_id

        # ── 1. Fetch connected platforms ──────────────────────────────
        result = await db.execute(
            select(SocialConnection).where(
                SocialConnection.user_id == user_id,
                SocialConnection.is_active == True,
            )
        )
        connections = result.scalars().all()
        platforms = [conn.platform.lower() for conn in connections]

        if not platforms:
            logger.info("[DailyPipeline] user_id=%s has no connected platforms. Skipping.", user_id)
            return

        # ── 2. Pick the best unused story ─────────────────────────────
        result = await db.execute(
            select(StoryContent)
            .where(
                StoryContent.user_id == user_id,
                StoryContent.is_used == False,
            )
            .order_by(StoryContent.score.desc())
            .limit(1)
        )
        top_story = result.scalar_one_or_none()

        if not top_story:
            logger.info("[DailyPipeline] user_id=%s has no fresh stories. Skipping.", user_id)
            return

        # Mark as used immediately so concurrent runs will not double-post
        top_story.is_used = True
        await db.commit()

        topic_text = (
            f"Title: {top_story.title}\n\n"
            f"Content: {top_story.content[:600]}"
        )
        logger.info(
            "[DailyPipeline] Selected story_id=%s (score=%s) for user_id=%s",
            top_story.id, top_story.score, user_id,
        )

        # ── 3. AI Enhancement ────────────────────────────────────────
        try:
            enhanced = await _enhancer.enhance_draft(
                raw_content=topic_text,
                target_platforms=platforms,
            )
            # enhanced is an EnhancedDraft pydantic model with .platforms dict
            drafts: dict = enhanced.platforms  # e.g. {"twitter": "...", "linkedin": "..."}
        except Exception as exc:
            logger.error("[DailyPipeline] AI enhancement failed for user_id=%s: %s", user_id, exc)
            return

        if not drafts:
            logger.error("[DailyPipeline] Enhancer returned empty drafts for user_id=%s.", user_id)
            return

        logger.info("[DailyPipeline] Generated drafts for platforms: %s", list(drafts.keys()))

        # ── 4. Telegram HITL (if configured) ─────────────────────────
        if bot_token and chat_id:
            # Show combined preview
            preview_lines = []
            for plat, text in drafts.items():
                preview_lines.append(f"[{plat.upper()}]\n{text}")
            preview_text = "\n\n---\n\n".join(preview_lines)

            logger.info("[DailyPipeline] Sending HITL preview to user_id=%s", user_id)
            approved = await send_preview_and_wait(
                bot_token=bot_token,
                chat_id=chat_id,
                platform="Daily Auto-Post",
                content=preview_text,
            )

            if not approved:
                logger.info("[DailyPipeline] user_id=%s REJECTED the post (or timeout). Done.", user_id)
                # Un-mark the story so it can be retried tomorrow
                top_story.is_used = False
                await db.commit()
                return
        else:
            logger.warning(
                "[DailyPipeline] user_id=%s has no Telegram linked. "
                "HITL is required; skipping publish.", user_id
            )
            # Un-mark the story
            top_story.is_used = False
            await db.commit()
            return

        # ── 5. Publish ────────────────────────────────────────────────
        logger.info("[DailyPipeline] user_id=%s APPROVED! Publishing to %d platforms...", user_id, len(drafts))

        from app.models.post import Post, PostResult
        
        new_post = Post(
            user_id=user_id,
            original_content=topic_text,
            enhanced_content=drafts,
            platforms=",".join(drafts.keys()),
            status="published",
        )
        db.add(new_post)
        await db.flush()

        results = await SocialService.publish_post(
            db=db,
            user_id=user_id,
            content_map=drafts,
        )

        success_count = 0
        for r in results:
            status = "published" if r.success else "failed"
            if r.success:
                success_count += 1
            
            post_result = PostResult(
                post_id=new_post.id,
                platform=r.platform,
                status=status,
                platform_post_url=r.post_url,
                platform_post_id=r.post_id,
                error_message=r.error,
            )
            db.add(post_result)
        
        if success_count == 0 and len(results) > 0:
            new_post.status = "failed"
            
        await db.commit()

        logger.info(
            "[DailyPipeline] user_id=%s result: %d/%d platforms succeeded.",
            user_id, success_count, len(results),
        )

        # ── 6. Telegram completion notification ───────────────────────
        await send_message(
            bot_token, chat_id,
            f"<b>Post Complete!</b>\n"
            f"Published to <b>{success_count}</b> / <b>{len(results)}</b> platforms.",
        )


# ── Global orchestrator (called by APScheduler) ──────────────────────────────

async def orchestrate_all_users():
    """
    Entrypoint for the APScheduler cron daemon.
    Loops over every active user and runs their daily pipeline.
    """
    logger.info("[DailyScheduler] ====== Starting daily orchestration ======")

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User.id).where(User.is_active == True)
        )
        user_ids = result.scalars().all()

    logger.info("[DailyScheduler] Found %d active users to process.", len(user_ids))

    for uid in user_ids:
        try:
            await run_daily_pipeline(uid)
        except Exception as exc:
            logger.error("[DailyScheduler] Pipeline FAILED for user_id=%s: %s", uid, exc, exc_info=True)

    logger.info("[DailyScheduler] ====== Daily orchestration complete ======")
