"""
KontentPyper - Public Pages Router
Serves the landing page, signup, terms, and privacy pages.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pathlib import Path

router = APIRouter()

PUBLIC_DIR = Path(__file__).parent
STATIC_DIR = PUBLIC_DIR / "static"


def _read(filename: str) -> str:
    return (PUBLIC_DIR / filename).read_text(encoding="utf-8")


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def landing_page():
    """Serve the public landing page."""
    return _read("landing.html")


@router.get("/signup", response_class=HTMLResponse, include_in_schema=False)
async def signup_page():
    """Serve the registration page."""
    return _read("signup.html")


@router.get("/terms", response_class=HTMLResponse, include_in_schema=False)
async def terms_page():
    """Serve the Terms of Service page."""
    return _read("terms.html")


@router.get("/privacy", response_class=HTMLResponse, include_in_schema=False)
async def privacy_page():
    """Serve the Privacy Policy page."""
    return _read("privacy.html")
