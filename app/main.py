"""
KontentPyper - Application Entrypoint
FastAPI server with CORS, lifespan hooks, and API router mounting.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.core.config import settings
from app.api import auth
from app.dashboard import routes as dashboard
from app.dashboard.routes import STATIC_DIR
from app.public import routes as public_pages
from app.public.routes import STATIC_DIR as PUBLIC_STATIC_DIR
from app.services.scheduler.engine import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Startup and shutdown lifecycle hooks."""
    print(f"[KontentPyper] Starting up...")
    start_scheduler()
    yield
    print(f"[KontentPyper] Shutting down...")
    stop_scheduler()

app = FastAPI(
    title=settings.APP_NAME,
    description="Autonomous social-media content agent and mini-studio",
    version="0.3.0",
    lifespan=lifespan,
)

# -- CORS ------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -- API Routes -------------------------------------------------------------
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])

from app.api import social, studio, analytics, news
app.include_router(social.router,    prefix="/api/v1/social",    tags=["social"])
app.include_router(studio.router,    prefix="/api/v1/studio",    tags=["studio"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(news.router,      prefix="/api/v1/news",      tags=["news"])

# -- Dashboard UI -----------------------------------------------------------
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
app.mount("/dashboard/static", StaticFiles(directory=str(STATIC_DIR)), name="dashboard-static")

# -- Public Pages (landing, signup, terms, privacy) -------------------------
app.include_router(public_pages.router, tags=["public"])
app.mount("/static", StaticFiles(directory=str(PUBLIC_STATIC_DIR)), name="public-static")

# -- Logo -------------------------------------------------------------------
from fastapi.responses import FileResponse
from pathlib import Path as _P
_LOGO = _P(__file__).parent.parent / "logo.png"

@app.get("/logo.png", include_in_schema=False)
async def serve_logo():
    return FileResponse(str(_LOGO), media_type="image/png")


# -- Health check -----------------------------------------------------------
@app.get("/health", tags=["system"])
async def health_check():
    return {"status": "ok", "agent": settings.APP_NAME}

