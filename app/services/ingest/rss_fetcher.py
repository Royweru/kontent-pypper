"""
KontentPyper - RSS Fetcher
Fetches latest tech and AI news from predefined RSS feeds.
"""
import feedparser
import logging
from datetime import datetime
from time import mktime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

RSS_SOURCES = [
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
    {"name": "Ars Technica AI", "url": "https://arstechnica.com/ai/feed"},
    {"name": "The Verge AI", "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"},
    {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/"},
    {"name": "Wired", "url": "https://www.wired.com/feed/rss"},
    {"name": "MIT Tech Review", "url": "https://feeds.technologyreview.com/technology_review"},
    {"name": "Fast Company AI", "url": "https://www.fastcompany.com/section/artificial-intelligence/rss"},
    {"name": "The Guardian AI", "url": "https://www.theguardian.com/technology/artificialintelligenceai/rss"},
    {"name": "AI Business", "url": "https://aibusiness.com/rss.xml"},
    {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss.xml"},
    {"name": "Hacker News", "url": "https://news.ycombinator.com/rss"},
]

def fetch_all_rss() -> List[Dict[str, Any]]:
    """
    Fetches the latest articles from all configured RSS feeds.
    Returns a list of dictionaries ready to be inserted as ContentItems.
    """
    items = []
    logger.info(f"[RSS Fetcher] Starting fetch from {len(RSS_SOURCES)} sources")
    
    for source in RSS_SOURCES:
        try:
            feed = feedparser.parse(source["url"])
            if not feed.entries:
                logger.warning(f"[RSS Fetcher] No entries found for {source['name']}")
                continue
                
            # Take top 5 from each feed to prevent overload
            for entry in feed.entries[:5]:
                # Extract date if available
                pub_date = datetime.utcnow()
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime.fromtimestamp(mktime(entry.published_parsed))
                
                # Extract summary/snippet
                snippet = ""
                if hasattr(entry, 'summary'):
                    # Basic strip of HTML tags
                    import re
                    snippet = re.sub(r'<[^>]+>', '', entry.summary)[:500] 
                
                items.append({
                    "title": entry.title,
                    "url": entry.link,
                    "source_name": source["name"],
                    "source_type": "rss",
                    "snippet": snippet,
                    "published_date": pub_date
                })
        except Exception as e:
            logger.error(f"[RSS Fetcher] Error fetching {source['name']}: {e}")
            
    logger.info(f"[RSS Fetcher] Successfully fetched {len(items)} RSS items")
    return items
