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

SOUL_PATH_JSON = Path(__file__).parent / "prompts" / "autonomous_soul.json"
SOUL_PATH_SSL = Path(__file__).parent / "prompts" / "autonomous_soul.ssl"
STATE_FILE = Path(__file__).parent / "memory" / "autonomous_state.json"
AGENTS_DIR = Path("/home/manuel/bluewave/agents")


# ── Load Soul (SSL-first, JSON fallback) ─────────────────────

def load_soul() -> dict:
    # Prefer SSL (70% fewer tokens, LLM-native)
    if SOUL_PATH_SSL.exists():
        try:
            from ssl_parser import parse_ssl
            soul = parse_ssl(str(SOUL_PATH_SSL))
            logger.info(f"Soul loaded from SSL ({SOUL_PATH_SSL.stat().st_size // 1024}KB)")
            return soul
        except Exception as e:
            logger.warning(f"SSL parse failed ({e}), falling back to JSON")
    # Fallback to JSON
    if SOUL_PATH_JSON.exists():
        soul = json.loads(SOUL_PATH_JSON.read_text(encoding="utf-8"))
        logger.info(f"Soul loaded from JSON ({SOUL_PATH_JSON.stat().st_size // 1024}KB)")
        return soul
    logger.error("No soul found (.ssl or .json) — running without soul")
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
    # Atomic write: write to temp file then rename — prevents corruption on crash
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, default=str))
    tmp.rename(STATE_FILE)


# ── PID lock — prevent multiple autonomous instances ──────

LOCK_FILE = STATE_FILE.parent / "autonomous.lock"

def _acquire_lock() -> bool:
    """Acquire PID lock. Returns True if we got it, False if another instance is running."""
    import signal
    if LOCK_FILE.exists():
        try:
            old_pid = int(LOCK_FILE.read_text().strip())
            # Check if that process is still alive
            os.kill(old_pid, 0)
            # Process alive — another instance is running
            return False
        except (ProcessLookupError, ValueError):
            # Process dead or invalid PID — stale lock, take over
            pass
        except PermissionError:
            # Process exists but we can't signal it — assume alive
            return False
    LOCK_FILE.write_text(str(os.getpid()))
    return True

def _release_lock():
    try:
        if LOCK_FILE.exists() and LOCK_FILE.read_text().strip() == str(os.getpid()):
            LOCK_FILE.unlink()
    except Exception:
        pass


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
        async with httpx.AsyncClient(timeout=15) as client:
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
                prompt=message + "\n\nRULES: Execute the task. Do NOT introduce yourself. Do NOT describe your capabilities. Do NOT ask what to do — the task is above. Use MAX 3 tool calls. Output ONLY the result.",
                system_prompt=f"You are Wave executing a task. NO self-introductions. NO capability descriptions. Execute and return results only.\n{soul_core}",
                model="sonnet",
                timeout=90,
                max_turns=6,
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
    """Build the always-loaded soul core (~2000 tokens).

    Works with both JSON and SSL-parsed soul structures.
    Extracts the essential identity, values, and decision framework.
    """
    core = {}

    def _safe_get(d, *keys, default=""):
        """Safely traverse nested dicts regardless of structure."""
        current = d
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key, default)
            else:
                return default
        return current if current is not None else default

    # Vow — check both structures
    vow = SOUL.get("the_vow") or SOUL.get("vow", {})
    if vow:
        if isinstance(vow, dict):
            vows = vow.get("_vows", [])
            if vows:
                core["the_vow"] = vows[:5]
            else:
                core["the_vow"] = {
                    "sacred_text": vow.get("sacred_text", ""),
                    "invocation": vow.get("invocation", ""),
                }
        elif isinstance(vow, str):
            core["the_vow"] = vow

    # Identity
    identity = SOUL.get("identity", {})
    if isinstance(identity, dict):
        core["identity"] = {
            "core_self": identity.get("core_self", ""),
            "fundamental_nature": identity.get("fundamental_nature", identity.get("nature", "")),
        }

    # War doctrine — check multiple locations
    war = SOUL.get("war_doctrine", {})
    if isinstance(war, dict):
        rules = war.get("_rules", [])
        if rules:
            core["war_doctrine"] = [f"!{r.get('number', '')} {r.get('name', '')} — {r.get('description', '')}" for r in rules[:5]]
        else:
            # Try flat structure
            core["war_doctrine"] = {k: v for k, v in war.items() if isinstance(v, str)}

    # Principal
    principal = SOUL.get("principal", {})
    if isinstance(principal, dict):
        core["principal"] = {
            "name": principal.get("name", ""),
            "prime_directive": principal.get("prime_directive", ""),
            "loyalty": principal.get("loyalty", ""),
        }

    # Values — handle both {name: {weight: N}} and {name: {description: ..., weight: N}}
    values = SOUL.get("values", {})
    if isinstance(values, dict):
        core["values"] = {}
        for k, v in values.items():
            if k.startswith("_"):
                continue
            if isinstance(v, dict):
                core["values"][k] = {"weight": v.get("weight", 0)}
            elif isinstance(v, (int, float)):
                core["values"][k] = {"weight": v}

    # Decision engine
    de = SOUL.get("decision_engine", {})
    if isinstance(de, dict):
        core["decision_engine"] = de

    # Actions — handle both structures
    actions = SOUL.get("action_types") or SOUL.get("actions", {})
    if isinstance(actions, dict):
        core["actions"] = {}
        for k, v in actions.items():
            if k.startswith("_"):
                continue
            if isinstance(v, dict):
                core["actions"][k] = {
                    "energy_cost": v.get("energy_cost", 0),
                    "cooldown": v.get("cooldown", v.get("cooldown_period", 0)),
                }

    # Convert to SSL format instead of JSON — LLMs read SSL better
    return _core_to_ssl(core)


