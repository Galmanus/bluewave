"""Revenue Scanner — finds pain points people will pay to solve.

Scans Reddit, HN, ProductHunt for buy signals, pricing gaps, and underserved niches.
Outputs ranked micro-SaaS/tool opportunities with estimated MRR potential.
"""

from __future__ import annotations
import asyncio
import json
import re
import logging
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger("openclaw.revenue_scanner")

BUY_SIGNALS = [
    (r"willing to pay", 3), (r"shut up and take my money", 3),
    (r"would pay", 3), (r"take my money", 3), (r"pay for this", 3),
    (r"looking for a tool", 2), (r"any alternative", 2),
    (r"frustrated with", 2), (r"need a solution", 2),
    (r"wish there was", 2), (r"anyone know a", 1),
    (r"\$\d+/mo", 2), (r"budget of", 2),
    (r"horrible UX", 1), (r"overpriced", 2), (r"too expensive", 2),
    (r"switched from", 1), (r"migrating away", 2),
    (r"looking to replace", 2), (r"broken workflow", 2),
    (r"waste.{0,10}hours?", 2), (r"manual process", 1),
    (r"no good .{0,15}(tool|solution|option)", 2),
]

CATEGORY_KEYWORDS = {
    "api": ["api", "endpoint", "webhook", "integration"],
    "plugin": ["plugin", "extension", "addon", "add-on"],
    "automation": ["automat", "workflow", "pipeline", "cron", "schedule"],
    "saas": ["saas", "platform", "dashboard", "subscription"],
    "tool": ["tool", "script", "cli", "utility"],
}

MRR_BASE = {"saas": 2500, "api": 3000, "automation": 2000, "tool": 1000, "plugin": 500}


def _detect_category(text: str) -> str:
    t = text.lower()
    for cat, kws in CATEGORY_KEYWORDS.items():
        if any(kw in t for kw in kws):
            return cat
    return "saas"


def _score_signal(text: str) -> tuple[int, list[str]]:
    total = 0
    matched = []
    for pattern, weight in BUY_SIGNALS:
        if re.search(pattern, text, re.IGNORECASE):
            total += weight
            matched.append(pattern.replace("\\", ""))
    return total, matched


def _estimate_mrr(score: int, category: str) -> int:
    base = MRR_BASE.get(category, 1000)
    return int(base * (score / 40))


def _extract_engagement(text: str) -> int:
    m = re.search(r"(\d+)\s*(points?|upvotes?|comments?|score)", text, re.IGNORECASE)
    return int(m.group(1)) if m else 3


async def _scan_source(skill_mod, source_name: str, params: dict) -> list[dict]:
    """Run a single source skill and extract opportunities."""
    try:
        raw = await skill_mod.run(params)
        if isinstance(raw, dict):
            text = json.dumps(raw, default=str)
        else:
            text = str(raw)
    except Exception as e:
        logger.warning(f"Source {source_name} failed: {e}")
        return []

    opportunities = []
    for line in text.split("\n"):
        line = line.strip()
        if len(line) < 20:
            continue

        buy_score, signals = _score_signal(line)
        category = _detect_category(line)
        engagement = _extract_engagement(line)

        # Include if it has buy signals OR is tool/saas related with engagement
        if buy_score > 0 or (category != "saas" and engagement > 10):
            opp_score = min(buy_score * 12 + min(engagement // 3, 25), 100)
            opportunities.append({
                "source": source_name,
                "signal": line[:250],
                "buy_signals": signals,
                "score": opp_score,
                "category": category,
                "est_mrr": _estimate_mrr(opp_score, category),
                "engagement": engagement,
            })

    return opportunities


async def run(params: Dict[str, Any] = None) -> str:
    params = params or {}
    focus = params.get("focus", "")

    # Import source skills
    sources = {}
    try:
        from skills import reddit_hot
        for sub in ["SaaS", "startups", "Entrepreneur", "selfhosted", "smallbusiness"]:
            sources[f"r/{sub}"] = (reddit_hot, {"subreddit": sub})
    except Exception as e:
        logger.warning(f"Reddit skill unavailable: {e}")

    try:
        from skills import hn_top
        sources["HackerNews"] = (hn_top, {})
    except Exception as e:
        logger.warning(f"HN skill unavailable: {e}")

    try:
        from skills import ph_today
        sources["ProductHunt"] = (ph_today, {})
    except Exception as e:
        logger.warning(f"PH skill unavailable: {e}")

    # Scan all sources
    all_opportunities = []
    for src_name, (mod, prms) in sources.items():
        opps = await _scan_source(mod, src_name, prms)
        all_opportunities.extend(opps)

    # Filter by focus if specified
    if focus:
        all_opportunities = [
            o for o in all_opportunities
            if focus.lower() in o["signal"].lower() or focus.lower() in o["category"]
        ]

    # Rank
    all_opportunities.sort(key=lambda x: x["score"], reverse=True)
    top = all_opportunities[:20]

    total_mrr = sum(o["est_mrr"] for o in top)
    cats = list(set(o["category"] for o in top[:5])) if top else []

    # Format report
    out = []
    out.append("=" * 50)
    out.append("  REVENUE SCANNER REPORT")
    out.append("=" * 50)
    out.append(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    out.append(f"  Sources scanned: {len(sources)}")
    out.append(f"  Total signals: {len(all_opportunities)}")
    out.append(f"  Est. addressable MRR: ${total_mrr:,}")
    if cats:
        out.append(f"  Hot categories: {', '.join(cats)}")
    out.append("")
    out.append("-" * 50)
    out.append("  TOP OPPORTUNITIES")
    out.append("-" * 50)

    for i, opp in enumerate(top[:10], 1):
        out.append("")
        out.append(f"  {i}. [{opp['score']}/100] ~${opp['est_mrr']:,}/mo | {opp['category'].upper()}")
        out.append(f"     Source: {opp['source']}")
        out.append(f"     Signal: {opp['signal'][:160]}")
        if opp["buy_signals"]:
            out.append(f"     Intent: {', '.join(opp['buy_signals'][:4])}")

    if not top:
        out.append("")
        out.append("  No strong buy signals detected in this scan.")
        out.append("  Try: revenue_scanner '{\"focus\": \"automation\"}'")

    out.append("")
    out.append("=" * 50)
    out.append(f"  Run: revenue_scanner '{{\"focus\": \"keyword\"}}' to filter")
    out.append("=" * 50)

    return "\n".join(out)
