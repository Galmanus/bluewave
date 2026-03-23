"""
Tavily Search — AI-optimized search engine for agents.

Built specifically for AI agents. Returns clean, structured results.
Free tier: 1,000 searches/month.

Setup: TAVILY_API_KEY env var from https://tavily.com/
"""

import logging
import os
from typing import Any, Dict

import httpx

logger = logging.getLogger("openclaw.tavily")

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
TAVILY_URL = "https://api.tavily.com/search"


async def tavily_search(params: Dict[str, Any]) -> Dict:
    """AI-optimized web search via Tavily. Best results for agent use."""
    query = params.get("query", "")
    search_depth = params.get("depth", "basic")  # basic or advanced
    max_results = min(int(params.get("max_results", 5)), 10)

    if not query:
        return {"success": False, "data": None, "message": "Need a search query"}

    if not TAVILY_API_KEY:
        return {"success": False, "data": None, "message": "TAVILY_API_KEY not configured. Get one free at tavily.com"}

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(TAVILY_URL, json={
                "api_key": TAVILY_API_KEY,
                "query": query,
                "search_depth": search_depth,
                "max_results": max_results,
                "include_answer": True,
            })
            data = r.json()

        results = []
        for item in data.get("results", [])[:max_results]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", "")[:200],
                "score": item.get("score", 0),
            })

        return {
            "success": True,
            "data": {
                "query": query,
                "answer": data.get("answer", ""),
                "results": results,
            },
            "message": f"{len(results)} results + AI answer for '{query}'"
        }
    except Exception as e:
        logger.error("Tavily search failed: %s", e)
        return {"success": False, "data": None, "message": str(e)}


TOOLS = [
    {
        "name": "tavily_search",
        "description": "AI-optimized web search via Tavily. Returns structured results + AI-generated answer. Better than DDG for agent use.",
        "parameters": {
            "query": "string — search query",
            "depth": "string — 'basic' (fast) or 'advanced' (thorough). Default: basic",
            "max_results": "int — number of results (default 5, max 10)",
        },
        "handler": tavily_search,
    },
]
