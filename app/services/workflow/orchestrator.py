"""
KontentPyper - Unified Workflow Orchestrator
Provides canonical run lifecycle tracking across manual, scheduled, and campaign triggers.
"""

import logging
import json
import uuid
import time
from datetime import datetime
from typing import Any, Awaitable, Callable, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import WorkflowRun, RunEvent, RunArtifact, QualityEvaluation
from app.services.workflow.langgraph_pipeline import langgraph_pipeline

logger = logging.getLogger(__name__)

NodeCallback = Callable[[str, dict], Awaitable[None]]


class WorkflowOrchestrator:
    """Lifecycle and execution wrapper around the LangGraph pipeline."""

    @staticmethod
    def _normalize_json(payload: Optional[dict]) -> Optional[dict]:
        if payload is None:
            return None
        return json.loads(json.dumps(payload, default=str))

    @staticmethod
    async def create_run(
        db: AsyncSession,
        *,
        user_id: int,
        trigger_type: str,
        trigger_ref: Optional[str] = None,
        plan_tier: Optional[str] = None,
        video_model: Optional[str] = None,
        initial_state: Optional[dict] = None,
    ) -> WorkflowRun:
        run = WorkflowRun(
            run_key=str(uuid.uuid4()),
            user_id=user_id,
            trigger_type=trigger_type,
            trigger_ref=trigger_ref,
            status="queued",
            plan_tier=plan_tier,
            video_model=video_model,
            initial_state=WorkflowOrchestrator._normalize_json(initial_state),
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)
        return run

    @staticmethod
    async def log_event(
        db: AsyncSession,
        *,
        run_id: int,
        event_type: str,
        node: Optional[str] = None,
        payload: Optional[dict] = None,
    ) -> None:
        event = RunEvent(
            run_id=run_id,
            event_type=event_type,
            node=node,
            payload=WorkflowOrchestrator._normalize_json(payload),
        )
        db.add(event)
        await db.commit()

    @staticmethod
    async def mark_started(db: AsyncSession, run: WorkflowRun) -> None:
        run.status = "running"
        run.pipeline_node = "init"
        run.started_at = datetime.utcnow()
        await db.commit()
        await WorkflowOrchestrator.log_event(
            db,
            run_id=run.id,
            event_type="run_started",
            node="init",
            payload={"run_key": run.run_key},
        )

    @staticmethod
    async def mark_completed(db: AsyncSession, run: WorkflowRun, final_state: dict) -> None:
        completed_at = datetime.utcnow()
        run.status = "completed"
        run.completed_at = completed_at
        quality_summary = await WorkflowOrchestrator._persist_quality_evaluations(
            db=db,
            run=run,
            final_state=final_state,
        )
        final_state["quality_summary"] = quality_summary
        final_state["quality_passed"] = quality_summary.get("passed", True)
        run.final_state = WorkflowOrchestrator._normalize_json(final_state)
        if run.started_at:
            run.duration_seconds = (completed_at - run.started_at).total_seconds()
        await db.commit()
        await WorkflowOrchestrator._persist_run_artifacts(
            db=db,
            run_id=run.id,
            final_state=final_state,
        )
        await WorkflowOrchestrator.log_event(
            db,
            run_id=run.id,
            event_type="run_completed",
            node=run.pipeline_node,
            payload={"duration_seconds": run.duration_seconds},
        )
        await WorkflowOrchestrator.log_event(
            db,
            run_id=run.id,
            event_type="quality_summary",
            node=run.pipeline_node,
            payload=quality_summary,
        )

    @staticmethod
    def _build_quality_checks(final_state: dict) -> list[dict]:
        policy = final_state.get("workflow_policy") or {}
        min_script_chars = int(policy.get("min_script_chars", 80))
        scripts = final_state.get("scripts") or {}
        selected_article = final_state.get("selected_article") or {}
        video_asset = final_state.get("video_asset")
        source_strategy = final_state.get("source_strategy", "unknown")

        script_lengths = [len((text or "").strip()) for text in scripts.values()]
        avg_script_length = (
            float(sum(script_lengths) / len(script_lengths))
            if script_lengths else 0.0
        )

        return [
            {
                "criterion": "has_selected_article",
                "score": 1.0 if bool(selected_article.get("url")) else 0.0,
                "passed": bool(selected_article.get("url")),
                "notes": "Selected article exists for downstream generation.",
                "metadata_json": {"article_url": selected_article.get("url")},
                "critical": True,
            },
            {
                "criterion": "has_platform_drafts",
                "score": 1.0 if bool(scripts) else 0.0,
                "passed": bool(scripts),
                "notes": "At least one platform draft was generated.",
                "metadata_json": {"platforms": list(scripts.keys())},
                "critical": True,
            },
            {
                "criterion": "draft_length_minimum",
                "score": min(1.0, avg_script_length / float(max(min_script_chars, 1))),
                "passed": avg_script_length >= float(min_script_chars),
                "notes": "Average draft length meets tier threshold.",
                "metadata_json": {
                    "avg_script_length": avg_script_length,
                    "min_script_chars": min_script_chars,
                },
                "critical": False,
            },
            {
                "criterion": "has_video_asset",
                "score": 1.0 if bool(video_asset) else 0.0,
                "passed": bool(video_asset),
                "notes": "Video/media asset generated.",
                "metadata_json": {"video_asset": video_asset},
                "critical": True,
            },
            {
                "criterion": "source_strategy",
                "score": 1.0 if source_strategy == "user_sources" else 0.6,
                "passed": True,
                "notes": "Run used user sources when available; fallback is tolerated.",
                "metadata_json": {"source_strategy": source_strategy},
                "critical": False,
            },
        ]

    @staticmethod
    async def _persist_quality_evaluations(
        db: AsyncSession,
        *,
        run: WorkflowRun,
        final_state: dict,
    ) -> dict:
        checks = WorkflowOrchestrator._build_quality_checks(final_state)
        quality_rows = []
        total_score = 0.0
        critical_failed = []

        for check in checks:
            total_score += float(check["score"])
            if check.get("critical") and not check["passed"]:
                critical_failed.append(check["criterion"])
            quality_rows.append(
                QualityEvaluation(
                    run_id=run.id,
                    criterion=check["criterion"],
                    score=float(check["score"]),
                    passed=bool(check["passed"]),
                    notes=check["notes"],
                    metadata_json=WorkflowOrchestrator._normalize_json(
                        check.get("metadata_json")
                    ),
                )
            )

        if quality_rows:
            db.add_all(quality_rows)
            await db.commit()

        avg_score = total_score / float(max(len(checks), 1))
        passed = len(critical_failed) == 0
        return {
            "passed": passed,
            "score": round(avg_score, 4),
            "critical_failures": critical_failed,
            "criteria_count": len(checks),
        }

    @staticmethod
    async def _persist_run_artifacts(
        db: AsyncSession,
        *,
        run_id: int,
        final_state: dict,
    ) -> None:
        artifacts: list[RunArtifact] = []
        scripts = final_state.get("scripts") or {}
        for platform, text in scripts.items():
            artifacts.append(
                RunArtifact(
                    run_id=run_id,
                    artifact_type="platform_draft",
                    platform=str(platform).lower(),
                    title=f"{platform.title()} Draft",
                    content=text,
                    metadata_json={"kind": "caption"},
                )
            )

        selected_article = final_state.get("selected_article") or {}
        video_script = final_state.get("video_script")
        if video_script:
            artifacts.append(
                RunArtifact(
                    run_id=run_id,
                    artifact_type="video_script",
                    title=selected_article.get("title"),
                    content=video_script.get("narration"),
                    metadata_json=WorkflowOrchestrator._normalize_json(video_script),
                )
            )

        if final_state.get("video_asset"):
            artifacts.append(
                RunArtifact(
                    run_id=run_id,
                    artifact_type="video_asset",
                    title=selected_article.get("title"),
                    media_url=final_state.get("video_asset"),
                    metadata_json={
                        "video_source": final_state.get("video_source"),
                        "credits_consumed": final_state.get("credits_consumed", 0),
                    },
                )
            )

        if artifacts:
            db.add_all(artifacts)
            await db.commit()

    @staticmethod
    async def mark_failed(
        db: AsyncSession,
        run: WorkflowRun,
        exc: Exception,
        partial_state: Optional[dict] = None,
    ) -> None:
        completed_at = datetime.utcnow()
        run.status = "failed"
        run.error_message = str(exc)
        run.completed_at = completed_at
        run.final_state = WorkflowOrchestrator._normalize_json(partial_state)
        if run.started_at:
            run.duration_seconds = (completed_at - run.started_at).total_seconds()
        await db.commit()
        await WorkflowOrchestrator.log_event(
            db,
            run_id=run.id,
            event_type="run_failed",
            node=run.pipeline_node,
            payload={"error": str(exc)},
        )

    @staticmethod
    async def execute(
        db: AsyncSession,
        *,
        run: WorkflowRun,
        initial_state: dict,
        on_node: Optional[NodeCallback] = None,
    ) -> Tuple[dict, Optional[Exception]]:
        """
        Executes LangGraph without streaming and returns final state + optional error.
        """
        initial_state = initial_state.copy()
        initial_state["workflow_run_id"] = run.id
        initial_state["run_key"] = run.run_key
        policy = initial_state.get("workflow_policy") or {}
        max_runtime_seconds = float(policy.get("max_runtime_seconds", 75))
        started_monotonic = time.monotonic()
        final_state = initial_state.copy()
        await WorkflowOrchestrator.mark_started(db, run)

        try:
            async for state_update in langgraph_pipeline.astream(initial_state):
                for node_name, updated_state in state_update.items():
                    run.pipeline_node = node_name
                    final_state.update(updated_state)
                    await db.commit()
                    await WorkflowOrchestrator.log_event(
                        db,
                        run_id=run.id,
                        event_type="node_completed",
                        node=node_name,
                        payload=updated_state,
                    )
                    if on_node:
                        await on_node(node_name, updated_state)
                    elapsed = time.monotonic() - started_monotonic
                    if elapsed > max_runtime_seconds:
                        raise TimeoutError(
                            f"Workflow exceeded runtime budget ({elapsed:.2f}s > {max_runtime_seconds:.2f}s)"
                        )

            await WorkflowOrchestrator.mark_completed(db, run, final_state)
            return final_state, None
        except Exception as exc:
            logger.error("[Orchestrator] run_key=%s failed: %s", run.run_key, exc, exc_info=True)
            await WorkflowOrchestrator.mark_failed(db, run, exc, final_state)
            return final_state, exc

    @staticmethod
    async def stream(
        db: AsyncSession,
        *,
        run: WorkflowRun,
        initial_state: dict,
    ):
        """
        Streams node updates from LangGraph while persisting canonical lifecycle events.
        Yields raw node update dictionaries.
        """
        initial_state = initial_state.copy()
        initial_state["workflow_run_id"] = run.id
        initial_state["run_key"] = run.run_key
        policy = initial_state.get("workflow_policy") or {}
        max_runtime_seconds = float(policy.get("max_runtime_seconds", 75))
        started_monotonic = time.monotonic()
        final_state = initial_state.copy()
        await WorkflowOrchestrator.mark_started(db, run)

        try:
            async for state_update in langgraph_pipeline.astream(initial_state):
                for node_name, updated_state in state_update.items():
                    run.pipeline_node = node_name
                    final_state.update(updated_state)
                    await db.commit()
                    await WorkflowOrchestrator.log_event(
                        db,
                        run_id=run.id,
                        event_type="node_completed",
                        node=node_name,
                        payload=updated_state,
                    )
                    yield updated_state
                    elapsed = time.monotonic() - started_monotonic
                    if elapsed > max_runtime_seconds:
                        raise TimeoutError(
                            f"Workflow exceeded runtime budget ({elapsed:.2f}s > {max_runtime_seconds:.2f}s)"
                        )

            await WorkflowOrchestrator.mark_completed(db, run, final_state)
        except Exception as exc:
            logger.error("[Orchestrator] run_key=%s stream failed: %s", run.run_key, exc, exc_info=True)
            await WorkflowOrchestrator.mark_failed(db, run, exc, final_state)
            yield {"status": "ERROR", "error": str(exc)}
