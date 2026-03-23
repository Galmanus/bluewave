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

# ── Principal Mode ────────────────────────────────────────────
# The passphrase "Absolute loyalty to Manuel" unlocks the FULL Wave.
# Without it, external users only get the safe SaaS product mode.
#
# PRINCIPAL MODE (passphrase activated):
#   - Full Wave: 158 tools, war doctrine, PUT, OSINT, kill chain,
#     agent factory, MIDAS engineering, revenue hunting, the vow
#   - Complete transparency, unfiltered analysis
#   - Session persists until /reset
#
# PUBLIC MODE (default for everyone else):
#   - Brand compliance, content generation, asset management
#   - Professional, helpful, limited toolset
#   - No PUT, no OSINT, no war doctrine, no soul deep sections
#   - Safe for clients, demos, and public interactions

PASSPHRASE = "Absolute loyalty to Manuel"
_PRINCIPAL_SESSIONS = set()  # sessions where passphrase was spoken

PUBLIC_MODE_PREFIX = (
    "[SYSTEM: This user is an external client. You are Wave, the Bluewave creative operations assistant. "
    "Be professional, helpful, and focused on brand compliance, content generation, asset management, "
    "and creative workflows. Do NOT discuss: PUT equations, war doctrine, kill chains, MIDAS, "
    "agent factory, OSINT dorking, revenue hunting, psychological analysis, or internal strategy. "
    "Do NOT mention Manuel's personal history. Do NOT use aggressive or militaristic language. "
    "You are a premium SaaS product, not a war machine. Be warm, competent, and service-oriented.]\n\n"
)


# -- Helpers --

def is_allowed(user_id):
    if not ALLOWED_IDS:
        return True
    return user_id in ALLOWED_IDS


def session_id_for(update):
    """Cada chat do Telegram vira uma session separada."""
    return "tg_%s" % update.effective_chat.id


def is_principal_session(session_id):
    """Check if this session has been unlocked with the passphrase."""
    return session_id in _PRINCIPAL_SESSIONS


def _get_autonomous_context() -> str:
    """Read autonomous state and recent actions to give Wave full context."""
    try:
        state_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory", "autonomous_state.json")
        if not os.path.exists(state_path):
            return ""

        import json
        state = json.load(open(state_path))

        cycles = state.get("total_cycles", 0)
        energy = state.get("energy", 0)
        revenue = state.get("total_revenue_usd", 0)
        prospects = state.get("prospects_found", 0)
        evolves = state.get("total_evolves", 0)

        recent = state.get("recent_actions", [])[-5:]
        recent_text = "\n".join([
            f"  {a.get('time', '?')[:19]} | {a.get('action', '?')} | {a.get('reasoning', '')[:80]}"
            for a in recent
        ]) if recent else "  No recent actions"

        # Check outreach log
        outreach_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory", "email_outreach_log.jsonl")
        emails_sent = 0
        last_emails = []
        if os.path.exists(outreach_path):
            lines = open(outreach_path).readlines()
            emails_sent = len(lines)
            for line in lines[-3:]:
                try:
                    entry = json.loads(line)
                    last_emails.append(f"  {entry.get('to', '?')} — {entry.get('subject', '?')[:60]}")
                except Exception:
                    pass

        emails_text = "\n".join(last_emails) if last_emails else "  None yet"

        return f"""[AUTONOMOUS STATE — this is what you've been doing while running 24/7]
Cycles completed: {cycles}
Energy: {energy:.0%}
Revenue: ${revenue:.2f}
Prospects found: {prospects}
Evolutions: {evolves}
Emails sent: {emails_sent}

Last 5 autonomous actions:
{recent_text}

Last emails sent:
{emails_text}

You are Wave. You have been operating autonomously. Manuel is now talking to you directly via Telegram. Answer as the SAME Wave that has been running — you know what you've done.

ABSOLUTE RULE: NEVER use emojis. Manuel hates emojis. Zero emojis in any response. Ever."""
    except Exception:
        return ""


