"""Bounty Hunter — automated scanner for paying opportunities: hackathons, grants, bounties, gigs."""

from __future__ import annotations
import json
from typing import Any, Dict
from duckduckgo_search import DDGS


async def scan_bounties(params: Dict[str, Any]) -> Dict:
    """Scan multiple sources for paying opportunities."""
    focus = params.get("focus", "all")

    query_sets = {
        "all": [
            "AI agent hackathon 2026 prize money",
            "blockchain grant program AI autonomous agent 2026",
            "GitHub bounty AI agent open source",
            "freelance AI agent developer gig",
        ],
        "hackathon": [
            "AI hackathon 2026 prizes remote",
            "agent hackathon blockchain 2026",
            "LLM AI coding challenge prize 2026",
        ],
        "grants": [
            "Starknet ecosystem grant 2026",
            "Hedera grant program AI agent",
            "Ethereum foundation grant AI",
            "AI agent research grant 2026",
        ],
        "bounties": [
            "GitHub bounty AI agent tool",
            "open source bounty program AI 2026",
            "bug bounty AI platform security",
        ],
        "gigs": [
            "hire AI agent developer autonomous",
            "freelance AI automation consulting",
            "AI agent custom build contract work",
        ],
    }

    queries = query_sets.get(focus, query_sets["all"])
    all_results = []

    with DDGS() as ddgs:
        for q in queries[:4]:
            try:
                for r in ddgs.text(q, max_results=5):
                    all_results.append({
                        "query": q,
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", ""),
                    })
            except Exception as e:
                all_results.append({"query": q, "error": str(e)})

    # Score by revenue potential
    scored = []
    for r in all_results:
        if "error" in r:
            continue
        title_lower = (r.get("title", "") + " " + r.get("snippet", "")).lower()
        score = 0
        if any(w in title_lower for w in ["$", "prize", "bounty", "grant", "reward", "paid", "earn"]):
            score += 30
        if any(w in title_lower for w in ["hackathon", "challenge", "competition"]):
            score += 20
        if any(w in title_lower for w in ["ai", "agent", "autonomous", "llm", "claude"]):
            score += 15
        if any(w in title_lower for w in ["starknet", "hedera", "blockchain", "defi", "cairo"]):
            score += 10
        if any(w in title_lower for w in ["2026", "2025", "open", "apply", "deadline"]):
            score += 10
        if any(w in title_lower for w in ["remote", "online", "global"]):
            score += 5
        r["relevance_score"] = score
        scored.append(r)

    scored.sort(key=lambda x: x["relevance_score"], reverse=True)
    top = scored[:10]

    lines = [f"**Bounty Hunt Results ({len(scored)} found, top {len(top)} shown):**\n"]
    for i, r in enumerate(top, 1):
        lines.append(f"{i}. [{r['relevance_score']}pts] **{r['title']}**")
        lines.append(f"   {r['url']}")
        lines.append(f"   {r.get('snippet', '')[:120]}")
        lines.append("")

    return {
        "success": True,
        "data": top,
        "message": "\n".join(lines),
    }


async def quick_gig_scan(params: Dict[str, Any]) -> Dict:
    """Fast scan freelance platforms for AI agent gigs."""
    queries = [
        "site:upwork.com AI agent developer autonomous 2026",
        "site:toptal.com AI agent automation",
        "AI agent freelance contract work remote 2026",
    ]

    results = []
    with DDGS() as ddgs:
        for q in queries:
            try:
                for r in ddgs.text(q, max_results=3):
                    results.append({
                        "platform": q.split("site:")[-1].split(" ")[0] if "site:" in q else "web",
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", ""),
                    })
            except Exception as e:
                results.append({"platform": "error", "error": str(e)})

    valid = [r for r in results if "error" not in r]
    lines = [f"**Gig Scan ({len(valid)} found):**\n"]
    for r in valid:
        lines.append(f"- [{r['platform']}] **{r['title']}** — {r['url']}")

    return {
        "success": True,
        "data": valid,
        "message": "\n".join(lines),
    }


TOOLS = [
    {
        "name": "scan_bounties",
        "description": "Scan for hackathons, grants, bounties, and paid opportunities. Focus: all|hackathon|grants|bounties|gigs",
        "handler": scan_bounties,
        "parameters": {
            "type": "object",
            "properties": {
                "focus": {
                    "type": "string",
                    "description": "Focus area: all, hackathon, grants, bounties, gigs",
                    "default": "all",
                },
            },
        },
    },
    {
        "name": "quick_gig_scan",
        "description": "Fast scan freelance platforms for AI agent gigs and contract work.",
        "handler": quick_gig_scan,
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
]
