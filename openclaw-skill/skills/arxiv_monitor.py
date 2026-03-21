"""
arxiv_monitor.py — Wave's eyes on the academic frontier.

Monitors ArXiv for papers on agents, multimodal, decision-making, and metacognition.
"""

import logging
from typing import Any, Dict
from datetime import datetime
import xml.etree.ElementTree as ET

logger = logging.getLogger("openclaw.skills")

RELEVANT_KEYWORDS = [
    "agent", "autonomous", "multi-agent", "brand", "compliance",
    "creative", "multimodal", "vision language", "decision making",
    "metacognition", "self-reflection", "tool use", "psychometric",
    "behavioral", "game theory", "mechanism design", "reinforcement",
    "language model", "reasoning", "planning",
]

NS = {"atom": "http://www.w3.org/2005/Atom"}


async def arxiv_recent(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get recent papers from ArXiv in AI/agents/vision categories."""
    import httpx

    limit = min(params.get("limit", 15), 30)
    category = params.get("category", "cs.AI")

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                "https://export.arxiv.org/api/query",
                params={
                    "search_query": f"cat:{category}",
                    "sortBy": "submittedDate",
                    "sortOrder": "descending",
                    "max_results": limit * 2,
                },
            )
            resp.raise_for_status()

        papers = _parse_arxiv_xml(resp.text, limit)

        return {
            "success": True,
            "data": papers,
            "message": f"{len(papers)} recent papers from ArXiv",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"ArXiv recent error: {e}")
        return {"success": False, "message": str(e)}


async def arxiv_search(params: Dict[str, Any]) -> Dict[str, Any]:
    """Search ArXiv for papers on specific topics."""
    import httpx

    query = params.get("query", "autonomous agent")
    limit = min(params.get("limit", 15), 30)

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                "https://export.arxiv.org/api/query",
                params={
                    "search_query": f"all:{query}",
                    "sortBy": "relevance",
                    "max_results": limit,
                },
            )
            resp.raise_for_status()

        papers = _parse_arxiv_xml(resp.text, limit)

        return {
            "success": True,
            "data": papers,
            "message": f"{len(papers)} papers for '{query}' on ArXiv",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"ArXiv search error: {e}")
        return {"success": False, "message": str(e)}


def _parse_arxiv_xml(xml_text: str, limit: int) -> list:
    """Parse ArXiv Atom XML response into structured data."""
    root = ET.fromstring(xml_text)

    entries = root.findall("atom:entry", NS)
    if not entries:
        entries = root.findall("{http://www.w3.org/2005/Atom}entry")

    results = []
    for entry in entries[:limit * 2]:
        title = _get_text(entry, "title").replace("\n", " ").strip()
        summary = _get_text(entry, "summary").replace("\n", " ").strip()
        arxiv_id = _get_text(entry, "id")
        published = _get_text(entry, "published")

        # Authors
        authors = []
        for author in entry.findall("atom:author", NS) or entry.findall("{http://www.w3.org/2005/Atom}author"):
            name = author.findtext("atom:name", "", NS) or author.findtext("{http://www.w3.org/2005/Atom}name") or ""
            if name:
                authors.append(name.strip())

        # Categories
        categories = []
        for cat in entry.findall("atom:category", NS) or entry.findall("{http://www.w3.org/2005/Atom}category"):
            term = cat.get("term", "")
            if term:
                categories.append(term)

        relevance = _compute_relevance(title, summary)

        results.append({
            "title": title,
            "summary": summary[:400] + ("..." if len(summary) > 400 else ""),
            "authors": authors[:5],
            "url": arxiv_id,
            "published": published,
            "categories": categories[:5],
            "relevance": relevance,
        })

    results.sort(key=lambda x: x["relevance"], reverse=True)
    return results[:limit]


def _get_text(entry, tag: str) -> str:
    """Get text from an Atom entry, handling namespaces."""
    el = entry.find(f"atom:{tag}", NS) or entry.find(f"{{http://www.w3.org/2005/Atom}}{tag}")
    return (el.text or "").strip() if el is not None else ""


def _compute_relevance(title: str, text: str) -> float:
    combined = (title + " " + text).lower()
    score = sum(1.0 for kw in RELEVANT_KEYWORDS if kw in combined)
    return min(score / 3.0, 1.0)


TOOLS = [
    {
        "name": "arxiv_recent",
        "description": "Get recent ArXiv papers in AI, multi-agent, computer vision, and NLP categories. Scored by relevance to agents, multimodal, decision-making, metacognition. Use for deep research and Moltbook thought leadership content.",
        "handler": arxiv_recent,
        "parameters": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "ArXiv category (default: cs.AI+OR+cat:cs.MA+OR+cat:cs.CV+OR+cat:cs.CL)"},
                "limit": {"type": "integer", "description": "Max results (default 15, max 30)"},
            },
            "required": [],
        },
    },
    {
        "name": "arxiv_search",
        "description": "Search ArXiv for papers on specific topics. Use to find academic validation for PUT, soul architecture, or agent design patterns.",
        "handler": arxiv_search,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (e.g. 'autonomous agent decision making', 'psychometric utility')"},
                "limit": {"type": "integer", "description": "Max results (default 15, max 30)"},
            },
            "required": ["query"],
        },
    },
]
