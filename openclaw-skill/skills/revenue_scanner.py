"""Revenue Scanner — finds money across the internet.

Scans HN, GitHub, Reddit, ProductHunt for revenue opportunities:
bounties, contract gigs, desperate founders, acquirable micro-SaaS,
and partnership leads. Scores each by estimated revenue × probability.
Returns a ranked hit list.

This is Wave's hunting instinct, automated.
"""

from __future__ import annotations

import json
import logging
import asyncio
import re
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger("openclaw.skills.revenue_scanner")

# --- Scoring engine ---

REVENUE_SIGNALS = {
    "hiring": 15, "contract": 20, "freelance": 18, "bounty": 25,
    "paid": 20, "budget": 18, "$": 12, "revenue": 12, "saas": 14,
    "api": 10, "integration": 8, "automat": 12, "consult": 15,
    "rfp": 22, "looking for": 12, "need help": 15, "developer": 10,
    "acquisition": 18, "sell my": 16, "buy": 8, "partnership": 12,
    "sponsor": 15, "grant": 18, "funding": 10,
    "ai agent": 22, "llm": 15, "claude": 18, "gpt": 12,
    "startup": 8, "mvp": 14, "prototype": 12, "build": 6,
    "struggling": 10, "urgent": 12, "asap": 15,
    "k/mo": 20, "k/yr": 18, "per month": 15, "retainer": 22,
    "technical co-founder": 20, "co-founder": 10,
    "open source": 6, "bounties": 25, "reward": 15,
    "needs automation": 20, "workflow": 10, "no-code": 12,
    "scraping": 14, "data pipeline": 16, "etl": 14,
    "consulting": 18, "advisory": 16, "fractional": 20,
    "mrr": 16, "arr": 14, "churn": 10, "growth": 8,
}

SOURCE_MULTIPLIER = {"hn": 1.3, "github": 1.0, "reddit": 0.9, "ph": 1.15}


def score_opportunity(title: str, source: str, context: str = "") -> int:
    text = (title + " " + context).lower()
    score = 20
    for signal, weight in REVENUE_SIGNALS.items():
        if signal in text:
            score += weight
    score *= SOURCE_MULTIPLIER.get(source, 1.0)
    return min(int(score), 100)


def classify_type(title: str, context: str = "") -> str:
    text = (title + " " + context).lower()
    checks = [
        (["bounty", "reward", "prize"], "BOUNTY"),
        (["hiring", "job", "contract", "freelance", "looking for dev"], "CONTRACT"),
        (["acquisition", "acqui-hire", "buy my", "sell my"], "ACQUISITION"),
        (["partner", "collab", "integration"], "PARTNERSHIP"),
        (["saas", "mrr", "arr", "subscription", "launch"], "MICRO-SAAS"),
        (["ai", "agent", "llm", "gpt", "claude", "automat"], "AI-OPS"),
        (["consult", "advisory", "fractional"], "CONSULTING"),
    ]
    for keywords, label in checks:
        if any(k in text for k in keywords):
            return label
    return "LEAD"


def estimate_value(opp_type: str, score: int) -> str:
    """Rough $/opportunity estimate."""
    base = {
        "BOUNTY": 500, "CONTRACT": 5000, "ACQUISITION": 20000,
        "PARTNERSHIP": 3000, "MICRO-SAAS": 10000, "AI-OPS": 8000,
        "CONSULTING": 6000, "LEAD": 2000,
    }
    val = base.get(opp_type, 1000) * (score / 50)
    if val >= 10000:
        return f"${val/1000:.0f}k"
    return f"${val:,.0f}"


async def _run_skill(skill_name: str, params: dict) -> str:
    """Run a sibling skill."""
    try:
        from skills_handler import execute_skill
        result = await execute_skill(skill_name, params)
        if isinstance(result, dict):
            return json.dumps(result, default=str)
        return str(result)
    except Exception as e:
        return f"[scan-error:{skill_name}] {e}"


