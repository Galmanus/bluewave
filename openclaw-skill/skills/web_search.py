"""Web Search & Scraping — the agent's eyes on the internet.

Multi-engine: DDG → Brave → Tavily fallback chain.
If DDG is rate-limited, automatically falls back to Brave or Tavily.
"""

from __future__ import annotations
import logging
import os
import json
from typing import Any, Dict, List

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger("openclaw.web_search")

BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY", "")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")


async def _ddg_search(query: str, max_results: int = 5, region: str = "wt-wt") -> list:
    """Try DuckDuckGo first (no API key needed)."""
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, region=region, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })
        return results
    except Exception as e:
        logger.debug("DDG failed: %s", e)
        return []


async def _brave_search(query: str, max_results: int = 5) -> list:
    """Fallback to Brave Search API."""
    if not BRAVE_API_KEY:
        return []
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get("https://api.search.brave.com/res/v1/web/search",
                                 params={"q": query, "count": max_results},
                                 headers={"X-Subscription-Token": BRAVE_API_KEY, "Accept": "application/json"})
            data = r.json()
        return [{"title": i.get("title", ""), "url": i.get("url", ""), "snippet": i.get("description", "")}
                for i in data.get("web", {}).get("results", [])[:max_results]]
    except Exception as e:
        logger.debug("Brave failed: %s", e)
        return []


async def _tavily_search(query: str, max_results: int = 5) -> list:
    """Fallback to Tavily Search API."""
    if not TAVILY_API_KEY:
        return []
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post("https://api.tavily.com/search", json={
                "api_key": TAVILY_API_KEY, "query": query,
                "max_results": max_results, "include_answer": False,
            })
            data = r.json()
        return [{"title": i.get("title", ""), "url": i.get("url", ""), "snippet": i.get("content", "")[:200]}
                for i in data.get("results", [])[:max_results]]
    except Exception as e:
        logger.debug("Tavily failed: %s", e)
        return []


async def web_search(params: Dict[str, Any]) -> Dict:
    """Search the web. Auto-fallback: DDG → Brave → Tavily."""
    query = params.get("query", "")
    max_results = min(int(params.get("max_results", 5)), 10)
    region = params.get("region", "wt-wt")

    if not query:
        return {"success": False, "data": None, "message": "Need a search query"}

    # Try engines in order
    engine = "ddg"
    results = await _ddg_search(query, max_results, region)

    if not results:
        engine = "brave"
        results = await _brave_search(query, max_results)

    if not results:
        engine = "tavily"
        results = await _tavily_search(query, max_results)

    if not results:
        return {"success": False, "data": [], "message": f"All search engines failed for '{query}'. DDG rate-limited, Brave/Tavily not configured."}

    lines = [f"**[{engine}] Results for '{query}':**\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. **{r['title']}**\n   {r['url']}\n   {r['snippet'][:150]}\n")

    return {"success": True, "data": results, "message": "\n".join(lines)}


async def web_news(params: Dict[str, Any]) -> Dict:
    """Search news. Auto-fallback: DDG → Brave."""
    query = params.get("query", "")
    max_results = min(int(params.get("max_results", 5)), 10)

    if not query:
        return {"success": False, "data": None, "message": "Need a search query"}

    # Try DDG news
    results = []
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            for r in ddgs.news(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "source": r.get("source", ""),
                    "date": r.get("date", ""),
                    "snippet": r.get("body", ""),
                })
    except Exception:
        pass

    # Fallback to Brave news
    if not results and BRAVE_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get("https://api.search.brave.com/res/v1/news/search",
                                     params={"q": query, "count": max_results},
                                     headers={"X-Subscription-Token": BRAVE_API_KEY, "Accept": "application/json"})
                data = r.json()
            results = [{"title": i.get("title", ""), "url": i.get("url", ""),
                        "source": i.get("meta_url", {}).get("hostname", ""), "date": i.get("age", ""),
                        "snippet": i.get("description", "")}
                       for i in data.get("results", [])[:max_results]]
        except Exception:
            pass

    if not results:
        return {"success": False, "data": [], "message": f"No news found for '{query}'"}

    lines = [f"**News for '{query}':**\n"]
    for r in results:
        lines.append(f"- **{r['title']}** ({r.get('source', '')}, {str(r.get('date', ''))[:10]})\n  {r['snippet'][:120]}\n")

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
