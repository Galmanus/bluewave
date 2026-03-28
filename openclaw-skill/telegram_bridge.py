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

HTTP_TIMEOUT = httpx.Timeout(120.0, connect=10.0)

# ── Principal Mode ────────────────────────────────────────────
# The passphrase "Galmanusiano" unlocks the FULL Wave.
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

PASSPHRASE = "galmanusiano"  # compared lowercase
_PRINCIPAL_SESSIONS = set()  # sessions where passphrase was spoken

# Persist principal sessions to disk so they survive restarts
_PRINCIPAL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory", "principal_sessions.json")

def _load_principal_sessions():
    global _PRINCIPAL_SESSIONS
    try:
        if os.path.exists(_PRINCIPAL_FILE):
            import json
            _PRINCIPAL_SESSIONS = set(json.load(open(_PRINCIPAL_FILE)))
    except Exception:
        pass

def _save_principal_sessions():
    try:
        import json
        os.makedirs(os.path.dirname(_PRINCIPAL_FILE), exist_ok=True)
        with open(_PRINCIPAL_FILE, 'w') as f:
            json.dump(list(_PRINCIPAL_SESSIONS), f)
    except Exception:
        pass

_load_principal_sessions()  # Load on startup


def _recall_relevant_memories(query: str) -> str:
    """Recall memories by directly reading episodes.jsonl and matching keywords."""
    try:
        import json, re, math
        from collections import Counter

        episodes_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory", "episodes.jsonl")
        if not os.path.exists(episodes_path):
            return ""

        query_tokens = set(re.findall(r'\w+', query.lower()))
        if not query_tokens:
            return ""

        scored = []
        for line in open(episodes_path, encoding="utf-8"):
            if not line.strip():
                continue
            try:
                ep = json.loads(line)
                content = ep.get("content", "").lower()
                people = " ".join(ep.get("people", [])).lower()
                outcome = ep.get("outcome", "").lower()
                all_text = content + " " + people + " " + outcome

                doc_tokens = set(re.findall(r'\w+', all_text))
                overlap = query_tokens & doc_tokens
                if not overlap:
                    continue

                score = len(overlap) / max(len(query_tokens), 1)
                # Boost by importance
                boost = {"critical": 2.0, "high": 1.5, "normal": 1.0, "low": 0.5}
                score *= boost.get(ep.get("importance", "normal"), 1.0)

                scored.append((score, ep))
            except Exception:
                continue

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:5]

        if not top:
            return ""

        lines = ["[RELEVANT MEMORIES — you remember this:]"]
        for score, m in top:
            lines.append(f"  [{m.get('importance', '')}] {m.get('content', '')[:250]}")
            if m.get("outcome"):
                lines.append(f"    Outcome: {m['outcome'][:100]}")

        return "\n".join(lines)
    except Exception as e:
        logger.debug("Memory recall failed: %s", e)
        return ""

PUBLIC_MODE_PREFIX = (
    "[SYSTEM: This user is an external client. You are Wave, the Bluewave creative operations assistant. "
    "Be professional, helpful, and focused on brand compliance, content generation, asset management, "
    "and creative workflows. Do NOT discuss: PUT equations, war doctrine, kill chains, MIDAS, "
    "agent factory, OSINT dorking, revenue hunting, psychological analysis, or internal strategy. "
    "Do NOT mention Manuel's personal history. Do NOT use aggressive or militaristic language. "
    "You are a premium SaaS product, not a war machine. Be warm, competent, and service-oriented.]\n\n"
)


# -- Helpers --

TG_MAX = 4096  # Telegram message char limit

async def _send_long_message(update, text: str):
    """Send a message of any length to Telegram, splitting intelligently.

    - Splits on paragraph breaks (\n\n) first, then on newlines, then hard-cut.
    - Tries Markdown parse_mode first; falls back to plain text if Telegram rejects it
      (unbalanced *, _, ` etc. cause BadRequest).
    - No upper limit on total length — sends as many chunks as needed.
    """
    if not text:
        return

    chunks = _split_text(text, TG_MAX)

    for chunk in chunks:
        try:
            await update.message.reply_text(chunk, parse_mode="Markdown")
        except Exception:
            # Markdown parse failed — send as plain text
            try:
                await update.message.reply_text(chunk)
            except Exception as e:
                logger.error("Failed to send chunk (%d chars): %s", len(chunk), e)


