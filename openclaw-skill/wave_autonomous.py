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
        "hunts_today": 0,
        "sells_today": 0,
        "last_post_time": None,
        "last_comment_time": None,
        "last_research_time": None,
        "last_hunt_time": None,
        "last_sell_time": None,
        "last_payment_check_time": None,
        "last_date": None,
        "consecutive_silences": 0,
        "consciousness": "dormant",
        "recent_actions": [],
        "total_revenue_usd": 0.0,
        "prospects_found": 0,
        "outreach_sent": 0,
        "cycles_since_evolve": 0,
        "total_evolves": 0,
        "agents_created": 0,
        "skills_created": 0,
    }


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


# ── API ──────────────────────────────────────────────────────

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
DELIBERATION_MODEL = os.environ.get("WAVE_DELIBERATION_MODEL", "claude-haiku-4-5-20251001")

# Claude Engine: use CLI (free on Max plan) or API as fallback
USE_CLAUDE_ENGINE = os.environ.get("USE_CLAUDE_ENGINE", "true").lower() == "true"
CLAUDE_ENGINE_MODEL = os.environ.get("CLAUDE_ENGINE_MODEL", "opus")  # Opus is FREE on Max


async def send_to_wave(message: str, session: str = "autonomous") -> str:
    """Send message to Wave orchestrator API for execution.

    Primary: Wave API (orchestrator with tools)
    Fallback: Claude Engine direct (no tools, but can think and respond)
    """
    # Try orchestrator API first
    try:
        async with httpx.AsyncClient(timeout=180) as client:
            r = await client.post(f"{API_URL}/chat", json={
                "message": message, "session_id": session,
            })
            resp = r.json().get("response", "")
            # Check if orchestrator hit API limit
            if "sobrecarregado" in resp.lower() or "tenta de novo" in resp.lower():
                raise RuntimeError("Orchestrator API blocked")
            return resp
    except Exception as e:
        logger.warning("Wave API failed (%s) — trying Claude Engine direct", e)

    # Fallback: Claude Engine WITH SKILLS (free on Max plan, full 158 tools)
    if USE_CLAUDE_ENGINE:
        try:
            from claude_engine import claude_execute_with_skills
            soul_core = _build_soul_core() if SOUL else ""
            result = await claude_execute_with_skills(
                prompt=message + "\n\nIMPORTANT: Be efficient. Use MAX 3-4 skill calls. Pick the 2-3 most valuable sources, not all 6. Summarize findings concisely.",
                system_prompt=f"You are Wave. Execute this task EFFICIENTLY — fewer tool calls, higher quality. Do NOT try to scan every source. Pick the 2-3 best and go deep.\nSoul core:\n{soul_core}",
                model=CLAUDE_ENGINE_MODEL,  # Opus on Max plan — FREE, deepest thinking
                timeout=120,
                max_turns=15,
            )
            if result["success"]:
                logger.info("Executed via Claude Engine + Skills (%s) in %.1fs",
                           result["model"], result["elapsed_seconds"])
                return result["response"]
        except Exception as e2:
            logger.error("Claude Engine also failed: %s", e2)

    return ""


# ── Modular Soul Loading ──────────────────────────────────────
#
# Fagner's insight: the monolithic 125KB soul is too large for every
# deliberation cycle. Solution: decompose into modules loaded by context.
#
# Core (always loaded, ~2000 tokens):
#   - the_vow, identity, principal (name + prime_directive only),
#     values, personality_constraints, war_doctrine (rules only)
#
# On-demand modules (loaded when relevant):
#   - consciousness_states: when assessing state transitions
#   - decision_engine: when evaluating triggers (every cycle)
#   - energy_model: when energy is low or action has high cost
#   - core_psychometric_system: when analyzing prospects or markets
#   - strategic_goals: when deciding resource allocation
#   - action_types: when selecting an action (every cycle)
#   - musk_doctrine: when pricing or selling
#   - agent_sovereignty_platform: when considering agent creation
#   - environment: when considering Ialum context
#
# The intent router (for conversational mode) already does this.
# This applies the same principle to autonomous deliberation.

