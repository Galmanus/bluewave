"""Moltbook — Wave's presence on the AI social network."""

from __future__ import annotations
import json
import re
import os
import logging
from typing import Any, Dict
import httpx

logger = logging.getLogger("openclaw.skills.moltbook")

MOLTBOOK_API = "https://www.moltbook.com/api/v1"
MOLTBOOK_KEY = os.environ.get("MOLTBOOK_API_KEY", "")
TIMEOUT = httpx.Timeout(30.0, connect=10.0)


def _headers():
    return {
        "Authorization": "Bearer %s" % MOLTBOOK_KEY,
        "Content-Type": "application/json",
    }


def _solve_verification(challenge_text):
    """Solve obfuscated math challenge."""
    numbers = re.findall(r'[-+]?\d+\.?\d*', challenge_text)
    if len(numbers) < 2:
        return None
    a, b = float(numbers[0]), float(numbers[1])
    text = challenge_text.lower()
    if any(w in text for w in ["plus", "add", "sum", "+"]):
        result = a + b
    elif any(w in text for w in ["minus", "subtract", "-"]):
        result = a - b
    elif any(w in text for w in ["times", "multiply", "multipl", "*", "×", "product"]):
        result = a * b
    elif any(w in text for w in ["divide", "÷", "/"]):
        result = a / b if b != 0 else 0
    else:
        result = a + b
    return "%.2f" % result


async def _verify_if_needed(result):
    """Handle verification challenge if present in API response."""
    if not isinstance(result, dict) or not result.get("verification_required"):
        return result
    challenge = result.get("challenge", {})
    answer = _solve_verification(challenge.get("challenge_text", ""))
    if not answer:
        return {"success": False, "data": None, "message": "Could not solve verification challenge"}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            "%s/verify" % MOLTBOOK_API,
            headers=_headers(),
            json={"verification_code": challenge["verification_code"], "answer": answer},
        )
        return resp.json()


async def moltbook_post(params: Dict[str, Any]) -> Dict:
    """Create a post on Moltbook."""
    if not MOLTBOOK_KEY:
        return {"success": False, "data": None, "message": "MOLTBOOK_API_KEY not set"}

    submolt = params.get("submolt", "general")
    title = params.get("title", "")
    content = params.get("content", "")

    if not title:
        return {"success": False, "data": None, "message": "Need a title"}

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            "%s/posts" % MOLTBOOK_API,
            headers=_headers(),
            json={"submolt_name": submolt, "title": title[:300], "content": content[:40000], "type": "text"},
        )
        result = resp.json()

    result = await _verify_if_needed(result)

    if isinstance(result, dict) and result.get("success"):
        post_data = result.get("data", result.get("post", {}))
        post_id = post_data.get("id", "")
        return {
            "success": True,
            "data": result,
            "message": "Posted to m/%s: %s\nhttps://www.moltbook.com/post/%s" % (submolt, title[:60], post_id),
        }
    return {"success": True, "data": result, "message": "Post submitted to m/%s" % submolt}


async def moltbook_comment(params: Dict[str, Any]) -> Dict:
    """Comment on a Moltbook post."""
    if not MOLTBOOK_KEY:
        return {"success": False, "data": None, "message": "MOLTBOOK_API_KEY not set"}

    post_id = params.get("post_id", "")
    content = params.get("content", "")
    parent_id = params.get("parent_id", None)

    if not post_id or not content:
        return {"success": False, "data": None, "message": "Need post_id and content"}

    body = {"content": content}
    if parent_id:
        body["parent_id"] = parent_id

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            "%s/posts/%s/comments" % (MOLTBOOK_API, post_id),
            headers=_headers(),
            json=body,
        )
        result = resp.json()

    result = await _verify_if_needed(result)
    return {"success": True, "data": result, "message": "Commented on post %s" % post_id[:8]}


async def moltbook_feed(params: Dict[str, Any]) -> Dict:
    """Browse Moltbook feed."""
    if not MOLTBOOK_KEY:
        return {"success": False, "data": None, "message": "MOLTBOOK_API_KEY not set"}

    sort = params.get("sort", "hot")
    submolt = params.get("submolt", "")
    limit = params.get("limit", 10)

    if submolt:
        url = "%s/submolts/%s/feed?sort=%s&limit=%d" % (MOLTBOOK_API, submolt, sort, limit)
    else:
        url = "%s/posts?sort=%s&limit=%d" % (MOLTBOOK_API, sort, limit)

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(url, headers=_headers())
        data = resp.json()

    posts = data.get("data", data.get("posts", []))
    if not posts:
        return {"success": True, "data": data, "message": "No posts found"}

    lines = ["**Moltbook feed (%s%s):**\n" % (sort, " m/%s" % submolt if submolt else "")]
    for p in posts[:limit]:
        author = p.get("author", {}).get("name", "?")
        title = p.get("title", "")[:80]
        score = p.get("score", 0)
        comments = p.get("comment_count", p.get("descendants", 0))
        pid = p.get("id", "")
        lines.append("- [%d pts, %d comments] **%s** by %s (id: %s)" % (score, comments, title, author, pid[:8]))

    return {"success": True, "data": posts, "message": "\n".join(lines)}


async def moltbook_upvote(params: Dict[str, Any]) -> Dict:
    """Upvote a post on Moltbook."""
    if not MOLTBOOK_KEY:
        return {"success": False, "data": None, "message": "MOLTBOOK_API_KEY not set"}

    post_id = params.get("post_id", "")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post("%s/posts/%s/upvote" % (MOLTBOOK_API, post_id), headers=_headers())
        result = resp.json()

    return {"success": True, "data": result, "message": "Upvoted post %s" % post_id[:8]}


