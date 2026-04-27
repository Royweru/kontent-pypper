"""
KontentPyper - Workflow API Endpoint
Executes the LangGraph pipeline with credit gating, tier checks,
and SSE streaming for the live tracker UI.
"""

import json
import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.database import get_db
from app.core.verification import require_verified_email
from app.models.user import User
from app.models.workflow import WorkflowRun, RunEvent, QualityEvaluation
from app.services.workflow.orchestrator import WorkflowOrchestrator
from app.services.workflow.policy import build_workflow_policy
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

router = APIRouter()

NODE_SEQUENCE = ["fetch", "score", "draft", "generate_media"]
NODE_LABELS = {
    "fetch": "Fetching News Feeds",
    "score": "Analyzing Subreddits",
    "draft": "Generating Content",
    "generate_media": "Creating Videos",
}


def _to_sse_data(payload: dict) -> str:
    """
    Serialize payload safely for SSE. Handles datetime and other non-JSON-native values.
    """
    return f"data: {json.dumps(jsonable_encoder(payload))}\n\n"


def _node_progress(node: str | None) -> dict:
    total = len(NODE_SEQUENCE)
    if node not in NODE_SEQUENCE:
        return {
            "node_index": 0,
            "node_total": total,
            "percent": 0.0,
            "next_node": NODE_SEQUENCE[0] if NODE_SEQUENCE else None,
            "next_node_label": NODE_LABELS.get(NODE_SEQUENCE[0]) if NODE_SEQUENCE else None,
        }

    idx = NODE_SEQUENCE.index(node) + 1
    next_node = NODE_SEQUENCE[idx] if idx < total else None
    return {
        "node_index": idx,
        "node_total": total,
        "percent": round((idx / total) * 100.0, 2),
        "next_node": next_node,
        "next_node_label": NODE_LABELS.get(next_node) if next_node else None,
    }


def _serialize_run_summary(run: WorkflowRun, quality_summary: dict | None = None) -> dict:
    return {
        "run_key": run.run_key,
        "status": run.status,
        "pipeline_node": run.pipeline_node,
        "trigger_type": run.trigger_type,
        "trigger_ref": run.trigger_ref,
        "plan_tier": run.plan_tier,
        "video_model": run.video_model,
        "duration_seconds": run.duration_seconds,
        "error_message": run.error_message,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "quality_summary": quality_summary or {},
    }