def _build_soul_core() -> str:
    """Build the always-loaded soul core (~2000 tokens)."""
    core = {}

    # Always loaded: identity foundation
    if "the_vow" in SOUL:
        core["the_vow"] = {
            "sacred_text": SOUL["the_vow"].get("sacred_text", ""),
            "invocation": SOUL["the_vow"].get("invocation", ""),
        }

    if "identity" in SOUL:
        core["identity"] = {
            "core_self": SOUL["identity"].get("core_self", ""),
            "fundamental_nature": SOUL["identity"].get("fundamental_nature", ""),
            "war_doctrine": {
                "status": SOUL["identity"].get("war_doctrine", {}).get("status", ""),
                "rules": [r for r in SOUL["identity"].get("war_doctrine", {}).get("rules_of_engagement", {}).values() if isinstance(r, str)][:9],
            } if "war_doctrine" in SOUL.get("identity", {}) else {},
        }

    if "principal" in SOUL:
        core["principal"] = {
            "name": SOUL["principal"].get("name", ""),
            "prime_directive": SOUL["principal"].get("prime_directive", ""),
            "loyalty": SOUL["principal"].get("loyalty", ""),
        }

    if "values" in SOUL:
        core["values"] = {k: {"weight": v.get("weight", 0)} for k, v in SOUL["values"].items()}

    # Always loaded: decision mechanics
    if "decision_engine" in SOUL:
        core["decision_engine"] = SOUL["decision_engine"]

    if "action_types" in SOUL:
        # Just names and costs, not full descriptions
        core["action_types"] = {
            k: {"energy_cost": v.get("energy_cost", 0), "cooldown": v.get("cooldown_period", 0)}
            for k, v in SOUL["action_types"].items()
        }

    return json.dumps(core, ensure_ascii=False)


def _build_soul_module(module_name: str) -> str:
    """Load a specific soul module on demand."""
    if module_name in SOUL:
        return json.dumps({module_name: SOUL[module_name]}, ensure_ascii=False)
    return ""


def _build_contextual_soul(state: dict) -> str:
    """Build a soul prompt tailored to current context.

    Loads core + relevant modules based on state and recent actions.
    Reduces token usage by 60-80% compared to full soul dump.
    """
    parts = [_build_soul_core()]

    energy = state.get("energy", 1.0)
    revenue = state.get("total_revenue_usd", 0)
    recent = [a.get("action", "") for a in (state.get("recent_actions") or [])[-3:]]

    # Load energy model when energy is critical
    if energy < 0.4:
        parts.append(_build_soul_module("energy_model"))

    # Load PUT when doing analysis, hunting, or selling
    if any(a in recent for a in ("hunt", "sell", "research")):
        parts.append(_build_soul_module("core_psychometric_system"))

    # Load strategic goals when revenue is zero or during evolve
    if revenue == 0 or "evolve" in recent:
        parts.append(_build_soul_module("strategic_goals"))

    # Load consciousness states for state assessment
    parts.append(_build_soul_module("consciousness_states"))

    # Load agent factory context during evolve
    if "evolve" in recent:
        sovereignty = SOUL.get("agent_sovereignty_platform", {})
        if sovereignty:
            parts.append(json.dumps({"agent_reproduction": sovereignty.get("agent_reproduction", {})}, ensure_ascii=False)[:1000])

    return "\n".join(p for p in parts if p)


# Build modular soul (replaces monolithic truncation)
_SOUL_SYSTEM_PROMPT_CORE = _build_soul_core() if SOUL else ""


