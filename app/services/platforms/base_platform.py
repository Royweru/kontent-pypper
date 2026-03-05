"""
KontentPyper - Base Platform Service
Abstract contract every platform adapter must implement.
"""

import httpx
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# Platform media limits
PLATFORM_LIMITS = {
    "twitter":  {"max_images": 4, "max_videos": 1, "max_video_mb": 512,  "max_chars": 280},
    "linkedin": {"max_images": 9, "max_videos": 1, "max_video_mb": 5120, "max_chars": 3000},
    "youtube":  {"max_images": 0, "max_videos": 1, "max_video_mb": 128000, "max_chars": 5000},
    "tiktok":   {"max_images": 0, "max_videos": 1, "max_video_mb": 4096, "max_chars": 2200},
}


class PlatformResult:
    """Immutable result from a platform post operation."""

    __slots__ = ("success", "platform", "post_id", "post_url", "error", "raw")

    def __init__(
        self,
        *,
        success: bool,
        platform: str,
        post_id:  Optional[str] = None,
        post_url: Optional[str] = None,
        error:    Optional[str] = None,
        raw:      Optional[dict] = None,
    ):
        self.success  = success
        self.platform = platform
        self.post_id  = post_id
        self.post_url = post_url
        self.error    = error
        self.raw      = raw or {}

    def to_dict(self) -> dict:
        return {
            "success":  self.success,
            "platform": self.platform,
            "post_id":  self.post_id,
            "post_url": self.post_url,
            "error":    self.error,
        }


class BasePlatformService(ABC):
    """
    Abstract base every platform adapter inherits from.
    Provides shared HTTP helpers, media utilities, and retry logic.
    """

    platform_name: str = ""
    DEFAULT_TIMEOUT = httpx.Timeout(60.0, connect=10.0)
    DOWNLOAD_TIMEOUT = httpx.Timeout(300.0, connect=10.0)

    # ── Abstract interface ────────────────────────────────────────

    @abstractmethod
    def get_oauth_config(self) -> dict:
        """Return the OAuth configuration dictionary for this platform."""

    @abstractmethod
    async def post(
        self,
        access_token: str,
        content:      str,
        image_urls:   Optional[list[str]] = None,
        video_urls:   Optional[list[str]] = None,
        **kwargs:     Any,
    ) -> PlatformResult:
        """Post content to this platform. Must be implemented by each adapter."""

    @abstractmethod
    async def get_user_info(self, access_token: str) -> dict:
        """Fetch basic profile info (id, username, avatar) for the given token."""

    # ── Shared HTTP helpers ───────────────────────────────────────

    def _make_client(self, headers: Optional[dict] = None) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            headers=headers or {},
            timeout=self.DEFAULT_TIMEOUT,
            follow_redirects=True,
        )

    async def download_media(self, url: str) -> bytes:
        """Download media from a URL. Raises on non-200 status."""
        async with httpx.AsyncClient(timeout=self.DOWNLOAD_TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            if len(resp.content) == 0:
                raise ValueError(f"Empty response body from {url}")
            return resp.content

    # ── Validation helpers ────────────────────────────────────────

    def validate_content_length(self, content: str) -> str:
        """Truncate content if it exceeds this platform's character limit."""
        limit = PLATFORM_LIMITS.get(self.platform_name, {}).get("max_chars")
        if limit and len(content) > limit:
            logger.warning(
                "[%s] Content truncated from %d to %d chars",
                self.platform_name, len(content), limit,
            )
            return content[: limit - 3] + "..."
        return content

    def validate_media_count(
        self,
        image_urls: Optional[list] = None,
        video_urls: Optional[list] = None,
    ) -> tuple[list, list]:
        """Clip media lists to platform limits and return cleaned lists."""
        limits = PLATFORM_LIMITS.get(self.platform_name, {})
        images = (image_urls or [])[: limits.get("max_images", 4)]
        videos = (video_urls or [])[: limits.get("max_videos", 1)]
        return images, videos

    # ── Result factories ──────────────────────────────────────────

    def ok(self, post_id: str, post_url: str = "", raw: dict = None) -> PlatformResult:
        return PlatformResult(
            success=True,
            platform=self.platform_name,
            post_id=post_id,
            post_url=post_url,
            raw=raw,
        )

    def fail(self, error: str, raw: dict = None) -> PlatformResult:
        logger.error("[%s] Post failed: %s", self.platform_name, error)
        return PlatformResult(
            success=False,
            platform=self.platform_name,
            error=error,
            raw=raw,
        )

    # ── Retry helper ──────────────────────────────────────────────

    async def retry(
        self,
        coro_fn,
        *args,
        attempts: int = 3,
        delay: float = 2.0,
        **kwargs,
    ):
        """Run an async callable with exponential back-off retry."""
        last_exc = None
        for attempt in range(1, attempts + 1):
            try:
                return await coro_fn(*args, **kwargs)
            except Exception as exc:
                last_exc = exc
                if attempt < attempts:
                    wait = delay * (2 ** (attempt - 1))
                    logger.warning(
                        "[%s] Attempt %d/%d failed (%s). Retry in %.1fs",
                        self.platform_name, attempt, attempts, exc, wait,
                    )
                    await asyncio.sleep(wait)
        raise last_exc
