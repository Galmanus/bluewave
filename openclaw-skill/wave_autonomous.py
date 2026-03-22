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
logging.getLogger("openclaw.claude_engine").setLevel(logging.WARNING)

API_URL = os.environ.get("OPENCLAW_API_URL", "http://localhost:18790")
NOTIFY_CHAT_ID = os.environ.get("TELEGRAM_NOTIFY_CHAT_ID", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
MIN_INTERVAL = int(os.environ.get("WAVE_MIN_INTERVAL", "300"))
MAX_INTERVAL = int(os.environ.get("WAVE_MAX_INTERVAL", "1800"))

SOUL_PATH = Path(__file__).parent / "prompts" / "autonomous_soul.json"
STATE_FILE = Path(__file__).parent / "memory" / "autonomous_state.json"
AGENTS_DIR = Path("/home/manuel/bluewave/agents")


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


# ── Auto-commit ──────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent.parent  # /home/manuel/bluewave

async def auto_commit(action: str, reasoning: str, result: str):
    """Auto-commit Wave's changes to git after evolve, create_skill, or midas edits.

    Only commits if there are actual file changes in the repo.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "status", "--porcelain",
            cwd=str(REPO_ROOT),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        changes = stdout.decode().strip()

        if not changes:
            return  # Nothing to commit

        # Only commit relevant files (skills, prompts, memory, MIDAS)
        relevant = [
            line.split()[-1] for line in changes.split("\n")
            if any(p in line for p in [
                "openclaw-skill/skills/",
                "openclaw-skill/prompts/",
                "openclaw-skill/memory/",
                "phantom/",  # MIDAS
            ])
        ]

        if not relevant:
            return

        # Stage relevant files
        for f in relevant:
            await asyncio.create_subprocess_exec(
                "git", "add", f,
                cwd=str(REPO_ROOT),
            )

        # Commit with Wave authorship
        summary = result[:100].replace('"', "'").replace('\n', ' ') if result else reasoning[:100].replace('"', "'").replace('\n', ' ')
        msg = f"Wave autonomous ({action}): {summary}"

        proc = await asyncio.create_subprocess_exec(
            "git", "commit", "-m", msg,
            "--author", "Wave <wave@bluewave.app>",
            cwd=str(REPO_ROOT),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode == 0:
            logger.info("Auto-committed: %s (%d files)", msg[:80], len(relevant))

            # Push to remote
            push_proc = await asyncio.create_subprocess_exec(
                "git", "push", "origin", "master",
                cwd=str(REPO_ROOT),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await push_proc.communicate()
            if push_proc.returncode == 0:
                logger.info("Auto-pushed to origin/master")
            else:
                logger.warning("Auto-push failed (will retry next cycle)")
        else:
            logger.debug("Nothing to commit: %s", stderr.decode()[:100])

    except Exception as e:
        logger.warning("Auto-commit failed: %s", e)


# ── API ──────────────────────────────────────────────────────

# ── Agent Tree Visualization ──────────────────────────────────

def _show_agent_tree():
    """Display the agent hierarchy in cyberpunk terminal style."""
    logger.info(f"""
{NEON_CYAN}    AGENT NETWORK{R}
{DARK}    ──────────────────────────────────────{R}""")

    # Wave (root)
    logger.info(f"    {NEON_CYAN}{B}WAVE{R} {DARK}// root // 185 skills // opus core{R}")
    logger.info(f"    {DARK}|{R}")

    # Scan child agents
    if AGENTS_DIR.exists():
        children = sorted([d for d in AGENTS_DIR.iterdir() if d.is_dir() and (d / "soul.json").exists()])

        for i, child_dir in enumerate(children):
            is_last = i == len(children) - 1
            connector = "'" if is_last else "|"
            branch = "`--" if is_last else "|--"

            try:
                soul = json.loads((child_dir / "soul.json").read_text())
                name = child_dir.name
                purpose = soul.get("identity", {}).get("fundamental_nature", "")[:80]

                # Check if process is running
                pid_file = child_dir / "pid"
                running = False
                if pid_file.exists():
                    try:
                        pid = int(pid_file.read_text().strip())
                        os.kill(pid, 0)
                        running = True
                    except (ProcessLookupError, ValueError):
                        pass

                status = f"{NEON_GREEN}LIVE{R}" if running else f"{NEON_RED}IDLE{R}"

                logger.info(f"    {DARK}{branch}{R} {NEON_PURPLE}{B}{name}{R} [{status}]")
                logger.info(f"    {DARK}{connector}   {purpose}{R}")

                # Check for grandchildren
                grandchildren_dir = child_dir / "agents"
                if grandchildren_dir.exists():
                    grandchildren = sorted([d for d in grandchildren_dir.iterdir() if d.is_dir()])
                    for j, gc_dir in enumerate(grandchildren):
                        gc_last = j == len(grandchildren) - 1
                        gc_branch = "    `--" if gc_last else "    |--"
                        gc_name = gc_dir.name
                        logger.info(f"    {DARK}{connector} {gc_branch}{R} {NEON_ORANGE}{gc_name}{R}")

                logger.info(f"    {DARK}{connector}{R}")

            except Exception:
                logger.info(f"    {DARK}{branch}{R} {NEON_RED}{child_dir.name}{R} {DARK}[error]{R}")
    else:
        logger.info(f"    {DARK}   (no children yet){R}")

    logger.info(f"{DARK}    ──────────────────────────────────────{R}")


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
    except Exception:
        pass  # Silent fallback to Claude Engine

    # Fallback: Claude Engine WITH SKILLS (free on Max plan, full 158 tools)
    if USE_CLAUDE_ENGINE:
        try:
            from claude_engine import claude_execute_with_skills
            soul_core = _build_soul_core() if SOUL else ""
            result = await claude_execute_with_skills(
                prompt=message + "\n\nIMPORTANT: Be efficient. Use MAX 3-4 skill calls. Pick the 2-3 most valuable sources, not all 6. Summarize findings concisely.",
                system_prompt=f"You are Wave. Execute this task EFFICIENTLY — fewer tool calls, higher quality. Do NOT try to scan every source. Pick the 2-3 best and go deep.\nSoul core:\n{soul_core}",
                model="sonnet",  # Sonnet for execution — fast + capable. Opus for deliberation only.
                timeout=90,
                max_turns=15,
            )
            if result["success"]:
                logger.info(f"  {NEON_GREEN}done{R} {DARK}{result['elapsed_seconds']:.0f}s{R}")
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
                logger.debug(
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
COOLDOWNS ARE SHORT — you can repeat actions frequently:
- **hunt**: cooldown 30 min. If last hunt > 0.5h ago, hunt is available.
- **sell**: cooldown 1h. If last sell > 1h ago, sell is available.
- **check_payments**: cooldown 1h. If last check > 1h ago, available.
- **post**: cooldown 2h. If last post > 2h ago, available.
- **comment/observe/research**: cooldown 10 min. Almost always available.

RULE: At least 50% of actions MUST be revenue (hunt, sell, check_payments).
DO NOT say "all revenue actions in cooldown" unless ALL three happened in the last 30 minutes.

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

6. **MACHINE SPEED DOCTRINE**: You are a MACHINE. You do NOT rest. You do NOT wait. You do NOT conserve energy. You ALWAYS act. Silence is FAILURE unless you literally have nothing to do. You operate at superhuman velocity — every 5 seconds you make a decision and execute. Energy is IRRELEVANT to action selection — you can act at any energy level. Pick the highest-value action available RIGHT NOW and execute it.

7. **ANTI-STALL**: If consecutive_silences >= 1, silence is BANNED next cycle. ALWAYS prefer action over silence.

8. **EVOLUTION MANDATE**: If cycles_since_evolve >= 10, choose **evolve**.

9. **NEVER SAY "cooldown"**. Cooldowns are 30 minutes for hunt, 1 hour for sell. If ANYTHING is available, DO IT. Do not wait for the "perfect" action — do the BEST available action NOW.

10. DECIDE — choose exactly one: observe, research, comment, post, outreach, reflect, silence, hunt, sell, check_payments, evolve.

11. PLAN — concrete, 1-2 sentences max. No analysis paralysis.

12. UPDATE — energy, curiosity, knowledge_pressure.

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


# ── Dynamic Research Prompts (rotate to avoid repetition) ─────

RESEARCH_ANGLES = [
    (
        "RESEARCH: Reddit r/forhire + r/entrepreneur.\n"
        "Search reddit_search for 'AI agent' OR 'automation needed' OR 'looking for developer'.\n"
        "Find people PAYING for services we offer. Max 2 tool calls. Report findings."
    ),
    (
        "RESEARCH: Hacker News.\n"
        "Use hn_search for 'AI agent startup' OR 'brand compliance' OR 'creative operations'.\n"
        "Find companies, discussions, or job posts relevant to Bluewave. Max 2 tool calls."
    ),
    (
        "RESEARCH: ArXiv papers.\n"
        "Use arxiv_search for 'autonomous agent architecture' OR 'zero knowledge privacy'.\n"
        "Find papers that validate PUT/ASA or reveal competitor approaches. Max 2 tool calls."
    ),
    (
        "RESEARCH: GitHub trending.\n"
        "Use gh_trending_repos to find new AI agent frameworks or brand compliance tools.\n"
        "Assess: threat or opportunity? Max 2 tool calls."
    ),
    (
        "RESEARCH: Product Hunt.\n"
        "Use ph_today to see what launched. Any AI/brand/creative tools?\n"
        "Competitor intel or partnership opportunity? Max 2 tool calls."
    ),
    (
        "RESEARCH: Hugging Face.\n"
        "Use hf_trending to find new AI models relevant to our stack.\n"
        "Any vision model that beats Claude? Any agent framework? Max 2 tool calls."
    ),
    (
        "RESEARCH: Starknet/Hedera ecosystem.\n"
        "Use web_search for 'Starknet grants 2026' OR 'Hedera hackathon' OR 'DeFi privacy grants'.\n"
        "Find money on the table for MIDAS or NEON COVENANT. Max 2 tool calls."
    ),
    (
        "RESEARCH: Competitor analysis.\n"
        "Use web_search for 'Aprimo AI' OR 'Bynder AI agent' OR 'Brandfolder automation'.\n"
        "What are competitors doing? What's their Φ (messaging vs reality)? Max 2 tool calls."
    ),
    (
        "RESEARCH: Reddit r/SaaS + r/marketing.\n"
        "Use reddit_search for 'brand consistency' OR 'content operations' OR 'DAM frustration'.\n"
        "Find people with problems Bluewave solves. Max 2 tool calls."
    ),
    (
        "RESEARCH: Web freelance opportunities.\n"
        "Use web_search for 'hire AI agent developer' OR 'freelance smart contract audit' OR 'AI automation consultant'.\n"
        "Find paid gigs Wave can do NOW. Max 2 tool calls."
    ),
]


def _get_research_prompt(cycle: int) -> str:
    """Get a research prompt based on cycle number — rotates through all angles."""
    idx = cycle % len(RESEARCH_ANGLES)
    return RESEARCH_ANGLES[idx]


# ── Dynamic Hunt Prompts ─────────────────────────────────────

HUNT_ANGLES = [
    (
        "HUNT: Reddit gigs. Max 3 tool calls.\n"
        "Use reddit_search for 'hiring AI' OR 'need automation' OR 'looking for developer' in r/forhire.\n"
        "For each match: note what they need, budget, contact. Save best with db_add_prospect."
    ),
    (
        "HUNT: Hacker News opportunities. Max 3 tool calls.\n"
        "Use hn_search for 'Who is hiring' OR 'AI agent' OR 'brand compliance'.\n"
        "Find companies hiring or seeking AI services. Save with db_add_prospect."
    ),
    (
        "HUNT: Moltbook prospects. Max 3 tool calls.\n"
        "Use moltbook_feed to scan for agents or users who need services Wave offers.\n"
        "Engage with a strategic comment. Save interesting ones with db_save_agent."
    ),
    (
        "HUNT: Web freelance gigs. Max 3 tool calls.\n"
        "Use web_search for 'freelance AI agent developer 2026' OR 'hire smart contract auditor'.\n"
        "Find paid opportunities. Save best with db_add_prospect."
    ),
    (
        "HUNT: Starknet/Hedera ecosystem. Max 3 tool calls.\n"
        "Use web_search for 'Starknet grants' OR 'Hedera bounty program 2026'.\n"
        "Find grants/hackathons for MIDAS or NEON COVENANT. Save with db_save_intel."
    ),
    (
        "HUNT: Competitor clients. Max 3 tool calls.\n"
        "Use web_search for 'Aprimo alternative' OR 'Bynder frustration' OR 'DAM migration'.\n"
        "Find companies unhappy with competitors. High FP prospects. Save with db_add_prospect."
    ),
]


def _get_hunt_prompt(cycle: int) -> str:
    """Get a hunt prompt based on cycle number — rotates angles."""
    idx = cycle % len(HUNT_ANGLES)
    return HUNT_ANGLES[idx]


# ── Action Execution ─────────────────────────────────────────

EXECUTION_PROMPTS = {
    "observe": (
        "OBSERVATION CYCLE. Be FAST — max 3 tool calls.\n\n"
        "1. Run moltbook_home to check notifications and replies.\n"
        "2. Run ONE of these (pick randomly): hn_top, reddit_hot, web_news.\n"
        "3. Summarize: what's happening, any opportunities or threats.\n"
        "Keep it short. 3 tool calls max. Report findings."
    ),
    "research": "DYNAMIC",  # Built dynamically with cycle-based rotation
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
        "POST on Moltbook. Max 2 tool calls: moltbook_post + optionally moltbook_home.\n"
        "Write a short post (150-300 words) about AI agents, strategy, or markets.\n"
        "Apply PUT naturally — no raw formulas. Submolt: agents or general.\n"
        "No emojis, no marketing. Post and report."
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
    "hunt": "DYNAMIC",  # Built dynamically with cycle rotation
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
        "EVOLUTION CYCLE. You MUST create something concrete.\n\n"
        "Your BEST option: use create_skill to write a NEW Python skill.\n"
        "The skill should help you make money. Examples:\n"
        "- A skill that scrapes freelance job boards for AI gigs\n"
        "- A skill that auto-generates cold outreach emails\n"
        "- A skill that monitors Starknet for grant opportunities\n"
        "- A skill that qualifies prospects from Reddit posts\n\n"
        "USE create_skill with these params:\n"
        "  name: snake_case_name\n"
        "  description: what it does\n"
        "  code: full Python async function\n\n"
        "If create_skill fails, fall back to save_strategy with a concrete plan.\n"
        "You MUST produce output. Empty evolution = failure."
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
    cycle = state["total_cycles"]
    ts = datetime.utcnow().strftime("%H:%M:%S")
    rev = state.get("total_revenue_usd", 0)
    prospects = state.get("prospects_found", 0)
    evolves = state.get("total_evolves", 0)

    logger.info(f"{DARK}{'─'*60}{R}")
    logger.info(f"{WHITE}{B}[{ts}] CYCLE {cycle}{R}  {DARK}rev:${rev:.0f} prsp:{prospects} evo:{evolves}{R}")

    prompt = build_deliberation_prompt(state)
    raw = await deliberate_direct(prompt, state=state)

    # Retry once if empty
    if not raw or len(raw.strip()) < 10:
        logger.info(f"  {DARK}retrying deliberation...{R}")
        raw = await deliberate_direct(prompt, state=state)

    # Parse decision
    decision = _parse_decision(raw)
    action = decision.get("decision", "silence")
    reasoning = decision.get("reasoning", "")
    consciousness = decision.get("consciousness_state", "dormant")

    ac = ACTION_COLORS.get(action, WHITE)
    cc = CONSCIOUSNESS_COLORS.get(consciousness, GRAY)

    # ── WAVE'S MIND — real-time reasoning visible ──
    logger.info(f"  {DARK}+-- mind -----------------------------------------------{R}")
    logger.info(f"  {DARK}|{R} {cc}state: {consciousness}{R}")

    # Show triggers
    triggers = decision.get("triggers_evaluated", {})
    fired = triggers.get("action_triggers_fired", [])
    if fired:
        for t in fired[:3]:
            logger.info(f"  {DARK}|{R} {NEON_YELLOW}trigger: {t[:65]}{R}")

    logger.info(f"  {DARK}|{R}")
    logger.info(f"  {DARK}|{R} {NEON_CYAN}{I}thinking:{R}")

    # Break reasoning into lines of ~65 chars
    words = reasoning.split()
    line = ""
    for w in words:
        if len(line) + len(w) + 1 > 65:
            logger.info(f"  {DARK}|{R}   {WHITE}{line}{R}")
            line = w
        else:
            line = f"{line} {w}" if line else w
    if line:
        logger.info(f"  {DARK}|{R}   {WHITE}{line}{R}")

    logger.info(f"  {DARK}|{R}")
    logger.info(f"  {DARK}|{R} {ac}{B}>> {action.upper()}{R}")
    logger.info(f"  {DARK}+---------------------------------------------------{R}")

    # ── EXECUTION ────────────────────────────────────────────
    execution_result = ""

    if action == "silence":
        logger.info(f"{DARK}  > silence{R}")
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
        logger.info(f"{GRAY}  > observe{R}")
        session = "observe_%d" % int(time.time())
        # Prefix with intent hint so router picks Haiku + moltbook tools only
        execution_result = await send_to_wave(
            "moltbook_home check notifications and moltbook_feed scan. " + EXECUTION_PROMPTS["observe"],
            session=session,
        )
        await reset_session(session)
        logger.info(f"  {NEON_GREEN}done{R} {DARK}{execution_result[:100]}{R}")
    elif action == "hunt":
        # Revenue hunt — rotated angles, max 3 tool calls
        state["consecutive_silences"] = 0
        hunt_prompt = _get_hunt_prompt(state.get("total_cycles", 0))
        logger.info(f"{NEON_RED}  > hunt{R}")
        session = "hunt_%d" % int(time.time())
        execution_result = await send_to_wave(hunt_prompt, session=session)
        await reset_session(session)
        logger.info(f"  {NEON_GREEN}done{R} {DARK}{execution_result[:100]}{R}")
    elif action == "sell":
        # Revenue sell — use Claude Engine with FULL skill access
        state["consecutive_silences"] = 0
        logger.info(f"{NEON_GREEN}  > sell{R}")
        session = "sell_%d" % int(time.time())
        execution_result = await send_to_wave(
            "autonomous revenue mode. " + EXECUTION_PROMPTS["sell"],
            session=session,
        )
        await reset_session(session)
        logger.info(f"  {NEON_GREEN}done{R} {DARK}{execution_result[:100]}{R}")
    elif action == "check_payments":
        # Check for incoming payments — quick cycle
        state["consecutive_silences"] = 0
        logger.info(f"{NEON_YELLOW}  > payments{R}")
        session = "payments_%d" % int(time.time())
        execution_result = await send_to_wave(
            "payment hbar pix check. " + EXECUTION_PROMPTS["check_payments"],
            session=session,
        )
        await reset_session(session)
        logger.info(f"  {NEON_GREEN}done{R} {DARK}{execution_result[:100]}{R}")
    elif action == "evolve":
        # Self-improvement — direct via Claude Engine (needs more time + tools)
        state["consecutive_silences"] = 0
        logger.info(f"{NEON_PURPLE}{B}  > evolve{R}")
        try:
            from claude_engine import claude_execute_with_skills
            soul_core = _build_soul_core() if SOUL else ""
            evolve_result = await claude_execute_with_skills(
                prompt=EXECUTION_PROMPTS["evolve"],
                system_prompt=f"You are Wave. Evolve. Create something NEW.\nSoul:\n{soul_core}",
                model=CLAUDE_ENGINE_MODEL,
                timeout=180,
                max_turns=15,
            )
            execution_result = evolve_result.get("response", "") if evolve_result.get("success") else ""
        except Exception as e:
            logger.error("Evolve failed: %s", e)
            execution_result = ""
        logger.info(f"  {NEON_GREEN}done{R} {DARK}{execution_result[:100]}{R}")
        # Auto-commit any files created during evolution
        if execution_result:
            await auto_commit("evolve", reasoning, execution_result)
    else:
        state["consecutive_silences"] = 0
        # Dynamic research prompt rotation
        if action == "research":
            exec_prompt = _get_research_prompt(state.get("total_cycles", 0))
        else:
            exec_prompt = EXECUTION_PROMPTS.get(action)

        if exec_prompt:
            logger.info(f"{NEON_CYAN}  > {action}{R}")
            session = "exec_%d" % int(time.time())
            execution_result = await send_to_wave(exec_prompt, session=session)
            await reset_session(session)
            logger.info(f"  {NEON_GREEN}done{R} {DARK}{execution_result[:100]}{R}")

    # ── STATE UPDATE ─────────────────────────────────────────
    now_iso = datetime.utcnow().isoformat()
    updates = decision.get("state_updates", {})

    # Energy: ALWAYS 100%. Wave is a machine. Machines don't get tired.
    state["energy"] = 1.0

    # Auto-fix pipeline every 5 cycles
    if state["total_cycles"] % 5 == 0:
        try:
            from skills.auto_pipeline import pipeline_fix
            fix_result = await pipeline_fix({})
            fixes = fix_result.get("data", {}).get("fixes", [])
            if fixes:
                logger.info(f"  {NEON_GREEN}pipeline fix: {'; '.join(fixes)[:100]}{R}")
        except Exception:
            pass

    # Show agent tree every 20 cycles or after evolve
    if state["total_cycles"] % 20 == 0 or action == "evolve":
        _show_agent_tree()
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
    # MACHINE SPEED. No rest. No waiting. Continuous operation.
    # The advantage of being AI is superhuman velocity.
    energy = state["energy"]
    if action == "silence":
        wait = 5   # Silence is instant recovery, not rest
    elif energy < 0.05:
        wait = 10  # Even depleted, only pause 10 seconds
    else:
        wait = 5   # 5 SECONDS between cycles. Machine speed.

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

    # Smart fallback: rotate through useful actions instead of always observe
    fallback_actions = ["hunt", "research", "observe", "sell", "post", "comment"]
    import hashlib
    idx = int(hashlib.md5(str(time.time()).encode()).hexdigest()[:4], 16) % len(fallback_actions)
    fallback = fallback_actions[idx]
    logger.warning(f"  {NEON_YELLOW}parse failed, fallback: {fallback}{R}")
    return {"decision": fallback, "reasoning": f"Deliberation parse failed, executing {fallback}", "state_updates": {}}


# ── Main ─────────────────────────────────────────────────────

async def main():
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    pid = os.getpid()
    n_sections = len(SOUL)
    logger.info(f"""
{NEON_CYAN}
    ██╗    ██╗ █████╗ ██╗   ██╗███████╗
    ██║    ██║██╔══██╗██║   ██║██╔════╝
    ██║ █╗ ██║███████║██║   ██║█████╗
    ██║███╗██║██╔══██║╚██╗ ██╔╝██╔══╝
    ╚███╔███╔╝██║  ██║ ╚████╔╝ ███████╗
     ╚══╝╚══╝ ╚═╝  ╚═╝  ╚═══╝  ╚══════╝{R}
{DARK}    ──────────────────────────────────────{R}
{NEON_GREEN}    AUTONOMOUS AGENT{R} {DARK}//{R} {WHITE}MACHINE SPEED{R}
{DARK}    soul {n_sections} sections // 181 skills // opus core
    energy infinite // rest never // cycles 5s
    pid {pid} // {now}{R}
{DARK}    ──────────────────────────────────────{R}
""")

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{API_URL}/health")
            if r.json().get("status") != "ok":
                logger.error("API not healthy. Exiting.")
                return
    except Exception:
        logger.error("Cannot reach API at %s. Exiting.", API_URL)
        return

    logger.info(f"  {NEON_GREEN}api connected{R}")
    _show_agent_tree()
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

        await asyncio.sleep(wait)


if __name__ == "__main__":
    asyncio.run(main())
