##News Feed System Upgrade — Task Checklist

## Phase 1 — Bug Fix (Critical, unblock everything)
 Fix source_name TypeError in 
app/api/news.py
 — renamed field now maps to valid ContentSource.source_name column
 Add source_name column to 
ContentSource
 model in 
app/models/content.py
 Add logo_url and 
category
 columns to 
ContentSource
 model (done here, not Phase 2, no drift)
 Write Alembic migration a1b2c3d4e5f6 (revises 9eb226871692) — applied successfully (exit 0)
 Verify migration applied: alembic current shows a1b2c3d4e5f6 (head)

##Phase 2 — Data Layer (Model + API enrichment)
 Add logo_url and 
category
 columns to 
ContentSource
 model (done in Phase 1)
 Add source_type support for 
reddit
 in 
ContentSource
 (subreddit mode)
 Add subreddit_name display field — exposed via API in Phase 1
 Update GET /feed/sources to return logo_url, 
category
, source_type (Phase 1)
 Write Alembic migration for logo_url, 
category
 columns (Phase 1)
 Add free-tier enforcement: 5 RSS feeds + 2 subreddits max (Phase 1)
 Add ContentItem.source_id FK linking fetched items back to the user source
 Add ContentItem.image_url for og:image / Reddit thumbnail
 Remove global URL unique constraint — per-user dedup instead
 Write + apply Alembic migration b2c3d4e5f6a7 (exit 0)

##Phase 3 — Curated Feed Catalogue (Backend)
 Create 
app/data/feed_catalogue.py
 — curated list of RSS feeds + subreddits by niche
Categories: Tech, Business, News, Entertainment, Real Estate, Science, Art & Media
64 RSS feeds (8-9 per category) with verified URLs + Clearbit logo URLs
38 subreddits (4-6 per niche) with descriptions
 Add GET /api/v1/news/catalogue endpoint returning the catalogue (no auth required)
 Add GET /api/v1/news/feed/preview?url=... endpoint (live RSS proxy, returns top 10 articles)
 Add GET /api/v1/news/subreddit/preview?sub=... endpoint (hot posts from any subreddit)
All three endpoints documented with Phase 6 pipeline integration notes

##Phase 4 — Personalized Feed Ingestion
 Refactor 
rss_fetcher.py
: 
fetch_all_rss()
 (global) + 
fetch_user_rss(sources)
 (per-user)
 Refactor 
reddit_fetcher.py
: 
fetch_all_reddit()
 (global) + 
fetch_user_reddit(sources)
 (per-user)
 Add 
personalized_ingest_job()
 to 
jobs.py
 — fans out per-user, every 6 hours
 Store fetched items with correct user_id + source_id (scorer updated)
 Per-user URL dedup in scorer (same URL can exist for different users)

##Phase 5 — Dashboard UI (News Feed Page)
 Trending Ticker — horizontal scrollable marquee bar at top of News Feed page showing latest headlines with source logos + timestamps (auto-refreshes every 60s)
 Explore Feeds Modal redesign — full curated catalogue with category tabs, logo cards, +Add / Remove toggle, search filter box, free-tier badge overlay when limit reached
 Active Feeds grid — show logo, name, category, last-fetched time, article count badge, Remove button
 Feed Reader Panel — clicking an active feed source opens a slide-in panel showing the imported full article list for that source (Buffer-style channel page within the modal)
Shows: thumbnail (og:image or placeholder), title, snippet, pubDate, "Create Post" button, "Open Link" button
 Latest Articles list — filtered to user's active sources, grouped by source, with source logo badge on each card
 Reddit tab in Explore Feeds — curated subreddits with community icon, subscriber count, niche category, +Add toggle
 "Create Post from Article" button on each content item -> opens Studio Modal pre-filled with article title + snippet
 Tier limit UI — when free tier is at limit (5 feeds / 2 subreddits), grey out +Add buttons with "Upgrade to Pro" tooltip
 Niche filter chips at top of active feeds area

##Phase 6 — Autonomous Pipeline Integration
 In the 10x Pipeline automate modal: show user's active feeds as selectable source cards (not just toggle list)
 Show feed logo + name + article count in pipeline source selector
 Pipeline fetches articles from selected sources before running score -> draft -> generate_media

##Verification
 Manual: click "+ Add Feed" -> modal opens without 500 error
 Manual: add TechCrunch from catalogue, see it appear in Active Feeds grid
 Manual: click a feed card, verify slide-in Feed Reader shows live articles
 Manual: click "Create Post" on an article -> Studio Modal opens pre-filled
 Manual: add 5 feeds as free user -> 6th shows upgrade nudge
 Manual: add a Reddit subreddit -> articles appear in Latest Articles with reddit icon