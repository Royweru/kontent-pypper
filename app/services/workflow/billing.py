"""
Workflow billing policy helpers.
Ensures credits are only charged for real, provider-generated video assets.
"""

from __future__ import annotations

from typing import Tuple


PLACEHOLDER_VIDEO_MARKERS = (
    "w3schools.com/html/mov_bbb.mp4",
)

# Canonical billable provider sources once real generation is wired in.
BILLABLE_VIDEO_SOURCES = {
    "kling_ai",
    "runway_premium",
    "sora_premium",
    "kling",
    "runway",
    "sora",
}

NON_BILLABLE_SOURCES = {
    "stock",
    "pexels_stock",
    "placeholder_stub",
    "",
    None,
}


def determine_billable_credits(final_state: dict, fallback_video_model: str | None = None) -> Tuple[int, str]:
    """
    Returns (billable_credits, reason).

    A run is billable only when:
      1) requested credits > 0
      2) video asset exists and is not a known placeholder
      3) video source is in the allowlisted billable provider set
    """
    requested = int(final_state.get("credits_consumed") or 0)
    if requested <= 0:
        return 0, "no_credits_requested"

    asset_url = str(final_state.get("video_asset") or "").strip()
    if not asset_url:
        return 0, "missing_video_asset"

    if any(marker in asset_url for marker in PLACEHOLDER_VIDEO_MARKERS):
        return 0, "placeholder_asset_not_billable"

    video_source = (final_state.get("video_source") or fallback_video_model or "").strip()
    if video_source in NON_BILLABLE_SOURCES:
        return 0, "non_billable_video_source"

    if video_source not in BILLABLE_VIDEO_SOURCES:
        return 0, "unknown_video_source_not_billable"

    return requested, "billable_provider_asset_confirmed"
