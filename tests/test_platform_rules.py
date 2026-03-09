import pytest
from app.core.platform_rules import validate_post_for_platform, PLATFORM_RULES

def test_x_validation_success():
    """Test a valid X post"""
    text = "This is a short, valid X post."
    errors = validate_post_for_platform("X", text, has_video=False, has_image=False)
    assert len(errors) == 0

def test_x_validation_character_limit():
    """Test X character limit failure"""
    text = "x" * 281
    errors = validate_post_for_platform("X", text, has_video=False, has_image=False)
    assert len(errors) == 1
    assert "character limit exceeded" in errors[0]

def test_tiktok_requires_media():
    """Test TikTok requiring media"""
    text = "No media, just text"
    errors = validate_post_for_platform("TIKTOK", text, has_video=False, has_image=False)
    assert len(errors) == 1
    assert "requires at least one image or video" in errors[0]

def test_tiktok_valid_with_video():
    """Test TikTok passing with video"""
    text = "Look at this dance"
    errors = validate_post_for_platform("TIKTOK", text, has_video=True, has_image=False)
    assert len(errors) == 0

def test_unknown_platform():
    """Test behavior with an unknown platform"""
    errors = validate_post_for_platform("UNKNOWN_PLATFORM", "Hello", False, False)
    assert len(errors) == 0 # Current implementation ignores unknown platforms

def test_video_duration_limit():
    """Test video duration limits"""
    # X has a limit of 140 seconds
    errors = validate_post_for_platform("X", "Video post", has_video=True, has_image=False, video_duration_sec=150)
    assert len(errors) == 1
    assert "video duration limit exceeded" in errors[0]
