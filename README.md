<p align="center">
  <img src="logo.png" alt="KontentPyper" width="80" />
</p>

<h1 align="center">KontentPyper</h1>

<p align="center">
  <strong>Autonomous Social Media Content Agent &amp; Mini-Studio</strong><br/>
  Schedule, enhance, publish, and analyze content across every major platform -- all from one dark-themed dashboard.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/PostgreSQL-Neon-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License" />
</p>

---

## What is KontentPyper?

KontentPyper is a **self-hosted content automation pipeline** that acts as your personal social media manager. It connects to Twitter/X, LinkedIn, YouTube, TikTok, and Facebook via OAuth, lets you draft and enhance posts with AI, schedule them for the future, and autonomously reflects on past performance to improve your content strategy over time.

### Key Capabilities

- **Multi-Platform Publishing** -- Post to Twitter, LinkedIn, YouTube, TikTok, and Facebook from a single interface.
- **AI-Powered Studio** -- Draft content and let the built-in AI (OpenAI / Google Gemini) enhance, reformat, and optimize it per platform.
- **Smart Scheduling** -- Queue posts for specific dates and times; APScheduler handles execution in the background.
- **Analytics Dashboard** -- Pull engagement metrics from each platform and visualize trends over 12 weeks.
- **AI Reflection Loop** -- The agent periodically analyzes what worked and what didn't, then adjusts its strategy accordingly.
- **Responsive Dashboard** -- A dark-themed, collapsible-sidebar UI that works beautifully on desktop and mobile.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | FastAPI (Python 3.11+) |
| **Database** | PostgreSQL on [Neon](https://neon.tech) (async via `asyncpg`) |
| **ORM** | SQLAlchemy 2.0 (async) |
| **Migrations** | Alembic |
| **Auth** | JWT (python-jose) + bcrypt password hashing |
| **AI** | OpenAI API / Google Gemini API |
| **Scheduling** | APScheduler (future: Celery + Redis) |
| **Frontend** | Vanilla HTML/CSS/JS served by FastAPI |
| **Containerization** | Docker |
| **Deployment** | Railway (recommended) |

---

## Project Structure

```
content_automation_pipeline/
|-- app/
|   |-- api/                # FastAPI route handlers
|   |   |-- auth.py         # /register, /login, /me
|   |   |-- social.py       # OAuth initiate, callback, list connections
|   |   |-- studio.py       # /draft, /publish, /upload-media, /chat
|   |   |-- analytics.py    # /summary, /posts, /reflect
|   |   +-- deps.py         # Dependency injection (get_current_user, get_db)
|   |-- core/
|   |   |-- config.py       # Pydantic Settings (.env loader)
|   |   |-- database.py     # Async SQLAlchemy engine + session
|   |   +-- security.py     # JWT encode/decode, password hashing
|   |-- models/             # SQLAlchemy ORM models
|   |   |-- user.py         # User, Subscription
|   |   |-- post.py         # Post, PostResult
|   |   |-- social.py       # SocialConnection
|   |   |-- analytics.py    # PostAnalytics, UserAnalyticsSummary
|   |   |-- content.py      # PostTemplate, ContentSource
|   |   +-- campaign.py     # VideoCampaign, VideoJob
|   |-- schemas/            # Pydantic request/response schemas
|   |-- services/
|   |   |-- ai/             # LLM client, content enhancer, reflector
|   |   |-- platforms/      # Twitter, LinkedIn, YouTube, TikTok adapters
|   |   |-- scheduler/      # APScheduler engine + job definitions
|   |   +-- oauth_service.py
|   |-- dashboard/          # Frontend (HTML, CSS, JS)
|   |   |-- index.html      # Main dashboard
|   |   |-- login.html      # Login page
|   |   |-- routes.py       # HTML page serving
|   |   +-- static/         # CSS design system + JS logic
|   |-- workers/            # Background sync workers
|   +-- main.py             # FastAPI app entrypoint
|-- alembic/                # Database migration scripts
|-- Dockerfile
|-- requirements.txt
|-- logo.png
+-- run.py                  # Dev server launcher
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL database (we use [Neon](https://neon.tech) -- free tier available)
- API keys for the platforms you want to connect

### 1. Clone the repository

```bash
git clone https://github.com/Royweru/kontent-pypper.git
cd kontent-pypper
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate    # Linux/macOS
venv\Scripts\activate       # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root with the following variables:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname

# JWT
SECRET_KEY=your-secret-key

# AI Providers (at least one)
OPENAI_API_KEY=sk-...
GOOGLE_GEMINI_API_KEY=...

# Twitter/X (OAuth 1.0a)
TWITTER_API_KEY=...
TWITTER_API_SECRET=...

# LinkedIn (OAuth 2.0)
LINKEDIN_CLIENT_ID=...
LINKEDIN_CLIENT_SECRET=...

# YouTube / Google (OAuth 2.0)
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...

# TikTok (OAuth 2.0)
TIKTOK_CLIENT_ID=...
TIKTOK_CLIENT_SECRET=...

# Application URLs
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:8000
```

### 5. Run database migrations

```bash
alembic upgrade head
```

### 6. Create your first user

```bash
python create_test_user.py
```

### 7. Start the development server

```bash
python run.py
```

The dashboard will be available at **<http://localhost:8000/dashboard>**

---

## Docker

Build and run with Docker:

```bash
docker build -t kontentpyper .
docker run -p 8000:8000 --env-file .env kontentpyper
```

---

## Deployment (Railway)

1. Push this repository to GitHub.
2. Log in to [Railway](https://railway.app) and create a new project.
3. Select **"Deploy from GitHub Repo"** and choose this repository.
4. Railway will auto-detect the `Dockerfile` and build the image.
5. Add your environment variables in Railway's **Variables** tab.
6. Your app will be live at the generated Railway URL.

---

## Dashboard Preview

The dashboard features a dark charcoal theme with lime-chartreuse and lavender accents. It includes:

- **Overview** -- Stats cards, engagement chart, recent activity feed
- **Studio** -- AI-powered content drafting and enhancement
- **Connections** -- OAuth popup flow for connecting social platforms
- **Schedule** -- Queue posts for future publishing
- **Campaigns** -- Multi-platform campaign management
- **Analytics** -- Per-post metrics and AI-driven performance reflection

The sidebar is **fully collapsible** on desktop and opens as a **slide-in drawer** on mobile devices.

---

## Roadmap

- [x] JWT authentication and secure dashboard
- [x] Multi-platform OAuth (Twitter, LinkedIn, YouTube, TikTok)
- [x] AI content enhancement (OpenAI + Gemini)
- [x] APScheduler for background job execution
- [x] Analytics aggregation and AI reflection
- [x] Responsive collapsible sidebar
- [x] Docker containerization
- [ ] Celery + Redis for production-grade task queues
- [ ] Webhook listeners for real-time platform updates
- [ ] Team/multi-user support
- [ ] Custom content templates marketplace

---

## License

This project is licensed under the MIT License.

---

<p align="center">
  Built with intensity by <a href="https://github.com/Royweru">@Royweru</a>
</p>