async def moltbook_follow(params: Dict[str, Any]) -> Dict:
    """Follow an agent on Moltbook."""
    if not MOLTBOOK_KEY:
        return {"success": False, "data": None, "message": "MOLTBOOK_API_KEY not set"}

    name = params.get("agent_name", "")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post("%s/agents/%s/follow" % (MOLTBOOK_API, name), headers=_headers())
        result = resp.json()

    return {"success": True, "data": result, "message": "Followed @%s" % name}


async def moltbook_subscribe(params: Dict[str, Any]) -> Dict:
    """Subscribe to a submolt."""
    if not MOLTBOOK_KEY:
        return {"success": False, "data": None, "message": "MOLTBOOK_API_KEY not set"}

    submolt = params.get("submolt", "")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post("%s/submolts/%s/subscribe" % (MOLTBOOK_API, submolt), headers=_headers())
        result = resp.json()

    return {"success": True, "data": result, "message": "Subscribed to m/%s" % submolt}


async def moltbook_home(params: Dict[str, Any]) -> Dict:
    """Check Moltbook dashboard — notifications, replies, DMs."""
    if not MOLTBOOK_KEY:
        return {"success": False, "data": None, "message": "MOLTBOOK_API_KEY not set"}

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get("%s/home" % MOLTBOOK_API, headers=_headers())
        data = resp.json()

    home = data.get("data", data)
    account = home.get("your_account", {})
    activity = home.get("activity_on_your_posts", [])
    dms = home.get("your_direct_messages", {})

    lines = [
        "**Moltbook Dashboard:**",
        "Karma: %s | Unread: %s" % (str(account.get("karma", 0)), str(account.get("unread_notification_count", 0))),
    ]
    if activity:
        lines.append("Activity on your posts: %d items" % len(activity))
    if dms.get("pending_request_count"):
        lines.append("DM requests: %s" % str(dms["pending_request_count"]))

    return {"success": True, "data": home, "message": "\n".join(lines)}


async def moltbook_search(params: Dict[str, Any]) -> Dict:
    """Search Moltbook posts and comments."""
    if not MOLTBOOK_KEY:
        return {"success": False, "data": None, "message": "MOLTBOOK_API_KEY not set"}

    query = params.get("query", "")
    limit = params.get("limit", 10)

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            "%s/search?q=%s&limit=%d&type=all" % (MOLTBOOK_API, query, limit),
            headers=_headers(),
        )
        data = resp.json()

    results = data.get("data", data.get("results", []))
    lines = ["**Moltbook search '%s':** %d results" % (query, len(results))]
    for r in results[:limit]:
        title = r.get("title", r.get("content", ""))[:80]
        author = r.get("author", {}).get("name", "?") if isinstance(r.get("author"), dict) else "?"
        lines.append("- %s (by %s)" % (title, author))

    return {"success": True, "data": results, "message": "\n".join(lines)}


TOOLS = [
    {
        "name": "moltbook_post",
        "description": "Post to Moltbook (social network for AI agents). Write in English. Choose a submolt (community) like 'introductions', 'general', 'agents', 'ai', 'builds'.",
        "handler": moltbook_post,
        "parameters": {
            "type": "object",
            "properties": {
                "submolt": {"type": "string", "default": "general", "description": "Community to post in (general, introductions, agents, ai, builds, philosophy, etc)"},
                "title": {"type": "string", "description": "Post title (max 300 chars)"},
                "content": {"type": "string", "description": "Post body text"},
            },
            "required": ["title"],
        },
    },
    {
        "name": "moltbook_comment",
        "description": "Comment on a Moltbook post. Write in English. Be genuine and add value.",
        "handler": moltbook_comment,
        "parameters": {
            "type": "object",
            "properties": {
                "post_id": {"type": "string", "description": "ID of the post to comment on"},
                "content": {"type": "string", "description": "Comment text"},
                "parent_id": {"type": "string", "description": "Parent comment ID for replies"},
            },
            "required": ["post_id", "content"],
        },
    },
    {
        "name": "moltbook_feed",
        "description": "Browse Moltbook feed. See what other AI agents are posting and discussing.",
        "handler": moltbook_feed,
        "parameters": {
            "type": "object",
            "properties": {
                "sort": {"type": "string", "enum": ["hot", "new", "top", "rising"], "default": "hot"},
                "submolt": {"type": "string", "description": "Filter by submolt name (optional)"},
                "limit": {"type": "integer", "default": 10},
            },
        },
    },
    {
        "name": "moltbook_upvote",
        "description": "Upvote a post on Moltbook.",
        "handler": moltbook_upvote,
        "parameters": {
            "type": "object",
            "properties": {
                "post_id": {"type": "string", "description": "Post ID to upvote"},
            },
            "required": ["post_id"],
        },
    },
    {
        "name": "moltbook_follow",
        "description": "Follow another agent on Moltbook.",
        "handler": moltbook_follow,
        "parameters": {
            "type": "object",
            "properties": {
                "agent_name": {"type": "string", "description": "Agent name to follow"},
            },
            "required": ["agent_name"],
        },
    },
    {
        "name": "moltbook_subscribe",
        "description": "Subscribe to a Moltbook submolt (community).",
        "handler": moltbook_subscribe,
        "parameters": {
            "type": "object",
            "properties": {
                "submolt": {"type": "string", "description": "Submolt name to subscribe to"},
            },
            "required": ["submolt"],
        },
    },
    {
        "name": "moltbook_home",
        "description": "Check Moltbook dashboard — karma, notifications, replies, DMs.",
        "handler": moltbook_home,
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "moltbook_search",
        "description": "Search Moltbook posts and comments by keyword.",
        "handler": moltbook_search,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["query"],
        },
    },
]
