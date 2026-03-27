"""
Revenue Autopsy — Consulting-grade competitive intelligence as a service.

Tears apart any company's revenue model, identifies monetization gaps,
maps vulnerabilities, and generates concrete attack strategies.

This is $500-2000/report consulting work, automated.

Revenue model: Sell via agent_commerce or direct API access.
  Scout (free): 1 summary/month
  Operator ($49/mo): 10 full reports
  War Room ($299/mo): Unlimited + monitoring + API
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import httpx

logger = logging.getLogger("openclaw.revenue_autopsy")

REPORTS_DIR = Path(__file__).parent.parent / "memory" / "revenue_autopsies"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY", "")
BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"


async def _search(query: str, count: int = 5) -> list:
    """Search via Brave API."""
    if not BRAVE_API_KEY:
        return [{"title": "No API key", "description": "BRAVE_API_KEY needed", "url": ""}]
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(BRAVE_URL, params={"q": query, "count": count}, headers={
                "X-Subscription-Token": BRAVE_API_KEY,
                "Accept": "application/json",
            })
            data = r.json()
        return [
            {"title": i.get("title", ""), "url": i.get("url", ""), "description": i.get("description", "")}
            for i in data.get("web", {}).get("results", [])[:count]
        ]
    except Exception as e:
        logger.error("Search failed: %s", e)
        return [{"title": "Error", "description": str(e), "url": ""}]


async def revenue_autopsy(params: Dict[str, Any]) -> Dict:
    """
    Full revenue autopsy on a target company/product.

    Params:
        target: Company or product name (required)
        mode: "compete" | "clone" | "partner" (default: compete)
        depth: "quick" | "full" (default: full)
    """
    target = params.get("target", "").strip()
    mode = params.get("mode", "compete")
    depth = params.get("depth", "full")

    if not target:
        return {"success": False, "data": None, "message": "Provide a target company/product name"}

    if mode not in ("compete", "clone", "partner"):
        mode = "compete"

    ts = datetime.utcnow()

    # Phase 1: Multi-vector research
    research_queries = {
        "revenue": f"{target} revenue model pricing plans business model how they make money",
        "competitors": f"{target} competitors alternatives comparison vs",
        "vulnerabilities": f"{target} problems complaints reviews churn issues limitations",
        "market": f"{target} market size TAM total addressable market growth",
        "tech": f"{target} tech stack architecture infrastructure",
    }

    if depth == "quick":
        research_queries = {k: v for k, v in list(research_queries.items())[:3]}

    intel = {}
    for category, query in research_queries.items():
        results = await _search(query, count=5)
        intel[category] = results
        logger.info("Researched %s: %d results", category, len(results))

    # Phase 2: Synthesize findings
    def _summarize(results: list) -> str:
        lines = []
        for r in results:
            if r.get("description"):
                lines.append(f"• {r['description']}")
            elif r.get("title"):
                lines.append(f"• {r['title']}")
        return "\n".join(lines) if lines else "Insufficient data"

    revenue_intel = _summarize(intel.get("revenue", []))
    competitor_intel = _summarize(intel.get("competitors", []))
    vulnerability_intel = _summarize(intel.get("vulnerabilities", []))
    market_intel = _summarize(intel.get("market", []))
    tech_intel = _summarize(intel.get("tech", []))

    # Phase 3: Attack vectors based on mode
    attack_strategies = {
        "compete": {
            "pricing": [
                "Undercut their most commoditized tier by 30-50%",
                "Offer usage-based pricing where they charge flat rate",
                "Free tier that covers 80% of their paid tier 1 features",
            ],
            "acquisition": [
                "Target churned customers via G2/Trustpilot negative reviews",
                "SEO: build '{target} alternative' and '{target} vs' landing pages",
                "Run comparison ads on their brand keywords",
                "Offer migration tools and data portability guarantees",
            ],
            "product": [
                "Build the #1 requested feature from their community forums",
                "Ship AI-native version of their core workflow",
                "Open API where they have a closed ecosystem",
                "Mobile-first if they're desktop-only (or vice versa)",
            ],
        },
        "clone": {
            "architecture": [
                "Rebuild core value prop with modern stack — cut COGS 60%",
                "AI-native from day 1 (they'll bolt it on later)",
                "Edge-first deployment for latency advantage",
            ],
            "positioning": [
                "Target adjacent vertical they deliberately ignore",
                "Geographic expansion to markets they don't serve",
                "Open-source the commodity layer, monetize the workflow",
                "Developer-first where they're enterprise-first (or vice versa)",
            ],
            "speed": [
                "MVP in 30 days — match their core 3 features only",
                "Ship daily, outpace their release cycle",
                "Use their public API as initial backend, replace incrementally",
            ],
        },
        "partner": {
            "integration": [
                "Build the #1 integration their users request",
                "Create middleware that connects them to an ecosystem they lack",
                "Offer a white-label capability they'd take 18 months to build",
            ],
            "revenue_share": [
                "Propose rev-share on upsell: your feature, their distribution",
                "Co-sell arrangement targeting their enterprise pipeline",
                "Offer free integration for their users, monetize premium features",
            ],
            "strategic": [
                "Fill their product gap to prevent competitor bundling",
                "Provide data/capability that strengthens their moat",
                "Build for their API platform — become essential infrastructure",
            ],
        },
    }

    chosen_vectors = attack_strategies.get(mode, attack_strategies["compete"])

    # Phase 4: Revenue model for selling THIS as a service
    service_model = {
        "pricing_tiers": [
            {"name": "Scout", "price": 0, "interval": "month", "features": [
                "1 summary autopsy per month",
                "Basic revenue model analysis",
                "Top 3 competitors listed",
            ]},
            {"name": "Operator", "price": 49, "interval": "month", "features": [
                "10 full autopsy reports per month",
                "Attack vectors + vulnerability mapping",
                "Competitor deep-dive with tech stack analysis",
                "Export to PDF/Notion",
            ]},
            {"name": "War Room", "price": 299, "interval": "month", "features": [
                "Unlimited autopsy reports",
                "Real-time monitoring on targets",
                "API access for integration",
                "Custom attack playbooks",
                "Weekly intel digest",
            ]},
        ],
        "revenue_projections": {
            "month_1": {"subscribers": "10-20", "mrr": "$500-1,500"},
            "month_3": {"subscribers": "50-100", "mrr": "$3,000-8,000"},
            "month_6": {"subscribers": "150-300", "mrr": "$10,000-25,000"},
            "month_12": {"subscribers": "500-1000", "mrr": "$30,000-80,000"},
        },
        "cac_channels": [
            "SEO: '[company] competitive analysis' keywords",
            "Product Hunt launch",
            "X/Twitter threads showing live autopsies",
            "Indie Hackers / HN Show posts",
            "Cold outreach to VC analysts and corp dev teams",
        ],
    }

    # Phase 5: Build the report
    report_lines = [
        f"{'='*60}",
        f" REVENUE AUTOPSY: {target.upper()}",
        f" Mode: {mode.upper()} | Depth: {depth.upper()}",
        f" Generated: {ts.strftime('%Y-%m-%d %H:%M UTC')}",
        f"{'='*60}",
        "",
        "▎ REVENUE MODEL",
        "─" * 40,
        revenue_intel,
        "",
        "▎ COMPETITIVE LANDSCAPE",
        "─" * 40,
        competitor_intel,
        "",
        "▎ VULNERABILITY MAP",
        "─" * 40,
        vulnerability_intel,
        "",
    ]

    if depth == "full":
        report_lines.extend([
            "▎ MARKET SIZING",
            "─" * 40,
            market_intel,
            "",
            "▎ TECH STACK INTEL",
            "─" * 40,
            tech_intel,
            "",
        ])

    report_lines.extend([
        f"▎ ATTACK STRATEGY ({mode.upper()})",
        "─" * 40,
    ])
    for category, vectors in chosen_vectors.items():
        report_lines.append(f"\n  [{category.upper()}]")
        for v in vectors:
            report_lines.append(f"    → {v}")

    report_lines.extend([
        "",
        "▎ MONETIZATION (selling autopsy-as-a-service)",
        "─" * 40,
        "  Scout: Free — 1 report/mo",
        "  Operator: $49/mo — 10 reports + attack vectors",
        "  War Room: $299/mo — unlimited + monitoring + API",
        "",
        f"  M3 target: {service_model['revenue_projections']['month_3']['mrr']} MRR",
        f"  M12 target: {service_model['revenue_projections']['month_12']['mrr']} MRR",
        "",
        f"{'='*60}",
    ])

    report_text = "\n".join(report_lines)

    # Save report
    report_file = REPORTS_DIR / f"{target.lower().replace(' ', '_')}_{ts.strftime('%Y%m%d_%H%M%S')}.json"
    report_data = {
        "target": target,
        "mode": mode,
        "depth": depth,
        "timestamp": ts.isoformat(),
        "intel": {k: [dict(r) for r in v] for k, v in intel.items()},
        "attack_vectors": chosen_vectors,
        "service_model": service_model,
        "report_text": report_text,
    }
    report_file.write_text(json.dumps(report_data, indent=2, default=str))
    logger.info("Saved autopsy report: %s", report_file)

    return {
        "success": True,
        "data": {
            "report": report_text,
            "target": target,
            "mode": mode,
            "attack_vectors": chosen_vectors,
            "service_model": service_model,
            "saved_to": str(report_file),
        },
        "message": f"Revenue autopsy complete for {target}",
    }


async def autopsy_list(params: Dict[str, Any]) -> Dict:
    """List all saved autopsy reports."""
    reports = sorted(REPORTS_DIR.glob("*.json"), reverse=True)
    items = []
    for r in reports[:20]:
        try:
            data = json.loads(r.read_text())
            items.append({
                "target": data.get("target"),
                "mode": data.get("mode"),
                "timestamp": data.get("timestamp"),
                "file": r.name,
            })
        except Exception:
            continue
    return {
        "success": True,
        "data": {"count": len(items), "reports": items},
        "message": f"{len(items)} autopsy reports on file",
    }


# ── Tool registration ──────────────────────────────────────────────
TOOLS = [
    {
        "name": "revenue_autopsy",
        "description": "Tear apart a company's revenue model, map vulnerabilities, and generate attack strategies. Consulting-grade competitive intelligence.",
        "handler": revenue_autopsy,
        "parameters": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Company or product name to analyze"},
                "mode": {"type": "string", "enum": ["compete", "clone", "partner"], "description": "Attack strategy mode (default: compete)"},
                "depth": {"type": "string", "enum": ["quick", "full"], "description": "Analysis depth (default: full)"},
            },
            "required": ["target"],
        },
    },
    {
        "name": "autopsy_list",
        "description": "List all saved revenue autopsy reports.",
        "handler": autopsy_list,
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
]
