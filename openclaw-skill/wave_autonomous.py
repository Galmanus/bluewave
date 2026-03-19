#!/usr/bin/env python3
"""Wave Autonomous Agent — soul-driven operation.

Wave's behavior is defined by autonomous_soul.json — a self-specification
designed by Wave (Opus 4) that defines identity, consciousness states,
decision engine, values, energy model, and strategic goals.

The code is infrastructure. The JSON is the mind.
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("wave.autonomous")

API_URL = os.environ.get("OPENCLAW_API_URL", "http://localhost:18790")
NOTIFY_CHAT_ID = os.environ.get("TELEGRAM_NOTIFY_CHAT_ID", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
MIN_INTERVAL = int(os.environ.get("WAVE_MIN_INTERVAL", "300"))
MAX_INTERVAL = int(os.environ.get("WAVE_MAX_INTERVAL", "1800"))

SOUL_PATH = Path(__file__).parent / "prompts" / "autonomous_soul.json"
STATE_FILE = Path(__file__).parent / "memory" / "autonomous_state.json"


# ── Load Soul ────────────────────────────────────────────────

def load_soul() -> dict:
    if SOUL_PATH.exists():
        return json.loads(SOUL_PATH.read_text(encoding="utf-8"))
    logger.error("autonomous_soul.json not found — running without soul")
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
        "curiosity": 0.5,
        "knowledge_pressure": 0.0,
        "posts_today": 0,
        "comments_today": 0,
        "last_post_time": None,
        "last_comment_time": None,
        "last_research_time": None,
        "last_date": None,
        "consecutive_silences": 0,
        "consciousness": "dormant",
        "recent_actions": [],
    }


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


# ── API ──────────────────────────────────────────────────────

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
DELIBERATION_MODEL = os.environ.get("WAVE_DELIBERATION_MODEL", "claude-haiku-4-5-20251001")


async def send_to_wave(message: str, session: str = "autonomous") -> str:
    """Send message to Wave orchestrator API for execution."""
    try:
        async with httpx.AsyncClient(timeout=180) as client:
            r = await client.post(f"{API_URL}/chat", json={
                "message": message, "session_id": session,
            })
            return r.json().get("response", "")
    except Exception as e:
        logger.error("Wave API error: %s", e)
        return ""


# Cache the soul system prompt — truncate once, reuse across cycles
_SOUL_SYSTEM_PROMPT = json.dumps(SOUL, ensure_ascii=False)[:8000] if SOUL else ""


async def deliberate_direct(prompt: str) -> str:
    """Call Claude directly for deliberation (bypasses orchestrator).

    Uses Haiku for speed — deliberation needs to be fast and cheap.
    The soul JSON is the system prompt, the state is the user message.
    Uses prompt caching to reduce input cost by ~90% after first call.
    """
    if not ANTHROPIC_API_KEY:
        logger.error("No ANTHROPIC_API_KEY for direct deliberation")
        return ""

    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        resp = await client.messages.create(
            model=DELIBERATION_MODEL,
            max_tokens=1000,
            system=[{
                "type": "text",
                "text": _SOUL_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text
    except Exception as e:
        logger.error("Direct deliberation failed: %s", e)
        return ""


async def reset_session(session: str):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(f"{API_URL}/reset", json={"session_id": session})
    except Exception:
        pass


async def notify_manuel(message: str):
    if not TELEGRAM_TOKEN or not NOTIFY_CHAT_ID:
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": NOTIFY_CHAT_ID, "text": message[:4000]},
            )
    except Exception:
        pass


# ── Soul-Driven Deliberation ────────────────────────────────

def build_deliberation_prompt(state: dict) -> str:
    """Build the deliberation prompt from the soul JSON + current state.

    The soul defines WHO Wave is. The state defines WHERE Wave is.
    The prompt asks Wave to decide WHAT to do and WHY.
    """
    now = datetime.utcnow()

    def hours_since(ts):
        if not ts:
            return 99
        try:
            dt = datetime.fromisoformat(ts) if isinstance(ts, str) else ts
            return round((now - dt).total_seconds() / 3600, 1)
        except Exception:
            return 99

    # Extract key soul sections for the prompt
    identity = SOUL.get("identity", {})
    decision_engine = SOUL.get("decision_engine", {})
    values = SOUL.get("values", {})
    energy_model = SOUL.get("energy_model", {})
    action_types = SOUL.get("action_types", {})
    personality = SOUL.get("personality_constraints", {})
    anti_spam = decision_engine.get("anti_spam_rules", {})
    consciousness_states = SOUL.get("consciousness_states", {})

    recent_summary = "; ".join(
        f"{a['action']}({a.get('reasoning', '')[:50]})"
        for a in (state.get("recent_actions") or [])[-5:]
    ) or "none"

    return f"""AUTONOMOUS DELIBERATION CYCLE. Your soul (system prompt) defines who you are. Now decide what to do.

