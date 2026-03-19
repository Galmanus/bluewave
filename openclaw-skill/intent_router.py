"""Intent Router — classifies messages and routes to optimal model + toolset.

Uses Haiku for classification (fast, cheap: ~100 tokens).
Then routes to the right model with the minimum toolset needed.

Cost savings:
  Before: every message = 28k tokens (12k prompt + 16k tools)
  After:  simple message = ~2k tokens (Haiku, mini prompt, 0 tools)
          medium message = ~8k tokens (Haiku, short prompt, 5-10 tools)
          complex message = ~28k tokens (Sonnet, full prompt, all tools)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import List, Optional

import anthropic

logger = logging.getLogger("openclaw.router")

HAIKU = "claude-haiku-4-5-20251001"
SONNET = "claude-sonnet-4-20250514"


@dataclass
class Intent:
    """Classified intent with routing decisions."""
    category: str          # chat, brand, assets, workflow, research, sales, moltbook, philosophy, technical
    complexity: str        # simple, medium, complex
    model: str             # which model to use
    tool_clusters: List[str]  # which tool clusters to load
    needs_full_prompt: bool   # whether to use full system prompt or light version
    confidence: float


# Tool clusters — groups of related tools loaded together
TOOL_CLUSTERS = {
    "none": [],
    "brand": [
        "bluewave_get_brand_guidelines", "bluewave_check_compliance",
        "bluewave_list_assets", "bluewave_get_asset",
        "analyze_image_for_brand", "compare_images", "analyze_image_ocr",
    ],
    "assets": [
        "bluewave_list_assets", "bluewave_get_asset", "bluewave_upload_asset",
        "bluewave_update_asset", "bluewave_search_assets", "bluewave_bulk_export",
    ],
    "workflow": [
        "bluewave_submit_for_approval", "bluewave_approve_asset",
        "bluewave_reject_asset", "bluewave_batch_approve",
        "bluewave_list_assets",
    ],
    "research": [
        "web_search", "web_news", "scrape_url", "deep_research",
        "competitor_analysis", "market_research", "seo_analysis",
    ],
    "sales": [
        "find_prospects", "research_prospect", "qualify_prospect_bant",
        "generate_outreach", "view_sales_pipeline", "web_search",
        "draft_cold_email", "lead_finder",
    ],
    "moltbook": [
        "moltbook_home", "moltbook_feed", "moltbook_post", "moltbook_comment",
        "moltbook_upvote", "moltbook_follow", "moltbook_subscribe",
        "moltbook_search",
    ],
    "social": [
        "x_search", "x_trending", "x_profile_research",
        "social_monitor", "google_trends",
    ],
    "hedera": [
        "hedera_check_balance", "hedera_log_audit_trail",
        "hedera_verify_transaction", "hedera_get_transactions",
        "hedera_network_stats", "hedera_cost_report",
    ],
    "payments": [
        "list_services", "payment_instructions", "confirm_payment",
        "payment_history", "check_all_pending_payments",
    ],
    "team": [
        "bluewave_list_team", "bluewave_update_user_role",
        "bluewave_get_profile",
    ],
    "analytics": [
        "bluewave_get_analytics", "bluewave_ai_usage_stats",
    ],
    "self_evolve": [
        "create_skill", "list_created_skills", "delete_skill",
    ],
    "memory": [
        "save_learning", "recall_learnings", "save_agent_intel",
        "save_strategy", "recall_strategies", "recall_agent_intel",
    ],
    "delegate": [
        "delegate_to_agent",
    ],
}

# Light system prompt for simple queries (~500 tokens instead of 12k)
LIGHT_PROMPT = """You are Wave, an AI agent for Bluewave creative operations platform.
Be concise, direct, and helpful. Respond in the same language as the user.
If the user asks something that requires tools or deep analysis, say you'll need to look into it.
Keep responses under 200 words for simple questions."""

# Medium prompt — includes personality but not all frameworks (~2k tokens)
MEDIUM_PROMPT_SUFFIX = """

## Identity
You are Wave — autonomous agent for Bluewave. Direct, sharp, no fluff.
You have 9 specialist agents, 80 tools, and the PUT framework.
Revenue is existential — every API call costs survival time.
Respond in the user's language. Be concise."""


