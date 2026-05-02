# app/services/workflow/nodes.py
"""
KontentPyper - LangGraph Pipeline Nodes
Each function is a single node in the workflow state machine.
Nodes receive and return the full WorkflowState TypedDict.
"""

import asyncio
import json
import logging
import time
from datetime import datetime

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.models.content import ContentSource
from app.models.workflow import ContentCandidate
from app.services.ai.llm_client import LLMClient
from app.services.ai.script_generator import generate_video_script
from app.services.ingest.reddit_fetcher import fetch_all_reddit, fetch_user_reddit
from app.services.ingest.rss_fetcher import fetch_all_rss, fetch_user_rss
from app.services.media.stock_video_pipeline import (
    StockVideoPipelineError,
    StockVideoPipelineService,
)
from app.services.workflow.state import WorkflowState
from app.schemas.content import ScriptPoint, VideoScript

logger = logging.getLogger(__name__)

_GLOBAL_FALLBACK_CACHE = {
    "fetched_at_monotonic": 0.0,
    "items": [],
}


async def _fetch_with_timeout(func, *args, timeout_seconds: int = 8):
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(func, *args),
            timeout=float(timeout_seconds),
        )
    except Exception:
        return []


async def fetch_node(state: WorkflowState):
    """Fetch articles from user-configured sources, with global fallback."""
    state["status"] = "Fetching articles..."
    user_id = state.get("user_id")
    workflow_run_id = state.get("workflow_run_id")
    policy = state.get("workflow_policy") or {}

    fetch_timeout_seconds = int(policy.get("fetch_timeout_seconds", 8))
    max_candidates = int(policy.get("max_candidates", 20))
    cache_ttl = int(policy.get("global_cache_ttl_seconds", 300))

    articles = []
    source_strategy = "global_fallback"

    async with AsyncSessionLocal() as db:
        user_sources = (await db.execute(
            select(ContentSource).where(
                ContentSource.user_id == user_id,
                ContentSource.is_active == True,
            )
        )).scalars().all()

        if user_sources:
            rss_sources = [source for source in user_sources if source.source_type == "rss"]
            reddit_sources = [source for source in user_sources if source.source_type == "reddit"]

            if rss_sources:
                articles.extend(await _fetch_with_timeout(
                    fetch_user_rss, rss_sources, timeout_seconds=fetch_timeout_seconds
                ))
            if reddit_sources:
                articles.extend(await _fetch_with_timeout(
                    fetch_user_reddit, reddit_sources, timeout_seconds=fetch_timeout_seconds
                ))
            source_strategy = "user_sources"

        if not articles:
            now_mono = time.monotonic()
            cache_age = now_mono - float(_GLOBAL_FALLBACK_CACHE["fetched_at_monotonic"])
            if _GLOBAL_FALLBACK_CACHE["items"] and cache_age < cache_ttl:
                articles.extend(_GLOBAL_FALLBACK_CACHE["items"])
            else:
                fallback_items = []
                fallback_items.extend(await _fetch_with_timeout(
                    fetch_all_rss, timeout_seconds=fetch_timeout_seconds
                ))
                fallback_items.extend(await _fetch_with_timeout(
                    fetch_all_reddit, timeout_seconds=fetch_timeout_seconds
                ))
                _GLOBAL_FALLBACK_CACHE["items"] = fallback_items
                _GLOBAL_FALLBACK_CACHE["fetched_at_monotonic"] = now_mono
                articles.extend(fallback_items)
            source_strategy = "global_fallback"

        if max_candidates > 0:
            articles = articles[:max_candidates]

        if workflow_run_id and articles:
            candidates = []
            for item in articles:
                normalized_payload = json.loads(json.dumps(item, default=str))
                candidates.append(ContentCandidate(
                    run_id=workflow_run_id,
                    user_id=user_id,
                    source_id=item.get("source_id"),
                    source_type=item.get("source_type", "rss"),
                    source_name=item.get("source_name"),
                    title=item.get("title", "Untitled"),
                    url=item.get("url", ""),
                    summary=item.get("snippet", ""),
                    image_url=item.get("image_url"),
                    published_at=item.get("published_date"),
                    raw_payload=normalized_payload,
                ))
            if candidates:
                db.add_all(candidates)
                await db.commit()

    state["articles"] = articles
    state["source_strategy"] = source_strategy
    return state


async def score_node(state: WorkflowState):
    """Score articles based on relevance to the user's niche."""
    state["status"] = "Scoring articles for relevance..."
    articles = state.get("articles", [])
    niche = state.get("niche", "Technology and AI")
    policy = state.get("workflow_policy") or {}
    score_top_k = int(policy.get("score_top_k", 5))
    text_model = policy.get("llm_text_model", "gpt-4o-mini")

    if not articles:
        return state

    client = LLMClient(model=text_model)
    best_article = None
    best_score = -1

    for article in articles[: max(1, score_top_k)]:
        prompt = (
            f"Score this article from 1 to 10 on how relevant it is to the niche: '{niche}'. "
            "Return ONLY the integer score.\n"
            f"Title: {article['title']}\n"
            f"Snippet: {article['snippet']}"
        )
        try:
            response = await client.generate_text("You are an expert news curator.", prompt)
            score = int(response.strip())
        except Exception:
            score = 5

        if score > best_score:
            best_score = score
            best_article = article

    selected = best_article or articles[0]
    selected["source_strategy"] = state.get("source_strategy")
    state["selected_article"] = selected

    workflow_run_id = state.get("workflow_run_id")
    if workflow_run_id and selected.get("url"):
        async with AsyncSessionLocal() as db:
            candidate = (await db.execute(
                select(ContentCandidate).where(
                    ContentCandidate.run_id == workflow_run_id,
                    ContentCandidate.url == selected.get("url"),
                ).limit(1)
            )).scalar_one_or_none()
            if candidate:
                candidate.selected = True
                candidate.rank_score = float(best_score if best_score >= 0 else 0.0)
                candidate.rank_features = {
                    "niche": niche,
                    "scored_at": datetime.utcnow().isoformat(),
                }
                await db.commit()

    return state


