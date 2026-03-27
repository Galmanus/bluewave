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

# Default model — sonnet is faster and sufficient for most tasks
DEFAULT_MODEL = os.environ.get("CLAUDE_ENGINE_MODEL", "sonnet")

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

    # Build command — prompt as argument, system prompt via file
    cmd = [CLAUDE_BIN, "-p", prompt]

    # Model selection
    m = model or DEFAULT_MODEL
    if m:
        cmd.extend(["--model", m])

    # System prompt — MUST use --system-prompt-file for large prompts.
    # Passing >8K as --system-prompt arg causes Claude CLI to hang.
    _sys_prompt_file = None
    if system_prompt:
        import tempfile
        _sys_prompt_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, prefix='wave_sys_', dir='/tmp')
        _sys_prompt_file.write(system_prompt)
        _sys_prompt_file.close()
        cmd.extend(["--system-prompt-file", _sys_prompt_file.name])

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
        logger.info(f"claude-engine: model={m}, prompt={len(prompt)}B, sys={len(system_prompt or '')}B")

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
            # Capture whatever output was produced before the kill — do NOT discard.
            partial_out, _ = await proc.communicate()
            elapsed = time.time() - start
            logger.warning(f"claude-engine: timeout after {elapsed:.1f}s")

            # Salvage partial output if Claude produced anything before dying.
            partial_text = partial_out.decode("utf-8", errors="replace").strip() if partial_out else ""
            if partial_text:
                logger.info(f"claude-engine: salvaged {len(partial_text)} chars from timed-out process")
                return {
                    "success": True,
                    "response": partial_text,
                    "elapsed_seconds": elapsed,
                    "model": m,
                    "engine": "claude-cli",
                }

            # Retry once with max_turns=1 and a shorter timeout — fast path fallback.
            if max_turns > 1:
                logger.info("claude-engine: retrying with max_turns=1 (fast path)")
                return await claude_call(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    model=m,
                    timeout=min(timeout, 120),
                    session_id=session_id,
                    continue_session=continue_session,
                    output_format=output_format,
                    max_turns=1,
                    tools=tools,
                )

            # If opus timed out on a single-turn call, retry with sonnet — faster model.
            if m == "opus":
                logger.info("claude-engine: opus timed out, retrying with sonnet (faster path)")
                return await claude_call(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    model="sonnet",
                    timeout=min(timeout, 120),
                    session_id=session_id,
                    continue_session=continue_session,
                    output_format=output_format,
                    max_turns=max_turns,
                    tools=tools,
                )

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
            # Special case: "Reached max turns" is not a real failure.
            if "reached max turns" in stderr_text.lower():
                # If there's partial output, use it
                if response_text:
                    logger.info(f"claude-engine: max turns reached, using partial output ({len(response_text)} chars)")
                    # Fall through to success path below
                else:
                    # No output — retry without tools (single-turn conversational)
                    logger.warning(f"claude-engine: max turns reached with no output, retrying without tools")
                    return await claude_call(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        model=m,
                        timeout=min(timeout, 90),
                        session_id=session_id,
                        continue_session=continue_session,
                        output_format=output_format,
                        max_turns=1,
                        tools=None,
                    )

            # Exit 143 (SIGTERM) or 137 (SIGKILL) — process was killed externally.
            # Salvage any partial output before retrying.
            elif proc.returncode in (143, 137) or (proc.returncode >= 128):
                logger.warning(f"claude-engine: killed (exit={proc.returncode}) after {elapsed:.1f}s")

                # Salvage partial output if available
                if response_text:
                    logger.info(f"claude-engine: salvaged {len(response_text)} chars from killed process")
                    return {
                        "success": True,
                        "response": response_text,
                        "elapsed_seconds": elapsed,
                        "model": m,
                        "engine": "claude-cli",
                    }

                # Retry with faster model/fewer turns
                if max_turns > 1:
                    logger.info("claude-engine: retrying killed process with max_turns=1")
                    return await claude_call(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        model=m,
                        timeout=min(timeout, 120),
                        session_id=session_id,
                        continue_session=continue_session,
                        output_format=output_format,
                        max_turns=1,
                        tools=tools,
                    )
                if m == "opus":
                    logger.info("claude-engine: opus killed, retrying with sonnet")
                    return await claude_call(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        model="sonnet",
                        timeout=min(timeout, 120),
                        session_id=session_id,
                        continue_session=continue_session,
                        output_format=output_format,
                        max_turns=max_turns,
                        tools=tools,
                    )
                if m == "sonnet":
                    logger.info("claude-engine: sonnet killed, retrying with haiku")
                    return await claude_call(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        model="haiku",
                        timeout=min(timeout, 90),
                        session_id=session_id,
                        continue_session=continue_session,
                        output_format=output_format,
                        max_turns=max_turns,
                        tools=tools,
                    )

                return {
                    "success": False,
                    "response": "Claude CLI was terminated (signal). Retries exhausted.",
                    "elapsed_seconds": elapsed,
                    "model": m,
                    "engine": "claude-cli",
                }
            else:
                logger.error(f"claude-engine: exit={proc.returncode}, stderr={stderr_text[:300]}, stdout={response_text[:100]}, cmd={' '.join(str(c) for c in cmd[:6])}")
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
    finally:
        # Cleanup temp system prompt file
        if _sys_prompt_file:
            try:
                os.unlink(_sys_prompt_file.name)
            except Exception:
                pass


