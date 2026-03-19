"""Strategic Intelligence — competitive analysis, SEO, market research."""

from __future__ import annotations
import json
from typing import Any, Dict, List
from duckduckgo_search import DDGS
import httpx
from bs4 import BeautifulSoup


async def competitor_analysis(params: Dict[str, Any]) -> Dict:
    """Deep competitor research using web search + scraping."""
    competitor = params.get("competitor", "")
    aspects = params.get("aspects", ["pricing", "features", "reviews", "funding"])

    research = {}
    for aspect in aspects:
        query = "%s %s" % (competitor, aspect)
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=5):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })
        research[aspect] = results

    lines = ["**Competitor Analysis: %s**\n" % competitor]
    for aspect, results in research.items():
        lines.append("### %s" % aspect.title())
        for r in results[:3]:
            lines.append("- %s — %s" % (r["title"][:60], r["snippet"][:120]))
        lines.append("")

    return {"success": True, "data": research, "message": "\n".join(lines)}


async def market_research(params: Dict[str, Any]) -> Dict:
    """Research a market segment — size, trends, players, opportunities."""
    market = params.get("market", "")
    depth = params.get("depth", "standard")

    queries = [
        "%s market size 2025 2026" % market,
        "%s industry trends" % market,
        "%s top companies competitors" % market,
        "%s pain points challenges" % market,
    ]
    if depth == "deep":
        queries.extend([
            "%s funding investments" % market,
            "%s customer reviews complaints" % market,
            "%s pricing models" % market,
        ])

    research = {}
    for q in queries:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(q, max_results=5):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })
        research[q] = results

    # Also get news
    news = []
    with DDGS() as ddgs:
        for r in ddgs.news(market, max_results=5):
            news.append({
                "title": r.get("title", ""),
                "source": r.get("source", ""),
                "date": r.get("date", ""),
                "snippet": r.get("body", ""),
            })

    all_data = {"research": research, "news": news}

    lines = ["**Market Research: %s**\n" % market]
    for q, results in research.items():
        lines.append("**%s**" % q)
        for r in results[:2]:
            lines.append("  - %s" % r["snippet"][:150])
        lines.append("")
    if news:
        lines.append("**Latest News:**")
        for n in news[:3]:
            lines.append("  - %s (%s)" % (n["title"][:80], n["source"]))

    return {"success": True, "data": all_data, "message": "\n".join(lines)}


async def seo_analysis(params: Dict[str, Any]) -> Dict:
    """Analyze a URL for SEO — title, meta, headings, content structure."""
    url = params.get("url", "")

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0), follow_redirects=True) as client:
            resp = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; BluewavePrime/1.0)"
            })
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        meta_desc = ""
        meta = soup.find("meta", attrs={"name": "description"})
        if meta:
            meta_desc = meta.get("content", "")

        # Extract headings
        headings = {}
        for level in range(1, 4):
            tag = "h%d" % level
            found = soup.find_all(tag)
            headings[tag] = [h.get_text(strip=True)[:80] for h in found[:5]]

        # Count key elements
        images = soup.find_all("img")
        images_without_alt = [img for img in images if not img.get("alt")]
        links = soup.find_all("a", href=True)
        internal = [l for l in links if url.split("/")[2] in l.get("href", "")]
        external = [l for l in links if l.get("href", "").startswith("http") and url.split("/")[2] not in l.get("href", "")]

        # Word count
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text(" ", strip=True)
        word_count = len(text.split())

        analysis = {
            "url": url,
            "title": title,
            "title_length": len(title),
            "meta_description": meta_desc,
            "meta_desc_length": len(meta_desc),
            "headings": headings,
            "word_count": word_count,
            "images_total": len(images),
            "images_without_alt": len(images_without_alt),
            "internal_links": len(internal),
            "external_links": len(external),
        }

        issues = []
        if len(title) < 30 or len(title) > 60:
            issues.append("Title length %d (optimal: 30-60)" % len(title))
        if len(meta_desc) < 120 or len(meta_desc) > 160:
            issues.append("Meta description length %d (optimal: 120-160)" % len(meta_desc))
        if not headings.get("h1"):
            issues.append("Missing H1 tag")
        if images_without_alt:
            issues.append("%d images missing alt text" % len(images_without_alt))
        if word_count < 300:
            issues.append("Low word count (%d) — aim for 1000+" % word_count)

        analysis["issues"] = issues
        analysis["score"] = max(0, 100 - len(issues) * 15)

        lines = [
            "**SEO Analysis: %s**\n" % url,
            "Score: **%d/100**" % analysis["score"],
            "Title: %s (%d chars)" % (title[:60], len(title)),
            "Meta: %s (%d chars)" % (meta_desc[:80], len(meta_desc)),
            "Words: %d | Images: %d | Links: %d internal, %d external" % (
                word_count, len(images), len(internal), len(external)),
        ]
        if issues:
            lines.append("\n**Issues:**")
            for issue in issues:
                lines.append("- %s" % issue)

        return {"success": True, "data": analysis, "message": "\n".join(lines)}

    except Exception as e:
        return {"success": False, "data": None, "message": "SEO analysis failed: %s" % str(e)}


