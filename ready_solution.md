# EXAMPLE OF REAL APP CODE 
I want you to copy the logic and implementation I'm using for the api with the social media platforms

** OAUTH INITILIZATION AND SERVICE **

```
# app/services/oauth_service.py
import secrets
import hashlib
import base64
from typing import Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from urllib.parse import urlencode, quote
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from jose import jwt, JWTError
from ..config import settings
from app import models

# --- OAuth Configuration ---
BASE_URL = settings.BACKEND_URL.rstrip("/")
CALLBACK_PATH = "/social/oauth/callback"

# Global state storage for OAuth 1.0a
_oauth1_states = {}


def _clean_oauth1_states():
    """Remove expired OAuth 1.0a states (older than 15 minutes)"""
    cutoff = datetime.utcnow() - timedelta(minutes=15)
    expired = [k for k, v in _oauth1_states.items() if v.get(
        "created_at", datetime.utcnow()) < cutoff]
    for k in expired:
        del _oauth1_states[k]


OAUTH_CONFIGS = {
    # ========================================================================
    # TWITTER - OAuth 1.0a (Three-Legged Flow)
    # ========================================================================
    "twitter": {
        "protocol": "oauth1",
        "consumer_key": settings.TWITTER_API_KEY,
        "consumer_secret": settings.TWITTER_API_SECRET,
        "request_token_url": "https://api.twitter.com/oauth/request_token",
        "authorize_url": "https://api.twitter.com/oauth/authorize",
        "access_token_url": "https://api.twitter.com/oauth/access_token",
        "callback_uri": f"{BASE_URL}{CALLBACK_PATH}/twitter",
        "user_info_url": "https://api.twitter.com/2/users/me",
        "platform_display_name": "Twitter/X"
    },



    # ========================================================================
    # LINKEDIN - OAuth 2.0
    # ========================================================================
    "linkedin": {
        "protocol": "oauth2",
        "client_id": settings.LINKEDIN_CLIENT_ID,
        "client_secret": settings.LINKEDIN_CLIENT_SECRET,
        "auth_url": "https://www.linkedin.com/oauth/v2/authorization",
        "token_url": "https://www.linkedin.com/oauth/v2/accessToken",
        "redirect_uri": f"{BASE_URL}{CALLBACK_PATH}/linkedin",
        "scope": "openid profile email w_member_social",
        "user_info_url": "https://api.linkedin.com/v2/userinfo",
        "uses_pkce": False,
        "token_auth_method": "body",
        "response_type": "code",
        "auth_params": {},
        "platform_display_name": "LinkedIn"
    },

    # ========================================================================
    # YOUTUBE (Google) - OAuth 2.0
    # ========================================================================
    "youtube": {
        "protocol": "oauth2",
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "redirect_uri": f"{BASE_URL}{CALLBACK_PATH}/youtube",
        "scope": "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/userinfo.profile",
        "user_info_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        "uses_pkce": False,
        "token_auth_method": "body",
        "response_type": "code",
        "auth_params": {
            "access_type": "offline",
            "prompt": "consent"
        },
        "platform_display_name": "YouTube"
    },

    # ========================================================================
    # TIKTOK - OAuth 2.0 with PKCE (FIXED)
    # ========================================================================
    "tiktok": {
        "protocol": "oauth2",
        "client_id": settings.TIKTOK_CLIENT_ID,
        "client_secret": settings.TIKTOK_CLIENT_SECRET,
        # 1. AUTH URL: Use www.tiktok.com for user interaction
        "auth_url": "https://www.tiktok.com/v2/auth/authorize/",
        # 2. TOKEN URL: Use open.tiktokapis.com with TRAILING SLASH for API calls
        "token_url": "https://open.tiktokapis.com/v2/oauth/token/",
        "redirect_uri": f"{BASE_URL}{CALLBACK_PATH}/tiktok",
        "scope": "user.info.basic,video.upload,video.publish",
        "user_info_url": "https://open.tiktokapis.com/v2/user/info/",
        "uses_pkce": True,
        "token_auth_method": "body",
        "response_type": "code",
        # 3. PARAMETER NAME: TikTok uses 'client_key', not 'client_id'
        "client_id_param_name": "client_key",
        "auth_params": {},
        "platform_display_name": "TikTok"
    }
}


class OAuthService:
    """
    Universal OAuth service supporting both OAuth 1.0a and OAuth 2.0.
    """

    # ========================================================================
    # MAIN ENTRY POINTS
    # ========================================================================

    @classmethod
    async def initiate_oauth(cls, user_id: int, platform: str) -> str:
        """
        Main entry point for initiating OAuth flow.
        Routes to OAuth 1.0a or 2.0 based on platform configuration.
        """
        platform = platform.lower()

        if platform not in OAUTH_CONFIGS:
            raise HTTPException(500, f"Platform {platform} not configured")

        config = OAUTH_CONFIGS[platform]
        protocol = config.get("protocol", "oauth2")

        print(f"\n{'='*60}")
        print(f"Initiating {protocol.upper()} flow for {platform.upper()}")
        print(f"{'='*60}\n")

        if protocol == "oauth1":
            return await cls._initiate_oauth1(user_id, platform, config)
        else:
            return await cls._initiate_oauth2(user_id, platform, config)

    @classmethod
    async def handle_oauth_callback(
        cls, platform: str,
        code: Optional[str], state: Optional[str],
        oauth_token: Optional[str], oauth_verifier: Optional[str],
        db: AsyncSession,
        error: Optional[str] = None
    ) -> Dict:
        """
        Main entry point for handling OAuth callbacks.
        """
        if error:
            return {"success": False, "error": f"Authorization denied: {error}"}

        platform = platform.lower()
        if platform not in OAUTH_CONFIGS:
            return {"success": False, "error": f"Unsupported platform: {platform}"}

        config = OAUTH_CONFIGS[platform]

        # Determine protocol based on parameters
        is_oauth1 = bool(oauth_token and oauth_verifier)
        is_oauth2 = bool(code)

        print(f"\n{'='*60}")
        print(f"📥 OAuth Callback - {platform.upper()}")
        print(f"OAuth 1.0a params: {is_oauth1}")
        print(f"OAuth 2.0 params: {is_oauth2}")
        print(f"State present: {bool(state)}")
        print(f"{'='*60}\n")

        if is_oauth1:
            return await cls._handle_oauth1_callback(
                platform, oauth_token, oauth_verifier, config, db
            )
        elif is_oauth2:
            if not state:
                return {
                    "success": False,
                    "error": "Missing state parameter for OAuth 2.0 flow"
                }

            return await cls._handle_oauth2_callback(
                platform, code, state, config, db
            )
        else:
            return {
                "success": False,
                "error": "Missing required OAuth parameters"
            }

    @classmethod
    async def _initiate_oauth1(cls, user_id: int, platform: str, config: Dict) -> str:
        """OAuth 1.0a Three-Legged Flow - Step 1 & 2"""
        try:
            from requests_oauthlib import OAuth1Session

            # Step 1: Create OAuth1 session
            oauth = OAuth1Session(
                config["consumer_key"],
                client_secret=config["consumer_secret"],
                callback_uri=config["callback_uri"]
            )

            # Step 2: Get request token
            fetch_response = oauth.fetch_request_token(
                config["request_token_url"])
            oauth_token = fetch_response.get('oauth_token')
            oauth_token_secret = fetch_response.get('oauth_token_secret')

            if not oauth_token or not oauth_token_secret:
                raise HTTPException(500, "Failed to get request token")

            # Store state server-side using oauth_token as key
            _clean_oauth1_states()
            _oauth1_states[oauth_token] = {
                "user_id": user_id,
                "platform": platform,
                "oauth_token_secret": oauth_token_secret,
                "created_at": datetime.utcnow()
            }

            print(f"OAuth 1.0a: Stored state for token: {oauth_token[:20]}...")

            authorization_url = oauth.authorization_url(
                config["authorize_url"])
            return authorization_url

        except Exception as e:
            print(f" OAuth 1.0a error: {e}")
            raise HTTPException(500, f"Failed to initiate OAuth: {str(e)}")

    @classmethod
    async def _handle_oauth1_callback(
        cls, platform: str, oauth_token: str, oauth_verifier: str,
        config: Dict, db: AsyncSession
    ) -> Dict:
        """OAuth 1.0a Three-Legged Flow - Step 3"""
        try:
            from requests_oauthlib import OAuth1Session

            state_data = _oauth1_states.get(oauth_token)

            if not state_data:
                return {
                    "success": False,
                    "error": "Invalid or expired authorization session."
                }

            user_id = state_data["user_id"]
            oauth_token_secret = state_data["oauth_token_secret"]
            del _oauth1_states[oauth_token]

            # Exchange for access token
            oauth = OAuth1Session(
                config["consumer_key"],
                client_secret=config["consumer_secret"],
                resource_owner_key=oauth_token,
                resource_owner_secret=oauth_token_secret,
                verifier=oauth_verifier
            )

            oauth_tokens = oauth.fetch_access_token(config["access_token_url"])
            access_token = oauth_tokens.get('oauth_token')
            access_token_secret = oauth_tokens.get('oauth_token_secret')

            if not access_token or not access_token_secret:
                return {"success": False, "error": "Failed to get access tokens"}

            combined_token = f"{access_token}:{access_token_secret}"

            # Get user info
            oauth_for_api = OAuth1Session(
                config["consumer_key"],
                client_secret=config["consumer_secret"],
                resource_owner_key=access_token,
                resource_owner_secret=access_token_secret
            )

            user_response = oauth_for_api.get(
                config["user_info_url"], timeout=10)

            user_info = {}
            if user_response.status_code == 200:
                user_data = user_response.json()
                if "data" in user_data:
                    user_info = {
                        "user_id": user_data["data"]["id"],
                        "username": user_data["data"]["username"],
                        "name": user_data["data"]["name"]
                    }
                else:
                    user_info = {
                        "user_id": str(oauth_tokens.get("user_id", "")),
                        "username": oauth_tokens.get("screen_name", ""),
                        "name": oauth_tokens.get("screen_name", "")
                    }
            else:
                user_info = {
                    "user_id": str(oauth_tokens.get("user_id", "")),
                    "username": oauth_tokens.get("screen_name", "Unknown"),
                    "name": oauth_tokens.get("screen_name", "Unknown")
                }

            # Save connection
            await cls._save_connection(
                db=db,
                user_id=user_id,
                platform=platform.upper(),
                access_token=combined_token,
                refresh_token=None,
                expires_in=None,
                platform_user_id=user_info["user_id"],
                platform_username=user_info["username"],
                platform_name=user_info["name"],
                platform_protocol="oauth1",
                oauth_token_secret=access_token_secret
            )

            return {
                "success": True,
                "platform": platform,
                "username": user_info["username"]
            }

        except Exception as e:
            print(f" OAuth 1.0a callback error: {e}")
            return {"success": False, "error": str(e)}

    # ========================================================================
    # OAUTH 2.0 IMPLEMENTATION (ALL OTHER PLATFORMS)
    # ========================================================================

    @classmethod
    async def _initiate_oauth2(cls, user_id: int, platform: str, config: Dict) -> str:
        """OAuth 2.0 Authorization Code Flow - Step 1"""
        try:
            # Generate state
            state = secrets.token_urlsafe(16)
            state_payload = {
                "user_id": user_id,
                "platform": platform,
                "state": state,
                "exp": datetime.utcnow() + timedelta(minutes=15)
            }

            client_id_param_name = config.get(
                "client_id_param_name", "client_id")

            # Build parameters
            params = {
                "response_type": config.get("response_type", "code"),
                # Uses 'client_key' if configured
                client_id_param_name: config["client_id"],
                "redirect_uri": config["redirect_uri"],
                "state": state
            }

            if config.get("scope"):
                params["scope"] = config["scope"]

            params.update(config.get("auth_params", {}))

            # Handle PKCE
            if config.get("uses_pkce", False):
                code_verifier = cls._generate_code_verifier()
                code_challenge = cls._generate_code_challenge(code_verifier)
                params.update({
                    "code_challenge": code_challenge,
                    "code_challenge_method": "S256"
                })
                state_payload["pkce_verifier"] = code_verifier

            # Encode state
            state_jwt = jwt.encode(
                state_payload, settings.SECRET_KEY, algorithm="HS256")
            params["state"] = state_jwt

            # Build URL
            query_string = urlencode(params, quote_via=quote)
            auth_url = f"{config['auth_url']}?{query_string}"

            print(f" OAuth 2.0 authorization URL generated for {platform}")
            return auth_url

        except Exception as e:
            print(f" OAuth 2.0 error: {e}")
            raise HTTPException(500, f"Failed to initiate OAuth: {str(e)}")

    @classmethod
    async def _handle_oauth2_callback(
        cls, platform: str, code: str, state: str,
        config: Dict, db: AsyncSession
    ) -> Dict:
        """OAuth 2.0 Authorization Code Flow - Step 2"""
        try:
            # Decode state
            state_payload = jwt.decode(
                state, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = state_payload["user_id"]
            code_verifier = state_payload.get("pkce_verifier")

            client_id_param_name = config.get(
                "client_id_param_name", "client_id")

            # Build token request
            token_params = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": config["redirect_uri"],
            }

            # Add client credentials to body if not basic auth
            if config.get("token_auth_method") != "basic":
                token_params[client_id_param_name] = config["client_id"]
                token_params["client_secret"] = config["client_secret"]

            if config.get("uses_pkce", False) and code_verifier:
                token_params["code_verifier"] = code_verifier

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "User-Agent": "SkedulukApp/1.0 (compatible; httpx/0.23.0)"
            }

            auth = None
            if config.get("token_auth_method") == "basic":
                auth = (config["client_id"], config["client_secret"])

            # Exchange code for token
            # ⚠️ CRITICAL FIX: follow_redirects=True to handle potential 301/308 redirects from TikTok
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                print(
                    f" Exchanging code for token with {config['token_url']}")
                token_response = await client.post(
                    config["token_url"],
                    data=token_params,
                    headers=headers,
                    auth=auth
                )

                if token_response.status_code != 200:
                    print(
                        f" Token exchange failed. Status: {token_response.status_code}")
                    print(f" Response body: {token_response.text}")
                    return {
                        "success": False,
                        "error": f"Token exchange failed: {token_response.status_code} {token_response.text[:200]}"
                    }

                token_data = token_response.json()
                access_token = token_data.get("access_token")

                if not access_token:
                    return {"success": False, "error": "No access token received"}

                # Exchange for long-lived token (Facebook/Instagram)
                if config.get("exchange_token"):
                    access_token, token_data = await cls._exchange_long_lived_token(
                        platform, access_token, config, client
                    )

                # Get user info
                user_info = await cls._get_platform_user_info(
                    platform, access_token, config["user_info_url"], client
                )

                if not user_info:
                    return {"success": False, "error": "Failed to get user profile"}

                # Save connection
                connection = await cls._save_connection(
                    db=db,
                    user_id=user_id,
                    platform=platform.upper(),
                    access_token=access_token,
                    refresh_token=token_data.get("refresh_token"),
                    expires_in=token_data.get("expires_in"),
                    platform_user_id=user_info.get("user_id"),
                    platform_username=user_info.get("username"),
                    platform_name=user_info.get("name"),
                    platform_protocol=config.get("protocol"),
                    oauth_token_secret=None
                )

                return {
                    "success": True,
                    "platform": platform,
                    "username": user_info.get("username") or user_info.get("name")
                }

        except JWTError:
            return {"success": False, "error": "Invalid or expired connection link"}
        except Exception as e:
            print(f" OAuth 2.0 callback error: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}

    @staticmethod
    def _generate_code_verifier() -> str:
        """Generate code verifier for PKCE (43-128 characters)"""
        verifier = base64.urlsafe_b64encode(
            secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        return verifier

    @staticmethod
    def _generate_code_challenge(verifier: str) -> str:
        """Generate code challenge from verifier using S256"""
        digest = hashlib.sha256(verifier.encode('utf-8')).digest()
        challenge = base64.urlsafe_b64encode(
            digest).decode('utf-8').rstrip('=')
        return challenge

    @classmethod
    async def _exchange_long_lived_token(
        cls, platform: str, short_token: str, config: Dict, client: httpx.AsyncClient
    ) -> Tuple[str, Dict]:
        """Exchange short-lived token for long-lived token (Facebook/Instagram)"""
        try:
            exchange_url = "https://graph.facebook.com/v20.0/oauth/access_token"
            params = {
                "grant_type": "fb_exchange_token",
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "fb_exchange_token": short_token
            }

            response = await client.get(exchange_url, params=params)

            if response.status_code == 200:
                data = response.json()
                return data["access_token"], data
            else:
                return short_token, {"access_token": short_token, "expires_in": 3600}

        except Exception as e:
            return short_token, {"access_token": short_token, "expires_in": 3600}

    @classmethod
    async def refresh_access_token(
        cls, connection: models.SocialConnection, db: AsyncSession
    ) -> Optional[Dict]:
        """Refresh an expired access token"""
        platform = connection.platform.lower()
        refresh_token = connection.refresh_token

        if not refresh_token or platform not in OAUTH_CONFIGS:
            return None

        config = OAUTH_CONFIGS[platform]
        client_id_param_name = config.get("client_id_param_name", "client_id")

        try:
            refresh_params = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                client_id_param_name: config["client_id"],
            }

            if config.get("token_auth_method") != "basic":
                refresh_params["client_secret"] = config["client_secret"]

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "User-Agent": "SkedulukApp/1.0"
            }

            auth = None
            if config.get("token_auth_method") == "basic":
                auth = (config["client_id"], config["client_secret"])

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    config["token_url"],
                    data=refresh_params,
                    headers=headers,
                    auth=auth
                )

                if response.status_code != 200:
                    print(f"Token refresh failed: {response.text}")
                    connection.is_active = False
                    await db.commit()
                    return None

                token_data = response.json()
                new_access_token = token_data.get("access_token")
                new_refresh_token = token_data.get(
                    "refresh_token", refresh_token)
                expires_in = token_data.get("expires_in")

                if not new_access_token:
                    return None

                # Update connection
                connection.access_token = new_access_token
                connection.refresh_token = new_refresh_token
                connection.token_expires_at = (
                    datetime.utcnow() + timedelta(seconds=int(expires_in))
                    if expires_in else None
                )
                connection.updated_at = datetime.utcnow()
                connection.last_synced = datetime.utcnow()
                connection.is_active = True
                await db.commit()

                return {
                    "access_token": new_access_token,
                    "refresh_token": new_refresh_token,
                    "expires_in": expires_in
                }

        except Exception as e:
            print(f" Token refresh exception: {e}")
            return None

    @classmethod
    async def _get_platform_user_info(
        cls, platform: str, access_token: str, user_info_url: str, client: httpx.AsyncClient
    ) -> Optional[Dict]:
        """Get user info from platform API"""
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            params = {}

            # CORRECTED: TikTok requires specific fields in params
            if platform == "tiktok":
                params = {"fields": "open_id,union_id,avatar_url,display_name"}

            response = await client.get(user_info_url, headers=headers, params=params)

            if response.status_code != 200:
                print(
                    f" User info error: {response.status_code} - {response.text}")
                return None

            data = response.json()

            if platform == "twitter":
                user_data = data.get("data", {})
                return {
                    "user_id": user_data.get("id"),
                    "username": user_data.get("username"),
                    "name": user_data.get("name")
                }
            elif platform in ["facebook", "instagram"]:
                return {
                    "user_id": data.get("id"),
                    "username": data.get("name"),
                    "name": data.get("name"),
                    "email": data.get("email")
                }
            elif platform in ["google", "youtube"]:
                return {
                    "user_id": data.get("sub"),
                    "username": data.get("email"),
                    "name": data.get("name"),
                    "email": data.get("email")
                }
            elif platform == "linkedin":
                return {
                    "user_id": data.get("sub"),
                    "username": data.get("email"),
                    "name": data.get("name"),
                    "email": data.get("email")
                }
            # CORRECTED: TikTok parsing logic
            elif platform == "tiktok":
                user_data = data.get("data", {}).get("user", {})
                return {
                    "user_id": user_data.get("open_id"),
                    "username": user_data.get("display_name"),
                    "name": user_data.get("display_name"),
                    "email": None
                }

        except Exception as e:
            print(f" Error getting user info: {e}")
            return None

        return None

    @classmethod
    async def _save_connection(
        cls, db: AsyncSession, user_id: int, platform: str, access_token: str,
        refresh_token: Optional[str], expires_in: Optional[int], platform_user_id: Optional[str],
        platform_username: Optional[str] = None, platform_name: Optional[str] = None,
        platform_email: Optional[str] = None, platform_protocol: Optional[str] = None,
        oauth_token_secret: Optional[str] = None
    ) -> models.SocialConnection:

        if not platform_user_id:
            raise ValueError(f"platform_user_id required for {platform}")

        platform_username = platform_username or platform_name or platform_user_id

        result = await db.execute(
            select(models.SocialConnection).where(
                models.SocialConnection.user_id == user_id,
                models.SocialConnection.platform == platform.upper(),
                models.SocialConnection.platform_user_id == platform_user_id
            )
        )
        connection = result.scalar_one_or_none()

        expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in)
                                                   ) if expires_in else None

        if connection:
            print(f"Updating existing connection ID: {connection.id}")
            connection.platform_username = platform_username
            connection.protocol = platform_protocol
            connection.username = platform_name or platform_username
            connection.access_token = access_token
            connection.refresh_token = refresh_token
            connection.token_expires_at = expires_at
            connection.is_active = True
            connection.updated_at = datetime.utcnow()
        else:
            print(f"Creating new connection for user {user_id}")
            connection = models.SocialConnection(
                user_id=user_id,
                platform=platform.upper(),
                protocol=platform_protocol,
                platform_user_id=platform_user_id,
                platform_username=platform_username,
                username=platform_name or platform_username,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expires_at=expires_at,
                is_active=True,
                updated_at=datetime.utcnow()
            )
            db.add(connection)

        # AUTO-SELECT FACEBOOK PAGE Logic (Existing code kept same)
        if platform.lower() == "facebook":
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    pages_response = await client.get(
                        "https://graph.facebook.com/v20.0/me/accounts",
                        params={
                            "access_token": access_token,
                            "fields": "id,name,category,access_token,picture"
                        }
                    )

                    if pages_response.status_code == 200:
                        pages_data = pages_response.json()
                        pages = pages_data.get("data", [])

                        if pages:
                            first_page = pages[0]
                            connection.facebook_page_id = first_page["id"]
                            connection.facebook_page_name = first_page["name"]
                            connection.facebook_page_access_token = first_page["access_token"]
                            connection.facebook_page_category = first_page.get(
                                "category", "Unknown")

                            picture_data = first_page.get("picture", {})
                            if isinstance(picture_data, dict):
                                picture_url = picture_data.get(
                                    "data", {}).get("url")
                            else:
                                picture_url = None
                            connection.facebook_page_picture = picture_url
            except Exception as e:
                print(f" Error fetching Facebook pages: {e}")

        await db.commit()
        await db.refresh(connection)

        return connection
```
---