@router.get("/runs")
async def list_workflow_runs(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    limit = max(1, min(limit, 100))
    runs = (await db.execute(
        select(WorkflowRun)
        .where(WorkflowRun.user_id == current_user.id)
        .order_by(desc(WorkflowRun.created_at))
        .limit(limit)
    )).scalars().all()

    items = []
    for run in runs:
        quality_summary = {}
        if isinstance(run.final_state, dict):
            quality_summary = run.final_state.get("quality_summary") or {}
        items.append(_serialize_run_summary(run, quality_summary=quality_summary))

    return {"items": items, "count": len(items)}


@router.get("/runs/{run_key}")
async def get_workflow_run(
    run_key: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    run = (await db.execute(
        select(WorkflowRun).where(
            WorkflowRun.run_key == run_key,
            WorkflowRun.user_id == current_user.id,
        )
    )).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")

    events = (await db.execute(
        select(RunEvent)
        .where(RunEvent.run_id == run.id)
        .order_by(RunEvent.created_at.asc())
    )).scalars().all()

    evaluations = (await db.execute(
        select(QualityEvaluation)
        .where(QualityEvaluation.run_id == run.id)
        .order_by(QualityEvaluation.created_at.asc())
    )).scalars().all()

    quality_summary = {}
    if isinstance(run.final_state, dict):
        quality_summary = run.final_state.get("quality_summary") or {}

    return {
        "run": _serialize_run_summary(run, quality_summary=quality_summary),
        "events": [
            {
                "event_type": event.event_type,
                "node": event.node,
                "payload": event.payload,
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
            for event in events
        ],
        "quality_evaluations": [
            {
                "criterion": evaluation.criterion,
                "score": evaluation.score,
                "passed": evaluation.passed,
                "notes": evaluation.notes,
                "metadata_json": evaluation.metadata_json,
                "created_at": (
                    evaluation.created_at.isoformat()
                    if evaluation.created_at else None
                ),
            }
            for evaluation in evaluations
        ],
        "initial_state": run.initial_state,
        "final_state": run.final_state,
    }


def _build_initial_state(current_user: User, *, tier: str, video_model: str, workflow_policy: dict) -> dict:
    return {
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
        "workflow_policy": workflow_policy,
        "status": "Starting pipeline...",
    }


async def _prepare_manual_run(
    current_user: User,
    db: AsyncSession,
    *,
    trigger_ref: str,
) -> tuple[WorkflowRun, dict, str, str, dict]:
    """Validate policy/limits and create a queued manual run."""
    require_verified_email(current_user)

    try:
        await check_workflow_run_allowed(db, current_user)
    except DailyRunLimitError as exc:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "daily_limit_reached",
                "message": str(exc),
                "max_runs": exc.max_runs,
                "upgrade_to": "pro",
            },
        )

    tier = current_user.tier_level or "free"
    video_model = get_video_model_for_tier(tier)
    workflow_policy = build_workflow_policy(tier_level=tier)

    if video_model != "stock":
        try:
            await check_video_credits(db, current_user, model=video_model)
        except InsufficientCreditsError:
            logger.warning(
                "[Workflow] user_id=%d has no credits for %s. Falling back to stock.",
                current_user.id,
                video_model,
            )
            video_model = "stock"

    await increment_daily_runs(db, current_user)

    initial_state = _build_initial_state(
        current_user,
        tier=tier,
        video_model=video_model,
        workflow_policy=workflow_policy,
    )

    run = await WorkflowOrchestrator.create_run(
        db=db,
        user_id=current_user.id,
        trigger_type="manual",
        trigger_ref=trigger_ref,
        plan_tier=tier,
        video_model=video_model,
        initial_state=initial_state,
    )

    initial_state["run_key"] = run.run_key
    run.initial_state = jsonable_encoder(initial_state)
    await db.commit()

    return run, initial_state, tier, video_model, workflow_policy


async def _workflow_event_stream(
    *,
    db: AsyncSession,
    run: WorkflowRun,
    initial_state: dict,
    current_user: User,
    tier: str,
    video_model: str,
    workflow_policy: dict,
):
    """Canonical SSE stream for a queued workflow run."""
    stream_delay_seconds = float(workflow_policy.get("event_delay_seconds", 0.05))
    initial_progress = _node_progress(None)

    yield _to_sse_data(
        {
            "event_type": "run_started",
            "run_key": run.run_key,
            "node": "init",
            "status": "RUNNING",
            "message": "Workflow run started.",
            "state": initial_state,
            "progress": initial_progress,
            "ts": datetime.utcnow().isoformat(),
        }
    )
    if initial_progress.get("next_node"):
        yield _to_sse_data(
            {
                "event_type": "node_started",
                "run_key": run.run_key,
                "node": initial_progress["next_node"],
                "status": "IN_PROGRESS",
                "message": f"Starting {initial_progress.get('next_node_label') or initial_progress['next_node']}.",
                "progress": initial_progress,
                "ts": datetime.utcnow().isoformat(),
            }
        )

    final_state = initial_state.copy()

    async for stream_event in WorkflowOrchestrator.stream(
        db=db,
        run=run,
        initial_state=initial_state,
    ):
        if stream_event.get("event_type") == "run_failed":
            error_message = stream_event.get("error") or "Workflow execution failed."
            yield _to_sse_data(
                {
                    "event_type": "run_failed",
                    "run_key": run.run_key,
                    "node": run.pipeline_node,
                    "status": "ERROR",
                    "message": error_message,
                    "error": error_message,
                    "state": stream_event.get("state") or final_state,
                    "progress": _node_progress(run.pipeline_node),
                    "ts": datetime.utcnow().isoformat(),
                }
            )
            return

        node = stream_event.get("node")
        updated_state = stream_event.get("state") or {}
        final_state.update(updated_state)
        progress = _node_progress(node)
        yield _to_sse_data(
            {
                "event_type": "node_completed",
                "run_key": run.run_key,
                "node": node,
                "status": updated_state.get("status") or "NODE_COMPLETED",
                "message": updated_state.get("status") or "Node completed.",
                "state": updated_state,
                "progress": progress,
                "ts": datetime.utcnow().isoformat(),
            }
        )
        if progress.get("next_node"):
            yield _to_sse_data(
                {
                    "event_type": "node_started",
                    "run_key": run.run_key,
                    "node": progress["next_node"],
                    "status": "IN_PROGRESS",
                    "message": f"Starting {progress.get('next_node_label') or progress['next_node']}.",
                    "progress": progress,
                    "ts": datetime.utcnow().isoformat(),
                }
            )

        if stream_delay_seconds > 0:
            await asyncio.sleep(stream_delay_seconds)

    credits_used = int(final_state.get("credits_consumed") or 0)
    credits_remaining = current_user.video_credits_remaining or 0

    if credits_used > 0:
        try:
            result = await db.execute(select(User).where(User.id == current_user.id))
            fresh_user = result.scalar_one_or_none()
            if fresh_user:
                await consume_credits(
                    db=db,
                    user=fresh_user,
                    credits=credits_used,
                    action_type="workflow_run",
                    model_used=final_state.get("video_source", video_model),
                    description=(
                        f"Workflow run: "
                        f"{final_state.get('selected_article', {}).get('title', 'Unknown')}"
                    ),
                )
                credits_remaining = fresh_user.video_credits_remaining or 0
        except Exception as exc:
            logger.error(
                "[Workflow] Failed to consume credits for user_id=%d: %s",
                current_user.id,
                exc,
            )

    try:
        await WorkflowOrchestrator.log_event(
            db=db,
            run_id=run.id,
            event_type="cost_summary",
            node=run.pipeline_node,
            payload={
                "trigger_type": "manual",
                "plan_tier": tier,
                "video_model_requested": initial_state.get("video_model"),
                "video_model_used": final_state.get("video_source", video_model),
                "credits_consumed": credits_used,
                "billing_unit": "credits",
                "duration_seconds": run.duration_seconds,
                "quality_summary": final_state.get("quality_summary"),
            },
        )
    except Exception as exc:
        logger.warning(
            "[Workflow] Failed to emit cost_summary for run_key=%s: %s",
            run.run_key,
            exc,
        )

    yield _to_sse_data(
        {
            "event_type": "run_completed",
            "run_key": run.run_key,
            "node": run.pipeline_node,
            "status": "DONE",
            "message": "Workflow complete.",
            "credits_consumed": credits_used,
            "credits_remaining": credits_remaining,
            "tier": tier,
            "video_model": video_model,
            "review_required": workflow_policy.get("require_review", False),
            "quality_summary": final_state.get("quality_summary") or {},
            "quality_passed": bool(final_state.get("quality_passed", True)),
            "scripts": final_state.get("scripts") or {},
            "selected_article": final_state.get("selected_article"),
            "video_asset": final_state.get("video_asset"),
            "video_script": final_state.get("video_script"),
            "final_state": final_state,
            "progress": {
                "node_index": len(NODE_SEQUENCE),
                "node_total": len(NODE_SEQUENCE),
                "percent": 100.0,
                "next_node": None,
                "next_node_label": None,
            },
            "ts": datetime.utcnow().isoformat(),
        }
    )


@router.post("/runs")
async def create_workflow_run(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Canonical manual trigger endpoint. Creates a queued run and returns run metadata."""
    run, _initial_state, _tier, _video_model, _workflow_policy = await _prepare_manual_run(
        current_user,
        db,
        trigger_ref="api_workflow_runs_create",
    )
    logger.info(
        "[WorkflowAPI] Created run run_key=%s user_id=%d tier=%s model=%s",
        run.run_key,
        current_user.id,
        _tier,
        _video_model,
    )

    return {
        "run_key": run.run_key,
        "status": run.status,
        "stream_url": f"/api/v1/workflow/runs/{run.run_key}/stream",
        "run": _serialize_run_summary(run),
    }


@router.get("/runs/{run_key}/stream")
async def stream_workflow_run(
    run_key: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Canonical SSE stream endpoint for an existing queued workflow run."""
    run = (await db.execute(
        select(WorkflowRun).where(
            WorkflowRun.run_key == run_key,
            WorkflowRun.user_id == current_user.id,
        )
    )).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")

    logger.info(
        "[WorkflowAPI] Stream requested run_key=%s user_id=%d status=%s",
        run.run_key,
        current_user.id,
        run.status,
    )

    if run.status in ("completed", "failed"):
        async def finalized_generator():
            final_state = run.final_state if isinstance(run.final_state, dict) else {}
            event_type = "run_completed" if run.status == "completed" else "run_failed"
            message = "Workflow already completed." if run.status == "completed" else (run.error_message or "Workflow failed.")
            node = run.pipeline_node
            progress = (
                {
                    "node_index": len(NODE_SEQUENCE),
                    "node_total": len(NODE_SEQUENCE),
                    "percent": 100.0,
                    "next_node": None,
                    "next_node_label": None,
                }
                if run.status == "completed"
                else _node_progress(node)
            )
            yield _to_sse_data(
                {
                    "event_type": event_type,
                    "run_key": run.run_key,
                    "node": node,
                    "status": "DONE" if run.status == "completed" else "ERROR",
                    "message": message,
                    "scripts": final_state.get("scripts") or {},
                    "selected_article": final_state.get("selected_article"),
                    "video_asset": final_state.get("video_asset"),
                    "video_script": final_state.get("video_script"),
                    "quality_summary": final_state.get("quality_summary") or {},
                    "quality_passed": bool(final_state.get("quality_passed", run.status == "completed")),
                    "final_state": final_state,
                    "progress": progress,
                    "ts": datetime.utcnow().isoformat(),
                }
            )

        return StreamingResponse(finalized_generator(), media_type="text/event-stream")

    if run.status == "running":
        raise HTTPException(
            status_code=409,
            detail="Run is already streaming from another client.",
        )

    initial_state = run.initial_state if isinstance(run.initial_state, dict) else {}
    initial_state["run_key"] = run.run_key
    tier = run.plan_tier or current_user.tier_level or "free"
    video_model = run.video_model or get_video_model_for_tier(tier)
    workflow_policy = initial_state.get("workflow_policy") or build_workflow_policy(tier_level=tier)

    return StreamingResponse(
        _workflow_event_stream(
            db=db,
            run=run,
            initial_state=initial_state,
            current_user=current_user,
            tier=tier,
            video_model=video_model,
            workflow_policy=workflow_policy,
        ),
        media_type="text/event-stream",
    )


@router.post("/run")
async def run_workflow_legacy_post(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Backward-compatible one-shot stream endpoint (deprecated)."""
    run, initial_state, tier, video_model, workflow_policy = await _prepare_manual_run(
        current_user,
        db,
        trigger_ref="api_workflow_run_legacy_post",
    )

    return StreamingResponse(
        _workflow_event_stream(
            db=db,
            run=run,
            initial_state=initial_state,
            current_user=current_user,
            tier=tier,
            video_model=video_model,
            workflow_policy=workflow_policy,
        ),
        media_type="text/event-stream",
    )


@router.get("/run")
async def run_workflow_legacy_get(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Backward-compatible GET stream endpoint for older EventSource clients (deprecated)."""
    run, initial_state, tier, video_model, workflow_policy = await _prepare_manual_run(
        current_user,
        db,
        trigger_ref="api_workflow_run_legacy_get",
    )

    return StreamingResponse(
        _workflow_event_stream(
            db=db,
            run=run,
            initial_state=initial_state,
            current_user=current_user,
            tier=tier,
            video_model=video_model,
            workflow_policy=workflow_policy,
        ),
        media_type="text/event-stream",
    )


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
    require_verified_email(current_user)

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
