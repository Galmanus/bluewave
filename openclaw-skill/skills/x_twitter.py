"""X/Twitter — search, monitor, and analyze tweets without API keys."""

from __future__ import annotations
import json
import re
from typing import Any, Dict
from duckduckgo_search import DDGS
import httpx
from bs4 import BeautifulSoup


async def x_search(params: Dict[str, Any]) -> Dict:
    """Search X/Twitter posts via web search. No API key needed."""
    query = params.get("query", "")
    max_results = params.get("max_results", 10)

    # Use DuckDuckGo to search Twitter
    search_query = "site:x.com OR site:twitter.com %s" % query
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(search_query, max_results=max_results):
            url = r.get("href", "")
            if "x.com" in url or "twitter.com" in url:
                results.append({
                    "title": r.get("title", ""),
                    "url": url,
                    "snippet": r.get("body", ""),
                })

    if not results:
        return {"success": True, "data": [], "message": "No tweets found for '%s'" % query}

    lines = ["**X/Twitter results for '%s':**\n" % query]
    for r in results:
        lines.append("- **%s**\n  %s\n  %s\n" % (r["title"][:80], r["url"], r["snippet"][:150]))

    return {"success": True, "data": results, "message": "\n".join(lines)}


async def x_trending(params: Dict[str, Any]) -> Dict:
    """Get trending topics on X/Twitter via web scraping."""
    region = params.get("region", "worldwide")

    search_query = "trending on twitter today %s" % region
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(search_query, max_results=10):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", ""),
            })

    news_results = []
    with DDGS() as ddgs:
        for r in ddgs.news("twitter trending %s" % region, max_results=5):
            news_results.append({
                "title": r.get("title", ""),
                "source": r.get("source", ""),
                "snippet": r.get("body", ""),
            })

    all_data = {"web_results": results, "news": news_results}

    lines = ["**Trending on X/Twitter (%s):**\n" % region]
    for r in results[:5]:
        lines.append("- %s — %s" % (r["title"][:80], r["snippet"][:100]))
    if news_results:
        lines.append("\n**Related news:**")
        for n in news_results[:3]:
            lines.append("- %s (%s)" % (n["title"][:80], n["source"]))

    return {"success": True, "data": all_data, "message": "\n".join(lines)}


async def x_profile_research(params: Dict[str, Any]) -> Dict:
    """Research an X/Twitter profile via web search."""
    username = params.get("username", "").lstrip("@")

    results = []
    with DDGS() as ddgs:
        for r in ddgs.text("site:x.com/%s OR site:twitter.com/%s" % (username, username), max_results=10):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", ""),
            })

    # Also search for mentions
    mentions = []
    with DDGS() as ddgs:
        for r in ddgs.text("@%s twitter" % username, max_results=5):
            mentions.append({
                "title": r.get("title", ""),
                "snippet": r.get("body", ""),
            })

    data = {"profile_results": results, "mentions": mentions}
    lines = ["**X/Twitter profile research: @%s**\n" % username]
    for r in results[:5]:
        lines.append("- %s\n  %s" % (r["title"][:80], r["snippet"][:120]))
    if mentions:
        lines.append("\n**Mentions:**")
        for m in mentions[:3]:
            lines.append("- %s" % m["snippet"][:120])

    return {"success": True, "data": data, "message": "\n".join(lines)}


async def social_monitor(params: Dict[str, Any]) -> Dict:
    """Monitor social media mentions of a brand/topic across platforms."""
    query = params.get("query", "")
    platforms = params.get("platforms", ["twitter", "reddit", "linkedin"])

    all_results = {}
    for platform in platforms:
        search = "site:%s.com %s" % (platform, query)
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(search, max_results=5):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })
        all_results[platform] = results

    lines = ["**Social monitoring for '%s':**\n" % query]
    for platform, results in all_results.items():
        lines.append("**%s** (%d mentions)" % (platform.title(), len(results)))
        for r in results[:3]:
            lines.append("  - %s" % r["snippet"][:120])
        lines.append("")

    return {"success": True, "data": all_results, "message": "\n".join(lines)}


TOOLS = [
    {
        "name": "x_search",
        "description": "Search X/Twitter posts and conversations. Use for market intelligence, brand monitoring, competitor analysis, trend discovery.",
        "handler": x_search,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query for X/Twitter"},
                "max_results": {"type": "integer", "default": 10},
            },
            "required": ["query"],
        },
    },
    {
        "name": "x_trending",
        "description": "Get currently trending topics on X/Twitter. Use for identifying viral content, cultural moments, and conversation opportunities.",
        "handler": x_trending,
        "parameters": {
            "type": "object",
            "properties": {
                "region": {"type": "string", "default": "worldwide", "description": "Region (worldwide, US, Brazil, etc)"},
            },
        },
    },
    {
        "name": "x_profile_research",
        "description": "Research an X/Twitter profile — recent posts, mentions, influence. Use for lead qualification, influencer analysis, competitive intelligence.",
        "handler": x_profile_research,
        "parameters": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "X/Twitter username (with or without @)"},
            },
            "required": ["username"],
        },
    },
    {
        "name": "social_monitor",
        "description": "Monitor brand/topic mentions across social platforms (Twitter, Reddit, LinkedIn). Use for reputation management and competitive intelligence.",
        "handler": social_monitor,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Brand or topic to monitor"},
                "platforms": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": ["twitter", "reddit", "linkedin"],
                    "description": "Platforms to monitor",
                },
            },
            "required": ["query"],
        },
    },
]
