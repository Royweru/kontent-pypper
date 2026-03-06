"""
KontentPyper - Auth Schemas
Pydantic models for authentication request/response payloads.
"""

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserRegister(BaseModel):
    email: EmailStr
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    is_active: bool
    plan: str
    posts_used: int
    posts_limit: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TelegramSettings(BaseModel):
    bot_token: str


class TelegramDetectResponse(BaseModel):
    success: bool
    chat_id: Optional[str] = None
    username: Optional[str] = None
    message: str = ""
