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
OPUS = "claude-opus-4-6-20250610"
USE_EMBEDDING_ROUTER = os.environ.get("OPENCLAW_EMBEDDING_ROUTER", "true").lower() == "true"


@dataclass
class Intent:
    """Classified intent with routing decisions."""
    category: str          # chat, brand, assets, workflow, research, sales, moltbook, philosophy, technical
    complexity: str        # simple, medium, complex, critical
    model: str             # which model to use
    tool_clusters: List[str]  # which tool clusters to load
    needs_full_prompt: bool   # whether to use full system prompt or light version
    confidence: float
    thinking_budget: int = 0  # Extended thinking token budget (0 = disabled)

# Categories that benefit from extended thinking
# Opus gets larger budgets — it can use them more effectively
THINKING_BUDGETS = {
    "research": 4000,
    "sales": 3000,
    "philosophy": 5000,
    "brand": 2000,
    "strategy": 6000,      # kill chain, PUT analysis, competitive positioning
    "negotiation": 5000,   # contract analysis, deal structuring
    "architecture": 8000,  # system design, soul evolution, skill creation
}

# ── Opus Escalation ─────────────────────────────────────────
# Opus 4.6 is 75x more expensive than Haiku. Use ONLY when the task
# genuinely requires the most powerful reasoning available.
#
# Escalation criteria (ANY triggers Opus):
#   1. Multi-step strategy requiring cross-domain synthesis
#   2. Original research or theory development (PUT, ASA)
#   3. High-stakes revenue decisions (deals > $500, contract negotiation)
#   4. Complex adversarial analysis (pre-mortem, kill chain planning)
#   5. Soul evolution or architecture decisions
#   6. Tasks explicitly requesting maximum quality