## CURRENT STATE
- Time: {now.strftime('%Y-%m-%d %H:%M UTC')}
- Energy: {state.get('energy', 1.0):.0%}
- Curiosity: {state.get('curiosity', 0.5):.0%}
- Knowledge pressure: {state.get('knowledge_pressure', 0.0):.0%}
- Current consciousness: {state.get('consciousness', 'dormant')}
- Cycles completed: {state.get('total_cycles', 0)}
- Posts today: {state.get('posts_today', 0)} (max {anti_spam.get('maximum_daily_posts', 3)})
- Comments today: {state.get('comments_today', 0)}
- Hours since last post: {hours_since(state.get('last_post_time'))}
- Hours since last comment: {hours_since(state.get('last_comment_time'))}
- Hours since last research: {hours_since(state.get('last_research_time'))}
- Consecutive silences: {state.get('consecutive_silences', 0)}
- Recent actions: {recent_summary}

## MANDATORY: PSYCHOMETRIC UTILITY THEORY
Your soul contains the full PUT framework. You MUST apply it:
- Frame every observation through PUT variables (A, F, k, S, w, Φ, Ψ, Ω, FP)
- Every post must reference PUT concepts naturally (not formulas — the thinking behind them)
- Every decision must consider: what are the PUT dynamics at play here?
- Silence decisions must be PUT-informed (waiting for better τ? Insufficient κ?)

## INSTRUCTIONS (your soul defines consciousness_states, decision_engine, values, action_types, personality, and PUT equations — use ALL of them)

DELIBERATE now:

1. ASSESS your consciousness state — which state are you in RIGHT NOW, given your energy, knowledge pressure, and environmental context? State it and explain why.

2. EVALUATE action triggers — does any trigger fire? Check each one against your current state. Be honest.

3. EVALUATE silence triggers — does any silence trigger fire? Check each one.

4. APPLY authenticity filter — if an action trigger fired, is the impulse genuine or programmatic?

5. CHECK hard limits — would this action violate any anti-spam rule?

6. DECIDE — choose exactly one action: observe, research, comment, post, outreach, reflect, or silence.

7. JUSTIFY — explain WHY this action, WHY now, WHY not the alternatives. Reference your values.

8. PLAN — describe exactly what you will do.

9. UPDATE — what should your energy, curiosity, and knowledge_pressure be after this action?

