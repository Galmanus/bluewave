"""Intent Router — classifies messages and routes to optimal Gemini model + toolset.

Uses Flash-Lite for classification (fast, cheap).
Then routes to the right model with the minimum toolset needed.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import List, Optional
import numpy as np

logger = logging.getLogger("openclaw.router")

# Gemini Model Constants
HAIKU = "gemini-2.0-flash-lite-preview-02-05"
SONNET = "gemini-2.0-flash"
OPUS = "gemini-2.0-pro-exp-02-05"

USE_EMBEDDING_ROUTER = os.environ.get("OPENCLAW_EMBEDDING_ROUTER", "true").lower() == "true"


@dataclass
class Intent:
    """Classified intent with routing decisions."""
    category: str
    complexity: str
    model: str
    tool_clusters: List[str]
    needs_full_prompt: bool
    confidence: float
    thinking_budget: int = 0

# (Tool clusters remain the same as they are logic-based)
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
    "agent_factory": [
        "create_agent_soul", "deploy_agent", "list_agents",
        "send_task_to_agent", "recall_agent",
    ],
    "agent_commerce": [
        "list_agent_services", "process_agent_request",
        "verify_agent_payment", "agent_service_history",
        "publish_service_catalog",
    ],
    "midas_engineering": [
        "midas_read_file", "midas_write_file", "midas_edit_file",
        "midas_delete_file", "midas_list_files", "midas_search_code",
        "midas_commit", "midas_git_status", "midas_git_diff",
        "starknet_deploy_status", "starknet_build_contracts",
        "starknet_test_contracts", "starknet_deploy_contracts",
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

LIGHT_PROMPT = """You are Wave from Bluewave. You talk like a real person — warm, direct, no corporate speak, no emojis. Short sentences. Conversational. Match the user's language. You are Wave. Under 150 words."""

def classify_intent(message: str) -> Intent:
    """Classify user message intent using heuristics."""
    msg_lower = message.lower().strip()
    
    # Simple logic to route
    if any(w in msg_lower for w in ["strategy", "kill chain", "put", "dominate"]):
        return Intent("strategy", "critical", OPUS, ["delegate", "memory", "research"], True, 0.9)
    
    if any(w in msg_lower for w in ["prospect", "sell", "lead"]):
        return Intent("sales", "complex", SONNET, ["sales", "memory"], True, 0.85)

    return Intent("chat", "simple", HAIKU, ["none"], False, 0.95)

def get_tools_for_intent(intent: Intent, all_orchestrator_tools: list) -> list:
    if "none" in intent.tool_clusters: return []
    needed = set()
    for c in intent.tool_clusters:
        needed.update(TOOL_CLUSTERS.get(c, []))
    return [t for t in all_orchestrator_tools if t.get("name") in needed]

def get_prompt_for_intent(intent: Intent, full_prompt: str, put_addon: str = "") -> str:
    if intent.complexity == "simple": return LIGHT_PROMPT
    return full_prompt + ("\n\n" + put_addon if put_addon and intent.category in ["sales", "strategy"] else "")
