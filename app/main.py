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
    # Restore active user cron jobs from the database
    await _restore_user_cron_jobs()
    yield
    print(f"[KontentPyper] Shutting down...")
    stop_scheduler()


async def _restore_user_cron_jobs():
    """Re-registers all active ScheduledJob cron entries on startup."""
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.schedule import ScheduledJob
    from app.api.schedule import _register_user_cron

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ScheduledJob).where(ScheduledJob.is_active == True)
            )
            jobs = result.scalars().all()

            for job in jobs:
                _register_user_cron(job.user_id, job.cron_hour, job.cron_minute, job.cron_dow)

            print(f"[KontentPyper] Restored {len(jobs)} active cron job(s).")
    except Exception as exc:
        print(f"[KontentPyper] Warning: Could not restore cron jobs: {exc}")

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

from app.api import social, studio, analytics, news, posts, media, workflow, assets, schedule, review, campaigns, billing, system
app.include_router(social.router,    prefix="/api/v1/social",    tags=["social"])
app.include_router(studio.router,    prefix="/api/v1/studio",    tags=["studio"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(news.router,      prefix="/api/v1/news",      tags=["news"])
app.include_router(posts.router,     prefix="/api/v1/posts",     tags=["posts"])
app.include_router(media.router,     prefix="/api/v1/media",     tags=["media"])
app.include_router(assets.router,    prefix="/api/v1/assets",    tags=["assets"])
app.include_router(workflow.router,  prefix="/api/v1/workflow",  tags=["workflow"])
app.include_router(schedule.router,  prefix="/api/v1/schedule",  tags=["schedule"])
app.include_router(review.router,    prefix="/api/v1/review",    tags=["review"])
app.include_router(campaigns.router, prefix="/api/v1/campaigns", tags=["campaigns"])
app.include_router(billing.router,   prefix="/api/v1/billing",   tags=["billing"])
app.include_router(system.router,    prefix="/api/v1/system",    tags=["system"])

# -- Dashboard UI -----------------------------------------------------------
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
app.mount("/dashboard/static", StaticFiles(directory=str(STATIC_DIR)), name="dashboard-static")

# -- Webhooks ---------------------------------------------------------------
from app.api.webhook import telegram as tg_webhook
app.include_router(tg_webhook.router, prefix="/webhook", tags=["webhook"])

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

if __name__ == "__main__":
    import uvicorn
    print("App starting on http://localhost:8000")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