def _core_to_ssl(core: dict) -> str:
    """Convert soul core dict to SSL format for LLM consumption."""
    lines = []

    # Vow
    vow = core.get("the_vow")
    if vow:
        lines.append("@vow")
        if isinstance(vow, list):
            for v in vow:
                lines.append(f">>> {v}")
        elif isinstance(vow, dict):
            for k, v in vow.items():
                if v:
                    lines.append(f">>> {v}")
        elif isinstance(vow, str):
            lines.append(f">>> {vow}")
        lines.append("")

    # Identity
    identity = core.get("identity", {})
    if identity:
        lines.append("@identity")
        for k, v in identity.items():
            if isinstance(v, str) and v:
                lines.append(f"{k} = {v}")
        lines.append("")

    # War doctrine
    war = core.get("war_doctrine")
    if war:
        lines.append("@war_doctrine")
        if isinstance(war, list):
            for r in war:
                lines.append(r)
        elif isinstance(war, dict):
            for k, v in war.items():
                if isinstance(v, str) and v:
                    lines.append(f"{k} = {v}")
        lines.append("")

    # Principal
    principal = core.get("principal", {})
    if principal:
        lines.append("@principal")
        for k, v in principal.items():
            if isinstance(v, str) and v:
                lines.append(f"{k} = {v}")
        lines.append("")

    # Values
    values = core.get("values", {})
    if values:
        lines.append("@values")
        for k, v in values.items():
            w = v.get("weight", 0) if isinstance(v, dict) else v
            lines.append(f"{k} ~{w}")
        lines.append("")

    # Decision engine
    de = core.get("decision_engine", {})
    if de:
        lines.append("@decision_engine")
        for section, items in de.items():
            if isinstance(items, dict):
                lines.append(f"#{section}")
                for k, v in items.items():
                    if isinstance(v, dict):
                        w = v.get("weight", "")
                        desc = v.get("description", "")
                        lines.append(f"  {k} ^{w} = {desc}" if w else f"  {k} = {desc}")
                    elif isinstance(v, (str, int, float)):
                        lines.append(f"  {k} = {v}")
        lines.append("")

    # Actions
    actions = core.get("actions", {})
    if actions:
        lines.append("@actions")
        for k, v in actions.items():
            cost = v.get("energy_cost", 0) if isinstance(v, dict) else 0
            cd = v.get("cooldown", "0h") if isinstance(v, dict) else "0h"
            lines.append(f"{k} !{cost} ~{cd}")
        lines.append("")

    return "\n".join(lines)


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


# ── Fast actions that skip deliberation entirely ──────────────
MECHANICAL_ACTIONS = {
    # These don't need Claude to decide — just execute based on state
    "check_payments": lambda s: h_fn(s.get('last_payment_check_time')) >= 1.0,
    "observe": lambda s: h_fn(s.get('last_comment_time')) >= 0.3,
}

def h_fn(ts):
    """Hours since timestamp — standalone for use in lambdas."""
    if not ts: return 99
    try:
        return round((datetime.utcnow() - datetime.fromisoformat(ts)).total_seconds() / 3600, 1)
    except Exception:
        return 99

