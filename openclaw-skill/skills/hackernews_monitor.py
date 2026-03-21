"""
hackernews_monitor.py — Wave's eyes on the tech/startup frontier.

Monitors Hacker News for trending stories, Show HN launches, and Ask HN discussions.
Filters by strategic relevance to Bluewave's domain.
"""

import logging
from typing import Any, Dict, List
from datetime import datetime

logger = logging.getLogger("openclaw.skills")

RELEVANT_KEYWORDS = [
    "ai agent", "autonomous", "multi-agent", "brand", "compliance",
    "creative", "design", "dam", "digital asset", "content ops",
    "saas", "startup", "computer vision", "llm", "claude",
    "anthropic", "openai", "multimodal", "hedera", "blockchain",
    "micropayment", "psychometric", "decision-making", "metacognition",
    "self-evolving", "tool use", "function calling", "agent framework",
]


async def hn_top_stories(params: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch top/trending stories from Hacker News, scored by relevance."""
    import httpx

    limit = min(params.get("limit", 15), 30)
    story_type = params.get("type", "top")  # top, new, best, show, ask

    type_map = {
        "top": "topstories",
        "new": "newstories",
        "best": "beststories",
        "show": "showstories",
        "ask": "askstories",
    }
    endpoint = type_map.get(story_type, "topstories")

    try:
        base = "https://hacker-news.firebaseio.com/v0"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{base}/{endpoint}.json")
            resp.raise_for_status()
            story_ids = resp.json()[:limit * 2]

            stories = []
            for sid in story_ids[:limit * 2]:
                r = await client.get(f"{base}/item/{sid}.json")
                if r.status_code == 200:
                    item = r.json()
                    if item and item.get("type") == "story":
                        title = item.get("title", "")
                        url = item.get("url", "")
                        text = item.get("text", "")
                        relevance = _compute_relevance(title, url, text)

                        stories.append({
                            "id": item.get("id"),
                            "title": title,
                            "url": url or f"https://news.ycombinator.com/item?id={item.get('id')}",
                            "score": item.get("score", 0),
                            "comments": item.get("descendants", 0),
                            "by": item.get("by", ""),
                            "time": datetime.fromtimestamp(item.get("time", 0)).isoformat(),
                            "relevance": relevance,
                        })

                if len(stories) >= limit:
                    break

        stories.sort(key=lambda x: (x["relevance"], x["score"]), reverse=True)

        return {
            "success": True,
            "data": stories[:limit],
            "message": f"{len(stories)} {story_type} stories from HN",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"HN top stories error: {e}")
        return {"success": False, "message": str(e)}


async def hn_search(params: Dict[str, Any]) -> Dict[str, Any]:
    """Search Hacker News via Algolia API for specific topics."""
    import httpx

    query = params.get("query", "ai agent")
    limit = min(params.get("limit", 10), 20)
    sort = params.get("sort", "points")  # points, date

    try:
        url = "https://hn.algolia.com/api/v1/search"
        if sort == "date":
            url = "https://hn.algolia.com/api/v1/search_by_date"

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params={
                "query": query,
                "tags": "story",
                "hitsPerPage": limit,
            })
            resp.raise_for_status()
            data = resp.json()

        results = []
        for hit in data.get("hits", []):
            title = hit.get("title", "")
            url_val = hit.get("url", "")
            relevance = _compute_relevance(title, url_val, hit.get("story_text", ""))

            results.append({
                "id": hit.get("objectID"),
                "title": title,
                "url": url_val or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                "score": hit.get("points", 0),
                "comments": hit.get("num_comments", 0),
                "by": hit.get("author", ""),
                "time": hit.get("created_at", ""),
                "relevance": relevance,
                "hn_url": f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
            })

        return {
            "success": True,
            "data": results,
            "message": f"{len(results)} results for '{query}' on HN",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"HN search error: {e}")
        return {"success": False, "message": str(e)}


async def hn_story_comments(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get top comments from a specific HN story — useful for sentiment and insights."""
    import httpx

    story_id = params.get("story_id")
    if not story_id:
        return {"success": False, "message": "story_id is required"}

    limit = min(params.get("limit", 10), 20)

    try:
        base = "https://hacker-news.firebaseio.com/v0"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{base}/item/{story_id}.json")
            resp.raise_for_status()
            story = resp.json()

            if not story:
                return {"success": False, "message": "Story not found"}

            comment_ids = story.get("kids", [])[:limit]
            comments = []

            for cid in comment_ids:
                r = await client.get(f"{base}/item/{cid}.json")
                if r.status_code == 200:
                    c = r.json()
                    if c and c.get("type") == "comment" and not c.get("deleted"):
                        text = c.get("text", "")
                        # Strip HTML tags
                        import re
                        clean = re.sub(r'<[^>]+>', '', text)
                        comments.append({
                            "by": c.get("by", ""),
                            "text": clean[:500] + ("..." if len(clean) > 500 else ""),
                            "time": datetime.fromtimestamp(c.get("time", 0)).isoformat(),
                            "replies": len(c.get("kids", [])),
                        })

        return {
            "success": True,
            "data": {
                "title": story.get("title", ""),
                "score": story.get("score", 0),
                "total_comments": story.get("descendants", 0),
                "comments": comments,
            },
            "message": f"{len(comments)} top comments from '{story.get('title', '')[:50]}'",
        }

    except Exception as e:
        logger.error(f"HN comments error: {e}")
        return {"success": False, "message": str(e)}


def _compute_relevance(title: str, url: str, text: str = "") -> float:
    """Score relevance to Bluewave's domain (0-1)."""
    combined = (title + " " + url + " " + text).lower()
    score = 0.0
    for kw in RELEVANT_KEYWORDS:
        if kw in combined:
            score += 1.0
    return min(score / 3.0, 1.0)


# ── Tool registration ───────────────────────────────────────────────

TOOLS = [
    {
        "name": "hn_top_stories",
        "description": "Get top/trending/best/show/ask stories from Hacker News, scored by relevance to Bluewave (AI agents, SaaS, creative ops, blockchain). Use for knowledge accumulation and Moltbook content.",
        "handler": hn_top_stories,
        "parameters": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "description": "Story type: 'top', 'new', 'best', 'show', 'ask' (default: 'top')",
                    "enum": ["top", "new", "best", "show", "ask"],
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 15, max 30)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "hn_search",
        "description": "Search Hacker News for specific topics via Algolia. Use to find discussions about competitors, AI agents, DAM platforms, or brand tech. Sort by points or date.",
        "handler": hn_search,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (e.g. 'ai agent autonomous', 'digital asset management', 'brand compliance')",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 10, max 20)",
                },
                "sort": {
                    "type": "string",
                    "description": "'points' for most popular, 'date' for most recent",
                    "enum": ["points", "date"],
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "hn_story_comments",
        "description": "Get top comments from a specific HN story. Use to understand market sentiment, extract insights, and find engagement opportunities.",
        "handler": hn_story_comments,
        "parameters": {
            "type": "object",
            "properties": {
                "story_id": {
                    "type": "integer",
                    "description": "HN story ID (from hn_top_stories or hn_search results)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max comments to fetch (default 10, max 20)",
                },
            },
            "required": ["story_id"],
        },
    },
]
