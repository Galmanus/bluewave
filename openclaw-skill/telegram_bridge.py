#!/usr/bin/env python3
"""Telegram Bridge — Machiavelli Prime no Telegram.

Recebe mensagens do Telegram, envia para o OpenClaw API,
e retorna a resposta do agente no chat.

Usage:
    TELEGRAM_BOT_TOKEN=... python3 telegram_bridge.py

Environment:
    TELEGRAM_BOT_TOKEN    — token do @BotFather (obrigatorio)
    OPENCLAW_API_URL      — URL do servidor OpenClaw (default: http://localhost:18790)
    TELEGRAM_ALLOWED_IDS  — IDs de usuarios permitidos, separados por virgula (opcional, vazio = todos)
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

import httpx
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("openclaw.telegram")

# -- Config --

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
OPENCLAW_API = os.environ.get("OPENCLAW_API_URL", "http://localhost:18790")
ALLOWED_IDS_RAW = os.environ.get("TELEGRAM_ALLOWED_IDS", "")
ALLOWED_IDS = set()
if ALLOWED_IDS_RAW.strip():
    ALLOWED_IDS = {int(x.strip()) for x in ALLOWED_IDS_RAW.split(",") if x.strip()}

HTTP_TIMEOUT = httpx.Timeout(180.0, connect=10.0)


# -- Helpers --

def is_allowed(user_id):
    if not ALLOWED_IDS:
        return True
    return user_id in ALLOWED_IDS


def session_id_for(update):
    """Cada chat do Telegram vira uma session separada."""
    return "tg_%s" % update.effective_chat.id


async def send_to_agent(message, session_id):
    """Envia mensagem para o OpenClaw API e retorna a resposta."""
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.post(
            "%s/chat" % OPENCLAW_API,
            json={"message": message, "session_id": session_id},
        )
        resp.raise_for_status()
        data = resp.json()
        return data["response"], data.get("elapsed_seconds", 0)


# -- Handlers --

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        await update.message.reply_text("Acesso negado.")
        return

    await update.message.reply_text(
        "Wave online.\n\n"
        "Fala comigo direto. Pesquiso, analiso, crio skills, "
        "coordeno 6 especialistas e opero 24/7.\n\n"
        "/reset - limpar contexto\n"
        "/agents - listar agentes"
    )


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return

    session = session_id_for(update)
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            await client.post(
                "%s/reset" % OPENCLAW_API,
                params={"session_id": session},
            )
        await update.message.reply_text("Contexto limpo. Nova conversa iniciada.")
    except Exception as e:
        await update.message.reply_text("Erro ao resetar: %s" % str(e))


async def cmd_agents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.get("%s/agents" % OPENCLAW_API)
            data = resp.json()

        lines = ["Agentes do sistema:\n"]
        for agent in data.get("agents", []):
            role = "CHEFE" if agent["role"] == "orchestrator" else "especialista"
            lines.append(
                "%s %s (%s) - %s" % (
                    agent["emoji"], agent["name"], role,
                    agent.get("description", "")[:80],
                )
            )
        await update.message.reply_text("\n".join(lines))
    except Exception as e:
        await update.message.reply_text("Erro: %s" % str(e))


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler principal — recebe qualquer mensagem de texto e envia pro agente."""
    if not update.message or not update.message.text:
        return

    if not is_allowed(update.effective_user.id):
        await update.message.reply_text("Acesso negado.")
        return

    user_text = update.message.text.strip()
    if not user_text:
        return

    session = session_id_for(update)
    user_name = update.effective_user.first_name or "Principe"

    logger.info(
        "[%s] %s: %s",
        session, user_name, user_text[:100],
    )

    # Envia "digitando..." enquanto o agente pensa
    await update.effective_chat.send_action("typing")

    try:
        response, elapsed = await send_to_agent(user_text, session)

        # Telegram tem limite de 4096 chars por mensagem
        if len(response) <= 4096:
            await update.message.reply_text(
                response,
                parse_mode="Markdown",
            )
        else:
            # Divide em chunks
            chunks = []
            while response:
                if len(response) <= 4096:
                    chunks.append(response)
                    break
                # Tenta cortar em newline
                cut = response[:4096].rfind("\n")
                if cut < 100:
                    cut = 4096
                chunks.append(response[:cut])
                response = response[cut:]

            for chunk in chunks:
                await update.message.reply_text(chunk, parse_mode="Markdown")

        logger.info(
            "[%s] Respondido em %.1fs (%d chars)",
            session, elapsed, len(response) if isinstance(response, str) else 0,
        )

    except httpx.ConnectError:
        await update.message.reply_text(
            "Servidor OpenClaw offline. Verifique se o API server esta rodando."
        )
    except Exception as e:
        logger.error("Erro: %s", e, exc_info=True)
        # Tenta sem markdown se falhou o parse
        try:
            await update.message.reply_text(
                response if 'response' in dir() else "Erro: %s" % str(e)
            )
        except Exception:
            await update.message.reply_text("Erro ao processar: %s" % str(e))


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages — download and send to Wave for vision analysis."""
    if not update.message:
        return
    if not is_allowed(update.effective_user.id):
        await update.message.reply_text("Acesso negado.")
        return

    session = session_id_for(update)

    # Get the photo file
    if update.message.photo:
        photo = update.message.photo[-1]  # highest resolution
        file = await context.bot.get_file(photo.file_id)
    elif update.message.document:
        file = await context.bot.get_file(update.message.document.file_id)
    else:
        return

    # Download photo bytes
    import base64
    photo_bytes = await file.download_as_bytearray()
    b64_data = base64.standard_b64encode(bytes(photo_bytes)).decode("utf-8")

    # Build the message for Wave
    caption = update.message.caption or ""
    user_prompt = caption if caption else "Analyze this image. What do you see?"

    # Send to Wave with instruction to use vision
    vision_message = (
        "The user sent an image via Telegram. Use the analyze_image tool with this base64 data to see it.\n\n"
        "image_base64: %s\n"
        "media_type: image/jpeg\n"
        "User's message: %s\n\n"
        "Analyze the image and respond to what the user asked. If they just sent it without context, "
        "describe what you see and suggest what you could do with it (brand analysis, OCR, etc)."
    ) % (b64_data[:100] + "...[truncated for prompt, use the full base64 in the tool call]", user_prompt)

    # Actually we need to pass the full base64 to the agent. Let's save it temporarily.
    import tempfile, os, json
    tmp = os.path.join(tempfile.gettempdir(), "wave_img_%s.json" % file.file_id[:16])
    with open(tmp, "w") as f:
        json.dump({"base64": b64_data, "media_type": "image/jpeg"}, f)

    vision_message = (
        "The user sent an image via Telegram. Analyze it using the analyze_image tool.\n"
        "Pass image_base64 from this file: %s\n"
        "Or use this image_base64 directly (it's the full data): %s\n"
        "media_type: image/jpeg\n\n"
        "User's message: %s"
    ) % (tmp, b64_data, user_prompt)

    await update.effective_chat.send_action("typing")

    try:
        response, elapsed = await send_to_agent(vision_message, session)

        if len(response) <= 4096:
            await update.message.reply_text(response)
        else:
            chunks = []
            temp = response
            while temp:
                if len(temp) <= 4096:
                    chunks.append(temp)
                    break
                cut = temp[:4096].rfind("\n")
                if cut < 100:
                    cut = 4096
                chunks.append(temp[:cut])
                temp = temp[cut:]
            for chunk in chunks:
                await update.message.reply_text(chunk)

        logger.info("[%s] Image analyzed in %.1fs", session, elapsed)

    except Exception as e:
        logger.error("Photo error: %s", e)
        await update.message.reply_text("Erro ao analisar imagem: %s" % str(e))

    # Cleanup
    try:
        os.unlink(tmp)
    except Exception:
        pass


# -- Main --

def main():
    if not TOKEN:
        print("TELEGRAM_BOT_TOKEN nao configurado!")
        print("  export TELEGRAM_BOT_TOKEN='seu-token-do-botfather'")
        sys.exit(1)

    logger.info("Conectando ao Telegram...")
    logger.info("OpenClaw API: %s", OPENCLAW_API)
    if ALLOWED_IDS:
        logger.info("Usuarios permitidos: %s", ALLOWED_IDS)
    else:
        logger.info("Sem restricao de usuarios (qualquer um pode falar)")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("agents", cmd_agents))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.IMAGE, handle_photo))

    logger.info("Machiavelli Prime online no Telegram. Aguardando mensagens...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
