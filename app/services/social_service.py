"""
KontentPyper - Social Service Orchestrator
Coordinates multi-platform posting using the adapters.
"""

import logging
from typing import Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.models.social import SocialConnection
from app.services.oauth_service import PLATFORMS
from app.services.platforms.base_platform import PlatformResult

logger = logging.getLogger(__name__)


class SocialService:
    """Orchestrates post distribution across multiple social platforms."""

    @classmethod
    async def get_active_connections(cls, db: AsyncSession, user_id: int) -> list[SocialConnection]:
        """Fetch all connected & active platforms for a user."""
        q = select(SocialConnection).where(
            SocialConnection.user_id == user_id,
            SocialConnection.is_active == True
        )
        return list((await db.execute(q)).scalars().all())

    @classmethod
    async def publish_post(
        cls,
        db: AsyncSession,
        user_id: int,
        content_map: Dict[str, str],  # {"twitter": "...", "linkedin": "..."}
        image_urls: list[str] = None,
        video_urls: list[str] = None,
    ) -> list[PlatformResult]:
        """
        Publish platform-specific content to each active requested platform.
        Expects content_map keys to be matching platform names (e.g. 'twitter').
        """
        connections = await cls.get_active_connections(db, user_id)
        
        # Build map of available connections by platform name (lowercase)
        conn_map = {c.platform.lower(): c for c in connections}
        
        results = []
        
        for platform_name, text_content in content_map.items():
            platform_name = platform_name.lower()
            
            # Validation
            if platform_name not in PLATFORMS:
                results.append(PLATFORMS["twitter"].fail(f"Unsupported platform: {platform_name}"))
                logger.error("Attempted to publish to unsupported platform: %s", platform_name)
                continue
                
            conn = conn_map.get(platform_name)
            if not conn:
                results.append(PLATFORMS[platform_name].fail(f"Not connected to {platform_name}"))
                logger.warning("User %s attempted to post to %s, but is not connected.", user_id, platform_name)
                continue

            adapter = PLATFORMS[platform_name]
            
            # Prepare arguments matching the specific API
            kwargs = {}
            if platform_name == "twitter":
                # For OAuth 1.0a, Twitter uses both halves. We stored access:secret.
                try:
                    access, secret = conn.access_token.split(":")
                    kwargs["access_token"] = access
                    kwargs["token_secret"] = secret
                except ValueError:
                    results.append(adapter.fail("Corrupted Twitter token format"))
                    continue
            else:
                kwargs["access_token"] = conn.access_token

            # Some platforms (like LinkedIn) specifically require the DB URN ID
            kwargs["urn"] = conn.platform_user_id

            logger.info("Publishing to %s for user %s", platform_name, user_id)
            
            # Execute with exponential back-off wrapper provided by base adapter
            try:
                res = await adapter.retry(
                    adapter.post,
                    content=text_content,
                    image_urls=image_urls,
                    video_urls=video_urls,
                    **kwargs
                )
                results.append(res)
            except Exception as e:
                # Fatal retry exhaustion
                results.append(adapter.fail(f"All retries failed: {str(e)}"))
                logger.exception("Publishing failed on %s", platform_name)

        return results
