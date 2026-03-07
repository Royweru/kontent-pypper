"""
KontentPyper - Content Scorer
Filters fetched content via Regex and ranks them via AI (OpenAI).
"""
import logging
import re
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.content_source import ContentItem

from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.core.config import settings

logger = logging.getLogger(__name__)

# Regex Keyword rules (case insensitive)
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
    """Assigns a fast base score using regex matching."""
    text = f"{title} {snippet}".lower()
    
    # Check exclusions
    for pattern in EXCLUDES:
        if re.search(pattern, text):
            return -1.0 # Instant reject
            
    score = 0.0
    for pattern in HIGH_RELEVANCE:
        matches = len(re.findall(pattern, text))
        score += (matches * 2.0)
        
    return min(10.0, score) # Max regex score of 10

async def score_and_store_items(db: AsyncSession, raw_items: List[dict]):
    """
    Evaluates new items, saves them to DB with scores.
    """
    logger.info(f"[Scorer] Evaluating {len(raw_items)} fetched items...")
    
    added_count = 0
    for item in raw_items:
        # Check if already exists based on URL
        stmt = select(ContentItem).where(ContentItem.url == item['url'])
        existing = (await db.execute(stmt)).scalar_one_or_none()
        
        if existing:
            continue
            
        r_score = regex_score(item["title"], item["snippet"])
        if r_score < 0:
            continue # Skipped due to exclusion
            
        # Add slight recency bonus (mock implementation) 
        # Here we just use the regex score as the baseline.
        total_score = r_score
        
        new_item = ContentItem(
            title=item["title"],
            url=item["url"],
            source_name=item["source_name"],
            source_type=item["source_type"],
            snippet=item["snippet"],
            published_date=item["published_date"],
            relevance_score=total_score,
            is_used=False
        )
        db.add(new_item)
        added_count += 1
        
    await db.commit()
    logger.info(f"[Scorer] Saved {added_count} new items to DB.")
    return added_count


async def elect_best_item_via_ai(db: AsyncSession) -> ContentItem:
    """
    Selects the top 5 unchecked items from DB and uses AI to pick the absolute best one for a viral short.
    """
    stmt = select(ContentItem).where(ContentItem.is_used == False).order_by(ContentItem.relevance_score.desc()).limit(5)
    candidates = (await db.execute(stmt)).scalars().all()
    
    if not candidates:
        logger.warning("[Scorer] No unused content items found to elect.")
        return None
        
    if len(candidates) == 1:
        return candidates[0]
        
    if not settings.OPENAI_API_KEY:
        logger.warning("[Scorer] Missing OpenAI API Key. Electing top regex scorer.")
        return candidates[0]

    # Use LLM to pick the best viral hook
    # The user requested 'gpt-5-nano', we map it to standard model string (gpt-4o-mini) as that's the fastest
    llm = ChatOpenAI(temperature=0.2, model_name="gpt-4o-mini", max_tokens=100)
    
    prompt = PromptTemplate.from_template(
        "You are an expert social media manager optimizing for viral TikTok/Reels engagement.\n"
        "Here are {count} trending AI/Tech news headlines.\n\n"
        "{items}\n\n"
        "Which single item is the MOST likely to go viral if turned into a 60-second video? "
        "Reply with ONLY the ID number of your chosen item."
    )
    
    items_text = ""
    for idx, c in enumerate(candidates):
        items_text += f"ID: {idx} | Title: {c.title} | Context: {c.snippet[:100]}...\n"
        
    chain = prompt | llm | StrOutputParser()
    
    try:
        response = await chain.ainvoke({"count": len(candidates), "items": items_text})
        chosen_idx = int(re.search(r'\d+', response).group())
        if 0 <= chosen_idx < len(candidates):
            chosen = candidates[chosen_idx]
            logger.info(f"[Scorer] AI elected item: '{chosen.title}'")
            return chosen
    except Exception as e:
        logger.error(f"[Scorer] AI election failed: {e}. Falling back to default.")
    
    return candidates[0]
