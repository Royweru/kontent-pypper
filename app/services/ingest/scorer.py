"""
KontentPyper - Content Scorer
==============================
Filters and ranks fetched content items.

Two public entry points:

  score_and_store_items(db, raw_items)
    Accepts a list of item dicts (as returned by rss_fetcher / reddit_fetcher)
    and persists them with their computed relevance scores.
    - Dedup is per-user: the same URL may be stored for multiple users.
    - Each item dict MUST include user_id, source_id (can be None for global feed).

  elect_best_item_via_ai(db, user_id?)
    Picks the best unused item for a given user (or globally) via regex scoring
    + optional LLM tie-breaker.
"""
import logging
import re
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.content_source import ContentItem
from app.core.config import settings

logger = logging.getLogger(__name__)


# ── Regex rule sets ───────────────────────────────────────────────────────────
# NOTE: These are unchanged from the original implementation.

HIGH_RELEVANCE = [
    r'\bgpt-[45o]\w*\b',
    r'\bclaude\b',
    r'\bgemini\b',
    r'\bllm\b',
    r'\bai (?:agent|model|tool|startup|video)\b',
    r'\bbreakthrough\b',
    r'\bopenai\b',
    r'\banthropic\b',
    r'\bgenerative ai\b',
    r'\bmultimodal\b',
]

EXCLUDES = [
    r'\bpolitics\b',
    r'\bsports\b',
    r'\bcelebrity\b',
]


def regex_score(title: str, snippet: str) -> float:
    """Fast base score via regex pattern matching. Returns -1.0 for excluded content."""
    text = f"{title} {snippet}".lower()
    for pattern in EXCLUDES:
        if re.search(pattern, text):
            return -1.0  # Instant reject
    score = 0.0
    for pattern in HIGH_RELEVANCE:
        matches = len(re.findall(pattern, text))
        score += matches * 2.0
    return min(10.0, score)


# ── Main store function ───────────────────────────────────────────────────────

async def score_and_store_items(
    db: AsyncSession,
    raw_items: List[dict],
) -> int:
    """
    Evaluates, deduplicates, and persists new content items.

    Dedup strategy:
      - For user-scoped items (user_id != None): skip if (url, user_id) already exists.
      - For global items (user_id = None): skip if url already exists without a user_id.

    Args:
        db:        async SQLAlchemy session
        raw_items: list of dicts from rss_fetcher / reddit_fetcher. Expected keys:
                   title, url, source_name, source_type, snippet, image_url,
                   published_date, user_id, source_id.

    Returns: number of newly stored items.
    """
    logger.info("[Scorer] Evaluating %d fetched items...", len(raw_items))
    added_count = 0

    for item in raw_items:
        url = item.get("url")
        user_id = item.get("user_id")
        if not url:
            continue

        # Dedup query
        stmt = select(ContentItem).where(ContentItem.url == url)
        if user_id is not None:
            stmt = stmt.where(ContentItem.user_id == user_id)
        else:
            stmt = stmt.where(ContentItem.user_id.is_(None))

        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            continue

        # Relevance scoring
        r_score = regex_score(
            item.get("title", ""),
            item.get("snippet", ""),
        )
        if r_score < 0:
            continue  # Excluded by EXCLUDES patterns

        new_item = ContentItem(
            title=item["title"],
            url=url,
            source_name=item.get("source_name", ""),
            source_type=item.get("source_type", "rss"),
            snippet=item.get("snippet", ""),
            image_url=item.get("image_url"),
            published_date=item.get("published_date"),
            relevance_score=r_score,
            is_used=False,
            user_id=user_id,
            source_id=item.get("source_id"),
        )
        db.add(new_item)
        added_count += 1

    if added_count:
        await db.commit()

    logger.info("[Scorer] Saved %d new items to DB.", added_count)
    return added_count


# ── AI election ───────────────────────────────────────────────────────────────

async def elect_best_item_via_ai(
    db: AsyncSession,
    user_id: Optional[int] = None,
) -> Optional[ContentItem]:
    """
    Selects the top 5 candidates for a user (or globally) and uses the LLM
    to pick the most viral-potential item.

    Args:
        db:      async SQLAlchemy session
        user_id: if provided, restrict candidates to that user's items.
                 If None, draw from the global pool (user_id IS NULL).
    """
    stmt = (
        select(ContentItem)
        .where(ContentItem.is_used == False)
        .order_by(ContentItem.relevance_score.desc())
        .limit(5)
    )
    if user_id is not None:
        stmt = stmt.where(ContentItem.user_id == user_id)
    else:
        stmt = stmt.where(ContentItem.user_id.is_(None))

    candidates = (await db.execute(stmt)).scalars().all()

    if not candidates:
        logger.warning("[Scorer] No unused content items found (user_id=%s).", user_id)
        return None

    if len(candidates) == 1 or not settings.OPENAI_API_KEY:
        return candidates[0]

    try:
        from langchain_openai import ChatOpenAI
        from langchain.prompts import PromptTemplate
        from langchain_core.output_parsers import StrOutputParser

        llm = ChatOpenAI(temperature=0.2, model_name="gpt-4o-mini", max_tokens=100)
        prompt = PromptTemplate.from_template(
            "You are an expert social media manager optimizing for viral TikTok/Reels engagement.\n"
            "Here are {count} trending AI/Tech news headlines.\n\n"
            "{items}\n\n"
            "Which single item is the MOST likely to go viral if turned into a 60-second video? "
            "Reply with ONLY the ID number of your chosen item."
        )
        items_text = "".join(
            f"ID: {i} | Title: {c.title} | Context: {(c.snippet or '')[:100]}...\n"
            for i, c in enumerate(candidates)
        )
        chain = prompt | llm | StrOutputParser()
        response = await chain.ainvoke({"count": len(candidates), "items": items_text})
        chosen_idx = int(re.search(r'\d+', response).group())
        if 0 <= chosen_idx < len(candidates):
            chosen = candidates[chosen_idx]
            logger.info("[Scorer] AI elected: '%s'", chosen.title)
            return chosen
    except Exception as exc:
        logger.error("[Scorer] AI election failed: %s. Falling back to top scorer.", exc)

    return candidates[0]
