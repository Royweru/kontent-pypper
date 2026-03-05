"""
KontentPyper - AI Enhancer Service
Takes raw ideas and formats them perfectly for selected target platforms.
Uses LangChain structured output to guarantee schema-valid responses.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from app.services.ai.llm_client import LLMClient
from app.core.config import settings


# ── Structured Output Schema ──────────────────────────────────────

class EnhancedDraft(BaseModel):
    """The strict format the LLM must return when enhancing content."""
    platforms: Dict[str, str] = Field(
        ...,
        description=(
            "A dictionary mapping the platform name (e.g., 'twitter', 'linkedin') "
            "to the fully formatted, ready-to-publish content string for that platform."
        ),
    )
    suggested_hashtags: List[str] = Field(
        default=[],
        description="A list of 3-5 high-impact suggested tags without the # symbol.",
    )


# ── Service ───────────────────────────────────────────────────────

class EnhancerService:
    """
    Transforms raw concepts into platform-optimized posts using LangChain + gpt-5-nano.
    """

    SYSTEM_PROMPT = """You are KontentPyper, an elite social media manager and copywriter.
Your task is to take a user's raw idea, notes, or draft, and rewrite it perfectly for the requested platforms.
Do NOT use generic corporate speak. Use high-craft, native language for each platform.

PLATFORM RULES:
1. twitter: Short, punchy, max 280 chars. Hook -> Value -> Conclusion. Minimal hashtags (1-2 max).
2. linkedin: Professional but authentic. Use whitespace (blank lines). Start with a strong hook. Limit emojis.
3. youtube: This will be a video description. Include a clear hook, a short summary of the video, and a CTA.
4. tiktok: This will be a short video caption. Extremely concise, trendy tone, max 3 hashtags.

Output the EXACT finalized text that will be posted without surrounding quotes or 'Here is your text' fluff."""

    def __init__(self):
        self.llm = LLMClient(
            api_key=settings.OPENAI_API_KEY,
            model="gpt-5-nano",
        )

    async def enhance_draft(
        self,
        raw_content: str,
        target_platforms: List[str],
        user_context: Optional[str] = None,
    ) -> EnhancedDraft:
        """
        Takes raw string content and a list of platforms.
        Returns structured content mapped to specific platform tones/limits.
        """
        platforms_str = ", ".join(target_platforms)

        user_prompt = (
            f"Please adapt the following content for these platforms: {platforms_str}.\n\n"
            f"RAW CONTENT:\n{raw_content}\n\n"
        )

        if user_context:
            user_prompt += f"ADDITIONAL CONTEXT FROM USER:\n{user_context}\n\n"

        draft = await self.llm.generate_structured(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=EnhancedDraft,
            temperature=0.7,
        )

        return draft
