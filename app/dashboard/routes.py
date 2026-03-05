"""
KontentPyper - Dashboard Router
Serves HTML pages and mounts the static/ directory for CSS/JS.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

router = APIRouter()

DASHBOARD_DIR = Path(__file__).parent


def _read(filename: str) -> str:
    return (DASHBOARD_DIR / filename).read_text(encoding="utf-8")


# ── Static files (CSS, JS) ────────────────────────────────────────
# Mounted in main.py so paths can be /dashboard/static/...
STATIC_DIR = DASHBOARD_DIR / "static"


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def dashboard_root():
    """Serve the main dashboard (auth guard handled client-side via JWT)."""
    return _read("index.html")


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page():
    """Serve the login page."""
    return _read("login.html")
