"""
KontentPyper - Content Schemas
Pydantic models for the autonomous content pipeline.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class ScriptPoint(BaseModel):
    """A single talking point in the video script."""
    text: str = Field(..., description="The narration text for this point (1-2 sentences)")
    visual_cue: str = Field(..., description="Brief description of what visuals to show during this point")


class VideoScript(BaseModel):
    """Full video script for a 60-second short-form vertical video."""
    title: str = Field(..., description="Catchy short title for the video (max 60 chars)")
    hook: str = Field(..., description="Opening hook line to grab attention in the first 3 seconds")
    points: List[ScriptPoint] = Field(..., min_length=3, max_length=5, description="3-5 key talking points")
    cta: str = Field(..., description="Call-to-action closing line")
    hashtags: List[str] = Field(..., min_length=3, max_length=8, description="Relevant hashtags without #")
    search_query: str = Field(..., description="Best single search query to find B-roll footage on Pexels for this topic")

    @property
    def full_narration(self) -> str:
        """Returns the complete narration script as a single string."""
        parts = [self.hook]
        for p in self.points:
            parts.append(p.text)
        parts.append(self.cta)
        return " ".join(parts)

    @property
    def caption_text(self) -> str:
        """Returns a social-media-ready caption with hashtags."""
        tags = " ".join(f"#{h}" for h in self.hashtags)
        return f"{self.title}\n\n{self.hook}\n\n{tags}"
