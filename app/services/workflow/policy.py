"""
KontentPyper - Workflow Policy Service
Centralizes plan-aware constraints for pipeline execution.
"""

from typing import Optional

from app.services.credit_service import get_tier_config


def build_workflow_policy(tier_level: str, target_platforms: Optional[list[str]] = None) -> dict:
    tier = (tier_level or "free").lower()
    cfg = get_tier_config(tier)

    requested_platforms = [p.lower() for p in (target_platforms or []) if p]
    if not requested_platforms:
        requested_platforms = ["twitter", "linkedin"]

    max_platforms = cfg.get("max_platforms_per_run")
    if isinstance(max_platforms, int):
        requested_platforms = requested_platforms[:max_platforms]

    require_review = tier == "free"
    if require_review:
        auto_publish_allowed = False
    else:
        auto_publish_allowed = True

    latency_profiles = {
        "free": {"max_runtime_seconds": 45, "score_top_k": 3, "fetch_timeout_seconds": 8, "event_delay_seconds": 0.05, "max_candidates": 20},
        "pro": {"max_runtime_seconds": 70, "score_top_k": 5, "fetch_timeout_seconds": 10, "event_delay_seconds": 0.05, "max_candidates": 30},
        "max": {"max_runtime_seconds": 90, "score_top_k": 7, "fetch_timeout_seconds": 12, "event_delay_seconds": 0.05, "max_candidates": 40},
    }
    perf = latency_profiles.get(tier, latency_profiles["free"])
    quality_profiles = {
        "free": {"min_script_chars": 80, "auto_publish_min_quality": 0.7},
        "pro": {"min_script_chars": 110, "auto_publish_min_quality": 0.75},
        "max": {"min_script_chars": 140, "auto_publish_min_quality": 0.8},
    }
    quality = quality_profiles.get(tier, quality_profiles["free"])

    return {
        "tier_level": tier,
        "target_platforms": requested_platforms,
        "max_platforms_per_run": max_platforms,
        "max_videos_per_run": 1,
        "require_review": require_review,
        "auto_publish_allowed": auto_publish_allowed,
        "video_quality": cfg.get("video_quality", "stock"),
        "llm_text_model": "gpt-4o-mini",
        "max_runtime_seconds": perf["max_runtime_seconds"],
        "score_top_k": perf["score_top_k"],
        "fetch_timeout_seconds": perf["fetch_timeout_seconds"],
        "event_delay_seconds": perf["event_delay_seconds"],
        "max_candidates": perf["max_candidates"],
        "global_cache_ttl_seconds": 300,
        "quality_gate_enabled": True,
        "require_review_on_quality_fail": True,
        "min_script_chars": quality["min_script_chars"],
        "auto_publish_min_quality": quality["auto_publish_min_quality"],
    }
