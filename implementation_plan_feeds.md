## News Feed System Upgrade — Implementation Plan

Critical bug:
news.py
 passes source_name=req.title to
ContentSource(...)
 but that model has no source_name column — causing a TypeError on every "Add Feed" click.
No personalization: RSS fetcher uses hardcoded global sources; user-added sources are stored but never used for fetching.
No experience: No logos, no live feed reader, no trending articles, no Reddit integration in the UI.
Goal
Deliver a premium, Buffer-beating News Feed experience that:

Shows a curated catalogue of 65+ feeds and subreddits with logos, organized by niche
Lets users add sources and immediately browse articles from that source
Shows a scrollable trending ticker with real-time headlines
"Create Post from Article" to seed the Studio workflow
Enforces tier limits gracefully (5 feeds + 2 subs free, unlimited Pro)
Feeds the 10x autonomous pipeline from the user's personal sources
User Review Required
IMPORTANT

Alembic migrations will modify the production database schema. Two new columns are added to content_sources (source_name, logo_url, category). Review the migration before applying to production.

WARNING

Reddit API credentials (REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET) must be set in the
.env
 / deployment environment for subreddit browsing and fetching to work. The feature degrades gracefully (hides Reddit tab) if credentials are missing.

NOTE

Real Estate niche is added as a new feed category (user requested). The existing four categories (Tech, Business, News, Entertainment) are preserved. A "Science" and "Art & Media" category are also added for richness.

Proposed Changes
1 — Bug Fix (Unblocks Everything)
[MODIFY]
content.py
Add three columns to
ContentSource
:

python
source_name   = Column(String, nullable=True)   # "TechCrunch", "r/technology"
logo_url      = Column(String, nullable=True)   # CDN favicon URL for UI display
category      = Column(String, nullable=True)   # "tech" | "business" | "news" | ...
[NEW] Alembic Migration add_source_name_logo_category_to_content_sources
bash
alembic revision --autogenerate -m "add_source_name_logo_category_to_content_sources"
alembic upgrade head
[MODIFY]
news.py
Fix
add_feed_source
: pass source_name=req.title — now valid after migration.
Return logo_url, category, source_type in GET /feed/sources.
Extend
AddFeedRequest
 with optional logo_url, category, source_type fields.
Change free-tier count: count RSS AND Reddit separately (5 RSS + 2 subreddits).
Add new endpoints:
GET /news/catalogue — returns full curated catalogue JSON (no auth).
GET /news/feed/preview?url={rss_url} — fetches live top-10 articles from any RSS URL.
GET /news/subreddit/preview?sub={name} — fetches hot posts via PRAW.
2 — Curated Feed Catalogue
[NEW]
app/data/feed_catalogue.py
A Python dict exported as JSON by the /catalogue endpoint. Structure:

python
CATALOGUE = {
  "tech": {
    "rss": [
      { "name": "TechCrunch", "url": "https://techcrunch.com/feed/", "logo": "https://...", "description": "Startup & tech news" },
      { "name": "The Verge", ... },
      { "name": "Wired", ... },
      { "name": "Ars Technica", ... },
      { "name": "VentureBeat", ... },
      { "name": "MIT Technology Review", ... },
      { "name": "Hacker News", ... },
      { "name": "Gizmodo", ... },
    ],
    "reddit": [
      { "name": "r/technology", "sub": "technology", "description": "Tech news & discussion" },
      { "name": "r/MachineLearning", ... },
      { "name": "r/artificial", ... },
      { "name": "r/programming", ... },
    ]
  },
  "business": { "rss": [...8 feeds], "reddit": [...4 subs] },
  "news":        { "rss": [...8 feeds], "reddit": [...4 subs] },
  "entertainment": { "rss": [...8 feeds], "reddit": [...4 subs] },
  "real_estate": { "rss": [...8 feeds], "reddit": [...4 subs] },
  "science":     { "rss": [...8 feeds], "reddit": [...4 subs] },
  "art_media":   { "rss": [...8 feeds], "reddit": [...4 subs] },
}
Logo URLs are sourced from:

<https://logo.clearbit.com/{domain}> (Clearbit Logo API — free, no key required)
Fallback: <https://www.google.com/s2/favicons?sz=64&domain={domain}>
3 — Personalized Feed Ingestion Refactor
[MODIFY]
rss_fetcher.py
python

# New signature accepts a list of ContentSource records for one user

async def fetch_user_rss(sources: List[ContentSource], db: AsyncSession) -> int:
    ...
    # Stores ContentItem with user_id=source.user_id, source_id=source.id
    # Deduplicates by URL per user
Keep the old
fetch_all_rss()
 for the global background job.

[MODIFY]
reddit_fetcher.py
python
async def fetch_user_reddit(sources: List[ContentSource], db: AsyncSession) -> int:
    # Uses source.subreddit_name for user-selected subs
[MODIFY]
daily_pipeline.py
Add a per-user ingest pass: for each user with active sources, call fetch_user_rss + fetch_user_reddit, storing items tagged to that user.

