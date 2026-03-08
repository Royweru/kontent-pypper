"""
KontentPyper - OAuth Service
Universal OAuth 1.0a / 2.0 state manager, decoupling configs to platform adapters.
"""

import secrets
import hashlib
import base64
import time
import httpx
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlencode, quote, parse_qsl
from jose import jwt, JWTError

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.core.config import settings
from app.models.social import SocialConnection

# Import platform adapters
from app.services.platforms.twitter import TwitterService
from app.services.platforms.youtube import YouTubeService
from app.services.platforms.linkedin import LinkedInService
from app.services.platforms.tiktok import TikTokService

logger = logging.getLogger(__name__)

# Dynamic registry - avoids God-class configuration
PLATFORMS = {
    "twitter":  TwitterService(settings.TWITTER_API_KEY, settings.TWITTER_API_SECRET),
    "youtube":  YouTubeService(settings.GOOGLE_CLIENT_ID, settings.GOOGLE_CLIENT_SECRET),
    "linkedin": LinkedInService(settings.LINKEDIN_CLIENT_ID, settings.LINKEDIN_CLIENT_SECRET),
    "tiktok":   TikTokService(settings.TIKTOK_CLIENT_ID, settings.TIKTOK_CLIENT_SECRET),
}

# OAuth 1.0a in-memory state storage (short-lived)
_oauth1_states = {}


