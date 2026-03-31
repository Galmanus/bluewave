"""backends.py — Pluggable inference backends for the Orchestrator.

Two implementations with the same interface:
  AnthropicSDKBackend — uses anthropic SDK, native tool_use, richer protocol
  GeminiCLIBackend    — uses gemini CLI subprocess, tool calls via JSON tags

The Orchestrator calls backend.complete() and gets back BackendResult — either
a text response or a list of tool calls. It doesn't know which backend is active.

Backend selection (automatic, in api.py):
  ANTHROPIC_API_KEY set → AnthropicSDKBackend
  else                  → GeminiCLIBackend
"""

from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("openclaw.backends")


# ── Shared data types ────────────────────────────────────────

@dataclass
class ToolCall:
    id: str
    name: str
    input: Dict[str, Any]


@dataclass
class BackendResult:
    text: Optional[str] = None
    tool_calls: List[ToolCall] = field(default_factory=list)

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)


# Normalized history message types:
#   {"role": "user",              "content": "string"}
#   {"role": "assistant",         "content": "string"}
#   {"role": "assistant_tools",   "tool_calls": [ToolCall, ...]}
#   {"role": "tool_result",       "tool_use_id": "id", "tool_name": "name", "content": "string"}


class Backend(ABC):
    @abstractmethod
    async def complete(
        self,
        messages: List[Dict],
        system_prompt: str,
        tools: List[Dict],
        model: str,
    ) -> BackendResult:
        ...


# ── Anthropic SDK Backend ────────────────────────────────────

class AnthropicSDKBackend(Backend):
    """Uses anthropic SDK directly. Supports native tool_use protocol."""

    MODEL_MAP = {
        "haiku":  "claude-haiku-4-5-20251001",
        "sonnet": "claude-sonnet-4-6",
        "opus":   "claude-opus-4-6",
        # Gemini-style aliases
        "gemini-2.0-flash-lite-preview-02-05": "claude-haiku-4-5-20251001",
        "gemini-2.0-flash":                    "claude-sonnet-4-6",
        "gemini-2.0-pro-exp-02-05":            "claude-opus-4-6",
    }

    def __init__(self):
        import anthropic
        self.client = anthropic.Anthropic()

    def _resolve_model(self, model: str) -> str:
        return self.MODEL_MAP.get(model, model)

    def _convert_tool(self, t: Dict) -> Dict:
        """Normalize tool to Anthropic input_schema format."""
        return {
            "name": t["name"],
            "description": t.get("description", ""),
            "input_schema": t.get("input_schema") or t.get("parameters") or {
                "type": "object", "properties": {},
            },
        }

    def _to_anthropic_messages(self, messages: List[Dict]) -> List[Dict]:
        """Convert normalized history to Anthropic message format.

        Anthropic requires:
        - Tool calls in assistant content as {type: tool_use} blocks
        - Tool results in user content as {type: tool_result} blocks
        - Multiple tool results in a single user message (one per tool call)
        """
        result = []
        i = 0
        while i < len(messages):
            msg = messages[i]
            role = msg["role"]

            if role == "user":
                result.append({"role": "user", "content": msg["content"]})
                i += 1

            elif role == "assistant":
                result.append({"role": "assistant", "content": msg["content"]})
                i += 1

            elif role == "assistant_tools":
                # Convert tool calls to assistant content blocks
                blocks = []
                for tc in msg["tool_calls"]:
                    blocks.append({
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.input,
                    })
                result.append({"role": "assistant", "content": blocks})

                # Collect all consecutive tool_result messages into one user message
                tool_results = []
                i += 1
                while i < len(messages) and messages[i]["role"] == "tool_result":
                    tr = messages[i]
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tr["tool_use_id"],
                        "content": tr["content"],
                    })
                    i += 1
                if tool_results:
                    result.append({"role": "user", "content": tool_results})

            else:
                i += 1

        return result

    async def complete(
        self,
        messages: List[Dict],
        system_prompt: str,
        tools: List[Dict],
        model: str,
    ) -> BackendResult:
        resolved = self._resolve_model(model)
        anthropic_messages = self._to_anthropic_messages(messages)
        anthropic_tools = [self._convert_tool(t) for t in tools] if tools else []

        kwargs: Dict[str, Any] = {
            "model": resolved,
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": anthropic_messages,
        }
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools

        try:
            import anthropic as _anthropic
            response = self.client.messages.create(**kwargs)
        except Exception as e:
            logger.error("Anthropic API error: %s", e)
            return BackendResult(text=f"[Erro Anthropic: {e}]")

        if response.stop_reason == "tool_use":
            tool_calls = [
                ToolCall(id=b.id, name=b.name, input=b.input)
                for b in response.content
                if hasattr(b, "type") and b.type == "tool_use"
            ]
            return BackendResult(tool_calls=tool_calls)

        text = "".join(
            b.text for b in response.content if hasattr(b, "text")
        )
        return BackendResult(text=text)


