"""Prospect Pipeline — Revenue Engine.

Finds companies with AI/automation buying signals (hiring, RFPs, announcements),
generates personalized cold outreach emails ready to send.
Converts public data into qualified leads.
"""

from __future__ import annotations
import logging
import json
import re
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger("openclaw.prospect_pipeline")

TOOL_SCHEMA = {
    "name": "prospect_pipeline",
    "description": "Revenue engine: finds companies actively hiring for AI/automation (buying signal), generates personalized cold outreach for consulting services.",
    "input_schema": {
        "type": "object",
        "properties": {
            "industry": {"type": "string", "description": "Target industry or niche, e.g. 'AI automation', 'fintech AI', 'healthcare ML'", "default": "AI automation"},
            "service": {"type": "string", "description": "Service offering description", "default": "AI agent development and process automation"},
            "sender": {"type": "string", "description": "Your name", "default": "Manuel Galmanus"},
            "company": {"type": "string", "description": "Your company", "default": "Bluewave"},
            "max": {"type": "integer", "description": "Max prospects to generate", "default": 5}
        }
    }
}


async def run(params: Dict[str, Any]) -> Dict[str, Any]:
    industry = params.get("industry", "AI automation")
    service_offer = params.get("service", "AI agent development and process automation")
    sender_name = params.get("sender", "Manuel Galmanus")
    sender_company = params.get("company", "Bluewave")
    max_prospects = params.get("max", 5)

    # Import sibling skill for web search
    from skills.web_search import run as web_search

    search_queries = [
        f"companies hiring {industry} engineer 2026",
        f"{industry} consulting RFP contract opportunity 2026",
        f"startup implementing {industry} looking for help",
    ]

    prospects = []
    seen = set()

    for query in search_queries:
        try:
            search_result = await web_search({"query": query, "max_results": max_prospects})
            results = []
            if isinstance(search_result, dict):
                results = search_result.get("results", search_result.get("organic", []))
            elif isinstance(search_result, list):
                results = search_result

            for r in results:
                title = r.get("title", "")
                url = r.get("url", r.get("href", r.get("link", "")))
                snippet = r.get("body", r.get("snippet", r.get("description", "")))

                # Extract domain
                m = re.search(r"https?://(?:www\.)?([^/]+)", url)
                domain = m.group(1) if m else url

                if domain in seen or not title:
                    continue
                seen.add(domain)

                company_name = re.split(r"\s[-|–—]\s", title)[0].strip()[:60]

                # Score the signal
                signal_keywords = ["hiring", "engineer", "automat", "ai ", "agent", "implement", "looking for", "rfp", "contract"]
                signal_score = sum(1 for kw in signal_keywords if kw in (title + snippet).lower())

                prospects.append({
                    "company": company_name,
                    "signal": snippet[:250],
                    "url": url,
                    "domain": domain,
                    "score": signal_score,
                })
        except Exception as e:
            logger.warning(f"Search query failed: {e}")
            continue

    # Deduplicate and rank
    prospects.sort(key=lambda x: x["score"], reverse=True)
    prospects = prospects[:max_prospects]

    # Generate outreach
    pipeline = []
    for p in prospects:
        priority = "HIGH" if p["score"] >= 2 else "MEDIUM" if p["score"] >= 1 else "LOW"

        email = f"""Subject: {p['company']} + {sender_company} — {industry} results without the hiring overhead

Hi,

I noticed {p['company']} is building out {industry} capabilities — that's a strong signal you're serious about this.

Rather than a 6-month hiring cycle, {sender_company} delivers production-ready AI agents in weeks. Recent results:

• Automated document processing pipeline — saved client 40+ hrs/week
• Custom AI agent replacing 3 manual review workflows  
• RAG system over proprietary data — 95%+ accuracy, deployed in 3 weeks

Would a 15-minute call next week make sense to explore fit?

{sender_name}
{sender_company}"""

        pipeline.append({
            "prospect": p,
            "priority": priority,
            "outreach_email": email.strip(),
        })

    return {
        "generated_at": datetime.now().isoformat(),
        "query_industry": industry,
        "service_offered": service_offer,
        "total_prospects": len(pipeline),
        "pipeline": pipeline,
        "revenue_actions": [
            "1. Personalize each email with specific company details from their job posting",
            "2. Find decision-maker (VP Eng, CTO, Head of AI) via LinkedIn",
            "3. Send emails Tue-Thu, 8-10am recipient's timezone",
            "4. Follow up Day 3 (value-add), Day 7 (soft close), Day 14 (breakup)",
            "5. Track in CRM — target 2-3% reply rate, 0.5% conversion",
            f"6. At $15-50k/engagement, {max_prospects} prospects × 2% = potential ${max_prospects * 0.02 * 25000:.0f} pipeline value",
        ]
    }
