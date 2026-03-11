"""
KontentPypper - Curated Feed Catalogue
=======================================
Authoritative list of RSS feeds and subreddits organized by niche.

Used by:
  - GET /api/v1/news/catalogue      — Explore Feeds modal (frontend list)
  - personalized_ingest_job()       — seeding user-selected sources
  - 10x Pipeline source selector    — Phase 6 integration

Category slugs (stable identifiers for frontend filtering):
  tech | business | news | entertainment | real_estate | science | art_media

Feed entry schema:
  name        - human-readable label shown in UI
  url         - RSS feed URL (verified working as of 2026-03)
  logo_url    - CDN favicon / icon (clearbit or direct)
  category    - category slug (matches CATEGORIES list)
  source_type - "rss" | "reddit"
  description - short blurb for the modal card
  subreddit   - subreddit name WITHOUT r/ prefix (reddit entries only)
"""
from typing import List, Dict, Any

# ── Category manifest ─────────────────────────────────────────────────────────
CATEGORIES: List[Dict[str, str]] = [
    {"slug": "tech",          "label": "Technology",       "icon": "laptop"},
    {"slug": "business",      "label": "Business",         "icon": "briefcase"},
    {"slug": "news",          "label": "World News",       "icon": "globe"},
    {"slug": "entertainment", "label": "Entertainment",    "icon": "film"},
    {"slug": "real_estate",   "label": "Real Estate",      "icon": "home"},
    {"slug": "science",       "label": "Science",          "icon": "flask"},
    {"slug": "art_media",     "label": "Art & Media",      "icon": "palette"},
]


