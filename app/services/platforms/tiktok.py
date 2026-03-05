"""
KontentPyper - TikTok Platform Service
OAuth 2.0 with PKCE and Direct Publish API.
"""

import logging
from typing import Optional

from app.services.platforms.base_platform import BasePlatformService, PlatformResult
from app.core.config import settings

logger = logging.getLogger(__name__)


class TikTokService(BasePlatformService):
    platform_name = "tiktok"

    def __init__(self, client_key: str = None, client_secret: str = None):
        self.client_key = client_key or settings.TIKTOK_CLIENT_ID
        self.client_secret = client_secret or settings.TIKTOK_CLIENT_SECRET

    # ── Configuration ─────────────────────────────────────────────

    def get_oauth_config(self) -> dict:
        return {
            "protocol": "oauth2",
            "client_id": self.client_key,  # Used as standard in oauth_service
            "client_secret": self.client_secret,
            "auth_url": "https://www.tiktok.com/v2/auth/authorize/",
            "token_url": "https://open.tiktokapis.com/v2/oauth/token/",
            "scope": "user.info.basic,video.upload,video.publish",
            "user_info_url": "https://open.tiktokapis.com/v2/user/info/",
            "uses_pkce": True,
            "token_auth_method": "body",
            "response_type": "code",
            "client_id_param_name": "client_key", # Required mapping for TikTok
            "auth_params": {},
            "platform_display_name": "TikTok"
        }

    # ── User info ─────────────────────────────────────────────────

    async def get_user_info(self, access_token: str) -> dict:
        url = self.get_oauth_config()["user_info_url"]
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {"fields": "open_id,union_id,avatar_url,display_name"}
        
        async with self._make_client(headers) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            user_data = resp.json().get("data", {}).get("user", {})
            return {
                "id":       user_data.get("open_id"),
                "username": user_data.get("display_name"),
                "avatar":   user_data.get("avatar_url"),
            }

    # ── Post logic ────────────────────────────────────────────────

    async def post(
        self,
        access_token: str,
        content: str,
        image_urls:   Optional[list[str]] = None,
        video_urls:   Optional[list[str]] = None,
        **kwargs
    ) -> PlatformResult:
        # TikTok strictly requires exactly one video
        _, videos = self.validate_media_count(image_urls, video_urls)
        
        if not videos:
            return self.fail("TikTok requires exactly 1 video. None provided.")

        try:
            return await self._upload_video(access_token, content, videos[0])
        except Exception as e:
            return self.fail(f"TikTok upload exception: {e}")

    async def _upload_video(self, token: str, description: str, video_url: str) -> PlatformResult:
        """TikTok Direct Post / Pull using open_id."""
        
        # Note: TikTok's Direct Post API requires the pull method if we are sending a URL, 
        # reducing our server load vs downloading and sending giant binaries.
        
        url = "https://open.tiktokapis.com/v2/post/publish/video/init/"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        payload = {
            "post_info": {
                "title": self.validate_content_length(description),
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "video_url": video_url
            }
        }

        async with self._make_client(headers) as client:
            resp = await client.post(url, json=payload)
            
            if resp.status_code == 200:
                data = resp.json()
                if data.get("error", {}).get("code") == "ok":
                    publish_id = data.get("data", {}).get("publish_id", "unknown")
                    # Since it's async processing on TikTok, there is no immediate public URL.
                    return self.ok(publish_id, "", data)
                    
            return self.fail(f"Init failed HTTP {resp.status_code}: {resp.text}")
