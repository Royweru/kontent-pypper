from typing import Dict, Any, List

# Dictionary of platform rules
PLATFORM_RULES: Dict[str, Dict[str, Any]] = {
    "X": {
        "max_chars": 280,
        "requires_media": False,
        "allowed_media": ["image", "video"],
        "max_video_duration_sec": 140, # 2m20s
        "max_images": 4,
        "max_video_size_mb": 512
    },
    "LINKEDIN": {
        "max_chars": 3000,
        "requires_media": False,
        "allowed_media": ["image", "video", "document"],
        "max_video_duration_sec": 900, # 15 minutes
        "max_images": 9,
        "max_video_size_mb": 5120 # 5GB
    },
    "TIKTOK": {
        "max_chars": 2200,
        "requires_media": True,
        "allowed_media": ["video", "image"], # Images are usually carousels
        "max_video_duration_sec": 3600, # 60 minutes for desktop upload, 10 for in-app
        "max_images": 35,
        "max_video_size_mb": 500 # standardizing on desktop upload limit, or could be lower
    },
    "YOUTUBE": {
        "max_chars": 10000, # Community post limit. Shorts is 100 title + 5000 desc
        "requires_media": True, # To count as a video/short, or image for community
        "allowed_media": ["video", "image"],
        "max_video_duration_sec": 180, # 3 minutes for shorts
        "max_images": 5,
        "max_video_size_mb": 256000 # 256GB standard limit
    },
    "FACEBOOK": {
        "max_chars": 63206,
        "requires_media": False,
        "allowed_media": ["image", "video"],
        "max_video_duration_sec": 14400, # 4 hours
        "max_images": 10,
        "max_video_size_mb": 10240 # 10GB
    },
    "INSTAGRAM": {
        "max_chars": 2200,
        "requires_media": True,
        "allowed_media": ["image", "video"],
        "max_video_duration_sec": 3600, # 60 mins for regular, 3 mins for reels
        "max_images": 20,
        "max_video_size_mb": 3600 # 3.6GB limit
    }
}

def validate_post_for_platform(platform: str, text: str, has_video: bool, has_image: bool, video_duration_sec: int = 0) -> List[str]:
    """
    Validates post content against a given platform's rules.
    Returns a list of error messages. If the list is empty, the post is valid.
    """
    platform_key = platform.upper()
    if platform_key not in PLATFORM_RULES:
        return [] # Unknown platform, skip validation or return error? Let's skip for now
    
    rules = PLATFORM_RULES[platform_key]
    errors = []
    
    # 1. Check Character Limit
    if len(text) > rules["max_chars"]:
        errors.append(f"{platform} character limit exceeded ({len(text)}/{rules['max_chars']}).")
        
    # 2. Check Media Requirements
    if rules["requires_media"] and not (has_video or has_image):
        errors.append(f"{platform} requires at least one image or video.")
        
    # 3. Check Media Type Allowance
    if has_video and "video" not in rules["allowed_media"]:
        errors.append(f"{platform} does not allow video uploads.")
    if has_image and "image" not in rules["allowed_media"]:
        errors.append(f"{platform} does not allow image uploads.")
        
    # 4. Check Video Duration
    if has_video and video_duration_sec > rules["max_video_duration_sec"]:
        errors.append(f"{platform} video duration limit exceeded ({video_duration_sec}s/max {rules['max_video_duration_sec']}s).")
        
    return errors