# ── RSS Feed catalogue ────────────────────────────────────────────────────────
RSS_CATALOGUE: List[Dict[str, Any]] = [
    # ── TECH ──────────────────────────────────────────────────────────────────
    {
        "name": "TechCrunch AI",
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "logo_url": "https://logo.clearbit.com/techcrunch.com",
        "category": "tech",
        "source_type": "rss",
        "description": "Breaking AI news, startup funding rounds, and product launches from Silicon Valley.",
    },
    {
        "name": "Ars Technica",
        "url": "https://arstechnica.com/ai/feed",
        "logo_url": "https://logo.clearbit.com/arstechnica.com",
        "category": "tech",
        "source_type": "rss",
        "description": "Deep-dive technical coverage of AI, hardware, and emerging technology.",
    },
    {
        "name": "The Verge",
        "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "logo_url": "https://logo.clearbit.com/theverge.com",
        "category": "tech",
        "source_type": "rss",
        "description": "Consumer tech, AI products, and the intersection of tech and culture.",
    },
    {
        "name": "VentureBeat AI",
        "url": "https://venturebeat.com/category/ai/feed/",
        "logo_url": "https://logo.clearbit.com/venturebeat.com",
        "category": "tech",
        "source_type": "rss",
        "description": "Enterprise AI, machine learning deployments, and transformative tech coverage.",
    },
    {
        "name": "Wired",
        "url": "https://www.wired.com/feed/rss",
        "logo_url": "https://logo.clearbit.com/wired.com",
        "category": "tech",
        "source_type": "rss",
        "description": "Technology, culture, science, and how the digital world shapes our lives.",
    },
    {
        "name": "MIT Technology Review",
        "url": "https://www.technologyreview.com/feed/",
        "logo_url": "https://logo.clearbit.com/technologyreview.com",
        "category": "tech",
        "source_type": "rss",
        "description": "Independent reporting on emerging technologies from MIT.",
    },
    {
        "name": "OpenAI Blog",
        "url": "https://openai.com/blog/rss.xml",
        "logo_url": "https://logo.clearbit.com/openai.com",
        "category": "tech",
        "source_type": "rss",
        "description": "Official research and product announcements straight from OpenAI.",
    },
    {
        "name": "Hacker News",
        "url": "https://news.ycombinator.com/rss",
        "logo_url": "https://news.ycombinator.com/favicon.ico",
        "category": "tech",
        "source_type": "rss",
        "description": "Top-voted tech and startup discussions from the Y Combinator community.",
    },
    {
        "name": "AI Business",
        "url": "https://aibusiness.com/rss.xml",
        "logo_url": "https://logo.clearbit.com/aibusiness.com",
        "category": "tech",
        "source_type": "rss",
        "description": "Practical AI adoption stories, enterprise case studies, and vendor news.",
    },

    # ── BUSINESS ──────────────────────────────────────────────────────────────
    {
        "name": "Harvard Business Review",
        "url": "https://feeds.hbr.org/harvardbusiness",
        "logo_url": "https://logo.clearbit.com/hbr.org",
        "category": "business",
        "source_type": "rss",
        "description": "Management insights, leadership strategies, and business innovation.",
    },
    {
        "name": "Forbes",
        "url": "https://www.forbes.com/business/feed/",
        "logo_url": "https://logo.clearbit.com/forbes.com",
        "category": "business",
        "source_type": "rss",
        "description": "Business news, entrepreneurship, and Forbes Billionaires coverage.",
    },
    {
        "name": "Fast Company",
        "url": "https://www.fastcompany.com/section/innovation/rss",
        "logo_url": "https://logo.clearbit.com/fastcompany.com",
        "category": "business",
        "source_type": "rss",
        "description": "Innovation in business, design, technology, and creative leadership.",
    },
    {
        "name": "Inc. Magazine",
        "url": "https://www.inc.com/rss.xml",
        "logo_url": "https://logo.clearbit.com/inc.com",
        "category": "business",
        "source_type": "rss",
        "description": "Startup advice, entrepreneur profiles, and small business guidance.",
    },
    {
        "name": "Wall Street Journal",
        "url": "https://feeds.a.dj.com/rss/RSSWSJD.xml",
        "logo_url": "https://logo.clearbit.com/wsj.com",
        "category": "business",
        "source_type": "rss",
        "description": "Authoritative financial news, markets, and business analysis.",
    },
    {
        "name": "Bloomberg Business",
        "url": "https://feeds.bloomberg.com/news/rss",
        "logo_url": "https://logo.clearbit.com/bloomberg.com",
        "category": "business",
        "source_type": "rss",
        "description": "Global finance, markets, economics, and corporate strategy.",
    },
    {
        "name": "Entrepreneur",
        "url": "https://www.entrepreneur.com/latest.rss",
        "logo_url": "https://logo.clearbit.com/entrepreneur.com",
        "category": "business",
        "source_type": "rss",
        "description": "Business tips, entrepreneurship guides, and startup success stories.",
    },
    {
        "name": "Morning Brew",
        "url": "https://www.morningbrew.com/rss/daily",
        "logo_url": "https://logo.clearbit.com/morningbrew.com",
        "category": "business",
        "source_type": "rss",
        "description": "Daily briefing on business, finance, and tech written for modern professionals.",
    },

    # ── WORLD NEWS ────────────────────────────────────────────────────────────
    {
        "name": "BBC News",
        "url": "https://feeds.bbci.co.uk/news/rss.xml",
        "logo_url": "https://logo.clearbit.com/bbc.com",
        "category": "news",
        "source_type": "rss",
        "description": "Balanced, authoritative world news and analysis from the BBC.",
    },
    {
        "name": "Reuters",
        "url": "https://feeds.reuters.com/reuters/topNews",
        "logo_url": "https://logo.clearbit.com/reuters.com",
        "category": "news",
        "source_type": "rss",
        "description": "Breaking wire news from Reuters correspondents around the globe.",
    },
    {
        "name": "The Guardian",
        "url": "https://www.theguardian.com/world/rss",
        "logo_url": "https://logo.clearbit.com/theguardian.com",
        "category": "news",
        "source_type": "rss",
        "description": "Progressive world news, investigation, and long-form journalism.",
    },
    {
        "name": "NPR News",
        "url": "https://feeds.npr.org/1001/rss.xml",
        "logo_url": "https://logo.clearbit.com/npr.org",
        "category": "news",
        "source_type": "rss",
        "description": "Impartial US and world news from National Public Radio.",
    },
    {
        "name": "Al Jazeera English",
        "url": "https://www.aljazeera.com/xml/rss/all.xml",
        "logo_url": "https://logo.clearbit.com/aljazeera.com",
        "category": "news",
        "source_type": "rss",
        "description": "Global news with an emphasis on underreported regions and perspectives.",
    },
    {
        "name": "Associated Press",
        "url": "https://rsshub.app/apnews/topics/apf-topnews",
        "logo_url": "https://logo.clearbit.com/apnews.com",
        "category": "news",
        "source_type": "rss",
        "description": "Trusted wire reporting from AP correspondents worldwide.",
    },
    {
        "name": "The Economist",
        "url": "https://www.economist.com/latest/rss.xml",
        "logo_url": "https://logo.clearbit.com/economist.com",
        "category": "news",
        "source_type": "rss",
        "description": "In-depth analysis of global politics, economics, and society.",
    },
    {
        "name": "Axios",
        "url": "https://api.axios.com/feed/",
        "logo_url": "https://logo.clearbit.com/axios.com",
        "category": "news",
        "source_type": "rss",
        "description": "Smart-brevity news briefings on politics, business, and tech.",
    },

    # ── ENTERTAINMENT ─────────────────────────────────────────────────────────
    {
        "name": "Variety",
        "url": "https://variety.com/feed/",
        "logo_url": "https://logo.clearbit.com/variety.com",
        "category": "entertainment",
        "source_type": "rss",
        "description": "Hollywood box office, streaming wars, and music industry news.",
    },
    {
        "name": "Deadline Hollywood",
        "url": "https://deadline.com/feed/",
        "logo_url": "https://logo.clearbit.com/deadline.com",
        "category": "entertainment",
        "source_type": "rss",
        "description": "Breaking film, TV, and streaming industry deals and casting news.",
    },
    {
        "name": "Billboard",
        "url": "https://www.billboard.com/feed/",
        "logo_url": "https://logo.clearbit.com/billboard.com",
        "category": "entertainment",
        "source_type": "rss",
        "description": "Music charts, artist interviews, and industry data.",
    },
    {
        "name": "The Hollywood Reporter",
        "url": "https://www.hollywoodreporter.com/feed/",
        "logo_url": "https://logo.clearbit.com/hollywoodreporter.com",
        "category": "entertainment",
        "source_type": "rss",
        "description": "Film reviews, TV recaps, and entertainment business reporting.",
    },
    {
        "name": "IGN",
        "url": "https://feeds.feedburner.com/ign/games-all",
        "logo_url": "https://logo.clearbit.com/ign.com",
        "category": "entertainment",
        "source_type": "rss",
        "description": "Video game reviews, trailers, and gaming culture.",
    },
    {
        "name": "Rolling Stone",
        "url": "https://www.rollingstone.com/feed/",
        "logo_url": "https://logo.clearbit.com/rollingstone.com",
        "category": "entertainment",
        "source_type": "rss",
        "description": "Music, pop culture, politics, and counter-culture journalism.",
    },
    {
        "name": "Entertainment Weekly",
        "url": "https://ew.com/rss/",
        "logo_url": "https://logo.clearbit.com/ew.com",
        "category": "entertainment",
        "source_type": "rss",
        "description": "TV, movies, music, and books coverage for pop-culture fans.",
    },
    {
        "name": "Pitchfork",
        "url": "https://pitchfork.com/rss/news/",
        "logo_url": "https://logo.clearbit.com/pitchfork.com",
        "category": "entertainment",
        "source_type": "rss",
        "description": "Indie music reviews, albums, and artist profiles.",
    },

    # ── REAL ESTATE ───────────────────────────────────────────────────────────
    {
        "name": "Inman Real Estate",
        "url": "https://www.inman.com/feed/",
        "logo_url": "https://logo.clearbit.com/inman.com",
        "category": "real_estate",
        "source_type": "rss",
        "description": "Real estate industry news, agent strategies, and market analysis.",
    },
    {
        "name": "Zillow Research",
        "url": "https://www.zillow.com/blog/feed/",
        "logo_inman": "https://logo.clearbit.com/zillow.com",
        "logo_url": "https://logo.clearbit.com/zillow.com",
        "category": "real_estate",
        "source_type": "rss",
        "description": "Housing market data, pricing trends, and buyer/seller guides.",
    },
    {
        "name": "RealtyTimes",
        "url": "https://realtytimes.com/feed.xml",
        "logo_url": "https://logo.clearbit.com/realtytimes.com",
        "category": "real_estate",
        "source_type": "rss",
        "description": "News, tips, and market data for real estate agents and investors.",
    },
    {
        "name": "HousingWire",
        "url": "https://www.housingwire.com/feed/",
        "logo_url": "https://logo.clearbit.com/housingwire.com",
        "category": "real_estate",
        "source_type": "rss",
        "description": "Mortgage, lending, and residential real estate industry coverage.",
    },
    {
        "name": "Big Real Estate Agent",
        "url": "https://www.biggerpockets.com/blog/feed",
        "logo_url": "https://logo.clearbit.com/biggerpockets.com",
        "category": "real_estate",
        "source_type": "rss",
        "description": "Real estate investing strategies, deal analysis, and wealth building.",
    },
    {
        "name": "National Association of Realtors",
        "url": "https://www.nar.realtor/rss.asmx/news",
        "logo_url": "https://logo.clearbit.com/nar.realtor",
        "category": "real_estate",
        "source_type": "rss",
        "description": "Official statistics, legal updates, and advocacy from NAR.",
    },
    {
        "name": "Commercial Observer",
        "url": "https://commercialobserver.com/feed/",
        "logo_url": "https://logo.clearbit.com/commercialobserver.com",
        "category": "real_estate",
        "source_type": "rss",
        "description": "Commercial real estate deals, CMBS, and NYC property market.",
    },
    {
        "name": "Curbed",
        "url": "https://www.curbed.com/rss/index.xml",
        "logo_url": "https://logo.clearbit.com/curbed.com",
        "category": "real_estate",
        "source_type": "rss",
        "description": "Home design, urban living, architecture, and neighborhood stories.",
    },

    # ── SCIENCE ───────────────────────────────────────────────────────────────
    {
        "name": "Nature",
        "url": "https://www.nature.com/nature.rss",
        "logo_url": "https://logo.clearbit.com/nature.com",
        "category": "science",
        "source_type": "rss",
        "description": "Peer-reviewed research breakthroughs from the world's top journal.",
    },
    {
        "name": "Science Daily",
        "url": "https://www.sciencedaily.com/rss/all.xml",
        "logo_url": "https://logo.clearbit.com/sciencedaily.com",
        "category": "science",
        "source_type": "rss",
        "description": "Accessible summaries of the latest scientific research.",
    },
    {
        "name": "NASA Breaking News",
        "url": "https://www.nasa.gov/rss/dyn/breaking_news.rss",
        "logo_url": "https://logo.clearbit.com/nasa.gov",
        "category": "science",
        "source_type": "rss",
        "description": "Space exploration missions, discoveries, and NASA announcements.",
    },
    {
        "name": "New Scientist",
        "url": "https://www.newscientist.com/feed/home/?cmpid=RSS|NSNS|2012-GLOBAL|home",
        "logo_url": "https://logo.clearbit.com/newscientist.com",
        "category": "science",
        "source_type": "rss",
        "description": "Engaging science news spanning physics, biology, climate, and space.",
    },
    {
        "name": "Scientific American",
        "url": "https://rss.sciam.com/ScientificAmerican-Global",
        "logo_url": "https://logo.clearbit.com/scientificamerican.com",
        "category": "science",
        "source_type": "rss",
        "description": "Expert science journalism and deep dives into research frontiers.",
    },
    {
        "name": "Physics Today",
        "url": "https://physicstoday.scitation.org/rss/site_5/36.xml",
        "logo_url": "https://logo.clearbit.com/physicstoday.org",
        "category": "science",
        "source_type": "rss",
        "description": "Cutting-edge physics research, opinion, and history of science.",
    },
    {
        "name": "EurekAlert! Science News",
        "url": "https://www.eurekalert.org/rss.xml",
        "logo_url": "https://logo.clearbit.com/eurekalert.org",
        "category": "science",
        "source_type": "rss",
        "description": "Press releases and research news from universities worldwide.",
    },
    {
        "name": "The Scientist",
        "url": "https://www.the-scientist.com/rss",
        "logo_url": "https://logo.clearbit.com/the-scientist.com",
        "category": "science",
        "source_type": "rss",
        "description": "Life sciences and biomedical research news for working scientists.",
    },

    # ── ART & MEDIA ───────────────────────────────────────────────────────────
    {
        "name": "Artsy Editorial",
        "url": "https://www.artsy.net/rss/news",
        "logo_url": "https://logo.clearbit.com/artsy.net",
        "category": "art_media",
        "source_type": "rss",
        "description": "Art market news, artist spotlights, and gallery/auction coverage.",
    },
    {
        "name": "Hyperallergic",
        "url": "https://hyperallergic.com/feed/",
        "logo_url": "https://logo.clearbit.com/hyperallergic.com",
        "category": "art_media",
        "source_type": "rss",
        "description": "Critical art writing, reviews, and contemporary cultural commentary.",
    },
    {
        "name": "Creative Bloq",
        "url": "https://www.creativebloq.com/rss",
        "logo_url": "https://logo.clearbit.com/creativebloq.com",
        "category": "art_media",
        "source_type": "rss",
        "description": "Design inspiration, tutorials, and digital art trends.",
    },
    {
        "name": "The Drum",
        "url": "https://www.thedrum.com/rss",
        "logo_url": "https://logo.clearbit.com/thedrum.com",
        "category": "art_media",
        "source_type": "rss",
        "description": "Marketing, advertising, and media industry news and campaigns.",
    },
    {
        "name": "AIGA Eye on Design",
        "url": "https://eyeondesign.aiga.org/feed/",
        "logo_url": "https://logo.clearbit.com/aiga.org",
        "category": "art_media",
        "source_type": "rss",
        "description": "Graphic design, typography, and visual communication culture.",
    },
    {
        "name": "Colossal",
        "url": "https://www.thisiscolossal.com/feed/",
        "logo_url": "https://logo.clearbit.com/thisiscolossal.com",
        "category": "art_media",
        "source_type": "rss",
        "description": "Jaw-dropping art, photography, crafts, and design from around the world.",
    },
    {
        "name": "Dezeen",
        "url": "https://feeds.feedburner.com/dezeen",
        "logo_url": "https://logo.clearbit.com/dezeen.com",
        "category": "art_media",
        "source_type": "rss",
        "description": "Architecture, interior design, and product design news.",
    },
    {
        "name": "Frieze",
        "url": "https://www.frieze.com/rss.xml",
        "logo_url": "https://logo.clearbit.com/frieze.com",
        "category": "art_media",
        "source_type": "rss",
        "description": "Contemporary art, culture, and the global gallery circuit.",
    },
]


