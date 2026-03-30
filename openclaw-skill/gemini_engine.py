"""
gemini_engine.py — Inference engine via claude CLI subprocess.

Uses `claude -p` (headless) with Opus. ~3s TTFB, sem overhead de auth.
Interface pública idêntica — orchestrator e telegram_bridge não mudam.
"""

import asyncio
import logging
import time
import os
from typing import Optional, Dict, Any, List

logger = logging.getLogger("openclaw.engine")

CLAUDE_CLI = os.environ.get("CLAUDE_CLI_PATH", "claude")
DEFAULT_MODEL = os.environ.get("CLAUDE_MODEL", "opus")


def _build_input(
    user_message: str,
    history: Optional[List[Dict]],
) -> str:
    """Build stdin: history + new user message."""
    parts: list[str] = []
    if history:
        for msg in history:
            role = "User" if msg.get("role") == "user" else "Assistant"
            content = msg.get("content", "").strip()
            if content:
                parts.append(f"{role}: {content}")
    parts.append(f"User: {user_message}")
    return "\n\n".join(parts)


async def gemini_call(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    history: Optional[List[Dict]] = None,
    tools: Optional[List[Dict]] = None,
    temperature: float = 0.7,
) -> Dict[str, Any]:
    """Execute inference via claude CLI. Same interface as before."""
    start = time.time()

    stdin_content = _build_input(prompt, history)

    cmd = [
        CLAUDE_CLI, "-p",
        "--output-format", "text",
        "--model", model,
        "--no-session-persistence",
    ]
    if system_prompt:
        cmd += ["--system-prompt", system_prompt]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate(input=stdin_content.encode())
        text = stdout.decode(errors="replace").strip()

        if proc.returncode == 0 and text:
            return {
                "success": True,
                "response": text,
                "elapsed_seconds": time.time() - start,
                "model": model,
                "engine": "claude-cli",
            }
        else:
            return {
                "success": False,
                "response": text or "claude CLI returned no output",
                "elapsed_seconds": time.time() - start,
                "model": model,
                "engine": "claude-cli",
            }
    except Exception as e:
        logger.error("claude CLI error: %s", e)
        return {
            "success": False,
            "response": str(e),
            "elapsed_seconds": time.time() - start,
            "model": model,
            "engine": "claude-cli",
        }
