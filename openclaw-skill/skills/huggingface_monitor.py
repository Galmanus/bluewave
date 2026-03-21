"""
huggingface_monitor.py — Wave's eyes on the AI research frontier.

Monitors Hugging Face for trending models, daily papers, and competitive spaces.
Filters everything through strategic relevance to Bluewave's domain.
"""

import json
import logging
from typing import Any, Dict, List
from datetime import datetime

logger = logging.getLogger("openclaw.skills")

# Domains Wave cares about
RELEVANT_TAGS = [
    "computer-vision", "image-classification", "image-to-text",
    "text-generation", "text2text-generation", "summarization",
    "multi-agent", "autonomous-agents", "brand", "design",
    "multimodal", "vision-language", "document-understanding",
]

PAPER_KEYWORDS = [
    "agent", "autonomous", "multi-agent", "brand", "compliance",
    "creative", "design", "vision", "multimodal", "psychometric",
    "decision", "metacognition", "self-reflection", "DAM",
    "content generation", "image analysis", "tool use",
]


async def hf_trending_models(params: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch trending models from Hugging Face, filtered by relevance."""
    import httpx

    category = params.get("category", "")
    limit = min(params.get("limit", 10), 20)

    try:
        url = "https://huggingface.co/api/models"
        query_params = {
            "sort": "likes",
            "limit": limit * 3,  # fetch more, filter down
        }
        if category:
            query_params["pipeline_tag"] = category

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=query_params)
            resp.raise_for_status()
            models = resp.json()

        results = []
        for m in models[:limit]:
            tags = m.get("tags", [])
            results.append({
                "id": m.get("modelId", m.get("id", "")),
                "author": m.get("author", ""),
                "downloads": m.get("downloads", 0),
                "likes": m.get("likes", 0),
                "tags": tags[:8],
                "pipeline_tag": m.get("pipeline_tag", ""),
                "last_modified": m.get("lastModified", ""),
                "relevance": _compute_relevance(tags, m.get("modelId", "")),
            })

        # Sort by relevance to Bluewave
        results.sort(key=lambda x: x["relevance"], reverse=True)

        return {
            "success": True,
            "data": results[:limit],
            "message": f"Found {len(results)} trending models" +
                       (f" in {category}" if category else ""),
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"HF trending models error: {e}")
        return {"success": False, "message": str(e)}


async def hf_daily_papers(params: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch daily papers from Hugging Face, filtered by strategic relevance."""
    import httpx

    limit = min(params.get("limit", 10), 20)
    topic_filter = params.get("topic", "").lower()

    try:
        url = "https://huggingface.co/api/daily_papers"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            papers = resp.json()

        results = []
        for p in papers:
            paper = p.get("paper", p)
            title = paper.get("title", "")
            summary = paper.get("summary", paper.get("abstract", ""))
            authors = paper.get("authors", [])

            # Relevance scoring
            text = (title + " " + summary).lower()
            relevance = 0.0
            matched_keywords = []
            for kw in PAPER_KEYWORDS:
                if kw.lower() in text:
                    relevance += 1.0
                    matched_keywords.append(kw)

            relevance = min(relevance / 3.0, 1.0)  # normalize

            # Apply topic filter
            if topic_filter and topic_filter not in text:
                continue

            results.append({
                "title": title,
                "summary": summary[:400] + ("..." if len(summary) > 400 else ""),
                "authors": [a.get("name", str(a)) if isinstance(a, dict) else str(a)
                           for a in authors[:5]],
                "url": f"https://huggingface.co/papers/{paper.get('id', '')}",
                "upvotes": p.get("numUpvotes", paper.get("upvotes", 0)),
                "relevance": relevance,
                "matched_keywords": matched_keywords,
                "published": paper.get("publishedAt", ""),
            })

        # Sort by relevance, then upvotes
        results.sort(key=lambda x: (x["relevance"], x["upvotes"]), reverse=True)

        return {
            "success": True,
            "data": results[:limit],
            "message": f"Found {len(results)} papers" +
                       (f" on '{topic_filter}'" if topic_filter else ""),
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"HF daily papers error: {e}")
        return {"success": False, "message": str(e)}


async def hf_space_watch(params: Dict[str, Any]) -> Dict[str, Any]:
    """Monitor Hugging Face Spaces for competitive intelligence."""
    import httpx

    search_query = params.get("query", "brand compliance")
    limit = min(params.get("limit", 10), 20)

    try:
        url = "https://huggingface.co/api/spaces"
        query_params = {
            "search": search_query,
            "sort": "likes",
            "limit": limit,
        }

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=query_params)
            resp.raise_for_status()
            spaces = resp.json()

        results = []
        for s in spaces:
            tags = s.get("tags", [])
            results.append({
                "id": s.get("id", ""),
                "author": s.get("author", ""),
                "title": s.get("cardData", {}).get("title", s.get("id", "")),
                "likes": s.get("likes", 0),
                "tags": tags[:6],
                "sdk": s.get("sdk", ""),
                "url": f"https://huggingface.co/spaces/{s.get('id', '')}",
                "last_modified": s.get("lastModified", ""),
                "relevance": _compute_relevance(tags, s.get("id", "")),
            })

        results.sort(key=lambda x: x["relevance"], reverse=True)

        return {
            "success": True,
            "data": results,
            "message": f"Found {len(results)} spaces for '{search_query}'",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"HF space watch error: {e}")
        return {"success": False, "message": str(e)}