** Posting service for different platforms **
```

# app/services/social_service.py
"""
Main social media service orchestrator.
 FIXED: Proper handling of Twitter OAuth 1.0a tokens
"""

from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from ..models import SocialConnection
from .platforms import get_platform_service
from .oauth_service import OAuthService


class SocialService:
    """
    Main orchestrator for social media posting.
    Routes requests to platform-specific services.
    """

    
    #  NEW: Platforms that use OAuth 1.0a (no token refresh)
    OAUTH_1_0A_PLATFORMS = {"TWITTER"}
    
    @classmethod
    async def ensure_valid_token(
        cls,
        connection: SocialConnection,
        db: AsyncSession
    ) -> str:
        """
        Ensure token is valid, refresh if needed.
        
        ✅ FIXED: Aggressively skips refresh for Twitter/X (OAuth 1.0a)
        """
        # normalize: ensure string, uppercase, and remove ALL whitespace
        platform = str(connection.platform).upper().strip()
        
        # 🛑 HARD STOP: Explicitly check for Twitter to prevent ANY refresh attempt
        if "TWITTER" in platform or platform == "X":
            print(f" {platform}: OAuth 1.0a detected - Skipping token refresh.")
            return connection.access_token
            
        # Check standard OAuth 1.0a list
        if platform in cls.OAUTH_1_0A_PLATFORMS:
            print(f" {platform}: Using OAuth 1.0a token (no refresh needed)")
            return connection.access_token
        
        # Check if token is expired (for OAuth 2.0 platforms only)
        if connection.token_expires_at and connection.token_expires_at < datetime.utcnow():
            print(f" Token expired for {platform}, refreshing...")
            
            try:
                result = await OAuthService.refresh_access_token(connection, db)
                if not result:
                    # If refresh fails, try to return existing token as hail mary
                    print(f"] Refresh failed for {platform}, using existing token as fallback")
                    return connection.access_token
                
                return result["access_token"]
            except Exception as e:
                print(f"Token refresh failed for {platform}: {e}")
                # Don't crash the whole process, return the old token
                return connection.access_token
        
        return connection.access_token
    
    @classmethod
    async def publish_to_platform(
        cls,
        connection: SocialConnection,
        content: str,
        image_urls: Optional[List[str]] = None,
        video_urls: Optional[List[str]] = None,
        db: Optional[AsyncSession] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Publish content to a specific social platform.
        
        Args:
            connection: SocialConnection object
            content: Post content
            image_urls: List of image URLs
            video_urls: List of video URLs
            db: Database session (for token refresh)
            **kwargs: Platform-specific parameters
            
        Returns:
            Dict with keys: success, platform_post_id, url, error (if failed)
        """
        platform = connection.platform.upper()
        
        print(f"\n{'='*60}")
        print(f" Publishing to {platform}")
        print(f"{'='*60}")
        
        # Get platform service
        service_class = get_platform_service(platform)
        if not service_class:
            return {
                "success": False,
                "error": f"Unsupported platform: {platform}",
                "platform": platform
            }
        
        try:
            # Ensure valid token
            if db:
                access_token = await cls.ensure_valid_token(connection, db)
            else:
                access_token = connection.access_token
            
            # Pass connection for platforms that need it (Facebook)
            if platform == "FACEBOOK":
                kwargs["connection"] = connection
            
            # Call platform-specific service
            result = await service_class.post(
                access_token=access_token,
                content=content,
                image_urls=image_urls,
                video_urls=video_urls,
                **kwargs
            )
            
            # Add platform to result
            result["platform"] = platform
            
            if result["success"]:
                print(f" {platform}: Posted successfully!")
                print(f"   URL: {result.get('url', 'N/A')}")
            else:
                print(f" {platform}: Failed - {result.get('error', 'Unknown error')}")
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            print(f" {platform}: Exception - {error_msg}")
            import traceback
            traceback.print_exc()
            
            return {
                "success": False,
                "error": error_msg,
                "platform": platform
            }
    
    @classmethod
    async def publish_to_multiple_platforms(
        cls,
        connections: List[SocialConnection],
        content: str,
        image_urls: Optional[List[str]] = None,
        video_urls: Optional[List[str]] = None,
        db: Optional[AsyncSession] = None,
        platform_specific_content: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Publish to multiple platforms concurrently.
        
        Args:
            connections: List of social connections
            content: Default content for all platforms
            image_urls: Image URLs
            video_urls: Video URLs
            db: Database session
            platform_specific_content: Dict of platform -> custom content
            **kwargs: Additional parameters
            
        Returns:
            Summary dict with results for each platform
        """
        import asyncio
        
        print(f"\n{'='*60}")
        print(f" Multi-Platform Publishing")
        print(f"📝 Content: {content[:50]}...")
        print(f"🖼️ Images: {len(image_urls) if image_urls else 0}")
        print(f"🎬 Videos: {len(video_urls) if video_urls else 0}")
        print(f"{'='*60}\n")
        
        tasks = []
        for connection in connections:
            # Use platform-specific content if available
            platform_content = content
            if platform_specific_content and connection.platform.lower() in platform_specific_content:
                platform_content = platform_specific_content[connection.platform.lower()]
            
            # Create task
            task = cls.publish_to_platform(
                connection=connection,
                content=platform_content,
                image_urls=image_urls,
                video_urls=video_urls,
                db=db,
                **kwargs
            )
            tasks.append(task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful = []
        failed = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Task raised exception
                platform = connections[i].platform
                failed.append({
                    "platform": platform,
                    "error": str(result)
                })
            elif result.get("success"):
                successful.append(result)
            else:
                failed.append(result)
        
        print(f"\n{'='*60}")
        print(f"📊 PUBLISHING SUMMARY")
        print(f"{'='*60}")
        print(f" Successful: {len(successful)}/{len(connections)}")
        print(f" Failed: {len(failed)}/{len(connections)}")
        print(f"{'='*60}\n")
        
        return {
            "success": len(successful) > 0,
            "total_platforms": len(connections),
            "successful": len(successful),
            "failed": len(failed),
            "results": successful + failed
        }
    
    @classmethod
    async def validate_platform_connection(
        cls,
        connection: SocialConnection,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """
        Validate if a platform connection is still valid.
        
        Args:
            connection: Social connection to validate
            db: Database session for token refresh
            
        Returns:
            True if valid, False otherwise
        """
        platform = connection.platform.upper()
        service_class = cls.PLATFORM_SERVICES.get(platform)
        
        if not service_class:
            return False
        
        try:
            # Ensure valid token (handles OAuth 1.0a vs 2.0)
            if db:
                access_token = await cls.ensure_valid_token(connection, db)
            else:
                access_token = connection.access_token
            
            # Validate
            return await service_class.validate_token(access_token)
            
        except Exception as e:
            print(f" Validation error for {platform}: {e}")
            return False
    
    @classmethod
    def get_platform_limits(cls, platform: str) -> Dict[str, int]:
        """
        Get media limits for a specific platform.
        
        Args:
            platform: Platform name (TWITTER, FACEBOOK, etc.)
            
        Returns:
            Dict with max_images, max_videos, etc.
        """
        service_class = cls.PLATFORM_SERVICES.get(platform.upper())
        
        if not service_class:
            return {}
        
        return {
            "max_images": service_class.MAX_IMAGES,
            "max_videos": service_class.MAX_VIDEOS,
            "max_video_size_mb": service_class.MAX_VIDEO_SIZE_MB,
            "max_video_duration": service_class.MAX_VIDEO_DURATION_SECONDS
        }
    
    @classmethod
    def get_all_platform_limits(cls) -> Dict[str, Dict[str, int]]:
        """Get limits for all platforms"""
        return {
            platform: cls.get_platform_limits(platform)
            for platform in cls.PLATFORM_SERVICES.keys()
        }
        
        
```
---
```
service for X
# app/services/platforms/twitter.py
"""
Twitter/X platform service using OAuth 1.0a with API V1.1 for media uploads.
 FIXED: Proper chunked upload for videos (INIT → APPEND → FINALIZE → STATUS)
 Uses v1.1 endpoint for media (reliable until March 31, 2025)
 Posts tweets using v2 API
"""

import httpx
from typing import Dict, List, Any, Optional
from requests_oauthlib import OAuth1Session
from io import BytesIO
import mimetypes
import asyncio
import time
import os
from .base_platform import BasePlatformService


class TwitterService(BasePlatformService):
    """Twitter/X platform service implementation with chunked video upload"""
    
    PLATFORM_NAME = "TWITTER"
    MAX_IMAGES = 4
    MAX_VIDEOS = 1
    MAX_VIDEO_SIZE_MB = 512
    MAX_VIDEO_DURATION_SECONDS = 140
    
    # API endpoints
    API_BASE = "https://api.twitter.com/2"
    UPLOAD_BASE = "https://upload.twitter.com/1.1"
    
    # Chunked upload settings
    CHUNK_SIZE = 5 * 1024 * 1024  # 5MB chunks (Twitter's max per chunk)
    MAX_UPLOAD_RETRIES = 3
    
    @classmethod
    async def post(
        cls,
        access_token: str,
        content: str,
        image_urls: Optional[List[str]] = None,
        video_urls: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Post to Twitter using OAuth 1.0a.
        
        Args:
            access_token: Format "oauth_token:oauth_token_secret"
            content: Tweet text (max 280 chars)
            image_urls: List of image URLs (max 4)
            video_urls: List of video URLs (max 1)
        
        Returns:
            Dict with success status, platform_post_id, url, and error (if failed)
        """
        print(f"\n Twitter: Starting tweet creation")
        
        #  Validate token format
        if ':' not in access_token:
            error_msg = "Invalid token format. Expected 'oauth_token:oauth_secret'"
            print(f" Twitter: {error_msg}")
            return cls.format_error_response(error_msg)
        
        try:
            oauth_token, oauth_token_secret = access_token.split(':', 1)
        except Exception as e:
            return cls.format_error_response(f"Token parsing error: {e}")
        
        # Validate media
        error = cls.validate_media_count(image_urls, video_urls)
        if error:
            return cls.format_error_response(error)
        
        # Validate content length
        if len(content) > 280:
            return cls.format_error_response(
                f"Tweet too long: {len(content)} chars (max 280)"
            )
        
        try:
            from app.config import settings
            
            #  Create OAuth1 session
            print(f" Twitter: Initializing OAuth 1.0a session")
            twitter = OAuth1Session(
                client_key=settings.TWITTER_API_KEY,
                client_secret=settings.TWITTER_API_SECRET,
                resource_owner_key=oauth_token,
                resource_owner_secret=oauth_token_secret
            )
            
            #  STEP 1: Upload media if present
            media_ids = []
            
            # Upload images (simple upload)
            if image_urls:
                print(f" Twitter: Uploading {len(image_urls)} images")
                for idx, image_url in enumerate(image_urls[:cls.MAX_IMAGES], 1):
                    media_id = await cls._upload_image(twitter, image_url, idx)
                    if media_id:
                        media_ids.append(media_id)
                        print(f"    Image {idx} uploaded: {media_id}")
                    else:
                        print(f"    Image {idx} upload failed, continuing...")
            
            # Upload videos (chunked upload - THE FIX)
            if video_urls:
                print(f" Twitter: Uploading video using CHUNKED UPLOAD")
                video_id = await cls._upload_video_chunked(twitter, video_urls[0])
                if video_id:
                    media_ids.append(video_id)
                    print(f"    Video uploaded: {video_id}")
                else:
                    print(f"  Video upload failed")
                    return cls.format_error_response(
                        "Video upload failed. Check logs for details."
                    )
            
            #  STEP 2: Create tweet using v2 API
            tweet_data = {"text": content}
            
            if media_ids:
                tweet_data["media"] = {"media_ids": media_ids}
                print(f" Twitter: Posting tweet with {len(media_ids)} media attachments")
            else:
                print(f" Twitter: Posting text-only tweet")
            
            # Post tweet
            response = twitter.post(
                f"{cls.API_BASE}/tweets",
                json=tweet_data,
                timeout=30
            )
            
            #  Handle response
            if response.status_code == 201:
                data = response.json()
                tweet_id = data["data"]["id"]
                
                print(f" Twitter: Tweet posted successfully!")
                print(f"   Tweet ID: {tweet_id}")
                
                return cls.format_success_response(
                    tweet_id,
                    f"https://twitter.com/user/status/{tweet_id}"
                )
            
            elif response.status_code == 401:
                error_data = response.json() if response.text else {}
                error_msg = cls._parse_error_message(error_data)
                print(f" Twitter: 401 Unauthorized - {error_msg}")
                
                return cls.format_error_response(
                    f"Authentication failed: {error_msg}. "
                    "Please try reconnecting your Twitter account."
                )
            
            elif response.status_code == 403:
                error_data = response.json() if response.text else {}
                error_msg = cls._parse_error_message(error_data)
                print(f" Twitter: 403 Forbidden - {error_msg}")
                
                if "Read and write" in error_msg or "permission" in error_msg.lower():
                    return cls.format_error_response(
                        "Twitter app lacks 'Read and Write' permissions. "
                        "Please check your Twitter Developer Portal settings."
                    )
                
                return cls.format_error_response(f"Forbidden: {error_msg}")
            
            elif response.status_code == 429:
                print(f" Twitter: 429 Rate Limit Exceeded")
                return cls.format_error_response(
                    "Twitter API rate limit exceeded. Please wait a few minutes."
                )
            
            else:
                error_data = response.json() if response.text else {}
                error_msg = cls._parse_error_message(error_data)
                print(f" Twitter: Error {response.status_code} - {error_msg}")
                
                return cls.format_error_response(
                    f"Tweet failed ({response.status_code}): {error_msg}"
                )
                
        except Exception as e:
            print(f" Twitter post error: {e}")
            import traceback
            traceback.print_exc()
            return cls.format_error_response(f"Unexpected error: {str(e)}")
    
    @classmethod
    async def _upload_image(
        cls,
        twitter_session: OAuth1Session,
        image_url: str,
        index: int = 1
    ) -> Optional[str]:
        """
        Upload image using simple upload endpoint.
        
        Args:
            twitter_session: OAuth1Session instance
            image_url: URL of the image to upload
            index: Image number (for logging)
        
        Returns:
            media_id_string if successful, None otherwise
        """
        try:
            print(f"   📥 Downloading image {index}...")
            media_data = await cls.download_media(image_url, timeout=60)
            if not media_data:
                print(f"  Failed to download image")
                return None
            
            media_size_mb = len(media_data) / (1024 * 1024)
            print(f"   📦 Image size: {media_size_mb:.2f}MB")
            
            # Determine content type
            content_type = mimetypes.guess_type(image_url)[0] or "image/jpeg"
            
            # Upload using simple endpoint (works for images)
            files = {
                "media": (
                    f"image.{content_type.split('/')[-1]}", 
                    BytesIO(media_data), 
                    content_type
                )
            }
            
            response = twitter_session.post(
                f"{cls.UPLOAD_BASE}/media/upload.json",
                files=files,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("media_id_string")
            else:
                print(f"  Image upload failed: {response.status_code}")
                print(f"  Response: {response.text[:200]}")
                return None
                
        except Exception as e:
            print(f"  Image upload error: {e}")
            return None
    
    @classmethod
    async def _upload_video_chunked(
        cls,
        twitter_session: OAuth1Session,
        video_url: str
    ) -> Optional[str]:
        """
         MAIN FIX: Upload video using proper chunked upload process.
        
        This is the correct way to upload videos to Twitter:
        1. INIT - Initialize upload with file size and type
        2. APPEND - Upload file in chunks (max 5MB per chunk)
        3. FINALIZE - Complete the upload
        4. STATUS - Wait for processing (if needed)
        
        Args:
            twitter_session: OAuth1Session instance
            video_url: URL of the video to upload
        
        Returns:
            media_id_string if successful, None otherwise
        """
        try:
            # Download video
            print(f"   📥 Downloading video...")
            video_data = await cls.download_media(video_url, timeout=180)
            if not video_data:
                print(f"  Failed to download video")
                return None
            
            video_size = len(video_data)
            video_size_mb = video_size / (1024 * 1024)
            print(f"   📦 Video size: {video_size_mb:.2f}MB ({video_size} bytes)")
            
            # Validate size
            if video_size_mb > cls.MAX_VIDEO_SIZE_MB:
                print(f"  Video too large: {video_size_mb:.2f}MB (max {cls.MAX_VIDEO_SIZE_MB}MB)")
                return None
            
            # Determine media type
            media_type = mimetypes.guess_type(video_url)[0] or "video/mp4"
            print(f"   🎬 Media type: {media_type}")
            
            # ========================================================
            # STEP 1: INIT - Initialize chunked upload
            # ========================================================
            print(f"    INIT: Initializing chunked upload...")
            
            init_data = {
                "command": "INIT",
                "total_bytes": str(video_size),
                "media_type": media_type,
                "media_category": "tweet_video"  # Required for videos
            }
            
            init_response = twitter_session.post(
                f"{cls.UPLOAD_BASE}/media/upload.json",
                data=init_data,
                timeout=30
            )
            
            if init_response.status_code != 200 and init_response.status_code != 201:
                print(f"  INIT failed: {init_response.status_code}")
                print(f"  Response: {init_response.text}")
                return None
            
            init_result = init_response.json()
            media_id = init_result.get("media_id_string")
            
            if not media_id:
                print(f"  No media_id received from INIT")
                return None
            
            print(f"    INIT successful. Media ID: {media_id}")
            
            # ========================================================
            # STEP 2: APPEND - Upload video in chunks
            # ========================================================
            print(f"    APPEND: Uploading video in chunks...")
            
            segment_index = 0
            bytes_sent = 0
            
            while bytes_sent < video_size:
                # Get chunk
                chunk_start = bytes_sent
                chunk_end = min(bytes_sent + cls.CHUNK_SIZE, video_size)
                chunk = video_data[chunk_start:chunk_end]
                chunk_size = len(chunk)
                
                print(f"   📦 Uploading chunk {segment_index + 1} "
                      f"({bytes_sent}-{chunk_end}/{video_size} bytes)")
                
                # Upload chunk
                append_data = {
                    "command": "APPEND",
                    "media_id": media_id,
                    "segment_index": str(segment_index)
                }
                
                append_files = {
                    "media": BytesIO(chunk)
                }
                
                append_response = twitter_session.post(
                    f"{cls.UPLOAD_BASE}/media/upload.json",
                    data=append_data,
                    files=append_files,
                    timeout=120
                )
                
                # APPEND returns 204 No Content on success
                if append_response.status_code not in [200, 201, 204]:
                    print(f"  APPEND failed at segment {segment_index}: {append_response.status_code}")
                    print(f"  Response: {append_response.text}")
                    return None
                
                print(f"    Chunk {segment_index + 1} uploaded successfully")
                
                bytes_sent += chunk_size
                segment_index += 1
            
            print(f"    All {segment_index} chunks uploaded")
            
            # ========================================================
            # STEP 3: FINALIZE - Complete the upload
            # ========================================================
            print(f"    FINALIZE: Completing upload...")
            
            finalize_data = {
                "command": "FINALIZE",
                "media_id": media_id
            }
            
            finalize_response = twitter_session.post(
                f"{cls.UPLOAD_BASE}/media/upload.json",
                data=finalize_data,
                timeout=60
            )
            
            if finalize_response.status_code != 200 and finalize_response.status_code != 201:
                print(f"  FINALIZE failed: {finalize_response.status_code}")
                print(f"  Response: {finalize_response.text}")
                return None
            
            finalize_result = finalize_response.json()
            print(f"    FINALIZE successful")
            
            # ========================================================
            # STEP 4: STATUS - Wait for processing (if needed)
            # ========================================================
            processing_info = finalize_result.get("processing_info")
            
            if processing_info:
                state = processing_info.get("state")
                print(f"   Video processing: {state}")
                
                # Wait for processing to complete
                max_wait_time = 300  # 5 minutes
                start_time = time.time()
                check_after_secs = processing_info.get("check_after_secs", 5)
                
                while state in ["pending", "in_progress"]:
                    # Check if we've waited too long
                    if time.time() - start_time > max_wait_time:
                        print(f"  Video processing timeout after {max_wait_time}s")
                        return None
                    
                    # Wait before checking status
                    print(f"   Waiting {check_after_secs}s before status check...")
                    await asyncio.sleep(check_after_secs)
                    
                    # Check status
                    status_data = {
                        "command": "STATUS",
                        "media_id": media_id
                    }
                    
                    status_response = twitter_session.get(
                        f"{cls.UPLOAD_BASE}/media/upload.json",
                        params=status_data,
                        timeout=30
                    )
                    
                    if status_response.status_code != 200:
                        print(f"  STATUS check failed: {status_response.status_code}")
                        return None
                    
                    status_result = status_response.json()
                    processing_info = status_result.get("processing_info", {})
                    state = processing_info.get("state")
                    check_after_secs = processing_info.get("check_after_secs", 5)
                    
                    print(f"   Processing state: {state}")
                
                # Check final state
                if state == "succeeded":
                    print(f"    Video processing completed successfully")
                elif state == "failed":
                    error = processing_info.get("error", {})
                    error_msg = error.get("message", "Unknown error")
                    print(f"  Video processing failed: {error_msg}")
                    return None
            
            print(f"   🎉 Video upload complete! Media ID: {media_id}")
            return media_id
            
        except Exception as e:
            print(f"  Video upload error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @classmethod
    def _parse_error_message(cls, error_data: Dict) -> str:
        """Parse Twitter API error response"""
        if not error_data:
            return "Unknown error"
        
        # V2 API error format
        if "detail" in error_data:
            return error_data["detail"]
        
        if "title" in error_data:
            title = error_data["title"]
            detail = error_data.get("detail", "")
            return f"{title}: {detail}" if detail else title
        
        # V1.1 API error format
        if "errors" in error_data:
            errors = error_data["errors"]
            if isinstance(errors, list) and errors:
                first_error = errors[0]
                return first_error.get("message", str(first_error))
        
        # Simple error format
        if "error" in error_data:
            return error_data["error"]
        
        return str(error_data)
    
    @classmethod
    async def validate_token(cls, access_token: str) -> bool:
        """
        Validate Twitter OAuth tokens.
        
        Args:
            access_token: Format "oauth_token:oauth_token_secret"
        
        Returns:
            True if valid, False otherwise
        """
        try:
            if ':' not in access_token:
                print(f" Twitter: Invalid token format")
                return False
            
            from app.config import settings
            oauth_token, oauth_token_secret = access_token.split(':', 1)
            
            twitter = OAuth1Session(
                client_key=settings.TWITTER_API_KEY,
                client_secret=settings.TWITTER_API_SECRET,
                resource_owner_key=oauth_token,
                resource_owner_secret=oauth_token_secret
            )
            
            # Use v2 /users/me endpoint (lightweight)
            response = twitter.get(
                f"{cls.API_BASE}/users/me",
                timeout=10
            )
            
            is_valid = response.status_code == 200
            
            if not is_valid:
                print(f" Twitter: Token validation failed - {response.status_code}")
                print(f"   Response: {response.text[:200]}")
            
            return is_valid
            
        except Exception as e:
            print(f" Twitter: Token validation error - {e}")
            return False
    
   ```

