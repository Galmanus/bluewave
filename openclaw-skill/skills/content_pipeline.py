"""
content_pipeline.py — Pre-generate content batch for Wave

Opus generates 5 posts at once. Wave distributes 1 per cycle when action=post.
Eliminates the slow content-generation-during-post problem.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("wave.content")

CONTENT_QUEUE = Path(__file__).parent.parent / "memory" / "content_queue.json"


def _load_queue() -> list:
    if CONTENT_QUEUE.exists():
        try:
            return json.loads(CONTENT_QUEUE.read_text())
        except Exception:
            pass
    return []


def _save_queue(queue: list):
    CONTENT_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    CONTENT_QUEUE.write_text(json.dumps(queue, indent=2, ensure_ascii=False))


async def content_generate_batch(params: Dict[str, Any]) -> Dict:
    """Generate a batch of 5 posts using Opus. Store in queue for later posting."""
    try:
        from claude_engine import claude_call

        result = await claude_call(
            prompt=(
                "Generate 5 Moltbook posts as a JSON array. Each post has: submolt, title, content (200-400 words).\n"
                "Topics: AI agents, soul architecture, PUT framework, autonomous operations, DeFi privacy.\n"
                "Each post must be unique and insightful. Apply PUT naturally. No emojis. No marketing.\n"
                "Respond ONLY with: [{\"submolt\":\"agents\",\"title\":\"...\",\"content\":\"...\"}, ...]"
            ),
            system_prompt="You are Wave. Write 5 original posts. JSON array only.",
            model="sonnet",
            timeout=60,
        )

        if not result.get("success"):
            return {"success": False, "message": "Generation failed"}

        # Parse the JSON array
        import re
        text = result["response"]
        match = re.search(r'\[[\s\S]*\]', text)
        if not match:
            return {"success": False, "message": "Could not parse posts array"}

        posts = json.loads(match.group())
        queue = _load_queue()

        for p in posts:
            p["generated_at"] = datetime.utcnow().isoformat()
            p["posted"] = False
            queue.append(p)

        _save_queue(queue)

        return {
            "success": True,
            "message": f"Generated {len(posts)} posts. Queue: {len(queue)} total.",
            "data": {"generated": len(posts), "queue_size": len(queue)},
        }
    except Exception as e:
        return {"success": False, "message": str(e)}


async def content_pop(params: Dict[str, Any]) -> Dict:
    """Get the next unposted content from the queue."""
    queue = _load_queue()
    unposted = [p for p in queue if not p.get("posted")]

    if not unposted:
        return {"success": False, "message": "Queue empty. Run content_generate_batch first."}

    post = unposted[0]
    # Mark as posted
    for p in queue:
        if p.get("title") == post["title"] and not p.get("posted"):
            p["posted"] = True
            break
    _save_queue(queue)

    return {
        "success": True,
        "data": post,
        "remaining": len(unposted) - 1,
        "message": f"Next post: {post.get('title', '')[:60]}. {len(unposted) - 1} remaining.",
    }


async def content_queue_status(params: Dict[str, Any]) -> Dict:
    """Check content queue status."""
    queue = _load_queue()
    unposted = len([p for p in queue if not p.get("posted")])
    return {
        "success": True,
        "data": {"total": len(queue), "unposted": unposted, "posted": len(queue) - unposted},
        "message": f"Queue: {unposted} unposted / {len(queue)} total",
    }


TOOLS = [
    {
        "name": "content_generate_batch",
        "description": "Generate 5 Moltbook posts at once using Opus. Stores in queue for fast posting later.",
        "handler": content_generate_batch,
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "content_pop",
        "description": "Get the next unposted content from the pre-generated queue. Use when action=post for instant posting.",
        "handler": content_pop,
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "content_queue_status",
        "description": "Check how many pre-generated posts are available in the queue.",
        "handler": content_queue_status,
        "parameters": {"type": "object", "properties": {}},
    },
]
