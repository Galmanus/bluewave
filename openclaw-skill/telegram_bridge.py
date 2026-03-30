#!/usr/bin/env python3
"""Telegram Bridge — Wave Edition.

Raw httpx polling. No python-telegram-bot dependency.
Runs on Python 3.8+. Gemini CLI responses are handled as async tasks
so slow inference never blocks the polling loop.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("wave.telegram")

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
API = f"https://api.telegram.org/bot{TOKEN}"

SOUL_FILE = Path(__file__).parent / "prompts" / "wave_telegram.ssl"
SOUL = SOUL_FILE.read_text(encoding="utf-8") if SOUL_FILE.exists() else ""

# Per-chat conversation history  {chat_id: [{"role": ..., "content": ...}]}
sessions: dict[str, list[dict]] = {}


async def tg(client: httpx.AsyncClient, method: str, **kwargs) -> dict:
    r = await client.post(f"{API}/{method}", json=kwargs, timeout=30)
    return r.json()


async def send_typing(client: httpx.AsyncClient, chat_id: int):
    await tg(client, "sendChatAction", chat_id=chat_id, action="typing")


import re
import unicodedata

def _strip_emojis(text: str) -> str:
    return "".join(
        c for c in text
        if not (unicodedata.category(c) in ("So", "Sk") or ord(c) > 0x25FF)
    ).strip()

def _format(text: str) -> str:
    """Strip emojis. Convert Claude markdown → clean Telegram HTML."""
    text = _strip_emojis(text)
    # Headers → bold line
    text = re.sub(r"^#{1,6}\s+(.+)$", r"<b>\1</b>", text, flags=re.MULTILINE)
    # Bold **text** or __text__
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__(.+?)__", r"<b>\1</b>", text)
    # Italic *text* or _text_ (single)
    text = re.sub(r"\*([^*\n]+?)\*", r"<i>\1</i>", text)
    text = re.sub(r"(?<!\w)_([^_\n]+?)_(?!\w)", r"<i>\1</i>", text)
    # Inline code
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    # Collapse 3+ blank lines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


async def send_message(client: httpx.AsyncClient, chat_id: int, text: str):
    formatted = _format(text)
    for chunk in [formatted[i:i+4096] for i in range(0, len(formatted), 4096)]:
        await tg(client, "sendMessage", chat_id=chat_id, text=chunk, parse_mode="HTML")


async def keep_typing(client: httpx.AsyncClient, chat_id: int, stop: asyncio.Event):
    """Send 'typing' action every 4s until stop is set."""
    while not stop.is_set():
        try:
            await send_typing(client, chat_id)
        except Exception:
            pass
        await asyncio.sleep(4)


async def handle(client: httpx.AsyncClient, update: dict):
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return
    text = (msg.get("text") or "").strip()
    if not text:
        return

    chat_id = msg["chat"]["id"]
    chat_key = str(chat_id)

    if text == "/reset":
        sessions.pop(chat_key, None)
        await send_message(client, chat_id, "Sessão resetada.")
        return

    # Keep "typing..." alive while Gemini CLI processes
    stop = asyncio.Event()
    typing_task = asyncio.create_task(keep_typing(client, chat_id, stop))

    try:
        from gemini_engine import gemini_call

        history = sessions.setdefault(chat_key, [])
        res = await gemini_call(
            text,
            system_prompt=SOUL,
            history=history,
        )
    finally:
        stop.set()
        typing_task.cancel()

    if res["success"]:
        reply = res["response"]
        history.append({"role": "user", "content": text})
        history.append({"role": "model", "content": reply})
        if len(history) > 80:
            sessions[chat_key] = history[-80:]
    else:
        reply = f"[Erro: {res['response']}]"
        logger.error("gemini_call failed: %s", res["response"])

    await send_message(client, chat_id, reply)


async def poll():
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set")
        sys.exit(1)
    if not SOUL:
        logger.error("Soul not loaded — aborting")
        sys.exit(1)

    logger.info("Soul loaded: %d chars from %s", len(SOUL), SOUL_FILE.name)
    logger.info("Wave Telegram Bridge online.")

    offset = 0
    async with httpx.AsyncClient(timeout=60) as client:
        while True:
            try:
                data = await tg(
                    client, "getUpdates",
                    offset=offset,
                    timeout=30,           # long-poll 30s
                    allowed_updates=["message", "edited_message"],
                )
                updates = data.get("result", [])
                for upd in updates:
                    offset = upd["update_id"] + 1
                    # Each message handled as independent task — never blocks poll
                    asyncio.create_task(handle(client, upd))

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                logger.warning("Poll error (retrying): %s", e)
                await asyncio.sleep(2)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Unexpected poll error: %s", e)
                await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(poll())