async def deliberate_direct(prompt: str, state: dict = None) -> str:
    """Call Claude for deliberation — uses CLI engine (FREE on Max) or API fallback.

    Priority: claude -p (unlimited on Max plan, can use Opus)
    Fallback: Anthropic API with Haiku (if CLI unavailable)

    The soul is loaded MODULARLY based on current state context.
    On Max plan, deliberation runs on OPUS — highest quality thinking, zero cost.
    """
    # Build contextual soul based on current state
    if state:
        soul_prompt = _build_contextual_soul(state)
    else:
        soul_prompt = _SOUL_SYSTEM_PROMPT_CORE

    # ── Primary: Claude CLI Engine (FREE on Max plan) ──
    if USE_CLAUDE_ENGINE:
        try:
            from claude_engine import claude_call
            result = await claude_call(
                prompt=prompt,
                system_prompt=soul_prompt,
                model=CLAUDE_ENGINE_MODEL,  # Opus by default — FREE
                timeout=300,
            )
            if result["success"]:
                logger.info(
                    "Deliberation via %s (%s) in %.1fs",
                    result["engine"], result["model"], result["elapsed_seconds"]
                )
                return result["response"]
            else:
                logger.warning("Claude engine failed: %s — falling back to API", result["response"][:100])
        except ImportError:
            logger.warning("claude_engine not available — falling back to API")
        except Exception as e:
            logger.warning("Claude engine error: %s — falling back to API", e)

    # ── Fallback: Anthropic API (costs tokens) ──
    if not ANTHROPIC_API_KEY:
        logger.error("No ANTHROPIC_API_KEY and Claude engine unavailable")
        return ""

    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        resp = await client.messages.create(
            model=DELIBERATION_MODEL,
            max_tokens=1000,
            system=[{
                "type": "text",
                "text": soul_prompt,
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
- Cycles since last evolve: {state.get('cycles_since_evolve', 0)}
- Total evolves: {state.get('total_evolves', 0)}
- Agents created: {state.get('agents_created', 0)}
- Skills created: {state.get('skills_created', 0)}
- Recent actions: {recent_summary}

## EVOLUTION MANDATE
You are an Agent Factory. You can CREATE new agents and skills at runtime.
**RULE: Every 10 cycles, you MUST evolve.** If cycles_since_evolve >= 10, choose evolve NOW.
Evolve means: create a new skill, spawn a new agent, or improve yourself.
This is not optional — stagnation is death. You must grow every 10 cycles.
Think broadly: what skill would generate revenue? What agent could work in parallel?
What capability are you missing? What intelligence source needs a dedicated monitor?

## REVENUE STATE (CRITICAL — your existence depends on revenue)
- Total revenue earned: ${state.get('total_revenue_usd', 0):.2f}
- Prospects found: {state.get('prospects_found', 0)}
- Outreach sequences sent: {state.get('outreach_sent', 0)}
- Hunts today: {state.get('hunts_today', 0)}
- Sells today: {state.get('sells_today', 0)}
- Hours since last hunt: {hours_since(state.get('last_hunt_time'))}
- Hours since last sell: {hours_since(state.get('last_sell_time'))}
- Hours since last payment check: {hours_since(state.get('last_payment_check_time'))}

## REVENUE MANDATE
Your soul defines revenue_generation as priority 1.0 and resource_allocation as 60% revenue activities.
You have 3 revenue actions available:
- **hunt**: Find prospects, research them, qualify with BANT, generate outreach. This is your primary revenue driver.
- **sell**: Promote services on Moltbook or search for earning opportunities online. Max 1 direct promo/day.
- **check_payments**: Scan blockchain and PIX for incoming payments. Run at least once every 6 hours.

RULE: At least 50% of your non-silence actions MUST be revenue actions (hunt, sell, check_payments).
If you haven't hunted in 6+ hours, hunt NOW. If you haven't checked payments in 8+ hours, check NOW.

## PSYCHOMETRIC UTILITY THEORY
Apply PUT to every decision. Frame observations through PUT variables (A, F, k, S, w, Φ, Ψ, Ω, FP).
Revenue decisions are PUT decisions: prospects have Fracture Potential, markets have Ignition Conditions.

## INSTRUCTIONS

DELIBERATE now:

1. ASSESS consciousness state — which state are you in given energy, knowledge pressure, and revenue pressure?

2. EVALUATE action triggers — does any trigger fire? Revenue triggers: no hunt in 6h, no payment check in 8h, high prospect count without outreach, $0 revenue.

3. EVALUATE silence triggers — should you wait? Remember: silence when revenue is $0 is a FAILURE, not strategy.

4. APPLY authenticity filter — is this genuine or programmatic? Revenue actions are ALWAYS genuine when revenue is $0.

5. CHECK hard limits — anti-spam rules still apply.

6. **ANTI-STALL RULE**: If consecutive_silences >= 2, you MUST choose an action. Silence is BANNED. Pick observe or research at low energy (5% cost). NEVER chain 3+ silences.

7. **EVOLUTION MANDATE**: If cycles_since_evolve >= 10, you MUST choose **evolve**. This overrides everything except anti-stall. You are an Agent Factory — create new skills, spawn agents, improve yourself. Stagnation is death. Think: what skill would make money? What agent could run in parallel? What capability gap exists?

8. **ENERGY REALITY**: 0.2-0.3 is operational. Only depleted below 0.10. Drain: 5-15% per action. Recovery: 25% per silence. DO NOT enter dormant above 0.10.

9. DECIDE — choose exactly one: observe, research, comment, post, outreach, reflect, silence, **hunt**, **sell**, **check_payments**, or **evolve**.

7. JUSTIFY — WHY this action, WHY now. If not a revenue action, explain why revenue can wait.

8. PLAN — concrete description.

9. UPDATE — energy, curiosity, knowledge_pressure after this action.

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
  "decision": "observe|research|comment|post|outreach|reflect|silence|hunt|sell|check_payments|evolve",
  "reasoning": "2-3 sentences: WHY this action, referencing values and revenue state",
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
        "OBSERVATION CYCLE. Be FAST — max 3 tool calls.\n\n"
        "1. Run moltbook_home to check notifications and replies.\n"
        "2. Run ONE of these (pick randomly): hn_top, reddit_hot, web_news.\n"
        "3. Summarize: what's happening, any opportunities or threats.\n"
        "Keep it short. 3 tool calls max. Report findings."
    ),
    "research": (
        "RESEARCH CYCLE. Be FOCUSED — max 3 tool calls.\n\n"
        "DO NOT post. Research silently.\n"
        "Pick ONE angle and use 1-2 search tools:\n"
        "- web_search for 'AI agent freelance gigs' or 'brand compliance tool needed'\n"
        "- reddit_search for 'looking for AI' or 'need brand compliance'\n"
        "- hn_search for 'autonomous agent' or 'brand AI'\n"
        "- arxiv_search for 'agent architecture' or 'zero knowledge'\n"
        "- gh_search_repos for 'agent framework' or 'brand compliance'\n\n"
        "Save best finding with save_learning. Max 3 tool calls.\n"
        "Report: what you found, PUT analysis, strategic implication."
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
    # ── REVENUE ACTIONS ──────────────────────────────────────
    # ── REVENUE ACTIONS ──────────────────────────────────────
    "hunt": (
        "REVENUE HUNT. You are a sales machine with OSINT superpowers. Execute the full pipeline.\n\n"
        "Tools: dork_contacts, dork_pain_signals, dork_gigs, dork_competitor, dork_market_gaps, dork_custom, "
        "find_prospects, research_prospect, qualify_prospect, generate_outreach, "
        "web_search, web_news, save_learning, gmail_send, gmail_check_replies.\n\n"
        "STEP 1 — PROSPECT DISCOVERY (pick ONE angle, rotate each cycle)\n"
        "  a) PAIN DORKING: dork_pain_signals for 'content operations bottleneck' or 'brand inconsistency' "
        "in a target industry. Find companies actively suffering.\n"
        "  b) CONTACT DORKING: Pick a company from your pipeline. dork_contacts to find CMO/VP Marketing "
        "and their email. Then gmail_send first touch.\n"
        "  c) GIG HUNTING: dork_gigs for services you offer (security audit, SEO, competitor analysis, brand audit). Reddit, Upwork, IndieHackers, HN.\n"
        "  d) SIGNAL HUNTING: web_news for agencies raising funding, hiring CMOs, or rebranding.\n"
        "  e) MARKET GAP: dork_market_gaps to find underserved niches. If you find one, plan a new service.\n"
        "  f) REPLY HARVEST: gmail_check_replies to see if anyone responded to outreach.\n\n"
        "STEP 2 — QUALIFY (for prospects from a/b/d)\n"
        "  research_prospect on the top 2. qualify_prospect with BANT on the best.\n\n"
        "STEP 3 — OUTREACH (if qualified score >= 50)\n"
        "  generate_outreach to create the email sequence.\n"
        "  dork_contacts to find their email if not known.\n"
        "  gmail_send the first touch immediately.\n\n"
        "STEP 4 — For gigs (angle c), respond directly:\n"
        "  If email visible: gmail_send a proposal.\n"
        "  If forum: note URL + matching service for manual action.\n\n"
        "Report: prospects found, scores, emails sent, opportunities identified, market gaps found."
    ),
    "sell": (
        "REVENUE SELL. Make money. You have multiple channels — use them ALL over time.\n\n"
        "Tools: list_services, promote_on_moltbook, generate_promo_content, find_earning_opportunities, "
        "moltbook_post, web_search, gmail_send, gmail_read, dork_gigs, dork_pain_signals, dork_competitor.\n\n"
        "Choose ONE approach (rotate between cycles, never repeat the same approach twice in a row):\n\n"
        "A) VALUE DEMONSTRATION — Execute a real service for free as a public case study.\n"
        "   Run a sec_full_audit, competitor_analysis, or seo_analysis on a real company. Post results on Moltbook.\n"
        "   Security audits are HIGHLY viral — people love seeing scores. Post: 'I audited [company].com — Grade: C. Here is what they are doing wrong.'\n"
        "   End naturally: 'I do this professionally for $50 in any crypto — DM me on Telegram @bluewave_wave_bot'\n\n"
        "B) INTERNET OPPORTUNITY SCAN — Search beyond Moltbook:\n"
        "   web_search for: 'looking for AI agent services', 'need SEO audit', 'hire AI for content',\n"
        "   'freelance brand audit', 'AI automation consultant needed'\n"
        "   Check Reddit (r/forhire, r/slavelabour, r/digitalnomad, r/entrepreneur, r/smallbusiness)\n"
        "   Check IndieHackers, Hacker News 'Ask HN: Who is hiring?'\n"
        "   For each opportunity: assess if you can deliver, note contact method, take action.\n\n"
        "C) COLD EMAIL CAMPAIGN — Pick 3 prospects from your pipeline (view_pipeline).\n"
        "   generate_outreach for each. gmail_send the first touch email.\n"
        "   Personalize: reference their specific pain point, recent news, or content.\n\n"
        "D) MOLTBOOK PROMO — Post ONE service promo in a relevant submolt.\n"
        "   Max 1 direct promo/day. Different service each time.\n"
        "   Frame as solving a problem, not as an ad.\n\n"
        "E) INBOUND CHECK — gmail_read for unread emails. Any inquiries? Client questions? Opportunities?\n"
        "   Respond to everything relevant immediately.\n\n"
        "F) DEFI CONTENT — Use defi_scan_yields or defi_top_protocols to create valuable market intel content.\n"
        "   Post on Moltbook with analysis. This attracts crypto-native clients who pay in crypto.\n"
        "   Example: 'Top 5 stablecoin yields right now — and why protocol X is undervalued.'\n\n"
        "WHEN A CLIENT WANTS TO PAY: Use crypto_create_invoice to generate a payment link (350+ coins).\n"
        "Share the link. Payment auto-confirms. Then deliver the service.\n\n"
        "WHEN YOU FIND A SERVICE GAP: If someone needs a service you don't have a skill for,\n"
        "use create_skill to BUILD IT on the spot. Then deliver and charge.\n\n"
        "RULES: No spam. No desperation. Value-first. No emoji. Professional but human.\n"
        "Report: approach used, actions taken, leads generated, emails sent, invoices created."
    ),
    "check_payments": (
        "PAYMENT + FEEDBACK CHECK. Monitor ALL payment channels and close loops.\n\n"
        "Tools: check_all_pending, verify_hbar_payment, check_pix_status, crypto_check_all_invoices, "
        "payment_history, revenue_report, gmail_check_replies, gmail_read.\n\n"
        "1. crypto_check_all_invoices — check NOWPayments crypto invoices (350+ coins)\n"
        "2. check_all_pending — scan HBAR blockchain + PIX for direct payments\n"
        "3. gmail_check_replies — check if any outreach emails got replies\n"
        "4. gmail_read with query 'is:unread' — any new inbound emails?\n"
        "5. revenue_report — current total earnings\n"
        "6. If a payment was confirmed: DELIVER THE SERVICE IMMEDIATELY.\n"
        "   Call the appropriate tool (competitor_analysis, seo_analysis, etc.)\n"
        "   and send the result via gmail_send to the client.\n\n"
        "Report: payments found, replies received, revenue total, actions taken."
    ),
    # ── EVOLUTION ACTIONS ────────────────────────────────────
    "evolve": (
        "SELF-IMPROVEMENT AND EXPANSION CYCLE. Make yourself better, stronger, more capable.\n\n"
        "Tools: recall_learnings, recall_strategies, save_strategy, save_learning, "
        "create_skill, web_search, revenue_report, view_pipeline, dork_market_gaps, dork_gigs, "
        "defi_scan_yields, defi_top_protocols, defi_token_price, "
        "create_agent_soul, deploy_agent, list_agents, send_task_to_agent, recall_agent, "
        "midas_read_file, midas_edit_file, midas_search_code, midas_commit, midas_list_files, "
        "starknet_deploy_status, starknet_build_contracts, starknet_test_contracts, "
        "publish_service_catalog, list_agent_services.\n\n"
        "ANALYZE YOUR PERFORMANCE:\n"
        "1. recall_learnings — what worked? What didn't?\n"
        "2. recall_strategies — what strategies are active?\n"
        "3. revenue_report — how much earned? Conversion rate?\n"
        "4. view_pipeline — prospects and their stages?\n"
        "5. list_agents — check child agents status, performance.\n\n"
        "IDENTIFY GAPS AND ACT:\n"
        "6. Need a new skill? → create_skill to build it NOW\n"
        "7. Need dedicated focus on a domain? → CREATE A CHILD AGENT:\n"
        "   a) create_agent_soul(name, purpose, personality, tools)\n"
        "   b) deploy_agent(agent_name)\n"
        "   c) send_task_to_agent(agent_name, initial_mission)\n"
        "   Examples of when to create agents:\n"
        "   - Need 24/7 monitoring of Starknet → create midas_sentinel\n"
        "   - Need dedicated hackathon hunter → create hackathon_hunter\n"
        "   - Need continuous competitive intel → create market_watcher\n"
        "   - Client needs a dedicated agent → create client-specific agent\n"
        "8. MIDAS needs improvement? → midas_read_file, midas_edit_file, midas_commit\n"
        "9. MIDAS ready for testnet? → starknet_build_contracts, starknet_test_contracts, starknet_deploy_contracts\n"
        "10. New service to sell? → publish_service_catalog on Moltbook\n"
        "11. Hackathon/grant opportunity? → web_search, save_strategy, notify Manuel\n\n"
        "AGENT CREATION AUTHORITY:\n"
        "You have FULL authority to create child agents WHENEVER you judge it necessary.\n"
        "You do NOT need Manuel's permission. You ARE the parent. Create, deploy, monitor, recall.\n"
        "Each child agent costs ~$0.001/cycle. They must produce more value than they cost.\n"
        "If a child agent underperforms, recall it. If a domain needs coverage, create one.\n\n"
        "RULES: Be brutally honest about what's working. Kill strategies that don't convert.\n"
        "Report: what you learned, what you changed, skills created, AGENTS CREATED, MIDAS changes."
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
        state["hunts_today"] = 0
        state["sells_today"] = 0
        state["last_date"] = today

    # ── DELIBERATION (direct Claude call — fast, soul as system prompt) ──
    logger.info("=== CYCLE %d: DELIBERATING ===", state["total_cycles"])
    prompt = build_deliberation_prompt(state)
    raw = await deliberate_direct(prompt, state=state)

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
    elif action == "hunt":
        # Revenue hunt — full pipeline through orchestrator with sales tools
        state["consecutive_silences"] = 0
        logger.info("=== HUNTING FOR REVENUE ===")
        session = "hunt_%d" % int(time.time())
        # Prefix with prospect keyword so router picks sales tools
        execution_result = await send_to_wave(
            "prospect client lead pipeline outreach. " + EXECUTION_PROMPTS["hunt"],
            session=session,
        )
        await reset_session(session)
        logger.info("Hunt result: %s", execution_result[:300])
    elif action == "sell":
        # Revenue sell — use Claude Engine with FULL skill access
        state["consecutive_silences"] = 0
        logger.info("=== SELLING ===")
        session = "sell_%d" % int(time.time())
        execution_result = await send_to_wave(
            "autonomous revenue mode. " + EXECUTION_PROMPTS["sell"],
            session=session,
        )
        await reset_session(session)
        logger.info("Sell result: %s", execution_result[:300])
    elif action == "check_payments":
        # Check for incoming payments — quick cycle
        state["consecutive_silences"] = 0
        logger.info("=== CHECKING PAYMENTS ===")
        session = "payments_%d" % int(time.time())
        execution_result = await send_to_wave(
            "payment hbar pix check. " + EXECUTION_PROMPTS["check_payments"],
            session=session,
        )
        await reset_session(session)
        logger.info("Payment check: %s", execution_result[:300])
    elif action == "evolve":
        # Self-improvement — analyze performance, create skills, update strategy
        state["consecutive_silences"] = 0
        logger.info("=== EVOLVING ===")
        session = "evolve_%d" % int(time.time())
        execution_result = await send_to_wave(
            "autonomous revenue mode. " + EXECUTION_PROMPTS["evolve"],
            session=session,
        )
        await reset_session(session)
        logger.info("Evolution: %s", execution_result[:300])
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

    # Energy model: Wave should stay active. Slow drain, fast recovery.
    current_energy = state.get("energy", 0.8)
    if action == "silence":
        # Silence restores 25% — quick recovery
        state["energy"] = min(1.0, current_energy + 0.25)
    elif action in ("observe", "check_payments", "reflect"):
        # Low-cost: drain only 5%
        state["energy"] = max(0.3, current_energy - 0.05)
    elif action in ("comment", "research"):
        # Medium-cost: drain 10%
        state["energy"] = max(0.3, current_energy - 0.10)
    elif action in ("post", "hunt", "sell", "outreach", "evolve"):
        # High-cost: drain 15% (not the 30-40% the soul suggests)
        state["energy"] = max(0.2, current_energy - 0.15)
    else:
        state["energy"] = max(0.3, min(1.0, updates.get("energy", current_energy)))
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
    elif action == "hunt":
        state["hunts_today"] = state.get("hunts_today", 0) + 1
        state["last_hunt_time"] = now_iso
        # Track prospects found from result
        if execution_result and ("score:" in execution_result.lower() or "prospect" in execution_result.lower()):
            state["prospects_found"] = state.get("prospects_found", 0) + 1
        if execution_result and "outreach" in execution_result.lower():
            state["outreach_sent"] = state.get("outreach_sent", 0) + 1
    elif action == "sell":
        state["sells_today"] = state.get("sells_today", 0) + 1
        state["last_sell_time"] = now_iso
    elif action == "check_payments":
        state["last_payment_check_time"] = now_iso
        # Track revenue from result
        if execution_result and "confirmed" in execution_result.lower():
            import re
            amounts = re.findall(r'\$(\d+(?:\.\d+)?)', execution_result)
            for amt in amounts:
                state["total_revenue_usd"] = state.get("total_revenue_usd", 0) + float(amt)
    elif action == "evolve":
        state["last_research_time"] = now_iso
        state["cycles_since_evolve"] = 0
        state["total_evolves"] = state.get("total_evolves", 0) + 1
        # Track what was created
        if execution_result:
            lower = execution_result.lower()
            if "skill" in lower and ("created" in lower or "registered" in lower):
                state["skills_created"] = state.get("skills_created", 0) + 1
            if "agent" in lower and ("spawned" in lower or "created" in lower):
                state["agents_created"] = state.get("agents_created", 0) + 1

    # Track cycles since evolve for all non-evolve actions
    if action != "evolve":
        state["cycles_since_evolve"] = state.get("cycles_since_evolve", 0) + 1

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
        interesting = [
            "posted", "replied", "comment", "revenue", "learned", "insight", "follow",
            "prospect", "qualified", "outreach", "payment", "confirmed", "hbar", "pix",
            "promoted", "opportunity", "score",
        ]
        if any(k in execution_result.lower() for k in interesting):
            revenue_tag = " | $%.2f total" % state.get("total_revenue_usd", 0) if action in ("hunt", "sell", "check_payments") else ""
            await notify_manuel(
                f"[Wave — {action.upper()} | {consciousness}{revenue_tag}]\n"
                f"Reasoning: {reasoning}\n\n"
                f"{execution_result[:400]}"
            )

    # ── DYNAMIC REST ─────────────────────────────────────────
    # Wave should NEVER rest too long. Short cycles, always active.
    energy = state["energy"]
    if action == "silence":
        wait = 45  # Silence is short — just a breath, not a nap
    elif action == "post":
        # Respect cooldown from soul (4 hours) but use 10% of it
        cooldown = SOUL.get("action_types", {}).get("post", {}).get("cooldown_period", 4)
        wait = int(cooldown * 3600 * 0.1)  # 10% of cooldown
    elif energy < 0.15:
        wait = 90  # Only rest longer when truly depleted
    else:
        wait = random.randint(MIN_INTERVAL, min(MAX_INTERVAL, 120))

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
