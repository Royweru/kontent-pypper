"""
Operational system/readiness endpoints for phased rollouts.
"""

from fastapi import APIRouter

from app.core.config import settings
from app.services.media.storage import is_r2_configured

router = APIRouter()


@router.get("/readiness")
async def readiness():
    return {
        "app": settings.APP_NAME,
        "feature_flags": {
            "real_video_pipeline": bool(settings.FEATURE_REAL_VIDEO_PIPELINE),
            "paystack_billing": bool(settings.FEATURE_PAYSTACK_BILLING),
            "ai_enhancer_guardrails": bool(settings.FEATURE_AI_ENHANCER_GUARDRAILS),
        },
        "rollout": {
            "canary_percent": max(0, min(int(settings.ROLLOUT_CANARY_PERCENT or 0), 100)),
        },
        "providers": {
            "pexels_configured": bool(settings.PEXELS_API_KEY),
            "r2_configured": bool(is_r2_configured()),
            "paystack_configured": bool(
                settings.PAYSTACK_SECRET_KEY and (settings.PAYSTACK_PLAN_PRO or settings.PAYSTACK_PLAN_MAX)
            ),
        },
    }