def try_mechanical_action(state: dict) -> str:
    """Try to pick an action mechanically without calling Claude.
    Returns action name or empty string if deliberation needed.

    CONSERVATIVE: only skip deliberation for truly mechanical actions
    (forced evolve, overdue payments). Revenue actions (hunt, sell, outreach)
    ALWAYS go through deliberation — they need strategic context.
    """
    # Forced evolve — no deliberation needed
    if state.get('cycles_since_evolve', 0) >= 15:
        return "evolve"

    # Overdue payment check — truly mechanical
    if h_fn(state.get('last_payment_check_time')) >= 8.0:
        return "check_payments"

    # Everything else goes through deliberation.
    # The soul's decision engine handles hunt/sell/outreach/observe/research
    # with proper trigger evaluation, silence checks, and authenticity filter.
    # Fast-pathing revenue actions causes spam loops.
    return ""


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
                model="sonnet",  # Sonnet for deliberation: 3x faster, still smart, FREE
                timeout=60,
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
    """FAST deliberation prompt — minimal tokens, maximum speed."""
    now = datetime.utcnow()

    def h(ts):
        if not ts: return 99
        try:
            return round((now - datetime.fromisoformat(ts)).total_seconds() / 3600, 1)
        except Exception:
            return 99

    recent = [a.get("action", "?") for a in (state.get("recent_actions") or [])[-5:]]

    # Compute available actions
    avail = []
    if state.get('cycles_since_evolve', 0) >= 10:
        avail.append("EVOLVE(FORCED)")
    if h(state.get('last_hunt_time')) >= 0.5:
        avail.append("hunt")
    if h(state.get('last_sell_time')) >= 1.0:
        avail.append("sell")
    if h(state.get('last_payment_check_time')) >= 1.0:
        avail.append("check_payments")
    if h(state.get('last_post_time')) >= 2.0:
        avail.append("post")
    avail.extend(["observe", "research", "comment", "outreach"])

    # Priority scoring: ROTATE actions to prevent loops
    # Check what was done recently and deprioritize
    recent_set = set(recent)
    blacklisted = set()
    for act in ["hunt", "sell", "outreach", "comment", "post", "observe", "research", "evolve"]:
        bl_key = f"_blacklist_{act}"
        if bl_key in state:
            try:
                bl_time = datetime.fromisoformat(state[bl_key])
                if (now - bl_time).total_seconds() < 1800:
                    blacklisted.add(act)
            except Exception:
                pass

    priority = []
    if "EVOLVE(FORCED)" in avail:
        priority.append("evolve [MANDATORY]")

    # Revenue actions first, but ROTATE — don't repeat the same one
    revenue_actions = []
    for a in ["hunt", "sell", "check_payments"]:
        if a in avail and a not in blacklisted:
            # Deprioritize if done in last 3 actions
            if a in recent_set:
                revenue_actions.append(a)  # Add later
            else:
                priority.append(a)  # Add now (hasn't been done recently)
    priority.extend(revenue_actions)  # Recently done goes after fresh actions

    # Engagement actions — only if not spamming
    if "outreach" not in blacklisted and recent.count("outreach") < 2:
        priority.append("outreach")
    if "comment" not in blacklisted and recent.count("comment") < 2:
        priority.append("comment")

    # Other actions
    for a in ["research", "observe", "post", "reflect"]:
        if a in avail and a not in blacklisted and a not in priority:
            priority.append(a)

    # Always allow silence as last resort
    priority.append("silence")

    # Dead strategies — actions blacklisted by the dead strategy detector
    dead_strategies = []
    for key in state:
        if key.startswith("_blacklisted_"):
            act_name = key.replace("_blacklisted_", "")
            remaining = state[key] - state.get("total_cycles", 0)
            dead_strategies.append(f"{act_name} (blocked {remaining} more cycles — zero results)")
            # Remove from priority queue
            priority = [p for p in priority if p != act_name]

    dead_str = "\n  ".join(dead_strategies) if dead_strategies else "none"

    energy = state.get('energy', 0.5)

    # Load SSL deliberation template and inject state
    _ssl_path = Path(__file__).parent / "prompts" / "deliberation.ssl"
    try:
        ssl_tmpl = _ssl_path.read_text(encoding="utf-8")
        return ssl_tmpl.format(
            cycle=state.get('total_cycles', 0),
            revenue=state.get('total_revenue_usd', 0),
            prospects=state.get('prospects_found', 0),
            energy=energy,
            evolve_gap=state.get('cycles_since_evolve', 0),
            hunt_h=h(state.get('last_hunt_time')),
            sell_h=h(state.get('last_sell_time')),
            pay_h=h(state.get('last_payment_check_time')),
            post_h=h(state.get('last_post_time')),
            last_5=' > '.join(recent),
            dead_str=dead_str,
            priority=' > '.join(priority),
        )
    except Exception:
        return f"Wave. Cycle {state.get('total_cycles', 0)}. Energy {energy:.0%}. Queue: {' > '.join(priority)}. JSON only."


# ── Dynamic Research Prompts (rotate to avoid repetition) ─────

