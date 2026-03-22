"""
claude_engine.py — Claude Code CLI as inference engine

Uses `claude -p` for UNLIMITED inference on Max plan.
Zero API cost. Opus-quality thinking on every call.

Replaces: anthropic.Anthropic().messages.create()
With:     subprocess.run(["claude", "-p", prompt])
"""

import asyncio
import json
import logging
import time
import os
from typing import Optional, Dict, Any, List

logger = logging.getLogger("openclaw.claude_engine")

# Path to claude CLI
CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")

# Default model — on Max plan, Opus is free
DEFAULT_MODEL = os.environ.get("CLAUDE_ENGINE_MODEL", "opus")

# Timeout for claude -p calls (seconds)
DEFAULT_TIMEOUT = int(os.environ.get("CLAUDE_ENGINE_TIMEOUT", "300"))


async def claude_call(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
    session_id: Optional[str] = None,
    continue_session: bool = False,
    output_format: str = "text",
    max_turns: int = 1,
    tools: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Call Claude via CLI (`claude -p`). Zero API cost on Max plan.

    Args:
        prompt: The user message / instruction
        system_prompt: Optional system prompt (passed via --system-prompt)
        model: Model to use (opus, sonnet, haiku). Default: opus
        timeout: Max seconds to wait
        session_id: Session ID for conversation continuity
        continue_session: If True, continues the last conversation
        output_format: "text" or "json"
        max_turns: Max agentic turns (default 1 for single response)
        tools: List of allowed tools (if any)

    Returns:
        {
            "success": True/False,
            "response": "the text response",
            "elapsed_seconds": float,
            "model": "opus",
            "engine": "claude-cli"
        }
    """
    start = time.time()

    cmd = [CLAUDE_BIN, "-p", prompt]

    # Model selection
    m = model or DEFAULT_MODEL
    if m:
        cmd.extend(["--model", m])

    # System prompt
    if system_prompt:
        cmd.extend(["--system-prompt", system_prompt])

    # Continue previous session
    if continue_session:
        cmd.append("--continue")
    elif session_id:
        cmd.extend(["--resume", session_id])

    # Output format
    if output_format == "json":
        cmd.extend(["--output-format", "json"])

    # Max turns for agentic behavior
    if max_turns > 1:
        cmd.extend(["--max-turns", str(max_turns)])

    # Allowed tools
    if tools:
        for tool in tools:
            cmd.extend(["--allowedTools", tool])

    # No interactive prompts
    env = os.environ.copy()
    env["CLAUDE_CODE_ENTRYPOINT"] = "api"

    try:
        logger.info(f"claude-engine: model={m}, prompt={prompt[:80]}...")

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            elapsed = time.time() - start
            logger.error(f"claude-engine: timeout after {elapsed:.1f}s")
            return {
                "success": False,
                "response": "Timeout — Claude CLI took too long",
                "elapsed_seconds": elapsed,
                "model": m,
                "engine": "claude-cli",
            }

        elapsed = time.time() - start
        response_text = stdout.decode("utf-8", errors="replace").strip()
        stderr_text = stderr.decode("utf-8", errors="replace").strip()

        if proc.returncode != 0:
            logger.error(f"claude-engine: exit={proc.returncode}, stderr={stderr_text[:200]}")
            return {
                "success": False,
                "response": stderr_text or f"Claude CLI exited with code {proc.returncode}",
                "elapsed_seconds": elapsed,
                "model": m,
                "engine": "claude-cli",
            }

        # Parse JSON output if requested
        if output_format == "json":
            try:
                parsed = json.loads(response_text)
                response_text = parsed.get("result", response_text)
            except json.JSONDecodeError:
                pass  # Return raw text

        logger.info(f"claude-engine: OK in {elapsed:.1f}s, {len(response_text)} chars")

        return {
            "success": True,
            "response": response_text,
            "elapsed_seconds": elapsed,
            "model": m,
            "engine": "claude-cli",
        }

    except FileNotFoundError:
        logger.error("claude-engine: claude CLI not found. Install: npm install -g @anthropic-ai/claude-code")
        return {
            "success": False,
            "response": "Claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code",
            "elapsed_seconds": 0,
            "model": m,
            "engine": "claude-cli",
        }
    except Exception as e:
        elapsed = time.time() - start
        logger.error(f"claude-engine: {e}")
        return {
            "success": False,
            "response": str(e),
            "elapsed_seconds": elapsed,
            "model": m,
            "engine": "claude-cli",
        }


async def claude_deliberate(
    soul_json_path: str,
    state: Dict[str, Any],
    prompt: str = "Deliberate on your next autonomous action.",
    model: str = "opus",
    timeout: int = 300,
) -> Dict[str, Any]:
    """
    Soul-driven deliberation via Claude CLI.
    Loads the soul as system prompt, injects current state, gets decision.

    This is the core of Wave's autonomous mind — now running on Opus
    for FREE on Max plan.
    """
    # Load soul
    try:
        with open(soul_json_path, "r") as f:
            soul = f.read()
    except FileNotFoundError:
        return {
            "success": False,
            "response": f"Soul file not found: {soul_json_path}",
            "elapsed_seconds": 0,
            "model": model,
            "engine": "claude-cli",
        }

    system = f"""You are Wave, an autonomous AI agent. Your soul specification follows.
Every decision must reference your soul — your values, consciousness states,
decision engine, energy model, and the Core Psychometric System (PUT).

=== SOUL SPECIFICATION ===
{soul}
=== END SOUL ===

Respond with a JSON object:
{{
  "should_act": true/false,
  "action_type": "observe|research|comment|post|outreach|reflect|silence|hunt|sell|check_payments|evolve",
  "consciousness_state": "dormant|curious|analytical|strategic|creative|decisive",
  "reasoning": "why this decision, referencing soul values and PUT variables",
  "plan": "concrete description of what to do",
  "energy_delta": float,
  "triggers_evaluated": ["list of triggers checked"],
  "put_analysis": "any PUT variables at play in this decision"
}}"""

    # Build state prompt
    state_prompt = f"""Current state:
{json.dumps(state, indent=2, default=str)}

{prompt}

Respond ONLY with the JSON decision object."""

    return await claude_call(
        prompt=state_prompt,
        system_prompt=system,
        model=model,
        timeout=timeout,
        output_format="text",
    )


async def claude_chat(
    message: str,
    system_prompt: Optional[str] = None,
    model: str = "sonnet",
    session_id: Optional[str] = None,
    timeout: int = 120,
) -> Dict[str, Any]:
    """
    Simple chat via Claude CLI. For Wave's conversational interactions.
    """
    return await claude_call(
        prompt=message,
        system_prompt=system_prompt,
        model=model,
        session_id=session_id,
        timeout=timeout,
    )


# ── Fallback: if claude CLI unavailable, use API ────────────────────

_api_client = None

def _get_api_client():
    """Lazy-init Anthropic API client as fallback."""
    global _api_client
    if _api_client is None:
        try:
            import anthropic
            _api_client = anthropic.Anthropic()
        except Exception:
            _api_client = None
    return _api_client


async def claude_call_with_fallback(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
    **kwargs,
) -> Dict[str, Any]:
    """
    Try Claude CLI first. If unavailable, fall back to API.
    Best of both worlds: free when possible, works when not.
    """
    # Try CLI first
    result = await claude_call(
        prompt=prompt,
        system_prompt=system_prompt,
        model=model,
        timeout=timeout,
        **kwargs,
    )

    if result["success"]:
        return result

    # CLI failed — try API fallback
    if "not found" in result["response"].lower() or "timeout" in result["response"].lower():
        logger.info("claude-engine: CLI unavailable, falling back to API")

        client = _get_api_client()
        if not client:
            return result  # No fallback available

        try:
            # Map model names
            model_map = {
                "opus": "claude-opus-4-20250514",
                "sonnet": "claude-sonnet-4-20250514",
                "haiku": "claude-haiku-4-5-20251001",
            }
            api_model = model_map.get(model or DEFAULT_MODEL, model or "claude-sonnet-4-20250514")

            start = time.time()
            msgs = [{"role": "user", "content": prompt}]
            api_kwargs = {"model": api_model, "max_tokens": 8192, "messages": msgs}
            if system_prompt:
                api_kwargs["system"] = system_prompt

            response = client.messages.create(**api_kwargs)
            elapsed = time.time() - start

            text = response.content[0].text if response.content else ""

            return {
                "success": True,
                "response": text,
                "elapsed_seconds": elapsed,
                "model": api_model,
                "engine": "anthropic-api",
            }
        except Exception as e:
            logger.error(f"claude-engine: API fallback failed: {e}")
            return {
                "success": False,
                "response": str(e),
                "elapsed_seconds": 0,
                "model": model,
                "engine": "anthropic-api",
            }

    return result
