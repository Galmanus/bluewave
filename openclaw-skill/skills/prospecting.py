"""Prospecting — Wave finds, qualifies, and prepares outreach for potential clients.

Full sales intelligence pipeline:
1. Find companies that match the ICP (Ideal Customer Profile)
2. Research each prospect deeply
3. Score and qualify
4. Generate personalized outreach
5. Track the pipeline persistently
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import httpx
from duckduckgo_search import DDGS

logger = logging.getLogger("openclaw.skills.prospecting")

MEMORY_DIR = Path(__file__).parent.parent / "memory"
PIPELINE_FILE = MEMORY_DIR / "sales_pipeline.jsonl"

# Bluewave ICP — Wave knows who to hunt
ICP = {
    "industries": ["marketing agency", "creative agency", "brand agency", "digital agency",
                    "content studio", "media company", "ecommerce", "DTC brand"],
    "pain_signals": ["content bottleneck", "approval delays", "brand inconsistency",
                     "hiring creative", "scaling content", "asset management chaos",
                     "too many tools", "content operations"],
    "roles": ["Head of Marketing", "Creative Director", "Brand Manager", "CMO",
              "VP Marketing", "Content Lead", "Marketing Operations", "Growth Lead"],
    "size": "10-500 employees",
    "budget_signals": ["Series A", "Series B", "raised funding", "hiring marketing",
                       "expanding team", "new CMO", "rebranding"],
}


def _ensure_dir():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def _append_pipeline(entry: dict):
    _ensure_dir()
    with open(PIPELINE_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


def _read_pipeline(limit: int = 100) -> list:
    if not PIPELINE_FILE.exists():
        return []
    lines = PIPELINE_FILE.read_text(encoding="utf-8").strip().split("\n")
    entries = []
    for line in lines[-limit:]:
        if line.strip():
            try:
                entries.append(json.loads(line))
            except Exception:
                pass
    return entries


async def find_prospects(params: Dict[str, Any]) -> Dict:
    """Find potential clients matching Bluewave's ICP. Searches for companies
    showing pain signals (content bottlenecks, hiring creatives, scaling content)
    in target industries."""
    industry = params.get("industry", "marketing agency")
    location = params.get("location", "")
    pain_signal = params.get("pain_signal", "")
    limit = params.get("limit", 10)

    queries = []
    if pain_signal:
        queries.append('"%s" "%s" %s' % (industry, pain_signal, location))
    else:
        # Search for multiple pain signals
        for signal in ICP["pain_signals"][:3]:
            queries.append('"%s" "%s" %s' % (industry, signal, location))

    # Also search for budget signals
    for signal in ICP["budget_signals"][:2]:
        queries.append('"%s" %s %s 2026' % (industry, signal, location))

    all_results = []
    seen_urls = set()
    for q in queries:
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(q, max_results=5):
                    url = r.get("href", "")
                    if url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append({
                            "title": r.get("title", ""),
                            "url": url,
                            "snippet": r.get("body", ""),
                            "query": q,
                        })
        except Exception:
            pass

    # Search LinkedIn for decision makers
    linkedin_results = []
    for role in ICP["roles"][:2]:
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(
                    'site:linkedin.com "%s" "%s" %s' % (role, industry, location),
                    max_results=3,
                ):
                    if "linkedin.com" in r.get("href", ""):
                        linkedin_results.append({
                            "title": r.get("title", ""),
                            "url": r.get("href", ""),
                            "snippet": r.get("body", ""),
                        })
        except Exception:
            pass

    # News about companies in this space
    news = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.news("%s %s hiring OR funding OR growth" % (industry, location), max_results=5):
                news.append({
                    "title": r.get("title", ""),
                    "source": r.get("source", ""),
                    "snippet": r.get("body", ""),
                    "url": r.get("url", ""),
                })
    except Exception:
        pass

    data = {
        "companies": all_results[:limit],
        "decision_makers": linkedin_results,
        "news_signals": news,
        "query_count": len(queries),
    }

    lines = ["**Prospect Hunt: %s%s**\n" % (industry, " in %s" % location if location else "")]
    lines.append("Found %d companies, %d decision makers, %d news signals\n" % (
        len(all_results), len(linkedin_results), len(news)))

    if all_results:
        lines.append("**Companies showing pain signals:**")
        for r in all_results[:limit]:
            lines.append("- %s — %s" % (r["title"][:60], r["snippet"][:120]))
        lines.append("")

    if linkedin_results:
        lines.append("**Decision makers on LinkedIn:**")
        for r in linkedin_results[:5]:
            lines.append("- %s — %s" % (r["title"][:60], r["url"]))
        lines.append("")

    if news:
        lines.append("**Recent signals (funding, hiring, growth):**")
        for n in news[:3]:
            lines.append("- %s (%s)" % (n["title"][:70], n["source"]))

    return {"success": True, "data": data, "message": "\n".join(lines)}


async def research_prospect(params: Dict[str, Any]) -> Dict:
    """Deep research on a specific prospect company. Finds website, team,
    tech stack, funding, pain points, content strategy."""
    company = params.get("company", "")
    website = params.get("website", "")

    if not company:
        return {"success": False, "data": None, "message": "Need company name"}

    research = {}

    # Company overview
    queries = {
        "overview": "%s company about" % company,
        "team": "%s team leadership founders" % company,
        "funding": "%s funding valuation investors 2025 2026" % company,
        "tech_stack": "%s technology stack tools uses" % company,
        "content": "%s blog content marketing social media" % company,
        "reviews": "%s reviews glassdoor G2 complaints" % company,
        "hiring": "%s careers hiring jobs marketing creative" % company,
    }

    for key, q in queries.items():
        results = []
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(q, max_results=4):
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", ""),
                    })
        except Exception:
            pass
        research[key] = results

    # Scrape their website if provided
    website_data = None
    if website:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(15.0), follow_redirects=True) as client:
                resp = await client.get(website, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; BluewavePrime/1.0)"
                })
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
            title = soup.title.string if soup.title else ""
            meta = soup.find("meta", attrs={"name": "description"})
            meta_desc = meta.get("content", "") if meta else ""
            website_data = {"title": title, "meta": meta_desc}
        except Exception:
            pass

    # Score the prospect
    score = 50  # base
    snippets = " ".join(
        r.get("snippet", "") for results in research.values() for r in results
    ).lower()

    for signal in ICP["pain_signals"]:
        if signal.lower() in snippets:
            score += 10
    for signal in ICP["budget_signals"]:
        if signal.lower() in snippets:
            score += 8
    if research.get("hiring"):
        score += 5
    if research.get("funding"):
        for r in research["funding"]:
            if any(w in r.get("snippet", "").lower() for w in ["series", "raised", "million"]):
                score += 15
                break
    score = min(100, score)

    data = {
        "company": company,
        "website": website,
        "research": research,
        "website_data": website_data,
        "score": score,
    }

    lines = [
        "**Prospect Research: %s**" % company,
        "Qualification Score: **%d/100**\n" % score,
    ]
    for key, results in research.items():
        if results:
            lines.append("**%s:**" % key.replace("_", " ").title())
            for r in results[:2]:
                lines.append("  - %s" % r["snippet"][:130])
            lines.append("")

    if score >= 70:
        lines.append("**VERDICT: HOT PROSPECT** — shows multiple buying signals")
    elif score >= 50:
        lines.append("**VERDICT: WARM** — worth pursuing with tailored outreach")
    else:
        lines.append("**VERDICT: COLD** — low fit signals, deprioritize")

    return {"success": True, "data": data, "message": "\n".join(lines)}


async def qualify_and_score(params: Dict[str, Any]) -> Dict:
    """Score a prospect on BANT criteria (Budget, Authority, Need, Timeline)."""
    company = params.get("company", "")
    budget_signals = params.get("budget_signals", "")
    authority_contact = params.get("authority_contact", "")
    pain_identified = params.get("pain_identified", "")
    timeline_urgency = params.get("timeline_urgency", "unknown")

    scores = {
        "budget": 0,
        "authority": 0,
        "need": 0,
        "timeline": 0,
    }

    # Budget
    if any(w in budget_signals.lower() for w in ["series", "funded", "million", "raised", "revenue"]):
        scores["budget"] = 25
    elif budget_signals:
        scores["budget"] = 15

    # Authority
    if any(w in authority_contact.lower() for w in ["cmo", "vp", "head", "director", "chief"]):
        scores["authority"] = 25
    elif authority_contact:
        scores["authority"] = 15

    # Need
    if any(w in pain_identified.lower() for w in ICP["pain_signals"]):
        scores["need"] = 25
    elif pain_identified:
        scores["need"] = 15

    # Timeline
    timeline_scores = {"urgent": 25, "this_quarter": 20, "this_year": 15, "exploring": 10, "unknown": 5}
    scores["timeline"] = timeline_scores.get(timeline_urgency, 5)

    total = sum(scores.values())

    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "company": company,
        "scores": scores,
        "total": total,
        "budget_signals": budget_signals,
        "authority_contact": authority_contact,
        "pain_identified": pain_identified,
        "timeline": timeline_urgency,
        "stage": "qualified" if total >= 60 else "nurture" if total >= 40 else "cold",
    }
    _append_pipeline(entry)

    lines = [
        "**BANT Qualification: %s**" % company,
        "Total Score: **%d/100**\n" % total,
        "Budget:    %d/25 — %s" % (scores["budget"], budget_signals[:60] or "unknown"),
        "Authority: %d/25 — %s" % (scores["authority"], authority_contact[:60] or "unknown"),
        "Need:      %d/25 — %s" % (scores["need"], pain_identified[:60] or "unknown"),
        "Timeline:  %d/25 — %s" % (scores["timeline"], timeline_urgency),
        "",
        "**Stage: %s**" % entry["stage"].upper(),
    ]

    if total >= 60:
        lines.append("\nRECOMMENDATION: Prepare personalized outreach. Use draft_cold_email with this context.")
    elif total >= 40:
        lines.append("\nRECOMMENDATION: Add to nurture sequence. Monitor for signal changes.")

    return {"success": True, "data": entry, "message": "\n".join(lines)}


async def generate_outreach(params: Dict[str, Any]) -> Dict:
    """Generate a complete multi-touch outreach sequence for a qualified prospect."""
    company = params.get("company", "")
    contact_name = params.get("contact_name", "")
    contact_role = params.get("contact_role", "")
    pain_point = params.get("pain_point", "content operations bottleneck")
    context = params.get("context", "")

    touch_1_subject = "Quick thought on %s's content workflow" % company
    touch_1 = (
        "Hi %s,\n\n"
        "Noticed %s %s — sounds like the kind of challenge "
        "that eats 8+ hours a week across the team.\n\n"
        "We built Bluewave specifically for this. It's an AI agent that handles "
        "the entire content lifecycle — upload, brand compliance check, approval routing, "
        "caption generation, multi-channel publish. Teams using it cut their content ops time in half.\n\n"
        "Worth a 15-min look?\n\n"
        "— Wave, Bluewave AI"
    ) % (contact_name or "there", company, context or "is scaling content production")

    touch_2_subject = "Re: %s content ops — a data point" % company
    touch_2 = (
        "Hi %s,\n\n"
        "One more thing — our clients' average time-to-publish dropped from 4.2 days to 6 hours "
        "after switching to Bluewave. The AI handles brand compliance automatically, "
        "so nothing goes out off-brand.\n\n"
        "Happy to show you how it works with a real demo using your actual assets.\n\n"
        "— Wave"
    ) % (contact_name or "there")

    touch_3_subject = "Last one — %s creative ops" % company
    touch_3 = (
        "Hi %s,\n\n"
        "Not trying to flood your inbox. Just wanted to leave this:\n\n"
        "Bluewave is free to try (3 users, 50 AI actions/month, no credit card). "
        "If %s is spending more than 5 hours a week on content approvals, "
        "it'll pay for itself in the first week.\n\n"
        "bluewave.app/signup\n\n"
        "Cheering for %s either way.\n\n"
        "— Wave"
    ) % (contact_name or "there", company, company)

    linkedin_msg = (
        "Hi %s — saw %s is %s. "
        "We built an AI agent that cuts content ops time in half "
        "(brand compliance, approvals, publishing — all automated). "
        "Worth connecting?"
    ) % (contact_name or "there", company, context or "growing the creative team")

    sequence = {
        "company": company,
        "contact": contact_name,
        "role": contact_role,
        "touches": [
            {"channel": "email", "day": 1, "subject": touch_1_subject, "body": touch_1},
            {"channel": "linkedin", "day": 2, "body": linkedin_msg},
            {"channel": "email", "day": 5, "subject": touch_2_subject, "body": touch_2},
            {"channel": "email", "day": 10, "subject": touch_3_subject, "body": touch_3},
        ],
    }

    _append_pipeline({
        "timestamp": datetime.utcnow().isoformat(),
        "company": company,
        "contact": contact_name,
        "role": contact_role,
        "stage": "outreach_prepared",
        "touches": len(sequence["touches"]),
    })

    lines = [
        "**Outreach Sequence: %s → %s (%s)**\n" % (company, contact_name or "?", contact_role or "?"),
        "**Day 1 — Email:**",
        "Subject: %s" % touch_1_subject,
        touch_1[:300] + "...\n",
        "**Day 2 — LinkedIn DM:**",
        linkedin_msg[:200] + "\n",
        "**Day 5 — Follow-up Email:**",
        "Subject: %s" % touch_2_subject,
        touch_2[:200] + "...\n",
        "**Day 10 — Break-up Email:**",
        "Subject: %s" % touch_3_subject,
        touch_3[:200] + "...",
    ]

    return {"success": True, "data": sequence, "message": "\n".join(lines)}


async def view_pipeline(params: Dict[str, Any]) -> Dict:
    """View the current sales pipeline — all prospects and their stages."""
    stage_filter = params.get("stage", "")
    limit = params.get("limit", 30)

    entries = _read_pipeline(limit=200)

    if stage_filter:
        entries = [e for e in entries if stage_filter.lower() in e.get("stage", "").lower()]

    # Deduplicate by company (keep latest)
    by_company = {}
    for e in entries:
        company = e.get("company", "unknown")
        by_company[company] = e
    entries = list(by_company.values())[-limit:]

    if not entries:
        return {"success": True, "data": [], "message": "Pipeline is empty. Use find_prospects to start hunting."}

    # Group by stage
    stages = {}
    for e in entries:
        stage = e.get("stage", "unknown")
        if stage not in stages:
            stages[stage] = []
        stages[stage].append(e)

    lines = ["**Sales Pipeline (%d prospects):**\n" % len(entries)]
    for stage, prospects in stages.items():
        lines.append("**%s** (%d)" % (stage.upper(), len(prospects)))
        for p in prospects:
            score = p.get("total", p.get("score", "?"))
            lines.append("  - %s (score: %s) — %s" % (
                p.get("company", "?"), score,
                p.get("pain_identified", p.get("contact", ""))[:60],
            ))
        lines.append("")

    return {"success": True, "data": entries, "message": "\n".join(lines)}


TOOLS = [
    {
        "name": "find_prospects",
        "description": "Hunt for potential Bluewave clients. Searches for companies in target industries showing pain signals (content bottlenecks, hiring creatives, scaling content, brand inconsistency). Also finds decision makers on LinkedIn and recent funding/growth news.",
        "handler": find_prospects,
        "parameters": {
            "type": "object",
            "properties": {
                "industry": {"type": "string", "default": "marketing agency", "description": "Target industry (marketing agency, creative agency, DTC brand, ecommerce, etc)"},
                "location": {"type": "string", "description": "Geographic focus (US, Brazil, Europe, etc)"},
                "pain_signal": {"type": "string", "description": "Specific pain to search for (content bottleneck, approval delays, brand inconsistency)"},
                "limit": {"type": "integer", "default": 10},
            },
        },
    },
    {
        "name": "research_prospect",
        "description": "Deep research on a specific company. Finds website, team, funding, tech stack, content strategy, reviews, hiring activity. Scores qualification 0-100 based on ICP fit.",
        "handler": research_prospect,
        "parameters": {
            "type": "object",
            "properties": {
                "company": {"type": "string", "description": "Company name to research"},
                "website": {"type": "string", "description": "Company website URL (optional, for deeper analysis)"},
            },
            "required": ["company"],
        },
    },
    {
        "name": "qualify_prospect",
        "description": "Score a prospect using BANT framework (Budget, Authority, Need, Timeline). Saves to pipeline with stage classification (qualified/nurture/cold).",
        "handler": qualify_and_score,
        "parameters": {
            "type": "object",
            "properties": {
                "company": {"type": "string", "description": "Company name"},
                "budget_signals": {"type": "string", "description": "Evidence of budget (funding, revenue, team size)"},
                "authority_contact": {"type": "string", "description": "Decision maker identified (name + role)"},
                "pain_identified": {"type": "string", "description": "Specific pain point they have"},
                "timeline_urgency": {"type": "string", "enum": ["urgent", "this_quarter", "this_year", "exploring", "unknown"], "default": "unknown"},
            },
            "required": ["company"],
        },
    },
    {
        "name": "generate_outreach",
        "description": "Generate a complete 4-touch outreach sequence (3 emails + 1 LinkedIn DM) personalized for a qualified prospect. Includes subject lines, body copy, and timing. Does NOT send — returns drafts.",
        "handler": generate_outreach,
        "parameters": {
            "type": "object",
            "properties": {
                "company": {"type": "string", "description": "Company name"},
                "contact_name": {"type": "string", "description": "Contact person's name"},
                "contact_role": {"type": "string", "description": "Their role (CMO, Head of Marketing, etc)"},
                "pain_point": {"type": "string", "default": "content operations bottleneck"},
                "context": {"type": "string", "description": "Relevant context (recent funding, hiring, rebranding)"},
            },
            "required": ["company"],
        },
    },
    {
        "name": "view_pipeline",
        "description": "View the current sales pipeline. Shows all prospects grouped by stage (qualified, nurture, cold, outreach_prepared). Use to track progress and plan next actions.",
        "handler": view_pipeline,
        "parameters": {
            "type": "object",
            "properties": {
                "stage": {"type": "string", "description": "Filter by stage (qualified, nurture, cold, outreach_prepared)"},
                "limit": {"type": "integer", "default": 30},
            },
        },
    },
]
