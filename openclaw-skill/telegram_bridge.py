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

# Per-chat conversation history with TTL-based cleanup
# {chat_id: {"history": [...], "last_active": timestamp}}
import time as _time

SESSION_TTL_SECONDS = 24 * 3600  # 24 hours
_sessions_raw: dict[str, dict] = {}


def _cleanup_sessions():
    """Remove sessions inactive for more than SESSION_TTL_SECONDS."""
    now = _time.time()
    expired = [k for k, v in _sessions_raw.items()
               if now - v.get("last_active", 0) > SESSION_TTL_SECONDS]
    for k in expired:
        del _sessions_raw[k]
    if expired:
        logger.info("Cleaned up %d expired sessions", len(expired))


def _get_session(chat_key: str) -> list[dict]:
    """Get or create session history, updating last_active timestamp."""
    if chat_key not in _sessions_raw:
        _sessions_raw[chat_key] = {"history": [], "last_active": _time.time()}
    else:
        _sessions_raw[chat_key]["last_active"] = _time.time()
    return _sessions_raw[chat_key]["history"]


def _set_session_history(chat_key: str, history: list[dict]):
    """Replace session history (used for truncation)."""
    if chat_key in _sessions_raw:
        _sessions_raw[chat_key]["history"] = history


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


# Tempo (segundos) antes de enviar o ACK "Processando..."
# Respostas rápidas chegam antes disso — nenhuma mensagem extra é enviada.
ACK_AFTER_SECONDS = 20

# Intervalo de pulso de status para tarefas muito longas (em segundos)
PULSE_INTERVAL = 120


async def keep_typing(client: httpx.AsyncClient, chat_id: int, stop: asyncio.Event):
    """Send 'typing' action every 4s until stop is set."""
    while not stop.is_set():
        try:
            await send_typing(client, chat_id)
        except Exception:
            pass
        await asyncio.sleep(4)


async def _run_inference(
    client: httpx.AsyncClient,
    chat_id: int,
    chat_key: str,
    text: str,
):
    """Execute inference and deliver result to Telegram.

    Decoupled from the polling loop — runs as a fire-and-forget task.
    ACK_AFTER_SECONDS after start, if not done, sends ONE status message
    so the user knows the task is alive. Never times out externally.
    """
    from claude_engine import gemini_call

    history = _get_session(chat_key)

    stop = asyncio.Event()
    typing_task = asyncio.create_task(keep_typing(client, chat_id, stop))
    ack_sent = False
    start_elapsed = 0

    # Wrap inference in a task so we can race it against the ACK timer
    inference_task = asyncio.create_task(
        gemini_call(text, system_prompt=SOUL, history=history)
    )

    try:
        while not inference_task.done():
            try:
                await asyncio.wait_for(
                    asyncio.shield(inference_task),
                    timeout=ACK_AFTER_SECONDS,
                )
            except asyncio.TimeoutError:
                start_elapsed += ACK_AFTER_SECONDS
                if not ack_sent:
                    # One-time notification that this is a long task
                    ack_sent = True
                    await send_message(
                        client, chat_id,
                        "Processando tarefa complexa. Aviso quando terminar."
                    )
                elif start_elapsed % PULSE_INTERVAL == 0:
                    # Periodic pulse for very long tasks (every 2 min after first ACK)
                    mins = start_elapsed // 60
                    await send_message(
                        client, chat_id,
                        f"Ainda trabalhando... {mins}min"
                    )

        res = inference_task.result()

    except Exception as e:
        logger.error("inference task error: %s", e)
        res = {"success": False, "response": str(e)}

    finally:
        stop.set()
        typing_task.cancel()

    if res["success"]:
        reply = res["response"]
        history.append({"role": "user", "content": text})
        history.append({"role": "model", "content": reply})
        if len(history) > 80:
            _set_session_history(chat_key, history[-80:])
    else:
        reply = f"[Erro: {res['response']}]"
        logger.error("inference failed: %s", res["response"])

    await send_message(client, chat_id, reply)


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
        _sessions_raw.pop(chat_key, None)
        await send_message(client, chat_id, "Sessão resetada.")
        return

    # Fire-and-forget: polling loop never blocks on inference
    asyncio.create_task(_run_inference(client, chat_id, chat_key, text))


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
        # Force-disconnect any competing polling session
        logger.info("Clearing competing sessions...")
        for _ in range(10):
            try:
                resp = await tg(client, "getUpdates", offset=-1, timeout=0)
                results = resp.get("result", [])
                if results:
                    offset = results[-1]["update_id"] + 1
            except Exception:
                pass
            await asyncio.sleep(0.5)
        logger.info("Session acquired. Starting long-poll loop.")

        _cleanup_counter = 0
        while True:
            # Periodic session cleanup every ~100 poll cycles (~50 min with 30s timeout)
            _cleanup_counter += 1
            if _cleanup_counter % 100 == 0:
                _cleanup_sessions()

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
