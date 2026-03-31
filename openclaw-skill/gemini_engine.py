"""
gemini_engine.py — Inference engine via Gemini CLI subprocess.

Uses `gemini --prompt` (headless) with OAuth credentials (Ultra plan).
Interface pública idêntica — wave_autonomous, orchestrator e telegram_bridge não mudam.
"""

import asyncio
import logging
import time
import os
from typing import Optional, Dict, Any, List

logger = logging.getLogger("openclaw.gemini_engine")

GEMINI_CLI = os.environ.get("GEMINI_CLI_PATH", "gemini")
GEMINI_TIMEOUT = int(os.environ.get("GEMINI_TIMEOUT", "120"))


def _build_prompt(
    user_message: str,
    system_prompt: Optional[str],
    history: Optional[List[Dict]],
) -> str:
    """Monta prompt completo: system + history + mensagem atual."""
    parts: list[str] = []
    if system_prompt:
        parts.append(system_prompt)
    if history:
        for msg in history:
            role = "User" if msg.get("role") == "user" else "Assistant"
            content = msg.get("content", "").strip()
            if content:
                parts.append(f"{role}: {content}")
    parts.append(user_message)
    return "\n\n".join(parts)


async def gemini_call(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: str = "flash",
    history: Optional[List[Dict]] = None,
    tools: Optional[List[Dict]] = None,
    temperature: float = 0.7,
) -> Dict[str, Any]:
    """Execute inference via Gemini CLI. Aguarda resposta completa (retries automáticos pelo CLI)."""
    start = time.time()

    full_prompt = _build_prompt(prompt, system_prompt, history)

    cmd = [GEMINI_CLI, "--prompt", full_prompt]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=GEMINI_TIMEOUT,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return {
                "success": False,
                "response": f"gemini CLI timeout after {GEMINI_TIMEOUT}s",
                "elapsed_seconds": time.time() - start,
                "model": "gemini-default",
                "engine": "gemini-cli",
            }

        text = stdout.decode(errors="replace").strip()
        elapsed = time.time() - start

        # Logar retries visíveis no stderr (não são erros fatais)
        stderr_text = stderr.decode(errors="replace")
        attempts = [l for l in stderr_text.splitlines() if "Attempt" in l]
        if attempts:
            logger.info("gemini retries: %d attempt(s), total %.1fs", len(attempts), elapsed)

        if proc.returncode == 0 and text:
            return {
                "success": True,
                "response": text,
                "elapsed_seconds": elapsed,
                "model": "gemini-default",
                "engine": "gemini-cli",
            }
        else:
            error_lines = [l for l in stderr_text.splitlines()
                           if "Error" in l and "Keychain" not in l and "libsecret" not in l]
            return {
                "success": False,
                "response": "\n".join(error_lines) or "gemini CLI returned no output",
                "elapsed_seconds": elapsed,
                "model": "gemini-default",
                "engine": "gemini-cli",
            }

    except Exception as e:
        logger.error("gemini CLI error: %s", e)
        return {
            "success": False,
            "response": str(e),
            "elapsed_seconds": time.time() - start,
            "model": "gemini-default",
            "engine": "gemini-cli",
        }
