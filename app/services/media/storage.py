"""
Cloud storage utilities for generated media assets.
"""

from __future__ import annotations

import asyncio
import mimetypes
import os
import uuid
from pathlib import Path

import boto3

from app.core.config import settings


class MediaStorageError(RuntimeError):
    """Raised when media upload/persistence fails."""


def is_r2_configured() -> bool:
    return all(
        [
            settings.R2_ACCOUNT_ID,
            settings.R2_ACCESS_KEY_ID,
            settings.R2_SECRET_ACCESS_KEY,
            settings.R2_BUCKET_NAME,
            settings.R2_PUBLIC_DEV_URL,
        ]
    )


def _r2_client():
    if not is_r2_configured():
        raise MediaStorageError("Cloudflare R2 is not fully configured.")
    return boto3.client(
        service_name="s3",
        endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )


async def upload_local_media_to_r2(local_path: str, *, prefix: str = "generated-videos") -> str:
    """
    Upload a local media file to Cloudflare R2 and return its public URL.
    """
    if not os.path.exists(local_path):
        raise MediaStorageError(f"Local file not found: {local_path}")

    filename = Path(local_path).name
    ext = Path(filename).suffix or ".bin"
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    object_key = f"{prefix.strip('/')}/{uuid.uuid4().hex}{ext}"

    client = _r2_client()

    def _upload():
        with open(local_path, "rb") as fh:
            client.upload_fileobj(
                fh,
                settings.R2_BUCKET_NAME,
                object_key,
                ExtraArgs={"ContentType": content_type},
            )

    await asyncio.to_thread(_upload)
    return f"{settings.R2_PUBLIC_DEV_URL.rstrip('/')}/{object_key}"