----

```
Service for linkedin 
# app/services/platforms/linkedin.py
"""
LinkedIn platform service with PROPER video upload support.
âœ… FIXED: Videos now check processing status before posting
"""

import httpx
import asyncio
from typing import Dict, List, Any, Optional
from .base_platform import BasePlatformService


class LinkedInService(BasePlatformService):
    """LinkedIn platform service implementation"""
    
    PLATFORM_NAME = "LINKEDIN"
    MAX_IMAGES = 9
    MAX_VIDEOS = 1
    MAX_VIDEO_SIZE_MB = 5120  # 5GB
    MAX_VIDEO_DURATION_SECONDS = 600  # 10 minutes
    
    API_BASE = "https://api.linkedin.com/v2"
    
    # âœ… VIDEO PROCESSING CONFIGURATION
    MAX_PROCESSING_WAIT_TIME = 300  # 5 minutes max wait
    STATUS_CHECK_INTERVAL = 5  # Check every 5 seconds
    
    @classmethod
    async def post(
        cls,
        access_token: str,
        content: str,
        image_urls: Optional[List[str]] = None,
        video_urls: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Post content to LinkedIn with images or video.
        
        âœ… FIXED: Now properly waits for video processing to complete
        """
        print(f"ðŸ'¼ LinkedIn: Starting post creation")
        
        # Validate media counts
        error = cls.validate_media_count(image_urls, video_urls)
        if error:
            return cls.format_error_response(error)
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                # Step 1: Get user profile (author URN)
                author_urn = await cls._get_author_urn(client, access_token)
                if not author_urn:
                    return cls.format_error_response("Failed to get user profile")
                
                print(f"ðŸ'¼ LinkedIn: Author URN: {author_urn}")
                
                # Step 2: Handle video upload if present
                if video_urls and len(video_urls) > 0:
                    return await cls._post_with_video(
                        client, access_token, author_urn, content, video_urls[0]
                    )
                
                # Step 3: Handle image upload if present
                if image_urls and len(image_urls) > 0:
                    return await cls._post_with_images(
                        client, access_token, author_urn, content, image_urls
                    )
                
                # Step 4: Text-only post
                return await cls._post_text_only(
                    client, access_token, author_urn, content
                )
                
        except Exception as e:
            print(f"âŒ LinkedIn post error: {e}")
            import traceback
            traceback.print_exc()
            return cls.format_error_response(str(e))
    
    @classmethod
    async def _get_author_urn(cls, client: httpx.AsyncClient, access_token: str) -> Optional[str]:
        """Get LinkedIn user profile URN"""
        try:
            response = await client.get(
                f"{cls.API_BASE}/userinfo",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "X-Restli-Protocol-Version": "2.0.0"
                }
            )
            
            if response.status_code == 200:
                profile = response.json()
                return f"urn:li:person:{profile['sub']}"
            
            print(f"âŒ Failed to get profile: {response.status_code} - {response.text}")
            return None
            
        except Exception as e:
            print(f"âŒ Error getting author URN: {e}")
            return None
    
    @classmethod
    async def _check_asset_status(
        cls,
        client: httpx.AsyncClient,
        access_token: str,
        asset_urn: str
    ) -> Optional[str]:
        """
        âœ… NEW: Check if video asset has finished processing
        
        Returns:
            - "AVAILABLE" if ready to use
            - "PROCESSING" if still processing
            - "PROCESSING_FAILED" if upload failed
            - None if can't determine status
        """
        try:
            # Extract asset ID from URN (format: urn:li:digitalmediaAsset:ASSET_ID)
            asset_id = asset_urn.split(":")[-1]
            
            response = await client.get(
                f"{cls.API_BASE}/assets/{asset_id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "X-Restli-Protocol-Version": "2.0.0"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check recipe status
                recipes = data.get("recipes", [])
                if recipes:
                    recipe_status = recipes[0].get("status", "UNKNOWN")
                    print(f"ðŸ'¼ LinkedIn: Asset status = {recipe_status}")
                    return recipe_status
                
                # Fallback to overall status
                return data.get("status", "UNKNOWN")
            
            print(f"âš ï¸ LinkedIn: Could not check asset status: {response.status_code}")
            return None
            
        except Exception as e:
            print(f"âŒ Error checking asset status: {e}")
            return None
    
    @classmethod
    async def _wait_for_video_processing(
        cls,
        client: httpx.AsyncClient,
        access_token: str,
        asset_urn: str
    ) -> bool:
        """
        âœ… NEW: Wait for LinkedIn to finish processing the video
        
        This is THE CRITICAL FIX - LinkedIn videos are processed asynchronously!
        According to LinkedIn docs: "If the post is created before confirming 
        upload success and the video upload fails to process, the post won't 
        be visible to members."
        
        Returns:
            True if video is ready, False if failed or timeout
        """
        print(f"ðŸ'¼ LinkedIn: Waiting for video processing to complete...")
        print(f"   (This can take 1-5 minutes depending on video size)")
        
        start_time = asyncio.get_event_loop().time()
        elapsed = 0
        
        while elapsed < cls.MAX_PROCESSING_WAIT_TIME:
            # Check status
            status = await cls._check_asset_status(client, access_token, asset_urn)
            
            if status == "AVAILABLE":
                print(f"✅ LinkedIn: Video processing complete! (took {elapsed:.1f}s)")
                return True
            
            elif status == "PROCESSING_FAILED":
                print(f"âŒ LinkedIn: Video processing FAILED")
                return False
            
            elif status == "PROCESSING":
                # Still processing, wait and check again
                print(f"   âłï¸ Still processing... ({elapsed:.1f}s elapsed)")
                await asyncio.sleep(cls.STATUS_CHECK_INTERVAL)
                elapsed = asyncio.get_event_loop().time() - start_time
                continue
            
            else:
                # Unknown status, wait a bit and try again
                print(f"   âš ï¸ Unknown status: {status}, retrying...")
                await asyncio.sleep(cls.STATUS_CHECK_INTERVAL)
                elapsed = asyncio.get_event_loop().time() - start_time
        
        # Timeout
        print(f"⏰ LinkedIn: Video processing timeout after {cls.MAX_PROCESSING_WAIT_TIME}s")
        return False
    
    @classmethod
    async def _post_with_video(
        cls,
        client: httpx.AsyncClient,
        access_token: str,
        author_urn: str,
        content: str,
        video_url: str
    ) -> Dict[str, Any]:
        """
        Post with video to LinkedIn.
        âœ… FIXED: Now properly waits for video processing
        """
        print(f"ðŸ'¼ LinkedIn: Uploading video from {video_url}")
        
        try:
            # Download video
            video_data = await cls.download_media(video_url, timeout=120)
            if not video_data:
                return cls.format_error_response("Failed to download video")
            
            video_size = len(video_data)
            video_size_mb = video_size / (1024*1024)
            print(f"ðŸ'¼ LinkedIn: Video size: {video_size_mb:.2f} MB")
            
            # Check video size limit
            if video_size_mb > cls.MAX_VIDEO_SIZE_MB:
                return cls.format_error_response(
                    f"Video too large: {video_size_mb:.2f}MB (max: {cls.MAX_VIDEO_SIZE_MB}MB)"
                )
            
            # Step 1: Register video upload
            print(f"ðŸ'¼ LinkedIn: Registering video upload...")
            register_response = await client.post(
                f"{cls.API_BASE}/assets?action=registerUpload",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "X-Restli-Protocol-Version": "2.0.0"
                },
                json={
                    "registerUploadRequest": {
                        "recipes": ["urn:li:digitalmediaRecipe:feedshare-video"],
                        "owner": author_urn,
                        "serviceRelationships": [{
                            "relationshipType": "OWNER",
                            "identifier": "urn:li:userGeneratedContent"
                        }]
                    }
                }
            )
            
            if register_response.status_code not in [200, 201]:
                return cls.format_error_response(
                    f"Video registration failed: {register_response.text}"
                )
            
            register_data = register_response.json()
            upload_url = register_data["value"]["uploadMechanism"][
                "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
            video_urn = register_data["value"]["asset"]
            
            print(f"ðŸ'¼ LinkedIn: Video URN: {video_urn}")
            print(f"ðŸ'¼ LinkedIn: Upload URL obtained")
            
            # Step 2: Upload video data
            print(f"ðŸ'¼ LinkedIn: Uploading video data ({video_size_mb:.2f}MB)...")
            upload_response = await client.put(
                upload_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/octet-stream"
                },
                content=video_data
            )
            
            if upload_response.status_code not in [200, 201]:
                return cls.format_error_response(
                    f"Video upload failed: {upload_response.text}"
                )
            
            print(f"✅ LinkedIn: Video uploaded successfully")
            
            # âœ… CRITICAL FIX: Wait for LinkedIn to process the video
            # This is what was missing! LinkedIn processes videos asynchronously
            # and if we create the post before processing completes, 
            # the video won't appear in the post!
            video_ready = await cls._wait_for_video_processing(
                client, access_token, video_urn
            )
            
            if not video_ready:
                return cls.format_error_response(
                    "Video upload succeeded but processing failed or timed out. "
                    "LinkedIn needs time to process videos. Try again or use a smaller video."
                )
            
            # Step 3: Create post with video (now that it's READY)
            post_data = {
                "author": author_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": content},
                        "shareMediaCategory": "VIDEO",
                        "media": [{
                            "status": "READY",  # âœ… Now we KNOW it's ready!
                            "description": {"text": content[:200]},
                            "media": video_urn,
                            "title": {"text": "Video"}
                        }]
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
            
            print(f"ðŸ'¼ LinkedIn: Creating UGC post with processed video...")
            post_response = await client.post(
                f"{cls.API_BASE}/ugcPosts",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "X-Restli-Protocol-Version": "2.0.0"
                },
                json=post_data
            )
            
            if post_response.status_code in [200, 201]:
                result = post_response.json()
                post_id = result.get("id", "")
                print(f"✅ LinkedIn: Video post created successfully!")
                print(f"   Post ID: {post_id}")
                return cls.format_success_response(
                    post_id,
                    f"https://www.linkedin.com/feed/update/{post_id}/"
                )
            else:
                error_text = post_response.text
                print(f"âŒ LinkedIn: Post creation failed: {error_text}")
                return cls.format_error_response(f"Post creation failed: {error_text}")
            
        except Exception as e:
            print(f"âŒ LinkedIn video upload error: {e}")
            import traceback
            traceback.print_exc()
            return cls.format_error_response(str(e))
    
    @classmethod
    async def _post_with_images(
        cls,
        client: httpx.AsyncClient,
        access_token: str,
        author_urn: str,
        content: str,
        image_urls: List[str]
    ) -> Dict[str, Any]:
        """Post with images to LinkedIn"""
        print(f"ðŸ'¼ LinkedIn: Uploading {len(image_urls)} images")
        
        uploaded_assets = []
        
        for idx, image_url in enumerate(image_urls[:cls.MAX_IMAGES], 1):
            try:
                print(f"ðŸ'¼ LinkedIn: Processing image {idx}/{min(len(image_urls), cls.MAX_IMAGES)}")
                
                # Register upload
                register_response = await client.post(
                    f"{cls.API_BASE}/assets?action=registerUpload",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                        "X-Restli-Protocol-Version": "2.0.0"
                    },
                    json={
                        "registerUploadRequest": {
                            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                            "owner": author_urn,
                            "serviceRelationships": [{
                                "relationshipType": "OWNER",
                                "identifier": "urn:li:userGeneratedContent"
                            }]
                        }
                    }
                )
                
                if register_response.status_code not in [200, 201]:
                    print(f"âŒ Failed to register image {idx}: {register_response.text}")
                    continue
                
                register_data = register_response.json()
                upload_url = register_data["value"]["uploadMechanism"][
                    "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
                asset = register_data["value"]["asset"]
                
                # Download image
                image_data = await cls.download_media(image_url)
                if not image_data:
                    print(f"âŒ Failed to download image {idx}")
                    continue
                
                # Upload image
                upload_response = await client.post(
                    upload_url,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "image/jpeg"
                    },
                    content=image_data
                )
                
                if upload_response.status_code in [200, 201]:
                    uploaded_assets.append(asset)
                    print(f"✅ Image {idx} uploaded: {asset}")
                else:
                    print(f"âŒ Failed to upload image {idx}: {upload_response.status_code}")
                
            except Exception as e:
                print(f"âŒ Failed to upload image {idx}: {e}")
                continue
        
        if not uploaded_assets:
            return cls.format_error_response("Failed to upload any images")
        
        print(f"ðŸ'¼ LinkedIn: Successfully uploaded {len(uploaded_assets)}/{len(image_urls)} images")
        
        # Create post with images
        post_data = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": content},
                    "shareMediaCategory": "IMAGE",
                    "media": [
                        {
                            "status": "READY",
                            "description": {"text": content[:200]},
                            "media": asset,
                            "title": {"text": f"Image {i+1}"}
                        }
                        for i, asset in enumerate(uploaded_assets)
                    ]
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
        
        response = await client.post(
            f"{cls.API_BASE}/ugcPosts",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0"
            },
            json=post_data
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            post_id = result.get("id", "")
            print(f"✅ LinkedIn: Image post created successfully!")
            return cls.format_success_response(
                post_id,
                f"https://www.linkedin.com/feed/update/{post_id}/"
            )
        else:
            return cls.format_error_response(f"Post failed: {response.text}")
    
    @classmethod
    async def _post_text_only(
        cls,
        client: httpx.AsyncClient,
        access_token: str,
        author_urn: str,
        content: str
    ) -> Dict[str, Any]:
        """Post text-only content to LinkedIn"""
        post_data = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": content},
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
        
        response = await client.post(
            f"{cls.API_BASE}/ugcPosts",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0"
            },
            json=post_data
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            post_id = result.get("id", "")
            return cls.format_success_response(
                post_id,
                f"https://www.linkedin.com/feed/update/{post_id}/"
            )
        else:
            return cls.format_error_response(f"Post failed: {response.text}")
    
    @classmethod
    async def validate_token(cls, access_token: str) -> bool:
        """Validate LinkedIn access token"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{cls.API_BASE}/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                return response.status_code == 200
        except:
            return False


    ```
