import pytest
from fastapi import HTTPException

from app.core.publish_scope import build_scoped_content_map
from app.services.workflow.billing import determine_billable_credits
from app.services.credit_service import get_tier_config
from app.services.workflow.policy import build_workflow_policy
import app.services.ai.enhancer as enhancer_module
import app.services.platforms.linkedin as linkedin_module


def test_enhancer_imports_structured_response_schema():
    assert hasattr(enhancer_module, "EnhancedDraftResponse")


def test_linkedin_module_has_httpx_for_status_error_handler():
    assert hasattr(linkedin_module, "httpx")


def test_build_scoped_content_map_rejects_unselected_payload_platforms():
    with pytest.raises(HTTPException) as exc:
        build_scoped_content_map(
            requested_platforms=["twitter"],
            platform_specific_content={"twitter": "ok", "linkedin": "not allowed"},
            original_content="fallback",
        )
    assert exc.value.status_code == 400
    assert "unselected platforms" in str(exc.value.detail)


def test_build_scoped_content_map_normalizes_and_deduplicates_platforms():
    platforms, content_map = build_scoped_content_map(
        requested_platforms=["TWITTER", "twitter", " linkedin "],
        platform_specific_content={"Twitter": "x-post"},
        original_content="fallback",
    )
    assert platforms == ["twitter", "linkedin"]
    assert content_map == {"twitter": "x-post", "linkedin": "fallback"}


def test_determine_billable_credits_rejects_placeholder_asset():
    credits, reason = determine_billable_credits(
        {
            "credits_consumed": 3,
            "video_source": "runway_premium",
            "video_asset": "https://www.w3schools.com/html/mov_bbb.mp4",
        }
    )
    assert credits == 0
    assert reason == "placeholder_asset_not_billable"


def test_determine_billable_credits_rejects_unknown_video_source():
    credits, reason = determine_billable_credits(
        {
            "credits_consumed": 3,
            "video_source": "mystery_provider",
            "video_asset": "https://cdn.example.com/video.mp4",
        }
    )
    assert credits == 0
    assert reason == "unknown_video_source_not_billable"


def test_determine_billable_credits_allows_real_billable_provider_asset():
    credits, reason = determine_billable_credits(
        {
            "credits_consumed": 3,
            "video_source": "runway_premium",
            "video_asset": "https://cdn.example.com/generated/runway_asset.mp4",
        }
    )
    assert credits == 3
    assert reason == "billable_provider_asset_confirmed"


def test_free_tier_trial_limits_are_relaxed():
    cfg = get_tier_config("free")
    assert cfg["monthly_video_credits"] == 5
    assert cfg["max_runs_per_day"] == 3
    assert cfg["max_platforms_per_run"] is None


def test_free_workflow_policy_allows_all_platforms_per_run():
    policy = build_workflow_policy(
        tier_level="free",
        target_platforms=["twitter", "linkedin", "youtube"],
    )
    assert policy["target_platforms"] == ["twitter", "linkedin", "youtube"]
