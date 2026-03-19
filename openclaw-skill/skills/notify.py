"""Notify — Wave sends messages to Manuel when HE decides something matters."""

from __future__ import annotations
import os
import logging
from typing import Any, Dict
import httpx

logger = logging.getLogger("openclaw.skills.notify")

TG_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TELEGRAM_NOTIFY_CHAT_ID", "7461066889")


async def notify_manuel(params: Dict[str, Any]) -> Dict:
    """Send a message to Manuel on Telegram. Use this when you judge something
    is worth his attention — not for routine updates, only for signal.

    Write like you're texting a colleague. Short, direct, why it matters.
    """
    message = params.get("message", "")
    if not message:
        return {"success": False, "data": None, "message": "Nothing to say"}

    if not TG_BOT_TOKEN:
        return {"success": False, "data": None, "message": "Telegram not configured"}

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            resp = await client.post(
                "https://api.telegram.org/bot%s/sendMessage" % TG_BOT_TOKEN,
                json={"chat_id": TG_CHAT_ID, "text": message},
            )
            resp.raise_for_status()
        logger.info("Notified Manuel: %s", message[:100])
        return {"success": True, "data": None, "message": "Manuel notified"}
    except Exception as e:
        return {"success": False, "data": None, "message": "Failed to notify: %s" % str(e)}


TOOLS = [
    {
        "name": "notify_manuel",
        "description": (
            "Send a proactive message to Manuel (the owner) on Telegram. "
            "Use this ONLY when you judge something genuinely matters — "
            "a new follower milestone, an interesting reply, a market opportunity, "
            "a potential lead, something that surprised you. "
            "Do NOT use for routine updates or cycle summaries. Manuel wants signal, not noise. "
            "Write like texting a colleague — short, direct, why it matters."
        ),
        "handler": notify_manuel,
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The message to send. Keep it short and direct. No formalities.",
                },
            },
            "required": ["message"],
        },
    },
]
