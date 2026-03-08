"""
KontentPyper - Telegram HITL (Human-in-the-Loop) Service
=========================================================
Sends content previews to a user's personal Telegram bot.
The operator replies with /approve or /reject to control publishing.

Flow:
  1. Pipeline prepares a post draft.
  2. This service sends a formatted card to the user's Telegram chat.
  3. The bot stores a `pending_approval` entry keyed by Telegram message_id.
  4. When the user replies `/approve <id>` or `/reject <id>`, the Telegram
     webhook endpoint resolves the pending future and the pipeline continues.

Design notes:
  - Uses httpx.AsyncClient (same dependency already in the project).
  - The approval state is kept in an in-process dict. Fine for MVP; in V2
    this becomes a Redis key-value store with a TTL.
  - One bot token per user; stored in the `users` table columns that already exist.
"""

import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta

import httpx

logger = logging.getLogger(__name__)

# ── In-process approval registry ──────────────────────────────────────────────
# Key:   (chat_id, message_id)  as strings -> "chat_id:msg_id"
# Value: asyncio.Future that resolves to True (approved) or False (rejected)
_PENDING: Dict[str, asyncio.Future] = {}

APPROVAL_TIMEOUT_MINUTES = 30   # after 30 min the draft is auto-rejected


# ── Low-level Telegram API helpers ────────────────────────────────────────────

async def _tg_post(bot_token: str, method: str, payload: dict) -> dict:
    """Fire-and-forget helper to call the Telegram Bot API."""
    url = f"https://api.telegram.org/bot{bot_token}/{method}"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()


async def send_message(bot_token: str, chat_id: str, text: str, **kwargs) -> dict:
    """Send a plain or HTML-formatted message. Returns the message object."""
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", **kwargs}
    return await _tg_post(bot_token, "sendMessage", payload)


async def send_photo(bot_token: str, chat_id: str, photo_url: str, caption: str, **kwargs) -> dict:
    """Send a photo with caption."""
    payload = {
        "chat_id": chat_id,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "HTML",
        **kwargs,
    }
    return await _tg_post(bot_token, "sendPhoto", payload)


# ── HITL Core ─────────────────────────────────────────────────────────────────

def _approval_key(chat_id: str, message_id: int) -> str:
    return f"{chat_id}:{message_id}"


async def send_preview_and_wait(
    bot_token: str,
    chat_id: str,
    platform: str,
    content: str,
    image_url: Optional[str] = None,
) -> bool:
    """
    Sends a formatted preview card to the user's Telegram and waits for
    /approve or /reject.

    Returns:
        True  -> approved (pipeline should publish)
        False -> rejected or timed out (pipeline should skip)
    """
    # Format the preview card
    platform_emoji = {
        "twitter": "𝕏",
        "linkedin": "💼",
        "youtube": "▶",
        "tiktok": "♪",
    }.get(platform.lower(), "📣")

    card = (
        f"<b>🔔 KontentPyper — Content Approval Required</b>\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"{platform_emoji} <b>Platform:</b> {platform.upper()}\n\n"
        f"<b>Draft:</b>\n<i>{content[:800]}</i>\n\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"Reply with the command + the message ID shown below."
    )

    # Inline keyboard for quick reply
    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Approve", "callback_data": "approve"},
            {"text": "❌ Reject",  "callback_data": "reject"},
        ]]
    }

    try:
        if image_url:
            result = await send_photo(
                bot_token, chat_id, image_url, card,
                reply_markup=keyboard,
            )
        else:
            result = await send_message(
                bot_token, chat_id, card,
                reply_markup=keyboard,
            )
    except Exception as exc:
        logger.error("[TelegramHITL] Failed to send preview card: %s", exc)
        return False

    message_id: int = result["result"]["message_id"]
    key = _approval_key(chat_id, message_id)

    logger.info("[TelegramHITL] Sent preview message_id=%s for %s. Waiting for approval...", message_id, platform)

    # Send the message ID so the user knows which draft they are approving
    await send_message(
        bot_token, chat_id,
        f"<b>Draft ID:</b> <code>{message_id}</code>\n"
        f"Use the inline buttons above or type:\n"
        f"  /approve {message_id}\n"
        f"  /reject {message_id}"
    )

    # Create a Future and register it
    loop = asyncio.get_event_loop()
    future: asyncio.Future = loop.create_future()
    _PENDING[key] = future

    try:
        # Wait up to APPROVAL_TIMEOUT_MINUTES
        result = await asyncio.wait_for(
            asyncio.shield(future),
            timeout=APPROVAL_TIMEOUT_MINUTES * 60,
        )
        logger.info("[TelegramHITL] message_id=%s resolved -> %s", message_id, result)
        return result
    except asyncio.TimeoutError:
        logger.warning("[TelegramHITL] message_id=%s timed out after %d min. Auto-rejecting.", message_id, APPROVAL_TIMEOUT_MINUTES)
        await send_message(bot_token, chat_id,
            f"⏰ Draft <code>{message_id}</code> timed out after {APPROVAL_TIMEOUT_MINUTES} minutes and was auto-rejected.")
        return False
    finally:
        _PENDING.pop(key, None)


def resolve_approval(chat_id: str, message_id: int, approved: bool) -> bool:
    """
    Called by the webhook handler when the user sends /approve or /reject.
    Returns True if a pending future was found and resolved, False otherwise.
    """
    key = _approval_key(str(chat_id), message_id)
    future = _PENDING.get(key)
    if future and not future.done():
        future.set_result(approved)
        logger.info("[TelegramHITL] Resolved key=%s approved=%s", key, approved)
        return True
    logger.warning("[TelegramHITL] No pending future found for key=%s", key)
    return False
