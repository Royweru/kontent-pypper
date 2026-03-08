"""
KontentPyper - Telegram Webhook Endpoint
=========================================
Receives incoming Telegram updates (messages + callback queries)
and routes /approve and /reject commands to the HITL service.

Register this URL with BotFather using:
  POST https://api.telegram.org/bot<TOKEN>/setWebhook
  {"url": "https://kontent-pypper.onrender.com/webhook/telegram"}

Or use the convenience endpoint: POST /api/v1/auth/settings/telegram/register-webhook
"""

import logging
from fastapi import APIRouter, Request, HTTPException, Response
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.services.notifications.telegram_hitl import resolve_approval, send_message

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/telegram", include_in_schema=False)
async def telegram_webhook(request: Request):
    """
    Receives Telegram Bot API updates.
    Handles:
      - callback_query (inline button presses)  -> approve / reject
      - /approve <message_id>                   -> approve
      - /reject  <message_id>                   -> reject
      - /start                                  -> link chat_id to user account
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    logger.debug("[TgWebhook] Raw update: %s", body)

    # ── Callback Query (inline keyboard button press) ──────────────────────────
    if "callback_query" in body:
        cq = body["callback_query"]
        chat_id      = str(cq["message"]["chat"]["id"])
        message_id   = cq["message"]["message_id"]
        data         = cq.get("data", "")          # "approve" or "reject"
        approved     = (data == "approve")
        callback_qid = cq["id"]

        found = resolve_approval(chat_id, message_id, approved)

        # Answer the callback so the spinning indicator stops
        async with _get_bot_client(chat_id) as (token, client):
            if token:
                answer_url = f"https://api.telegram.org/bot{token}/answerCallbackQuery"
                await client.post(answer_url, json={
                    "callback_query_id": callback_qid,
                    "text": "✅ Approved!" if approved else "❌ Rejected",
                })

        if not found:
            logger.warning("[TgWebhook] No pending draft for chat_id=%s msg_id=%s", chat_id, message_id)

        return Response(status_code=200)

    # ── Text Message (command) ─────────────────────────────────────────────────
    if "message" in body:
        msg     = body["message"]
        chat_id = str(msg["chat"]["id"])
        text    = msg.get("text", "").strip()

        if not text:
            return Response(status_code=200)

        # /approve <message_id>
        if text.lower().startswith("/approve"):
            parts = text.split()
            if len(parts) == 2 and parts[1].isdigit():
                resolved = resolve_approval(chat_id, int(parts[1]), True)
                async with _get_bot_client(chat_id) as (token, _):
                    if token:
                        reply = "✅ Draft approved! Publishing now..." if resolved else "No pending draft found with that ID."
                        await send_message(token, chat_id, reply)

        # /reject <message_id>
        elif text.lower().startswith("/reject"):
            parts = text.split()
            if len(parts) == 2 and parts[1].isdigit():
                resolved = resolve_approval(chat_id, int(parts[1]), False)
                async with _get_bot_client(chat_id) as (token, _):
                    if token:
                        reply = "❌ Draft rejected. It will not be published." if resolved else "No pending draft found with that ID."
                        await send_message(token, chat_id, reply)

        # /start  -- link this chat_id to the user's account
        elif text.lower().startswith("/start"):
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(User).where(User.telegram_chat_id == chat_id)
                )
                existing = result.scalar_one_or_none()

            async with _get_bot_client(chat_id) as (token, _):
                if token:
                    if existing:
                        msg_text = (
                            f"✅ Chat already linked to <b>{existing.username}</b>! "
                            "You'll receive content approval previews here."
                        )
                    else:
                        msg_text = (
                            "👋 <b>Welcome to KontentPyper!</b>\n\n"
                            "To link this chat to your account, go to "
                            "<b>Settings → Telegram Integration</b> "
                            "in the dashboard and click <b>Detect Chat ID</b>."
                        )
                    await send_message(token, chat_id, msg_text)

    return Response(status_code=200)


# ── Helper: look up bot token from DB for this chat_id ────────────────────────
from contextlib import asynccontextmanager
import httpx

@asynccontextmanager
async def _get_bot_client(chat_id: str):
    """Yields (bot_token, httpx_client) for the user who owns this chat_id."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User.telegram_bot_token).where(User.telegram_chat_id == chat_id)
        )
        token = result.scalar_one_or_none()

    async with httpx.AsyncClient(timeout=5) as client:
        yield token, client