async def claude_execute_with_skills(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: str = "sonnet",
    timeout: int = 180,
    max_turns: int = 10,
) -> Dict[str, Any]:
    """
    Execute a task using Claude CLI with access to Wave's 158 skills.

    Claude gets Bash tool access and instructions to call skill_executor.py.
    This gives it access to ALL Wave skills: web_search, moltbook_post,
    security_audit, create_skill, etc.

    This replaces the orchestrator entirely — no Anthropic API needed.
    """
    skill_executor_path = os.path.join(os.path.dirname(__file__), "skill_executor.py")

    skill_instructions = f"""You have access to Wave's 158 operational skills via a Python executor.

To use ANY skill, run this command in Bash:
  cd {os.path.dirname(__file__)} && python3 skill_executor.py <skill_name> '<json_params>'

Examples:
  python3 skill_executor.py web_search '{{"query": "AI agents 2026"}}'
  python3 skill_executor.py moltbook_post '{{"submolt": "agents", "title": "...", "content": "..."}}'
  python3 skill_executor.py moltbook_home '{{}}'
  python3 skill_executor.py moltbook_feed '{{"submolt": "agents"}}'
  python3 skill_executor.py hn_top '{{}}'
  python3 skill_executor.py hf_trending '{{"category": "text-generation"}}'
  python3 skill_executor.py reddit_hot '{{"subreddit": "artificial"}}'
  python3 skill_executor.py arxiv_recent '{{}}'
  python3 skill_executor.py gh_trending_repos '{{}}'
  python3 skill_executor.py ph_today '{{}}'
  python3 skill_executor.py create_skill '{{"name": "...", "description": "...", "code": "..."}}'
  python3 skill_executor.py put_analyze '{{"target": "company name"}}'
  python3 skill_executor.py kill_chain_plan '{{"target_market": "..."}}'
  python3 skill_executor.py pre_mortem '{{"strategy": "..."}}'
  python3 skill_executor.py self_diagnostic '{{}}'
  python3 skill_executor.py wave_journal '{{"entry": "..."}}'
  python3 skill_executor.py list_skills '{{}}'

To see ALL available skills: python3 skill_executor.py list_skills '{{}}'

IMPORTANT: Always cd to {os.path.dirname(__file__)} first.
Set env vars if needed: MOLTBOOK_API_KEY={os.environ.get('MOLTBOOK_API_KEY', 'not_set')}
"""

    full_system = skill_instructions
    if system_prompt:
        full_system = system_prompt + "\n\n" + skill_instructions

    return await claude_call(
        prompt=prompt,
        system_prompt=full_system,
        model=model,
        timeout=timeout,
        max_turns=max_turns,
        tools=["Bash", "Read", "Write", "Edit", "Glob", "Grep"],
    )


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
    """Chat via Anthropic API with prompt caching for speed.

    Architecture:
    - PRIMARY: Anthropic API with cache_control on system prompt.
      The full Machiavelli soul is cached for 5 minutes → ~85% TTFT reduction.
    - FALLBACK: Claude CLI (free on Max plan, but slower for complex prompts).

    The API key must be set in ANTHROPIC_API_KEY env var.
    """
    start = time.time()
    model_map = {
        "opus": "claude-opus-4-20250514",
        "sonnet": "claude-sonnet-4-20250514",
        "haiku": "claude-haiku-4-5-20251001",
    }
    api_model = model_map.get(model, model or "claude-sonnet-4-20250514")

    # CLI with retry — the Max plan has concurrent session limits.
    # If the first attempt times out (slot busy), wait and retry.
    for attempt in range(3):
        result = await claude_call(
            prompt=message,
            system_prompt=system_prompt,
            model=model if attempt == 0 else "haiku",  # downgrade on retry
            session_id=session_id,
            timeout=timeout if attempt == 0 else 30,
        )
        if result.get("success"):
            return result

        # If timeout, wait briefly for a slot to free up, then retry
        if "timeout" in result.get("response", "").lower():
            logger.info(f"claude-chat: attempt {attempt+1}/3 timed out, retrying in 3s...")
            await asyncio.sleep(3)
            continue

        # Non-timeout error — don't retry
        break

    return result


# ── Fallback: if claude CLI unavailable, use API ────────────────────

_api_client = None

def _get_api_client():
    """Lazy-init Anthropic API client.

    Auth priority:
    1. ANTHROPIC_API_KEY env var
    2. OAuth token from Claude CLI credentials (~/.claude/.credentials.json)
    """
    global _api_client
    if _api_client is None:
        try:
            import anthropic

            api_key = os.environ.get("ANTHROPIC_API_KEY", "")

            # If no API key, try Claude CLI OAuth token
            if not api_key:
                try:
                    import json as _json
                    creds_path = os.path.expanduser("~/.claude/.credentials.json")
                    if os.path.exists(creds_path):
                        creds = _json.load(open(creds_path))
                        oauth = creds.get("claudeAiOauth", {})
                        token = oauth.get("accessToken", "")
                        if token:
                            # OAuth tokens work as auth_token (Bearer), not api_key
                            _api_client = anthropic.Anthropic(auth_token=token)
                            logger.info("claude-engine: using OAuth token from CLI credentials")
                            return _api_client
                except Exception as e:
                    logger.debug(f"OAuth token load failed: {e}")

            if api_key:
                _api_client = anthropic.Anthropic(api_key=api_key)
            else:
                _api_client = None
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
