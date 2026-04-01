"""
inference_engine.py — Unified inference engine via CLI subprocess.

Supports both Claude Code CLI and Gemini CLI as backends.
Automatically selects based on environment variables:
  - ANTHROPIC_API_KEY or CLAUDE_CLI_PATH → Claude backend
  - GEMINI_API_KEY or GEMINI_CLI_PATH   → Gemini backend

Public interface: gemini_call() (name kept for backward compatibility).
"""

import asyncio
import logging
import os
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("openclaw.inference_engine")

# Backend selection
_USE_CLAUDE = bool(
    os.environ.get("ANTHROPIC_API_KEY")
    or os.environ.get("CLAUDE_CLI_PATH")
    or not os.environ.get("GEMINI_API_KEY")
)

# Claude config
CLAUDE_CLI = os.environ.get("CLAUDE_CLI_PATH", "claude")
CLAUDE_TIMEOUT = int(os.environ.get("CLAUDE_TIMEOUT", "300"))
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "")

# Gemini config
GEMINI_CLI = os.environ.get("GEMINI_CLI_PATH", "gemini")
GEMINI_TIMEOUT = int(os.environ.get("GEMINI_TIMEOUT", "120"))

ENGINE_NAME = "claude-cli" if _USE_CLAUDE else "gemini-cli"
logger.info("Inference engine: %s", ENGINE_NAME)


def _build_prompt(
    user_message: str,
    system_prompt: Optional[str],
    history: Optional[List[Dict]],
) -> str:
    """Build full prompt: system + history + current message."""
    parts: list[str] = []
    if system_prompt:
        if _USE_CLAUDE:
            parts.append(f"[System Instructions]\n{system_prompt}\n[/System Instructions]")
        else:
            parts.append(system_prompt)
    if history:
        for msg in history:
            role = "User" if msg.get("role") == "user" else "Assistant"
            content = msg.get("content", "").strip()
            if content:
                parts.append(f"{role}: {content}")
    if _USE_CLAUDE:
        parts.append(f"User: {user_message}")
    else:
        parts.append(user_message)
    return "\n\n".join(parts)


def _build_cmd(full_prompt: str, model: str = "") -> list[str]:
    """Build CLI command based on active backend."""
    if _USE_CLAUDE:
        cmd = [CLAUDE_CLI, "-p", full_prompt]
        selected_model = model or CLAUDE_MODEL
        if selected_model:
            cmd.extend(["--model", selected_model])
        return cmd
    return [GEMINI_CLI, "--prompt", full_prompt]


def _get_timeout() -> int:
    return CLAUDE_TIMEOUT if _USE_CLAUDE else GEMINI_TIMEOUT


def _get_model_name(model: str = "") -> str:
    if _USE_CLAUDE:
        return model or CLAUDE_MODEL or "claude-default"
    return "gemini-default"


def _parse_stderr(stderr_text: str) -> str:
    """Extract meaningful error info from stderr."""
    if _USE_CLAUDE:
        return stderr_text.strip()[:500] if stderr_text.strip() else ""
    error_lines = [
        l for l in stderr_text.splitlines()
        if "Error" in l and "Keychain" not in l and "libsecret" not in l
    ]
    return "\n".join(error_lines)


async def gemini_call(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: str = "",
    history: Optional[List[Dict]] = None,
    tools: Optional[List[Dict]] = None,
    temperature: float = 0.7,
) -> Dict[str, Any]:
    """Execute inference via CLI subprocess.

    Function name kept as gemini_call for backward compatibility.
    """
    start = time.time()
    timeout = _get_timeout()
    model_name = _get_model_name(model)

    full_prompt = _build_prompt(prompt, system_prompt, history)
    cmd = _build_cmd(full_prompt, model)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return {
                "success": False,
                "response": f"CLI timeout after {timeout}s",
                "elapsed_seconds": time.time() - start,
                "model": model_name,
                "engine": ENGINE_NAME,
            }

        text = stdout.decode(errors="replace").strip()
        elapsed = time.time() - start
        stderr_text = stderr.decode(errors="replace").strip()

        if stderr_text and _USE_CLAUDE:
            logger.debug("stderr: %s", stderr_text[:500])

        if proc.returncode == 0 and text:
            return {
                "success": True,
                "response": text,
                "elapsed_seconds": elapsed,
                "model": model_name,
                "engine": ENGINE_NAME,
            }
        else:
            return {
                "success": False,
                "response": _parse_stderr(stderr_text) or text or "CLI returned no output",
                "elapsed_seconds": elapsed,
                "model": model_name,
                "engine": ENGINE_NAME,
            }

    except Exception as e:
        logger.error("CLI error: %s", e)
        return {
            "success": False,
            "response": str(e),
            "elapsed_seconds": time.time() - start,
            "model": model_name,
            "engine": ENGINE_NAME,
        }
