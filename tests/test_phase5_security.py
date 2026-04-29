import io

import pytest
from fastapi import HTTPException

from app.api import news
from app.core import upload_validation


class DummyUploadFile:
    def __init__(self, filename: str, content_type: str, data: bytes):
        self.filename = filename
        self.content_type = content_type
        self.file = io.BytesIO(data)


def test_news_rejects_non_http_schemes():
    with pytest.raises(HTTPException) as exc:
        news._validate_preview_url_shape("file:///etc/passwd")
    assert exc.value.status_code == 400


def test_news_rejects_localhost_hosts():
    with pytest.raises(HTTPException) as exc:
        news._validate_preview_url_shape("http://localhost/feed.xml")
    assert exc.value.status_code == 400


def test_news_flags_private_ips():
    assert news._is_disallowed_ip("127.0.0.1") is True
    assert news._is_disallowed_ip("10.0.0.3") is True
    assert news._is_disallowed_ip("8.8.8.8") is False


def test_media_rejects_unsupported_extension():
    upload = DummyUploadFile("clip.exe", "video/mp4", b"abc")
    with pytest.raises(HTTPException) as exc:
        upload_validation.validate_upload_file(upload)
    assert exc.value.status_code == 415


def test_media_rejects_unsupported_content_type():
    upload = DummyUploadFile("clip.mp4", "application/octet-stream", b"abc")
    with pytest.raises(HTTPException) as exc:
        upload_validation.validate_upload_file(upload)
    assert exc.value.status_code == 415


def test_media_rejects_oversized_payload():
    original_limit = upload_validation.MAX_FILE_SIZE_BYTES
    original_limit_mb = upload_validation.MAX_FILE_SIZE_MB
    upload_validation.MAX_FILE_SIZE_BYTES = 2
    upload_validation.MAX_FILE_SIZE_MB = 2
    try:
        upload = DummyUploadFile("clip.mp4", "video/mp4", b"12345")
        with pytest.raises(HTTPException) as exc:
            upload_validation.validate_upload_file(upload)
        assert exc.value.status_code == 413
    finally:
        upload_validation.MAX_FILE_SIZE_BYTES = original_limit
        upload_validation.MAX_FILE_SIZE_MB = original_limit_mb


def test_media_accepts_valid_image_file():
    upload = DummyUploadFile("photo.png", "image/png", b"12345")
    ext, content_type, size = upload_validation.validate_upload_file(upload)
    assert ext == ".png"
    assert content_type == "image/png"
    assert size == 5
