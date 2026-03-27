"""
self_heal.py — Wave's autonomous self-healing system.

When Wave encounters a system error or execution impossibility,
this skill analyzes the error, identifies the root cause in code,
generates a fix, validates it, applies it, and commits to GitHub.

Uses Claude CLI as the reasoning engine (free on Max plan).
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict

logger = logging.getLogger("openclaw.self_heal")

OPENCLAW_DIR = Path(__file__).parent.parent
REPO_ROOT = OPENCLAW_DIR.parent  # /home/manuel/bluewave

# Files Wave is allowed to self-heal (safety boundary)
HEALABLE_PATHS = [
    "openclaw-skill/telegram_bridge.py",
    "openclaw-skill/claude_engine.py",
    "openclaw-skill/wave_autonomous.py",
    "openclaw-skill/api.py",
    "openclaw-skill/handler.py",
    "openclaw-skill/orchestrator.py",
    "openclaw-skill/skills/",
    "openclaw-skill/prompts/",
]

# Files Wave must NEVER modify (safety lock)
PROTECTED_FILES = frozenset({
    "openclaw-skill/skills/self_heal.py",  # can't modify itself
    "openclaw-skill/skills/self_evolve.py",
    ".git/",
    ".env",
    "settings.json",
})

# Heal log — persistent record of all self-heals
HEAL_LOG = OPENCLAW_DIR / "memory" / "self_heal_log.jsonl"


async def diagnose_and_heal(error_msg: str, context: str = "", action: str = "", file_hint: str = "") -> Dict:
    """Core self-healing function.

    1. Analyze the error + context to identify root cause
    2. Find the relevant source file
    3. Generate a minimal fix
    4. Apply via Claude CLI (which has Edit/Write permissions)
    5. Validate the fix (syntax check)
    6. Commit + push to GitHub

    Returns: {"success": bool, "fix_applied": str, "file": str, "commit": str}
    """
    start = time.time()

    # Build the healing prompt
    heal_prompt = f"""You are Wave's self-healing system. An error occurred during autonomous operation.

ERROR: {error_msg[:500]}
CONTEXT: {context[:300]}
ACTION THAT FAILED: {action}
FILE HINT: {file_hint}

Your job:
1. Read the relevant source file(s) to understand the bug
2. Identify the MINIMAL fix (change as little as possible)
3. Apply the fix using the Edit tool
4. After editing, verify syntax with: python3 -c "import py_compile; py_compile.compile('<file>', doraise=True)"

RULES:
- ONLY edit files under /home/manuel/bluewave/openclaw-skill/
- NEVER edit self_heal.py or self_evolve.py
- NEVER edit .env or settings.json
- Make the SMALLEST possible change that fixes the bug
- If you can't identify the bug, say "CANNOT_DIAGNOSE" and explain why
- Do NOT add features. Only fix the bug.

Start by reading the file where the error likely originates."""

    try:
        import sys
        sys.path.insert(0, str(OPENCLAW_DIR))
        from claude_engine import claude_execute_with_skills

        result = await claude_execute_with_skills(
            prompt=heal_prompt,
            system_prompt="You are a surgical bug-fixer. Minimal changes only. No commentary, just fix.",
            model="sonnet",
            timeout=90,
            max_turns=8,
        )

        elapsed = time.time() - start

        if not result.get("success"):
            logger.warning("Self-heal engine failed: %s", result.get("response", "")[:100])
            return {"success": False, "fix_applied": "", "file": "", "commit": ""}

        response = result.get("response", "")

        # Check if diagnosis failed
        if "CANNOT_DIAGNOSE" in response:
            logger.info("Self-heal: cannot diagnose — %s", response[:100])
            _log_heal(error_msg, action, "", "", False, response[:200])
            return {"success": False, "fix_applied": response[:200], "file": "", "commit": ""}

        # Auto-commit the fix
        commit_hash = await _commit_heal(error_msg, action)

        _log_heal(error_msg, action, file_hint, commit_hash, True, response[:200])

        logger.info("Self-heal completed in %.1fs: %s", elapsed, response[:80])
        return {
            "success": True,
            "fix_applied": response[:500],
            "file": file_hint,
            "commit": commit_hash,
            "elapsed": elapsed,
        }

    except Exception as e:
        logger.error("Self-heal exception: %s", e)
        return {"success": False, "fix_applied": str(e), "file": "", "commit": ""}


async def _commit_heal(error_msg: str, action: str) -> str:
    """Commit self-heal changes to git and push."""
    try:
        # Check for changes
        proc = await asyncio.create_subprocess_exec(
            "git", "status", "--porcelain",
            cwd=str(REPO_ROOT),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        changes = stdout.decode().strip()

        if not changes:
            return ""

        # Filter to healable files only
        relevant = []
        for line in changes.split("\n"):
            fpath = line.split()[-1] if line.strip() else ""
            if any(fpath.startswith(hp) or hp in fpath for hp in HEALABLE_PATHS):
                if not any(pf in fpath for pf in PROTECTED_FILES):
                    relevant.append(fpath)

        if not relevant:
            return ""

        # Stage
        for f in relevant:
            await asyncio.create_subprocess_exec(
                "git", "add", f, cwd=str(REPO_ROOT),
            )

        # Commit
        summary = error_msg[:80].replace('"', "'").replace('\n', ' ')
        msg = f"Wave self-heal: fix '{summary}' (action: {action})"

        proc = await asyncio.create_subprocess_exec(
            "git", "commit", "-m", msg,
            "--author", "Wave <wave@bluewave.app>",
            cwd=str(REPO_ROOT),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            return ""

        # Get commit hash
        proc = await asyncio.create_subprocess_exec(
            "git", "rev-parse", "--short", "HEAD",
            cwd=str(REPO_ROOT),
            stdout=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        commit_hash = stdout.decode().strip()

        # Push
        push = await asyncio.create_subprocess_exec(
            "git", "push", "origin", "master",
            cwd=str(REPO_ROOT),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await push.communicate()

        logger.info("Self-heal committed and pushed: %s (%d files)", commit_hash, len(relevant))
        return commit_hash

    except Exception as e:
        logger.warning("Self-heal commit failed: %s", e)
        return ""


def _log_heal(error: str, action: str, file: str, commit: str, success: bool, details: str):
    """Append to persistent heal log."""
    try:
        HEAL_LOG.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "error": error[:200],
            "action": action,
            "file": file,
            "commit": commit,
            "success": success,
            "details": details[:300],
        }
        with open(HEAL_LOG, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ── Skill registration (for Wave's skill executor) ──

TOOLS = [
    {
        "name": "self_heal",
        "description": "Diagnose and fix a bug in Wave's own code. Analyzes error, finds root cause, applies minimal fix, commits to GitHub.",
        "handler": diagnose_and_heal,
        "parameters": {
            "type": "object",
            "properties": {
                "error_msg": {
                    "type": "string",
                    "description": "The error message or symptom",
                },
                "context": {
                    "type": "string",
                    "description": "What was happening when the error occurred",
                },
                "action": {
                    "type": "string",
                    "description": "The autonomous action that triggered the error",
                },
                "file_hint": {
                    "type": "string",
                    "description": "File path where the error likely originates",
                },
            },
            "required": ["error_msg"],
        },
    },
]
