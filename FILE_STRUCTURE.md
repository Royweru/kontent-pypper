# KontentPyper - Definitive Project File Structure

Below is every file in the **final** repository. Old prototype directories
(`config/`, `dashboard/`, `pipeline/`, `data/`, `output/`) are superseded
by the new `app/` package and can be safely removed.

```text
content_automation_pipeline/
|
|-- .env                              # Environment variables (secrets, API keys)
|-- .gitignore
|-- requirements.txt                  # Python dependencies
|-- alembic.ini                       # Alembic migration config
|-- run.py                            # Quick-start script: uvicorn app.main:app
|-- plan.md                           # Architecture plan
|-- ready_solution.md                 # Reference solution doc
|
|-- alembic/                          # Database migrations
|   |-- env.py
|   |-- versions/
|
|-- uploads/                          # Local media upload fallback
|
|-- app/
    |-- __init__.py
    |-- main.py                       # FastAPI entrypoint, CORS, lifespan
    |
    |-- core/
    |   |-- __init__.py
    |   |-- config.py                 # Pydantic Settings (all env vars)
    |   |-- database.py               # Async SQLAlchemy engine (Neon PG)
    |   |-- security.py               # JWT encode/decode, password hashing
    |
    |-- models/
    |   |-- __init__.py               # Re-exports all models + Base
    |   |-- user.py                   # User, Subscription
    |   |-- social.py                 # SocialConnection
    |   |-- post.py                   # Post, PostResult
    |   |-- content.py                # PostTemplate, TemplateFolder, ContentSource, StoryContent
    |   |-- campaign.py               # VideoCampaign, VideoJob
    |   |-- analytics.py              # PostAnalytics, UserAnalyticsSummary, TemplateAnalytics
    |
    |-- schemas/
    |   |-- __init__.py
    |   |-- auth.py                   # Login / Register / Token schemas
    |   |-- post.py                   # Create post, draft, publish request/response
    |   |-- social.py                 # Connection status, OAuth state
    |   |-- analytics.py              # Analytics response shapes
    |
    |-- api/
    |   |-- __init__.py
    |   |-- deps.py                   # Shared FastAPI dependencies (get_current_user, get_db)
    |   |-- auth.py                   # POST /login, /register, GET /me
    |   |-- social.py                 # OAuth initiate, callback, list connections
    |   |-- studio.py                 # POST /draft, /publish, /upload-media
    |   |-- analytics.py              # GET analytics summaries, per-post metrics
    |
    |-- services/
    |   |-- __init__.py
    |   |-- oauth_service.py          # Universal OAuth 1.0a / 2.0 state manager
    |   |-- social_service.py         # Multi-platform publish orchestrator
    |   |
    |   |-- platforms/
    |   |   |-- __init__.py           # get_platform_service() registry
    |   |   |-- base_platform.py      # Abstract base: download, validate, format
    |   |   |-- twitter.py            # Twitter/X (OAuth 1.0a, chunked upload)
    |   |   |-- linkedin.py           # LinkedIn (UGC, video processing wait)
    |   |   |-- youtube.py            # YouTube (Google API Client upload)
    |   |   |-- tiktok.py             # TikTok (v2 Direct publish)
    |   |
    |   |-- ai/
    |   |   |-- __init__.py
    |   |   |-- llm_client.py         # Unified wrapper: OpenAI / Gemini
    |   |   |-- enhancer.py           # Content enhancement prompts & formatting
    |   |   |-- reflector.py          # Analytics reflection & strategy tuning
    |   |
    |   |-- scheduler/
    |       |-- __init__.py
    |       |-- engine.py             # APScheduler init & job registration
    |       |-- jobs.py               # Scheduled tasks (fetch, generate, publish)
```