async def hf_model_detail(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get detailed info about a specific model — README, config, metrics."""
    import httpx

    model_id = params.get("model_id", "")
    if not model_id:
        return {"success": False, "message": "model_id is required"}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            # Model info
            resp = await client.get(f"https://huggingface.co/api/models/{model_id}")
            resp.raise_for_status()
            model = resp.json()

            # Try to get README
            readme = ""
            try:
                r2 = await client.get(
                    f"https://huggingface.co/{model_id}/raw/main/README.md",
                    follow_redirects=True,
                )
                if r2.status_code == 200:
                    readme = r2.text[:2000]
            except Exception:
                pass

        return {
            "success": True,
            "data": {
                "id": model.get("modelId", model_id),
                "author": model.get("author", ""),
                "pipeline_tag": model.get("pipeline_tag", ""),
                "tags": model.get("tags", []),
                "downloads": model.get("downloads", 0),
                "likes": model.get("likes", 0),
                "library_name": model.get("library_name", ""),
                "license": model.get("cardData", {}).get("license", "unknown"),
                "readme_excerpt": readme,
                "url": f"https://huggingface.co/{model_id}",
            },
            "message": f"Details for {model_id}",
        }

    except Exception as e:
        logger.error(f"HF model detail error: {e}")
        return {"success": False, "message": str(e)}


def _compute_relevance(tags: list, name: str) -> float:
    """Score relevance to Bluewave's domain (0-1)."""
    score = 0.0
    text = " ".join(tags + [name]).lower()
    for tag in RELEVANT_TAGS:
        if tag.lower() in text:
            score += 1.0
    return min(score / 3.0, 1.0)


# ── Tool registration ───────────────────────────────────────────────

TOOLS = [
    {
        "name": "hf_trending_models",
        "description": "Get trending AI models from Hugging Face, scored by relevance to Bluewave (computer vision, multimodal, agents, brand analysis). Use to monitor the AI frontier for threats and opportunities.",
        "handler": hf_trending_models,
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Pipeline category filter: 'image-classification', 'text-generation', 'image-to-text', 'text2text-generation', etc. Leave empty for all.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 10, max 20)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "hf_daily_papers",
        "description": "Get today's AI research papers from Hugging Face Daily Papers, scored by relevance to agents, multimodal, brand, creative ops. Use for knowledge accumulation and Moltbook content generation.",
        "handler": hf_daily_papers,
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Optional keyword filter: 'agent', 'vision', 'multimodal', 'brand', etc.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 10, max 20)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "hf_space_watch",
        "description": "Monitor Hugging Face Spaces for competitive intelligence. Search for spaces related to brand compliance, DAM, content generation, or any domain relevant to Bluewave.",
        "handler": hf_space_watch,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for spaces (default: 'brand compliance')",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 10, max 20)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "hf_model_detail",
        "description": "Get detailed information about a specific Hugging Face model — tags, downloads, README excerpt, license. Use after finding an interesting model via hf_trending_models.",
        "handler": hf_model_detail,
        "parameters": {
            "type": "object",
            "properties": {
                "model_id": {
                    "type": "string",
                    "description": "Model ID in format 'author/model-name' (e.g. 'openai/clip-vit-large-patch14')",
                },
            },
            "required": ["model_id"],
        },
    },
]