---
```
Service for youtube

# app/services/platforms/youtube.py
"""
YouTube platform service for video uploads.
✅ REAL FIX: Uses Google's official API client library
"""

from typing import Dict, List, Any, Optional
from .base_platform import BasePlatformService
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload
from google.oauth2.credentials import Credentials
import sys


class YouTubeService(BasePlatformService):
    """YouTube platform service implementation"""
    
    PLATFORM_NAME = "YOUTUBE"
    MAX_IMAGES = 0
    MAX_VIDEOS = 1
    MAX_VIDEO_SIZE_MB = 128 * 1024
    MAX_VIDEO_DURATION_SECONDS = 3600
    
    @classmethod
    async def post(
        cls,
        access_token: str,
        content: str,
        image_urls: Optional[List[str]] = None,
        video_urls: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Upload video to YouTube using Google's official API client."""
        print(f"��� YouTube: Starting video upload")
        print(f"��� DEBUG: Using Google API Client version")
        
        if not video_urls or len(video_urls) == 0:
            return cls.format_error_response("YouTube requires a video")
        
        error = cls.validate_media_count(image_urls, video_urls)
        if error:
            return cls.format_error_response(error)
        
        try:
            video_url = video_urls[0]
            print(f"��� YouTube: Downloading video from {video_url}")
            video_data = await cls.download_media(video_url, timeout=300)
            
            if not video_data:
                return cls.format_error_response("Failed to download video")
            
            video_size_mb = len(video_data) / (1024 * 1024)
            print(f"��� YouTube: Video size: {video_size_mb:.2f} MB")
            
            title = content[:100] if len(content) <= 100 else content[:97] + "..."
            description = content
            privacy_status = kwargs.get("privacy_status", "public")
            category_id = kwargs.get("category_id", "22")
            tags = kwargs.get("tags", [])
            
            credentials = Credentials(token=access_token)
            youtube = build('youtube', 'v3', credentials=credentials)
            
            body = {
                "snippet": {
                    "title": title,
                    "description": description,
                    "categoryId": category_id
                },
                "status": {
                    "privacyStatus": privacy_status,
                    "selfDeclaredMadeForKids": False
                }
            }
            
            if tags:
                body["snippet"]["tags"] = tags
            
            print(f"��� YouTube: Uploading video ({video_size_mb:.2f}MB)...")
            
            media = MediaInMemoryUpload(
                video_data,
                mimetype="video/mp4",
                resumable=True,
                chunksize=1024*1024
            )
            
            request = youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media
            )
            
            response = None
            last_progress = 0
            
            while response is None:
                try:
                    status, response = request.next_chunk()
                    if status:
                        progress = int(status.progress() * 100)
                        if progress != last_progress:
                            print(f"   ��� Upload progress: {progress}%")
                            last_progress = progress
                except Exception as chunk_error:
                    print(f" Upload chunk error: {chunk_error}")
                    return cls.format_error_response(f"Upload failed: {str(chunk_error)}")
            
            video_id = response.get("id")
            
            if not video_id:
                return cls.format_error_response("No video ID in response")
            
            print(f"✅ YouTube: Video uploaded successfully!")
            print(f"   Video ID: {video_id}")
            
            return cls.format_success_response(
                video_id,
                f"https://www.youtube.com/watch?v={video_id}",
                video_id=video_id
            )
            
        except Exception as e:
            print(f" YouTube upload error: {e}")
            import traceback
            traceback.print_exc()
            
            error_msg = str(e)
            
            if "quotaExceeded" in error_msg or "Daily Limit Exceeded" in error_msg:
                return cls.format_error_response("YouTube API quota exceeded. Try again tomorrow.")
            elif "has not been used" in error_msg or "is disabled" in error_msg:
                return cls.format_error_response(
                    "YouTube Data API v3 is not enabled. Enable it in Google Cloud Console: "
                    "https://console.cloud.google.com/apis/library/youtube.googleapis.com"
                )
            else:
                return cls.format_error_response(f"Upload failed: {error_msg}")
    
    @classmethod
    async def validate_token(cls, access_token: str) -> bool:
        """Validate YouTube/Google access token"""
        try:
            credentials = Credentials(token=access_token)
            youtube = build('youtube', 'v3', credentials=credentials)
            request = youtube.channels().list(part="snippet", mine=True)
            response = request.execute()
            return "items" in response and len(response["items"]) > 0
        except:
            return False
    
    @classmethod
    async def get_channel_info(cls, access_token: str) -> Optional[Dict[str, Any]]:
        """Get YouTube channel information"""
        try:
            credentials = Credentials(token=access_token)
            youtube = build('youtube', 'v3', credentials=credentials)
            
            request = youtube.channels().list(
                part="snippet,statistics",
                mine=True
            )
            response = request.execute()
            
            if response.get("items"):
                channel = response["items"][0]
                return {
                    "id": channel["id"],
                    "title": channel["snippet"]["title"],
                    "subscriber_count": channel["statistics"].get("subscriberCount", 0),
                    "video_count": channel["statistics"].get("videoCount", 0),
                    "thumbnail": channel["snippet"]["thumbnails"]["default"]["url"]
                }
            return None
        except:
            return None
```

