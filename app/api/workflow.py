"""
KontentPyper - Workflow API Endpoint
Executes the LangGraph pipeline with credit gating, tier checks,
and SSE streaming for the live tracker UI.
"""

import json
import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.services.workflow.langgraph_pipeline import langgraph_pipeline
from app.services.credit_service import (
    check_workflow_run_allowed,
    increment_daily_runs,
    check_video_credits,
    consume_credits,
    get_video_model_for_tier,
    get_tier_config,
    DailyRunLimitError,
    InsufficientCreditsError,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/run")
async def run_workflow(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Executes the LangGraph automated content generation pipeline
    and streams back the state changes so the frontend can update live.

    Credit Gating:
      1. Check if the user is allowed to run (daily limit for free tier)
      2. Determine video model based on tier
      3. Pre-check if credits are sufficient (skip for stock/free)
      4. Run pipeline
      5. Consume credits after successful completion
    """

    # ── Step 1: Daily run limit check ────────────────────────────────
    try:
        await check_workflow_run_allowed(db, current_user)
    except DailyRunLimitError as e:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "daily_limit_reached",
                "message": str(e),
                "max_runs": e.max_runs,
                "upgrade_to": "pro",
            },
        )

    # ── Step 2: Determine video model for this tier ──────────────────
    tier = current_user.tier_level or "free"
    video_model = get_video_model_for_tier(tier)

    # ── Step 3: Pre-check credit availability (skip for stock) ───────
    if video_model != "stock":
        try:
            credit_cost = await check_video_credits(db, current_user, model=video_model)
        except InsufficientCreditsError as e:
            # Graceful fallback: use stock video if no credits remain
            logger.warning(
                "[Workflow] user_id=%d has no credits for %s. Falling back to stock.",
                current_user.id, video_model,
            )
            video_model = "stock"

    # ── Step 4: Increment daily run counter ──────────────────────────
    await increment_daily_runs(db, current_user)

    async def event_generator():
        """SSE generator that streams pipeline state to the frontend."""
        # Build initial state with tier/model info
        initial_state = {
            "user_id": current_user.id,
            "niche": current_user.active_niche or current_user.niche or "Technology and AI",
            "tier_level": tier,
            "video_model": video_model,
            "articles": [],
            "selected_article": None,
            "scripts": {},
            "video_asset": None,
            "video_source": None,
            "video_script": None,
            "credits_consumed": 0,
            "status": "Starting pipeline...",
        }

        yield f"data: {json.dumps(initial_state)}\n\n"

        final_state = initial_state.copy()

        # Stream nodes one-by-one
        try:
            async for state_update in langgraph_pipeline.astream(initial_state):
                for node_name, updated_state in state_update.items():
                    logger.info("[Workflow] user_id=%d finished node: %s", current_user.id, node_name)
                    final_state.update(updated_state)
                    yield f"data: {json.dumps(updated_state)}\n\n"
                    await asyncio.sleep(0.5)  # Small delay for UX visual feel
        except Exception as exc:
            logger.error("[Workflow] Pipeline error for user_id=%d: %s", current_user.id, exc)
            yield f"data: {json.dumps({'status': 'ERROR', 'error': str(exc)})}\n\n"
            return

        # ── Step 5: Post-pipeline credit consumption ─────────────────
        credits_used = final_state.get("credits_consumed", 0)
        if credits_used > 0:
            try:
                # Re-fetch user to get fresh state
                from sqlalchemy import select
                result = await db.execute(select(User).where(User.id == current_user.id))
                fresh_user = result.scalar_one_or_none()
                if fresh_user:
                    await consume_credits(
                        db=db,
                        user=fresh_user,
                        credits=credits_used,
                        action_type="workflow_run",
                        model_used=final_state.get("video_source", video_model),
                        description=f"Workflow run: {final_state.get('selected_article', {}).get('title', 'Unknown')}",
                    )
            except Exception as exc:
                logger.error("[Workflow] Failed to consume credits for user_id=%d: %s", current_user.id, exc)

        # Send final done signal with credit info
        done_payload = {
            "status": "DONE",
            "credits_consumed": credits_used,
            "credits_remaining": (current_user.video_credits_remaining or 0) - credits_used,
            "tier": tier,
            "video_model": video_model,
        }
        yield f"data: {json.dumps(done_payload)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/credits/status")
async def get_credits_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the current credit status for the authenticated user.
    Used by the dashboard to render the credits/tier widget.
    """
    from app.services.credit_service import get_user_credits
    return await get_user_credits(db, current_user.id)


@router.post("/regenerate-video")
async def regenerate_video(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Regenerates a video asset from the HITL screen.
    Consumes credits based on the user's tier model.

    Pro: 1 credit (Kling AI)
    Max: 1 credit (Kling) or 3 credits (Runway/Sora)
    Free: stock only (0 credits)
    """
    tier = current_user.tier_level or "free"
    video_model = get_video_model_for_tier(tier)

    # Override model if explicitly requested and user is max tier
    requested_model = payload.get("model")
    if requested_model and tier == "max" and requested_model in ("runway", "sora"):
        video_model = requested_model

    # Check credits
    try:
        credit_cost = await check_video_credits(db, current_user, model=video_model)
    except InsufficientCreditsError as e:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "insufficient_credits",
                "message": str(e),
                "required": e.required,
                "available": e.available,
                "tier": e.tier,
            },
        )

    # Consume credits
    if credit_cost > 0:
        await consume_credits(
            db=db,
            user=current_user,
            credits=credit_cost,
            action_type="regenerate",
            model_used=video_model,
            description=f"Video regeneration via HITL (model={video_model})",
        )

    # TODO: Actually call the video generation API here
    # For now, return a placeholder video URL
    return {
        "status": "success",
        "video_url": "https://www.w3schools.com/html/mov_bbb.mp4",
        "model_used": video_model,
        "credits_consumed": credit_cost,
        "credits_remaining": current_user.video_credits_remaining or 0,
    }
