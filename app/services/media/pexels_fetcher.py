import httpx
import logging
import random
import os
import asyncio
import re
import time
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

_PEXELS_QUERY_CACHE: dict[str, tuple[float, Optional[str]]] = {}
_PEXELS_QUERY_CACHE_TTL_SECONDS = 600

class PexelsFetcher:
    """
    Fetches raw stock footage from Pexels API to be used as B-Roll.
    Focuses on 9:16 vertical video suitable for Shorts/Reels/TikTok.
    """
    
    BASE_URL = "https://api.pexels.com/videos/search"
    
    def __init__(self):
        self.api_key = settings.PEXELS_API_KEY
        # Fallback queries if the LLM's query yields no results
        self.fallback_queries = ["technology abstract", "flowing abstract background", "ai neural network"]

    async def fetch_video(self, query: str, output_dir: str = "downloads") -> Optional[str]:
        """
        Searches Pexels and downloads a single HD vertical video clip.
        Returns the local filepath to the downloaded video, or None if failed.
        """
        if not self.api_key:
            logger.warning("Pexels API key not set. Skipping media fetch.")
            return None

        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # 1. Search for a video
        video_url = await self._search_for_video_url(query)
        
        # Fallback if no specific video found
        if not video_url:
            fallback = random.choice(self.fallback_queries)
            logger.info(f"No Pexels video found for '{query}'. Trying fallback: '{fallback}'")
            video_url = await self._search_for_video_url(fallback)

        if not video_url:
            logger.error("Could not find any suitable video on Pexels.")
            return None

        # 2. Download the video
        safe_query = re.sub(r"[^a-zA-Z0-9_-]+", "_", query).strip("_") or "stock"
        filename = f"pexels_{random.randint(1000,9999)}_{safe_query[:32]}.mp4"
        filepath = os.path.join(output_dir, filename)
        
        success = await self._download_file(video_url, filepath)
        return filepath if success else None

    async def _search_for_video_url(self, query: str) -> Optional[str]:
        cache_key = (query or "").strip().lower()
        if cache_key:
            cached = _PEXELS_QUERY_CACHE.get(cache_key)
            if cached:
                ts, cached_url = cached
                if (time.time() - ts) < _PEXELS_QUERY_CACHE_TTL_SECONDS:
                    return cached_url

        headers = {
            "Authorization": self.api_key
        }
        
        # Prioritize vertical orientation (portrait) and small/medium size
        params = {
            "query": query,
            "orientation": "portrait", 
            "size": "medium",
            "per_page": 10
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(self.BASE_URL, headers=headers, params=params)
                resp.raise_for_status()
                data = resp.json()

                videos = data.get("videos", [])
                if not videos:
                    if cache_key:
                        _PEXELS_QUERY_CACHE[cache_key] = (time.time(), None)
                    return None

                # Pick a random video from the top results to avoid repeating the exact same clip
                selected_video = random.choice(videos[:5])
                video_files = selected_video.get("video_files", [])

                # Find the best specific file (HD, ideally 1080x1920 or 720x1280)
                # Sort by height descending to get the best quality, but cap at 1920 to keep size reasonable
                hd_files = [
                    f for f in video_files
                    if isinstance(f, dict)
                    and int(f.get("height", 0) or 0) > 0
                    and int(f.get("width", 0) or 0) > 0
                    and int(f.get("height", 0) or 0) >= int(f.get("width", 0) or 0)  # portrait/square
                    and int(f.get("height", 0) or 0) <= 2000
                ]
                
                if hd_files:
                    hd_files.sort(key=lambda x: x.get("height", 0), reverse=True)
                    selected = hd_files[0]["link"]
                    if cache_key:
                        _PEXELS_QUERY_CACHE[cache_key] = (time.time(), selected)
                    return selected
                elif video_files:
                    selected = video_files[0]["link"]
                    if cache_key:
                        _PEXELS_QUERY_CACHE[cache_key] = (time.time(), selected)
                    return selected
                
                return None

        except httpx.HTTPError as e:
            logger.error(f"Pexels API error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error calling Pexels: {str(e)}")
            return None

    async def _download_file(self, url: str, filepath: str) -> bool:
        logger.info(f"Downloading Pexels video -> {filepath}")
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("GET", url) as r:
                    r.raise_for_status()
                    with open(filepath, "wb") as f:
                        async for chunk in r.aiter_bytes(chunk_size=8192):
                            f.write(chunk)
            logger.info("Download complete.")
            return True
        except Exception as e:
            logger.error(f"Failed to download video from Pexels: {str(e)}")
            if os.path.exists(filepath):
                os.remove(filepath)
            return False