---
```
service for tiktok posting

# app/services/platforms/tiktok.py
"""
TikTok platform service for video uploads.
Uses TikTok Content Posting API v2 with OAuth 2.0.
"""

import httpx
import asyncio
from typing import Dict, List, Any, Optional
from .base_platform import BasePlatformService


class TikTokService(BasePlatformService):
    """TikTok platform service implementation"""
    
    PLATFORM_NAME = "TIKTOK"
    MAX_IMAGES = 0  # TikTok is video-only via API
    MAX_VIDEOS = 1
    MAX_VIDEO_SIZE_MB = 4096  # 4GB
    MAX_VIDEO_DURATION_SECONDS = 600  # 10 minutes (can be up to 60 min for some accounts)
    
    # TikTok API endpoints
    API_BASE = "https://open.tiktokapis.com"
    OAUTH_BASE = "https://www.tiktok.com/v2/auth"
    
    # Rate limits
    MAX_STATUS_CHECKS = 60  # Check status up to 60 times
    STATUS_CHECK_INTERVAL = 5  # Check every 5 seconds
    
    @classmethod
    async def post(
        cls,
        access_token: str,
        content: str,
        image_urls: Optional[List[str]] = None,
        video_urls: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Post video to TikTok using Content Posting API.
        
        Args:
            access_token: TikTok OAuth 2.0 access token
            content: Video title/caption
            video_urls: List with one video URL
            **kwargs: Additional params like privacy_level, disable_duet, etc.
        
        TikTok Posting Process:
        1. Initialize upload (get upload URL and publish_id)
        2. Upload video binary data to upload URL
        3. Poll status endpoint until processing complete
        """
        print(f"🎵 TikTok: Starting video upload")
        
        # Validate video requirement
        if not video_urls or len(video_urls) == 0:
            return cls.format_error_response("TikTok requires a video")
        
        # Validate media counts
        error = cls.validate_media_count(image_urls, video_urls)
        if error:
            return cls.format_error_response(error)
        
        try:
            # Download video
            video_url = video_urls[0]
            print(f"🎵 TikTok: Downloading video from {video_url}")
            video_data = await cls.download_media(video_url, timeout=300)
            
            if not video_data:
                return cls.format_error_response("Failed to download video")
            
            video_size = len(video_data)
            video_size_mb = video_size / (1024 * 1024)
            print(f"🎵 TikTok: Video size: {video_size_mb:.2f} MB")
            
            # Check size limit
            if video_size_mb > cls.MAX_VIDEO_SIZE_MB:
                return cls.format_error_response(
                    f"Video too large: {video_size_mb:.2f}MB (max: {cls.MAX_VIDEO_SIZE_MB}MB)"
                )
            
            # ✅ STEP 1: Initialize video upload
            publish_id, upload_url = await cls._initialize_video_upload(
                access_token, content, video_size, **kwargs
            )
            
            if not publish_id or not upload_url:
                return cls.format_error_response("Failed to initialize video upload")
            
            # ✅ STEP 2: Upload video data
            upload_success = await cls._upload_video_data(upload_url, video_data)
            
            if not upload_success:
                return cls.format_error_response("Failed to upload video data")
            
            # ✅ STEP 3: Wait for processing and check status
            result = await cls._wait_for_processing(access_token, publish_id)
            
            if result["success"]:
                print(f"✅ TikTok: Video posted successfully!")
                return result
            else:
                return result
            
        except Exception as e:
            print(f"❌ TikTok upload error: {e}")
            import traceback
            traceback.print_exc()
            return cls.format_error_response(str(e))
    
    @classmethod
    async def _initialize_video_upload(
        cls,
        access_token: str,
        content: str,
        video_size: int,
        **kwargs
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Initialize TikTok video upload (Step 1).
        
        Returns:
            Tuple of (publish_id, upload_url) or (None, None) on failure
        """
        print(f"🎵 TikTok: Initializing video upload...")
        
        # Extract parameters
        privacy_level = kwargs.get("privacy_level", "SELF_ONLY")  # SELF_ONLY, MUTUAL_FOLLOW_FRIENDS, FOLLOWER_OF_CREATOR, PUBLIC_TO_EVERYONE
        disable_duet = kwargs.get("disable_duet", False)
        disable_comment = kwargs.get("disable_comment", False)
        disable_stitch = kwargs.get("disable_stitch", False)
        
        # Build request body
        request_body = {
            "post_info": {
                "title": content[:150],  # Max 150 chars for title
                "privacy_level": privacy_level,
                "disable_duet": disable_duet,
                "disable_comment": disable_comment,
                "disable_stitch": disable_stitch
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_size,
                "chunk_size": video_size,  # Single chunk upload
                "total_chunk_count": 1
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{cls.API_BASE}/v2/post/publish/video/init/",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json; charset=UTF-8"
                    },
                    json=request_body
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check for error in response
                    if data.get("error", {}).get("code") != "ok":
                        error_msg = data.get("error", {}).get("message", "Unknown error")
                        print(f"❌ TikTok init failed: {error_msg}")
                        return None, None
                    
                    publish_id = data.get("data", {}).get("publish_id")
                    upload_url = data.get("data", {}).get("upload_url")
                    
                    print(f"✅ TikTok: Initialized - publish_id: {publish_id}")
                    return publish_id, upload_url
                else:
                    print(f"❌ TikTok init failed: {response.status_code}")
                    print(f"   Response: {response.text}")
                    return None, None
                    
        except Exception as e:
            print(f"❌ TikTok init error: {e}")
            return None, None
    
    @classmethod
    async def _upload_video_data(
        cls,
        upload_url: str,
        video_data: bytes
    ) -> bool:
        """
        Upload video binary data to TikTok (Step 2).
        
        Returns:
            True if successful, False otherwise
        """
        print(f"🎵 TikTok: Uploading video data...")
        
        video_size = len(video_data)
        
        try:
            async with httpx.AsyncClient(timeout=600.0) as client:
                response = await client.put(
                    upload_url,
                    headers={
                        "Content-Range": f"bytes 0-{video_size-1}/{video_size}",
                        "Content-Length": str(video_size),
                        "Content-Type": "video/mp4"
                    },
                    content=video_data
                )
                
                if response.status_code in [200, 201, 204]:
                    print(f"✅ TikTok: Video data uploaded successfully")
                    return True
                else:
                    print(f"❌ TikTok upload failed: {response.status_code}")
                    print(f"   Response: {response.text}")
                    return False
                    
        except Exception as e:
            print(f"❌ TikTok upload error: {e}")
            return False
    
    @classmethod
    async def _wait_for_processing(
        cls,
        access_token: str,
        publish_id: str
    ) -> Dict[str, Any]:
        """
        Wait for TikTok to process the video (Step 3).
        
        Polls the status endpoint until video is published or fails.
        
        Returns:
            Success/error dict
        """
        print(f"🎵 TikTok: Waiting for video processing...")
        print(f"   (This can take 30 seconds to 5 minutes)")
        
        check_count = 0
        
        while check_count < cls.MAX_STATUS_CHECKS:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{cls.API_BASE}/v2/post/publish/status/fetch/",
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "Content-Type": "application/json; charset=UTF-8"
                        },
                        json={"publish_id": publish_id}
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Check for error in response
                        if data.get("error", {}).get("code") != "ok":
                            error_msg = data.get("error", {}).get("message", "Unknown error")
                            return cls.format_error_response(f"Status check failed: {error_msg}")
                        
                        status = data.get("data", {}).get("status")
                        
                        print(f"   📊 Status: {status} (check {check_count + 1}/{cls.MAX_STATUS_CHECKS})")
                        
                        # Check status
                        if status == "PUBLISH_COMPLETE":
                            # Get the post IDs
                            post_ids = data.get("data", {}).get("publicaly_available_post_id", [])
                            
                            if post_ids:
                                post_id = post_ids[0]
                                print(f"✅ TikTok: Video published successfully!")
                                print(f"   Post ID: {post_id}")
                                
                                # TikTok post URLs format: https://www.tiktok.com/@username/video/{post_id}
                                # Since we don't have username here, provide a generic URL
                                return cls.format_success_response(
                                    post_id,
                                    f"https://www.tiktok.com/video/{post_id}",
                                    post_id=post_id
                                )
                            else:
                                return cls.format_error_response("Video published but no post ID returned")
                        
                        elif status == "FAILED":
                            fail_reason = data.get("data", {}).get("fail_reason", "Unknown reason")
                            print(f"❌ TikTok: Video processing failed - {fail_reason}")
                            return cls.format_error_response(f"Video processing failed: {fail_reason}")
                        
                        elif status in ["PROCESSING_UPLOAD", "PROCESSING_DOWNLOAD", "SEND_TO_USER_INBOX", "PUBLISH_QUEUED"]:
                            # Still processing, wait and check again
                            await asyncio.sleep(cls.STATUS_CHECK_INTERVAL)
                            check_count += 1
                            continue
                        
                        else:
                            # Unknown status
                            print(f"⚠️ TikTok: Unknown status - {status}")
                            await asyncio.sleep(cls.STATUS_CHECK_INTERVAL)
                            check_count += 1
                            continue
                    else:
                        print(f"❌ TikTok status check failed: {response.status_code}")
                        return cls.format_error_response(f"Status check failed: {response.status_code}")
                        
            except Exception as e:
                print(f"❌ TikTok status check error: {e}")
                return cls.format_error_response(f"Status check error: {str(e)}")
        
        # Timeout
        print(f"⏰ TikTok: Processing timeout after {cls.MAX_STATUS_CHECKS * cls.STATUS_CHECK_INTERVAL} seconds")
        return cls.format_error_response(
            "Video processing timeout. Video may still be processing on TikTok."
        )
    
    @classmethod
    async def validate_token(cls, access_token: str) -> bool:
        """Validate TikTok access token"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{cls.API_BASE}/v2/user/info/",
                    params={"fields": "open_id,display_name"},
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("error", {}).get("code") == "ok"
                
                return False
        except:
            return False
    
    @classmethod
    async def get_user_info(cls, access_token: str) -> Optional[Dict[str, Any]]:
        """Get TikTok user information"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{cls.API_BASE}/v2/user/info/",
                    params={"fields": "open_id,union_id,avatar_url,display_name"},
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("error", {}).get("code") == "ok":
                        user = data.get("data", {}).get("user", {})
                        return {
                            "open_id": user.get("open_id"),
                            "union_id": user.get("union_id"),
                            "display_name": user.get("display_name"),
                            "avatar_url": user.get("avatar_url")
                        }
            
            return None
        except:
            return None
```