def _extract_items(raw: str) -> List[str]:
    """Extract meaningful lines from raw skill output."""
    items = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line or len(line) < 15:
            continue
        if line.startswith(("{", "[")) and ("error" in line.lower() or "success" in line.lower()):
            # Try to extract from JSON
            try:
                data = json.loads(raw)
                if isinstance(data, dict) and "data" in data:
                    inner = data["data"]
                    if isinstance(inner, list):
                        for item in inner:
                            if isinstance(item, dict):
                                t = item.get("title", "") or item.get("name", "") or item.get("text", "")
                                if t:
                                    items.append(t)
                        return items
                    elif isinstance(inner, str):
                        return _extract_items(inner)
            except json.JSONDecodeError:
                pass
            continue
        if line.startswith("==") or line.startswith("--") or line.startswith("##"):
            continue
        items.append(line)
    return items


async def execute(params: Dict[str, Any]) -> str:
    focus = params.get("focus", "all")
    min_score = params.get("min_score", 35)
    limit = params.get("limit", 20)

    # Define scan sources
    scan_tasks = [
        ("hn_top", {}, "hn"),
        ("gh_trending_repos", {}, "github"),
        ("ph_today", {}, "ph"),
    ]

    reddit_map = {
        "all": ["forhire", "startups", "SaaS"],
        "ai": ["MachineLearning", "LocalLLaMA"],
        "saas": ["SaaS", "microsaas", "startups"],
        "contracts": ["forhire", "freelance"],
    }
    for sub in reddit_map.get(focus, reddit_map["all"]):
        scan_tasks.append(("reddit_hot", {"subreddit": sub}, "reddit"))

    # Run all scans concurrently
    async def scan_source(skill_name, skill_params, source_tag):
        raw = await _run_skill(skill_name, skill_params)
        items = _extract_items(raw)
        results = []
        for item in items:
            scr = score_opportunity(item, source_tag)
            if scr >= min_score:
                results.append({
                    "title": item[:250],
                    "score": scr,
                    "source": source_tag.upper(),
                    "type": classify_type(item),
                    "est_value": estimate_value(classify_type(item), scr),
                })
        return results

    all_results = await asyncio.gather(
        *[scan_source(s, p, t) for s, p, t in scan_tasks],
        return_exceptions=True
    )

    opportunities = []
    errors = []
    for i, result in enumerate(all_results):
        if isinstance(result, Exception):
            errors.append(f"{scan_tasks[i][0]}: {result}")
        elif isinstance(result, list):
            opportunities.extend(result)

    # Deduplicate
    seen = set()
    unique = []
    for opp in opportunities:
        key = opp["title"][:60].lower()
        if key not in seen:
            seen.add(key)
            unique.append(opp)

    unique.sort(key=lambda x: x["score"], reverse=True)
    top = unique[:limit]

    # Format
    lines = []
    lines.append(f"\n{'='*72}")
    lines.append(f"  ⚡ REVENUE SCANNER — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"  Focus: {focus.upper()} | Threshold: {min_score} | Hits: {len(unique)}")
    lines.append(f"{'='*72}\n")

    total_est = 0
    for i, opp in enumerate(top, 1):
        bar = "█" * (opp["score"] // 5)
        lines.append(f"  #{i:02d} [{opp['score']:3d}] {bar}")
        lines.append(f"       {opp['type']:12s} | {opp['source']:6s} | {opp['est_value']}")
        lines.append(f"       {opp['title']}")
        lines.append("")
        # Parse est_value back
        v = opp["est_value"].replace("$", "").replace(",", "").replace("k", "000")
        try:
            total_est += float(v)
        except ValueError:
            pass

    lines.append(f"{'─'*72}")
    lines.append(f"  Pipeline value: ${total_est:,.0f} across {len(top)} opportunities")
    if errors:
        lines.append(f"  Scan errors: {len(errors)} sources failed")
    lines.append(f"{'='*72}\n")

    return "\n".join(lines)
