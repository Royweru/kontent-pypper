# app/services/workflow/state.py
"""
KontentPyper - LangGraph Workflow State
TypedDict defining all fields flowing through the pipeline.
"""

from typing import TypedDict, List, Dict, Any, Optional


class WorkflowState(TypedDict):
    """
    The shared state dict that flows through every LangGraph node.

    Fields:
      - user_id:           The authenticated user's database ID
      - niche:             The niche filter for article scoring
      - tier_level:        User's subscription tier (free/pro/max)
      - video_model:       Which video gen model to use (stock/kling/runway/sora)
      - articles:          Raw articles fetched from RSS feeds
      - selected_article:  The top-scoring article picked by the score node
      - scripts:           Platform -> text content map (draft node output)
      - video_asset:       URL of the generated video file
      - video_source:      Identifier of the video gen backend used
      - video_script:      Structured script data (title, hook, points, etc.)
      - credits_consumed:  How many credits this pipeline run used
      - status:            Human-readable status message for the live tracker UI
    """
    user_id: int
    niche: Optional[str]
    tier_level: Optional[str]
    video_model: Optional[str]
    articles: List[Dict[str, Any]]
    selected_article: Optional[Dict[str, Any]]
    scripts: Dict[str, str]
    video_asset: Optional[str]
    video_source: Optional[str]
    video_script: Optional[Dict[str, Any]]
    credits_consumed: int
    status: str