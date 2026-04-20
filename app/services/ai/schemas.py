#app/services/schemas.py
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

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

class PlatformDraft(BaseModel):
    platform: str = Field(description="The name of the platform, e.g., 'twitter', 'linkedin'")
    content: str = Field(description="The fully formatted, ready-to-publish content string for this platform")

class EnhancedDraftResponse(BaseModel):
    """The strict format the LLM must return when enhancing content."""
    drafts: List[PlatformDraft] = Field(
        description="A list of platform-specific drafts. Must contain exactly one item for each requested platform."
    )
    suggested_hashtags: List[str] = Field(
        default=[],
        description="A list of 3-5 high-impact suggested tags without the # symbol.",
    )

class EnhancedDraft(BaseModel):
    """Internal model returned to the services."""
    platforms: Dict[str, str]
    suggested_hashtags: List[str]