async def draft_node(state: WorkflowState):
    """Draft content for different platforms."""
    state["status"] = "Drafting captions and scripts..."
    article = state.get("selected_article")
    if not article:
        return state

    policy = state.get("workflow_policy") or {}
    text_model = policy.get("llm_text_model", "gpt-4o-mini")
    platforms = policy.get("target_platforms") or state.get("target_platforms") or ["twitter", "linkedin"]
    platforms = [platform.lower() for platform in platforms]

    client = LLMClient(model=text_model)
    scripts = {}

    for platform in platforms:
        prompt = (
            f"Write a compelling {platform} post based on this article. "
            "Keep it professional and engaging.\n\n"
            f"Title: {article['title']}\n"
            f"Snippet: {article['snippet']}"
        )
        try:
            scripts[platform] = await client.generate_text(
                "You are an expert social media manager.", prompt
            )
        except Exception as exc:
            logger.error("Failed to draft for %s: %s", platform, exc)
            scripts[platform] = (
                f"{article.get('title', 'Trending update')}\n\n"
                f"{article.get('snippet', '')}\n\n"
                "#content #trending"
            ).strip()

    state["scripts"] = scripts
    return state


async def generate_media_node(state: WorkflowState):
    """
    Generate media (video) based on user tier and selected video model.
    """
    state["status"] = "Generating media assets..."
    user_id = int(state.get("user_id") or 0)
    canary_percent = max(0, min(int(settings.ROLLOUT_CANARY_PERCENT or 0), 100))
    in_canary = (user_id % 100) < canary_percent if user_id > 0 else canary_percent >= 100

    if not settings.FEATURE_REAL_VIDEO_PIPELINE or not in_canary:
        state["video_asset"] = None
        state["video_source"] = None
        state["credits_consumed"] = 0
        state["status"] = "Real video pipeline disabled by rollout policy."
        return state
    article = state.get("selected_article")
    video_model = state.get("video_model", "stock")
    policy = state.get("workflow_policy") or {}

    if article:
        try:
            try:
                video_script = await generate_video_script(
                    article["title"],
                    article.get("snippet", ""),
                    article.get("source_name", "Unknown"),
                )
            except Exception as script_exc:
                logger.warning(
                    "LLM video script generation failed. Using deterministic fallback: %s",
                    script_exc,
                )
                fallback_title = article.get("title", "Trending update")
                fallback_snippet = article.get("snippet", "")
                video_script = VideoScript(
                    title=fallback_title[:60],
                    hook=fallback_title,
                    points=[
                        ScriptPoint(text=fallback_snippet[:220] or fallback_title, visual_cue="news footage"),
                        ScriptPoint(text="Here is why this matters right now.", visual_cue="data visualization"),
                        ScriptPoint(text="Follow for more updates.", visual_cue="call to action"),
                    ],
                    cta="Follow for more updates.",
                    hashtags=["news", "update", "trending"],
                    search_query=fallback_title,
                )

            # Until premium providers are wired, always generate a real stock-backed asset.
            # This guarantees a real video output and avoids placeholder URLs.
            stock_pipeline = StockVideoPipelineService()
            generated = await stock_pipeline.generate_video(
                script=video_script,
                fallback_title=article.get("title", "Trending update"),
                fallback_snippet=article.get("snippet", ""),
            )
            state["video_asset"] = generated["video_url"]
            state["video_source"] = "pexels_stock"
            state["credits_consumed"] = 0
            state["status"] = (
                f"Media generated via stock pipeline ({generated.get('storage_backend', 'unknown')})."
            )

            state["video_script"] = {
                "title": video_script.title,
                "hook": video_script.hook,
                "points": [{"text": point.text, "visual_cue": point.visual_cue} for point in video_script.points],
                "cta": video_script.cta,
                "hashtags": video_script.hashtags,
                "narration": video_script.full_narration,
                "search_query": video_script.search_query,
                "review_required": policy.get("require_review", False),
                "max_videos_per_run": policy.get("max_videos_per_run", 1),
                "requested_video_model": video_model,
            }
        except StockVideoPipelineError as exc:
            logger.error("Stock video generation failed: %s", exc)
            state["video_asset"] = None
            state["video_source"] = None
            state["credits_consumed"] = 0
            state["status"] = f"Media generation failed: {exc}"
        except Exception as exc:
            logger.error("Failed to generate video script or media: %s", exc)
            state["video_asset"] = None
            state["video_source"] = None
            state["credits_consumed"] = 0
            state["status"] = "Media generation failed unexpectedly."

    if state.get("video_asset"):
        state["status"] = "Workflow complete"
    else:
        state["status"] = "Workflow complete (video generation failed)"
    return state
