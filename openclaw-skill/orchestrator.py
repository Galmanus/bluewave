"""orchestrator.py — Wave: multi-agent orchestrator com dual-backend.

Fluxo:
  input → classify_intent → seleciona model + tools
        → backend.complete() loop (Anthropic SDK ou Gemini CLI)
        → tool call? executa skill / delega para especialista
        → texto final → retorna

Backend selecionado automaticamente:
  ANTHROPIC_API_KEY no env → AnthropicSDKBackend (tool_use nativo)
  caso contrário            → GeminiCLIBackend (JSON tag protocol)
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from agent_runtime import AgentConfig, AgentRuntime, load_prompt
from backends import Backend, AnthropicSDKBackend, GeminiCLIBackend, ToolCall
from intent_router import classify_intent, get_tools_for_intent, get_prompt_for_intent
from skills_handler import get_all_skill_tools, execute_skill, is_skill_tool
from handler import BlueWaveHandler

logger = logging.getLogger("openclaw.orchestrator")

MAX_TURNS = 10

DELEGATE_TOOL = {
    "name": "delegate_to_agent",
    "description": (
        "Delegate a complex task to a specialist agent. "
        "Available agents: asset-curator, workflow-director, brand-guardian, "
        "analytics-strategist, creative-strategist, ops-admin, "
        "legal-strategist, financial-strategist, security-auditor, "
        "blockchain-specialist, il-traditore."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "agent_id": {
                "type": "string",
                "description": "Specialist agent ID.",
            },
            "task": {
                "type": "string",
                "description": "Task description with full context for the specialist.",
            },
            "put_context": {
                "type": "object",
                "description": "Optional PUT variables (A, F, k, S, w, Phi, archetype).",
            },
        },
        "required": ["agent_id", "task"],
    },
}


def _make_backend() -> Backend:
    if os.environ.get("ANTHROPIC_API_KEY"):
        logger.info("Orchestrator backend: Anthropic SDK")
        return AnthropicSDKBackend()
    logger.info("Orchestrator backend: Gemini CLI")
    return GeminiCLIBackend()


class Orchestrator:
    def __init__(self, handler=None):
        self.backend = _make_backend()
        self.handler = handler
        self.history: List[Dict] = []
        self._call_counter = 0

        # Load agents config
        agents_path = Path(__file__).parent / "agents.json"
        agents_data = json.loads(agents_path.read_text(encoding="utf-8"))
        orch = agents_data["orchestrator"]

        self.system_prompt = load_prompt(
            orch["soul_prompt_file"].replace("prompts/", "")
        )

        # Build specialists map
        self.specialists: Dict[str, AgentConfig] = {}
        for spec in agents_data["specialists"]:
            self.specialists[spec["id"]] = AgentConfig(
                agent_id=spec["id"],
                name=spec["name"],
                emoji=spec.get("emoji", ""),
                system_prompt=load_prompt(
                    spec["soul_prompt_file"].replace("prompts/", "")
                ),
                tool_names=spec["tools"],
                description=spec.get("description", ""),
            )

        self._skill_tools = get_all_skill_tools()

        logger.info(
            "Orchestrator ready — backend: %s, specialists: %d",
            self.backend.__class__.__name__,
            len(self.specialists),
        )

    def _next_id(self) -> str:
        self._call_counter += 1
        return f"call_{self._call_counter}"

    async def _execute_tool(self, name: str, input: Dict) -> str:
        if is_skill_tool(name):
            result = await execute_skill(name, input)
            return json.dumps(result, ensure_ascii=False, default=str)
        if self.handler:
            try:
                result = await self.handler.execute(name, input)
                return json.dumps(result.to_dict(), ensure_ascii=False, default=str)
            except Exception as e:
                return json.dumps({"success": False, "message": str(e)})
        return json.dumps({"success": False, "message": f"No handler for tool: {name}"})

    async def _delegate(
        self,
        agent_id: str,
        task: str,
        put_context: Optional[Dict] = None,
    ) -> str:
        if agent_id not in self.specialists:
            return json.dumps({
                "success": False,
                "message": f"Unknown agent: {agent_id}. "
                           f"Available: {list(self.specialists.keys())}",
            })

        config = self.specialists[agent_id]
        runtime = AgentRuntime(config=config, all_tools=[], handler=self.handler)

        enriched = task
        if put_context:
            put_lines = "\n".join(f"- {k}: {v}" for k, v in put_context.items())
            enriched += f"\n\n--- PUT Context ---\n{put_lines}\n---"

        logger.info("Delegating to %s %s: %s", config.emoji, config.name, task[:60])
        result = await runtime.run(task, context=enriched)
        logger.info("  <- %s responded", config.name)
        return result.text or "(no response from specialist)"

    MAX_HISTORY_MESSAGES = 40

    def _prune_history(self):
        """Keep history within bounds to prevent unbounded memory growth.

        Retains the most recent MAX_HISTORY_MESSAGES entries. Tool results
        and assistant_tools entries are counted individually.
        """
        if len(self.history) > self.MAX_HISTORY_MESSAGES:
            pruned = len(self.history) - self.MAX_HISTORY_MESSAGES
            self.history = self.history[-self.MAX_HISTORY_MESSAGES:]
            logger.debug("Pruned %d old history entries", pruned)

    async def chat(self, user_message: str) -> str:
        self._prune_history()
        self.history.append({"role": "user", "content": user_message})

        # Classify intent → choose model + tool subset
        intent = classify_intent(user_message)
        skill_tools = get_tools_for_intent(intent, self._skill_tools)
        system = get_prompt_for_intent(intent, self.system_prompt)

        # Include delegate tool for non-trivial intents
        tools = list(skill_tools)
        if intent.complexity != "simple":
            tools.append(DELEGATE_TOOL)

        logger.info(
            "Chat — intent: %s, complexity: %s, model: %s, tools: %d",
            intent.category, intent.complexity, intent.model, len(tools),
        )

        # Agentic loop
        for turn in range(MAX_TURNS):
            result = await self.backend.complete(
                messages=self.history,
                system_prompt=system,
                tools=tools,
                model=intent.model,
            )

            if result.has_tool_calls:
                # Store assistant tool-call turn
                self.history.append({
                    "role": "assistant_tools",
                    "tool_calls": result.tool_calls,
                })

                # Execute each tool and collect results
                for tc in result.tool_calls:
                    logger.info("Tool call: %s(%s)", tc.name, str(tc.input)[:80])

                    if tc.name == "delegate_to_agent":
                        output = await self._delegate(
                            tc.input.get("agent_id", ""),
                            tc.input.get("task", ""),
                            tc.input.get("put_context"),
                        )
                    else:
                        output = await self._execute_tool(tc.name, tc.input)

                    logger.info("  -> result: %s", output[:80])
                    self.history.append({
                        "role": "tool_result",
                        "tool_use_id": tc.id,
                        "tool_name": tc.name,
                        "content": output,
                    })

            else:
                # Final text response
                self.history.append({
                    "role": "assistant",
                    "content": result.text,
                })
                return result.text or ""

        return "[Máximo de turnos atingido]"
