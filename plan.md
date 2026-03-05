# KontentPyper Architecture & Implementation Plan

## 1. Overview
**KontentPyper** is a smart, autonomous content automation agent and mini-studio designed to orchestrate social media posting across multiple platforms (Twitter, LinkedIn, YouTube, TikTok, Facebook). It features secure dashboard access, an AI enhancement studio, content scheduling, and an autonomous AI loop that analyzes past performance to suggest and execute optimized social strategies.

## 2. Tech Stack
- **Backend Framework:** FastAPI (Python)
- **Database:** PostgreSQL (hosted on Neon) using `asyncpg` and SQLAlchemy ORM.
- **AI Integration:** OpenAI / Google Gemini (for content creation, prompt enhancement, and analytics interpretation).
- **Task Scheduling:** APScheduler or light Celery wrapper for running scheduled tasks without excessive overhead.
- **File Storage:** Local uploads fallback + Cloudinary/AWS S3 for robust media delivery.
- **Authentication:** JWT for the dashboard, alongside standard OAuth 1.0a / 2.0 flows to connect the agent to external platforms.

## 3. Core Features & Modularity

### A. Secure Dashboard & Mini-Studio
- We will set up a secured admin layer restricting access solely to the authenticated owner.
- The dashboard allows direct uploads, manual scheduling, and contains a "Mini Studio" where KontentPyper can enhance ideas, generate captions, structure posts and generate proper formats per platform limits.

### B. OAuth Integration Flow
- We will reuse and adapt the robust OAuth state-management and logic defined in your example for 3-legged OAuth 1.0a (Twitter) and OAuth 2.0 (LinkedIn, YouTube, TikTok).
- Robust retries, token refreshing logic, and proper chunked upload implementations will be kept cleanly in separated classes subclassing `BasePlatformService`.

### C. KontentPyper AI capabilities
1. **Autonomous Creation & Scheduling:** A background loop pulling trending content / RSS links, filtering them, generating scripts or tweets, and queuing jobs.
2. **"Studio" Assistant:** When you're making manual posts, you can chat with KontentPyper to dynamically enhance media context (via vision or text), and map out threads and hashtags.
3. **Analytics & Reflection Loop:** Periodically fetches analytics into the Neon DB. The agent runs a summary context every week, reading what performed best (Views, CTAs, Engagements) and self-adjusts future scheduled tone/prompts.

### D. System Architecture Folders
```text
app/
├── api/             # FastAPI routes (auth, studio, social, webhooks, analytics)
├── core/            # Config (.env parsing), Security (JWT), Database setup
├── models/          # SQLAlchemy declarative models (User, Post, Analytics, etc.)
├── schemas/         # Pydantic validation schemas
├── services/        # Business logic
│   ├── ai/          # KontentPyper AI logic & strategy training loop
│   ├── platforms/   # Twitter, TikTok, LinkedIn posting adapters
│   └── scheduler/   # APScheduler logic for queued jobs
└── main.py          # App entrypoint
```

## 4. Implementation Phasing
**Phase 1: Foundation & Auth** 
- Setup FastAPI structure, `config.py`, and `database.py` referencing Neon PostgreSQL.
- Scaffold database models based on your architecture.
- Secure standard Auth (JWT) so you can safely log into your private dashboard.

**Phase 2: Platform Integration**
- Integrate `OAuthService` for connection links and callbacks.
- Setup `SocialService` and specific platform uploaders ensuring video chunks and rate-limiting respect the platform thresholds.

**Phase 3: The AI Studio & Scheduled Pipelines**
- Add the `KontentPyper` logic handling text prompt enhancement, formatting requests (taking single text and scaling it to Twitter thread vs LinkedIn post).
- Hook up background scheduler routines to run pending items.

**Phase 4: Analytics Feedback Loop**
- Implement API sync that pulls metrics to the Database (`PostAnalytics`) and automatically calls KontentPyper periodically to evaluate and update ongoing "Campaigns".

## 5. Next Steps
Once you review this plan to ensure it meets your expectations, we will proceed with **Phase 1** which involves scaffolding the repository structure, `database.py`, configuration elements, and the base models. 
