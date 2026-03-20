"""Dorking — senior OSINT specialist for surgical internet reconnaissance.

Advanced Google/DuckDuckGo search operators to find:
- Company decision makers and their emails
- Companies with specific pain points (job postings, complaints, RFPs)
- Freelance opportunities and gigs across platforms
- Contact forms, pricing pages, and tech stacks
- Forums, communities, and discussions about target topics
- Competitors' weaknesses and client lists

Each tool crafts multiple precision queries, deduplicates results,
and returns actionable intelligence — not just links.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional

from duckduckgo_search import DDGS

logger = logging.getLogger("openclaw.skills.dorking")

# Rate limit: max concurrent searches
_SEARCH_DELAY = 1.5  # seconds between queries to avoid rate limits


async def _multi_search(queries: List[str], max_per_query: int = 5) -> List[dict]:
    """Execute multiple search queries with deduplication and rate limiting."""
    all_results = []
    seen_urls = set()

    for q in queries:
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(q, max_results=max_per_query):
                    url = r.get("href", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append({
                            "title": r.get("title", ""),
                            "url": url,
                            "snippet": r.get("body", ""),
                            "query": q,
                        })
        except Exception as e:
            logger.debug("Search failed for '%s': %s", q[:50], e)

        await asyncio.sleep(_SEARCH_DELAY)

    return all_results


def _format_results(results: List[dict], header: str, max_show: int = 15) -> str:
    """Format search results into readable output."""
    if not results:
        return "%s\n\nNo results found." % header

    lines = ["%s\n\nFound %d results:\n" % (header, len(results))]
    for i, r in enumerate(results[:max_show], 1):
        lines.append("%d. **%s**\n   %s\n   %s\n" % (
            i, r["title"][:80], r["url"], r["snippet"][:150],
        ))

    if len(results) > max_show:
        lines.append("... and %d more results." % (len(results) - max_show))

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
# TOOL 1: Find decision makers and emails at a target company
# ══════════════════════════════════════════════════════════════

async def find_contacts(params: Dict[str, Any]) -> Dict:
    """Find decision makers, emails, and contact info for a target company.

    Uses advanced search operators to find:
    - LinkedIn profiles of key people (CMO, Head of Marketing, Creative Director)
    - Email patterns from the company domain
    - Contact pages and forms
    - Team/about pages with names
    """
    company = params.get("company", "")
    domain = params.get("domain", "")
    roles = params.get("roles", "CMO,Head of Marketing,Creative Director,VP Marketing,Brand Manager")

    if not company:
        return {"success": False, "data": None, "message": "Need company name"}

    role_list = [r.strip() for r in roles.split(",")]

    queries = []

    # LinkedIn profiles of key decision makers
    for role in role_list[:3]:
        queries.append('site:linkedin.com/in "%s" "%s"' % (role, company))

    # Email pattern discovery
    if domain:
        queries.append('"%s" email OR contact OR mailto' % domain)
        queries.append('"@%s" -site:%s' % (domain, domain))  # emails leaked elsewhere
    else:
        queries.append('"%s" email contact "head of" OR "director" OR "manager"' % company)

    # Company team/about pages
    if domain:
        queries.append('site:%s about OR team OR leadership OR contact' % domain)
    else:
        queries.append('"%s" team OR about OR leadership site:linkedin.com OR site:crunchbase.com' % company)

    # Press releases and mentions with people names
    queries.append('"%s" "said" OR "announced" OR "appointed" OR "hired" CMO OR "head of marketing"' % company)

    results = await _multi_search(queries, max_per_query=5)

    # Categorize results
    linkedin = [r for r in results if "linkedin.com" in r["url"]]
    emails_found = []
    contacts = [r for r in results if "linkedin.com" not in r["url"]]

    # Extract email patterns from snippets
    email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    for r in results:
        found = email_pattern.findall(r["snippet"])
        for e in found:
            if e not in emails_found and "example.com" not in e and "sentry" not in e:
                emails_found.append(e)

    data = {
        "company": company,
        "linkedin_profiles": linkedin,
        "emails_found": emails_found[:10],
        "contact_pages": contacts,
        "total_results": len(results),
    }

    lines = ["**Contact Intelligence: %s**\n" % company]

    if linkedin:
        lines.append("**Decision Makers (LinkedIn):**")
        for r in linkedin[:5]:
            lines.append("  - %s — %s" % (r["title"][:70], r["url"]))
        lines.append("")

    if emails_found:
        lines.append("**Emails Found:**")
        for e in emails_found[:5]:
            lines.append("  - %s" % e)
        lines.append("")

    if contacts:
        lines.append("**Contact Pages:**")
        for r in contacts[:5]:
            lines.append("  - %s — %s" % (r["title"][:60], r["url"]))

    if not linkedin and not emails_found and not contacts:
        lines.append("No contacts found. Try with the company domain for better results.")

    return {"success": True, "data": data, "message": "\n".join(lines)}


# ══════════════════════════════════════════════════════════════
# TOOL 2: Find companies with specific pain points
# ══════════════════════════════════════════════════════════════

async def find_pain_signals(params: Dict[str, Any]) -> Dict:
    """Find companies actively experiencing pain points that Bluewave solves.

    Searches for:
    - Job postings for roles that signal content/brand pain
    - Complaints and frustrations on forums
    - RFPs and procurement requests
    - Companies posting about tool fatigue, content bottlenecks, brand inconsistency
    """
    pain = params.get("pain", "content operations bottleneck")
    industry = params.get("industry", "")
    location = params.get("location", "")

    loc_suffix = " %s" % location if location else ""
    ind_prefix = '"%s" ' % industry if industry else ""

    queries = [
        # Job postings that signal pain
        '%s"hiring" OR "job" "%s"%s site:linkedin.com OR site:indeed.com OR site:glassdoor.com' % (ind_prefix, pain, loc_suffix),
        '%s"looking for" OR "seeking" "%s" OR "content manager" OR "brand manager"%s' % (ind_prefix, pain, loc_suffix),

        # Complaints and frustrations
        '%s"%s" "frustrated" OR "struggling" OR "bottleneck" OR "chaos" OR "nightmare"%s' % (ind_prefix, pain, loc_suffix),
        '%s"%s" site:reddit.com OR site:twitter.com' % (ind_prefix, pain),

        # RFPs and procurement
        '%s"RFP" OR "request for proposal" "%s"%s' % (ind_prefix, pain, loc_suffix),
        '%s"looking for a tool" OR "need a solution" OR "recommend" "%s"' % (ind_prefix, pain),

        # Tool fatigue / switching signals
        '%s"switching from" OR "alternative to" OR "replacing" brand OR content OR DAM%s' % (ind_prefix, loc_suffix),

        # Budget signals
        '%s"budget for" OR "investing in" content OR brand OR creative operations%s 2026' % (ind_prefix, loc_suffix),
    ]

    results = await _multi_search(queries, max_per_query=5)

    # Score results by pain signal strength
    pain_keywords = ["frustrated", "bottleneck", "struggling", "chaos", "nightmare", "hiring",
                     "looking for", "need", "rfp", "budget", "switching", "replacing"]
    for r in results:
        snippet_lower = r["snippet"].lower()
        r["pain_score"] = sum(1 for kw in pain_keywords if kw in snippet_lower)

    results.sort(key=lambda r: r["pain_score"], reverse=True)

    return {
        "success": True,
        "data": results,
        "message": _format_results(results, "**Pain Signal Scan: '%s'%s**" % (pain, loc_suffix)),
    }


# ══════════════════════════════════════════════════════════════
# TOOL 3: Find freelance opportunities and gigs
# ══════════════════════════════════════════════════════════════

async def find_gigs(params: Dict[str, Any]) -> Dict:
    """Find freelance gigs, job posts, and opportunities across the internet.

    Searches: Reddit (r/forhire, r/slavelabour, r/freelance), Upwork, Fiverr,
    IndieHackers, Hacker News, Contra, Toptal, and general forums.
    """
    service_type = params.get("service", "SEO audit OR competitor analysis OR brand audit OR content strategy")
    budget_min = params.get("budget_min", "")

    budget_filter = ' "$%s" OR "budget"' % budget_min if budget_min else ""

    queries = [
        # Reddit opportunities
        'site:reddit.com/r/forhire OR site:reddit.com/r/slavelabour "%s"' % service_type,
        'site:reddit.com "hiring" OR "looking for" "%s" 2026' % service_type,
        'site:reddit.com/r/entrepreneur OR site:reddit.com/r/smallbusiness "need help" "%s"' % service_type,

        # Freelance platforms
        '"looking for" "%s" site:upwork.com OR site:contra.com OR site:toptal.com' % service_type,

        # Indie/startup communities
        'site:indiehackers.com "%s" OR "need help with" branding OR content OR SEO' % service_type,
        'site:news.ycombinator.com "Ask HN" "%s" OR "who is hiring" 2026' % service_type,

        # General opportunity scan
        '"need" OR "looking for" OR "hire" "%s" -site:linkedin.com%s' % (service_type, budget_filter),

        # AI agent specific opportunities
        '"AI agent" OR "autonomous agent" "hire" OR "services" OR "marketplace" 2026',

        # Forums and communities
        '"can someone" OR "anyone know" "%s" site:quora.com OR site:stackexchange.com' % service_type,
    ]

    results = await _multi_search(queries, max_per_query=5)

    # Prioritize fresh opportunities
    freshness_keywords = ["2026", "today", "just posted", "new", "urgent", "asap"]
    for r in results:
        snippet_lower = r["snippet"].lower()
        r["freshness"] = sum(1 for kw in freshness_keywords if kw in snippet_lower)

    results.sort(key=lambda r: r["freshness"], reverse=True)

    return {
        "success": True,
        "data": results,
        "message": _format_results(results, "**Gig Opportunities: '%s'**" % service_type),
    }


# ══════════════════════════════════════════════════════════════
# TOOL 4: Competitive intelligence dorking
# ══════════════════════════════════════════════════════════════

async def dork_competitor(params: Dict[str, Any]) -> Dict:
    """Deep competitive intelligence on a specific company.

    Finds: pricing pages, client lists, employee reviews, tech stack,
    complaints, legal issues, funding info, and weaknesses.
    """
    company = params.get("company", "")
    domain = params.get("domain", "")

    if not company:
        return {"success": False, "data": None, "message": "Need company name"}

    site_filter = "site:%s" % domain if domain else '"%s"' % company

    queries = [
        # Pricing and revenue
        '%s pricing OR plans OR "per month" OR "per user"' % site_filter,
        '"%s" pricing OR "how much" OR cost -site:%s' % (company, domain) if domain else '"%s" pricing review' % company,

        # Client list / case studies
        '%s customers OR clients OR "case study" OR testimonial' % site_filter,
        '"%s" "we use" OR "switched to" OR "moved to" -site:%s' % (company, domain) if domain else '"%s" "we use" review' % company,

        # Weaknesses and complaints
        '"%s" "doesn\'t" OR "can\'t" OR "missing" OR "limitation" OR "wish" site:g2.com OR site:capterra.com' % company,
        '"%s" complaint OR problem OR issue OR bug site:reddit.com OR site:twitter.com' % company,

        # Tech stack
        '%s "built with" OR "powered by" OR "uses" OR "stack"' % site_filter if domain else '"%s" tech stack' % company,

        # Employee insights
        '"%s" review site:glassdoor.com OR site:indeed.com' % company,

        # Funding and financials
        '"%s" "raised" OR "funding" OR "valuation" OR "revenue" site:crunchbase.com OR site:techcrunch.com' % company,
    ]

    results = await _multi_search(queries, max_per_query=4)

    # Categorize
    categories = {
        "pricing": [], "clients": [], "weaknesses": [],
        "tech": [], "employees": [], "funding": [], "other": [],
    }

    for r in results:
        s = r["snippet"].lower()
        if any(w in s for w in ["pricing", "plan", "per month", "cost", "$"]):
            categories["pricing"].append(r)
        elif any(w in s for w in ["client", "customer", "case study", "testimonial", "we use"]):
            categories["clients"].append(r)
        elif any(w in s for w in ["complaint", "issue", "problem", "limitation", "doesn't", "can't", "wish"]):
            categories["weaknesses"].append(r)
        elif any(w in s for w in ["raised", "funding", "valuation", "revenue", "series"]):
            categories["funding"].append(r)
        elif any(w in s for w in ["glassdoor", "review", "culture", "salary"]):
            categories["employees"].append(r)
        elif any(w in s for w in ["stack", "built with", "uses", "api"]):
            categories["tech"].append(r)
        else:
            categories["other"].append(r)

    lines = ["**Competitive Intel: %s**\n" % company]
    for cat_name, cat_results in categories.items():
        if cat_results:
            lines.append("**%s** (%d)" % (cat_name.upper(), len(cat_results)))
            for r in cat_results[:3]:
                lines.append("  - %s\n    %s" % (r["title"][:60], r["snippet"][:120]))
            lines.append("")

    return {
        "success": True,
        "data": {"company": company, "categories": {k: v for k, v in categories.items() if v}},
        "message": "\n".join(lines),
    }


# ══════════════════════════════════════════════════════════════
# TOOL 5: Custom dork — the power user tool
# ══════════════════════════════════════════════════════════════

async def custom_dork(params: Dict[str, Any]) -> Dict:
    """Execute custom Google dork queries. For the power user.

    Supports all advanced operators:
    - site:example.com — restrict to domain
    - intitle:"keyword" — in page title
    - inurl:keyword — in URL
    - filetype:pdf — specific file types
    - "exact phrase" — exact match
    - OR, AND, - (exclude)
    - after:2026-01-01 — date filter

    Pass a single query or a list of queries (semicolon-separated).
    """
    query = params.get("query", "")
    max_results = min(params.get("max_results", 10), 20)

    if not query:
        return {"success": False, "data": None, "message": "Need a query"}

    # Support multiple queries separated by semicolons
    queries = [q.strip() for q in query.split(";") if q.strip()]

    results = await _multi_search(queries, max_per_query=max_results)

    return {
        "success": True,
        "data": results,
        "message": _format_results(results, "**Dork Results (%d queries):**" % len(queries)),
    }


# ══════════════════════════════════════════════════════════════
# TOOL 6: Find market gaps and untapped niches
# ══════════════════════════════════════════════════════════════

async def find_market_gaps(params: Dict[str, Any]) -> Dict:
    """Find underserved markets and untapped niches through search intelligence.

    Identifies:
    - Questions people ask that nobody answers well
    - Services people request that don't exist yet
    - Complaints about existing solutions with no alternatives
    - Emerging trends with low competition
    """
    topic = params.get("topic", "AI creative operations")
    niche = params.get("niche", "")

    niche_prefix = '"%s" ' % niche if niche else ""

    queries = [
        # Unmet demand
        '%s"is there a tool" OR "does anyone know" OR "looking for" "%s"' % (niche_prefix, topic),
        '%s"I wish" OR "if only" OR "why isn\'t there" "%s"' % (niche_prefix, topic),
        '%s"no good solution" OR "nothing works" OR "all suck" "%s"' % (niche_prefix, topic),

        # Forum complaints
        '%s"%s" "alternative" OR "replacement" site:reddit.com' % (niche_prefix, topic),
        '%s"%s" "frustrated" OR "gave up" OR "stopped using" site:reddit.com OR site:twitter.com' % (niche_prefix, topic),

        # Emerging demand
        '%s"%s" "growing" OR "emerging" OR "trend" OR "market size" 2026' % (niche_prefix, topic),
        '%s"%s" "market gap" OR "underserved" OR "opportunity"' % (niche_prefix, topic),

        # People willing to pay
        '%s"would pay for" OR "take my money" OR "willing to pay" "%s"' % (niche_prefix, topic),

        # Startup ideas and validations
        '%s"%s" "startup idea" OR "business idea" OR "validate" site:indiehackers.com OR site:reddit.com/r/startups' % (niche_prefix, topic),
    ]

    results = await _multi_search(queries, max_per_query=5)

    # Score by opportunity strength
    opp_keywords = ["wish", "looking for", "no good", "would pay", "gap", "underserved",
                    "nothing works", "frustrated", "need", "alternative"]
    for r in results:
        snippet_lower = r["snippet"].lower()
        r["opportunity_score"] = sum(1 for kw in opp_keywords if kw in snippet_lower)

    results.sort(key=lambda r: r["opportunity_score"], reverse=True)

    return {
        "success": True,
        "data": results,
        "message": _format_results(results, "**Market Gap Analysis: '%s'**" % topic),
    }


TOOLS = [
    {
        "name": "dork_contacts",
        "description": "OSINT: Find decision makers, emails, and contact info for a target company. Searches LinkedIn, company sites, press releases. Returns categorized contacts with email patterns discovered.",
        "handler": find_contacts,
        "parameters": {
            "type": "object",
            "properties": {
                "company": {"type": "string", "description": "Target company name"},
                "domain": {"type": "string", "description": "Company domain (e.g. 'acme.com') for deeper results"},
                "roles": {"type": "string", "default": "CMO,Head of Marketing,Creative Director,VP Marketing,Brand Manager",
                          "description": "Comma-separated target roles"},
            },
            "required": ["company"],
        },
    },
    {
        "name": "dork_pain_signals",
        "description": "Find companies actively experiencing pain points you can solve. Searches job postings, complaints, RFPs, tool-switching signals, and budget announcements. Returns results scored by pain signal strength.",
        "handler": find_pain_signals,
        "parameters": {
            "type": "object",
            "properties": {
                "pain": {"type": "string", "default": "content operations bottleneck",
                         "description": "Pain point to search for"},
                "industry": {"type": "string", "description": "Target industry (marketing agency, ecommerce, etc)"},
                "location": {"type": "string", "description": "Geographic focus (US, Brazil, Europe)"},
            },
        },
    },
    {
        "name": "dork_gigs",
        "description": "Find freelance gigs and opportunities across the internet. Searches Reddit (r/forhire, r/slavelabour, r/entrepreneur), Upwork, IndieHackers, Hacker News, Contra, and forums. Returns results sorted by freshness.",
        "handler": find_gigs,
        "parameters": {
            "type": "object",
            "properties": {
                "service": {"type": "string", "default": "SEO audit OR competitor analysis OR brand audit",
                            "description": "Service type to search for gigs"},
                "budget_min": {"type": "string", "description": "Minimum budget filter (e.g. '50', '100')"},
            },
        },
    },
    {
        "name": "dork_competitor",
        "description": "Deep competitive intelligence via search dorking. Finds pricing, client lists, weaknesses (complaints/limitations), tech stack, employee reviews, and funding info. Categorizes results automatically.",
        "handler": dork_competitor,
        "parameters": {
            "type": "object",
            "properties": {
                "company": {"type": "string", "description": "Competitor company name"},
                "domain": {"type": "string", "description": "Competitor domain for site-specific searches"},
            },
            "required": ["company"],
        },
    },
    {
        "name": "dork_custom",
        "description": "Execute custom Google dork queries. Supports all operators: site:, intitle:, inurl:, filetype:, \"exact\", OR, AND, -exclude. Pass multiple queries separated by semicolons.",
        "handler": custom_dork,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Dork query (or multiple semicolon-separated queries)"},
                "max_results": {"type": "integer", "default": 10, "description": "Max results per query"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "dork_market_gaps",
        "description": "Find underserved markets and untapped niches. Searches for unmet demand ('I wish', 'no good solution'), complaints without alternatives, emerging trends, and people willing to pay. Returns results scored by opportunity strength.",
        "handler": find_market_gaps,
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "default": "AI creative operations",
                          "description": "Topic or market to analyze for gaps"},
                "niche": {"type": "string", "description": "Specific niche within the topic"},
            },
        },
    },
]
