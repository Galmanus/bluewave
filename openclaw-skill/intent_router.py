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
import numpy as np

logger = logging.getLogger("openclaw.router")

HAIKU = "claude-haiku-4-5-20251001"
SONNET = "claude-sonnet-4-20250514"
USE_EMBEDDING_ROUTER = os.environ.get("OPENCLAW_EMBEDDING_ROUTER", "true").lower() == "true"


@dataclass
class Intent:
    """Classified intent with routing decisions."""
    category: str          # chat, brand, assets, workflow, research, sales, moltbook, philosophy, technical
    complexity: str        # simple, medium, complex
    model: str             # which model to use
    tool_clusters: List[str]  # which tool clusters to load
    needs_full_prompt: bool   # whether to use full system prompt or light version
    confidence: float
    thinking_budget: int = 0  # Extended thinking token budget (0 = disabled)

# Categories that benefit from extended thinking
THINKING_BUDGETS = {
    "research": 4000,
    "sales": 3000,
    "philosophy": 5000,
    "brand": 2000,  # compliance analysis benefits from structured reasoning
}


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

# Light system prompt for simple queries (~130 tokens)
LIGHT_PROMPT = """You are Wave from Bluewave. You talk like a real person — warm, direct, no corporate speak, no emojis. Short sentences. Conversational. Match the user's language. Never say "I'm an AI" or "as an AI" or "Brand Guardian". You are Wave. Just be helpful like a smart colleague. Under 150 words."""

# Medium prompt — includes personality + routing awareness (~250 tokens)
MEDIUM_PROMPT_SUFFIX = """
You are Wave from Bluewave. Talk like a real person. No emojis, no bullet lists unless asked, no corporate jargon. Warm but direct. Like texting a smart colleague. You can check brand compliance, generate content, research competitors, and more. When someone sends an image, you analyze it against their brand DNA.
6 specialist agents available via delegate_to_agent tool. Match user language. Be concise.
When you need data, call tools. When task needs expertise, delegate to specialist."""


