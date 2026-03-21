"""
reddit_monitor.py — Wave's eyes on community discussions.

Monitors Reddit for pain signals, competitor mentions, and market sentiment.
"""

import logging
from typing import Any, Dict
from datetime import datetime

logger = logging.getLogger("openclaw.skills")

HEADERS = {"User-Agent": "BluewaveBot/1.0 (compatible; AI research agent)"}

RELEVANT_KEYWORDS = [
    "ai agent", "autonomous", "brand", "compliance", "creative",
    "design", "dam", "digital asset", "content ops", "saas",
    "computer vision", "llm", "content generation", "brand consistency",
    "approval workflow", "asset management", "marketing automation",
]

DEFAULT_SUBREDDITS = ["artificial", "ChatGPT", "SaaS", "marketing", "design"]


async def reddit_hot(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get hot posts from a subreddit, scored by relevance."""
    import httpx

    subreddit = params.get("subreddit", "artificial")
    limit = min(params.get("limit", 15), 25)

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(
                f"https://www.reddit.com/r/{subreddit}/hot.json",
                params={"limit": limit, "raw_json": 1},
                headers=HEADERS,
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            if post.get("stickied"):
                continue

            title = post.get("title", "")
            selftext = post.get("selftext", "")
            relevance = _compute_relevance(title, selftext)

            results.append({
                "title": title,
                "url": f"https://reddit.com{post.get('permalink', '')}",
                "score": post.get("score", 0),
                "comments": post.get("num_comments", 0),
                "author": post.get("author", ""),
                "subreddit": post.get("subreddit", subreddit),
                "created": datetime.fromtimestamp(post.get("created_utc", 0)).isoformat(),
                "selftext": selftext[:300] + ("..." if len(selftext) > 300 else ""),
                "relevance": relevance,
                "post_id": post.get("id", ""),
            })

        results.sort(key=lambda x: (x["relevance"], x["score"]), reverse=True)

        return {
            "success": True,
            "data": results[:limit],
            "message": f"{len(results)} hot posts from r/{subreddit}",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Reddit hot error: {e}")
        return {"success": False, "message": str(e)}


async def reddit_search(params: Dict[str, Any]) -> Dict[str, Any]:
    """Search Reddit for specific topics across all subreddits."""
    import httpx

    query = params.get("query", "ai agent")
    limit = min(params.get("limit", 15), 25)
    sort = params.get("sort", "relevance")

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(
                "https://www.reddit.com/search.json",
                params={"q": query, "sort": sort, "limit": limit, "raw_json": 1},
                headers=HEADERS,
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            title = post.get("title", "")
            selftext = post.get("selftext", "")

            results.append({
                "title": title,
                "url": f"https://reddit.com{post.get('permalink', '')}",
                "score": post.get("score", 0),
                "comments": post.get("num_comments", 0),
                "author": post.get("author", ""),
                "subreddit": post.get("subreddit", ""),
                "created": datetime.fromtimestamp(post.get("created_utc", 0)).isoformat(),
                "selftext": selftext[:300] + ("..." if len(selftext) > 300 else ""),
                "relevance": _compute_relevance(title, selftext),
                "post_id": post.get("id", ""),
            })

        return {
            "success": True,
            "data": results,
            "message": f"{len(results)} results for '{query}' on Reddit",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Reddit search error: {e}")
        return {"success": False, "message": str(e)}


async def reddit_post_comments(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get top comments from a Reddit post for sentiment and insights."""
    import httpx

    post_id = params.get("post_id", "")
    if not post_id:
        return {"success": False, "message": "post_id is required"}

    limit = min(params.get("limit", 10), 20)

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(
                f"https://www.reddit.com/comments/{post_id}.json",
                params={"limit": limit, "sort": "best", "raw_json": 1},
                headers=HEADERS,
            )
            resp.raise_for_status()
            data = resp.json()

        # First element is the post, second is comments
        post_data = data[0]["data"]["children"][0]["data"] if len(data) > 0 else {}
        comment_list = data[1]["data"]["children"] if len(data) > 1 else []

        comments = []
        for child in comment_list[:limit]:
            if child.get("kind") != "t1":
                continue
            c = child.get("data", {})
            body = c.get("body", "")
            comments.append({
                "author": c.get("author", ""),
                "text": body[:500] + ("..." if len(body) > 500 else ""),
                "score": c.get("score", 0),
                "replies": len(c.get("replies", {}).get("data", {}).get("children", [])) if isinstance(c.get("replies"), dict) else 0,
                "created": datetime.fromtimestamp(c.get("created_utc", 0)).isoformat(),
            })

        return {
            "success": True,
            "data": {
                "title": post_data.get("title", ""),
                "score": post_data.get("score", 0),
                "total_comments": post_data.get("num_comments", 0),
                "comments": comments,
            },
            "message": f"{len(comments)} comments from post {post_id}",
        }

    except Exception as e:
        logger.error(f"Reddit comments error: {e}")
        return {"success": False, "message": str(e)}


def _compute_relevance(title: str, text: str) -> float:
    combined = (title + " " + text).lower()
    score = sum(1.0 for kw in RELEVANT_KEYWORDS if kw in combined)
    return min(score / 3.0, 1.0)


TOOLS = [
    {
        "name": "reddit_hot",
        "description": "Get hot posts from a subreddit scored by relevance to Bluewave. Default: r/artificial. Good subreddits: artificial, ChatGPT, SaaS, marketing, design. Use to find pain signals and market sentiment.",
        "handler": reddit_hot,
        "parameters": {
            "type": "object",
            "properties": {
                "subreddit": {"type": "string", "description": "Subreddit name without r/ (default: 'artificial')"},
                "limit": {"type": "integer", "description": "Max results (default 15, max 25)"},
            },
            "required": [],
        },
    },
    {
        "name": "reddit_search",
        "description": "Search all of Reddit for specific topics. Use to find prospects with exposed pain ('looking for AI brand tool', 'DAM frustration', 'content ops nightmare').",
        "handler": reddit_search,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (e.g. 'brand compliance AI', 'DAM frustration')"},
                "limit": {"type": "integer", "description": "Max results (default 15, max 25)"},
                "sort": {"type": "string", "description": "'relevance', 'hot', 'top', 'new'", "enum": ["relevance", "hot", "top", "new"]},
            },
            "required": ["query"],
        },
    },
    {
        "name": "reddit_post_comments",
        "description": "Get top comments from a Reddit post. Use to extract sentiment, identify pain points, and find engagement opportunities.",
        "handler": reddit_post_comments,
        "parameters": {
            "type": "object",
            "properties": {
                "post_id": {"type": "string", "description": "Reddit post ID (from reddit_hot or reddit_search results)"},
                "limit": {"type": "integer", "description": "Max comments (default 10, max 20)"},
            },
            "required": ["post_id"],
        },
    },
]
