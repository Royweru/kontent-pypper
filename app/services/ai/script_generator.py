"""
KontentPyper - Video Script Generator
Uses the existing LLMClient (GPT-5 Nano) to generate structured video scripts
from a ContentItem (news article).
"""

import logging
from app.services.ai.llm_client import LLMClient
from app.schemas.content import VideoScript
from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert short-form video scriptwriter for TikTok, YouTube Shorts, and Instagram Reels.

Your job is to turn a tech/AI news headline into a viral 60-second video script.

Rules:
- The HOOK must be shocking, curiosity-driven, or contrarian. It plays in the first 3 seconds.
- Each POINT should be 1-2 sentences max. Simple language. No jargon.
- Write for someone scrolling fast. Every sentence must earn the next second.
- The CTA should drive engagement: "Follow for more", "Comment what you think", etc.
- Hashtags should mix broad (#AI #Tech) with niche (#GPT5 #AIAgents).
- The search_query should describe the visual theme for stock footage (e.g. "futuristic technology server room").
- Keep the total narration under 150 words for a 60-second video."""


async def generate_video_script(title: str, snippet: str, source: str) -> VideoScript:
    """
    Takes a news article's title and snippet, returns a fully structured VideoScript.
    Uses the existing LLMClient with GPT-5 Nano and structured output.
    """
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not configured")

    client = LLMClient(model="gpt-4o-mini")

    user_prompt = (
        f"Create a viral 60-second video script based on this trending tech news:\n\n"
        f"HEADLINE: {title}\n"
        f"CONTEXT: {snippet}\n"
        f"SOURCE: {source}\n\n"
        f"Make it engaging, fast-paced, and optimized for maximum watch time."
    )

    try:
        script = await client.generate_structured(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=VideoScript,
            temperature=0.8,
        )
        logger.info(f"[ScriptGen] Generated script: '{script.title}' ({len(script.points)} points)")
        return script
    except Exception as e:
        logger.error(f"[ScriptGen] Failed to generate script: {e}")
        raise