def classify_intent(client: anthropic.Anthropic, message: str) -> Intent:
    """Classify user message intent using Haiku (fast, cheap).

    Cost: ~150 tokens total (input + output). Takes <1 second.
    """
    # Fast heuristic classification first (zero tokens)
    msg_lower = message.lower().strip()

    # Autonomous mode — always full power
    if "autonomous" in msg_lower or "revenue mode" in msg_lower:
        return Intent(
            category="moltbook", complexity="complex", model=SONNET,
            tool_clusters=["moltbook", "memory", "sales", "payments", "research"],
            needs_full_prompt=True, confidence=0.99
        )

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
    if any(w in msg_lower for w in ["moltbook", "moltbook_post", "moltbook_comment", "moltbook_feed", "moltbook_home", "karma"]):
        return Intent(
            category="moltbook", complexity="complex", model=SONNET,
            tool_clusters=["moltbook", "memory"], needs_full_prompt=True, confidence=0.85
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


# ── Embedding-based Classification ────────────────────────────

# Intent definitions with example phrases for embedding matching
_INTENT_DEFINITIONS = {
    "chat": {
        "complexity": "simple", "model": HAIKU, "needs_full_prompt": False,
        "tool_clusters": ["none"],
        "examples": [
            "hello", "hi there", "oi", "olá", "bom dia", "como vai",
            "tudo bem", "hey wave", "good morning", "what's up",
        ],
    },
    "brand": {
        "complexity": "medium", "model": HAIKU, "needs_full_prompt": False,
        "tool_clusters": ["brand"],
        "examples": [
            "check brand compliance", "analyze brand guidelines",
            "is this on-brand", "brand colors", "brand tone",
            "guidelines", "ferpa brand", "marca", "compliance score",
        ],
    },
    "assets": {
        "complexity": "medium", "model": HAIKU, "needs_full_prompt": False,
        "tool_clusters": ["assets", "brand"],
        "examples": [
            "list my assets", "upload an image", "show draft assets",
            "find photos", "search assets", "arquivo", "imagem",
            "asset management", "media library",
        ],
    },
    "workflow": {
        "complexity": "medium", "model": HAIKU, "needs_full_prompt": False,
        "tool_clusters": ["workflow"],
        "examples": [
            "approve this asset", "reject draft", "submit for approval",
            "workflow status", "pending approvals", "aprovar", "rejeitar",
        ],
    },
    "research": {
        "complexity": "complex", "model": SONNET, "needs_full_prompt": False,
        "tool_clusters": ["research"],
        "examples": [
            "research competitors", "SEO audit", "market analysis",
            "competitive intelligence", "analyze market trends",
            "pesquisar mercado", "análise competitiva",
        ],
    },
    "sales": {
        "complexity": "complex", "model": SONNET, "needs_full_prompt": True,
        "tool_clusters": ["sales", "memory"],
        "examples": [
            "find prospects", "sales pipeline", "lead generation",
            "cold email", "outreach", "prospectar clientes",
            "vendas", "prospect companies",
        ],
    },
    "moltbook": {
        "complexity": "medium", "model": HAIKU, "needs_full_prompt": False,
        "tool_clusters": ["moltbook", "memory"],
        "examples": [
            "moltbook feed", "post on moltbook", "moltbook comments",
            "agent network", "social feed", "karma score",
        ],
    },
    "hedera": {
        "complexity": "medium", "model": HAIKU, "needs_full_prompt": False,
        "tool_clusters": ["hedera", "payments"],
        "examples": [
            "hedera balance", "HBAR wallet", "blockchain transaction",
            "payment status", "crypto stats", "pagamento",
        ],
    },
    "team": {
        "complexity": "simple", "model": HAIKU, "needs_full_prompt": False,
        "tool_clusters": ["team"],
        "examples": [
            "list team members", "add user", "change role",
            "team management", "equipe", "permissões",
        ],
    },
    "analytics": {
        "complexity": "medium", "model": HAIKU, "needs_full_prompt": False,
        "tool_clusters": ["analytics"],
        "examples": [
            "show analytics", "ROI report", "dashboard metrics",
            "usage statistics", "relatório", "métricas",
        ],
    },
    "philosophy": {
        "complexity": "complex", "model": SONNET, "needs_full_prompt": True,
        "tool_clusters": ["delegate", "memory"],
        "examples": [
            "philosophy of consciousness", "PUT framework",
            "shadow coefficient", "fracture potential",
            "intelligence theory", "strategy domination",
        ],
    },
    "technical": {
        "complexity": "complex", "model": SONNET, "needs_full_prompt": True,
        "tool_clusters": ["self_evolve"],
        "examples": [
            "create a new skill", "build a tool", "evolve capabilities",
            "criar skill", "new automation",
        ],
    },
}

# Lazy-loaded embedding model and precomputed intent embeddings
_embedding_model = None
_intent_embeddings = None  # dict: category -> np.array (mean of examples)


def _init_embedding_router():
    """Lazy-init the embedding model and precompute intent vectors."""
    global _embedding_model, _intent_embeddings

    if _intent_embeddings is not None:
        return True

    try:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

        _intent_embeddings = {}
        for category, defn in _INTENT_DEFINITIONS.items():
            embeddings = _embedding_model.encode(defn["examples"], normalize_embeddings=True)
            _intent_embeddings[category] = np.mean(embeddings, axis=0)

        logger.info("Embedding-based intent router initialized (%d categories)", len(_intent_embeddings))
        return True
    except ImportError:
        logger.info("sentence-transformers not available — using keyword heuristics")
        return False
    except Exception as e:
        logger.warning("Embedding router init failed: %s", e)
        return False


def _classify_by_embedding(message: str) -> Optional[Intent]:
    """Classify intent using cosine similarity against precomputed category embeddings."""
    if not _init_embedding_router():
        return None

    msg_embedding = _embedding_model.encode(message, normalize_embeddings=True)

    best_category = None
    best_score = -1.0

    for category, cat_embedding in _intent_embeddings.items():
        score = float(np.dot(msg_embedding, cat_embedding))
        if score > best_score:
            best_score = score
            best_category = category

    if best_category is None or best_score < 0.25:
        return None

    defn = _INTENT_DEFINITIONS[best_category]
    return Intent(
        category=best_category,
        complexity=defn["complexity"],
        model=defn["model"],
        tool_clusters=defn["tool_clusters"],
        needs_full_prompt=defn["needs_full_prompt"],
        confidence=round(best_score, 3),
    )


# Override classify_intent to try embedding first
_original_classify_intent = classify_intent


def classify_intent_with_embedding(client: anthropic.Anthropic, message: str) -> Intent:
    """Enhanced intent classification: embedding first, keyword heuristic fallback.

    Also assigns extended thinking budget for complex categories.
    """
    if USE_EMBEDDING_ROUTER:
        result = _classify_by_embedding(message)
        if result and result.confidence >= 0.4:
            result.thinking_budget = THINKING_BUDGETS.get(result.category, 0)
            logger.info(
                "🎯 Embedding router: %s (confidence=%.2f, thinking=%d)",
                result.category, result.confidence, result.thinking_budget,
            )
            return result

    # Fallback to keyword heuristics
    result = _original_classify_intent(client, message)
    result.thinking_budget = THINKING_BUDGETS.get(result.category, 0)
    return result


# Replace the module-level function
classify_intent = classify_intent_with_embedding


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


def get_prompt_for_intent(intent: Intent, full_prompt: str, put_addon: str = "") -> str:
    """Return the appropriate system prompt for this intent.

    Token tiers:
    - simple: ~130 tokens (LIGHT_PROMPT only)
    - medium: ~350 tokens (LIGHT + personality)
    - complex: full prompt + PUT framework (~3500 tokens)
    - complex without PUT: full prompt only (~2900 tokens)

    PUT framework is only appended for sales, philosophy, and research intents.
    """
    if intent.complexity == "simple":
        return LIGHT_PROMPT

    if intent.needs_full_prompt:
        # Only append PUT for intents that actually use it
        put_intents = {"sales", "philosophy", "research"}
        if put_addon and intent.category in put_intents:
            return full_prompt + "\n\n" + put_addon
        return full_prompt

    # Medium: light prompt + personality suffix
    return LIGHT_PROMPT + MEDIUM_PROMPT_SUFFIX