---

```
Base platform 

# app/services/platforms/base_platform.py
"""
Abstract base class for all social media platform services.
Provides common interface and utilities for platform-specific implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import httpx
from datetime import datetime


class BasePlatformService(ABC):
    """
    Abstract base class for social media platforms.
    All platform services must inherit from this class.
    """
    
    PLATFORM_NAME: str = "UNKNOWN"
    MAX_IMAGES: int = 0
    MAX_VIDEOS: int = 0
    MAX_VIDEO_SIZE_MB: int = 0
    MAX_VIDEO_DURATION_SECONDS: int = 0
    
    @abstractmethod
    async def post(
        self,
        access_token: str,
        content: str,
        image_urls: Optional[List[str]] = None,
        video_urls: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Post content to the platform.
        
        Args:
            access_token: Platform access token
            content: Text content to post
            image_urls: List of image URLs to attach
            video_urls: List of video URLs to attach
            **kwargs: Platform-specific additional parameters
            
        Returns:
            Dict with keys: success, platform_post_id, url, error (if failed)
        """
        pass
    
    @abstractmethod
    async def validate_token(self, access_token: str) -> bool:
        """Validate if the access token is still valid"""
        pass
    
    @classmethod
    async def download_media(cls, url: str, timeout: int = 60) -> Optional[bytes]:
        """
        Download media file from URL.
        
        Args:
            url: Media file URL
            timeout: Request timeout in seconds
            
        Returns:
            File content as bytes or None if failed
        """
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return response.content
                print(f"❌ Failed to download media: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Error downloading media: {e}")
            return None
    
    @classmethod
    def format_error_response(cls, error: str) -> Dict[str, Any]:
        """Format error response"""
        return {
            "success": False,
            "error": f"{cls.PLATFORM_NAME} error: {error}",
            "platform": cls.PLATFORM_NAME
        }
    
    @classmethod
    def format_success_response(
        cls,
        platform_post_id: str,
        url: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Format success response"""
        return {
            "success": True,
            "platform_post_id": platform_post_id,
            "url": url,
            "platform": cls.PLATFORM_NAME,
            **kwargs
        }
    
    @classmethod
    def validate_media_count(
        cls,
        image_urls: Optional[List[str]],
        video_urls: Optional[List[str]]
    ) -> Optional[str]:
        """
        Validate media counts against platform limits.
        Returns error message if validation fails, None if passes.
        """
        image_count = len(image_urls) if image_urls else 0
        video_count = len(video_urls) if video_urls else 0
        
        if image_count > cls.MAX_IMAGES:
            return f"{cls.PLATFORM_NAME} allows max {cls.MAX_IMAGES} images, got {image_count}"
        
        if video_count > cls.MAX_VIDEOS:
            return f"{cls.PLATFORM_NAME} allows max {cls.MAX_VIDEOS} videos, got {video_count}"
        
        return None
    ```