class OAuthService:
    """Orchestrates OAuth flows using configs provided by platform adapters."""

    BASE_URL = settings.BACKEND_URL.rstrip("/")
    CALLBACK_PATH = "/api/v1/social/oauth/callback"

    @classmethod
    def _get_config(cls, platform: str) -> dict:
        if platform not in PLATFORMS:
            raise HTTPException(400, f"Unsupported platform: {platform}")
        
        config = PLATFORMS[platform].get_oauth_config()
        config["redirect_uri"] = f"{cls.BASE_URL}{cls.CALLBACK_PATH}/{platform}"
        # For Twitter OAuth 1.0a
        config["callback_uri"] = config["redirect_uri"]
        return config

    # ── 1. Initiate ───────────────────────────────────────────────

    @classmethod
    async def initiate_oauth(cls, user_id: int, platform: str) -> str:
        """Route to OAuth 1.0a or 2.0 based on platform config."""
        config = cls._get_config(platform)
        protocol = config.get("protocol", "oauth2")

        logger.info("[OAuth] Initiating %s flow for %s", protocol, platform)

        if protocol == "oauth1":
            return await cls._initiate_oauth1(user_id, platform, config)
        else:
            return await cls._initiate_oauth2(user_id, platform, config)

    @classmethod
    async def _initiate_oauth1(cls, user_id: int, platform: str, config: dict) -> str:
        """ OAuth 1.0a (Twitter) request token fetching without heavy libraries."""
        import uuid
        import hmac

        # 1. Build auth headers for request token
        nonce = uuid.uuid4().hex
        timestamp = str(int(time.time()))
        
        params = {
            "oauth_callback": config["callback_uri"],
            "oauth_consumer_key": config["consumer_key"],
            "oauth_nonce": nonce,
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": timestamp,
            "oauth_version": "1.0"
        }
        
        # Build base signature string
        sorted_params = "&".join(f"{quote(k, safe='')}={quote(v, safe='')}" for k, v in sorted(params.items()))
        base = f"POST&{quote(config['request_token_url'], safe='')}&{quote(sorted_params, safe='')}"
        
        signing_key = f"{quote(config['consumer_secret'], safe='')}&"
        digest = hmac.new(signing_key.encode(), base.encode(), hashlib.sha1).digest()
        params["oauth_signature"] = base64.b64encode(digest).decode()

        auth_header = "OAuth " + ", ".join(f'{quote(k, safe="")}="{quote(v, safe="")}"' for k, v in params.items())

        # 2. Fetch token via POST
        async with httpx.AsyncClient() as client:
            resp = await client.post(config["request_token_url"], headers={"Authorization": auth_header})
            
        if resp.status_code != 200:
            raise HTTPException(500, "Failed to get OAuth1 request token")

        # Parse token string like "oauth_token=XYZ&oauth_token_secret=ABC..."
        data = dict(parse_qsl(resp.text))
        oauth_token = data.get("oauth_token")
        oauth_secret = data.get("oauth_token_secret")
        
        # 3. Store server state
        _oauth1_states[oauth_token] = {
            "user_id": user_id,
            "secret": oauth_secret,
            "created_at": datetime.utcnow()
        }

        return f"{config['authorize_url']}?oauth_token={oauth_token}"

    @classmethod
    async def _initiate_oauth2(cls, user_id: int, platform: str, config: dict) -> str:
        """OAuth 2.0 URL generation."""
        state = secrets.token_urlsafe(16)
        
        state_payload = {
            "user_id": user_id,
            "platform": platform,
            "state": state,
            "exp": datetime.utcnow() + timedelta(minutes=15)
        }

        # TikTok requires specific client_id param mapping
        sid_param = config.get("client_id_param_name", "client_id")

        params = {
            "response_type": config.get("response_type", "code"),
            sid_param: config["client_id"],
            "redirect_uri": config["redirect_uri"],
        }
        
        if config.get("scope"):
            params["scope"] = config["scope"]
            
        params.update(config.get("auth_params", {}))

        # PKCE check
        if config.get("uses_pkce"):
            verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
            challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode('utf-8')).digest()).decode('utf-8').rstrip('=')
            
            params.update({"code_challenge": challenge, "code_challenge_method": "S256"})
            state_payload["pkce_verifier"] = verifier

        # JWT sign state
        state_jwt = jwt.encode(state_payload, settings.SECRET_KEY, algorithm="HS256")
        params["state"] = state_jwt

        return f"{config['auth_url']}?{urlencode(params, quote_via=quote)}"


    # ── 2. Callbacks ──────────────────────────────────────────────

    @classmethod
    async def handle_callback(
        cls,
        platform: str,
        db: AsyncSession,
        code: Optional[str] = None,
        state: Optional[str] = None,
        oauth_token: Optional[str] = None,
        oauth_verifier: Optional[str] = None,
        error: Optional[str] = None
    ) -> dict:
        """Route to appropriate protocol handler."""
        if error:
            return {"success": False, "error": error}
            
        config = cls._get_config(platform)
        protocol = config.get("protocol", "oauth2")

        if protocol == "oauth1":
            if not oauth_token or not oauth_verifier:
                return {"success": False, "error": "Missing OAuth1 parameters"}
            return await cls._handle_oauth1_callback(platform, config, db, oauth_token, oauth_verifier)
        else:
            if not code or not state:
                return {"success": False, "error": "Missing OAuth2 code/state"}
            return await cls._handle_oauth2_callback(platform, config, db, code, state)

    @classmethod
    async def _handle_oauth1_callback(
        cls, platform: str, config: dict, db: AsyncSession,
        oauth_token: str, oauth_verifier: str
    ) -> dict:
        import uuid, hmac, urllib
        
        state_data = _oauth1_states.pop(oauth_token, None)
        if not state_data:
            return {"success": False, "error": "Expired flow state"}
            
        user_id = state_data["user_id"]
        token_secret = state_data["secret"]

        # Exchange verifier for real tokens
        nonce = uuid.uuid4().hex
        timestamp = str(int(time.time()))
        params = {
            "oauth_consumer_key": config["consumer_key"],
            "oauth_nonce": nonce,
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": timestamp,
            "oauth_token": oauth_token,
            "oauth_verifier": oauth_verifier,
            "oauth_version": "1.0"
        }
        
        # Build signature using temporary token secret
        sorted_params = "&".join(f"{quote(k, safe='')}={quote(v, safe='')}" for k, v in sorted(params.items()))
        base = f"POST&{quote(config['access_token_url'], safe='')}&{quote(sorted_params, safe='')}"
        signing_key = f"{quote(config['consumer_secret'], safe='')}&{quote(token_secret, safe='')}"
        
        digest = hmac.new(signing_key.encode(), base.encode(), hashlib.sha1).digest()
        params["oauth_signature"] = base64.b64encode(digest).decode()
        auth_header = "OAuth " + ", ".join(f'{quote(k, safe="")}="{quote(v, safe="")}"' for k, v in params.items())

        async with httpx.AsyncClient() as client:
            resp = await client.post(config["access_token_url"], headers={"Authorization": auth_header})

        if resp.status_code != 200:
            return {"success": False, "error": "Token exchange failed"}

        tokens = dict(urllib.parse.parse_qsl(resp.text))
        final_access = tokens.get("oauth_token")
        final_secret = tokens.get("oauth_token_secret")

        user_info = await PLATFORMS[platform].get_user_info(final_access, token_secret=final_secret)

        return await cls._save_db(db, user_id, platform, protocol="oauth1", 
                           access_token=f"{final_access}:{final_secret}", 
                           user_info=user_info)


    @classmethod
    async def _handle_oauth2_callback(
        cls, platform: str, config: dict, db: AsyncSession,
        code: str, state: str
    ) -> dict:
        try:
            payload = jwt.decode(state, settings.SECRET_KEY, algorithms=["HS256"])
        except JWTError:
            return {"success": False, "error": "Invalid state token"}
            
        user_id = payload["user_id"]
        verifier = payload.get("pkce_verifier")
        
        sid_param = config.get("client_id_param_name", "client_id")
        
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": config["redirect_uri"],
        }
        
        if config.get("token_auth_method") != "basic":
            token_data[sid_param] = config["client_id"]
            token_data["client_secret"] = config["client_secret"]
            
        if config.get("uses_pkce") and verifier:
            token_data["code_verifier"] = verifier

        auth = (config["client_id"], config["client_secret"]) if config.get("token_auth_method") == "basic" else None

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.post(
                config["token_url"],
                data=token_data,
                auth=auth,
                headers={"Accept": "application/json"}
            )
            
            if resp.status_code != 200:
                logger.error("[%s] OAuth exchange failed: %s", platform, resp.text)
                return {"success": False, "error": "Exchange failed"}
                
            data = resp.json()
            access_token = data.get("access_token")
            
            user_info = await PLATFORMS[platform].get_user_info(access_token)

        return await cls._save_db(
            db, user_id, platform, "oauth2", 
            access_token=access_token,
            refresh_token=data.get("refresh_token"),
            expires_in=data.get("expires_in"),
            user_info=user_info
        )


    # ── Database Persistence ──────────────────────────────────────

    @classmethod
    async def _save_db(
        cls, db: AsyncSession, user_id: int, platform: str, protocol: str,
        access_token: str, user_info: dict,
        refresh_token: str = None, expires_in: int = None
    ) -> dict:
        
        expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in)) if expires_in else None
        
        q = select(SocialConnection).where(
            SocialConnection.user_id == user_id,
            SocialConnection.platform == platform.upper(),
            SocialConnection.platform_user_id == user_info["id"]
        )
        conn = (await db.execute(q)).scalar_one_or_none()

        if conn:
            conn.access_token = access_token
            conn.refresh_token = refresh_token
            conn.token_expires_at = expires_at
            conn.is_active = True
            conn.platform_username = user_info.get("username", "")
            conn.username = user_info.get("username", "")
            conn.updated_at = datetime.utcnow()
        else:
            conn = SocialConnection(
                user_id=user_id,
                platform=platform.upper(),
                protocol=protocol,
                platform_user_id=user_info["id"],
                platform_username=user_info.get("username", ""),
                username=user_info.get("username", ""),
                access_token=access_token,
                refresh_token=refresh_token,
                token_expires_at=expires_at,
                is_active=True
            )
            db.add(conn)

        await db.commit()
        return {"success": True, "platform": platform, "username": conn.username}