# ── Gemini CLI Backend ────────────────────────────────────────

class GeminiCLIBackend(Backend):
    """Uses gemini CLI as inference backend.

    Tool calls are negotiated via XML-tagged JSON — the model is instructed to
    respond with <TOOL_CALL>{...}</TOOL_CALL> when it wants to call a tool.
    Regular text responses bypass the tag entirely.
    """

    TAG = "TOOL_CALL"

    def _tools_to_system_section(self, tools: List[Dict]) -> str:
        if not tools:
            return ""
        lines = [
            "\n\n## Tool Calling Protocol",
            f"To call a tool, respond ONLY with (no extra text before or after):",
            f'<{self.TAG}>{{"name": "tool_name", "id": "call_1", "input": {{...}}}}</{self.TAG}>',
            "",
            "## Available Tools",
        ]
        for t in tools:
            params = t.get("parameters") or t.get("input_schema") or {}
            props = params.get("properties", {})
            required = set(params.get("required", []))
            param_desc = ", ".join(
                f"{k}{'*' if k in required else ''}" for k in props
            )
            lines.append(f"- **{t['name']}**: {t.get('description', '')} ({param_desc})")
        return "\n".join(lines)

    def _to_gemini_history(self, messages: List[Dict]) -> List[Dict]:
        """Convert normalized history to simple role/content pairs for gemini_engine."""
        result = []
        for msg in messages:
            role = msg["role"]
            if role == "user":
                result.append({"role": "user", "content": msg["content"]})
            elif role == "assistant":
                result.append({"role": "model", "content": msg["content"]})
            elif role == "assistant_tools":
                # Describe what the model decided to call
                calls_desc = ", ".join(tc.name for tc in msg["tool_calls"])
                result.append({"role": "model", "content": f"[Calling tools: {calls_desc}]"})
            elif role == "tool_result":
                result.append({
                    "role": "user",
                    "content": f"[Tool result for {msg.get('tool_name', '?')}]: {msg['content']}",
                })
        return result

    def _parse_tool_call(self, text: str) -> Optional[ToolCall]:
        pattern = rf"<{self.TAG}>(.*?)</{self.TAG}>"
        match = re.search(pattern, text, re.DOTALL)
        if not match:
            return None
        try:
            data = json.loads(match.group(1).strip())
            return ToolCall(
                id=data.get("id", "call_1"),
                name=data["name"],
                input=data.get("input", {}),
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to parse tool call JSON: %s — %s", match.group(1)[:100], e)
            return None

    async def complete(
        self,
        messages: List[Dict],
        system_prompt: str,
        tools: List[Dict],
        model: str,
    ) -> BackendResult:
        from gemini_engine import gemini_call

        full_system = system_prompt + self._tools_to_system_section(tools)

        # Split history from current message
        history = self._to_gemini_history(messages[:-1])
        last = messages[-1]
        user_msg = last.get("content", "") if last["role"] == "user" else ""

        res = await gemini_call(user_msg, system_prompt=full_system, history=history)

        if not res["success"]:
            return BackendResult(text=f"[Erro Gemini: {res['response']}]")

        text = res["response"]
        tool_call = self._parse_tool_call(text)

        if tool_call:
            return BackendResult(tool_calls=[tool_call])
        return BackendResult(text=text)
