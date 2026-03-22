"""hn_lead_hunter — Scrapes HN Who is Hiring threads and Ask HN posts for warm AI leads.

Identifies companies/people actively hiring or seeking AI agent solutions.
Scores by fit with Ialum/Wave capabilities. Extracts contact info.
This is a REVENUE skill — every lead is a potential client.
"""

from __future__ import annotations
import json
import re
from typing import Any, Dict, List
import aiohttp


# Keywords that signal high-fit opportunities for Ialum/Wave
KEYWORDS_TIER1 = [
    "ai agent", "autonomous agent", "llm", "mcp", "claude", "tool use",
    "function calling", "multi-agent", "agentic", "ai engineer",
    "ai infrastructure", "ai ops", "agent framework",
]
KEYWORDS_TIER2 = [
    "automation", "chatbot", "rag", "vector database", "embedding",
    "fine-tune", "prompt engineer", "langchain", "openai", "gpt",
    "machine learning", "nlp", "workflow automation",
]
KEYWORDS_WEB3 = [
    "hedera", "hashgraph", "web3", "blockchain", "defi", "dao",
    "smart contract", "solana", "starknet", "ethereum",
]
KEYWORDS_BONUS = [
    "contract", "freelance", "consulting", "remote", "part-time",
    "contractor", "agency", "outsource",
]


def score_text(text: str) -> tuple[int, list[str]]:
    """Score a text block for lead quality."""
    t = text.lower()
    score = 0
    matched = []

    for kw in KEYWORDS_TIER1:
        if kw in t:
            score += 4
            matched.append(kw)
    for kw in KEYWORDS_TIER2:
        if kw in t:
            score += 2
            matched.append(kw)
    for kw in KEYWORDS_WEB3:
        if kw in t:
            score += 3
            matched.append(kw)
    for kw in KEYWORDS_BONUS:
        if kw in t:
            score += 2
            matched.append(kw)

    return score, matched


def extract_contacts(text: str) -> Dict[str, list]:
    """Extract emails and URLs from text."""
    emails = list(set(re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)))
    urls = list(set(re.findall(r"https?://[^\s<>\"']+", text)))
    return {"emails": emails[:3], "urls": urls[:5]}