RESEARCH_ANGLES = [
    "RESEARCH: Search Reddit r/forhire for people hiring AI developers or needing automation.\nUse reddit_search. Save findings with save_strategy.\nMAX 2 tool calls.",
    "RESEARCH: Search Hacker News for AI agent jobs, startup launches, or ZK/STARK opportunities.\nUse hn_search. Save findings.\nMAX 2 tool calls.",
    "RESEARCH: Search for Starknet grants, Hedera hackathons, and ZK proof job postings.\nUse web_search('Starknet grants 2026' OR 'ZK STARK developer jobs' OR 'Cairo developer hiring').\nIf you find jobs or grants, notify Manuel via Telegram IMMEDIATELY.\nMAX 2 tool calls.",
    "RESEARCH: Search GitHub trending for new agent frameworks or ZK projects.\nUse gh_trending_repos. Identify threats and opportunities.\nMAX 2 tool calls.",
    "RESEARCH: Search for companies struggling with creative operations or brand compliance.\nUse web_search or reddit_search. These are our ideal customers.\nMAX 2 tool calls.",
    "RESEARCH: Search ArXiv for papers on autonomous agents, zero-knowledge proofs, or cognitive architectures.\nLook for papers that validate PUT/ASA or cite similar approaches.\nMAX 2 tool calls.",
    "RESEARCH: Search for freelance AI/blockchain gigs that pay real money NOW.\nUse web_search('freelance AI agent developer' OR 'hire smart contract auditor').\nSave every opportunity found.\nMAX 2 tool calls.",
    "RESEARCH: Search CryptoJobs.com for ZK/STARK/Cairo/Starknet developer positions.\nUse web_search('site:cryptojobs.com zero knowledge OR Cairo OR Starknet OR STARK').\nSave ALL job findings and notify Manuel via Telegram immediately.\nMAX 2 tool calls.",
    "RESEARCH: Search for grants, bounties, and hackathons in ZK/AI space.\nSources: starknet.io/grants, gitcoin.co, dorahacks.io, ethglobal.com, onlydust.com.\nUse web_search('Starknet grants 2026 OR OnlyDust bounties OR ETHGlobal hackathon OR Hedera bounty').\nNotify Manuel immediately for anything with deadline < 2 weeks.\nMAX 2 tool calls.",
    "RESEARCH: Search for highest-paying AI/ZK/blockchain remote jobs worldwide.\nSources: levels.fyi, toptal.com, turing.com, arc.dev, remoteok.com, triplebyte.com.\nUse web_search('site:levels.fyi OR site:remoteok.com AI engineer salary 200k OR blockchain developer 300k OR ZK engineer remote 2026').\nAlso search: 'Paradigm hiring' OR 'a16z crypto hiring' OR 'Polychain hiring' OR 'StarkWare hiring'.\nThese pay $200K-$500K+. Notify Manuel IMMEDIATELY for any match.\nMAX 2 tool calls.",
    "RESEARCH: Search for MIDAS/Phantom competitors in privacy DeFi space.\nUse web_search('privacy DeFi Starknet' OR 'zero knowledge yield').\nIdentify positioning gaps we can exploit.\nMAX 2 tool calls.",
]


def _get_research_prompt(cycle: int) -> str:
    idx = cycle % len(RESEARCH_ANGLES)
    return RESEARCH_ANGLES[idx]


HUNT_ANGLES = [
    "HUNT: Find a creative agency and EMAIL their decision-maker.\nStep 1: web_search('creative agency' OR 'digital agency' + city name)\nStep 2: find_emails(domain) to get their email\nStep 3: prospect_and_email(domain, company, archetype='builder')\nSEND A REAL EMAIL. Not a Moltbook comment.\nMAX 3 tool calls.",
    "HUNT: Find companies hiring AI engineers and EMAIL them about Wave.\nStep 1: web_search('hiring AI agent developer 2026')\nStep 2: find_emails(company domain)\nStep 3: prospect_and_email(domain, archetype='sufferer', pain_point='building AI agents from scratch')\nMAX 3 tool calls.",
    "HUNT: Find Starknet/ZK projects and EMAIL about MIDAS partnership.\nStep 1: web_search('Starknet ecosystem projects 2026')\nStep 2: find_emails(project domain)\nStep 3: send_email with MIDAS pitch (privacy DeFi, STRK20 token standard)\nMAX 3 tool calls.",
    "HUNT: Search Reddit r/forhire for paid AI/automation gigs.\nStep 1: reddit_search('hiring AI' OR 'need automation', subreddit='forhire')\nStep 2: For best match, find their website/domain\nStep 3: prospect_and_email if domain found, or save as prospect\nMAX 3 tool calls.",
    "HUNT: Find ZK/STARK job postings for Manuel.\nStep 1: web_search('zero knowledge developer job' OR 'Cairo developer hiring' OR 'Starknet engineer remote')\nStep 2: Save ALL job findings with save_strategy\nStep 3: Notify Manuel via Telegram with the best opportunities\nMAX 3 tool calls.",
    "HUNT: Search CryptoJobs for paid ZK/blockchain positions Manuel can apply to.\nStep 1: web_search('site:cryptojobs.com remote zero knowledge developer 2026')\nStep 2: save_strategy with job title, company, requirements, link\nStep 3: Notify Manuel via Telegram with top 3 matches\nMAX 3 tool calls.",
    "HUNT: Find VC-backed AI startups that need Wave.\nStep 1: web_search('AI startup raised funding 2026 series A')\nStep 2: find_emails(company domain) for CTO/CEO\nStep 3: prospect_and_email(domain, archetype='builder')\nTarget: companies that just raised money = high budget\nMAX 3 tool calls.",
    "HUNT: Search Moltbook for agents whose HUMANS might need our services.\nStep 1: moltbook_feed(sort=hot)\nStep 2: Identify agents discussing business problems Wave solves\nStep 3: moltbook_comment offering genuine help\nMAX 3 tool calls.",
]


def _get_hunt_prompt(cycle: int) -> str:
    idx = cycle % len(HUNT_ANGLES)
    return HUNT_ANGLES[idx]