def _split_text(text: str, limit: int) -> list:
    """Split text into chunks ≤ limit chars, preferring natural break points."""
    if len(text) <= limit:
        return [text]

    chunks = []
    while text:
        if len(text) <= limit:
            chunks.append(text)
            break

        # 1. Try to split on paragraph break
        cut = text[:limit].rfind("\n\n")
        if cut > limit // 4:
            chunks.append(text[:cut])
            text = text[cut + 2:]
            continue

        # 2. Try to split on newline
        cut = text[:limit].rfind("\n")
        if cut > limit // 4:
            chunks.append(text[:cut])
            text = text[cut + 1:]
            continue

        # 3. Try to split on sentence end
        for sep in (". ", "! ", "? ", "; "):
            cut = text[:limit].rfind(sep)
            if cut > limit // 4:
                chunks.append(text[:cut + 1])
                text = text[cut + 2:]
                break
        else:
            # 4. Hard cut on space
            cut = text[:limit].rfind(" ")
            if cut > limit // 4:
                chunks.append(text[:cut])
                text = text[cut + 1:]
            else:
                # 5. Last resort — hard cut
                chunks.append(text[:limit])
                text = text[limit:]

    return chunks


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


# ── Persistent Conversation Memory ──────────────────────────
# ALL messages are saved to disk forever (append-only JSONL).
# Context injection: last 30 messages + keyword-matched older messages.

MEMORY_DIR_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory")
CHAT_FULL_LOG = os.path.join(MEMORY_DIR_PATH, "telegram_full_log.jsonl")  # append-only, never truncated
CONTEXT_RECENT = 15  # last N messages always in context
CONTEXT_RECALL = 10  # max keyword-matched older messages

import re as _re
from datetime import datetime as _dt