---
## This are the models I have in this app

```
# app/models.py
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    Text,
    ForeignKey,
    JSON,
    Float,
)
import sqlalchemy as sa
import enum
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text
from .database import Base


class TemplateCategory(enum.Enum):
    PRODUCT_LAUNCH = "product_launch"
    EVENT_PROMOTION = "event_promotion"
    BLOG_POST = "blog_post"
    ENGAGEMENT = "engagement"
    EDUCATIONAL = "educational"
    PROMOTIONAL = "promotional"
    SEASONAL = "seasonal"
    ANNOUNCEMENT = "announcement"
    BEHIND_SCENES = "behind_scenes"
    USER_GENERATED = "user_generated"
    TESTIMONIAL = "testimonial"
    INSPIRATIONAL = "inspirational"


class TemplateTone(enum.Enum):
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    HUMOROUS = "humorous"
    INSPIRATIONAL = "inspirational"
    EDUCATIONAL = "educational"
    URGENT = "urgent"
    FRIENDLY = "friendly"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    auth_provider = Column(String, nullable=True, default="email")
    last_login_method = Column(String, nullable=True)

    is_email_verified = Column(Boolean, default=False)
    email_verification_token = Column(String, nullable=True)
    email_verification_expires = Column(DateTime, nullable=True)

    password_reset_token = Column(String, nullable=True)
    password_reset_expires = Column(DateTime, nullable=True)

    is_active = Column(Boolean, default=True)
    plan = Column(String, default="trial")
    trial_ends_at = Column(DateTime, nullable=True)
    posts_used = Column(Integer, server_default=text("0"))
    posts_limit = Column(Integer, server_default=text("10"))

    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        DateTime, server_default=text("CURRENT_TIMESTAMP"), onupdate=datetime.utcnow
    )
    last_login = Column(DateTime, nullable=True)

    # Email notification preferences
    email_on_post_success = Column(Boolean, server_default=text("TRUE"))
    email_on_post_failure = Column(Boolean, server_default=text("TRUE"))
    email_weekly_analytics = Column(Boolean, server_default=text("TRUE"))

    # Relationships
    social_connections = relationship(
        "SocialConnection", back_populates="user", cascade="all, delete-orphan"
    )
    posts = relationship("Post", back_populates="user", cascade="all, delete-orphan")
    post_templates = relationship(
        "PostTemplate", back_populates="user", cascade="all, delete-orphan"
    )
    subscriptions = relationship(
        "Subscription", back_populates="user", cascade="all, delete-orphan"
    )
    template_folders = relationship(
        "TemplateFolder", back_populates="user", cascade="all, delete-orphan"
    )
    analytics_summaries = relationship(
        "UserAnalyticsSummary", back_populates="user", cascade="all, delete-orphan"
    )
    content_sources = relationship(
        "ContentSource", back_populates="user", cascade="all, delete-orphan"
    )
    video_campaigns = relationship(
        "VideoCampaign", back_populates="user", cascade="all, delete-orphan"
    )
    story_contents = relationship(
        "StoryContent", back_populates="user", cascade="all, delete-orphan"
    )


class SocialConnection(Base):
    __tablename__ = "social_connections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    platform = Column(String, nullable=False, index=True)
    platform_user_id = Column(String, nullable=False)
    username = Column(String, nullable=False)
    protocol = Column(String, nullable=True)
    oauth_token_secret = Column(Text, nullable=True)
    access_token = Column(Text, nullable=False)

    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    platform_avatar_url = Column(String, nullable=True)
    platform_username = Column(String, nullable=True)
    last_synced = Column(DateTime, nullable=True)
    is_active = Column(Boolean, server_default=text("TRUE"))
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        DateTime, server_default=text("CURRENT_TIMESTAMP"), onupdate=datetime.utcnow
    )

    facebook_page_id = Column(String, nullable=True)
    facebook_page_name = Column(String, nullable=True)
    facebook_page_access_token = Column(Text, nullable=True)
    facebook_page_category = Column(String, nullable=True)
    facebook_page_picture = Column(String, nullable=True)

    user = relationship("User", back_populates="social_connections")


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    original_content = Column(Text, nullable=False)
    enhanced_content = Column(JSONB, nullable=True)
    image_urls = Column(Text, nullable=True)
    video_urls = Column(Text, nullable=True)
    platform_specific_content = Column(JSONB, nullable=True)
    audio_file_url = Column(String, nullable=True)
    platforms = Column(Text, nullable=False)
    status = Column(String, server_default=text("'processing'"))
    scheduled_for = Column(DateTime, nullable=True, index=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        DateTime, server_default=text("CURRENT_TIMESTAMP"), onupdate=datetime.utcnow
    )

    user = relationship("User", back_populates="posts")
    post_results = relationship(
        "PostResult", back_populates="post", cascade="all, delete-orphan"
    )
    analytics = relationship(
        "PostAnalytics", back_populates="post", cascade="all, delete-orphan"
    )
    template_analytics = relationship(
        "TemplateAnalytics", back_populates="post", cascade="all, delete-orphan"
    )


class PostResult(Base):
    __tablename__ = "post_results"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(
        Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    platform = Column(String, nullable=False)

    status = Column(String, server_default=text("'pending'"))
    platform_post_id = Column(String, nullable=True)
    platform_post_url = Column(String, nullable=True)
    content_used = Column(Text, nullable=True)

    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, server_default=text("0"))

    posted_at = Column(DateTime, nullable=True)
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        DateTime, server_default=text("CURRENT_TIMESTAMP"), onupdate=datetime.utcnow
    )

    post = relationship("Post", back_populates="post_results")


class PostTemplate(Base):
    __tablename__ = "post_templates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )

    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    # ✅ Changed from SAEnum to String
    category = Column(String, nullable=False, index=True)

    content_template = Column(Text, nullable=False)
    variables = Column(JSON, nullable=True)

    platform_variations = Column(JSON, nullable=True)
    supported_platforms = Column(JSON, nullable=False)

    # ✅ Changed from SAEnum to String
    tone = Column(String, server_default=text("'engaging'"))
    suggested_hashtags = Column(JSON, nullable=True)
    suggested_media_type = Column(String, nullable=True)

    is_public = Column(Boolean, server_default=text("FALSE"))
    is_premium = Column(Boolean, server_default=text("FALSE"))
    is_system = Column(Boolean, server_default=text("FALSE"))

    usage_count = Column(Integer, server_default=text("0"))
    success_rate = Column(Integer, server_default=text("0"))
    avg_engagement = Column(JSON, nullable=True)

    thumbnail_url = Column(String, nullable=True)
    color_scheme = Column(String, server_default=text("'#3B82F6'"))
    icon = Column(String, server_default=text("'sparkles'"))

    is_favorite = Column(Boolean, server_default=text("FALSE"))
    folder_id = Column(
        Integer, ForeignKey("template_folders.id", ondelete="SET NULL"), nullable=True
    )

    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        DateTime, server_default=text("CURRENT_TIMESTAMP"), onupdate=datetime.utcnow
    )
    last_used_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="post_templates")
    folder = relationship("TemplateFolder", back_populates="templates")
    template_analytics = relationship(
        "TemplateAnalytics", back_populates="template", cascade="all, delete-orphan"
    )


class TemplateFolder(Base):
    __tablename__ = "template_folders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String, server_default=text("'#6366F1'"))
    icon = Column(String, server_default=text("'folder'"))

    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        DateTime, server_default=text("CURRENT_TIMESTAMP"), onupdate=datetime.utcnow
    )

    user = relationship("User", back_populates="template_folders")
    templates = relationship(
        "PostTemplate", back_populates="folder", cascade="all, delete-orphan"
    )


class TemplateAnalytics(Base):
    __tablename__ = "template_analytics"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(
        Integer,
        ForeignKey("post_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    post_id = Column(
        Integer, ForeignKey("posts.id", ondelete="SET NULL"), nullable=True
    )

    views = Column(Integer, server_default=text("0"))
    likes = Column(Integer, server_default=text("0"))
    comments = Column(Integer, server_default=text("0"))
    shares = Column(Integer, server_default=text("0"))
    engagement_rate = Column(Integer, server_default=text("0"))

    platform = Column(String, nullable=False)
    posted_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    template = relationship("PostTemplate", back_populates="template_analytics")
    post = relationship("Post", back_populates="template_analytics")


class PostAnalytics(Base):
    __tablename__ = "post_analytics"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(
        Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    platform = Column(String, nullable=False, index=True)

    # Core metrics (common across platforms)
    views = Column(Integer, server_default=text("0"))
    impressions = Column(Integer, server_default=text("0"))
    reach = Column(Integer, server_default=text("0"))

    # Engagement metrics
    likes = Column(Integer, server_default=text("0"))
    comments = Column(Integer, server_default=text("0"))
    shares = Column(Integer, server_default=text("0"))
    saves = Column(Integer, server_default=text("0"))
    clicks = Column(Integer, server_default=text("0"))

    # Platform-specific metrics (stored as JSON)
    platform_specific_metrics = Column(JSONB, nullable=True)

    # Engagement rate calculation
    engagement_rate = Column(Float, server_default=text("0.0"))

    # Metadata
    fetched_at = Column(
        DateTime, nullable=False, index=True, server_default=text("CURRENT_TIMESTAMP")
    )
    error = Column(Text, nullable=True)

    __table_args__ = (
        sa.UniqueConstraint("post_id", "platform", name="uq_post_platform"),
    )

    post = relationship("Post", back_populates="analytics")


class UserAnalyticsSummary(Base):
    __tablename__ = "user_analytics_summaries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # ✅ Changed from Enum to String
    period = Column(String, nullable=False, index=True)
    start_date = Column(DateTime, nullable=False, index=True)
    end_date = Column(DateTime, nullable=False)
    total_posts = Column(Integer, server_default=text("0"))
    total_engagements = Column(Integer, server_default=text("0"))
    total_impressions = Column(Integer, server_default=text("0"))
    avg_engagement_rate = Column(Float, server_default=text("0.0"))
    platform_breakdown = Column(JSONB, nullable=True)
    updated_at = Column(
        DateTime, server_default=text("CURRENT_TIMESTAMP"), onupdate=datetime.utcnow
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "user_id", "period", "start_date", name="uq_user_period_start"
        ),
    )

    user = relationship("User", back_populates="analytics_summaries")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    plan = Column(String, nullable=False)
    status = Column(String, server_default=text("'active'"))
    amount = Column(Integer, nullable=False)
    currency = Column(String, server_default=text("'USD'"))
    payment_method = Column(String, nullable=False)
    payment_reference = Column(String, nullable=True)

    starts_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    ends_at = Column(DateTime, nullable=False)

    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        DateTime, server_default=text("CURRENT_TIMESTAMP"), onupdate=datetime.utcnow
    )

    user = relationship("User", back_populates="subscriptions")


class ContentSource(Base):
    __tablename__ = "content_sources"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    source_type = Column(String, nullable=False)
    source_url = Column(String, nullable=True)
    subreddit_name = Column(String, nullable=True)
    rss_feed_url = Column(String, nullable=True)

    keywords_filter = Column(JSON, nullable=True)
    exclude_keywords = Column(JSON, nullable=True)
    min_score = Column(Integer, server_default=text("100"))
    max_age_hours = Column(Integer, server_default=text("24"))

    is_active = Column(Boolean, server_default=text("TRUE"))
    last_fetched = Column(DateTime, nullable=True)
    fetch_interval_hours = Column(Integer, server_default=text("6"))

    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        DateTime, server_default=text("CURRENT_TIMESTAMP"), onupdate=datetime.utcnow
    )

    user = relationship("User", back_populates="content_sources")
    campaigns = relationship("VideoCampaign", back_populates="content_source")


class VideoCampaign(Base):
    __tablename__ = "video_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content_source_id = Column(
        Integer, ForeignKey("content_sources.id", ondelete="SET NULL"), nullable=True
    )

    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    video_style = Column(String, server_default=text("'ai_images_motion'"))
    aspect_ratio = Column(String, server_default=text("'9:16'"))
    duration_seconds = Column(Integer, server_default=text("60"))

    tts_provider = Column(String, server_default=text("'openai'"))
    tts_voice = Column(String, server_default=text("'alloy'"))
    tts_speed = Column(Float, server_default=text("1.0"))

    background_music_url = Column(String, nullable=True)
    music_volume = Column(Float, server_default=text("0.3"))

    caption_style = Column(String, server_default=text("'modern'"))
    caption_font = Column(String, server_default=text("'Montserrat'"))
    caption_color = Column(String, server_default=text("'#FFFFFF'"))
    caption_position = Column(String, server_default=text("'bottom'"))

    auto_generate = Column(Boolean, server_default=text("TRUE"))
    videos_per_day = Column(Integer, server_default=text("2"))
    preferred_times = Column(JSON, nullable=True)

    platforms = Column(JSON, nullable=False)

    status = Column(String, server_default=text("'active'"))
    videos_generated = Column(Integer, server_default=text("0"))
    last_generation = Column(DateTime, nullable=True)

    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        DateTime, server_default=text("CURRENT_TIMESTAMP"), onupdate=datetime.utcnow
    )

    user = relationship("User", back_populates="video_campaigns")
    content_source = relationship("ContentSource", back_populates="campaigns")
    video_jobs = relationship(
        "VideoJob", back_populates="campaign", cascade="all, delete-orphan"
    )


class VideoJob(Base):
    __tablename__ = "video_jobs"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(
        Integer,
        ForeignKey("video_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    source_url = Column(String, nullable=True)
    source_title = Column(String, nullable=True)
    source_content = Column(Text, nullable=True)

    script_text = Column(Text, nullable=True)
    script_scenes = Column(JSON, nullable=True)

    narration_url = Column(String, nullable=True)
    narration_duration = Column(Float, nullable=True)

    image_prompts = Column(JSON, nullable=True)
    image_urls = Column(JSON, nullable=True)

    video_url = Column(String, nullable=True)
    thumbnail_url = Column(String, nullable=True)
    video_duration = Column(Float, nullable=True)

    status = Column(String, server_default=text("'pending'"))
    progress = Column(Integer, server_default=text("0"))
    error_message = Column(Text, nullable=True)

    platforms = Column(JSON, nullable=True)
    platform_post_ids = Column(JSON, nullable=True)
    posted_at = Column(DateTime, nullable=True)

    scheduled_for = Column(DateTime, nullable=True)

    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        DateTime, server_default=text("CURRENT_TIMESTAMP"), onupdate=datetime.utcnow
    )

    campaign = relationship("VideoCampaign", back_populates="video_jobs")


class StoryContent(Base):
    __tablename__ = "story_contents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_id = Column(
        Integer, ForeignKey("content_sources.id", ondelete="SET NULL"), nullable=True
    )

    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    source_type = Column(String, nullable=False)
    source_url = Column(String, nullable=True)
    author = Column(String, nullable=True)

    score = Column(Integer, server_default=text("0"))
    num_comments = Column(Integer, server_default=text("0"))

    is_used = Column(Boolean, server_default=text("FALSE"))
    used_in_job_id = Column(
        Integer, ForeignKey("video_jobs.id", ondelete="SET NULL"), nullable=True
    )

    fetched_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    user = relationship("User", back_populates="story_contents")

```
### Extra info

