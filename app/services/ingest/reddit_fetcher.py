"""
KontentPyper - Reddit Fetcher
==============================
Two operating modes:

  1. fetch_all_reddit()       — global background job, uses hardcoded subreddits, no user context.
  2. fetch_user_reddit(...)   — personalized; pulls only from a user's saved ContentSource rows
                                whose source_type == 'reddit'.

Both modes return normalized item dicts. Persistence is handled by the caller.
"""
import praw
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Global hardcoded subreddits (used by the background daily job) ────────────
SUBREDDITS = [
    "artificial",
    "MachineLearning",
    "technology",
    "singularity",
    "OpenAI",
]


# ── Shared client factory ─────────────────────────────────────────────────────

def get_reddit_client() -> Optional[praw.Reddit]:
    """Initializes and returns a PRAW Reddit instance. Returns None if credentials absent."""
    if not settings.REDDIT_CLIENT_ID or not settings.REDDIT_CLIENT_SECRET:
        logger.warning("[Reddit Fetcher] Missing Reddit API credentials.")
        return None
    try:
        return praw.Reddit(
            client_id=settings.REDDIT_CLIENT_ID,
            client_secret=settings.REDDIT_CLIENT_SECRET,
            user_agent=settings.REDDIT_USER_AGENT,
        )
    except Exception as exc:
        logger.error("[Reddit Fetcher] Failed to initialize PRAW: %s", exc)
        return None


# ── Shared parse helper ───────────────────────────────────────────────────────

def _fetch_subreddit(
    reddit: praw.Reddit,
    sub_name: str,
    source_name: str,
    limit: int = 15,
    user_id: Optional[int] = None,
    source_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Fetches hot posts from a single subreddit and returns normalized item dicts."""
    items = []
    try:
        subreddit = reddit.subreddit(sub_name)
        for submission in subreddit.hot(limit=limit):
            if submission.stickied or not submission.url:
                continue

            # Reddit thumbnail (non-self posts)
            image_url = None
            thumb = getattr(submission, "thumbnail", "")
            if thumb and thumb.startswith("http"):
                image_url = thumb

            items.append({
                "title":          submission.title,
                "url":            submission.url,
                "source_name":    source_name,
                "source_type":    "reddit",
                "snippet":        submission.selftext[:500] if submission.selftext else "",
                "image_url":      image_url,
                "published_date": datetime.fromtimestamp(submission.created_utc),
                "user_id":        user_id,
                "source_id":      source_id,
            })
    except Exception as exc:
        logger.error("[Reddit Fetcher] Error fetching r/%s: %s", sub_name, exc)
    return items


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_all_reddit() -> List[Dict[str, Any]]:
    """
    Global background job: combines all hardcoded subreddits into one hot feed.
    Returns items with user_id=None, source_id=None.
    """
    items = []
    reddit = get_reddit_client()
    if not reddit:
        return items

    logger.info("[Reddit Fetcher] Global fetch from %d subreddits", len(SUBREDDITS))
    try:
        # Combine into a multi-subreddit query (faster than N separate requests)
        query = "+".join(SUBREDDITS)
        subreddit = reddit.subreddit(query)
        for submission in subreddit.hot(limit=15):
            if submission.stickied or not submission.url:
                continue
            image_url = None
            thumb = getattr(submission, "thumbnail", "")
            if thumb and thumb.startswith("http"):
                image_url = thumb

            items.append({
                "title":          submission.title,
                "url":            submission.url,
                "source_name":    f"r/{submission.subreddit.display_name}",
                "source_type":    "reddit",
                "snippet":        submission.selftext[:500] if submission.selftext else "",
                "image_url":      image_url,
                "published_date": datetime.fromtimestamp(submission.created_utc),
                "user_id":        None,
                "source_id":      None,
            })
    except Exception as exc:
        logger.error("[Reddit Fetcher] Global fetch error: %s", exc)

    logger.info("[Reddit Fetcher] Global fetch complete — %d items", len(items))
    return items


def fetch_user_reddit(sources) -> List[Dict[str, Any]]:
    """
    Personalized fetch: pull hot posts only from a user's saved subreddit sources.

    Args:
        sources: list of ContentSource ORM objects where source_type='reddit'

    Returns:
        List of normalized item dicts tagged with user_id and source_id.
    """
    items = []
    if not sources:
        return items

    reddit = get_reddit_client()
    if not reddit:
        logger.warning("[Reddit Fetcher] Skipping personalized fetch — no Reddit credentials.")
        return items

    logger.info("[Reddit Fetcher] Personalized fetch for %d subreddit sources", len(sources))
    for src in sources:
        sub_name = src.subreddit_name
        if not sub_name:
            continue
        parsed = _fetch_subreddit(
            reddit=reddit,
            sub_name=sub_name,
            source_name=src.source_name or f"r/{sub_name}",
            limit=10,
            user_id=src.user_id,
            source_id=src.id,
        )
        items.extend(parsed)

    logger.info("[Reddit Fetcher] Personalized fetch complete — %d items", len(items))
    return items
