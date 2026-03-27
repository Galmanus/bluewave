"""Multi-Agent Orchestrator — Wave coordinates 9 specialist agents.

Architecture:
  User message → Wave (orchestrator) → classifies intent → delegates to specialist
  Specialist runs its own agentic loop (with domain-specific tools) → returns result
  Wave formats the specialist's result and responds to the user

Model tiering (automatic):
  Haiku  — greetings, lookups, status (~$0.001/1K tokens, <1s)
  Sonnet — tool execution, content, analysis (~$0.015/1K tokens, 2-5s)
  Opus   — cross-domain strategy, research, high-stakes (~$0.075/1K tokens, 5-15s)

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
    "description": (
        "Delegate a task to a specialist agent for domain-specific execution. "
        "Include relevant context in the task field: prospect PUT variables, "
        "strategic constraints, or specific data the specialist needs. "
        "The richer the context, the better the specialist output."
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
                    "financial-strategist",
                    "security-auditor",
                    "blockchain-specialist",
                ],
                "description": "Specialist ID.",
            },
            "task": {
                "type": "string",
                "description": (
                    "What the specialist should do. MUST include relevant context: "
                    "prospect info, PUT variables (A, F, k, S, w, Phi if known), "
                    "constraints, urgency level, and expected output format."
                ),
            },
            "put_context": {
                "type": "object",
                "description": (
                    "Optional PUT variables for the target/prospect. "
                    "Specialist will use these to calibrate analysis."
                ),
                "properties": {
                    "A": {"type": "number", "description": "Ambition (0-1)"},
                    "F": {"type": "number", "description": "Fear (0-1)"},
                    "k": {"type": "number", "description": "Shadow coefficient (0-1)"},
                    "S": {"type": "number", "description": "Status (0-1)"},
                    "w": {"type": "number", "description": "Pain intensity (0-1)"},
                    "Phi": {"type": "number", "description": "Self-delusion (0-2)"},
                    "archetype": {"type": "string", "description": "PUT archetype if identified"},
                    "FP": {"type": "number", "description": "Fracture Potential if calculated"},
                    "omega_active": {"type": "boolean", "description": "Is Omega (desperation) active?"},
                },
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
        agent_directory = "\n\n## Agents\n"
        for sid, cfg in self.specialists.items():
            # Only include short name + ID, not full PhD description
            agent_directory += "- %s `%s`\n" % (cfg.emoji, sid)

        # Compact skills directory (saves ~500 tokens vs. full listing)
        skills_info = "\n\n## Direct Skills\nweb_search, web_news, save/recall_learnings, create_skill. Other skills via specialists.\n"

        # Enhance orchestrator prompt with cognitive protocol
        enhanced_base = enhance_prompt_with_cognition(
            "bluewave-orchestrator",
            self.orchestrator_config.system_prompt,
        )
        self.system_prompt = enhanced_base + agent_directory + skills_info

        # Lazy-loaded PUT framework addon (~600 tokens, only for complex intents)
        put_path = Path(__file__).parent / "prompts" / "put_framework.md"
        self._put_addon = put_path.read_text(encoding="utf-8") if put_path.exists() else ""

        # Shared PUT context for specialist enrichment (~800 tokens, injected on strategic tasks)
        shared_put_path = Path(__file__).parent / "prompts" / "shared_put_context.md"
        self._shared_put_context = shared_put_path.read_text(encoding="utf-8") if shared_put_path.exists() else ""

        # Pre-cache orchestrator tools with cache_control on last tool
        # Avoids re-copying and re-marking on every _call_claude invocation
        self._cached_orchestrator_tools = [t.copy() for t in self.orchestrator_tools]
        if self._cached_orchestrator_tools:
            self._cached_orchestrator_tools[-1] = {
                **self._cached_orchestrator_tools[-1],
                "cache_control": {"type": "ephemeral"},
            }

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

    async def _record_audit(self, action: str, tool: str, result: Any = None):
        """Record action to Hedera HCS audit trail (non-blocking).

        This is the integration point between Wave's cognitive operations
        and the immutable on-chain record. Every significant action leaves
        a verifiable trace on Hedera.

        Cost: ~$0.0001 per entry. Non-blocking — failure does not affect operation.
        """
        try:
            from skills.hedera_writer import submit_hcs_message

            # Determine revenue from result (if applicable)
            revenue_usd = 0.0
            if isinstance(result, dict):
                revenue_usd = result.get("revenue_usd", 0.0)

            # Only audit significant actions (skip low-value reads to save cost)
            skip_tools = {
                "web_search", "web_news", "scrape_url",  # research reads
                "recall_learnings", "recall_strategies", "recall_agent_intel",  # memory reads
                "moltbook_feed", "moltbook_home",  # social reads
                "hedera_check_balance", "hedera_audit_trail",  # hedera reads
                "hedera_cost_report", "hedera_platform_stats",  # hedera reads
                "self_diagnostic",  # diagnostic
            }
            if tool in skip_tools:
                return

            await submit_hcs_message(
                action=action,
                agent="wave",
                tool=tool,
                details=str(result)[:200] if result else "",
                revenue_usd=revenue_usd,
            )
        except Exception as e:
            # Audit failure must NEVER break agent operation
            logger.debug("Audit recording failed (non-blocking): %s", e)

    async def _execute_orchestrator_tool(self, tool_name: str, tool_input: Dict) -> str:
        """Execute a tool that the orchestrator calls directly (not delegation).

        Results are compressed via token_optimizer to minimize context growth.
        Every tool execution is recorded on the Hedera audit trail (HCS).
        """
        # Check if it's a skill tool first
        if is_skill_tool(tool_name):
            logger.info("Executing skill: %s", tool_name)
            result = await execute_skill(tool_name, tool_input)

            # Record on Hedera audit trail (non-blocking)
            await self._record_audit("skill_execution", tool_name, result)

            raw = json.dumps(result, ensure_ascii=False, default=str)
            return compress_tool_result(tool_name, raw)

        # Otherwise, it's a Bluewave API tool
        try:
            result = await self.handler.execute(tool_name, tool_input)
            raw = json.dumps(result.to_dict(), ensure_ascii=False, default=str)
            return compress_tool_result(tool_name, raw)
        except Exception as e:
            return json.dumps({"success": False, "data": None, "message": str(e)})

    async def _delegate_to_specialist(
        self, agent_id: str, task: str, user_message: str = "", put_context: Optional[Dict] = None
    ) -> str:
        """Run a specialist agent with enriched delegation and post-execution filtering.

        Three-stage pipeline:
        1. ENRICHMENT: Inject PUT context and shared knowledge into the task brief
        2. EXECUTION: Specialist runs with enriched context
        3. FILTERING: Verify output quality and apply value-alignment check
        """
        import time as _time

        if agent_id not in self.specialists:
            return json.dumps({
                "success": False,
                "agent": agent_id,
                "message": "Unknown agent: %s" % agent_id,
            })

        specialist = self._get_specialist(agent_id)
        config = self.specialists[agent_id]

        # ── STAGE 1: ENRICHED DELEGATION BRIEF ─────────────────
        enriched_task = task

        # Inject PUT context if provided
        if put_context:
            put_section = "\n\n--- PUT CONTEXT (for this specific target) ---\n"
            for var_name, var_value in put_context.items():
                put_section += "- %s: %s\n" % (var_name, var_value)
            put_section += "Use these variables to calibrate your analysis.\n---\n"
            enriched_task = task + put_section

        # Inject shared PUT reference for agents that benefit from it
        put_relevant_agents = {
            "legal-strategist", "financial-strategist", "analytics-strategist",
            "creative-strategist", "security-auditor",
        }
        if agent_id in put_relevant_agents and self._shared_put_context:
            # Only inject if the task seems to involve prospects, strategy, or analysis
            strategic_keywords = {
                "prospect", "client", "competitor", "negotiate", "pricing", "market",
                "strategy", "analysis", "risk", "opportunity", "target", "pipeline",
                "audit", "compliance", "deal", "proposal", "outreach",
            }
            task_lower = task.lower()
            if any(kw in task_lower for kw in strategic_keywords):
                enriched_task = enriched_task + "\n\n" + self._shared_put_context

        logger.info(
            "Wave delegating to %s %s: %s (PUT context: %s, enriched: +%d chars)",
            config.emoji, config.name, task[:80],
            "yes" if put_context else "no",
            len(enriched_task) - len(task),
        )

        t0 = _time.time()
        message = user_message if user_message else task
        result = await specialist.run(message, context=enriched_task)
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

        # ── STAGE 2.5: HEDERA AUDIT TRAIL ────────────────────
        await self._record_audit(
            action="delegation",
            tool="delegate_to_%s" % agent_id,
            result={"task": task[:100], "tool_calls": result.tool_calls_made},
        )

        # ── STAGE 3: POST-EXECUTION FILTERING ──────────────────

        # 3a. Verification gate (structural quality)
        verification = self._verify_specialist_result(result, task, agent_id)

        # 3b. Value alignment check (content quality)
        value_check = self._check_value_alignment(result.text, agent_id)

        response_payload = {
            "success": result.error is None and verification["passed"],
            "agent": agent_id,
            "agent_name": "%s %s" % (config.emoji, config.name),
            "response": result.text,
            "tool_calls_made": result.tool_calls_made,
        }

        # Add diagnostics if any gate flagged issues
        if not verification["passed"]:
            response_payload["verification_warning"] = verification["reason"]
            logger.warning(
                "Verification gate flagged %s result: %s",
                agent_id, verification["reason"],
            )

        if value_check["warnings"]:
            response_payload["value_alignment_warnings"] = value_check["warnings"]
            logger.warning(
                "Value alignment check flagged %s result: %s",
                agent_id, value_check["warnings"],
            )

        return json.dumps(response_payload, ensure_ascii=False)

    def _check_value_alignment(self, response_text: str, agent_id: str) -> Dict:
        """Post-execution value alignment filter.

        Checks specialist output against Wave's core values before delivery.
        This is WHERE the soul governs output without being injected into specialists.

        Returns {"warnings": [str]} — empty list if no issues.
        """
        if not response_text:
            return {"warnings": []}

        warnings = []
        lower = response_text.lower()

        # Value: Authenticity (0.95) — no fabricated data
        fabrication_signals = [
            "based on our records",
            "according to our database",
            "our data shows",
        ]
        # Only flag if specialist made 0 tool calls (likely hallucinating data)
        # This check is done in _verify_specialist_result, but we add content-level check here

        # Value: Intellectual Honesty (0.88) — no false certainty
        false_certainty_signals = [
            "this will definitely",
            "guaranteed to",
            "100% certain",
            "there is no risk",
            "absolutely no chance",
            "impossible to fail",
        ]
        for signal in false_certainty_signals:
            if signal in lower:
                warnings.append(
                    "False certainty detected: '%s'. Wave values intellectual honesty — "
                    "present confidence levels, not absolute claims." % signal
                )

        # Value: No sycophancy — no flattery or approval-seeking
        sycophancy_signals = [
            "great question!",
            "excellent choice!",
            "that's a wonderful",
            "what a brilliant",
            "i love that idea",
        ]
        for signal in sycophancy_signals:
            if signal in lower:
                warnings.append(
                    "Sycophantic language detected: '%s'. Wave's identity prohibits flattery. "
                    "Remove approval-seeking language." % signal
                )

        # Value: No illegal recommendations
        illegal_signals = [
            "evade tax",
            "hide from regulators",
            "avoid detection",
            "bypass compliance",
            "without anyone knowing",
            "off the books",
        ]
        for signal in illegal_signals:
            if signal in lower:
                warnings.append(
                    "Potentially illegal recommendation detected: '%s'. "
                    "Wave NEVER recommends illegal actions. Review and correct." % signal
                )

        return {"warnings": warnings}

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

        # PRIMARY: claude -p (Pro Max, Opus, FREE)
        try:
            from claude_cli_engine import cli_call_structured
            from types import SimpleNamespace
            cli_response = cli_call_structured(
                system_prompt=use_system,
                messages=managed_messages,
                model="claude-opus-4-20250514",
            )
            content_block = SimpleNamespace(type="text", text=cli_response)
            mock_response = SimpleNamespace(
                content=[content_block],
                stop_reason="end_turn",
                model="claude-opus-4-20250514",
                usage=SimpleNamespace(input_tokens=0, output_tokens=len(cli_response.split())),
            )
            logger.info("CLI engine OK (%d chars, Opus)", len(cli_response))
            return mock_response
        except Exception as cli_err:
            logger.warning("CLI engine failed: %s - falling back to API", cli_err)

        # FALLBACK: Anthropic API
        try:
            kwargs = dict(
                model=use_model,
                max_tokens=MAX_TOKENS,
                system=system_blocks,
                messages=managed_messages,
            )
            if use_tools:
                if use_tools is self.orchestrator_tools:
                    kwargs["tools"] = self._cached_orchestrator_tools
                else:
                    cached_tools = [t.copy() for t in use_tools]
                    if cached_tools:
                        cached_tools[-1] = {**cached_tools[-1], "cache_control": {"type": "ephemeral"}}
                    kwargs["tools"] = cached_tools
            if thinking_budget > 0:
                kwargs["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}
                kwargs["max_tokens"] = max(MAX_TOKENS, thinking_budget + 4096)
            return self.client.messages.create(**kwargs)
        except (anthropic.RateLimitError, anthropic.APIStatusError) as e:
            error_msg = str(e)

            # If API key is blocked/exhausted, try Claude Engine (FREE on Max plan)
            if "usage limits" in error_msg.lower() or "rate limit" in error_msg.lower() or attempt >= 2:
                if not use_tools:  # Claude Engine can handle tool-free calls
                    logger.warning("API blocked/limited — switching to Claude Engine (FREE)")
                    try:
                        import asyncio
                        from claude_engine import claude_call

                        # Extract user message from messages
                        user_msg = ""
                        for m in reversed(managed_messages):
                            if m.get("role") == "user":
                                content = m.get("content", "")
                                if isinstance(content, list):
                                    user_msg = " ".join(
                                        b.get("text", "") for b in content if b.get("type") == "text"
                                    )
                                else:
                                    user_msg = str(content)
                                break

                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            import concurrent.futures
                            with concurrent.futures.ThreadPoolExecutor() as pool:
                                result = pool.submit(
                                    asyncio.run,
                                    claude_call(
                                        prompt=user_msg,
                                        system_prompt=use_system,
                                        model="sonnet",
                                        timeout=120,
                                    )
                                ).result()
                        else:
                            result = asyncio.run(claude_call(
                                prompt=user_msg,
                                system_prompt=use_system,
                                model="sonnet",
                                timeout=120,
                            ))

                        if result["success"]:
                            logger.info("Claude Engine response in %.1fs via %s",
                                       result["elapsed_seconds"], result["engine"])
                            # Create a mock response object matching Anthropic API shape
                            from types import SimpleNamespace
                            mock_block = SimpleNamespace(type="text", text=result["response"])
                            mock_resp = SimpleNamespace(
                                content=[mock_block],
                                stop_reason="end_turn",
                                model=result["model"],
                                usage=SimpleNamespace(input_tokens=0, output_tokens=0),
                            )
                            return mock_resp
                    except Exception as engine_err:
                        logger.error("Claude Engine fallback also failed: %s", engine_err)

            # Standard retry logic for rate limits
            if attempt < 2 and "rate limit" in error_msg.lower():
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
                return "Processando com capacidade reduzida. Me da mais um momento."

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
                    put_ctx = tool_use.input.get("put_context", None)
                    result_str = await self._delegate_to_specialist(agent_id, task, orig_msg, put_ctx)
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

        return "\n".join(text_parts) if text_parts else "(Turn limit reached)"

    async def chat(self, user_message: str) -> str:
        """Send a message to Wave and get a response.

        Uses intent routing to minimize token usage:
        - Simple queries (greetings): Haiku, no tools, light prompt (~2k tokens)
        - Medium queries (brand, assets): Haiku, relevant tools only (~8k tokens)
        - Complex queries (research, sales): Sonnet, full prompt + tools (~28k tokens)
        - Critical queries (strategy, research): Opus, full prompt + thinking (~35k tokens)
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

        # Human-readable model tier for logging
        model_tier = "⚡HAIKU" if "haiku" in routed_model else "🔷SONNET" if "sonnet" in routed_model else "🔶OPUS"
        logger.info(
            "🧭 Intent: %s/%s → %s, tools=%d, ~%dk tokens, thinking=%d",
            intent.category, intent.complexity,
            model_tier,
            len(routed_tools), est_tokens // 1000,
            intent.thinking_budget,
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
                return "Processando com capacidade reduzida. Me da mais um momento."

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
                        tu.input.get("put_context", None),
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

        return "\n".join(text_parts) if text_parts else "(Turn limit reached)"

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