# ── Subreddit catalogue ───────────────────────────────────────────────────────
SUBREDDIT_CATALOGUE: List[Dict[str, Any]] = [
    # TECH
    {"name": "r/artificial",        "subreddit": "artificial",        "category": "tech",          "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "AI research, demos, and debate for the general public."},
    {"name": "r/MachineLearning",   "subreddit": "MachineLearning",   "category": "tech",          "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "Latest ML papers, implementations, and research discussions."},
    {"name": "r/technology",        "subreddit": "technology",        "category": "tech",          "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "General technology news, trends, and discussion."},
    {"name": "r/singularity",       "subreddit": "singularity",       "category": "tech",          "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "Technological acceleration, AGI, and exponential change."},
    {"name": "r/OpenAI",            "subreddit": "OpenAI",            "category": "tech",          "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "Community news, demos, and discussion around OpenAI products."},
    {"name": "r/LocalLLaMA",        "subreddit": "LocalLLaMA",        "category": "tech",          "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "Running large language models locally — guides and benchmarks."},

    # BUSINESS
    {"name": "r/Entrepreneur",      "subreddit": "Entrepreneur",      "category": "business",      "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "Startup journeys, business advice, and entrepreneur AMAs."},
    {"name": "r/smallbusiness",     "subreddit": "smallbusiness",     "category": "business",      "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "Support community for small business owners."},
    {"name": "r/startups",          "subreddit": "startups",          "category": "business",      "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "Startup funding, pivots, launches, and founder stories."},
    {"name": "r/finance",           "subreddit": "finance",           "category": "business",      "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "Personal finance, investing, and macroeconomics."},
    {"name": "r/investing",         "subreddit": "investing",         "category": "business",      "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "Stock market, ETFs, bonds, and long-term wealth building."},
    {"name": "r/SideProject",       "subreddit": "SideProject",       "category": "business",      "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "Share and discover indie side projects and micro-SaaS."},

    # WORLD NEWS
    {"name": "r/worldnews",         "subreddit": "worldnews",         "category": "news",          "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "Major international news events and breaking stories."},
    {"name": "r/news",              "subreddit": "news",              "category": "news",          "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "US and national news filtered for quality sourcing."},
    {"name": "r/UpliftingNews",     "subreddit": "UpliftingNews",     "category": "news",          "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "Positive and heartwarming news stories from around the world."},
    {"name": "r/geopolitics",       "subreddit": "geopolitics",       "category": "news",          "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "International relations, foreign policy, and global affairs."},

    # ENTERTAINMENT
    {"name": "r/movies",            "subreddit": "movies",            "category": "entertainment", "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "Film news, reviews, trailers, and box office discussion."},
    {"name": "r/television",        "subreddit": "television",        "category": "entertainment", "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "TV shows, streaming series, and viewer reactions."},
    {"name": "r/Music",             "subreddit": "Music",             "category": "entertainment", "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "Music discovery, news, and discussion across all genres."},
    {"name": "r/gaming",            "subreddit": "gaming",            "category": "entertainment", "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "Video game culture, news, and casual gaming discussion."},
    {"name": "r/NetflixBestOf",     "subreddit": "NetflixBestOf",     "category": "entertainment", "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "Community picks for best Netflix content."},
    {"name": "r/popculturechat",    "subreddit": "popculturechat",    "category": "entertainment", "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "Celebrity gossip, fandom, and pop culture commentary."},

    # REAL ESTATE
    {"name": "r/RealEstate",        "subreddit": "RealEstate",        "category": "real_estate",   "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "Buying, selling, investing, and renting property discussions."},
    {"name": "r/realestateinvesting","subreddit": "realestateinvesting","category": "real_estate",  "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "Rental properties, REITs, flipping, and passive income strategies."},
    {"name": "r/FirstTimeHomeBuyer","subreddit": "FirstTimeHomeBuyer","category": "real_estate",   "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "Guidance, questions, and experiences for first-time home buyers."},
    {"name": "r/HousingMarket",     "subreddit": "HousingMarket",     "category": "real_estate",   "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "Housing price trends, mortgage rates, and market predictions."},

    # SCIENCE
    {"name": "r/science",           "subreddit": "science",           "category": "science",       "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "Peer-reviewed science news moderated by experts."},
    {"name": "r/space",             "subreddit": "space",             "category": "science",       "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "Astronomy, space exploration, and the cosmos."},
    {"name": "r/biology",           "subreddit": "biology",           "category": "science",       "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "Life sciences, genetics, ecology, and biological discoveries."},
    {"name": "r/Physics",           "subreddit": "Physics",           "category": "science",       "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "Physics news, Q&A, and research paper discussion."},
    {"name": "r/Futurology",        "subreddit": "Futurology",        "category": "science",       "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "Science-based speculation about future technology and society."},
    {"name": "r/chemistry",         "subreddit": "chemistry",         "category": "science",       "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "Chemistry research, reactions, and lab science discussion."},

    # ART & MEDIA
    {"name": "r/Art",               "subreddit": "Art",               "category": "art_media",     "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "Fine art, digital art, paintings, sculptures, and photography."},
    {"name": "r/DigitalArt",        "subreddit": "DigitalArt",        "category": "art_media",     "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "Concept art, illustration, and AI-generated visual art."},
    {"name": "r/graphic_design",    "subreddit": "graphic_design",    "category": "art_media",     "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "Typography, branding, layout, and commercial design showcases."},
    {"name": "r/photography",       "subreddit": "photography",       "category": "art_media",     "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "Photography techniques, gear discussions, and photo critiques."},
    {"name": "r/advertising",       "subreddit": "advertising",       "category": "art_media",     "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "Ad campaigns, marketing creativity, and media strategy."},
    {"name": "r/WeAreTheMusicMakers","subreddit": "WeAreTheMusicMakers","category": "art_media",   "source_type": "reddit", "logo_url": "https://www.redditstatic.com/desktop2x/img/snoo_discovery@1x.png", "description": "Music production, beatmaking, and sound design."},
]


# ── Helper — used by /catalogue endpoint ─────────────────────────────────────

def get_full_catalogue() -> Dict[str, Any]:
    """
    Returns the full catalogue structured for the frontend Explore Feeds modal.

    Returns a dict with:
      categories: list of {slug, label, icon}
      rss:        list of all RSS feed entries
      reddit:     list of all subreddit entries

    The frontend can filter by category slug on client side for speed.
    """
    return {
        "categories": CATEGORIES,
        "rss": RSS_CATALOGUE,
        "subreddits": SUBREDDIT_CATALOGUE,
    }


def get_catalogue_by_category(category: str) -> Dict[str, Any]:
    """Returns feeds filtered to a single category slug."""
    return {
        "category": category,
        "rss": [f for f in RSS_CATALOGUE if f["category"] == category],
        "subreddits": [s for s in SUBREDDIT_CATALOGUE if s["category"] == category],
    }
