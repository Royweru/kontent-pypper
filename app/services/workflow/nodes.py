# app/services/workflow/nodes.py
"""
KontentPyper - LangGraph Pipeline Nodes
Each function is a single node in the workflow state machine.
Nodes receive and return the full WorkflowState TypedDict.
"""

import logging
from app.services.workflow.state import WorkflowState
from app.services.ingest.rss_fetcher import fetch_all_rss
from app.services.ai.script_generator import generate_video_script
from app.services.ai.llm_client import LLMClient
from app.core.config import settings

logger = logging.getLogger(__name__)


# ── Node 1: Fetch ─────────────────────────────────────────────────────
async def fetch_node(state: WorkflowState):
    """Fetch latest articles from configured RSS feeds."""
    state["status"] = "Fetching articles..."
    # In a full impl, we'd fetch based on user's selected feeds from ContentSource
    # For now, we use the global rss fetcher strategy.
    articles = fetch_all_rss()
    state["articles"] = articles
    return state


# ── Node 2: Score ─────────────────────────────────────────────────────
async def score_node(state: WorkflowState):
    """Score articles based on relevance to the user's niche."""
    state["status"] = "Scoring articles for relevance..."
    articles = state.get("articles", [])
    niche = state.get("niche", "Technology and AI")

    if not articles:
        return state

    client = LLMClient(model="gpt-4o-mini")

    best_article = None
    best_score = -1

    for article in articles[:5]:  # Score top 5 to save time/tokens
        prompt = (
            f"Score this article from 1 to 10 on how relevant it is to the niche: '{niche}'. "
            f"Return ONLY the integer score.\n"
            f"Title: {article['title']}\n"
            f"Snippet: {article['snippet']}"
        )
        try:
            res = await client.generate_text("You are an expert news curator.", prompt)
            score = int(res.strip())
        except Exception:
            score = 5

        if score > best_score:
            best_score = score
            best_article = article

    state["selected_article"] = best_article or articles[0]
    return state


# ── Node 3: Draft ─────────────────────────────────────────────────────
async def draft_node(state: WorkflowState):
    """Draft content for different platforms."""
    state["status"] = "Drafting captions and scripts..."
    article = state.get("selected_article")

    if not article:
        return state

    client = LLMClient(model="gpt-4o-mini")

    platforms = ["twitter", "linkedin"]
    scripts = {}

    for platform in platforms:
        prompt = (
            f"Write a compelling {platform} post based on this article. "
            f"Keep it professional and engaging.\n\n"
            f"Title: {article['title']}\n"
            f"Snippet: {article['snippet']}"
        )
        try:
            res = await client.generate_text("You are an expert social media manager.", prompt)
            scripts[platform] = res
        except Exception as e:
            logger.error(f"Failed to draft for {platform}: {e}")

    state["scripts"] = scripts
    return state


# ── Node 4: Generate Media ───────────────────────────────────────────
async def generate_media_node(state: WorkflowState):
    """
    Generate media (video) based on user tier.

    Credit gating logic:
      - free tier: Always uses Pexels stock video (0 credits)
      - pro tier:  Uses Kling AI (1 credit per video)
      - max tier:  Uses Runway Gen-4 (3 credits per video)

    If a paid user has no credits remaining, falls back to stock video.
    Credit consumption is handled by the workflow endpoint (not here)
    so that the database session is properly managed.
    """
    state["status"] = "Generating media assets..."
    article = state.get("selected_article")
    tier = state.get("tier_level", "free")
    video_model = state.get("video_model", "stock")

    if article:
        try:
            # Generate the video script from our existing generator
            video_script = await generate_video_script(
                article["title"],
                article.get("snippet", ""),
                article.get("source_name", "Unknown"),
            )

            if video_model == "stock":
                # FREE TIER: Stock video from Pexels + MoviePy
                state["video_asset"] = "https://www.w3schools.com/html/mov_bbb.mp4"
                state["video_source"] = "pexels_stock"
                state["credits_consumed"] = 0
                logger.info("[MediaNode] Generated stock video (0 credits)")
            elif video_model == "kling":
                # PRO TIER: Kling AI via Fal.ai (placeholder for actual API call)
                state["video_asset"] = "https://www.w3schools.com/html/mov_bbb.mp4"
                state["video_source"] = "kling_ai"
                state["credits_consumed"] = 1
                logger.info("[MediaNode] Generated Kling AI video (1 credit)")
            elif video_model in ("runway", "sora"):
                # MAX TIER: Runway Gen-4 or Sora-2 (placeholder for actual API call)
                state["video_asset"] = "https://www.w3schools.com/html/mov_bbb.mp4"
                state["video_source"] = f"{video_model}_premium"
                state["credits_consumed"] = 3
                logger.info("[MediaNode] Generated %s premium video (3 credits)", video_model)
            else:
                # Fallback to stock
                state["video_asset"] = "https://www.w3schools.com/html/mov_bbb.mp4"
                state["video_source"] = "pexels_stock"
                state["credits_consumed"] = 0

            # Store the generated script data for HITL display
            state["video_script"] = {
                "title": video_script.title,
                "hook": video_script.hook,
                "points": [{"text": p.text, "visual_cue": p.visual_cue} for p in video_script.points],
                "cta": video_script.cta,
                "hashtags": video_script.hashtags,
                "narration": video_script.full_narration,
            }

        except Exception as e:
            logger.error(f"Failed to generate video script or media: {e}")
            state["video_asset"] = None
            state["credits_consumed"] = 0

    state["status"] = "Workflow complete"
    return state