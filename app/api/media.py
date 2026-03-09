"""
KontentPyper - Media Uploader API Router
Handles multiple file uploads to Cloudflare R2 bucket.
"""

import os
import uuid
import boto3
from typing import List
from botocore.exceptions import ClientError
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends

from app.api.deps import CurrentUser
from app.core.config import settings

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

    s3_client = get_r2_client()
    urls = []
    
    for file in files:
        try:
            # Create a unique filename to avoid overwrites
            ext = os.path.splitext(file.filename)[1]
            unique_filename = f"{uuid.uuid4().hex}{ext}"
            
            # Read file data
            file_bytes = await file.read()
            
            # Identify content type (Boto3 doesn't auto-detect for raw bytes robustly sometimes)
            content_type = file.content_type or "application/octet-stream"
            
            # Upload to R2 Bucket
            s3_client.put_object(
                Bucket=settings.R2_BUCKET_NAME,
                Key=unique_filename,
                Body=file_bytes,
                ContentType=content_type
            )
            
            # Construct public URL
            dev_url = settings.R2_PUBLIC_DEV_URL.rstrip('/')
            if not dev_url:
                # Fallback to dev url requirement, otherwise media won't be accessible publicly
                raise HTTPException(500, "R2_PUBLIC_DEV_URL is not configured.")
                
            public_url = f"{dev_url}/{unique_filename}"
            urls.append({
                "original_filename": file.filename,
                "url": public_url,
                "type": "video" if content_type.startswith("video") else "image"
            })
            
        except ClientError as e:
            raise HTTPException(status_code=500, detail=f"S3 Upload failed: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

    return {"uploaded": urls}
