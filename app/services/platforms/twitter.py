"""
KontentPyper - Twitter/X Platform Service
OAuth 1.0a — text via v2 API, media via v1.1 chunked upload.
"""

import hmac
import hashlib
import base64
import time
import uuid
import urllib.parse
import math
import asyncio
import logging
import httpx
from typing import Optional

from app.services.platforms.base_platform import BasePlatformService, PlatformResult

logger = logging.getLogger(__name__)

# Chunk size for video uploads: 4 MB
CHUNK_SIZE = 4 * 1024 * 1024

TWITTER_V1  = "https://api.twitter.com/1.1"
TWITTER_V2  = "https://api.twitter.com/2"
UPLOAD_URL  = "https://upload.twitter.com/1.1/media/upload.json"


class TwitterService(BasePlatformService):
    platform_name = "twitter"

    def __init__(self, api_key: str, api_secret: str):
        self.api_key    = api_key
        self.api_secret = api_secret

    def get_oauth_config(self) -> dict:
        return {
            "protocol": "oauth1",
            "consumer_key": self.api_key,
            "consumer_secret": self.api_secret,
            "request_token_url": "https://api.twitter.com/oauth/request_token",
            "authorize_url": "https://api.twitter.com/oauth/authorize",
            "access_token_url": "https://api.twitter.com/oauth/access_token",
            "user_info_url": "https://api.twitter.com/2/users/me?user.fields=profile_image_url",
            "platform_display_name": "Twitter/X",
        }

    # ── OAuth 1.0a signature ──────────────────────────────────────

    def _build_auth_header(
        self,
        method: str,
        url: str,
        token: str,
        token_secret: str,
        extra_params: dict = None,
    ) -> str:
        """Generate OAuth 1.0a HMAC-SHA1 Authorization header."""
        # Separate base URL from query string
        parsed_url = urllib.parse.urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
        query_params = dict(urllib.parse.parse_qsl(parsed_url.query))

        params = {
            "oauth_consumer_key":     self.api_key,
            "oauth_nonce":            uuid.uuid4().hex,
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp":        str(int(time.time())),
            "oauth_token":            token,
            "oauth_version":          "1.0",
        }
        if extra_params:
            params.update(extra_params)

        # Base signature demands queryparams + authparams sorted together
        sig_params = params.copy()
        sig_params.update(query_params)

        # Build base string
        sorted_params = "&".join(
            f"{urllib.parse.quote(k, safe='')}"
            f"={urllib.parse.quote(str(v), safe='')}"
            for k, v in sorted(sig_params.items())
        )
        base = "&".join([
            method.upper(),
            urllib.parse.quote(base_url, safe=""),
            urllib.parse.quote(sorted_params, safe=""),
        ])

        signing_key = (
            urllib.parse.quote(self.api_secret, safe="") + "&" +
            urllib.parse.quote(token_secret, safe="")
        )
        digest = hmac.new(signing_key.encode(), base.encode(), hashlib.sha1).digest()
        params["oauth_signature"] = base64.b64encode(digest).decode()

        return "OAuth " + ", ".join(
            f'{urllib.parse.quote(k, safe="")}="{urllib.parse.quote(str(v), safe="")}"'
            for k, v in sorted(params.items())
            if k.startswith("oauth_")
        )

    def _headers(self, method: str, url: str, access_token: str, token_secret: str) -> dict:
        return {"Authorization": self._build_auth_header(method, url, access_token, token_secret)}

    # ── User info ─────────────────────────────────────────────────

    async def get_user_info(self, access_token: str, token_secret: str = "") -> dict:
        url = f"{TWITTER_V2}/users/me?user.fields=profile_image_url,username"
        headers = self._headers("GET", url, access_token, token_secret)
        async with self._make_client(headers) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json().get("data", {})
            return {
                "id":       data.get("id"),
                "username": data.get("username"),
                "avatar":   data.get("profile_image_url"),
            }

    # ── Main post method ──────────────────────────────────────────

    async def post(
        self,
        access_token: str,
        content: str,
        image_urls: Optional[list[str]] = None,
        video_urls: Optional[list[str]] = None,
        token_secret: str = "",
        **kwargs,
    ) -> PlatformResult:
        content = self.validate_content_length(content)
        images, videos = self.validate_media_count(image_urls, video_urls)

        media_ids = []

        # Upload images
        for url in images:
            try:
                data = await self.download_media(url)
                mid = await self._upload_image(data, access_token, token_secret)
                media_ids.append(mid)
            except Exception as exc:
                logger.warning("[twitter] Image upload failed: %s", exc)

        # Upload video (chunked)
        if videos:
            try:
                data = await self.download_media(videos[0])
                mid = await self._upload_video_chunked(data, access_token, token_secret)
                if mid:
                    media_ids.append(mid)
            except Exception as exc:
                logger.warning("[twitter] Video upload failed: %s", exc)

        return await self._post_tweet(content, media_ids, access_token, token_secret)

    # ── Tweet creation ────────────────────────────────────────────

    async def _post_tweet(
        self,
        text: str,
        media_ids: list[str],
        access_token: str,
        token_secret: str,
    ) -> PlatformResult:
        url = f"{TWITTER_V2}/tweets"
        payload = {"text": text}
        if media_ids:
            payload["media"] = {"media_ids": media_ids}

        headers = {
            **self._headers("POST", url, access_token, token_secret),
            "Content-Type": "application/json",
        }

        async with self._make_client(headers) as client:
            resp = await client.post(url, json=payload)

        if resp.status_code in (200, 201):
            data = resp.json().get("data", {})
            tweet_id = data.get("id", "")
            return self.ok(
                tweet_id,
                f"https://twitter.com/i/web/status/{tweet_id}",
                resp.json(),
            )
        return self.fail(f"HTTP {resp.status_code}: {resp.text[:200]}", resp.json())

    # ── Image upload ──────────────────────────────────────────────

    async def _upload_image(self, data: bytes, token: str, secret: str) -> str:
        headers = {
            **self._headers("POST", UPLOAD_URL, token, secret),
        }
        async with self._make_client(headers) as client:
            resp = await client.post(
                UPLOAD_URL,
                data={"media_category": "tweet_image"},
                files={"media": ("image.jpg", data, "image/jpeg")},
            )
            resp.raise_for_status()
            return str(resp.json()["media_id"])

    # ── Chunked video upload ──────────────────────────────────────

    async def _upload_video_chunked(self, data: bytes, token: str, secret: str) -> Optional[str]:
        """INIT → APPEND chunks → FINALIZE → poll STATUS until ready."""
        total = len(data)

        # 1. INIT
        init_resp = await self._media_command(
            token, secret,
            command="INIT",
            total_bytes=total,
            media_type="video/mp4",
            media_category="tweet_video",
        )
        media_id = str(init_resp["media_id"])

        # 2. APPEND chunks
        num_chunks = math.ceil(total / CHUNK_SIZE)
        for i in range(num_chunks):
            chunk = data[i * CHUNK_SIZE: (i + 1) * CHUNK_SIZE]
            await self._media_append(token, secret, media_id, chunk, i)

        # 3. FINALIZE
        final = await self._media_command(
            token, secret, command="FINALIZE", media_id=media_id,
        )

        # 4. Poll STATUS until processing_info is done
        info = final.get("processing_info")
        while info and info.get("state") not in ("succeeded", "failed"):
            wait = info.get("check_after_secs", 5)
            await asyncio.sleep(wait)
            status = await self._media_command(token, secret, command="STATUS", media_id=media_id)
            info = status.get("processing_info", {})

        if info and info.get("state") == "failed":
            raise RuntimeError(f"Twitter video processing failed: {info}")

        return media_id

    async def _media_command(self, token: str, secret: str, **params) -> dict:
        """Send a COMMAND request to the Twitter v1.1 media upload endpoint."""
        headers = self._headers("POST", UPLOAD_URL, token, secret)
        async with self._make_client(headers) as client:
            resp = await client.post(UPLOAD_URL, data=params)
            resp.raise_for_status()
            return resp.json() if resp.content else {}

    async def _media_append(
        self,
        token: str,
        secret: str,
        media_id: str,
        chunk: bytes,
        index: int,
    ) -> None:
        headers = self._headers("POST", UPLOAD_URL, token, secret)
        async with self._make_client(headers) as client:
            resp = await client.post(
                UPLOAD_URL,
                data={"command": "APPEND", "media_id": media_id, "segment_index": index},
                files={"media": ("chunk", chunk, "application/octet-stream")},
            )
            resp.raise_for_status()
