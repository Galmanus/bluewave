"""Multi-Agent Orchestrator — Wave coordinates 6 specialist agents.

Architecture:
  User message → Wave (orchestrator) → classifies intent → delegates to specialist
  Specialist runs its own agentic loop (with domain-specific tools) → returns result
  Wave formats the specialist's result and responds to the user

The delegation happens via a special `delegate_to_agent` tool that Wave can call.
When Wave calls it, we intercept the call, run the specialist, and return
the specialist's response as the tool result.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import anthropic

from agent_runtime import (
    AgentConfig,
    AgentResult,
    AgentRuntime,
    convert_tool_to_claude_schema,
    enhance_prompt_with_cognition,
    load_all_tools,
    load_prompt,
    MAX_TOKENS,
    MAX_TURNS,
)
from handler import BlueWaveHandler
from skills_handler import get_all_skill_tools, execute_skill, is_skill_tool
from skills.tracing import trace_agent_cycle, trace_delegation, trace_thinking, is_enabled as tracing_enabled
from intent_router import classify_intent, get_tools_for_intent, get_prompt_for_intent
from context_manager import ContextWindowManager
from token_optimizer import compress_tool_result, compress_old_tool_results

logger = logging.getLogger("openclaw.orchestrator")

MODEL = os.environ.get("OPENCLAW_MODEL", "claude-haiku-4-5-20251001")

# ── Delegation Tool (special) ─────────────────────────────────

DELEGATE_TOOL = {
    "name": "delegate_to_agent",
    "description": "Delegate a task to a specialist agent for domain-specific execution.",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_id": {
                "type": "string",
                "enum": [
                    "asset-curator",
                    "workflow-director",
                    "brand-guardian",
                    "analytics-strategist",
                    "creative-strategist",
                    "ops-admin",
                ],
                "description": "Specialist ID.",
            },
            "task": {
                "type": "string",
                "description": "What the specialist should do, with context.",
            },
        },
        "required": ["agent_id", "task"],
    },
}


# ── Orchestrator ──────────────────────────────────────────────

class Orchestrator:
    """Wave — the orchestrator that routes messages to specialist agents.

    Wave has a few lightweight tools (list assets, get profile, etc.) for
    simple queries, plus the special `delegate_to_agent` tool for complex tasks.
    """

    def __init__(
        self,
        handler: Optional[BlueWaveHandler] = None,
        client: Optional[anthropic.Anthropic] = None,
        model: Optional[str] = None,
    ):
        self.client = client or anthropic.Anthropic()
        self.model = model or MODEL
        self.handler = handler or BlueWaveHandler()
        self.all_tools = load_all_tools()
        self.messages = []  # type: List[Dict]
        self.context_manager = ContextWindowManager()

        # Load agent configs from agents.json
        agents_path = Path(__file__).parent / "agents.json"
        agents_data = json.loads(agents_path.read_text(encoding="utf-8"))

        # Build orchestrator config
        orch = agents_data["orchestrator"]
        self.orchestrator_config = AgentConfig(
            agent_id=orch["id"],
            name=orch["name"],
            emoji=orch["emoji"],
            system_prompt=load_prompt(orch["soul_prompt_file"].replace("prompts/", "")),
            tool_names=orch["tools"],
            description=orch["description"],
        )

        # Build specialist configs
        self.specialists = {}  # type: Dict[str, AgentConfig]
        for spec in agents_data["specialists"]:
            config = AgentConfig(
                agent_id=spec["id"],
                name=spec["name"],
                emoji=spec["emoji"],
                system_prompt=load_prompt(spec["soul_prompt_file"].replace("prompts/", "")),
                tool_names=spec["tools"],
                description=spec["description"],
            )
            self.specialists[spec["id"]] = config

        # Build orchestrator's Claude tools (its own tools + delegate tool)
        orch_tool_names = set(self.orchestrator_config.tool_names)
        orch_tool_names.discard("delegate_to_agent")  # handled specially
        self.orchestrator_tools = [
            convert_tool_to_claude_schema(t)
            for t in self.all_tools
            if t["name"] in orch_tool_names
        ]
        self.orchestrator_tools.append(DELEGATE_TOOL)

        # Only add essential skill tools to orchestrator (web_search, memory).
        # Other skill tools are loaded per-specialist via _skill_tool_names_by_agent.
        # This saves ~1800 tokens per orchestrator call.
        self.skill_tools = get_all_skill_tools()
        _orch_skill_allowlist = {
            "web_search", "web_news", "save_learning", "recall_learnings",
            "create_skill", "list_skills", "tracing_status",
        }
        for skill_tool in self.skill_tools:
            if skill_tool["name"] in _orch_skill_allowlist:
                self.orchestrator_tools.append(convert_tool_to_claude_schema(skill_tool))

        # Also add skill tools to relevant specialists
        self._skill_tool_names_by_agent = {
            "analytics-strategist": [
                "web_search", "web_news", "competitor_analysis", "market_research",
                "seo_analysis", "social_monitor", "x_trending",
            ],
            "creative-strategist": [
                "web_search", "web_news", "x_search", "x_trending",
                "google_trends", "scrape_url",
            ],
            "brand-guardian": [
                "web_search", "seo_analysis", "social_monitor", "scrape_url",
            ],
            "ops-admin": [
                "web_search", "lead_finder", "draft_cold_email",
                "send_email", "directory_submission",
            ],
        }

        # Pre-create specialist runtimes (lazy — created on first delegation)
        self._specialist_runtimes = {}  # type: Dict[str, AgentRuntime]

        # Compact agent directory (saves ~200 tokens vs. full descriptions)
        agent_directory = "\n\n## Agentes\n"
        for sid, cfg in self.specialists.items():
            # Only include short name + ID, not full PhD description
            agent_directory += "- %s `%s`\n" % (cfg.emoji, sid)

        # Compact skills directory (saves ~500 tokens vs. full listing)
        skills_info = "\n\n## Skills Diretas\nweb_search, web_news, save/recall_learnings, create_skill. Demais skills via especialistas.\n"

        # Enhance orchestrator prompt with cognitive protocol
        enhanced_base = enhance_prompt_with_cognition(
            "bluewave-orchestrator",
            self.orchestrator_config.system_prompt,
        )
        self.system_prompt = enhanced_base + agent_directory + skills_info

        # Lazy-loaded PUT framework addon (~600 tokens, only for complex intents)
        put_path = Path(__file__).parent / "prompts" / "put_framework.md"
        self._put_addon = put_path.read_text(encoding="utf-8") if put_path.exists() else ""

        logger.info(
            "🌊 Orchestrator initialized: %d specialists, %d orchestrator tools, model=%s",
            len(self.specialists), len(self.orchestrator_tools), self.model,
        )

    def _get_specialist(self, agent_id: str) -> AgentRuntime:
        """Get or create a specialist AgentRuntime."""
        if agent_id not in self._specialist_runtimes:
            config = self.specialists[agent_id]
            runtime = AgentRuntime(
                config=config,
                all_tools=self.all_tools,
                handler=self.handler,
                client=self.client,
                model=self.model,
            )
            self._specialist_runtimes[agent_id] = runtime
        return self._specialist_runtimes[agent_id]

    def reset(self):
        """Reset all conversation state."""
        self.messages = []
        self.context_manager = ContextWindowManager()
        for rt in self._specialist_runtimes.values():
            rt.reset()

    async def _execute_orchestrator_tool(self, tool_name: str, tool_input: Dict) -> str:
        """Execute a tool that the orchestrator calls directly (not delegation).

        Results are compressed via token_optimizer to minimize context growth.
        """
        # Check if it's a skill tool first
        if is_skill_tool(tool_name):
            logger.info("Executing skill: %s", tool_name)
            result = await execute_skill(tool_name, tool_input)
            raw = json.dumps(result, ensure_ascii=False, default=str)
            return compress_tool_result(tool_name, raw)

        # Otherwise, it's a Bluewave API tool
        try:
            result = await self.handler.execute(tool_name, tool_input)
            raw = json.dumps(result.to_dict(), ensure_ascii=False, default=str)
            return compress_tool_result(tool_name, raw)
        except Exception as e:
            return json.dumps({"success": False, "data": None, "message": str(e)})

    async def _delegate_to_specialist(self, agent_id: str, task: str, user_message: str = "") -> str:
        """Run a specialist agent with verification gate.

        Verification: checks that the specialist's response is non-empty,
        doesn't contain error indicators, and actually addresses the task.
        If verification fails, adds diagnostic context for the orchestrator.
        """
        import time as _time

        if agent_id not in self.specialists:
            return json.dumps({
                "success": False,
                "agent": agent_id,
                "message": "Agente desconhecido: %s" % agent_id,
            })

        specialist = self._get_specialist(agent_id)
        config = self.specialists[agent_id]

        logger.info(
            "🌊 Wave delegating to %s %s: %s",
            config.emoji, config.name, task[:100],
        )

        t0 = _time.time()
        message = user_message if user_message else task
        result = await specialist.run(message, context=task)
        duration_ms = (_time.time() - t0) * 1000

        logger.info(
            "  <- %s %s responded (%d tool calls, %d turns, %.1fms)",
            config.emoji, config.name, result.tool_calls_made, result.turns_used, duration_ms,
        )

        # Trace delegation to LangSmith
        trace_delegation(
            "orchestrator", agent_id, task,
            result.text[:500] if result.text else "",
            duration_ms,
        )

        # ── VERIFICATION GATE ─────────────────────────────────
        verification = self._verify_specialist_result(result, task, agent_id)

        response_payload = {
            "success": result.error is None and verification["passed"],
            "agent": agent_id,
            "agent_name": "%s %s" % (config.emoji, config.name),
            "response": result.text,
            "tool_calls_made": result.tool_calls_made,
        }

        # Add diagnostic context if verification flagged issues
        if not verification["passed"]:
            response_payload["verification_warning"] = verification["reason"]
            logger.warning(
                "⚠️ Verification gate flagged %s result: %s",
                agent_id, verification["reason"],
            )

        return json.dumps(response_payload, ensure_ascii=False)

    def _verify_specialist_result(self, result: AgentResult, task: str, agent_id: str) -> Dict:
        """Verification gate: check specialist output quality.

        Returns {"passed": bool, "reason": str}
        Zero API calls — pure heuristic checks.
        """
        # Check 1: Non-empty response
        if not result.text or len(result.text.strip()) < 20:
            return {"passed": False, "reason": "Specialist returned empty or too-short response. May need re-query."}

        # Check 2: Error in response
        if result.error:
            return {"passed": False, "reason": "Specialist encountered error: %s" % result.error}

        # Check 3: Hit max turns (may be incomplete)
        if result.turns_used >= MAX_TURNS - 1:
            return {"passed": False, "reason": "Specialist hit turn limit — response may be incomplete."}

        # Check 4: Response is just an error message forwarded
        lower = result.text.lower()
        error_indicators = ["sobrecarregado", "tenta de novo", "error", "failed", "cannot connect"]
        if any(ind in lower for ind in error_indicators) and result.tool_calls_made == 0:
            return {"passed": False, "reason": "Specialist returned error without attempting tools."}

        # Check 5: Zero tool calls for tool-requiring tasks
        tool_keywords = {"list", "get", "check", "search", "analyze", "report", "approve", "reject"}
        task_lower = task.lower()
        if result.tool_calls_made == 0 and any(kw in task_lower for kw in tool_keywords):
            return {"passed": False, "reason": "Specialist answered without calling tools — may be hallucinating data."}

        return {"passed": True, "reason": ""}

    def _call_claude(self, messages, model=None, system_prompt=None, tools=None, attempt=0, thinking_budget=0):
        """Call Claude with prompt caching, extended thinking, and context management.

        Prompt caching: system prompt is cached at 90% discount on turns 2+.
        Extended thinking: for complex intents, Claude gets a thinking budget
        to reason internally before responding (improves quality on analysis tasks).
        """
        import time as _time

        use_model = model or self.model
        use_system = system_prompt or self.system_prompt
        use_tools = tools if tools is not None else self.orchestrator_tools

        # Apply rolling context window to prevent token overflow
        managed_messages = self.context_manager.prepare_messages(messages)

        # Build system prompt with cache_control for prompt caching
        # The system prompt is static across turns — perfect cache candidate
        system_blocks = [
            {
                "type": "text",
                "text": use_system,
                "cache_control": {"type": "ephemeral"},
            }
        ]

        try:
            kwargs = dict(
                model=use_model,
                max_tokens=MAX_TOKENS,
                system=system_blocks,
                messages=managed_messages,
            )
            if use_tools:
                # Mark tools with cache_control on the last tool (Anthropic requirement)
                cached_tools = [t.copy() for t in use_tools]
                if cached_tools:
                    cached_tools[-1] = {**cached_tools[-1], "cache_control": {"type": "ephemeral"}}
                kwargs["tools"] = cached_tools

            # Extended thinking: give Claude a scratchpad for complex reasoning
            if thinking_budget > 0:
                kwargs["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}
                # Extended thinking requires higher max_tokens
                kwargs["max_tokens"] = max(MAX_TOKENS, thinking_budget + 4096)
                logger.info("🧠 Extended thinking enabled: %d token budget", thinking_budget)

            return self.client.messages.create(**kwargs)
        except anthropic.RateLimitError as e:
            if attempt < 2:
                wait = 15 if attempt == 0 else 5
                fallback = "claude-haiku-4-5-20251001"
                logger.warning("Rate limited (attempt %d), waiting %ds then trying %s...",
                             attempt, wait, fallback)
                _time.sleep(wait)
                return self._call_claude(messages, model=fallback, system_prompt=use_system,
                                         tools=use_tools, attempt=attempt + 1)
            raise

    async def chat_streaming(self, user_message: str, on_text_chunk=None, on_tool_start=None, on_tool_end=None) -> str:
        """Streaming-aware chat — calls callbacks for progressive UI updates.

        Falls back to regular chat() but adds hook points for SSE integration.
        Currently uses the synchronous Claude SDK, so text arrives as full blocks
        per turn. Full streaming (token-by-token) requires the async streaming API.
        """
        intent = classify_intent(self.client, user_message)
        routed_tools = get_tools_for_intent(intent, self.orchestrator_tools)
        routed_prompt = get_prompt_for_intent(intent, self.system_prompt, self._put_addon)
        routed_model = intent.model

        self.messages.append({"role": "user", "content": user_message})

        turns = 0
        text_parts = []

        while turns < MAX_TURNS:
            turns += 1

            try:
                response = self._call_claude(
                    self.messages,
                    model=routed_model,
                    system_prompt=routed_prompt,
                    tools=routed_tools if routed_tools else None,
                )
            except anthropic.APIError as e:
                logger.error("Claude API error: %s", e)
                return "Tô sobrecarregado agora, tenta de novo em 1 minuto."

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
                    trace_thinking("orchestrator", thinking_text, turns, intent.category)
                elif block.type == "text":
                    text_parts.append(block.text)
                    assistant_content.append({"type": "text", "text": block.text})
                    if on_text_chunk:
                        on_text_chunk(block.text)
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
                return "\n".join(text_parts)

            tool_results = []
            for tool_use in tool_uses:
                if on_tool_start:
                    on_tool_start(tool_use.name)

                if tool_use.name == "delegate_to_agent":
                    agent_id = tool_use.input.get("agent_id", "")
                    task = tool_use.input.get("task", "")
                    orig_msg = tool_use.input.get("user_message", user_message)
                    result_str = await self._delegate_to_specialist(agent_id, task, orig_msg)
                else:
                    result_str = await self._execute_orchestrator_tool(tool_use.name, tool_use.input)

                if on_tool_end:
                    on_tool_end(tool_use.name)

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result_str,
                })

            self.messages.append({"role": "user", "content": tool_results})

        return "\n".join(text_parts) if text_parts else "(Limite de turnos atingido)"

    async def chat(self, user_message: str) -> str:
        """Send a message to Wave and get a response.

        Uses intent routing to minimize token usage:
        - Simple queries (greetings): Haiku, no tools, light prompt (~2k tokens)
        - Medium queries (brand, assets): Haiku, relevant tools only (~8k tokens)
        - Complex queries (research, sales): Sonnet, full prompt + tools (~28k tokens)
        """
        import time as _time
        _t0 = _time.time()

        # Classify intent (zero tokens — heuristic-based)
        intent = classify_intent(self.client, user_message)

        # Select tools and prompt based on intent
        routed_tools = get_tools_for_intent(intent, self.orchestrator_tools)
        routed_prompt = get_prompt_for_intent(intent, self.system_prompt, self._put_addon)
        routed_model = intent.model

        est_tokens = len(routed_prompt) // 4 + len(routed_tools) * 200
        logger.info(
            "🧭 Intent: %s/%s → model=%s, tools=%d, ~%dk tokens (was ~28k)",
            intent.category, intent.complexity,
            routed_model.split("-")[1] if "-" in routed_model else routed_model,
            len(routed_tools), est_tokens // 1000,
        )

        # Trace the overall chat cycle
        trace_agent_cycle("chat", "orchestrator", {
            "intent": intent.category,
            "complexity": intent.complexity,
            "model": routed_model,
            "tools_count": len(routed_tools),
            "est_tokens": est_tokens,
            "message_preview": user_message[:200],
            "context_stats": self.context_manager.get_stats(),
        })

        self.messages.append({"role": "user", "content": user_message})

        turns = 0
        text_parts = []

        while turns < MAX_TURNS:
            turns += 1

            try:
                # Only use thinking budget on first turn (not tool-result turns)
                use_thinking = intent.thinking_budget if turns == 1 else 0
                response = self._call_claude(
                    self.messages,
                    model=routed_model,
                    system_prompt=routed_prompt,
                    tools=routed_tools if routed_tools else None,
                    thinking_budget=use_thinking,
                )
            except anthropic.APIError as e:
                logger.error("Claude API error: %s", e)
                return "Tô sobrecarregado agora, tenta de novo em 1 minuto."

            # Track token usage for cost awareness
            usage = response.usage if hasattr(response, "usage") else None
            if usage:
                self.context_manager.track_usage(
                    input_tokens=getattr(usage, "input_tokens", 0),
                    output_tokens=getattr(usage, "output_tokens", 0),
                )

            # Parse response
            assistant_content = []
            text_parts = []
            tool_uses = []

            for block in response.content:
                if block.type == "thinking":
                    thinking_text = block.thinking if hasattr(block, "thinking") else ""
                    # Must preserve signature for API round-trip (required by Anthropic)
                    thinking_block = {"type": "thinking", "thinking": thinking_text}
                    if hasattr(block, "signature") and block.signature:
                        thinking_block["signature"] = block.signature
                    assistant_content.append(thinking_block)
                    logger.info("🧠 Thinking: %d chars", len(thinking_text))

                    # Send full thinking to LangSmith
                    trace_thinking(
                        agent_id="orchestrator",
                        thinking_text=thinking_text,
                        turn=turns,
                        intent=intent.category,
                    )
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

            # No tool calls — done
            if not tool_uses:
                return "\n".join(text_parts)

            # Execute tool calls — parallel for non-delegation, sequential for delegation
            import asyncio as _aio

            async def _exec_one(tu):
                if tu.name == "delegate_to_agent":
                    return await self._delegate_to_specialist(
                        tu.input.get("agent_id", ""),
                        tu.input.get("task", ""),
                        tu.input.get("user_message", user_message),
                    )
                else:
                    logger.info("🌊 Wave calling tool: %s", tu.name)
                    return await self._execute_orchestrator_tool(tu.name, tu.input)

            if len(tool_uses) == 1:
                result_str = await _exec_one(tool_uses[0])
                tool_results = [{"type": "tool_result", "tool_use_id": tool_uses[0].id, "content": result_str}]
            else:
                # Parallel execution for multiple tools in same turn
                logger.info("🌊 Executing %d tools in parallel", len(tool_uses))
                results = await _aio.gather(
                    *(_exec_one(tu) for tu in tool_uses),
                    return_exceptions=True,
                )
                tool_results = []
                for tu, res in zip(tool_uses, results):
                    content = res if isinstance(res, str) else json.dumps({"success": False, "message": str(res)})
                    tool_results.append({"type": "tool_result", "tool_use_id": tu.id, "content": content})

            self.messages.append({"role": "user", "content": tool_results})

        return "\n".join(text_parts) if text_parts else "(Limite de turnos atingido)"

    def chat_sync(self, user_message: str) -> str:
        """Synchronous wrapper for chat()."""
        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, self.chat(user_message)).result()
        else:
            return asyncio.run(self.chat(user_message))