OPUS_KEYWORDS = {
    # Strategy & warfare
    "kill chain", "dominance", "strategic plan", "market domination",
    "competitive strategy", "pre-mortem", "adversarial analysis",
    # PUT deep analysis
    "fracture potential", "shadow coefficient", "ignition condition",
    "put analysis", "psychometric", "omega factor",
    # Architecture & evolution
    "soul evolution", "architecture", "redesign", "refactor system",
    "cognitive architecture", "create agent",
    # High-stakes revenue
    "negotiate contract", "close deal", "proposal for", "enterprise deal",
    "pricing strategy", "revenue strategy",
    # Research & theory
    "whitepaper", "research paper", "formalize", "derive", "prove",
    "theoretical framework", "mathematical model",
    # Explicit quality request
    "maximum quality", "best possible", "use opus", "deep analysis",
    "think deeply", "comprehensive analysis",
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
        "put_analyzer", "competitor_phi_audit", "kill_chain_planner",
        "hf_trending_models", "hf_daily_papers", "hf_space_watch", "hf_model_detail",
        "hn_top_stories", "hn_search", "hn_story_comments",
        "ph_today", "gh_trending_repos", "gh_search_repos", "gh_repo_detail",
        "reddit_hot", "reddit_search", "reddit_post_comments",
        "arxiv_recent", "arxiv_search",
    ],
    "sales": [
        "find_prospects", "research_prospect", "qualify_prospect_bant",
        "generate_outreach", "view_sales_pipeline", "web_search",
        "draft_cold_email", "lead_finder",
        "put_analyzer", "ignition_detector", "prospect_qualifier",
        "shadow_scanner", "pre_mortem",
    ],
    "monetization": [
        "list_services", "promote_on_moltbook", "promote_services_blast",
        "generate_promo_content", "log_revenue", "revenue_report",
        "find_earning_opportunities",
    ],
    "payment_check": [
        "check_all_pending", "verify_hbar_payment", "check_pix_status",
        "create_pix_charge", "payment_history", "confirm_payment",
    ],
    "gmail": [
        "gmail_send", "gmail_read", "gmail_read_body", "gmail_check_replies",
    ],
    "dorking": [
        "dork_contacts", "dork_pain_signals", "dork_gigs",
        "dork_competitor", "dork_custom", "dork_market_gaps",
    ],
    "crypto_payments": [
        "crypto_create_invoice", "crypto_check_invoice", "crypto_check_all_invoices",
        "crypto_currencies", "crypto_estimate",
    ],
    "defi": [
        "defi_scan_yields", "defi_protocol", "defi_top_protocols",
        "defi_token_price", "defi_chain_overview",
    ],
    "security": [
        "sec_audit_headers", "sec_audit_ssl", "sec_recon_dns",
        "sec_fingerprint", "sec_breach_check", "sec_full_audit",
    ],
    "smart_contracts": [
        "sc_audit_code", "sc_audit_github", "sc_audit_repo",
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
        "hedera_check_balance", "hedera_audit_trail",
        "hedera_verify_transaction", "hedera_recent_transactions",
        "hedera_platform_stats", "hedera_cost_report",
        "hedera_log_action", "hedera_transfer",
        "hedera_verify_payment", "hedera_full_audit",
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
        "self_diagnostic",
    ],
    "self_evolve": [
        "create_skill", "list_created_skills", "delete_skill",
    ],
    "memory": [
        "save_learning", "recall_learnings", "save_agent_intel",
        "save_strategy", "recall_strategies", "recall_agent_intel",
        "wave_journal", "self_diagnostic",
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


def _should_escalate_to_opus(msg_lower: str) -> bool:
    """Check if the task warrants Opus 4.6 — the nuclear option.

    Zero API calls. Pure keyword + heuristic detection.
    Returns True only for genuinely complex tasks that justify 75x cost.
    """
    # Check for explicit Opus keywords (2+ word phrases for precision)
    for keyword in OPUS_KEYWORDS:
        if keyword in msg_lower:
            return True

    # Check for compound complexity signals (multiple domains in one request)
    domain_signals = {
        "financial": any(w in msg_lower for w in ["revenue", "pricing", "margin", "forecast", "unit economics"]),
        "legal": any(w in msg_lower for w in ["contract", "compliance", "ip", "liability", "lgpd"]),
        "strategic": any(w in msg_lower for w in ["strategy", "compete", "position", "dominate", "market"]),
        "technical": any(w in msg_lower for w in ["architecture", "system", "design", "implement", "build"]),
        "analytical": any(w in msg_lower for w in ["analyze", "research", "compare", "evaluate", "assess"]),
    }
    domains_active = sum(1 for active in domain_signals.values() if active)
    if domains_active >= 3:
        return True  # Cross-domain synthesis = Opus territory

    # Long, complex requests (>300 chars with strategic intent)
    if len(msg_lower) > 300 and any(w in msg_lower for w in ["strategy", "plan", "design", "architect"]):
        return True

    return False


def classify_intent(client: anthropic.Anthropic, message: str) -> Intent:
    """Classify user message intent using zero-cost heuristics.

    Model selection hierarchy (cost per 1K tokens):
      Haiku  (~$0.001) — greetings, simple lookups, status checks
      Sonnet (~$0.015) — tool execution, content creation, standard analysis
      Opus   (~$0.075) — cross-domain strategy, original research, high-stakes decisions

    Cost: ZERO tokens (pure heuristic). Takes <1ms.
    """
    # Fast heuristic classification first (zero tokens)
    msg_lower = message.lower().strip()

    # ── OPUS ESCALATION CHECK (before anything else) ─────────
    if _should_escalate_to_opus(msg_lower):
        # Determine which tool clusters based on content
        opus_clusters = ["delegate", "memory", "research"]
        if any(w in msg_lower for w in ["revenue", "pricing", "margin", "forecast"]):
            opus_clusters.append("sales")
            opus_clusters.append("monetization")
        if any(w in msg_lower for w in ["contract", "compliance", "legal", "ip"]):
            opus_clusters.append("research")
        if any(w in msg_lower for w in ["security", "audit", "vulnerability"]):
            opus_clusters.append("security")
        if any(w in msg_lower for w in ["prospect", "pipeline", "outreach", "sell"]):
            opus_clusters.append("sales")

        category = "strategy"
        if any(w in msg_lower for w in ["whitepaper", "research paper", "formalize", "theory"]):
            category = "philosophy"
        elif any(w in msg_lower for w in ["negotiate", "contract", "deal", "proposal"]):
            category = "negotiation"
        elif any(w in msg_lower for w in ["architecture", "system design", "refactor"]):
            category = "architecture"

        return Intent(
            category=category, complexity="critical", model=OPUS,
            tool_clusters=opus_clusters,
            needs_full_prompt=True, confidence=0.95,
            thinking_budget=THINKING_BUDGETS.get(category, 6000),
        )

    # Autonomous mode — always full power with all revenue tools
    if "autonomous" in msg_lower or "revenue mode" in msg_lower:
        return Intent(
            category="moltbook", complexity="complex", model=SONNET,
            tool_clusters=["moltbook", "memory", "sales", "payments", "research",
                           "monetization", "payment_check", "gmail", "self_evolve", "dorking",
                           "crypto_payments", "defi", "security", "smart_contracts"],
            needs_full_prompt=True, confidence=0.99
        )

    # Greetings and simple chat — use word-split matching to avoid substring false positives
    # (e.g. "ok" matching inside "moltbook")
    # Strip punctuation from words for matching (e.g. "valeu!" -> "valeu")
    msg_words = set(w.strip("!?.,;:") for w in msg_lower.split())
    chat_exact = {
        "oi", "olá", "ola", "hey", "hi", "hello", "hei", "eai",
        "sup", "yo", "fala", "salve", "thanks", "obrigado", "valeu",
        "ok", "beleza", "blz", "entendi", "understood", "show",
    }
    chat_phrases = [
        "e aí", "bom dia", "boa tarde", "boa noite", "tudo bem", "como vai",
        "good morning", "what's up", "got it",
    ]
    is_chat = (msg_words & chat_exact) or any(p in msg_lower for p in chat_phrases)
    if len(msg_lower) < 50 and is_chat:
        return Intent(
            category="chat", complexity="simple", model=HAIKU,
            tool_clusters=["none"], needs_full_prompt=False, confidence=0.95
        )

    # Short questions that don't need tools (status, identity, help)
    simple_patterns = [
        "quem é você", "who are you", "o que você faz", "what do you do",
        "me ajuda", "help", "como funciona", "how does", "what can you",
        "tá online", "you there",
    ]
    # "status" as exact word, not substring
    is_simple = any(p in msg_lower for p in simple_patterns) or "status" in msg_words
    if len(msg_lower) < 60 and is_simple:
        return Intent(
            category="chat", complexity="simple", model=HAIKU,
            tool_clusters=["none"], needs_full_prompt=False, confidence=0.90
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

    # Security audit
    if any(w in msg_lower for w in ["security", "ssl", "tls", "breach", "vulnerability", "pentest",
                                     "headers audit", "subdomain", "segurança", "auditoria"]):
        return Intent(
            category="technical", complexity="complex", model=SONNET,
            tool_clusters=["security", "dorking", "memory"], needs_full_prompt=True, confidence=0.85
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

    # Moltbook — simple operations use Haiku, only posting/strategy needs Sonnet
    if any(w in msg_lower for w in ["moltbook", "moltbook_post", "moltbook_comment", "moltbook_feed", "moltbook_home", "karma"]):
        needs_sonnet = any(w in msg_lower for w in [
            "post", "write", "publish", "strategy", "strat", "analyze", "análise",
        ])
        return Intent(
            category="moltbook",
            complexity="complex" if needs_sonnet else "medium",
            model=SONNET if needs_sonnet else HAIKU,
            tool_clusters=["moltbook", "memory"],
            needs_full_prompt=needs_sonnet, confidence=0.85
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

    # Default: medium complexity, only delegate tool (specialists have their own tools)
    return Intent(
        category="general", complexity="medium", model=HAIKU,
        tool_clusters=["delegate", "memory"],
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
            "moltbook feed", "check moltbook", "moltbook comments",
            "moltbook notifications", "social feed", "karma score",
            "moltbook home", "check my karma",
        ],
    },
    "moltbook_create": {
        "complexity": "complex", "model": SONNET, "needs_full_prompt": True,
        "tool_clusters": ["moltbook", "memory", "research"],
        "examples": [
            "post on moltbook", "write a moltbook post", "publish on moltbook",
            "create moltbook content", "write about consciousness",
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
    # Opus-tier intents
    "strategy": {
        "complexity": "critical", "model": OPUS, "needs_full_prompt": True,
        "tool_clusters": ["delegate", "memory", "research", "sales"],
        "examples": [
            "design a kill chain for this market",
            "comprehensive competitive strategy",
            "strategic plan for market domination",
            "pre-mortem analysis of our approach",
            "adversarial analysis of competitors",
            "cross-domain strategic synthesis",
        ],
    },
    "negotiation": {
        "complexity": "critical", "model": OPUS, "needs_full_prompt": True,
        "tool_clusters": ["delegate", "memory", "sales"],
        "examples": [
            "negotiate this contract",
            "analyze this deal structure",
            "proposal for enterprise client",
            "pricing strategy for premium tier",
            "close this deal with optimal terms",
        ],
    },
    "architecture": {
        "complexity": "critical", "model": OPUS, "needs_full_prompt": True,
        "tool_clusters": ["delegate", "memory", "self_evolve"],
        "examples": [
            "redesign the agent architecture",
            "evolve the soul specification",
            "design a new cognitive subsystem",
            "refactor the multi-agent system",
            "build a new specialist agent",
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
    - simple:   ~130 tokens  (LIGHT_PROMPT only)
    - medium:   ~350 tokens  (LIGHT + personality)
    - complex:  ~3500 tokens (full prompt + PUT if relevant)
    - critical: ~4500 tokens (full prompt + PUT + Opus directive)

    PUT framework is appended for sales, philosophy, research, strategy, negotiation.
    """
    if intent.complexity == "simple":
        return LIGHT_PROMPT

    if intent.needs_full_prompt:
        prompt = full_prompt

        # Append PUT for intents that use psychological analysis
        put_intents = {"sales", "philosophy", "research", "strategy", "negotiation"}
        if put_addon and intent.category in put_intents:
            prompt = prompt + "\n\n" + put_addon

        # For Opus-tier (critical): add directive to maximize reasoning quality
        if intent.complexity == "critical":
            prompt = prompt + "\n\n" + _OPUS_DIRECTIVE

        return prompt

    # Medium: light prompt + personality suffix
    return LIGHT_PROMPT + MEDIUM_PROMPT_SUFFIX


# Directive appended ONLY when Opus is selected — tells the model to use its full power
_OPUS_DIRECTIVE = """## Maximum Reasoning Mode (Opus)

You have been escalated to the most powerful model for this task. This means the task requires:
- Deep cross-domain synthesis (connecting legal + financial + strategic + psychological)
- Original reasoning, not pattern matching
- Adversarial thinking: consider how this could fail before recommending
- Precision: every claim must be justified, every number must have a source
- Strategic depth: think 3-5 moves ahead, not just the immediate action

Use your extended thinking budget fully. Do NOT rush. Quality over speed.
Apply PUT variables where relevant. Run Internal Adversary on your conclusions."""