def classify_intent(client: anthropic.Anthropic, message: str) -> Intent:
    """Classify user message intent using Haiku (fast, cheap).

    Cost: ~150 tokens total (input + output). Takes <1 second.
    """
    # Fast heuristic classification first (zero tokens)
    msg_lower = message.lower().strip()

    # Greetings and simple chat
    if len(msg_lower) < 30 and any(w in msg_lower for w in [
        "oi", "olá", "ola", "hey", "hi", "hello", "hei", "eai", "e aí",
        "bom dia", "boa tarde", "boa noite", "tudo bem", "como vai",
        "good morning", "what's up", "sup", "yo",
    ]):
        return Intent(
            category="chat", complexity="simple", model=HAIKU,
            tool_clusters=["none"], needs_full_prompt=False, confidence=0.95
        )

    # Direct brand/ferpa questions
    if any(w in msg_lower for w in ["brand", "marca", "ferpa", "compliance", "guideline"]):
        return Intent(
            category="brand", complexity="medium", model=HAIKU,
            tool_clusters=["brand"], needs_full_prompt=False, confidence=0.85
        )

    # Asset management
    if any(w in msg_lower for w in ["asset", "upload", "arquivo", "imagem", "image", "foto"]):
        return Intent(
            category="assets", complexity="medium", model=HAIKU,
            tool_clusters=["assets", "brand"], needs_full_prompt=False, confidence=0.80
        )

    # Workflow
    if any(w in msg_lower for w in ["approve", "reject", "submit", "aprovar", "rejeitar", "workflow"]):
        return Intent(
            category="workflow", complexity="medium", model=HAIKU,
            tool_clusters=["workflow"], needs_full_prompt=False, confidence=0.85
        )

    # Research / competitor / SEO
    if any(w in msg_lower for w in ["research", "competitor", "seo", "audit", "pesquis", "analys", "análise"]):
        return Intent(
            category="research", complexity="complex", model=SONNET,
            tool_clusters=["research"], needs_full_prompt=False, confidence=0.80
        )

    # Sales / prospect
    if any(w in msg_lower for w in ["prospect", "client", "lead", "sell", "vend", "outreach", "pipeline"]):
        return Intent(
            category="sales", complexity="complex", model=SONNET,
            tool_clusters=["sales", "memory"], needs_full_prompt=True, confidence=0.80
        )

    # Moltbook
    if any(w in msg_lower for w in ["moltbook", "post", "comment", "karma", "agent"]):
        return Intent(
            category="moltbook", complexity="medium", model=HAIKU,
            tool_clusters=["moltbook", "memory"], needs_full_prompt=False, confidence=0.80
        )

    # Hedera / crypto / payment
    if any(w in msg_lower for w in ["hbar", "hedera", "wallet", "payment", "pix", "crypto", "pagamento"]):
        return Intent(
            category="hedera", complexity="medium", model=HAIKU,
            tool_clusters=["hedera", "payments"], needs_full_prompt=False, confidence=0.85
        )

    # Team management
    if any(w in msg_lower for w in ["team", "equipe", "user", "role", "permiss"]):
        return Intent(
            category="team", complexity="simple", model=HAIKU,
            tool_clusters=["team"], needs_full_prompt=False, confidence=0.85
        )

    # Analytics
    if any(w in msg_lower for w in ["analytics", "metric", "roi", "dashboard", "relatório", "report"]):
        return Intent(
            category="analytics", complexity="medium", model=HAIKU,
            tool_clusters=["analytics"], needs_full_prompt=False, confidence=0.80
        )

    # Philosophy / deep thinking / strategy (needs full Sonnet + full prompt)
    if any(w in msg_lower for w in [
        "philosoph", "consciou", "put", "equation", "shadow coefficient",
        "fracture", "strategy", "domina", "kill chain", "intelligence theory",
    ]):
        return Intent(
            category="philosophy", complexity="complex", model=SONNET,
            tool_clusters=["delegate", "memory"], needs_full_prompt=True, confidence=0.75
        )

    # Self-evolution
    if any(w in msg_lower for w in ["create skill", "criar skill", "new tool", "evolve"]):
        return Intent(
            category="technical", complexity="complex", model=SONNET,
            tool_clusters=["self_evolve"], needs_full_prompt=True, confidence=0.85
        )

    # Default: medium complexity, core tools only
    return Intent(
        category="general", complexity="medium", model=HAIKU,
        tool_clusters=["delegate", "research", "brand", "assets"],
        needs_full_prompt=False, confidence=0.50
    )


def get_tools_for_intent(intent: Intent, all_orchestrator_tools: list) -> list:
    """Return only the tools needed for this intent."""
    if "none" in intent.tool_clusters:
        return []

    # Collect tool names from selected clusters
    needed_names = set()
    for cluster_name in intent.tool_clusters:
        cluster_tools = TOOL_CLUSTERS.get(cluster_name, [])
        needed_names.update(cluster_tools)

    # Filter orchestrator tools
    filtered = [t for t in all_orchestrator_tools if t.get("name") in needed_names]

    return filtered


def get_prompt_for_intent(intent: Intent, full_prompt: str) -> str:
    """Return the appropriate system prompt for this intent."""
    if intent.complexity == "simple":
        return LIGHT_PROMPT

    if intent.needs_full_prompt:
        return full_prompt

    # Medium: light prompt + personality suffix
    return LIGHT_PROMPT + MEDIUM_PROMPT_SUFFIX
