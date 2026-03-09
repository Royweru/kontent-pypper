"""
KontentPyper - LinkedIn Platform Service
OAuth 2.0 and API integration for LinkedIn (ugcPosts via v2 API).
"""

import logging
import asyncio
from typing import Optional

from app.services.platforms.base_platform import BasePlatformService, PlatformResult
from app.core.config import settings

logger = logging.getLogger(__name__)


class LinkedInService(BasePlatformService):
    platform_name = "linkedin"

    def __init__(self, client_id: str = None, client_secret: str = None):
        self.client_id = client_id or settings.LINKEDIN_CLIENT_ID
        self.client_secret = client_secret or settings.LINKEDIN_CLIENT_SECRET

    # ── Configuration ─────────────────────────────────────────────

    def get_oauth_config(self) -> dict:
        return {
            "protocol": "oauth2",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "auth_url": "https://www.linkedin.com/oauth/v2/authorization",
            "token_url": "https://www.linkedin.com/oauth/v2/accessToken",
            "scope": "openid profile email w_member_social",
            "user_info_url": "https://api.linkedin.com/v2/userinfo",
            "uses_pkce": False,
            "token_auth_method": "body",
            "response_type": "code",
            "auth_params": {},
            "platform_display_name": "LinkedIn"
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
        urn: str = None,  # the user's URN id, passed from the db record
        **kwargs
    ) -> PlatformResult:
        if not urn:
            return self.fail("LinkedIn requires user URN id to post.")
            
        author = f"urn:li:person:{urn}"
        content = self.validate_content_length(content)
        images, videos = self.validate_media_count(image_urls, video_urls)

        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
        }

        try:
            media_assets = []
            
            # If there's an image, register and upload it
            if images:
                asset = await self._upload_image(access_token, author, images[0], headers)
                if asset:
                    media_assets.append({"media": asset, "status": "READY"})
                    
            # (LinkedIn videos require a much more complex async Flow.
            #  For MVP reliability, if a video is forced we just post text with the video link)
            if videos and not images:
                content += f"\n\nVideo Link: {videos[0]}"

            share_media_category = "NONE"
            if media_assets:
                share_media_category = "IMAGE"

            payload = {
                "author": author,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": content},
                        "shareMediaCategory": share_media_category,
                        "media": media_assets
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }

            async with self._make_client(headers) as client:
                resp = await client.post("https://api.linkedin.com/v2/ugcPosts", json=payload)
                resp.raise_for_status()
                
                # URN of new post comes back in a header usually: x-restli-id
                post_urn = resp.headers.get("x-restli-id", "")
                post_id = post_urn.split(":")[-1] if post_urn else "unknown"
                url = f"https://www.linkedin.com/feed/update/{post_urn}/" if post_urn else ""

                return self.ok(post_id, url, resp.json() if resp.content else {})

        except httpx.HTTPStatusError as e:
            return self.fail(f"HTTP {e.response.status_code}: {e.response.text}")
        except Exception as e:
            return self.fail(f"Exception: {e}")

    # ── Image Helper ──────────────────────────────────────────────

    async def _upload_image(self, token: str, author: str, image_url: str, base_headers: dict) -> Optional[str]:
        image_data = await self.download_media(image_url)

        # 1. Register
        reg_payload = {
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "owner": author,
                "serviceRelationships": [{"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}]
            }
        }
        
        async with self._make_client(base_headers) as client:
            resp = await client.post("https://api.linkedin.com/v2/assets?action=registerUpload", json=reg_payload)
            resp.raise_for_status()
            data = resp.json()
            
            asset_urn = data.get("value", {}).get("asset")
            upload_url = data.get("value", {}).get("uploadMechanism", {}).get("com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest", {}).get("uploadUrl")
            
            if not asset_urn or not upload_url:
                raise ValueError("LinkedIn registerUpload did not return expected upload URL")

            # 2. Upload binary
            up_resp = await client.put(
                upload_url,
                content=image_data,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/octet-stream"}
            )
            up_resp.raise_for_status()
            
            
            return asset_urn

    # ── Analytics ─────────────────────────────────────────────────

    async def fetch_analytics(self, access_token: str, platform_post_id: str, **kwargs) -> dict:
        """Fetch basic socialAction data for a LinkedIn post (URN)"""
        urn = f"urn:li:ugcPost:{platform_post_id}"
        url = f"https://api.linkedin.com/v2/socialActions/{urn}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
        }
        
        try:
            async with self._make_client(headers) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                
                return {
                    "views": 0,  # Standard API does not provide impressions directly
                    "likes": data.get("likesSummary", {}).get("totalLikes", 0),
                    "comments": data.get("commentsSummary", {}).get("totalFirstLevelComments", 0),
                    "shares": 0,
                    "clicks": 0
                }
        except Exception as e:
            logger.error("[linkedin] Analytics fetch failed: %s", e)
            return {"views": 0, "likes": 0, "comments": 0, "shares": 0, "clicks": 0}