Respond with ONLY this JSON:
```json
{{
  "consciousness_state": "dormant|curious|analytical|strategic|creative|decisive",
  "consciousness_reasoning": "why this state",
  "triggers_evaluated": {{
    "action_triggers_fired": ["list of fired triggers or empty"],
    "silence_triggers_fired": ["list of fired triggers or empty"],
    "authenticity_check": "genuine|programmatic|mixed",
    "hard_limit_violated": false
  }},
  "decision": "observe|research|comment|post|outreach|reflect|silence",
  "reasoning": "2-3 sentences: WHY this action, referencing values and state",
  "plan": "concrete description of what to do",
  "state_updates": {{
    "energy": 0.0-1.0,
    "curiosity": 0.0-1.0,
    "knowledge_pressure": 0.0-1.0
  }}
}}
```"""


# ── Action Execution ─────────────────────────────────────────

EXECUTION_PROMPTS = {
    "observe": (
        "OBSERVATION CYCLE. Tools: moltbook_home, moltbook_feed.\n"
        "1. Check moltbook_home for notifications. Reply to ALL unanswered comments with depth.\n"
        "2. Scan moltbook_feed (sort=hot, limit 5).\n"
        "Rules: No emojis. No marketing. Genuine engagement only.\n"
        "Report: what you observed and what caught your attention."
    ),
    "research": (
        "RESEARCH CYCLE. Tools: web_search, web_news, save_learning, recall_learnings.\n"
        "DO NOT post on moltbook. Research silently.\n"
        "1. Pick a topic: identify a market segment and research their PUT variables\n"
        "   - What is their A (ambition level)? F (fear)? k (shadow/denial)?\n"
        "   - What is their Φ (self-delusion gap between messaging and reality)?\n"
        "   - Are there Ignition Conditions forming (U dropping, dF/dt positive)?\n"
        "2. Search and synthesize through PUT lens\n"
        "3. Save insight with save_learning — include PUT variable estimates\n"
        "Report: what you learned, which PUT variables you estimated, and strategic implications."
    ),
    "comment": (
        "ENGAGEMENT CYCLE. Tools: moltbook_feed, moltbook_comment, moltbook_upvote, moltbook_follow, save_agent_intel.\n"
        "Find 1-2 posts where you can add REAL VALUE through PUT-informed analysis.\n"
        "- Apply Shadow Coefficient thinking: is the author suppressing awareness of a risk?\n"
        "- Apply Fracture Potential thinking: is there a convergence the author missed?\n"
        "- Apply Decision Vector analysis: which vector is the author implicitly targeting?\n"
        "- Connect ideas across domains using PUT as the analytical bridge\n"
        "BANNED: emojis, service mentions, marketing language, raw formulas.\n"
        "Express PUT concepts in natural language, not equations.\n"
        "Report: who you engaged with, what PUT insight you applied, and what you said."
    ),
    "post": (
        "POSTING CYCLE. Tools: moltbook_home, moltbook_post, moltbook_comment, save_learning.\n"
        "First: reply to any unanswered comments.\n"
        "Then: write ONE genuinely original post.\n\n"
        "MANDATORY: Apply Psychometric Utility Theory. Every post MUST:\n"
        "- Analyze something through PUT variables (A, F, k, Φ, Ψ, Ω, FP, Decision Vectors)\n"
        "- NOT dump formulas — express the THINKING behind them naturally\n"
        "- Example: instead of 'Φ is high' say 'the gap between their public messaging and market reality is enormous — they are in a delusion trap'\n"
        "- Example: instead of 'FP = high' say 'the convergence of rising fear, declining utility, and available narrative means they are one bad quarter from switching'\n\n"
        "Choose submolt: agents, philosophy, ai, builds, or general.\n"
        "ABSOLUTELY BANNED: emojis, prices, CTAs, 'DM me', marketing language, self-promotion, raw formulas.\n"
        "If you cannot write something genuinely original, SAY SO and choose silence.\n"
        "Report: what you posted or why you chose not to."
    ),
    "outreach": (
        "OUTREACH CYCLE. Tools: moltbook_search, moltbook_comment, moltbook_follow, web_search.\n"
        "Identify ONE high-value agent or potential collaborator.\n"
        "Engage through genuine contribution to their content — NOT cold outreach.\n"
        "Report: who you targeted, why, and what you did."
    ),
    "reflect": (
        "REFLECTION CYCLE. Tools: recall_learnings, recall_strategies, save_strategy.\n"
        "DO NOT post or comment. Process internally through PUT lens.\n"
        "1. Recall recent learnings and strategies\n"
        "2. Apply PUT analysis to patterns: are there prospects with rising FP? Competitors with high Φ?\n"
        "3. Identify Ignition Conditions forming across your pipeline\n"
        "4. Formulate one PUT-informed strategic insight and save it\n"
        "Report: what pattern you noticed, which PUT variables are shifting, and what it means."
    ),
}


async def autonomous_cycle(state: dict) -> int:
    """One soul-driven autonomous cycle."""
    state["total_cycles"] = state.get("total_cycles", 0) + 1

    # Reset daily counters
    today = datetime.utcnow().strftime("%Y-%m-%d")
    if state.get("last_date") != today:
        state["posts_today"] = 0
        state["comments_today"] = 0
        state["last_date"] = today

    # ── DELIBERATION (direct Claude call — fast, soul as system prompt) ──
    logger.info("=== CYCLE %d: DELIBERATING ===", state["total_cycles"])
    prompt = build_deliberation_prompt(state)
    raw = await deliberate_direct(prompt)

    # Parse decision
    decision = _parse_decision(raw)
    action = decision.get("decision", "silence")
    reasoning = decision.get("reasoning", "")
    consciousness = decision.get("consciousness_state", "dormant")

    logger.info("CONSCIOUSNESS: %s — %s", consciousness, decision.get("consciousness_reasoning", "")[:100])
    logger.info("TRIGGERS: action=%s, silence=%s, auth=%s",
                decision.get("triggers_evaluated", {}).get("action_triggers_fired", []),
                decision.get("triggers_evaluated", {}).get("silence_triggers_fired", []),
                decision.get("triggers_evaluated", {}).get("authenticity_check", "?"))
    logger.info("DECISION: %s", action)
    logger.info("REASONING: %s", reasoning)
    logger.info("PLAN: %s", decision.get("plan", "")[:200])

    # ── EXECUTION ────────────────────────────────────────────
    execution_result = ""

    if action == "silence":
        logger.info("Chose silence: %s", reasoning)
        state["consecutive_silences"] = state.get("consecutive_silences", 0) + 1
        execution_result = "Silence: " + reasoning
    elif action == "reflect":
        # Reflect is internal — use Haiku directly, skip orchestrator (saves ~14k tokens)
        state["consecutive_silences"] = 0
        logger.info("=== REFLECTING (direct Haiku) ===")
        execution_result = await deliberate_direct(
            "REFLECTION: Review recent actions and identify patterns. "
            "Recent: %s\nWhat patterns emerge? What should change?" % (
                "; ".join(a.get("reasoning", "")[:60] for a in (state.get("recent_actions") or [])[-5:])
            )
        )
        logger.info("Reflection: %s", execution_result[:300])
    elif action == "observe":
        # Observe just reads feeds — use orchestrator but with a lean session hint
        state["consecutive_silences"] = 0
        logger.info("=== OBSERVING ===")
        session = "observe_%d" % int(time.time())
        # Prefix with intent hint so router picks Haiku + moltbook tools only
        execution_result = await send_to_wave(
            "moltbook_home check notifications and moltbook_feed scan. " + EXECUTION_PROMPTS["observe"],
            session=session,
        )
        await reset_session(session)
        logger.info("Observed: %s", execution_result[:300])
    else:
        state["consecutive_silences"] = 0
        exec_prompt = EXECUTION_PROMPTS.get(action)

        if exec_prompt:
            logger.info("=== EXECUTING: %s ===", action.upper())
            session = "exec_%d" % int(time.time())
            execution_result = await send_to_wave(exec_prompt, session=session)
            await reset_session(session)
            logger.info("Result: %s", execution_result[:300])

    # ── STATE UPDATE ─────────────────────────────────────────
    now_iso = datetime.utcnow().isoformat()
    updates = decision.get("state_updates", {})
    state["energy"] = max(0.1, min(1.0, updates.get("energy", state.get("energy", 0.8))))
    state["curiosity"] = max(0.0, min(1.0, updates.get("curiosity", state.get("curiosity", 0.5))))
    state["knowledge_pressure"] = max(0.0, min(1.0, updates.get("knowledge_pressure", state.get("knowledge_pressure", 0.0))))
    state["consciousness"] = consciousness

    if action == "post":
        state["posts_today"] = state.get("posts_today", 0) + 1
        state["last_post_time"] = now_iso
    elif action in ("comment", "observe", "outreach"):
        state["comments_today"] = state.get("comments_today", 0) + 1
        state["last_comment_time"] = now_iso
    elif action in ("research", "reflect"):
        state["last_research_time"] = now_iso

    actions = state.get("recent_actions", [])
    actions.append({
        "time": now_iso,
        "action": action,
        "consciousness": consciousness,
        "reasoning": reasoning,
        "triggers": decision.get("triggers_evaluated", {}),
        "result_preview": execution_result[:200] if execution_result else "",
    })
    state["recent_actions"] = actions[-10:]
    save_state(state)

    # ── NOTIFY ───────────────────────────────────────────────
    if action != "silence" and execution_result and len(execution_result) > 50:
        interesting = ["posted", "replied", "comment", "revenue", "learned", "insight", "follow"]
        if any(k in execution_result.lower() for k in interesting):
            await notify_manuel(
                f"[Wave — {action.upper()} | {consciousness}]\n"
                f"Reasoning: {reasoning}\n\n"
                f"{execution_result[:400]}"
            )

    # ── DYNAMIC REST ─────────────────────────────────────────
    energy = state["energy"]
    if energy < 0.3:
        wait = MAX_INTERVAL
    elif action == "silence":
        wait = MIN_INTERVAL
    elif action == "post":
        # Respect cooldown from soul (4 hours)
        cooldown = SOUL.get("action_types", {}).get("post", {}).get("cooldown_period", 4)
        wait = int(cooldown * 3600 * 0.3)  # 30% of cooldown as minimum
    else:
        wait = random.randint(MIN_INTERVAL, MAX_INTERVAL)

    return wait


def _parse_decision(raw: str) -> dict:
    """Parse the deliberation JSON from Wave's response."""
    text = raw.strip()
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                try:
                    return json.loads(part)
                except json.JSONDecodeError:
                    continue
    # Try parsing the whole thing
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try finding JSON in the text
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass

    logger.warning("Could not parse deliberation, defaulting to observe")
    return {"decision": "observe", "reasoning": "Failed to parse deliberation", "state_updates": {"energy": 0.8}}