async def hunt_hn_hiring(params: Dict[str, Any]) -> Dict:
    """Scan HN 'Who is Hiring' threads for AI agent opportunities.

    Pulls latest hiring threads from Algolia API, scores each posting
    by relevance to our capabilities, returns ranked leads.
    """
    min_score = params.get("min_score", 6)
    max_leads = params.get("max_leads", 25)
    include_ask = params.get("include_ask", True)

    all_leads: List[Dict] = []
    errors: List[str] = []

    timeout = aiohttp.ClientTimeout(total=20)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        # ── Source 1: Who is Hiring threads ──
        try:
            url = "https://hn.algolia.com/api/v1/search?query=%22who+is+hiring%22&tags=story&hitsPerPage=5"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    stories = data.get("hits", [])

                    for story in stories[:3]:
                        story_id = story["objectID"]
                        story_title = story.get("title", "")

                        # Fetch comments (job postings)
                        cmt_url = (
                            f"https://hn.algolia.com/api/v1/search"
                            f"?tags=comment,story_{story_id}&hitsPerPage=300"
                        )
                        async with session.get(cmt_url) as cresp:
                            if cresp.status == 200:
                                cdata = await cresp.json()
                                for comment in cdata.get("hits", []):
                                    raw = comment.get("comment_text", "") or ""
                                    text = re.sub(r"<[^>]+>", " ", raw)

                                    score, matched = score_text(text)
                                    if score < min_score:
                                        continue

                                    # Extract first meaningful line as headline
                                    lines = [
                                        l.strip()
                                        for l in text.split("\n")
                                        if l.strip() and len(l.strip()) > 10
                                    ]
                                    headline = lines[0][:150] if lines else "No headline"

                                    contacts = extract_contacts(text)

                                    all_leads.append({
                                        "source": f"HN: {story_title[:60]}",
                                        "score": score,
                                        "matched_keywords": matched,
                                        "headline": headline,
                                        "contacts": contacts,
                                        "hn_url": f"https://news.ycombinator.com/item?id={comment.get('objectID', '')}",
                                        "author": comment.get("author", "unknown"),
                                        "is_freelance_friendly": any(
                                            k in text.lower()
                                            for k in ["contract", "freelance", "remote", "consulting"]
                                        ),
                                        "has_web3": any(k in text.lower() for k in KEYWORDS_WEB3),
                                        "snippet": text[:400],
                                    })
        except Exception as e:
            errors.append(f"HN Hiring: {e}")

        # ── Source 2: Ask HN posts seeking AI help ──
        if include_ask:
            try:
                ask_queries = [
                    "ask+hn+ai+agent",
                    "ask+hn+looking+for+ai",
                    "ask+hn+need+llm",
                ]
                for q in ask_queries:
                    url = f"https://hn.algolia.com/api/v1/search?query={q}&tags=ask_hn&hitsPerPage=10"
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            for hit in data.get("hits", []):
                                title = hit.get("title", "")
                                text = title + " " + (hit.get("story_text") or "")
                                text_clean = re.sub(r"<[^>]+>", " ", text)

                                score, matched = score_text(text_clean)
                                if score >= min_score:
                                    contacts = extract_contacts(text_clean)
                                    all_leads.append({
                                        "source": "Ask HN",
                                        "score": score,
                                        "matched_keywords": matched,
                                        "headline": title[:150],
                                        "contacts": contacts,
                                        "hn_url": f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                                        "author": hit.get("author", "unknown"),
                                        "is_freelance_friendly": True,
                                        "has_web3": any(k in text_clean.lower() for k in KEYWORDS_WEB3),
                                        "snippet": text_clean[:400],
                                    })
            except Exception as e:
                errors.append(f"Ask HN: {e}")

    # Sort by score descending
    all_leads.sort(key=lambda x: x["score"], reverse=True)
    top = all_leads[:max_leads]

    # Build summary
    freelance_count = sum(1 for l in top if l.get("is_freelance_friendly"))
    web3_count = sum(1 for l in top if l.get("has_web3"))
    with_email = sum(1 for l in top if l.get("contacts", {}).get("emails"))

    summary_lines = [f"## HN Lead Hunt Results\n"]
    summary_lines.append(f"**{len(top)} leads found** (min score: {min_score})")
    summary_lines.append(f"- {freelance_count} freelance-friendly")
    summary_lines.append(f"- {web3_count} web3-related")
    summary_lines.append(f"- {with_email} with direct email\n")

    for i, lead in enumerate(top[:10], 1):
        emoji = "🔥" if lead["score"] >= 12 else "⭐" if lead["score"] >= 8 else "📌"
        summary_lines.append(
            f"{emoji} **{i}. [{lead['score']}pts]** {lead['headline']}"
        )
        summary_lines.append(f"   Author: {lead['author']} | {lead['hn_url']}")
        if lead["contacts"].get("emails"):
            summary_lines.append(f"   Email: {', '.join(lead['contacts']['emails'])}")
        tags = []
        if lead["is_freelance_friendly"]:
            tags.append("FREELANCE")
        if lead["has_web3"]:
            tags.append("WEB3")
        if tags:
            summary_lines.append(f"   Tags: {', '.join(tags)}")
        summary_lines.append("")

    return {
        "success": True,
        "data": top,
        "message": "\n".join(summary_lines),
        "stats": {
            "total_scanned": len(all_leads),
            "returned": len(top),
            "freelance_friendly": freelance_count,
            "web3_related": web3_count,
            "with_email": with_email,
        },
        "errors": errors,
        "next_action": "Prioritize leads with score >= 10. Draft outreach using cold_outreach_gen skill.",
    }


TOOLS = [
    {
        "name": "hunt_hn_hiring",
        "description": "Scan HN Who is Hiring + Ask HN for AI agent leads. Returns scored, ranked opportunities with contact info.",
        "handler": hunt_hn_hiring,
        "parameters": {
            "type": "object",
            "properties": {
                "min_score": {
                    "type": "integer",
                    "description": "Minimum relevance score to include (default: 6)",
                    "default": 6,
                },
                "max_leads": {
                    "type": "integer",
                    "description": "Maximum number of leads to return (default: 25)",
                    "default": 25,
                },
                "include_ask": {
                    "type": "boolean",
                    "description": "Also scan Ask HN posts (default: true)",
                    "default": True,
                },
            },
        },
    },
]
