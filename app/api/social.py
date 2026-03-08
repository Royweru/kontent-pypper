"""
KontentPyper - Social API Router
Handles OAuth initialization, callbacks, and platform connections listing.
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from app.api.deps import CurrentUser, DB
from app.services.oauth_service import OAuthService
from app.services.social_service import SocialService
from app.core.config import settings

router = APIRouter()

# ── Connections ───────────────────────────────────────────────────

@router.get("/connections", summary="List Connected Platforms")
async def list_connections(user: CurrentUser, db: DB):
    """Returns a list of platforms the user is authenticated to."""
    connections = await SocialService.get_active_connections(db, user.id)
    return [
        {
            "platform": c.platform,
            "username": c.platform_username,
            "updated_at": c.updated_at
        }
        for c in connections
    ]

# ── OAuth initialization ──────────────────────────────────────────

@router.get("/oauth/initiate/{platform}", summary="Init OAuth Flow")
async def initiate_oauth(platform: str, user: CurrentUser):
    """
    Returns the authorization URL for the user to visit.
    Frontend opens this in a popup window.
    """
    try:
        auth_url = await OAuthService.initiate_oauth(user.id, platform)
        return {"auth_url": auth_url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ── OAuth callback ────────────────────────────────────────────────

def _build_callback_html(success: bool, platform: str, error_msg: str = "") -> str:
    """
    Returns a self-closing HTML page that sends a postMessage to the
    parent (opener) dashboard window and then closes this popup.
    """
    status = "connected" if success else "failed"
    title = f"Connected to {platform}!" if success else f"Connection failed"
    subtitle = f"You can close this window." if success else error_msg
    dot_color = "#52c41a" if success else "#ff4d4f"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <title>KontentPyper OAuth</title>
  <style>
    body {{
      margin: 0; display: flex; align-items: center; justify-content: center;
      height: 100vh; background: #0a0a0f; color: #e0e0e0;
      font-family: 'Inter', system-ui, sans-serif;
    }}
    .card {{
      text-align: center; padding: 40px; border-radius: 12px;
      background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
    }}
    .dot {{ width: 12px; height: 12px; border-radius: 50%; display: inline-block;
            background: {dot_color}; margin-right: 8px; }}
    h2 {{ margin: 0 0 8px; font-size: 20px; }}
    p {{ margin: 0; font-size: 14px; color: #888; }}
  </style>
</head>
<body>
  <div class="card">
    <h2><span class="dot"></span>{title}</h2>
    <p>{subtitle}</p>
  </div>
  <script>
    // Notify the parent dashboard window
    if (window.opener) {{
      window.opener.postMessage({{
        type: 'oauth_callback',
        status: '{status}',
        platform: '{platform}'
      }}, '*');
    }}
    // Auto-close after a short delay so the user sees the confirmation
    setTimeout(() => window.close(), 1800);
  </script>
</body>
</html>"""


@router.get("/oauth/callback/{platform}", summary="OAuth Callback URL", include_in_schema=False)
async def oauth_callback(
    platform: str,
    request: Request,
    db: DB,
    code: str = None,
    state: str = None,
    oauth_token: str = None,
    oauth_verifier: str = None,
    error: str = None,
):
    """
    Consumes the callback from the external provider.
    Validates tokens, exchanges them, and saves to SocialConnection DB table.
    Returns a self-closing HTML page that notifies the opener window via postMessage.
    """
    result = await OAuthService.handle_callback(
        platform=platform,
        db=db,
        code=code,
        state=state,
        oauth_token=oauth_token,
        oauth_verifier=oauth_verifier,
        error=error
    )

    if result.get("success"):
        return HTMLResponse(_build_callback_html(True, platform))
    else:
        err_msg = result.get("error", "unknown_error")
        return HTMLResponse(_build_callback_html(False, platform, err_msg))


@router.delete("/disconnect/{platform}")
async def disconnect_platform(
    platform: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a social platform connection for the current user."""
    stmt = delete(SocialConnection).where(
        SocialConnection.user_id == current_user.id,
        SocialConnection.platform == platform,
    )
    await db.execute(stmt)
    await db.commit()
    return {"success": True, "message": f"Disconnected {platform}"}
