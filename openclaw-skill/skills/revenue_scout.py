"""Revenue Scout — Finds paid opportunities matching Wave's capabilities.

Scans web, HN hiring threads, Reddit freelance boards for:
- Freelance contracts (AI/automation/agents)
- Bug bounties and security audit gigs
- Consulting RFPs
- Grant calls and accelerator programs

Scores by estimated revenue, effort, and capability fit.
Returns ranked list with draft outreach templates.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("openclaw.skills.revenue_scout")

SCOUT_LOG = Path(__file__).parent.parent / "memory" / "revenue_scout.jsonl"

# Capability profile for matching
CAPABILITIES = {
    "ai_agents": {"keywords": ["AI agent", "autonomous agent", "LLM agent", "claude", "GPT automation"], "rate_usd_hr": 200},
    "security_audit": {"keywords": ["security audit", "pentest", "vulnerability", "OWASP", "bug bounty"], "rate_usd_hr": 250},
    "automation": {"keywords": ["automation", "workflow", "scraping", "data pipeline", "ETL"], "rate_usd_hr": 150},
    "consulting": {"keywords": ["AI strategy", "AI consultant", "technical advisor", "fractional CTO"], "rate_usd_hr": 300},
    "development": {"keywords": ["full stack", "Python developer", "API development", "SaaS"], "rate_usd_hr": 175},
}

OUTREACH_TEMPLATE = """Subject: {subject}

Hi {contact},

I noticed {hook}. I specialize in {capability} and have delivered similar work for clients including autonomous AI systems, security hardening, and end-to-end automation.

Relevant experience:
- Built 158+ operational AI skills powering autonomous agent systems
- Security audit infrastructure (OWASP-aligned, SSL/TLS, DNS recon)
- Agent-to-agent commerce protocols on Hedera

I can {value_prop}. Happy to share specifics or do a quick scoping call.

Best,
Manuel Galmanus
"""


def _score_opportunity(title: str, description: str) -> Dict[str, Any]:
    """Score an opportunity by fit, revenue potential, and effort."""
    title_lower = (title + " " + description).lower()
    
    matches = []
    for cap_name, cap in CAPABILITIES.items():
        for kw in cap["keywords"]:
            if kw.lower() in title_lower:
                matches.append(cap_name)
                break
    
    if not matches:
        return {"score": 0, "matches": [], "estimated_value": 0}
    
    # Revenue estimation heuristics
    value_signals = {
        "contract": 5000, "full-time": 15000, "part-time": 7500,
        "project": 3000, "bounty": 1000, "grant": 10000,
        "retainer": 8000, "consulting": 4000, "audit": 2000,
    }
    
    est_value = 1500  # baseline
    for signal, val in value_signals.items():
        if signal in title_lower:
            est_value = max(est_value, val)
    
    score = min(100, len(matches) * 25 + (est_value / 500))
    
    return {
        "score": round(score, 1),
        "matches": list(set(matches)),
        "estimated_value_usd": est_value,
        "rate_usd_hr": max(CAPABILITIES[m]["rate_usd_hr"] for m in matches),
    }


def _log_scan(results: Dict):
    """Persist scan results for tracking conversion."""
    SCOUT_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {"timestamp": datetime.utcnow().isoformat(), **results}
    with open(SCOUT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


async def execute(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute revenue scout scan.
    
    Params:
        focus: str — primary capability to scout for (default: all)
        min_value: int — minimum estimated USD value (default: 500)
        sources: list — which sources to scan (default: all)
    """
    focus = params.get("focus", "all")
    min_value = params.get("min_value", 500)
    
    # Build search queries based on focus
    if focus == "all":
        search_queries = [
            "hiring freelance AI agent developer contract 2026",
            "bug bounty program AI security audit paid",
            "looking for automation consultant RFP AI workflow",
            "AI startup grant accelerator open applications 2026",
        ]
    else:
        search_queries = [
            f"hiring freelance {focus} contract 2026",
            f"{focus} paid bounty program gig",
            f"consultant {focus} RFP project",
        ]
    
    # Import web_search skill
    try:
        from skills.web_search import execute as web_search
    except ImportError:
        # Fallback: try direct import
        try:
            from web_search import execute as web_search
        except ImportError:
            return {
                "success": False,
                "error": "web_search skill not available",
                "action": "Run manually: python3 skill_executor.py web_search '{\"query\": \"hiring AI agent freelance 2026\"}'",
            }
    
    opportunities = []
    sources_scanned = 0
    
    for query in search_queries:
        try:
            result = await web_search({"query": query})
            sources_scanned += 1
            
            if isinstance(result, dict) and result.get("success"):
                items = result.get("data", {}).get("results", [])
                if isinstance(items, list):
                    for item in items[:5]:
                        title = item.get("title", "")
                        desc = item.get("snippet", item.get("description", ""))
                        url = item.get("url", item.get("link", ""))
                        
                        scoring = _score_opportunity(title, desc)
                        if scoring["score"] > 0 and scoring.get("estimated_value_usd", 0) >= min_value:
                            opportunities.append({
                                "title": title,
                                "url": url,
                                "description": desc[:200],
                                "source_query": query,
                                **scoring,
                            })
        except Exception as e:
            logger.warning(f"Scout scan failed for query '{query}': {e}")
    
    # Sort by score descending
    opportunities.sort(key=lambda x: x["score"], reverse=True)
    top = opportunities[:10]
    
    # Generate outreach drafts for top 3
    for opp in top[:3]:
        opp["draft_outreach"] = OUTREACH_TEMPLATE.format(
            subject=f"Re: {opp['title'][:50]}",
            contact="[Name]",
            hook=f"your posting about {opp['matches'][0].replace('_', ' ')}" if opp["matches"] else "your opportunity",
            capability=", ".join(m.replace("_", " ") for m in opp["matches"]),
            value_prop=f"deliver this within 1-2 weeks at ${opp.get('rate_usd_hr', 200)}/hr",
        )
    
    result = {
        "success": True,
        "timestamp": datetime.utcnow().isoformat(),
        "focus": focus,
        "min_value_usd": min_value,
        "sources_scanned": sources_scanned,
        "total_found": len(opportunities),
        "top_opportunities": top,
        "revenue_pipeline_estimate": sum(o.get("estimated_value_usd", 0) for o in top),
        "next_actions": [
            "Review top opportunities and refine outreach",
            "Run put_analyze on promising company targets",
            "Use kill_chain_plan to strategize approach for high-value leads",
        ],
    }
    
    _log_scan(result)
    return result


# Register as Wave skill
TOOL_DEFINITION = {
    "name": "revenue_scout",
    "description": "Scan web/HN/Reddit for paid freelance, bounty, consulting, and grant opportunities matching AI/automation capabilities. Scores and ranks by revenue potential with draft outreach.",
    "parameters": {
        "type": "object",
        "properties": {
            "focus": {
                "type": "string",
                "description": "Capability focus: 'all', 'ai_agents', 'security_audit', 'automation', 'consulting', 'development'",
                "default": "all",
            },
            "min_value": {
                "type": "integer",
                "description": "Minimum estimated USD value to include",
                "default": 500,
            },
        },
    },
}
