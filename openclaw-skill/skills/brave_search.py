"""
Brave Search API — rate-limit-free web search for Wave.

Replaces DuckDuckGo scraping which gets 202 rate limits.
Free tier: 2,000 queries/month.

Setup: BRAVE_API_KEY env var from https://brave.com/search/api/
"""

import logging
import os
from typing import Any, Dict

import httpx

logger = logging.getLogger("openclaw.brave_search")

BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY", "")
BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"


async def brave_search(params: Dict[str, Any]) -> Dict:
    """Search the web using Brave Search API. No rate limits."""
    query = params.get("query", "")
    count = min(int(params.get("count", 5)), 10)

    if not query:
        return {"success": False, "data": None, "message": "Need a search query"}

    if not BRAVE_API_KEY:
        return {"success": False, "data": None, "message": "BRAVE_API_KEY not configured. Get one free at brave.com/search/api"}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(BRAVE_URL, params={"q": query, "count": count}, headers={
                "X-Subscription-Token": BRAVE_API_KEY,
                "Accept": "application/json",
            })
            data = r.json()

        results = []
        for item in data.get("web", {}).get("results", [])[:count]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "description": item.get("description", ""),
            })

        return {
            "success": True,
            "data": {"query": query, "results": results, "count": len(results)},
            "message": f"{len(results)} results for '{query}'"
        }
    except Exception as e:
        logger.error("Brave search failed: %s", e)
        return {"success": False, "data": None, "message": str(e)}


async def brave_news(params: Dict[str, Any]) -> Dict:
    """Search news using Brave Search API."""
    query = params.get("query", "")
    count = min(int(params.get("count", 5)), 10)

    if not query:
        return {"success": False, "data": None, "message": "Need a search query"}

    if not BRAVE_API_KEY:
        return {"success": False, "data": None, "message": "BRAVE_API_KEY not configured"}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get("https://api.search.brave.com/res/v1/news/search",
                                 params={"q": query, "count": count},
                                 headers={"X-Subscription-Token": BRAVE_API_KEY, "Accept": "application/json"})
            data = r.json()

        results = []
        for item in data.get("results", [])[:count]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "description": item.get("description", ""),
                "age": item.get("age", ""),
            })

        return {
            "success": True,
            "data": {"query": query, "results": results},
            "message": f"{len(results)} news results for '{query}'"
        }
    except Exception as e:
        return {"success": False, "data": None, "message": str(e)}


TOOLS = [
    {
        "name": "brave_search",
        "description": "Search the web using Brave Search API. Fast, no rate limits. Use instead of web_search when DDG is blocked.",
        "parameters": {
            "query": "string — search query",
            "count": "int — number of results (default 5, max 10)",
        },
        "handler": brave_search,
    },
    {
        "name": "brave_news",
        "description": "Search recent news using Brave Search API.",
        "parameters": {
            "query": "string — news search query",
            "count": "int — number of results (default 5, max 10)",
        },
        "handler": brave_news,
    },
]
