"""
Real stock-video pipeline:
Pexels clip fetch -> MoviePy composition -> R2 upload.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.schemas.content import VideoScript
from app.services.media.pexels_fetcher import PexelsFetcher
from app.services.media.storage import MediaStorageError, is_r2_configured, upload_local_media_to_r2
from app.services.media.video_composer import VideoComposer

logger = logging.getLogger(__name__)


class StockVideoPipelineError(RuntimeError):
    """Raised when stock-video generation cannot complete."""


class StockVideoPipelineService:
    def __init__(self):
        self.fetcher = PexelsFetcher()
        self.temp_dir = settings.VIDEO_TEMP_DIR or "temp"
        self.output_dir = settings.VIDEO_OUTPUT_DIR or "videos"
        self.composer = VideoComposer(output_dir=self.output_dir)

    async def generate_video(
        self,
        *,
        script: VideoScript,
        fallback_title: str,
        fallback_snippet: str = "",
    ) -> dict:
        """
        Generates and persists a stock video asset.
        Returns a dict with `video_url` and `storage_backend`.
        """
        search_query = (
            (script.search_query or "").strip()
            or fallback_title.strip()
            or "technology"
        )
        caption_text = (script.full_narration or "").strip() or fallback_snippet or fallback_title

        source_path: Optional[str] = None
        composed_path: Optional[str] = None
        cleanup_paths: list[str] = []

        try:
            source_path = await self.fetcher.fetch_video(search_query, output_dir=self.temp_dir)
            if not source_path:
                raise StockVideoPipelineError("No stock clip available from Pexels.")
            cleanup_paths.append(source_path)

            composed_path = await asyncio.to_thread(
                self.composer.create_short_video,
                source_path,
                caption_text,
            )
            if not composed_path:
                raise StockVideoPipelineError("MoviePy composition failed.")
            cleanup_paths.append(composed_path)

            if is_r2_configured():
                video_url = await upload_local_media_to_r2(
                    composed_path,
                    prefix="generated/stock",
                )
                storage_backend = "r2"
            else:
                # Last resort for local/dev environments when R2 is not configured.
                video_url = str(Path(composed_path).resolve())
                storage_backend = "local"

            return {
                "video_url": video_url,
                "storage_backend": storage_backend,
                "search_query": search_query,
            }
        except MediaStorageError as exc:
            logger.error("[StockVideoPipeline] Storage failed: %s", exc)
            raise StockVideoPipelineError(str(exc)) from exc
        except Exception as exc:
            logger.error("[StockVideoPipeline] Generation failed: %s", exc, exc_info=True)
            raise
        finally:
            self._safe_cleanup(cleanup_paths)

    @staticmethod
    def _safe_cleanup(paths: list[str]) -> None:
        for path in paths:
            try:
                if path and os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass

