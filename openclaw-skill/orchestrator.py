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
    load_all_tools,
    load_prompt,
    MAX_TOKENS,
    MAX_TURNS,
)
from handler import BlueWaveHandler
from skills_handler import get_all_skill_tools, execute_skill, is_skill_tool
from skills.tracing import trace_agent_cycle, trace_delegation, is_enabled as tracing_enabled
from intent_router import classify_intent, get_tools_for_intent, get_prompt_for_intent
from context_manager import ContextWindowManager
from token_optimizer import compress_tool_result, compress_old_tool_results

logger = logging.getLogger("openclaw.orchestrator")

MODEL = os.environ.get("OPENCLAW_MODEL", "claude-haiku-4-5-20251001")

# ── Delegation Tool (special) ─────────────────────────────────

DELEGATE_TOOL = {
    "name": "delegate_to_agent",
    "description": (
        "Delegate a task to a specialist agent. Use this when the user's request "
        "requires domain expertise. Pass the specialist ID and a clear task description. "
        "The specialist will execute the task autonomously (including calling tools) "
        "and return their response."
    ),
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
                    "legal-strategist",
                    "security-auditor",
                    "blockchain-specialist",
                ],
                "description": "ID of the specialist agent to delegate to.",
            },
            "task": {
                "type": "string",
                "description": (
                    "Clear description of what the specialist should do. "
                    "Include all relevant context from the user's message."
                ),
            },
            "user_message": {
                "type": "string",
                "description": "The original user message, verbatim.",
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

        # Add all skill tools (web search, X/Twitter, email, intelligence, etc.)
        self.skill_tools = get_all_skill_tools()
        for skill_tool in self.skill_tools:
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

        # Enhance system prompt with agent directory
        agent_directory = "\n\n## Agentes Disponíveis\n\n"
        for sid, cfg in self.specialists.items():
            agent_directory += "- **%s %s** (`%s`): %s\n" % (cfg.emoji, cfg.name, sid, cfg.description)

        # Add skills directory to system prompt
        skills_info = "\n\n## Capacidades Diretas (Skills)\n\n"
        skills_info += "Além de delegar para especialistas, você tem acesso direto a:\n"
        skills_info += "- **web_search** / **web_news** — pesquisa web e noticias em tempo real\n"
        skills_info += "- **scrape_url** — extrair conteudo de qualquer URL\n"
        skills_info += "- **x_search** / **x_trending** — inteligencia do X/Twitter\n"
        skills_info += "- **x_profile_research** — pesquisa de perfis do X\n"
        skills_info += "- **social_monitor** — monitoramento de mencoes em redes sociais\n"
        skills_info += "- **competitor_analysis** — analise competitiva profunda\n"
        skills_info += "- **market_research** — pesquisa de mercado\n"
        skills_info += "- **seo_analysis** — auditoria SEO de qualquer URL\n"
        skills_info += "- **lead_finder** — encontrar prospects e leads\n"
        skills_info += "- **draft_cold_email** — gerar emails de outreach\n"
        skills_info += "- **send_email** — enviar emails\n"
        skills_info += "- **directory_submission** — pacote de submissao para diretorios\n"
        skills_info += "- **google_trends** — tendencias de busca\n"

        self.system_prompt = self.orchestrator_config.system_prompt + agent_directory + skills_info

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
        """Run a specialist agent and return its response. Traced via LangSmith."""
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

        return json.dumps({
            "success": result.error is None,
            "agent": agent_id,
            "agent_name": "%s %s" % (config.emoji, config.name),
            "response": result.text,
            "tool_calls_made": result.tool_calls_made,
        }, ensure_ascii=False)

    def _call_claude(self, messages, model=None, system_prompt=None, tools=None, attempt=0):
        """Call Claude with intent-optimized model/prompt/tools and context management."""
        import time as _time

        use_model = model or self.model
        use_system = system_prompt or self.system_prompt
        use_tools = tools if tools is not None else self.orchestrator_tools

        # Apply rolling context window to prevent token overflow
        managed_messages = self.context_manager.prepare_messages(messages)

        try:
            kwargs = dict(
                model=use_model,
                max_tokens=MAX_TOKENS,
                system=use_system,
                messages=managed_messages,
            )
            if use_tools:
                kwargs["tools"] = use_tools
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
        routed_prompt = get_prompt_for_intent(intent, self.system_prompt)
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
                if block.type == "text":
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
        routed_prompt = get_prompt_for_intent(intent, self.system_prompt)
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
                response = self._call_claude(
                    self.messages,
                    model=routed_model,
                    system_prompt=routed_prompt,
                    tools=routed_tools if routed_tools else None,
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

            # No tool calls — done
            if not tool_uses:
                return "\n".join(text_parts)

            # Execute tool calls
            tool_results = []
            for tool_use in tool_uses:
                if tool_use.name == "delegate_to_agent":
                    # Special: delegate to a specialist agent
                    agent_id = tool_use.input.get("agent_id", "")
                    task = tool_use.input.get("task", "")
                    orig_msg = tool_use.input.get("user_message", user_message)

                    result_str = await self._delegate_to_specialist(agent_id, task, orig_msg)
                else:
                    # Regular tool call
                    logger.info("🌊 Wave calling tool: %s", tool_use.name)
                    result_str = await self._execute_orchestrator_tool(
                        tool_use.name, tool_use.input
                    )

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result_str,
                })

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
