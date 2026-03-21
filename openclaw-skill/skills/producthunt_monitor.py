"""
producthunt_monitor.py — Wave's eyes on startup launches.

Monitors Product Hunt for new products via RSS/Atom feed.
"""

import logging
from typing import Any, Dict
from datetime import datetime
import xml.etree.ElementTree as ET

logger = logging.getLogger("openclaw.skills")

RELEVANT_KEYWORDS = [
    "ai agent", "autonomous", "brand", "compliance", "creative",
    "design", "dam", "digital asset", "content", "saas",
    "computer vision", "llm", "multimodal", "marketing",
    "approval", "workflow", "asset management",
]


async def ph_today(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get today's products from Product Hunt via Atom feed."""
    import httpx

    limit = min(params.get("limit", 15), 30)

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(
                "https://www.producthunt.com/feed",
                headers={"User-Agent": "BluewaveBot/1.0"},
            )
            resp.raise_for_status()

        root = ET.fromstring(resp.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entries = root.findall("atom:entry", ns) or root.findall("entry")

        # Fallback: try RSS if Atom fails
        if not entries:
            items = root.findall(".//item")
            results = []
            for item in items[:limit]:
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                desc = (item.findtext("description") or "").strip()
                pub = (item.findtext("pubDate") or "").strip()
                relevance = _compute_relevance(title, desc)
                results.append({
                    "title": title,
                    "url": link,
                    "description": desc[:300],
                    "published": pub,
                    "relevance": relevance,
                })
        else:
            results = []
            for entry in entries[:limit]:
                title = (entry.findtext("atom:title", "", ns) or entry.findtext("title") or "").strip()
                link_el = entry.find("atom:link", ns) or entry.find("link")
                link = link_el.get("href", "") if link_el is not None else ""
                summary = (entry.findtext("atom:summary", "", ns) or entry.findtext("summary") or "").strip()
                published = (entry.findtext("atom:published", "", ns) or entry.findtext("published") or "").strip()
                relevance = _compute_relevance(title, summary)
                results.append({
                    "title": title,
                    "url": link,
                    "description": summary[:300],
                    "published": published,
                    "relevance": relevance,
                })

        results.sort(key=lambda x: x["relevance"], reverse=True)

        return {
            "success": True,
            "data": results[:limit],
            "message": f"{len(results)} products from Product Hunt",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"PH today error: {e}")
        return {"success": False, "message": str(e)}


def _compute_relevance(title: str, text: str) -> float:
    combined = (title + " " + text).lower()
    score = sum(1.0 for kw in RELEVANT_KEYWORDS if kw in combined)
    return min(score / 3.0, 1.0)


TOOLS = [
    {
        "name": "ph_today",
        "description": "Get today's Product Hunt launches scored by relevance to Bluewave (AI agents, SaaS, brand tools, DAM, creative ops). Use for competitive intelligence on new product launches.",
        "handler": ph_today,
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 15, max 30)",
                },
            },
            "required": [],
        },
    },
]
