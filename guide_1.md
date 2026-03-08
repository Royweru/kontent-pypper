# KontentPyper: Complete System Guide & Codebase Walkthrough

Here is a complete, high-level guide and walkthrough of the **KontentPyper** content automation pipeline, how everything wires together, and how you use it.

---

## 🧠 1. The Autonomous Pipeline (How It Works)

We built an end-to-end "brain" that can essentially run a social media empire without you lifting a finger—except to say "yes" or "no" on Telegram.

Here is the exact lifecycle of the **Daily Pipeline**, which wakes up every morning at **08:00 AM**:

1. **Ingestion (The Eyes & Ears):** The system constantly monitors 12 RSS feeds and 5 subreddits (`rss_fetcher.py`, `reddit_fetcher.py`).
2. **Scoring (The Brain Filter):** It feeds those articles to an AI `scorer.py` which ranks them from 1 to 10 based on how viral they might be for your niche.
3. **Selection & Generation (The Writer):** At 8:00 AM, `daily_pipeline.py` grabs the single highest-scoring, unused story. It passes it to `enhancer.py` (using LangChain and GPT-5-nano), which writes perfectly formatted drafts tailored to the constraints of Twitter, LinkedIn, etc.
4. **Telegram HITL (The Safety Net):** It doesn't post blindly. `telegram_hitl.py` formats those drafts into a beautiful summary card and sends it to your personal Telegram bot with **Approve** and **Reject** buttons.
5. **Publishing (The Megaphone):** If you tap *Approve* (caught by the `webhook/telegram.py`), the script resumes execution and pushes the post out via `social_service.py` to all your connected platforms simultaneously.

---

## 🏗️ 2. Codebase Walkthrough (The Key Files)

Here are the most critical files you should know about if you ever need to debug or extend the system:

* **`app/main.py`**: The entry point. It sets up the FastAPI server, mounts the dashboard HTML/JS, connects the Webhooks (for Telegram), and crucially, turns on the `APScheduler` (the heartbeat of your automation).
* **`app/core/config.py`**: Your `.env` map. If an API key is missing (like `PEXELS_API_KEY` or `TELEGRAM_BOT_TOKEN`), this is where it gets loaded.
* **`app/services/scheduler/jobs.py`**: The "clock". This is where we tell the app to run Analytics every hour, AI Reflection every 7 days, and the `orchestrate_all_users` (Daily Pipeline) at 8:00 AM.
* **`app/services/social_service.py`**: The central switchboard for posting. It talks to the individual platform adapters (like `twitter.py` and `linkedin.py`) and handles the actual HTTP requests to those networks.
* **`app/services/ai/enhancer.py`**: Uses LangChain's structured output. This is where the prompt lives that tells the AI *how* to write for Twitter vs. LinkedIn. If you want to change your brand voice, you edit the `SYSTEM_PROMPT` in this file.
* **`app/services/media/video_composer.py`**: The workhorse for Phase 4. It uses `moviepy` to stitch together downloaded Pexels stock footage, audio, and overlaid karaoke-style text (`caption_animator.py`).

---

## 🎮 3. How to Trigger and Use the System

### Option A: 100% Autonomous (The Daily 8:00 AM Job)

You literally do nothing.

1. Go to **Settings** in the Dashboard and configure your Telegram Bot.
2. Go to **Connections** and connect your X/LinkedIn accounts.
3. Tomorrow at 8:00 AM, your phone will buzz with a Telegram message proposing a post. You click "Approve" and it goes live.

### Option B: Semi-Autonomous (The News Feed Workflow)

1. Open the Dashboard and click **News Feed**.
2. You will see a list of articles curated by the AI, sorted by relevance score.
3. See something cool? Click the **"✎ Write Post"** button on that card.
4. This instantly teleports the article's title and link into your **Studio** tab.
5. Click **"✦ ENHANCE WITH AI"**. The system will draft your specific social posts on the spot.
6. Click **"↑ PUBLISH NOW"**.

### Option C: Creating Your First Video (The Video Pipeline)

*(Note: As of Phase 7, the Video Composer exists perfectly in the backend (`video_composer.py`), but we have not yet wired a specific UI button into the Studio to trigger it. Currently, the Studio handles text + manual media uploads).*

To trigger a video programmatically or as part of a script:

1. You use `script_generator.py` to turn a topic into a `VideoScript` JSON schema (with visual descriptions and narration).
2. You use `pexels_fetcher.py` to download a background video matching the visual description.
3. You pass those to `video_composer.py`'s `generate_final_video()` which uses FFmpeg/ImageMagick to process the 9:16 Tiktok/Shorts ready MP4, complete with auto-pacing karaoke captions.
*(Our next step in a future phase would be adding a "Create Video" tab to the UI that wires into these functions).*

---

## 🧭 4. Quick Dashboard Guide

* **Overview:** Your command center. Shows total posts, remaining limits, and active agent status.
* **Studio:** Where manual creation happens. Type ideas + attach media -> let AI enhance it -> publish to selected networks. The AI Agent chat box acts as your personal copywriter.
* **Connections:** Crucial first step. You *must* OAuth into X, LinkedIn, etc., here for the pipeline to have permission to post.
* **News Feed:** Your personalized feed of trending topics ingested via RSS/Reddit and scored by GPT-4o.
* **Analytics:** Pulls views/likes from platforms. Clicking "Run Analysis" tells the AI to read your past performance and rewrite its own internal strategy rules.
* **Settings:** Where you link your Telegram bot so the Daily Pipeline can send you HITL (Human-in-the-Loop) approval requests.

---
*Created by KontentPyper Agent*
