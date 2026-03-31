"""Revenue Scanner — finds monetizable gaps across tech ecosystems.

Scans HN, ProductHunt, GitHub trending, HuggingFace to identify
micro-SaaS gaps, underserved niches, and cloneable products with
validated demand. Scores by effort/reward ratio.
"""

from __future__ import annotations
import json
import subprocess
import logging
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger("openclaw.revenue_scanner")


def _run_skill(name: str, params: dict) -> str:
    try:
        result = subprocess.run(
            ["python3", "skill_executor.py", name, json.dumps(params)],
            capture_output=True, text=True, timeout=45,
            cwd="/home/manuel/bluewave/openclaw-skill"
        )
        return result.stdout
    except Exception as e:
        logger.warning(f"Skill {name} failed: {e}")
        return ""


def _score(title: str, desc: str, source: str) -> int:
    s = 50
    combined = (title + " " + desc).lower()
    for kw in ["api", "saas", "paid", "subscription", "pricing", "b2b", "enterprise",
                "billing", "payment", "automat", "workflow", "dashboard", "analytic",
                "monitor", "deploy", "devtool", "infra", "integrat"]:
        if kw in combined: s += 7
    for kw in ["ai", "llm", "agent", "gpt", "claude", "automation", "no-code",
                "scraping", "data", "security", "compliance", "seo", "rag"]:
        if kw in combined: s += 6
    for kw in ["open-source", "cli", "tool", "wrapper", "template", "sdk", "plugin"]:
        if kw in combined: s += 4
    s += {"ph": 12, "hn": 8, "gh": 5, "hf": 7}.get(source, 0)
    return min(s, 100)


def _parse(raw: str, source: str) -> list:
    opps = []
    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line or len(line) < 15:
            continue
        sc = _score(line[:100], line, source)
        if sc >= 55:
            opps.append({"title": line[:140], "score": sc, "source": source})
    return opps


async def run(params: Dict[str, Any]) -> Dict[str, Any]:
    focus = params.get("focus", "ai tools")
    min_score = params.get("min_score", 58)

    all_opps = []
    sources = [
        ("ph", "ph_today", {}),
        ("hn", "hn_top", {}),
        ("gh", "gh_trending_repos", {}),
        ("hf", "hf_trending", {"category": "text-generation"}),
    ]

    for src_key, skill_name, skill_params in sources:
        raw = _run_skill(skill_name, skill_params)
        all_opps.extend(_parse(raw, src_key))

    all_opps.sort(key=lambda x: x["score"], reverse=True)
    filtered = [o for o in all_opps if o["score"] >= min_score]
    top = filtered[:12]

    src_labels = {"ph": "ProductHunt", "hn": "HackerNews", "gh": "GitHub", "hf": "HuggingFace"}

    lines = [
        f"{'='*60}",
        f" REVENUE SCANNER — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"{'='*60}",
        f"Focus: {focus} | Threshold: {min_score} | Hits: {len(filtered)}",
        "",
    ]

    for i, opp in enumerate(top, 1):
        lines.append(f"#{i} [{opp['score']}/100] [{src_labels.get(opp['source'], '?')}]")
        lines.append(f"   {opp['title']}")
        if i <= 3:
            lines.append(f"   → Strategy: Build focused SaaS wrapping this validated demand")
            lines.append(f"   → Pricing: Freemium + $29-99/mo pro tiers")
            lines.append(f"   → MVP timeline: 1-2 weeks with AI-assisted dev")
        lines.append("")

    if not top:
        lines.append("No opportunities above threshold. Lower min_score or broaden focus.")

    lines.append(f"{'='*60}")
    report = "\n".join(lines)

    return {"success": True, "data": report, "message": f"Found {len(filtered)} revenue opportunities"}