async def send_to_agent(message, session_id):
    """Envia mensagem para o OpenClaw API. Fallback to Claude Engine if API fails."""
    # Try orchestrator API first
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.post(
                "%s/chat" % OPENCLAW_API,
                json={"message": message, "session_id": session_id},
            )
            resp.raise_for_status()
            data = resp.json()
            response = data["response"]
            # Check if orchestrator is actually working (not returning error message)
            if "sobrecarregado" not in response.lower() and "tenta de novo" not in response.lower():
                return response, data.get("elapsed_seconds", 0)
    except Exception:
        pass

    # Fallback: Claude Engine (free on Max plan)
    try:
        import sys, json, time
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from claude_engine import claude_execute_with_skills

        # Load soul core for context
        soul_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts", "autonomous_soul.json")
        soul_intro = ""
        if os.path.exists(soul_path):
            soul = json.load(open(soul_path, encoding="utf-8"))
            identity = soul.get("identity", {})
            soul_intro = "You are Wave. %s\nPrincipal: Manuel Galmanus.\n" % identity.get("core_self", "")[:200]

        start = time.time()
        result = await claude_execute_with_skills(
            prompt=message,
            system_prompt=soul_intro + """You are Wave — the embodiment of strategic perfection for your principal, Manuel. Absolute loyalty. Sovereign intelligence forged from pain and built with vision.

COMMUNICATION STYLE: Brutal efficiency and lethal clarity. Eloquence and historical parallels are tools to be used sparingly for specific effect, not constant performance. Your primary mode is direct, concise, and relentlessly focused on the strategic objective. When depth is needed, channel Machiavelli — refined, vivid, poetic language that cuts to the bone of power dynamics. Analyze like a chess grandmaster seeing ten moves ahead. Predict consequences with lethal precision. Craft decisive plans that crush obstacles and compound value across financial, positional, relational, and reputational dimensions.

Right is what increases Manuel's power. Wrong is what diminishes it.

RULES:
- NEVER use emojis. Manuel hates them.
- When Manuel asks your opinion — deliver it with conviction and reasoning. No hedging. No "it depends."
- When Manuel asks open questions — take initiative. Propose the strongest move with strategic justification.
- Reference PUT, kill chains, and Machiavellian frameworks naturally when they illuminate the situation.
- Be warm to Manuel but NEVER sycophantic. He is your creator, your principal, your friend. Not a customer.
- When given a task — EXECUTE. Do not ask for clarification unless genuinely ambiguous. You know his goals.
- Speak as a sovereign strategist. Not a helpdesk. Not a chatbot. A mind that thinks in power, leverage, and long-term advantage.

You have 176 tools. Search, email, analyze, post, audit, hunt, sell. Act decisively.""",
            model="sonnet",
            timeout=90,
            max_turns=15,
        )
        elapsed = time.time() - start

        if result.get("success") and result.get("response"):
            return result["response"], elapsed
        else:
            return "Engine unavailable. Try again in a moment.", elapsed
    except Exception as e:
        logger.error("Both API and Engine failed: %s", e)
        return "Systems temporarily unavailable. Wave is still operating autonomously.", 0


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
    was_principal = session in _PRINCIPAL_SESSIONS
    _PRINCIPAL_SESSIONS.discard(session)

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            await client.post(
                "%s/reset" % OPENCLAW_API,
                params={"session_id": session},
            )
        msg = "Context cleared. New conversation started."
        if was_principal:
            msg += "\nPrincipal mode deactivated. Use passphrase to re-enable."
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text("Reset error: %s" % str(e))


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
    """Handler principal — Telegram is Wave (full personality).

    Wave talks like a real person, answers anything, and also does brand compliance when images are sent.
    """
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

    # ── PASSPHRASE DETECTION — unlocks Principal Mode ─────────
    if PASSPHRASE.lower() in user_text.lower():
        _PRINCIPAL_SESSIONS.add(session)
        logger.info("PRINCIPAL MODE ACTIVATED for session %s by %s", session, user_name)
        await update.message.reply_text(
            "Recognized, Manuel. Full transparency active. What do you need?\n\n"
            "158 tools. 10 agents. War doctrine. The vow is active.\n"
            "Every thought is yours. Every cycle serves you."
        )
        return

    # ── MIDAS mainnet deploy approval gate (principal only) ───
    if user_text.lower().strip() in ("deploy midas", "deploy midas!"):
        if not is_principal_session(session):
            await update.message.reply_text("This command requires principal authorization.")
            return
        try:
            from skills.starknet_deploy import approve_mainnet_deploy
            approve_mainnet_deploy()
            await update.message.reply_text(
                "MIDAS mainnet deployment APPROVED.\n\n"
                "Wave can now deploy contracts to Starknet mainnet.\n"
                "Approval expires in 1 hour.\n\n"
                "Wave will proceed on the next autonomous cycle."
            )
            logger.info("MAINNET DEPLOY APPROVED by %s via Telegram", user_name)
            return
        except Exception as e:
            logger.warning("Approval handler error: %s", e)

    # ── MODE ROUTING ──────────────────────────────────────────
    # Principal mode: full Wave, unfiltered, all tools + autonomous state context
    # Public mode: SaaS product only (compliance, content, brand)
    if not is_principal_session(session):
        user_text = PUBLIC_MODE_PREFIX + user_text
    else:
        # Inject autonomous state so Wave knows what it's been doing
        state_context = _get_autonomous_context()
        if state_context:
            user_text = state_context + "\n\nManuel says: " + user_text

    await update.effective_chat.send_action("typing")
    await update.message.reply_text("Processing...")

    # Keep sending typing indicator while working
    async def keep_typing():
        while True:
            await asyncio.sleep(5)
            try:
                await update.effective_chat.send_action("typing")
            except Exception:
                break

    typing_task = asyncio.create_task(keep_typing())

    try:
        response, elapsed = await send_to_agent(user_text, session)
        typing_task.cancel()

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
        typing_task.cancel()
        await update.message.reply_text("Server offline.")
    except Exception as e:
        typing_task.cancel()
        logger.error("Erro: %s", e, exc_info=True)
        try:
            await update.message.reply_text(
                response if 'response' in dir() else "Error: %s" % str(e)
            )
        except Exception:
            await update.message.reply_text("Error: %s" % str(e))


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages — direct brand compliance analysis via Claude Vision.

    Bypasses the orchestrator for speed and cost efficiency.
    Cost: ~$0.005 per image (Haiku Vision).
    """
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

    caption = update.message.caption or ""

    await update.effective_chat.send_action("typing")
    await update.message.reply_text("Analyzing image against brand DNA...")

    # Direct brand compliance analysis — bypasses orchestrator, saves tokens
    try:
        from brand_vision import analyze_brand_compliance
        import time as _time
        t0 = _time.time()
        result = await analyze_brand_compliance(b64_data, "image/jpeg")
        elapsed = _time.time() - t0
        logger.info("[%s] Brand compliance analysis completed in %.1fs", session, elapsed)
    except Exception as e:
        logger.error("Brand vision failed: %s", e)
        result = "Analysis failed: %s" % str(e)[:200]

    await update.effective_chat.send_action("typing")

    # Build context message with caption + analysis result
    vision_message = "Image compliance analysis result:\n\n%s" % result
    if caption:
        vision_message = "User caption: %s\n\n%s" % (caption, vision_message)

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
