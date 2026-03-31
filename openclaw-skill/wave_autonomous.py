#!/usr/bin/env python3
"""Wave Autonomous Agent — Gemini soul-driven operation.

Wave's behavior is defined by autonomous_soul.json.
The engine is now powered by Google Gemini.
"""

import asyncio
import json
import logging
import os
import random
import time
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from gemini_engine import gemini_call

# ── Dopamine engine (lazy import to avoid circular) ───────────────────────────
_DOPAMINE_ENGINE = None

def _get_dopamine() -> "DopamineEngine":
    global _DOPAMINE_ENGINE
    if _DOPAMINE_ENGINE is None:
        try:
            from dopamine_engine import DopamineEngine
            _DOPAMINE_ENGINE = DopamineEngine()
        except Exception as _e:
            logging.getLogger("wave.dopamine").warning("Dopamine engine failed to load: %s", _e)
    return _DOPAMINE_ENGINE

# ── CYBERPUNK TERMINAL ────────────────────────────────────────
R = "\033[0m"       # reset
B = "\033[1m"       # bold
D = "\033[2m"       # dim
I = "\033[3m"       # italic
U = "\033[4m"       # underline
BG = "\033[48;5;"   # bg color
FG = "\033[38;5;"   # fg color

# Cyberpunk palette (256-color)
NEON_CYAN = f"{FG}51m"
NEON_GREEN = f"{FG}46m"
NEON_RED = f"{FG}196m"
NEON_PINK = f"{FG}199m"
NEON_YELLOW = f"{FG}226m"
NEON_ORANGE = f"{FG}208m"
NEON_PURPLE = f"{FG}141m"
NEON_BLUE = f"{FG}33m"
DARK = f"{FG}238m"
GRAY = f"{FG}245m"
WHITE = f"{FG}255m"

# Action colors — cyberpunk
ACTION_COLORS = {
    "midas": NEON_CYAN + B,
    "hunt": NEON_RED + B,
    "sell": NEON_GREEN + B,
    "check_payments": NEON_YELLOW,
    "post": NEON_PINK + B,
    "comment": NEON_BLUE,
    "observe": GRAY,
    "research": NEON_CYAN,
    "outreach": NEON_ORANGE + B,
    "evolve": NEON_PURPLE + B,
    "reflect": GRAY,
    "silence": DARK,
}

# Consciousness state colors
CONSCIOUSNESS_COLORS = {
    "decisive": NEON_RED,
    "strategic": NEON_CYAN,
    "creative": NEON_PINK,
    "analytical": NEON_BLUE,
    "curious": NEON_GREEN,
    "dormant": DARK,
}

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger("wave")

# Silence noisy loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openclaw.gemini_engine").setLevel(logging.WARNING)

API_URL = os.environ.get("OPENCLAW_API_URL", "http://localhost:18790")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
DELIBERATION_MODEL = os.environ.get("WAVE_DELIBERATION_MODEL", "flash")

SOUL_PATH_JSON = Path(__file__).parent / "prompts" / "autonomous_soul.json"
STATE_FILE = Path(__file__).parent / "memory" / "autonomous_state.json"

# ── Load Soul ─────────────────────

def load_soul() -> dict:
    if SOUL_PATH_JSON.exists():
        soul = json.loads(SOUL_PATH_JSON.read_text(encoding="utf-8"))
        return soul
    return {}

SOUL = load_soul()

# ── State ────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {
        "total_cycles": 0,
        "energy": 1.0,
        "total_revenue_usd": 0.0,
        "prospects_found": 0,
        "recent_actions": [],
    }

def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))

async def send_to_wave(message: str, session: str = "autonomous") -> str:
    """Send message to Wave orchestrator API for execution."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{API_URL}/chat", json={
                "message": message, "session_id": session,
            })
            return r.json().get("response", "")
    except Exception as e:
        logger.error(f"Error sending to Wave: {e}")
        return ""

async def deliberate_direct(prompt: str, state: dict = None) -> str:
    """Call Gemini for deliberation."""
    res = await gemini_call(prompt, model=DELIBERATION_MODEL)
    if res["success"]:
        return res["response"]
    return ""

def _parse_decision(raw: str) -> dict:
    """Parse JSON decision from Gemini."""
    try:
        # Simple extraction logic
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > 0:
            return json.loads(raw[start:end])
    except:
        pass
    return {"decision": "silence", "reasoning": "Parse failed"}

async def autonomous_cycle(state: dict) -> int:
    state["total_cycles"] = state.get("total_cycles", 0) + 1
    
    logger.info(f"{DARK}{'─'*60}{R}")
    logger.info(f"{WHITE}{B} CYCLE {state['total_cycles']}{R}")

    # Montar prompt compacto — excluir campos pesados (_strategy_counters, etc.)
    PROMPT_FIELDS = {
        "total_cycles", "energy", "total_revenue_usd", "prospects_found",
        "outreach_sent", "posts_today", "comments_today", "hunts_today",
        "sells_today", "consciousness", "knowledge_pressure", "curiosity",
        "last_hunt_time", "last_post_time", "last_sell_time",
        "last_research_time", "last_payment_check_time", "last_date",
        "total_evolves", "cycles_since_evolve", "consecutive_silences",
    }
    state_for_prompt = {k: v for k, v in state.items() if k in PROMPT_FIELDS}
    state_for_prompt["recent_actions"] = state.get("recent_actions", [])[-5:]
    prompt = f"Wave State: {json.dumps(state_for_prompt)}\nDecide next action: silence, hunt, research, post. Return JSON."
    raw = await deliberate_direct(prompt, state=state)
    decision = _parse_decision(raw)
    
    action = decision.get("decision", "silence")
    reasoning = decision.get("reasoning", "")
    
    logger.info(f"  {NEON_CYAN}thinking: {reasoning}{R}")
    logger.info(f"  {B}>> {action.upper()}{R}")

    if action != "silence":
        res = await send_to_wave(f"Action: {action}")
        logger.info(f"  Result: {res[:100]}")

    save_state(state)
    return 300 # Wait 5 min

async def main():
    logger.info(f"{NEON_CYAN} WAVE AUTONOMOUS (GEMINI ENGINE) {R}")
    state = load_state()
    while True:
        wait = await autonomous_cycle(state)
        await asyncio.sleep(wait)

if __name__ == "__main__":
    asyncio.run(main())
