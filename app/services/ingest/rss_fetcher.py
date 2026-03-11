"""
KontentPyper - RSS Fetcher
==========================
Two operating modes:

  1. fetch_all_rss()       — global background job, uses hardcoded feeds, no user context.
  2. fetch_user_rss(...)   — personalized; pulls only from a user's saved ContentSource rows.

Both modes return items as dicts. Persistence is handled by the caller (scorer or ingest helpers).
"""
import re
import feedparser
import logging
from datetime import datetime
from time import mktime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# ── Global hardcoded feeds (used by the background daily job) ─────────────────
RSS_SOURCES = [
    {"name": "TechCrunch AI",    "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
    {"name": "Ars Technica AI",  "url": "https://arstechnica.com/ai/feed"},
    {"name": "The Verge AI",     "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"},
    {"name": "VentureBeat AI",   "url": "https://venturebeat.com/category/ai/feed/"},
    {"name": "Wired",            "url": "https://www.wired.com/feed/rss"},
    {"name": "MIT Tech Review",  "url": "https://feeds.technologyreview.com/technology_review"},
    {"name": "Fast Company AI",  "url": "https://www.fastcompany.com/section/artificial-intelligence/rss"},
    {"name": "The Guardian AI",  "url": "https://www.theguardian.com/technology/artificialintelligenceai/rss"},
    {"name": "AI Business",      "url": "https://aibusiness.com/rss.xml"},
    {"name": "OpenAI Blog",      "url": "https://openai.com/blog/rss.xml"},
    {"name": "Hacker News",      "url": "https://news.ycombinator.com/rss"},
]


# ── Shared parse helper ───────────────────────────────────────────────────────

def _parse_feed(
    feed_url: str,
    source_name: str,
    source_type: str = "rss",
    user_id: Optional[int] = None,
    source_id: Optional[int] = None,
    max_entries: int = 5,
) -> List[Dict[str, Any]]:
    """
    Parses a single RSS feed URL and returns a list of normalized item dicts.
    Enriches each dict with user_id and source_id when provided.
    """
    items = []
    try:
        feed = feedparser.parse(feed_url)
        if not feed.entries:
            logger.warning("[RSS Fetcher] No entries found for %s", source_name)
            return items

        for entry in feed.entries[:max_entries]:
            # Published date
            pub_date = datetime.utcnow()
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                pub_date = datetime.fromtimestamp(mktime(entry.published_parsed))

            # Snippet: strip HTML tags from summary
            snippet = ""
            if hasattr(entry, "summary"):
                snippet = re.sub(r"<[^>]+>", "", entry.summary)[:500]

            # og:image / media thumbnail
            image_url = None
            if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
                image_url = entry.media_thumbnail[0].get("url")
            elif hasattr(entry, "media_content") and entry.media_content:
                image_url = entry.media_content[0].get("url")

            items.append({
                "title":          entry.title,
                "url":            entry.link,
                "source_name":    source_name,
                "source_type":    source_type,
                "snippet":        snippet,
                "image_url":      image_url,
                "published_date": pub_date,
                "user_id":        user_id,
                "source_id":      source_id,
            })

    except Exception as exc:
        logger.error("[RSS Fetcher] Error parsing %s (%s): %s", source_name, feed_url, exc)

    return items


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_all_rss() -> List[Dict[str, Any]]:
    """
    Global background job: fetches all hardcoded RSS sources.
    Returns items with user_id=None, source_id=None.
    """
    items = []
    logger.info("[RSS Fetcher] Global fetch from %d sources", len(RSS_SOURCES))
    for source in RSS_SOURCES:
        items.extend(_parse_feed(
            feed_url=source["url"],
            source_name=source["name"],
        ))
    logger.info("[RSS Fetcher] Global fetch complete — %d items", len(items))
    return items


def fetch_user_rss(sources) -> List[Dict[str, Any]]:
    """
    Personalized fetch: pull articles only from a user's saved ContentSource rows.

    Args:
        sources: list of ContentSource ORM objects filtered by user_id and source_type='rss'

    Returns:
        List of normalized item dicts, each tagged with user_id and source_id.
    """
    items = []
    if not sources:
        return items

    logger.info("[RSS Fetcher] Personalized fetch for %d user sources", len(sources))
    for src in sources:
        feed_url = src.rss_feed_url
        if not feed_url:
            continue
        parsed = _parse_feed(
            feed_url=feed_url,
            source_name=src.source_name or feed_url,
            source_type="rss",
            user_id=src.user_id,
            source_id=src.id,
            max_entries=10,   # More articles per user-subscribed feed
        )
        items.extend(parsed)

    logger.info("[RSS Fetcher] Personalized fetch complete — %d items", len(items))
    return items