Now I know this might not be aligned with the techstack you are using ,but I would like you to have the logic and know how I'm calling the social media apis . Now I would like to have an option also to upload content in my dashboard and sometimes I might have content I want to schedule(We can work on the scheduling feature later), but I want a content automation system so cool that , it keeps previous posts, and it goes on to grow my social media following and brand , I want this agent to be running autonomusly , a very cool project and I want the dashboard to have an option where sometimes where I can just post from that dashboard with AI enhancment tools and I can have that like a small studio ,this should be a very cool project with the best design possible , I'm also going to upload the settings I have in my other app for you to get inspiration and more context and idea


```
# app/config.py
from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    # ========== REQUIRED FIELDS ==========
    # Database - MUST be set
    DATABASE_URL: str

    # JWT - MUST be set
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24

    # ========== OPTIONAL FIELDS WITH DEFAULTS ==========

    # Redis (Optional - only if you're using Celery)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Celery (Optional - only if you're using background tasks)
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""
    USE_CLOUDINARY: bool = False

    # File Storage (Optional - AWS S3 for production)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_BUCKET_NAME: str = ""
    AWS_REGION: str = "us-east-1"

    # AI Services (Optional - can add later)
    OPENAI_API_KEY: str = ""

    # Social Platform APIs - Twitter/X (Optional)
    TWITTER_API_KEY: str = ""
    TWITTER_API_SECRET: str = ""
    TWITTER_BEARER_TOKEN: str = ""
    TWITTER_CLIENT_ID: str = ""
    TWITTER_CLIENT_SECRET: str = ""

    # Facebook (Optional)
    FACEBOOK_APP_ID: str = ""
    FACEBOOK_APP_SECRET: str = ""

    # LinkedIn (Optional)
    LINKEDIN_CLIENT_ID: str = ""
    LINKEDIN_CLIENT_SECRET: str = ""

    # Instagram (Optional)
    INSTAGRAM_CLIENT_ID: str = ""
    INSTAGRAM_CLIENT_SECRET: str = ""

    # TIKTOK (Optional)
    TIKTOK_CLIENT_ID: str = ""
    TIKTOK_CLIENT_SECRET: str = ""

    # Youtube
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # Local storage dir path (fallback if no cloud storage)
    UPLOAD_DIR: str = "uploads/"

    # Application URLs
    FRONTEND_URL: str = "https://skeduluk-social.vercel.app"
    BACKEND_URL: str = "https://skeduluk-fastapi.onrender.com"
    APP_URL: str = "https://skeduluk-social.vercel.app"


    # SMTP/Email Configuration (Optional - can add later)
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = "noreply@skeduluk.com"
    FROM_NAME: str = "Skeduluk"

    # Application
    ALLOWED_ORIGINS: List[str] = [
        "https://skeduluk-social.vercel.app",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ]
    APP_NAME: str = "Skeduluk"
    DEBUG: bool = False

    # Reddit API (for content fetching)
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = "Skeduluk/1.0"

    # Video Generation Settings
    VIDEO_OUTPUT_DIR: str = "videos/"
    VIDEO_TEMP_DIR: str = "temp/"
    VIDEO_MAX_DURATION: int = 180
    VIDEO_DEFAULT_ASPECT: str = "9:16"

    # TTS Settings (OpenAI)
    OPENAI_TTS_MODEL: str = "tts-1"
    OPENAI_TTS_VOICE: str = "alloy"

    # Image Generation (DALL-E)
    DALLE_MODEL: str = "dall-e-3"
    DALLE_IMAGE_SIZE: str = "1024x1024"
    DALLE_IMAGE_QUALITY: str = "standard"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
```
    


So I also want to have an option of open ai , you can notice here that I'm using the google client id and google client secret, and you can notice I also have a defined endpoint for a call back url that is dynamnic but same base for different platforms , same idea I'm thinking for this app  .I want you tob be creative and come up with the best way to mitigate this and come up with the best content creation pipeline that will make me go viral , now I don't know wheter we will be using github actions for automations or which simple solution can we integrate that will not cost much resources and time , go ahead and give me the idea ...Go ahead and come up with the best solution , something that is going to work, don't copy the whole code and just paste what i have given you , no I want you to develop a solution using the same logic in the code but I don't want you to copy the code i have just given you word for word....FInd something we can work on 

Again I want to have a database using sql alchemy as the ORM and i'm going to link this up with my postgre sql , let me give you my db.py to show you how I usually create this 

---
```

# app/database.py
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv

load_dotenv()

def get_async_database_url():
    """Convert DATABASE_URL to asyncpg format"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    
    # Split URL at the '?' to separate base URL from query parameters
    if '?' in database_url:
        base_url = database_url.split('?')[0]
    else:
        base_url = database_url
    
    # Convert to asyncpg format
    if base_url.startswith('postgresql://'):
        async_url = base_url.replace('postgresql://', 'postgresql+asyncpg://')
    elif base_url.startswith('postgres://'):
        async_url = base_url.replace('postgres://', 'postgresql+asyncpg://')
    else:
        async_url = base_url
    
    return async_url

# ==================== GLOBAL ENGINE FOR FASTAPI ====================

engine = create_async_engine(
    get_async_database_url(),
    echo=False,
    pool_pre_ping=True,  # Verify connections are alive before using
    pool_recycle=300,  # Recycle connections after 5 minutes
    pool_size=20,  # ✅ Increased pool size for concurrent requests
    max_overflow=10,  # ✅ Allow extra connections during peak
    pool_timeout=30,  # ✅ Wait up to 30 seconds for a connection
    connect_args={
        "ssl": "require",  # Neon requires SSL
        "timeout": 60,  # ✅ 60 second connection timeout
        "command_timeout": 60,  # ✅ 60 second command timeout
        "server_settings": {
            "application_name": "social_scheduler_fastapi", # replace this with the name of the agent lets call this kontentPyper
            "jit": "off"  # Disable JIT for faster simple queries
        }
    }
)

# Create async session factory for FastAPI
AsyncSessionLocal = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

Base = declarative_base()

# ==================== DEPENDENCY FOR FASTAPI ====================

async def get_async_db():
    """
    FastAPI dependency that provides a database session.
    ✅ Improved error handling for connection issues
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            print(f"❌ Database session error: {e}")
            # Let FastAPI's exception handler deal with it
            raise
        finally:
            # Close session cleanly
            try:
                await session.close()
            except Exception as close_error:
                print(f"⚠️ Error closing session: {close_error}")
                # Don't re-raise - session is already problematic
```
---
# AGENT NAME : kontent Pyper

So I have given you the context on what I expect , tech stack is perfect fast api is good , python is perfect , the database we can switch this up to neon(postgre sql) and connecting this with sql alchemy , we will also be working on the dashboard auth not just anybody can login , but I think it will be cool to have an agent that can create posts on occation , get analytics and even train on the data of your socials and give you suggestions to improve or restratagize , go ahead and build this my 10 x developer