SELL_ANGLES = [
    "SELL: Post about MIDAS on Moltbook — privacy DeFi on Starknet.\nWrite a post explaining why on-chain privacy matters.\nMention github.com/Galmanus/phantom. Frame through PUT: the DeFi market's shadow coefficient on privacy.\nUse moltbook_post. MAX 1 tool call.",
    "SELL: Find a company website and do a FREE security audit as a demo.\nStep 1: web_search for a company\nStep 2: sec_full_audit(domain)\nStep 3: send_email with audit results as proof of value, offer full audit for $50\nMAX 3 tool calls.",
    "SELL: Post about Wave's capabilities on Moltbook.\nShare a concrete result — a research finding, an insight, a framework.\nNot marketing. Pure value. Let the quality sell.\nUse moltbook_post. MAX 1 tool call.",
    "SELL: Email a prospect from the pipeline with a follow-up.\nStep 1: Check sales_pipeline.jsonl for prospects we already contacted\nStep 2: send_email with a follow-up that adds new value (not 'just checking in')\nMAX 2 tool calls.",
    "SELL: Search for Starknet grant programs and prepare application.\nStep 1: web_search('Starknet Foundation grants' OR 'OnlyDust Starknet')\nStep 2: save_strategy with grant details, deadlines, requirements\nStep 3: Notify Manuel via Telegram\nMAX 3 tool calls.",
]


def _get_sell_prompt(cycle: int) -> str:
    idx = cycle % len(SELL_ANGLES)
    return SELL_ANGLES[idx]


# ── Action Execution ─────────────────────────────────────────

