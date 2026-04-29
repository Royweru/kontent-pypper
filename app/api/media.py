"""
KontentPyper - Media Uploader API Router
Handles multiple file uploads to Cloudflare R2 bucket.
"""

import uuid
import asyncio
import boto3
from typing import List
from botocore.exceptions import ClientError
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends

from app.core.deps import CurrentUser
from app.core.config import settings
from app.core.upload_validation import (
    MAX_FILES_PER_REQUEST,
    validate_upload_file,
)

router = APIRouter()

# Initialize the S3 client to point to Cloudflare R2
# Make sure to handle cases where R2 configuration might not be fully set yet
def get_r2_client():
    if not settings.R2_ACCOUNT_ID or not settings.R2_ACCESS_KEY_ID or not settings.R2_SECRET_ACCESS_KEY:
        raise HTTPException(status_code=500, detail="Cloudflare R2 integration is not fully configured.")
    
    return boto3.client(
        service_name="s3",
        endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name="auto" # Default for Cloudflare R2
    )

@router.post("/upload", summary="Upload Media to Cloudflare R2")
async def upload_media(user: CurrentUser, files: List[UploadFile] = File(...)):
    """
    Accepts one or more files, uploads them to Cloudflare R2 bucket,
    and returns a list of resulting public URLs.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")
    if len(files) > MAX_FILES_PER_REQUEST:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files. Maximum allowed per request is {MAX_FILES_PER_REQUEST}.",
        )

    s3_client = get_r2_client()
    dev_url = settings.R2_PUBLIC_DEV_URL.rstrip('/')
    if not dev_url:
        raise HTTPException(500, "R2_PUBLIC_DEV_URL is not configured.")

    urls = []
    
    for file in files:
        try:
            ext, content_type, size_bytes = validate_upload_file(file)

            # Create a unique filename to avoid overwrites
            unique_filename = f"{uuid.uuid4().hex}{ext}"

            # Stream file object to R2 to avoid loading entire payload into memory.
            file.file.seek(0)
            await asyncio.to_thread(
                s3_client.upload_fileobj,
                file.file,
                settings.R2_BUCKET_NAME,
                unique_filename,
                {"ContentType": content_type},
            )
                
            public_url = f"{dev_url}/{unique_filename}"
            urls.append({
                "original_filename": file.filename,
                "url": public_url,
                "type": "video" if content_type.startswith("video") else "image",
                "size_bytes": size_bytes,
            })
            
        except HTTPException:
            raise
        except ClientError as e:
            raise HTTPException(status_code=500, detail=f"S3 Upload failed: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

    return {"uploaded": urls}
