"""Core Agent Runtime — the beating heart of the OpenClaw agent system.

Uses the Anthropic Claude API with tool_use to create autonomous agents
that can reason, plan, and execute tools against the Bluewave platform.

Each agent runs an agentic loop:
  1. Send messages + tools to Claude
  2. Claude responds (text and/or tool_use blocks)
  3. Execute each tool call via BlueWaveHandler
  4. Feed results back to Claude
  5. Repeat until Claude responds with only text (no more tool calls)
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import anthropic

from handler import BlueWaveHandler, ToolResult
from token_optimizer import compress_tool_result

logger = logging.getLogger("openclaw.runtime")

# ── Configuration ─────────────────────────────────────────────

MODEL = os.environ.get("OPENCLAW_MODEL", "claude-sonnet-4-20250514")
MAX_TOKENS = int(os.environ.get("OPENCLAW_MAX_TOKENS", "4096"))
MAX_TURNS = int(os.environ.get("OPENCLAW_MAX_TURNS", "25"))
PROMPTS_DIR = Path(__file__).parent / "prompts"

# Cognitive protocols loaded once at module level
_COGNITIVE_BASE = ""
_COGNITIVE_PROTOCOLS: Dict[str, str] = {}

def _load_cognitive_protocols():
    global _COGNITIVE_BASE, _COGNITIVE_PROTOCOLS
    base_path = PROMPTS_DIR / "cognitive_protocol.md"
    if base_path.exists():
        _COGNITIVE_BASE = base_path.read_text(encoding="utf-8")

    for name in ("orchestrator", "guardian", "strategist"):
        path = PROMPTS_DIR / f"cognitive_{name}.md"
        if path.exists():
            _COGNITIVE_PROTOCOLS[name] = path.read_text(encoding="utf-8")

_load_cognitive_protocols()


# ── Data types ────────────────────────────────────────────────

@dataclass
class AgentConfig:
    """Configuration for a single agent."""
    agent_id: str
    name: str
    emoji: str
    system_prompt: str
    tool_names: List[str]
    description: str = ""


@dataclass
class ConversationTurn:
    """A single turn in the conversation."""
    role: str  # "user" or "assistant"
    content: Any  # str or list of content blocks


@dataclass
class AgentResult:
    """Result of an agent execution."""
    agent_id: str
    text: str
    tool_calls_made: int = 0
    turns_used: int = 0
    error: Optional[str] = None


# ── Tool Schema Converter ─────────────────────────────────────

def convert_tool_to_claude_schema(tool_def: Dict) -> Dict:
    """Convert an OpenClaw tool definition to Claude API tool schema."""
    schema = {
        "name": tool_def["name"],
        "description": tool_def["description"],
        "input_schema": tool_def.get("parameters", {"type": "object", "properties": {}}),
    }
    return schema


# ── Agent Runtime ─────────────────────────────────────────────

class AgentRuntime:
    """Runs a single agent with its own conversation context, tools, and system prompt.

    This is the fundamental unit — one Claude conversation with tool_use enabled.
    The orchestrator creates multiple AgentRuntime instances (one per specialist).
    """

    def __init__(
        self,
        config: AgentConfig,
        all_tools: List[Dict],
        handler: BlueWaveHandler,
        client: Optional[anthropic.Anthropic] = None,
        model: Optional[str] = None,
    ):
        self.config = config
        self.handler = handler
        self.client = client or anthropic.Anthropic()
        self.model = model or MODEL
        self.messages = []  # type: List[Dict]

        # Enhance system prompt with cognitive protocols
        self.config = AgentConfig(
            agent_id=config.agent_id,
            name=config.name,
            emoji=config.emoji,
            system_prompt=enhance_prompt_with_cognition(config.agent_id, config.system_prompt),
            tool_names=config.tool_names,
            description=config.description,
        )

        # Filter tools to only those this agent can use
        tool_names_set = set(config.tool_names)
        self.claude_tools = [
            convert_tool_to_claude_schema(t)
            for t in all_tools
            if t["name"] in tool_names_set
        ]

        logger.info(
            "%s %s initialized with %d tools, model=%s, cognitive=True",
            config.emoji, config.name, len(self.claude_tools), self.model,
        )

    def reset(self):
        """Clear conversation history."""
        self.messages = []

    def _call_with_retry(self, messages, attempt=0):
        """Call Claude with prompt caching, retry, and fallback to Haiku.

        Prompt caching: system prompt + tools are marked with cache_control.
        On turn 2+, cached tokens cost 90% less.
        """
        import time as _time
        models = [self.model, "claude-haiku-4-5-20251001"]
        model = models[min(attempt, len(models) - 1)]

        # System prompt with cache_control
        system_blocks = [
            {
                "type": "text",
                "text": self.config.system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]

        # Tools with cache_control on last entry
        cached_tools = None
        if self.claude_tools:
            cached_tools = [t.copy() for t in self.claude_tools]
            if cached_tools:
                cached_tools[-1] = {**cached_tools[-1], "cache_control": {"type": "ephemeral"}}

        try:
            return self.client.messages.create(
                model=model,
                max_tokens=MAX_TOKENS,
                system=system_blocks,
                tools=cached_tools,
                messages=messages,
            )
        except anthropic.RateLimitError:
            if attempt < 2:
                wait = 15 if attempt == 0 else 5
                logger.warning("Rate limited, waiting %ds then trying %s...", wait, models[min(attempt+1, len(models)-1)])
                _time.sleep(wait)
                return self._call_with_retry(messages, attempt + 1)
            raise

    async def execute_tool(self, tool_name: str, tool_input: Dict) -> str:
        """Execute a tool with error recovery context.

        If a tool fails, the returned error includes reasoning guidance
        so Claude can adapt its strategy instead of blindly retrying.
        """
        import time as _t
        _t0 = _t.time()
        try:
            # Check if it's a skill tool
            from skills_handler import is_skill_tool, execute_skill
            if is_skill_tool(tool_name):
                result = await execute_skill(tool_name, tool_input)
                raw = json.dumps(result, ensure_ascii=False, default=str)
                return compress_tool_result(tool_name, raw)

            # Otherwise use Bluewave handler
            result = await self.handler.execute(tool_name, tool_input)
            raw = json.dumps(result.to_dict(), ensure_ascii=False, default=str)
            compressed = compress_tool_result(tool_name, raw)

            # Check for API-level errors in the result
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict) and not parsed.get("success", True):
                    error_msg = parsed.get("message", "")
                    compressed = json.dumps({
                        "success": False,
                        "message": error_msg,
                        "recovery_hint": _get_recovery_hint(tool_name, error_msg),
                    }, ensure_ascii=False)
            except (json.JSONDecodeError, TypeError):
                pass

            return compressed
        except Exception as e:
            logger.error("Tool %s failed: %s", tool_name, e)
            return json.dumps({
                "success": False,
                "message": str(e),
                "recovery_hint": _get_recovery_hint(tool_name, str(e)),
            }, ensure_ascii=False)
        finally:
            try:
                from skills.tracing import trace_tool_call
                _duration = (_t.time() - _t0) * 1000
                trace_tool_call(tool_name, tool_input, {}, _duration)
            except Exception:
                pass

    def run_sync(self, user_message: str, context: Optional[str] = None) -> AgentResult:
        """Run the agent synchronously (blocking agentic loop).

        This is the main entry point. Sends user_message to Claude with the
        agent's system prompt and tools, then loops until Claude stops calling tools.
        """
        import asyncio

        # Build the user message
        if context:
            full_message = "%s\n\n---\nContext from orchestrator: %s" % (user_message, context)
        else:
            full_message = user_message

        self.messages.append({"role": "user", "content": full_message})

        total_tool_calls = 0
        turns = 0

        while turns < MAX_TURNS:
            turns += 1

            try:
                response = self._call_with_retry(self.messages)
            except anthropic.APIError as e:
                logger.error("Claude API error: %s", e)
                return AgentResult(
                    agent_id=self.config.agent_id,
                    text="Sobrecarregado, tenta de novo em 1 minuto.",
                    tool_calls_made=total_tool_calls,
                    turns_used=turns,
                    error=str(e),
                )

            assistant_content = []
            text_parts = []
            tool_uses = []

            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    tool_uses.append(block)
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })

            self.messages.append({"role": "assistant", "content": assistant_content})

            if not tool_uses:
                final_text = "\n".join(text_parts)
                return AgentResult(
                    agent_id=self.config.agent_id,
                    text=final_text,
                    tool_calls_made=total_tool_calls,
                    turns_used=turns,
                )

            # Execute all tool calls and build tool_result messages
            tool_results = []
            for tool_use in tool_uses:
                total_tool_calls += 1
                logger.info(
                    "%s %s calling tool: %s(%s)",
                    self.config.emoji, self.config.name,
                    tool_use.name, json.dumps(tool_use.input, ensure_ascii=False)[:200],
                )

                # Run the tool
                loop = asyncio.get_event_loop() if asyncio._get_running_loop() else None
                if loop and loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        result_str = pool.submit(
                            asyncio.run,
                            self.execute_tool(tool_use.name, tool_use.input)
                        ).result()
                else:
                    result_str = asyncio.run(
                        self.execute_tool(tool_use.name, tool_use.input)
                    )

                logger.info(
                    "  -> %s result: %s",
                    tool_use.name, result_str[:300],
                )

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result_str,
                })

            # Add tool results to conversation
            self.messages.append({"role": "user", "content": tool_results})

        # Hit max turns
        final_text = "\n".join(text_parts) if text_parts else "(Limite de turnos atingido)"
        return AgentResult(
            agent_id=self.config.agent_id,
            text=final_text,
            tool_calls_made=total_tool_calls,
            turns_used=turns,
        )

    async def run(self, user_message: str, context: Optional[str] = None) -> AgentResult:
        """Run the agent asynchronously (agentic loop).

        This is the async version. Preferred for HTTP server usage.
        """
        if context:
            full_message = "%s\n\n---\nContext from orchestrator: %s" % (user_message, context)
        else:
            full_message = user_message

        self.messages.append({"role": "user", "content": full_message})

        total_tool_calls = 0
        turns = 0
        text_parts = []

        while turns < MAX_TURNS:
            turns += 1

            try:
                response = self._call_with_retry(self.messages)
            except anthropic.APIError as e:
                logger.error("Claude API error: %s", e)
                return AgentResult(
                    agent_id=self.config.agent_id,
                    text="Sobrecarregado, tenta de novo em 1 minuto.",
                    tool_calls_made=total_tool_calls,
                    turns_used=turns,
                    error=str(e),
                )

            assistant_content = []
            text_parts = []
            tool_uses = []

            for block in response.content:
                if block.type == "thinking":
                    thinking_text = block.thinking if hasattr(block, "thinking") else ""
                    thinking_block = {"type": "thinking", "thinking": thinking_text}
                    if hasattr(block, "signature") and block.signature:
                        thinking_block["signature"] = block.signature
                    assistant_content.append(thinking_block)
                    try:
                        from skills.tracing import trace_thinking
                        trace_thinking(self.config.agent_id, thinking_text, turns)
                    except Exception:
                        pass
                elif block.type == "text":
                    text_parts.append(block.text)
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    tool_uses.append(block)
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })

            self.messages.append({"role": "assistant", "content": assistant_content})

            if not tool_uses:
                return AgentResult(
                    agent_id=self.config.agent_id,
                    text="\n".join(text_parts),
                    tool_calls_made=total_tool_calls,
                    turns_used=turns,
                )

            # Execute tools in PARALLEL when multiple are requested in the same turn
            # This cuts latency by ~50% for multi-tool turns (e.g., list_assets + get_brand)
            total_tool_calls += len(tool_uses)

            if len(tool_uses) == 1:
                # Single tool — no overhead of gather
                tu = tool_uses[0]
                logger.info("%s %s calling: %s", self.config.emoji, self.config.name, tu.name)
                result_str = await self.execute_tool(tu.name, tu.input)
                tool_results = [{"type": "tool_result", "tool_use_id": tu.id, "content": result_str}]
            else:
                # Multiple tools — execute concurrently
                import asyncio as _aio
                logger.info(
                    "%s %s calling %d tools in parallel: %s",
                    self.config.emoji, self.config.name,
                    len(tool_uses), ", ".join(tu.name for tu in tool_uses),
                )
                results = await _aio.gather(
                    *(self.execute_tool(tu.name, tu.input) for tu in tool_uses),
                    return_exceptions=True,
                )
                tool_results = []
                for tu, res in zip(tool_uses, results):
                    if isinstance(res, Exception):
                        res = json.dumps({"success": False, "message": str(res), "recovery_hint": "Tool raised exception. Try alternative."})
                    tool_results.append({"type": "tool_result", "tool_use_id": tu.id, "content": res})

            self.messages.append({"role": "user", "content": tool_results})

        final_text = "\n".join(text_parts) if text_parts else "(Limite de turnos atingido)"
        return AgentResult(
            agent_id=self.config.agent_id,
            text=final_text,
            tool_calls_made=total_tool_calls,
            turns_used=turns,
        )


# ── Helpers ───────────────────────────────────────────────────

def _json_to_prompt(data: dict, depth: int = 0) -> str:
    """Convert a JSON prompt definition into a readable system prompt string."""
    lines = []
    indent = ""
    for key, value in data.items():
        header = key.replace("_", " ").title()
        if isinstance(value, str):
            if depth == 0:
                lines.append("## %s\n%s\n" % (header, value))
            else:
                lines.append("%s- **%s**: %s" % (indent, header, value))
        elif isinstance(value, bool):
            lines.append("%s- **%s**: %s" % (indent, header, "Yes" if value else "No"))
        elif isinstance(value, (int, float)):
            lines.append("%s- **%s**: %s" % (indent, header, value))
        elif isinstance(value, list):
            lines.append("\n%s**%s:**" % (indent, header))
            for item in value:
                if isinstance(item, str):
                    lines.append("%s- %s" % (indent, item))
                elif isinstance(item, dict):
                    parts = []
                    for k, v in item.items():
                        if isinstance(v, list):
                            parts.append("%s: %s" % (k, " -> ".join(str(x) for x in v)))
                        else:
                            parts.append("%s: %s" % (k, v))
                    lines.append("%s- %s" % (indent, " | ".join(parts)))
        elif isinstance(value, dict):
            if depth == 0:
                lines.append("\n## %s\n" % header)
            else:
                lines.append("\n%s**%s:**" % (indent, header))
            lines.append(_json_to_prompt(value, depth + 1))
    return "\n".join(lines)


def enhance_prompt_with_cognition(agent_id: str, base_prompt: str) -> str:
    """Inject cognitive protocols into an agent's system prompt.

    Adds:
    1. Base cognitive protocol (think-before-act) — all agents
    2. Domain-specific cognitive protocol — matching agents only

    This is where reasoning quality is structurally enforced.
    Token cost: ~200-400 tokens (small relative to response quality gain).
    """
    parts = [base_prompt]

    # Base protocol for all agents
    if _COGNITIVE_BASE:
        parts.append("\n\n" + _COGNITIVE_BASE)

    # Domain-specific protocol
    agent_type_map = {
        "bluewave-orchestrator": "orchestrator",
        "brand-guardian": "guardian",
        "analytics-strategist": "strategist",
        "creative-strategist": "strategist",  # reuse strategist's analytical protocol
    }
    specific_key = agent_type_map.get(agent_id, "")
    if specific_key and specific_key in _COGNITIVE_PROTOCOLS:
        parts.append("\n\n" + _COGNITIVE_PROTOCOLS[specific_key])

    return "\n".join(parts)


def _get_recovery_hint(tool_name: str, error_msg: str) -> str:
    """Generate a recovery hint for the agent when a tool fails.

    This guides Claude's next reasoning step instead of letting it
    blindly retry or give up.
    """
    error_lower = error_msg.lower()

    if "not found" in error_lower or "404" in error_lower:
        return "Resource not found. Verify the ID is correct, or search for the resource by name instead."

    if "connect" in error_lower or "timeout" in error_lower:
        return "Connection failed. The service may be temporarily unavailable. Try answering from context or inform the user."

    if "permission" in error_lower or "403" in error_lower or "401" in error_lower:
        return "Permission denied. This action may require a different role. Inform the user about the access requirement."

    if "limit" in error_lower or "402" in error_lower:
        return "Plan limit reached. Inform the user they need to upgrade their plan."

    if "500" in error_lower or "internal" in error_lower:
        return "Server error. Do NOT retry the same call. Try an alternative approach or inform the user."

    if "empty" in error_lower or "no data" in error_lower:
        return "No data available. The tenant may not have this data yet. Guide the user on how to create it."

    return "Tool failed. Analyze the error, consider an alternative tool or approach, and inform the user if the issue persists."


def load_prompt(filename: str) -> str:
    """Load a soul prompt from the prompts/ directory. Supports .md and .json."""
    path = PROMPTS_DIR / filename

    # Try JSON version first (more detailed)
    json_path = path.with_suffix(".json")
    if json_path.exists():
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            return _json_to_prompt(data)
        except Exception as e:
            logger.warning("Failed to parse JSON prompt %s: %s", json_path, e)

    # Fall back to markdown
    if path.exists():
        return path.read_text(encoding="utf-8")

    logger.warning("Prompt file not found: %s", path)
    return "You are a helpful assistant."


def load_all_tools() -> List[Dict]:
    """Load all tool definitions from tools.json."""
    tools_path = Path(__file__).parent / "tools.json"
    if tools_path.exists():
        data = json.loads(tools_path.read_text(encoding="utf-8"))
        return data.get("tools", [])
    return []