4 — Dashboard UI Overhaul
[MODIFY]
index.html
A) Trending Ticker (top of News Feed section)

A horizontally scrolling animated ticker bar styled in the KontentPyper dark theme (accent color --accent, glass surface) showing the latest 20 headlines from the user's sources. Auto-refreshes every 60 seconds via setInterval. Each chip: source logo circle + headline text + pubDate.

B) Explore Feeds Modal redesign

Replace current simple 3-card grid with:

Category tab bar: All | Tech | Business | News | Entertainment | Real Estate | Science | Art & Media
Two sub-tabs within each: RSS Feeds and Reddit
Feed cards (two-column grid): 64px logo circle, name, description, URL truncated, + Add / Checkmark (if already added), free-tier badge overlay if at limit
Search/filter input at top of modal body
Custom RSS URL input section at bottom (existing, kept)
Free-tier lock: "5/5 RSS feeds used — Upgrade to Pro" banner when at limit
C) Feed Reader Slide-in Panel

Clicking an active source card in "Your Active Feeds" opens a slide-in right panel (400px wide) that:

Loads articles via GET /news/feed/preview?url={rss_url} (or subreddit preview)
Shows: og-image thumbnail (150x100px, fallback placeholder), title (clickable, opens in new tab), snippet (2 lines), pub date, "Create Post" button
"Create Post" pre-fills Studio Modal studioInput with {title}\n\n{snippet}\n\nSource: {url}
Panel title: source logo + source name + "Last refreshed N min ago" + refresh icon
Has its own close button (X)
D) Latest Articles list (bottom of News Feed)

Fetches from GET /api/v1/news/feed filtered to current user. Groups by source. Each item:

Source logo badge (24px circle), headline, snippet (1 line), pub date, "Create Post" pill button
E) Active Feeds grid redesign

Cards styled with: logo (64px), source name, category pill, article count badge, last-fetched timestamp, Remove (trash icon) button. Empty state upgraded with CTA.

F) Tier limit UX

When userSources.rss.length >= 5, all + Add RSS buttons become dimmed with cursor: not-allowed and a tooltip "Upgrade to Pro for unlimited feeds". Same logic for Reddit (limit 2).

[MODIFY]
dashboard.js
New/updated JS functions:

loadCatalogue(category) — fetches /news/catalogue, renders cards into modal
addFeedFromCatalogue(name, url, logo, category, type) — posts to /feed/sources
openFeedReader(source) — fetches preview, renders slide-in panel
loadTicker() — fetches /news/feed, renders ticker HTML
createPostFromArticle(title, snippet, url) — opens Studio Modal pre-filled
loadActiveSources() — renders active feeds grid
checkTierLimit() — disables buttons if at limit
[NEW] Dashboard CSS additions (in dashboard.css or inline)
css
/*Trending Ticker */
.news-ticker { ... marquee animation, glassmorphism ... }
/* Explore Feeds — new card style */
.catalogue-card { logo circle, hover glow border, accent + Add button }
/* Feed Reader Panel */
.feed-reader-panel { position fixed right, slide-in transform animation }
/* Article card in reader*/
.reader-article { thumbnail + text layout, Create Post accent pill }
5 — 10x Pipeline Source Integration
[MODIFY]
index.html
 — #automateFeedsSelection
Replace text toggle list with card-based source selector: logo + name + article count. When user selects sources and clicks "Run Workflow Pipeline", the selected source ids are posted to the workflow endpoint.

Verification Plan
A. Bug Fix Verification (most critical)
Start the dev server: uvicorn app.main:app --reload
Log in at /dashboard/login
Navigate to "News Feed" page
Click "+ Add Feed"
Expected: Modal opens, no 500 error. Add a feed via "Custom RSS URL" input (paste <https://techcrunch.com/feed/>)
Expected: Feed appears in "Your Active Feeds" grid
B. Catalogue Endpoint Test
bash
curl <http://localhost:8000/api/v1/news/catalogue>
Expected: JSON with 7 categories, each with
rss
 and
reddit
 arrays.

C. Feed Preview Endpoint Test
bash
curl "<http://localhost:8000/api/v1/news/feed/preview?url=https://techcrunch.com/feed/>"
Expected: JSON array of 10 articles with title, url, snippet, thumbnail, pub_date.

D. Free Tier Limit Test
Add 5 RSS feeds as a free user.
Try to add a 6th.
Expected: API returns 400 "Free plan limited to 5 feeds". UI shows greyed-out buttons with "Upgrade to Pro" tooltip.
E. Create Post from Article
Open News Feed, click a feed source card.
Feed Reader panel slides in showing articles.
Click "Create Post" on any article.
Expected: Studio Modal opens with studioInput pre-filled with article title + snippet.
F. Reddit Sources
Open Explore Feeds modal, click "Tech" category, click "Reddit" sub-tab.
Add r/technology.
Expected: Source appears in Active Feeds grid with Reddit icon.
Click the subreddit card: Feed Reader shows hot posts.
