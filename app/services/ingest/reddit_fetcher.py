"""
KontentPyper - Reddit Fetcher
Fetches latest tech and AI news from predefined subreddits using PRAW.
"""
import praw
import logging
from datetime import datetime
from typing import List, Dict, Any

from app.core.config import settings

logger = logging.getLogger(__name__)

SUBREDDITS = [
    "artificial",
    "MachineLearning",
    "technology",
    "singularity",
    "OpenAI",
]

def get_reddit_client():
    """Initializes and returns a PRAW Reddit instance safely."""
    if not settings.REDDIT_CLIENT_ID or not settings.REDDIT_CLIENT_SECRET:
        logger.warning("[Reddit Fetcher] Missing Reddit API credentials in config.")
        return None
        
    try:
        reddit = praw.Reddit(
            client_id=settings.REDDIT_CLIENT_ID,
            client_secret=settings.REDDIT_CLIENT_SECRET,
            user_agent=settings.REDDIT_USER_AGENT
        )
        return reddit
    except Exception as e:
        logger.error(f"[Reddit Fetcher] Failed to initialize PRAW: {e}")
        return None

def fetch_all_reddit() -> List[Dict[str, Any]]:
    """
    Fetches the top "hot" posts from today for configured subreddits.
    Returns a list of dictionaries ready to be inserted as ContentItems.
    """
    items = []
    reddit = get_reddit_client()
    
    if not reddit:
        return items
        
    logger.info(f"[Reddit Fetcher] Starting fetch from {len(SUBREDDITS)} subreddits")    
    
    try:
        # Combine subreddits into one query string: "artificial+MachineLearning+..."
        query = "+".join(SUBREDDITS)
        subreddit = reddit.subreddit(query)
        
        # Get top 15 hot posts
        for submission in subreddit.hot(limit=15):
            # Skip stickied mod posts or self-promotion
            if submission.stickied or not submission.url:
                continue
                
            pub_date = datetime.fromtimestamp(submission.created_utc)
            
            items.append({
                "title": submission.title,
                "url": submission.url,
                "source_name": f"r/{submission.subreddit.display_name}",
                "source_type": "reddit",
                "snippet": submission.selftext[:500] if submission.selftext else "",
                "published_date": pub_date
            })
            
    except Exception as e:
        logger.error(f"[Reddit Fetcher] Error fetching Reddit posts: {e}")
        
    logger.info(f"[Reddit Fetcher] Successfully fetched {len(items)} Reddit items")
    return items
