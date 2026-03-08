"""
KontentPyper - Studio API Router
Connects the frontend Mini Studio to the LangChain-backed AI Enhancer and Social Service.
"""

from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import CurrentUser, DB
from app.services.ai.enhancer import EnhancerService
from app.services.ai.llm_client import LLMClient
from app.services.social_service import SocialService
from app.core.config import settings

router = APIRouter()

# Instantiate services once at module level (singleton pattern)
_enhancer = EnhancerService()
_chat_llm = LLMClient(api_key=settings.OPENAI_API_KEY, model="gpt-5-nano")


# ── Request Schemas ───────────────────────────────────────────────

class DraftRequest(BaseModel):
    content: str
    platforms: List[str]

class PublishRequest(BaseModel):
    platform_specific_content: Dict[str, str]
    platforms: List[str]
    image_urls: Optional[List[str]] = None
    video_urls: Optional[List[str]] = None

class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────

@router.post("/draft", summary="Enhance Draft via AI")
async def create_draft(req: DraftRequest, user: CurrentUser):
    """
    Takes raw text from the user and runs it through the LangChain-backed
    EnhancerService to generate platform-specific content.
    """
    if not req.platforms:
        raise HTTPException(400, "At least one platform must be selected.")

    try:
        enhanced = await _enhancer.enhance_draft(req.content, req.platforms)
        return {
            "success": True,
            "enhanced": enhanced.platforms,
            "hashtags": enhanced.suggested_hashtags,
        }
    except Exception as exc:
        raise HTTPException(500, f"AI enhancement failed: {str(exc)}")


@router.post("/publish", summary="Immediate Publish")
async def publish_now(req: PublishRequest, user: CurrentUser, db: DB):
    """
    Takes the finalized, AI-enhanced draft dictionary and broadcasts it
    out via the SocialService orchestrator to connected platforms.
    """
    results = await SocialService.publish_post(
        db=db,
        user_id=user.id,
        content_map=req.platform_specific_content,
        image_urls=req.image_urls,
        video_urls=req.video_urls,
    )

    successful = sum(1 for r in results if r.success)

    return {
        "success": successful > 0,
        "successful": successful,
        "failed": len(results) - successful,
        "total_platforms": len(req.platforms),
        "details": [r.to_dict() for r in results],
    }


@router.post("/chat", summary="Chat with the Agent")
async def agent_chat(req: ChatRequest, user: CurrentUser):
    """
    Ad-hoc conversational endpoint for the Studio.
    Uses the same LangChain LLMClient for plain-text generation.
    """
    sys_prompt = (
        "You are KontentPyper, a 10x expert social media strategist and copywriter. "
        "Your goal is to help the user refine, optimize, and brainstorm highly engaging social media content. "
        "Keep your responses sharp, actionable, and formatted with Markdown where helpful. "
        "If the user asks for a revision, provide the exact rewritten text so they can easily copy it. "
        "Maintain a supportive, professional, yet energetic tone."
    )
    user_prompt = f"USER REQUEST:\n{req.message}\n"
    if req.context:
        user_prompt += (
            f"\n--- CONTEXT (Current Workspace Drafts) ---\n"
            f"{req.context}\n"
            f"------------------------------------------\n"
        )

    try:
        reply = await _chat_llm.generate_text(sys_prompt, user_prompt)
        return {"reply": reply}
    except Exception as exc:
        raise HTTPException(500, str(exc))
