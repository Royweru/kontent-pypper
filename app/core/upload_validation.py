"""
Upload validation helpers used by media API.
"""

from __future__ import annotations

import os
from fastapi import HTTPException, UploadFile

MAX_FILES_PER_REQUEST = int(os.getenv("UPLOAD_MAX_FILES", "5"))
MAX_FILE_SIZE_MB = int(os.getenv("UPLOAD_MAX_FILE_MB", "100"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

ALLOWED_MIME_PREFIXES = ("image/", "video/")
ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".gif",
    ".mp4", ".mov", ".m4v", ".webm",
}


def file_size_bytes(upload: UploadFile) -> int:
    file_obj = upload.file
    current = file_obj.tell()
    file_obj.seek(0, os.SEEK_END)
    size = file_obj.tell()
    file_obj.seek(current, os.SEEK_SET)
    return int(size)


def validate_upload_file(upload: UploadFile) -> tuple[str, str, int]:
    filename = (upload.filename or "").strip()
    if not filename:
        raise HTTPException(status_code=400, detail="Each file must have a filename.")

    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file extension '{ext}'.",
        )

    content_type = (upload.content_type or "").strip().lower()
    if not any(content_type.startswith(prefix) for prefix in ALLOWED_MIME_PREFIXES):
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported content type '{content_type or 'unknown'}'.",
        )

    size = file_size_bytes(upload)
    if size <= 0:
        raise HTTPException(status_code=400, detail=f"File '{filename}' is empty.")
    if size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                f"File '{filename}' exceeds maximum allowed size "
                f"({MAX_FILE_SIZE_MB} MB)."
            ),
        )

    return ext, content_type, size
