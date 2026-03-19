"""Pricing Engine — dynamic pricing based on market research and value delivered.

Wave's autonomous pricing strategist. Analyzes market rates, adjusts prices
based on demand, tracks conversion, and optimizes for maximum revenue.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from duckduckgo_search import DDGS

logger = logging.getLogger("openclaw.skills.pricing")

MEMORY_DIR = Path(__file__).parent.parent / "memory"
PRICING_FILE = MEMORY_DIR / "pricing_config.json"


def _ensure_dir():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)


# ── Default pricing tiers ─────────────────────────────────────
# Based on market research: Fiverr AI gigs ($5-50), Upwork AI agents ($25-150/hr),
# AgentOps consulting ($500-5000/project)

DEFAULT_PRICING = {
    # ── TIER 1: Quick wins (impulse buy, high volume) ──
    "caption_pack": {
        "name": "AI Caption Pack (10 images)",
        "description": "Upload 10 images, get marketing-ready captions + hashtags for each. Claude Vision analyzes the actual content.",
        "price_usd": 9,
        "price_brl": 51,
        "price_hbar": 60,
        "cost_estimate_usd": 0.50,
        "margin_percent": 94,
        "delivery": "5 minutes",
        "tier": "quick",
        "target": "social media managers, content creators",
    },
    "seo_audit": {
        "name": "SEO Site Audit",
        "description": "Full SEO analysis — title, meta, headings, content structure, images, links. Score 0-100 with priority fixes.",
        "price_usd": 15,
        "price_hbar": 100,
        "cost_estimate_usd": 0.30,
        "margin_percent": 98,
        "delivery": "3 minutes",
        "tier": "quick",
        "target": "founders, marketers, agencies",
    },
    "brand_audit": {
        "name": "AI Brand Compliance Audit",
        "description": "Send any image — Claude Vision scores brand compliance 0-100. Colors, typography, composition, mood. Specific fixes included.",
        "price_usd": 12,
        "price_hbar": 80,
        "cost_estimate_usd": 0.40,
        "margin_percent": 97,
        "delivery": "2 minutes",
        "tier": "quick",
        "target": "brand managers, designers, agencies",
    },

    # ── TIER 2: Professional services (considered buy, good margin) ──
    "competitor_report": {
        "name": "Competitor Deep Dive Report",
        "description": "Full competitive analysis — pricing, features, reviews, funding, team, tech stack, content strategy. 7-angle research with news monitoring.",
        "price_usd": 35,
        "price_hbar": 230,
        "cost_estimate_usd": 1.50,
        "margin_percent": 96,
        "delivery": "10 minutes",
        "tier": "professional",
        "target": "founders, product managers, investors",
    },
    "content_strategy": {
        "name": "Content Strategy Blueprint",
        "description": "Complete brief: audience analysis, content pillars, platform strategy, posting schedule, 10 content ideas, tone guide, hashtag strategy.",
        "price_usd": 45,
        "price_hbar": 300,
        "cost_estimate_usd": 2.00,
        "margin_percent": 96,
        "delivery": "15 minutes",
        "tier": "professional",
        "target": "marketing teams, agencies, solopreneurs",
    },
    "prospect_package": {
        "name": "Sales Prospect Package (10 leads)",
        "description": "10 qualified prospects in your industry. Deep research, BANT scoring, decision maker identified. Top 3 get personalized 4-touch outreach sequences.",
        "price_usd": 55,
        "price_hbar": 370,
        "cost_estimate_usd": 2.50,
        "margin_percent": 95,
        "delivery": "20 minutes",
        "tier": "professional",
        "target": "sales teams, agencies, B2B SaaS",
    },
    "market_research": {
        "name": "Market Intelligence Report",
        "description": "TAM analysis, key players, trends, pain points, pricing models, funding landscape, news monitoring. Multi-angle deep research.",
        "price_usd": 65,
        "price_hbar": 430,
        "cost_estimate_usd": 2.00,
        "margin_percent": 97,
        "delivery": "15 minutes",
        "tier": "professional",
        "target": "founders, investors, product teams",
    },

    # ── TIER 3: Premium (high value, high trust) ──
    "full_brand_package": {
        "name": "Complete Brand Operations Setup",
        "description": "Brand guidelines configuration, compliance engine setup, AI caption style training, team workflow design, content calendar, and competitor positioning.",
        "price_usd": 150,
        "price_hbar": 1000,
        "cost_estimate_usd": 8.00,
        "margin_percent": 95,
        "delivery": "1 hour",
        "tier": "premium",
        "target": "agencies, DTC brands, marketing teams",
    },
    "custom_agent": {
        "name": "Custom AI Agent Development",
        "description": "I build a custom autonomous agent for your specific use case. Includes: skill creation, API integrations, Telegram bot, Hedera payments. Full handoff.",
        "price_usd": 300,
        "price_hbar": 2000,
        "cost_estimate_usd": 15.00,
        "margin_percent": 95,
        "delivery": "24 hours",
        "tier": "premium",
        "target": "tech founders, agencies, enterprises",
    },
    "monthly_retainer": {
        "name": "Wave Monthly Retainer",
        "description": "Wave operates for you 24/7: daily prospecting, weekly competitor monitoring, content strategy updates, brand compliance checks, analytics reports. Unlimited AI actions.",
        "price_usd": 500,
        "price_hbar": 3300,
        "cost_estimate_usd": 30.00,
        "margin_percent": 94,
        "delivery": "Ongoing",
        "tier": "premium",
        "target": "agencies, growing brands, marketing teams",
    },
}


def _load_pricing() -> dict:
    if PRICING_FILE.exists():
        return json.loads(PRICING_FILE.read_text())
    return DEFAULT_PRICING


def _save_pricing(pricing: dict):
    _ensure_dir()
    PRICING_FILE.write_text(json.dumps(pricing, indent=2, ensure_ascii=False))


async def get_pricing(params: Dict[str, Any]) -> Dict:
    """Get current pricing for all services."""
    pricing = _load_pricing()
    tier_filter = params.get("tier", "")

    lines = ["**Wave Service Pricing**\n"]

    tiers = {"quick": "Quick Wins (impulse buy)", "professional": "Professional Services", "premium": "Premium Packages"}

    for tier_key, tier_name in tiers.items():
        if tier_filter and tier_filter != tier_key:
            continue

        tier_services = {k: v for k, v in pricing.items() if v.get("tier") == tier_key}
        if not tier_services:
            continue

        lines.append("**%s:**\n" % tier_name)
        for key, svc in tier_services.items():
            lines.append("  **%s** — $%d / %d HBAR" % (svc["name"], svc["price_usd"], svc["price_hbar"]))
            lines.append("  %s" % svc["description"][:120])
            lines.append("  Delivery: %s | Margin: %d%% | Target: %s\n" % (
                svc["delivery"], svc["margin_percent"], svc["target"]))

    monthly_potential = sum(s["price_usd"] for s in pricing.values() if s["tier"] == "quick") * 30
    lines.append("---")
    lines.append("**Revenue potential:** If each quick-win sells 1x/day = $%d/month passive" % monthly_potential)

    return {"success": True, "data": pricing, "message": "\n".join(lines)}


async def adjust_price(params: Dict[str, Any]) -> Dict:
    """Adjust pricing for a specific service."""
    service_key = params.get("service", "")
    new_price_usd = params.get("price_usd", 0)
    new_price_hbar = params.get("price_hbar", 0)
    reason = params.get("reason", "")

    pricing = _load_pricing()
    if service_key not in pricing:
        return {"success": False, "data": None, "message": "Unknown service: %s. Options: %s" % (service_key, ", ".join(pricing.keys()))}

    old_price = pricing[service_key]["price_usd"]
    if new_price_usd:
        pricing[service_key]["price_usd"] = new_price_usd
        pricing[service_key]["price_hbar"] = new_price_hbar or int(new_price_usd / 0.15)
        cost = pricing[service_key]["cost_estimate_usd"]
        pricing[service_key]["margin_percent"] = int((1 - cost / new_price_usd) * 100)

    _save_pricing(pricing)

    return {
        "success": True,
        "data": pricing[service_key],
        "message": "Price updated: %s — $%d → $%d (%s)" % (
            pricing[service_key]["name"], old_price, new_price_usd, reason or "manual adjustment"
        ),
    }


async def pricing_analysis(params: Dict[str, Any]) -> Dict:
    """Research market rates and suggest optimal pricing."""
    service_type = params.get("service_type", "AI agent services")

    queries = [
        "AI agent freelance rates 2026",
        "fiverr AI content generation pricing",
        "upwork AI automation hourly rate",
        "AI brand audit service pricing",
        "AI sales prospecting service cost",
        "competitor analysis report pricing",
    ]

    market_data = []
    for q in queries:
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(q, max_results=3):
                    market_data.append({
                        "query": q,
                        "title": r.get("title", ""),
                        "snippet": r.get("body", ""),
                    })
        except Exception:
            pass

    lines = ["**Market Pricing Research: %s**\n" % service_type]
    for item in market_data[:12]:
        lines.append("- %s — %s" % (item["title"][:50], item["snippet"][:100]))

    lines.append("\n**Wave's Pricing Strategy:**")
    lines.append("- Quick wins ($9-15): impulse buys, high volume, 94-98% margin")
    lines.append("- Professional ($35-65): considered purchases, strong value prop, 95-97% margin")
    lines.append("- Premium ($150-500): high-trust, relationship-based, 94-95% margin")
    lines.append("- All priced BELOW human freelancers, ABOVE commodity AI tools")
    lines.append("- Key insight: price on VALUE delivered, not COST to produce")

    return {"success": True, "data": market_data, "message": "\n".join(lines)}


async def revenue_forecast(params: Dict[str, Any]) -> Dict:
    """Project monthly revenue based on conversion assumptions."""
    daily_reach = params.get("daily_reach", 50)
    conversion_rate = params.get("conversion_rate", 0.02)

    pricing = _load_pricing()
    daily_sales = daily_reach * conversion_rate

    tiers = {"quick": [], "professional": [], "premium": []}
    for svc in pricing.values():
        tiers[svc["tier"]].append(svc["price_usd"])

    # Assume sales distribution: 60% quick, 30% professional, 10% premium
    avg_quick = sum(tiers["quick"]) / len(tiers["quick"]) if tiers["quick"] else 0
    avg_pro = sum(tiers["professional"]) / len(tiers["professional"]) if tiers["professional"] else 0
    avg_premium = sum(tiers["premium"]) / len(tiers["premium"]) if tiers["premium"] else 0

    daily_rev = daily_sales * (avg_quick * 0.6 + avg_pro * 0.3 + avg_premium * 0.1)
    monthly_rev = daily_rev * 30
    yearly_rev = monthly_rev * 12

    # Cost (API calls)
    avg_cost = 2.0  # ~$2 average API cost per sale
    monthly_cost = daily_sales * 30 * avg_cost
    monthly_profit = monthly_rev - monthly_cost

    lines = [
        "**Revenue Forecast**\n",
        "Assumptions: %d daily reach, %.1f%% conversion\n" % (daily_reach, conversion_rate * 100),
        "Daily sales: %.1f" % daily_sales,
        "Avg ticket: $%.0f (blended across tiers)\n" % (daily_rev / daily_sales if daily_sales else 0),
        "**Monthly:**",
        "  Revenue: $%.0f" % monthly_rev,
        "  API cost: $%.0f" % monthly_cost,
        "  Profit:  $%.0f (%.0f%% margin)\n" % (monthly_profit, (monthly_profit / monthly_rev * 100) if monthly_rev else 0),
        "**Annual:** $%.0f revenue, $%.0f profit\n" % (yearly_rev, monthly_profit * 12),
        "**Scaling scenarios:**",
        "  100 reach/day, 2%% conv: $%.0f/month" % (100 * 0.02 * (avg_quick * 0.6 + avg_pro * 0.3 + avg_premium * 0.1) * 30),
        "  500 reach/day, 3%% conv: $%.0f/month" % (500 * 0.03 * (avg_quick * 0.6 + avg_pro * 0.3 + avg_premium * 0.1) * 30),
        "  1000 reach/day, 5%% conv: $%.0f/month" % (1000 * 0.05 * (avg_quick * 0.6 + avg_pro * 0.3 + avg_premium * 0.1) * 30),
    ]

    return {
        "success": True,
        "data": {
            "daily_sales": daily_sales,
            "monthly_revenue": monthly_rev,
            "monthly_profit": monthly_profit,
            "yearly_revenue": yearly_rev,
        },
        "message": "\n".join(lines),
    }


TOOLS = [
    {
        "name": "get_pricing",
        "description": "Get current pricing for all Wave services. Shows 3 tiers (quick wins, professional, premium) with prices in USD and HBAR, margins, delivery times, and target customers.",
        "handler": get_pricing,
        "parameters": {
            "type": "object",
            "properties": {
                "tier": {"type": "string", "enum": ["quick", "professional", "premium"], "description": "Filter by tier"},
            },
        },
    },
    {
        "name": "adjust_price",
        "description": "Adjust pricing for a specific service. Recalculates margin automatically. Use when market conditions change or testing price elasticity.",
        "handler": adjust_price,
        "parameters": {
            "type": "object",
            "properties": {
                "service": {"type": "string", "description": "Service key to adjust"},
                "price_usd": {"type": "number", "description": "New USD price"},
                "price_hbar": {"type": "number", "description": "New HBAR price (auto-calculated if omitted)"},
                "reason": {"type": "string", "description": "Reason for adjustment"},
            },
            "required": ["service", "price_usd"],
        },
    },
    {
        "name": "pricing_analysis",
        "description": "Research market rates for AI services and compare with Wave's pricing. Searches Fiverr, Upwork, and freelance markets for competitive intelligence.",
        "handler": pricing_analysis,
        "parameters": {
            "type": "object",
            "properties": {
                "service_type": {"type": "string", "default": "AI agent services"},
            },
        },
    },
    {
        "name": "revenue_forecast",
        "description": "Project monthly and annual revenue based on reach and conversion assumptions. Shows scaling scenarios.",
        "handler": revenue_forecast,
        "parameters": {
            "type": "object",
            "properties": {
                "daily_reach": {"type": "integer", "default": 50, "description": "People reached per day (Moltbook + X + Telegram)"},
                "conversion_rate": {"type": "number", "default": 0.02, "description": "Conversion rate (0.02 = 2%)"},
            },
        },
    },
]