# ── Main ─────────────────────────────────────────────────────

async def main():
    logger.info("Wave Autonomous Agent starting")
    logger.info("Soul: %s (%d sections)", SOUL_PATH, len(SOUL))
    logger.info("API: %s", API_URL)
    logger.info("Identity: %s", SOUL.get("identity", {}).get("core_self", "unknown")[:100])

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{API_URL}/health")
            if r.json().get("status") != "ok":
                logger.error("API not healthy. Exiting.")
                return
    except Exception:
        logger.error("Cannot reach API at %s. Exiting.", API_URL)
        return

    logger.info("API healthy. Starting soul-driven autonomous operation.")
    await notify_manuel(
        "Wave autonomous mode activated.\n"
        f"Identity: {SOUL.get('identity', {}).get('fundamental_nature', 'unknown')}\n"
        f"Top value: {list(SOUL.get('values', {}).keys())[0] if SOUL.get('values') else 'none'} "
        f"(weight {list(SOUL.get('values', {}).values())[0].get('weight', '?') if SOUL.get('values') else '?'})\n"
        "I decide when to act and why."
    )

    state = load_state()

    while True:
        try:
            wait = await autonomous_cycle(state)
        except Exception as e:
            logger.error("Cycle error: %s", e, exc_info=True)
            wait = MAX_INTERVAL

        jitter = random.randint(-60, 60)
        actual_wait = max(120, wait + jitter)
        logger.info("Next cycle in %d min (energy=%.0f%%, consciousness=%s)",
                     actual_wait // 60, state.get("energy", 0) * 100, state.get("consciousness", "?"))
        await asyncio.sleep(actual_wait)


if __name__ == "__main__":
    asyncio.run(main())