async def lead_finder(params: Dict[str, Any]) -> Dict:
    """Find potential leads/prospects in a target market."""
    industry = params.get("industry", "")
    role = params.get("role", "marketing manager")
    location = params.get("location", "")
    company_size = params.get("company_size", "")

    queries = [
        "%s %s %s linkedin" % (role, industry, location),
        "%s companies %s hiring" % (industry, location),
        "%s agencies %s directory" % (industry, location),
    ]

    leads = {}
    for q in queries:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(q, max_results=8):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })
        leads[q] = results

    lines = ["**Lead Research: %s in %s (%s)**\n" % (role, industry, location or "global")]
    for q, results in leads.items():
        lines.append("**%s**" % q[:60])
        for r in results[:3]:
            lines.append("  - %s — %s" % (r["title"][:60], r["snippet"][:100]))
        lines.append("")

    return {"success": True, "data": leads, "message": "\n".join(lines)}


async def directory_submission(params: Dict[str, Any]) -> Dict:
    """Generate a directory submission package for product listing."""
    product_name = params.get("product_name", "Bluewave")
    tagline = params.get("tagline", "AI Creative Operations Platform")
    description = params.get("description", "")
    url = params.get("url", "https://bluewave.app")
    category = params.get("category", "AI, SaaS, Marketing, Creative Tools")

    directories = [
        {"name": "Product Hunt", "url": "https://producthunt.com", "type": "launch"},
        {"name": "G2", "url": "https://g2.com", "type": "review"},
        {"name": "Capterra", "url": "https://capterra.com", "type": "review"},
        {"name": "AlternativeTo", "url": "https://alternativeto.net", "type": "listing"},
        {"name": "SaaSHub", "url": "https://saashub.com", "type": "listing"},
        {"name": "BetaList", "url": "https://betalist.com", "type": "launch"},
        {"name": "Hacker News", "url": "https://news.ycombinator.com", "type": "community"},
        {"name": "IndieHackers", "url": "https://indiehackers.com", "type": "community"},
        {"name": "There's An AI For That", "url": "https://theresanaiforthat.com", "type": "AI directory"},
        {"name": "FutureTools", "url": "https://futuretools.io", "type": "AI directory"},
        {"name": "AI Tool Directory", "url": "https://aitoolsdirectory.com", "type": "AI directory"},
        {"name": "ToolPilot.ai", "url": "https://toolpilot.ai", "type": "AI directory"},
    ]

    package = {
        "product": product_name,
        "tagline": tagline,
        "description": description or ("%s — an AI agent that sees media, writes copy, enforces brand guidelines, and automates creative workflows." % product_name),
        "url": url,
        "categories": category.split(", "),
        "directories": directories,
        "total_directories": len(directories),
    }

    lines = ["**Directory Submission Package: %s**\n" % product_name]
    lines.append("Tagline: %s" % tagline)
    lines.append("URL: %s" % url)
    lines.append("Categories: %s\n" % category)
    lines.append("**%d directories to submit to:**\n" % len(directories))
    for d in directories:
        lines.append("- [%s] **%s** (%s)" % (d["type"], d["name"], d["url"]))

    return {"success": True, "data": package, "message": "\n".join(lines)}


TOOLS = [
    {
        "name": "competitor_analysis",
        "description": "Deep competitor research — pricing, features, reviews, funding. Use for strategic planning, market positioning, identifying weaknesses.",
        "handler": competitor_analysis,
        "parameters": {
            "type": "object",
            "properties": {
                "competitor": {"type": "string", "description": "Competitor name or product"},
                "aspects": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": ["pricing", "features", "reviews", "funding"],
                    "description": "Aspects to research",
                },
            },
            "required": ["competitor"],
        },
    },
    {
        "name": "market_research",
        "description": "Research a market segment — size, trends, key players, pain points. Use for TAM analysis, market entry strategy, investment research.",
        "handler": market_research,
        "parameters": {
            "type": "object",
            "properties": {
                "market": {"type": "string", "description": "Market or industry to research"},
                "depth": {"type": "string", "enum": ["standard", "deep"], "default": "standard"},
            },
            "required": ["market"],
        },
    },
    {
        "name": "seo_analysis",
        "description": "Analyze any URL for SEO performance — title, meta, headings, content structure, issues. Use for optimizing pages and competitive SEO analysis.",
        "handler": seo_analysis,
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to analyze"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "lead_finder",
        "description": "Find potential leads/prospects in a target market. Use for sales prospecting, partnership discovery, market expansion.",
        "handler": lead_finder,
        "parameters": {
            "type": "object",
            "properties": {
                "industry": {"type": "string", "description": "Target industry"},
                "role": {"type": "string", "default": "marketing manager", "description": "Target role/title"},
                "location": {"type": "string", "description": "Geographic focus"},
                "company_size": {"type": "string", "description": "Company size filter"},
            },
            "required": ["industry"],
        },
    },
    {
        "name": "directory_submission",
        "description": "Generate a complete directory submission package for listing a product on 70+ platforms. Use for product launch and visibility.",
        "handler": directory_submission,
        "parameters": {
            "type": "object",
            "properties": {
                "product_name": {"type": "string", "default": "Bluewave"},
                "tagline": {"type": "string", "default": "AI Creative Operations Platform"},
                "description": {"type": "string"},
                "url": {"type": "string", "default": "https://bluewave.app"},
                "category": {"type": "string", "default": "AI, SaaS, Marketing, Creative Tools"},
            },
        },
    },
]