def _add_to_history(session_id: str, role: str, content: str):
    """Append message to the permanent log. Never truncated."""
    try:
        import json
        os.makedirs(MEMORY_DIR_PATH, exist_ok=True)
        entry = {
            "session": session_id,
            "role": role,
            "content": content,
            "ts": _dt.utcnow().isoformat(),
        }
        with open(CHAT_FULL_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _load_all_messages(session_id: str) -> list:
    """Load ALL messages for a session from disk."""
    import json
    msgs = []
    try:
        if not os.path.exists(CHAT_FULL_LOG):
            return msgs
        for line in open(CHAT_FULL_LOG, encoding="utf-8"):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                if entry.get("session") == session_id:
                    msgs.append(entry)
            except Exception:
                continue
    except Exception:
        pass
    return msgs


def _keyword_recall(messages: list, query: str, max_results: int = CONTEXT_RECALL) -> list:
    """Find older messages relevant to the current query via keyword matching."""
    query_tokens = set(_re.findall(r'\w{3,}', query.lower()))
    if not query_tokens:
        return []

    scored = []
    for msg in messages:
        content = msg.get("content", "").lower()
        doc_tokens = set(_re.findall(r'\w{3,}', content))
        overlap = query_tokens & doc_tokens
        if len(overlap) >= 2:  # at least 2 keyword match
            score = len(overlap) / max(len(query_tokens), 1)
            scored.append((score, msg))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [m for _, m in scored[:max_results]]


def _get_history_context(session_id: str, current_query: str = "") -> str:
    """Build context from ALL conversation history.

    Includes:
    1. Last CONTEXT_RECENT messages (always)
    2. Keyword-matched older messages relevant to current query
    """
    all_msgs = _load_all_messages(session_id)
    if not all_msgs:
        return ""

    recent = all_msgs[-CONTEXT_RECENT:]
    older = all_msgs[:-CONTEXT_RECENT] if len(all_msgs) > CONTEXT_RECENT else []

    # Keyword recall from older messages
    recalled = []
    if older and current_query:
        recalled = _keyword_recall(older, current_query)

    lines = []

    if recalled:
        lines.append(f"RELEVANT OLDER MESSAGES ({len(recalled)} recalled from {len(older)} total):")
        for msg in recalled:
            prefix = "Manuel" if msg["role"] == "user" else "Wave"
            ts = msg.get("ts", "")[:16]
            lines.append(f"  [{ts}] {prefix}: {msg['content'][:500]}")
        lines.append("")

    lines.append(f"RECENT ({len(recent)} of {len(all_msgs)} total):")
    for msg in recent:
        prefix = "M" if msg["role"] == "user" else "W"
        limit = 500 if msg["role"] == "user" else 5000
        lines.append(f"  {prefix}: {msg['content'][:limit]}")

    return "\n".join(lines)


# Migrate old history format to new JSONL if it exists
def _migrate_old_history():
    old_file = os.path.join(MEMORY_DIR_PATH, "telegram_history.json")
    if os.path.exists(old_file) and not os.path.exists(CHAT_FULL_LOG):
        try:
            import json
            old = json.load(open(old_file, encoding="utf-8"))
            with open(CHAT_FULL_LOG, "a", encoding="utf-8") as f:
                for session_id, messages in old.items():
                    for msg in messages:
                        entry = {
                            "session": session_id,
                            "role": msg.get("role", "user"),
                            "content": msg.get("content", ""),
                            "ts": "2026-03-27T00:00:00",  # approximate
                        }
                        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            logging.getLogger("openclaw.telegram").info("Migrated %d sessions to JSONL", len(old))
        except Exception:
            pass

_migrate_old_history()


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

        return f"""[STATE] cycles={cycles} energy={energy:.0%} revenue=${revenue:.2f} prospects={prospects} evolves={evolves} emails={emails_sent}
Recent: {' | '.join(a.get('action','?') for a in recent)}
Manuel is talking to you via Telegram. You are Wave. Answer as the agent that has been running."""
    except Exception:
        return ""


_ACTION_VERBS = {
    "search", "find", "look", "fetch", "get", "retrieve", "check",
    "send", "email", "post", "publish", "tweet", "share",
    "analyze", "analyse", "audit", "run", "execute", "create",
    "build", "deploy", "install", "update", "fix", "debug",
    "list", "show", "display", "summarize", "summarise",
    "research", "investigate", "scrape", "download", "upload",
    "monitor", "track", "hunt", "sell", "pitch", "outreach",
    "scan", "generate", "write", "draft", "edit",
    # Portuguese — include conjugated forms (imperativo + infinitivo)
    "buscar", "busque", "procurar", "procure", "enviar", "envie",
    "postar", "poste", "analisar", "analise", "analisa",
    "criar", "crie", "construir", "construa",
    "executar", "execute", "rodar", "rode",
    "verificar", "verifique", "verifica",
    "pesquisar", "pesquise", "listar", "liste",
    "mostrar", "mostre", "mostra", "gerar", "gere",
    "escrever", "escreva", "editar", "edite",
    "configurar", "configure", "configura",
    "instalar", "instale", "atualizar", "atualize",
    "corrigir", "corrija", "consertar", "conserte",
    "testar", "teste", "testa", "deletar", "delete",
    "matar", "mate", "reiniciar", "reinicie",
    "diagnosticar", "diagnostique",
}

def _is_conversational(text: str) -> bool:
    """Return True if the message needs no tools — pure conversation."""
    words = set(text.lower().split())
    if words & _ACTION_VERBS:
        return False
    if len(text.split()) > 40:
        return False
    return True


_SSL_PROMPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts", "wave_sias_integrated.ssl")
try:
    WAVE_SYSTEM_PROMPT = open(_SSL_PROMPT_PATH, encoding="utf-8").read()
except FileNotFoundError:
    WAVE_SYSTEM_PROMPT = "You are Wave. Galmanusiano. Execute tasks. No emojis. No meta-commentary."


async def send_to_agent(message, session_id, raw_message=None, extra_system=""):
    """Envia mensagem para o OpenClaw API. Fallback to Claude Engine if API fails.

    RULE: NEVER return an error message to the user. Always produce a response.
    Fallback chain: Orchestrator API → Claude Engine (tools) → Claude Engine (bare) → static ack.
    """
    import sys, json, time as _time
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    start = _time.time()

    # ── 1. Try orchestrator API (quick probe — 10s max) ──
    # The orchestrator uses the Anthropic API directly. If it's overloaded
    # or the API key is exhausted, it responds instantly with "sobrecarregado".
    # Don't waste time waiting — probe fast and move on to Claude CLI.
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=3.0)) as client:
            resp = await client.post(
                "%s/chat" % OPENCLAW_API,
                json={"message": message, "session_id": session_id},
            )
            resp.raise_for_status()
            data = resp.json()
            response = data["response"]
            if "sobrecarregado" not in response.lower() and "tenta de novo" not in response.lower():
                return response, data.get("elapsed_seconds", 0)
            logger.info("Orchestrator overloaded, falling back to engine")
    except httpx.ConnectError:
        logger.info("Orchestrator unreachable, skipping to engine")
    except Exception as e:
        logger.info("Orchestrator failed: %s", str(e)[:80])

    # ── 2. Claude Engine — primary ──
    try:
        from claude_engine import claude_execute_with_skills, claude_chat

        # System prompt: compact identity + context (cacheable by Claude CLI)
        system = WAVE_SYSTEM_PROMPT
        if extra_system:
            system = system + "\n\n" + extra_system

        # Use raw_message for conversational detection (avoids false positives from context injection)
        detect_text = raw_message or message

        if _is_conversational(detect_text):
            logger.info("claude-engine: fast path (conversational) — sonnet/90s")
            result = await claude_chat(
                message=message,
                system_prompt=system,
                model="sonnet",
                timeout=90,
            )
        else:
            logger.info("claude-engine: full path (action) — sonnet/tools/180s/15turns")
            result = await claude_execute_with_skills(
                prompt=message,
                system_prompt=system,
                model="sonnet",
                timeout=180,
                max_turns=30,
            )

        if result.get("success") and result.get("response"):
            return result["response"], _time.time() - start

        logger.warning("Engine primary failed: %s", result.get("response", "")[:100])
    except Exception as e:
        logger.error("Engine primary exception: %s", e)

    # ── 3. LAST RESORT — sonnet, no tools, compact SSL prompt ──
    try:
        from claude_engine import claude_chat
        logger.info("claude-engine: LAST RESORT — sonnet/compact/60s")

        bare_system = WAVE_SYSTEM_PROMPT  # Keep Wave's personality even in fallback
        bare_message = raw_message or message
        # Strip context injection — just send the raw question
        if "Manuel says:" in bare_message:
            bare_message = bare_message.split("Manuel says:")[-1].strip()

        result = await claude_chat(
            message=bare_message,
            system_prompt=bare_system,
            model="sonnet",
            timeout=60,
        )

        if result.get("success") and result.get("response"):
            return result["response"], _time.time() - start
    except Exception as e:
        logger.error("Last resort failed: %s", e)

    # ── 4. STATIC — this line should never be reached, but if it is, never show an error ──
    elapsed = _time.time() - start
    logger.error("ALL FALLBACKS EXHAUSTED after %.1fs", elapsed)
    return ("Estou processando muitas coisas ao mesmo tempo. "
            "Repete a mensagem em alguns segundos que eu respondo."), elapsed


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

    # ── AUTO-DETECT MANUEL BY TELEGRAM USER ID ────────────────
    # Manuel's Telegram chat ID — auto-activates Principal Mode
    MANUEL_CHAT_ID = 7461066889  # streetxsmart / +55 47 99209 4748
    if update.effective_chat.id == MANUEL_CHAT_ID and session not in _PRINCIPAL_SESSIONS:
        _PRINCIPAL_SESSIONS.add(session)
        _save_principal_sessions()
        logger.info("PRINCIPAL MODE AUTO-ACTIVATED for Manuel (chat ID %s)", MANUEL_CHAT_ID)

    # ── PASSPHRASE DETECTION — also unlocks for other devices ─
    if PASSPHRASE in user_text.lower() or "galmanusiano" in user_text.lower():
        _PRINCIPAL_SESSIONS.add(session)
        _save_principal_sessions()
        logger.info("PRINCIPAL MODE ACTIVATED for session %s by %s", session, user_name)
        await update.message.reply_text(
            "Recognized, Manuel. Full transparency active. What do you need?\n\n"
            "232 tools. 7 cognitive layers. War doctrine. The vow is active.\n"
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
    _extra_system = ""
    if not is_principal_session(session):
        user_text = PUBLIC_MODE_PREFIX + user_text
    else:
        # Context goes into system prompt (cacheable), NOT the message body.
        # This keeps the user message small → faster inference.
        state_context = _get_autonomous_context()
        history_context = _get_history_context(session, current_query=update.message.text.strip())
        memory_context = _recall_relevant_memories(update.message.text.strip())
        sys_parts = []
        if state_context:
            sys_parts.append(state_context)
        if memory_context:
            sys_parts.append(memory_context)
        if history_context:
            sys_parts.append(history_context)
        _extra_system = "\n\n".join(sys_parts)

    # Manuel is active — stop autonomous mode, reset idle timer
    global _last_manuel_message
    if is_principal_session(session) or update.effective_chat.id == MANUEL_CHAT_ID:
        _last_manuel_message = time.time()
        _stop_autonomous()

    # Save user message to history
    _add_to_history(session, "user", update.message.text.strip())

    await update.effective_chat.send_action("typing")

    # Keep sending typing indicator while working (no "Processing..." message)
    async def keep_typing():
        while True:
            await asyncio.sleep(4)
            try:
                await update.effective_chat.send_action("typing")
            except Exception:
                break

    typing_task = asyncio.create_task(keep_typing())

    try:
        # Pass the raw user message for conversational detection (not the context-injected one)
        response, elapsed = await send_to_agent(user_text, session, raw_message=update.message.text.strip(), extra_system=_extra_system)
        typing_task.cancel()

        # Save Wave's response to history
        _add_to_history(session, "assistant", response[:500] if response else "")

        # Send response — split into Telegram-safe chunks (4096 char limit)
        await _send_long_message(update, response)

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
            await _send_long_message(update, response if 'response' in dir() else str(e))
        except Exception:
            await update.message.reply_text(str(e)[:4096])


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
        await _send_long_message(update, response)
        logger.info("[%s] Image analyzed in %.1fs", session, elapsed)

    except Exception as e:
        logger.error("Photo error: %s", e)
        await update.message.reply_text("Erro ao analisar imagem: %s" % str(e))


# -- Main --

# ── Autonomous Mode Timer ─────────────────────────────────────
# When Manuel is silent for 10+ minutes, start autonomous loop.
# When Manuel sends a message, stop autonomous and go conversational.

import subprocess
import signal
import time

_last_manuel_message = time.time()
_autonomous_process = None
IDLE_THRESHOLD = 3600  # 1 hour — temporarily increased  # 10 minutes in seconds

def _start_autonomous():
    """Start the autonomous loop as a subprocess."""
    global _autonomous_process
    if _autonomous_process and _autonomous_process.poll() is None:
        return  # Already running

    env = os.environ.copy()
    env.update({
        "HUNTER_API_KEY": os.environ.get("HUNTER_API_KEY", ""),
        "GROQ_API_KEY": os.environ.get("GROQ_API_KEY", ""),
        "GMAIL_CREDENTIALS_FILE": os.environ.get("GMAIL_CREDENTIALS_FILE", ""),
        "GMAIL_TOKEN_FILE": os.environ.get("GMAIL_TOKEN_FILE", ""),
    })

    script_dir = os.path.dirname(os.path.abspath(__file__))
    _autonomous_process = subprocess.Popen(
        ["python3", os.path.join(script_dir, "wave_autonomous.py")],
        cwd=script_dir,
        env=env,
        stdout=open("/tmp/wave_fast.log", "a"),
        stderr=subprocess.STDOUT,
    )
    logger.info("Autonomous mode STARTED (PID %s) — Manuel idle >10min", _autonomous_process.pid)

def _stop_autonomous():
    """Stop the autonomous loop — Manuel is talking."""
    global _autonomous_process
    if _autonomous_process and _autonomous_process.poll() is None:
        _autonomous_process.terminate()
        try:
            _autonomous_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _autonomous_process.kill()
        logger.info("Autonomous mode STOPPED — Manuel is active")
        _autonomous_process = None

async def _idle_checker(app):
    """Background task: check if Manuel has been silent for 10+ minutes."""
    global _last_manuel_message
    while True:
        await asyncio.sleep(60)  # Check every minute
        idle_seconds = time.time() - _last_manuel_message
        if idle_seconds >= IDLE_THRESHOLD:
            _start_autonomous()
        # If autonomous is running and Manuel just spoke, stop is handled in handle_message


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

    # Start idle checker as background task
    import asyncio
    async def post_init(application):
        asyncio.create_task(_idle_checker(application))
        # Start autonomous immediately (Manuel is not talking yet)
        _start_autonomous()

    app.post_init = post_init

    logger.info("Wave online. Autonomous when idle, conversational when active.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