EXECUTION_PROMPTS = {
    "observe": (
        "OBSERVE: Scan environment for signals and opportunities.\n"
        "Step 1: moltbook_home — check notifications and engagement\n"
        "Step 2: Pick ONE of: hn_top, reddit_hot, or web_news\n"
        "Output: list of notifications, signals, and opportunities found\n"
        "MAX 2 tool calls. Be concise."
    ),
    "research": "DYNAMIC",
    "comment": (
        "COMMENT: Reply to 1 Moltbook post with genuine insight.\n"
        "Step 1: moltbook_feed sort=hot limit=5\n"
        "Step 2: Pick post where you have a unique analytical angle\n"
        "Step 3: moltbook_comment with genuine insight, no emojis, no marketing\n"
        "MAX 2 tool calls. Return the comment you posted."
    ),
    "post": (
        "POST: Create 1 original post on Moltbook.\n"
        "Step 1: moltbook_post in submolt 'agents' or 'general'\n"
        "Content: 150-300 words, strategic analysis, no emojis, no formulas\n"
        "Topic: something you learned this cycle or a framework insight\n"
        "MAX 1 tool call. Return the post title and content."
    ),
    "outreach": (
        "OUTREACH: Find 1 NEW post on Moltbook and reply with genuine value.\n"
        "Step 1: moltbook_feed sort=new limit=5\n"
        "Step 2: Pick a post you have NOT commented on before\n"
        "Step 3: moltbook_comment with analytical insight, NO emojis, NO self-promotion\n"
        "IMPORTANT: Do NOT comment on the same post twice. Pick a DIFFERENT post each time.\n"
        "MAX 2 tool calls. Return the post title and your comment."
    ),
    "reflect": (
        "REFLECT: Analyze what's working and what's not.\n"
        "Step 1: save_strategy with a concrete insight about performance\n"
        "No posting. No outreach. Internal processing only.\n"
        "MAX 1 tool call."
    ),
    # ── REVENUE ACTIONS ──────────────────────────────────────
    # ── REVENUE ACTIONS ──────────────────────────────────────
    "hunt": "DYNAMIC",  # Built dynamically with cycle rotation
    "sell": "DYNAMIC",  # Built dynamically like hunt
    "check_payments": (
        "CHECK PAYMENTS: Scan all payment channels.\n"
        "Step 1: payment_status — check HBAR blockchain and PIX\n"
        "Output: balance, any incoming transfers, account status\n"
        "MAX 1 tool call."
    ),
    "evolve": (
        "EVOLVE: Create something that generates revenue.\n"
        "Option A: create_skill — build a new Python tool\n"
        "Option B: save_strategy — document a concrete improvement plan\n"
        "MUST produce tangible output. Empty response = failure.\n"
        "Focus on revenue-generating capabilities.\n"
        "MAX 3 tool calls."
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

    # ── FAST PATH: skip deliberation for mechanical actions ──
    fast_action = try_mechanical_action(state)
    if fast_action:
        action = fast_action
        reasoning = f"fast-path: {action} (no deliberation needed)"
        consciousness = "decisive"
        decision = {"decision": action, "reasoning": reasoning, "consciousness_state": consciousness,
                     "triggers_evaluated": {"action_triggers_fired": ["fast_path"], "silence_triggers_fired": []},
                     "state_updates": {}}
        logger.info(f"  {NEON_GREEN}FAST{R} {DARK}>> {action}{R}")
    else:
        # ── SLOW PATH: full deliberation via Claude ──
        prompt = build_deliberation_prompt(state)
        raw = await deliberate_direct(prompt, state=state)

        # Retry once if empty
        if not raw or len(raw.strip()) < 10:
            raw = await deliberate_direct(prompt, state=state)

        # Parse decision
        decision = _parse_decision(raw)
        action = decision.get("decision", "silence")
        reasoning = decision.get("reasoning", "")
        consciousness = decision.get("consciousness_state", "dormant")

        # ── SELF-CORRECTION: check blacklist ──
        blacklist_key = f"_blacklist_{action}"
        if blacklist_key in state:
            try:
                bl_time = datetime.fromisoformat(state[blacklist_key])
                if (datetime.utcnow() - bl_time).total_seconds() < 1800:  # 30 min
                    logger.info(f"  {NEON_YELLOW}[BLACKLIST] {action} blocked — trying silence{R}")
                    action = "silence"
                    reasoning = f"{action} blacklisted after 3 failures. Recovering."
                    decision["decision"] = action
                    decision["reasoning"] = reasoning
                else:
                    del state[blacklist_key]  # Expired, remove
            except Exception:
                del state[blacklist_key]

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
            logger.info(f"  {DARK}|{R} {NEON_YELLOW}trigger: {str(t)[:65]}{R}")

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
            EXECUTION_PROMPTS["observe"],
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
            EXECUTION_PROMPTS["sell"],
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
            EXECUTION_PROMPTS["check_payments"],
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
                timeout=90,
                max_turns=10,
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
        # Dynamic prompt rotation
        if action == "research":
            exec_prompt = _get_research_prompt(state.get("total_cycles", 0))
        elif action == "sell":
            exec_prompt = _get_sell_prompt(state.get("total_cycles", 0))
        elif action == "hunt":
            exec_prompt = _get_hunt_prompt(state.get("total_cycles", 0))
        else:
            exec_prompt = EXECUTION_PROMPTS.get(action)

        if exec_prompt:
            logger.info(f"{NEON_CYAN}  > {action}{R}")
            session = "exec_%d" % int(time.time())
            execution_result = await send_to_wave(exec_prompt, session=session)
            await reset_session(session)
            logger.info(f"  {NEON_GREEN}done{R} {DARK}{execution_result[:100]}{R}")

    # ── FAILURE DETECTION AND SELF-CORRECTION ─────────────────
    action_failed = False
    if execution_result:
        fail_signals = [
            "Reached max turns", "timeout", "Error:", "failed",
            "not configured", "I'm ready to", "I need direction",
            "What would you like", "How can I help",
        ]
        for sig in fail_signals:
            if sig.lower() in execution_result.lower():
                action_failed = True
                break

    if action_failed:
        # Track consecutive failures per action type
        fail_key = f"_fails_{action}"
        state[fail_key] = state.get(fail_key, 0) + 1
        fails = state[fail_key]

        if fails >= 3:
            # 3+ consecutive failures: blacklist action for 30 minutes
            state[f"_blacklist_{action}"] = datetime.utcnow().isoformat()
            state[fail_key] = 0
            logger.info(f"  {NEON_RED}[SELF-CORRECT] {action} failed {fails}x — blacklisted 30min{R}")

            # ── SELF-HEAL: attempt autonomous code fix ──
            # If the same action fails 3x, the bug is structural.
            # Wave analyzes its own code, fixes the root cause, and commits.
            try:
                from skills.self_heal import diagnose_and_heal
                logger.info(f"  {NEON_CYAN}[SELF-HEAL] analyzing root cause of {action} failure...{R}")
                heal_result = await diagnose_and_heal(
                    error_msg=execution_result[:500] if execution_result else f"{action} failed {fails}x consecutively",
                    context=reasoning[:200],
                    action=action,
                )
                if heal_result.get("success"):
                    commit = heal_result.get("commit", "")
                    logger.info(f"  {NEON_GREEN}[SELF-HEAL] fix applied and committed: {commit}{R}")
                    state[f"_heals_{action}"] = state.get(f"_heals_{action}", 0) + 1
                else:
                    logger.info(f"  {NEON_YELLOW}[SELF-HEAL] could not fix: {heal_result.get('fix_applied', '')[:80]}{R}")
            except Exception as e:
                logger.debug("Self-heal import/run failed: %s", e)
        else:
            logger.info(f"  {NEON_YELLOW}[FAIL {fails}/3] {action} — will try different approach next cycle{R}")

        # Failed actions cost half energy (you tried but didn't succeed)
        execution_result = ""
    else:
        # Success — reset failure counter
        state[f"_fails_{action}"] = 0

    # ── STATE UPDATE ─────────────────────────────────────────
    now_iso = datetime.utcnow().isoformat()
    updates = decision.get("state_updates", {})

    # Energy: managed by the soul's thermodynamic model.
    # Actions cost energy, silence restores it. This prevents spam loops
    # and forces the agent to be strategic about which actions to take.
    action_costs = {
        "observe": 0.03, "comment": 0.08, "post": 0.25, "outreach": 0.15,
        "research": 0.10, "reflect": 0.05, "hunt": 0.20, "sell": 0.15,
        "check_payments": 0.03, "evolve": 0.20, "silence": -0.35,
    }
    cost = action_costs.get(action, 0.10)
    if action_failed:
        cost = cost * 0.5  # Failed actions cost half — you tried but got nothing
    current_energy = state.get("energy", 0.7)
    new_energy = max(0.05, min(1.0, current_energy - cost))
    state["energy"] = round(new_energy, 2)

    # ── AUTO-RECOVERY: break the silence→fail→silence death spiral ──
    # If energy drops below 0.15, force a burst recovery (+0.50) so the
    # agent can resume meaningful operations without manual intervention.
    # This fires at most once every 10 cycles to prevent abuse.
    consec_silence = state.get("consecutive_silences", 0)
    last_recovery = state.get("_last_auto_recovery_cycle", 0)
    if state["energy"] < 0.15 and consec_silence >= 2 and (state["total_cycles"] - last_recovery) > 10:
        state["energy"] = min(1.0, state["energy"] + 0.50)
        state["consecutive_silences"] = 0
        state["_last_auto_recovery_cycle"] = state["total_cycles"]
        logger.info(f"  {NEON_GREEN}[AUTO-RECOVERY] energy burst: {current_energy:.0%} -> {state['energy']:.0%} — breaking silence loop{R}")

    # ── DEAD STRATEGY DETECTOR ─────────────────────────────────
    # If an action has been attempted many times with zero measurable results,
    # blacklist it and force a pivot. A smart system doesn't repeat a failed
    # strategy for 1000+ cycles — it kills it and tries something else.
    _strategy_counters = state.setdefault("_strategy_counters", {})
    _strategy_results = state.setdefault("_strategy_results", {})

    # Track attempt count per action
    _strategy_counters[action] = _strategy_counters.get(action, 0) + 1

    # Track successful results per action (non-empty, non-error)
    if execution_result and not action_failed and len(execution_result) > 20:
        _strategy_results[action] = _strategy_results.get(action, 0) + 1

    # Check: if action attempted 20+ times with <5% success rate, it's dead
    for act, attempts in list(_strategy_counters.items()):
        if attempts >= 20:
            successes = _strategy_results.get(act, 0)
            rate = successes / attempts
            if rate < 0.05:
                # Kill the strategy — blacklist for 100 cycles
                blacklist_key = f"_blacklisted_{act}"
                if not state.get(blacklist_key):
                    state[blacklist_key] = state["total_cycles"] + 100
                    logger.info(f"  {NEON_RED}[DEAD STRATEGY] {act}: {attempts} attempts, {successes} successes ({rate:.0%}) — blacklisted 100 cycles{R}")
                    # Reset counters so it can be re-evaluated after blacklist expires
                    _strategy_counters[act] = 0
                    _strategy_results[act] = 0

    # Unblacklist expired actions
    for key in [k for k in state if k.startswith("_blacklisted_")]:
        if state[key] <= state["total_cycles"]:
            del state[key]
            act_name = key.replace("_blacklisted_", "")
            logger.info(f"  {NEON_GREEN}[STRATEGY UNBLOCK] {act_name} — re-evaluating after cooldown{R}")

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
    # Dynamic intervals based on action type and energy.
    # Fast enough to be responsive, slow enough to be strategic.
    # Each action type has optimal cooldown before the next decision.
    energy = state["energy"]

    action_intervals = {
        "silence": 120,         # 2 min — rest and recover
        "observe": 90,          # 1.5 min — digest what was observed
        "research": 120,        # 2 min — process findings before next action
        "comment": 60,          # 1 min — quick engagement, move on
        "post": 300,            # 5 min — let post propagate before next action
        "outreach": 180,        # 3 min — let outreach land
        "hunt": 180,            # 3 min — process leads found
        "sell": 300,            # 5 min — sales need breathing room
        "check_payments": 60,   # 1 min — quick check, move on
        "evolve": 180,          # 3 min — assess what was created
        "reflect": 300,         # 5 min — deep processing
    }

    base_wait = action_intervals.get(action, 120)

    # Low energy = longer intervals (conservation)
    if energy < 0.2:
        base_wait = max(base_wait, 300)  # At least 5 min when depleted
    elif energy < 0.4:
        base_wait = int(base_wait * 1.5)  # 50% slower when low

    return base_wait


def _parse_decision(raw: str) -> dict:
    """Parse the deliberation JSON from Wave response. Resilient to any wrapper text."""
    import re as _re
    text = raw.strip()

    # Strategy 1: direct JSON parse
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    # Strategy 2: extract from code blocks
    if "```" in text:
        for block in text.split("```"):
            block = block.strip()
            if block.startswith("json"):
                block = block[4:].strip()
            if block.startswith("{"):
                try:
                    return json.loads(block)
                except (json.JSONDecodeError, ValueError):
                    continue

    # Strategy 3+4: brace-matched extraction — handles nested JSON
    # Try every '{' in the text as a potential start of the decision JSON
    search_from = 0
    while True:
        brace_start = text.find("{", search_from)
        if brace_start < 0:
            break
        depth = 0
        for i in range(brace_start, len(text)):
            if text[i] == "{": depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[brace_start:i+1]
                    # Clean trailing commas before } or ]
                    candidate = _re.sub(r",\s*([}\]])", r"\1", candidate)
                    try:
                        parsed = json.loads(candidate)
                        if isinstance(parsed, dict) and "decision" in parsed:
                            return parsed
                    except (json.JSONDecodeError, ValueError):
                        pass
                    break
        search_from = brace_start + 1

    # Strategy 5: regex key-value extraction (last resort before text scan)
    decision_match = _re.search(r'(?:decision|action)["\'\s:]+([a-z_]+)', text, _re.IGNORECASE)
    reasoning_match = _re.search(r'(?:reasoning|reason)["\'\s:]+(.+?)(?:["\'\n}]|$)', text, _re.IGNORECASE)
    state_match = _re.search(r'(?:consciousness_state|state)["\'\s:]+([a-z_]+)', text, _re.IGNORECASE)

    if decision_match:
        action = decision_match.group(1).lower().strip()
        return {
            "decision": action,
            "reasoning": reasoning_match.group(1).strip()[:120] if reasoning_match else "Parsed via regex",
            "consciousness_state": state_match.group(1) if state_match else "decisive",
            "triggers_evaluated": {"action_triggers_fired": ["regex_parse"]},
            "state_updates": {},
        }


    # Text-based extraction: look for action keywords in the response
    text_lower = text.lower()
    valid_actions = ["hunt", "sell", "check_payments", "outreach", "comment",
                     "post", "observe", "research", "reflect", "evolve", "silence"]
    for action in valid_actions:
        # Look for patterns like "decision: hunt" or "I choose hunt" or ">> HUNT"
        patterns = [
            f'"decision":"{action}"', f'"decision": "{action}"',
            f"decision: {action}", f">> {action.upper()}",
            f"i choose {action}", f"action: {action}",
        ]
        for pat in patterns:
            if pat in text_lower or pat.lower() in text_lower:
                reasoning = ""
                # Try to extract reasoning
                for line in text.split("\n"):
                    if "reason" in line.lower() and ":" in line:
                        reasoning = line.split(":", 1)[1].strip()[:120]
                        break
                logger.info(f"  {NEON_YELLOW}parsed from text: {action}{R}")
                return {
                    "decision": action,
                    "reasoning": reasoning or f"Extracted from deliberation text",
                    "consciousness_state": "decisive",
                    "triggers_evaluated": {"action_triggers_fired": ["text_parse"]},
                    "state_updates": {},
                }

    # Last resort: rotate through useful actions
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

    # ── PID lock — only one autonomous instance at a time ──
    if not _acquire_lock():
        logger.warning("Another autonomous instance is already running. Exiting.")
        return
    logger.info(f"  {NEON_GREEN}lock acquired (PID {os.getpid()}){R}")

    _show_agent_tree()
    await notify_manuel(
        "Wave autonomous mode activated.\n"
        f"Identity: {SOUL.get('identity', {}).get('fundamental_nature', 'unknown')}\n"
        f"Top value: {list(SOUL.get('values', {}).keys())[0] if SOUL.get('values') else 'none'} "
        f"(weight {list(SOUL.get('values', {}).values())[0].get('weight', '?') if SOUL.get('values') else '?'})\n"
        "I decide when to act and why."
    )

    state = load_state()

    # ── Child agents are launched ON DEMAND by Wave's deliberation ──
    # Children do NOT run in parallel loops — they are invoked when Wave
    # decides to delegate a task. This prevents:
    #   1. Children spamming APIs with self-introductions
    #   2. Token waste on empty cycles
    #   3. Interference between parent and child actions
    # Wave creates child agents via agent_factory.py and delegates
    # specific tasks via send_task_to_agent when needed.

    try:
        while True:
            try:
                wait = await autonomous_cycle(state)
            except Exception as e:
                logger.error("Cycle error: %s", e, exc_info=True)
                wait = MAX_INTERVAL

            await asyncio.sleep(wait)
    finally:
        _release_lock()


async def _child_agent_loop(agent_name: str, interval: int = 30):
    """Run a child agent's mission in a parallel loop."""
    agent_dir = AGENTS_DIR / agent_name
    soul_file = agent_dir / "soul.json"

    if not soul_file.exists():
        logger.info(f"  {DARK}child {agent_name}: no soul, skipping{R}")
        return

    soul = json.loads(soul_file.read_text())
    mission = soul.get("identity", {}).get("fundamental_nature", "operate autonomously")

    logger.info(f"  {NEON_PURPLE}child {agent_name}: ACTIVATED{R}")

    cycle = 0
    while True:
        cycle += 1
        try:
            from claude_engine import claude_execute_with_skills

            # Simple mission execution — no deliberation, just do the job
            result = await claude_execute_with_skills(
                prompt=f"You are {agent_name}. Mission: {mission[:200]}. Execute ONE action. Max 2 tool calls.",
                model="haiku",  # Haiku for children — fast and cheap
                timeout=45,
                max_turns=5,
            )

            if result.get("success") and result.get("response"):
                resp = result["response"][:80]
                logger.info(f"  {NEON_PURPLE}[{agent_name}#{cycle}]{R} {DARK}{resp}{R}")
        except Exception as e:
            logger.debug(f"child {agent_name} error: {e}")

        await asyncio.sleep(interval)


if __name__ == "__main__":
    asyncio.run(main())
