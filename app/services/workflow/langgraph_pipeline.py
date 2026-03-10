import logging
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from app.models.user import User
from app.services.ingest.rss_fetcher import fetch_all_rss
from app.services.ai.script_generator import generate_video_script
from app.services.ai.llm_client import LLMClient
from app.core.config import settings

logger = logging.getLogger(__name__)

# ── State Definition ───────────────────────────────────────────────────
class WorkflowState(TypedDict):
    user_id: int
    niche: Optional[str]
    articles: List[Dict[str, Any]]
    selected_article: Optional[Dict[str, Any]]
    scripts: Dict[str, str] # platform -> script
    video_asset: Optional[str]
    status: str

# ── Nodes ─────────────────────────────────────────────────────────────
async def fetch_node(state: WorkflowState):
    """Fetch latest articles from configured RSS feeds."""
    state["status"] = "Fetching articles..."
    # In a full impl, we'd fetch based on user's selected feeds from ContentSource
    # For now, we use the global rss fetcher strategy.
    articles = fetch_all_rss()
    state["articles"] = articles
    return state

async def score_node(state: WorkflowState):
    """Score articles based on relevance to the user's niche."""
    state["status"] = "Scoring articles for relevance..."
    articles = state.get("articles", [])
    niche = state.get("niche", "Technology and AI")
    
    if not articles:
        return state
        
    client = LLMClient(api_key=settings.OPENAI_API_KEY, model="gpt-5-nano")
    
    best_article = None
    best_score = -1
    
    for article in articles[:5]: # Score top 5 to save time/tokens
        prompt = f"Score this article from 1 to 10 on how relevant it is to the niche: '{niche}'. Return ONLY the integer score.\nTitle: {article['title']}\Snippet: {article['snippet']}"
        try:
            res = await client.generate_text("You are an expert news curator.", prompt)
            score = int(res.strip())
        except:
            score = 5
            
        if score > best_score:
            best_score = score
            best_article = article
            
    state["selected_article"] = best_article or articles[0]
    return state

async def draft_node(state: WorkflowState):
    """Draft content for different platforms."""
    state["status"] = "Drafting captions and scripts..."
    article = state.get("selected_article")
    
    if not article:
        return state
        
    client = LLMClient(api_key=settings.OPENAI_API_KEY, model="gpt-5-nano")
    
    platforms = ["twitter", "linkedin"]
    scripts = {}
    
    for platform in platforms:
        prompt = f"Write a compelling {platform} post based on this article. Keep it professional and engaging.\n\nTitle: {article['title']}\Snippet: {article['snippet']}"
        try:
            res = await client.generate_text("You are an expert social media manager.", prompt)
            scripts[platform] = res
        except Exception as e:
            logger.error(f"Failed to draft for {platform}: {e}")
            
    state["scripts"] = scripts
    return state

async def generate_media_node(state: WorkflowState):
    """Generate media (video) based on user tier."""
    state["status"] = "Generating media assets..."
    article = state.get("selected_article")
    
    if article:
        try:
            # We generate the video script from our existing generator
            video_script = await generate_video_script(article['title'], article.get('snippet', ''), article['source_name'])
            # Since we are combining free and pro video gen, we mock the result string for now
            # where actual video composition would happen via video_composer.py
            state["video_asset"] = "https://www.w3schools.com/html/mov_bbb.mp4" 
        except Exception as e:
            logger.error(f"Failed to generate video script or media: {e}")
            
    state["status"] = "Workflow complete"
    return state

# ── Wire Graph ────────────────────────────────────────────────────────
def build_graph():
    workflow = StateGraph(WorkflowState)
    
    workflow.add_node("fetch", fetch_node)
    workflow.add_node("score", score_node)
    workflow.add_node("draft", draft_node)
    workflow.add_node("generate_media", generate_media_node)
    
    workflow.set_entry_point("fetch")
    workflow.add_edge("fetch", "score")
    workflow.add_edge("score", "draft")
    workflow.add_edge("draft", "generate_media")
    workflow.add_edge("generate_media", END)
    
    return workflow.compile()

langgraph_pipeline = build_graph()
