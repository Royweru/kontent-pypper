from pathlib import Path

from app.api import billing
from app.core.config import settings
from app.services.credit_service import get_tier_config


def test_free_tier_is_trial_friendly():
    cfg = get_tier_config("free")
    assert cfg["monthly_video_credits"] == 5
    assert cfg["max_runs_per_day"] == 3
    assert cfg["max_platforms_per_run"] is None


def test_billing_plan_to_tier_mapping_uses_config(monkeypatch):
    monkeypatch.setattr(settings, "PAYSTACK_PLAN_PRO", "PLN_PRO_123")
    monkeypatch.setattr(settings, "PAYSTACK_PLAN_MAX", "PLN_MAX_456")

    assert billing._tier_for_plan_code("PLN_PRO_123") == "pro"
    assert billing._tier_for_plan_code("PLN_MAX_456") == "max"
    assert billing._tier_for_plan_code("PLN_OTHER") is None


def test_placeholder_video_urls_removed_from_pipeline_paths():
    workflow_src = Path("app/api/workflow.py").read_text(encoding="utf-8")
    nodes_src = Path("app/services/workflow/nodes.py").read_text(encoding="utf-8")

    assert "mov_bbb.mp4" not in workflow_src
    assert "mov_bbb.mp4" not in nodes_src
