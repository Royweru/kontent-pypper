"""
KontentPyper - AI Reflection Engine
Analyzes past performance data to derive strategic insights for future content.
Uses LangChain structured output with gpt-5-nano.
"""

from typing import List
from pydantic import BaseModel, Field

from app.services.ai.llm_client import LLMClient
from app.core.config import settings


# ── Structured Output Schema ──────────────────────────────────────

class StrategicInsight(BaseModel):
    """Structured insight derived from analytics."""
    what_worked: List[str] = Field(
        description="Bullet points of what specific elements succeeded in high-performing posts."
    )
    what_failed: List[str] = Field(
        description="Bullet points of what specific elements failed in low-performing posts."
    )
    new_rules: List[str] = Field(
        description="New copywriting rules the Enhancer should adopt going forward."
    )


# ── Service ───────────────────────────────────────────────────────

class ReflectorService:
    """
    The feedback loop. Looks at recent post analytics and tells the system how to improve.
    Uses gpt-5-nano for cost-efficient analytical reasoning.
    """

    SYSTEM_PROMPT = """You are KontentPyper Core Intelligence.
Analyze the following post performance data containing actual engagement metrics (views, likes, clicks).
Identify concrete patterns. Do not be vague.
Example of a good rule: 'Posts with questions in the first line get 3x more replies.'
Example of a bad rule: 'Make posts engaging.'
Provide your analysis in the strict JSON format requested."""

    def __init__(self):
        self.llm = LLMClient(
            api_key=settings.OPENAI_API_KEY,
            model="gpt-5-nano",
        )

    async def analyze_performance(self, analytics_data_dump: str) -> StrategicInsight:
        """
        Processes a raw dump of analytics data and returns a structured reflection object.
        """
        user_prompt = (
            f"Here is the performance data for the last 30 days:\n\n"
            f"{analytics_data_dump}\n\n"
            f"Derive insights."
        )

        insight = await self.llm.generate_structured(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=StrategicInsight,
            temperature=0.4,
        )

        return insight
