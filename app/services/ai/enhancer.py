# app/services/ai/enhancer.py
"""
KontentPyper - AI Enhancer Service
Takes raw ideas and formats them perfectly for selected target platforms.
Uses LangChain structured output to guarantee schema-valid responses.
"""
from app.services.ai.llm_client import LLMClient
from typing import Optional
from .schemas import EnhancedDraft, EnhancedDraftResponse

# ── Service ───────────────────────────────────────────────────────

class EnhancerService:
    """
    Transforms raw concepts into platform-optimized posts using LangChain.
    """

    SYSTEM_PROMPT = """You are KontentPyper, an elite social media manager and copywriter.
Your task is to take a user's raw idea, notes, or draft, and rewrite it perfectly for the requested platforms.
Do NOT use generic corporate speak. Use high-craft, native language for each platform.

PLATFORM RULES:
1. twitter: Short, punchy, max 280 chars. Hook -> Value -> Conclusion. Minimal hashtags (1-2 max).
2. linkedin: Professional but authentic. Use whitespace (blank lines). Start with a strong hook. Limit emojis.
3. youtube: This will be a video description. Include a clear hook, a short summary of the video, and a CTA.
4. tiktok: This will be a short video caption. Extremely concise, trendy tone, max 3 hashtags.

CRITICAL INSTRUCTION ON JSON OUTPUT: 
You must strictly adhere to the expected schema. 
Return the JSON object exactly with the `drafts` list and `suggested_hashtags` list."""

    def __init__(self):
        self.llm = LLMClient()

    async def enhance_draft(
        self,
        raw_content: str,
        target_platforms: list[str],
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

        response = await self.llm.generate_structured(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=EnhancedDraftResponse,
            temperature=1.0
        )
        
        # Remap the List[PlatformDraft] back into a simple Dictionary for the caller
        platforms_dict = {d.platform.lower(): d.content for d in response.drafts}
        
        return EnhancedDraft(
            platforms=platforms_dict,
            suggested_hashtags=response.suggested_hashtags
        )
