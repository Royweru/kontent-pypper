"""
KontentPyper - YouTube Platform Service
OAuth 2.0 and video uploading via Google APIs.
"""

import logging
import httpx
from typing import Optional

from app.services.platforms.base_platform import BasePlatformService, PlatformResult
from app.core.config import settings

logger = logging.getLogger(__name__)


class YouTubeService(BasePlatformService):
    platform_name = "youtube"

    def __init__(self, client_id: str = None, client_secret: str = None):
        self.client_id = client_id or settings.GOOGLE_CLIENT_ID
        self.client_secret = client_secret or settings.GOOGLE_CLIENT_SECRET

    # ── Configuration ─────────────────────────────────────────────

    def get_oauth_config(self) -> dict:
        return {
            "protocol": "oauth2",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "scope": (
                "https://www.googleapis.com/auth/youtube.upload "
                "https://www.googleapis.com/auth/youtube.readonly "
                "https://www.googleapis.com/auth/userinfo.profile "
                "https://www.googleapis.com/auth/userinfo.email"
            ),
            "user_info_url": "https://www.googleapis.com/oauth2/v3/userinfo",
            "uses_pkce": False,
            "token_auth_method": "body",
            "response_type": "code",
            "auth_params": {
                "access_type": "offline",
                "prompt": "consent"
            },
            "platform_display_name": "YouTube"
        }

    # ── User info ─────────────────────────────────────────────────

    async def get_user_info(self, access_token: str) -> dict:
        url = self.get_oauth_config()["user_info_url"]
        headers = {"Authorization": f"Bearer {access_token}"}
        async with self._make_client(headers) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            return {
                "id":       data.get("sub"),
                "username": data.get("name"),
                "avatar":   data.get("picture"),
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
        # YouTube strictly requires a video
        _, videos = self.validate_media_count(image_urls, video_urls)
        
        if not videos:
            return self.fail("YouTube requires exactly 1 video. None provided.")

        try:
            # Note: We are using a basic resumable upload pattern here 
            # for 10x scalability without bloated client libraries.
            return await self._upload_video(access_token, content, videos[0])
        except Exception as e:
            return self.fail(f"Upload exception: {e}")

    async def _upload_video(self, token: str, description: str, video_url: str) -> PlatformResult:
        """Execute a resumable video upload to YouTube."""
        video_data = await self.download_media(video_url)
        
        # 1. Init upload session
        init_url = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"
        
        metadata = {
            "snippet": {
                "title": description.split("\n")[0][:100] if description else "KontentPyper Upload",
                "description": description,
                "categoryId": "22",  # People & Blogs
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False
            }
        }

        init_headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Upload-Content-Length": str(len(video_data)),
            "X-Upload-Content-Type": "video/mp4"
        }

        async with self._make_client() as client:
            # Start session
            init_resp = await client.post(init_url, headers=init_headers, json=metadata)
            if init_resp.status_code != 200:
                return self.fail(f"Init failed HTTP {init_resp.status_code}: {init_resp.text}")
                
            upload_url = init_resp.headers.get("Location")
            if not upload_url:
                return self.fail("Google did not return a resumable upload Location.")

            # 2. Upload bytes
            upload_headers = {
                "Authorization": f"Bearer {token}",
                "Content-Length": str(len(video_data)),
                "Content-Type": "video/mp4"
            }
            upload_resp = await client.put(upload_url, headers=upload_headers, content=video_data, timeout=300.0)
            
            if upload_resp.status_code in (200, 201):
                data = upload_resp.json()
                vid = data.get("id")
                return self.ok(vid, f"https://youtube.com/watch?v={vid}", data)
            
            return self.fail(f"Upload put failed HTTP {upload_resp.status_code}: {upload_resp.text}")

    # ── Analytics ─────────────────────────────────────────────────

    async def fetch_analytics(self, access_token: str, platform_post_id: str, **kwargs) -> dict:
        """Fetch video statistics from YouTube Data API v3."""
        url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            "part": "statistics",
            "id": platform_post_id
        }
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            async with self._make_client(headers) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                
                if not data.get("items"):
                    return {"views": 0, "likes": 0, "comments": 0, "shares": 0, "clicks": 0}
                    
                stats = data["items"][0].get("statistics", {})
                
                return {
                    "views": int(stats.get("viewCount", 0)),
                    "likes": int(stats.get("likeCount", 0)),
                    "comments": int(stats.get("commentCount", 0)),
                    "shares": 0,
                    "clicks": 0
                }
        except Exception as e:
            logger.error("[youtube] Analytics fetch failed: %s", e)
            return {"views": 0, "likes": 0, "comments": 0, "shares": 0, "clicks": 0}
