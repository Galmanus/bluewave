"""Web Search & Scraping — the agent's eyes on the internet."""

from __future__ import annotations
import json
from typing import Any, Dict, List
from duckduckgo_search import DDGS
import httpx
from bs4 import BeautifulSoup


async def web_search(params: Dict[str, Any]) -> Dict:
    """Search the web using DuckDuckGo. No API key needed."""
    query = params.get("query", "")
    max_results = params.get("max_results", 10)
    region = params.get("region", "wt-wt")

    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, region=region, max_results=max_results):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", ""),
            })

    if not results:
        return {"success": True, "data": [], "message": "No results found for '%s'" % query}

    lines = ["**Search results for '%s':**\n" % query]
    for i, r in enumerate(results, 1):
        lines.append("%d. **%s**\n   %s\n   %s\n" % (i, r["title"], r["url"], r["snippet"][:150]))

    return {"success": True, "data": results, "message": "\n".join(lines)}


async def web_news(params: Dict[str, Any]) -> Dict:
    """Search news using DuckDuckGo News."""
    query = params.get("query", "")
    max_results = params.get("max_results", 10)

    results = []
    with DDGS() as ddgs:
        for r in ddgs.news(query, max_results=max_results):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "source": r.get("source", ""),
                "date": r.get("date", ""),
                "snippet": r.get("body", ""),
            })

    if not results:
        return {"success": True, "data": [], "message": "No news found for '%s'" % query}

    lines = ["**News for '%s':**\n" % query]
    for r in results:
        lines.append("- **%s** (%s, %s)\n  %s\n" % (r["title"], r["source"], r["date"][:10] if r["date"] else "", r["snippet"][:120]))

    return {"success": True, "data": results, "message": "\n".join(lines)}


async def scrape_url(params: Dict[str, Any]) -> Dict:
    """Fetch and extract text content from a URL."""
    url = params.get("url", "")
    max_chars = params.get("max_chars", 5000)

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0), follow_redirects=True) as client:
            resp = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; BluewavePrime/1.0)"
            })
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove script/style
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        title = soup.title.string if soup.title else ""
        text = soup.get_text(separator="\n", strip=True)[:max_chars]

        # Extract meta description
        meta_desc = ""
        meta = soup.find("meta", attrs={"name": "description"})
        if meta:
            meta_desc = meta.get("content", "")

        return {
            "success": True,
            "data": {"title": title, "meta_description": meta_desc, "text": text, "url": url},
            "message": "**%s**\n%s\n\n%s" % (title, meta_desc, text[:2000]),
        }
    except Exception as e:
        return {"success": False, "data": None, "message": "Failed to scrape %s: %s" % (url, str(e))}


async def google_trends(params: Dict[str, Any]) -> Dict:
    """Get trending topics from DuckDuckGo suggestions."""
    query = params.get("query", "trending")

    suggestions = []
    with DDGS() as ddgs:
        for r in ddgs.suggestions(query):
            suggestions.append(r.get("phrase", ""))

    return {
        "success": True,
        "data": suggestions,
        "message": "**Trending suggestions for '%s':**\n%s" % (query, "\n".join("- %s" % s for s in suggestions)),
    }


# Tool definitions for registration
TOOLS = [
    {
        "name": "web_search",
        "description": "Search the web using DuckDuckGo. Returns titles, URLs and snippets. Use for research, competitive intelligence, market analysis, finding information about anything.",
        "handler": web_search,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "default": 10, "description": "Max results (1-25)"},
                "region": {"type": "string", "default": "wt-wt", "description": "Region code (wt-wt=worldwide, us-en, br-pt, etc)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "web_news",
        "description": "Search latest news articles. Use for monitoring trends, competitor news, industry updates, market intelligence.",
        "handler": web_news,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "News search query"},
                "max_results": {"type": "integer", "default": 10, "description": "Max results"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "scrape_url",
        "description": "Fetch and extract text content from any URL. Use for reading articles, analyzing competitor pages, extracting data from websites.",
        "handler": scrape_url,
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to scrape"},
                "max_chars": {"type": "integer", "default": 5000, "description": "Max characters to extract"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "google_trends",
        "description": "Get trending search suggestions and related topics. Use for identifying market trends and content opportunities.",
        "handler": google_trends,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Topic to explore trends for"},
            },
            "required": ["query"],
        },
    },
]
