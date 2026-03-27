"""Deal Flow Radar — Scans multiple sources for revenue opportunities.

Aggregates signals from HN, ProductHunt, GitHub Trending, and web search
to surface: freelance gigs, underserved niches, consulting demand, and
tools ripe for productization.

This is Wave's revenue-generation intelligence layer.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("openclaw.skills.deal_flow")

DEAL_LOG = Path(__file__).parent.parent / "memory" / "deal_flow.jsonl"

REVENUE_KEYWORDS = {
    "high": ["hiring", "paying", "contract", "freelance", "consulting", "enterprise",
             "b2b", "revenue", "saas", "api", "monetize", "subscription", "pricing"],
    "medium": ["launch", "startup", "automation", "agent", "llm", "gpt", "claude",
               "ai", "workflow", "integration", "platform", "deploy"],
    "low": ["open source", "tool", "framework", "library", "sdk", "cli"]
}

FOCUS_QUERIES = {
    "ai_consulting": ["hiring AI consultant 2026", "need AI integration contractor", "AI automation agency"],
    "saas": ["wish there was a tool for", "paying too much for", "looking for alternative to"],
    "freelance": ["freelance AI developer remote contract", "AI project contract work"],
    "arbitrage": ["white label AI solution", "AI wrapper business opportunity", "underserved AI niche"],
}

TOOL_SPEC = {
    "name": "deal_flow",
    "description": "Revenue opportunity radar. Scans HN, ProductHunt, GitHub, and web for actionable money-making signals. Params: focus (ai_consulting|saas|freelance|arbitrage), depth (quick|deep).",
    "parameters": {
        "type": "object",
        "properties": {
            "focus": {
                "type": "string",
                "enum": ["ai_consulting", "saas", "freelance", "arbitrage"],
                "default": "ai_consulting",
                "description": "Revenue angle to optimize for"
            },
            "depth": {
                "type": "string",
                "enum": ["quick", "deep"],
                "default": "quick",
                "description": "quick=HN+PH only, deep=all sources+web search"
            }
        }
    }
}


def _score_signal(text: str) -> int:
    """Score a text signal by revenue keyword density."""
    lower = text.lower()
    score = 0
    score += sum(3 for kw in REVENUE_KEYWORDS["high"] if kw in lower)
    score += sum(2 for kw in REVENUE_KEYWORDS["medium"] if kw in lower)
    score += sum(1 for kw in REVENUE_KEYWORDS["low"] if kw in lower)
    return score


def _classify(text: str) -> str:
    """Classify opportunity type."""
    lower = text.lower()
    if any(kw in lower for kw in ["hiring", "contract", "freelance", "consulting"]):
        return "💰 DIRECT_REVENUE"
    if any(kw in lower for kw in ["launch", "startup", "saas", "pricing"]):
        return "🎯 MARKET_GAP"
    if any(kw in lower for kw in ["agent", "automation", "workflow", "integration"]):
        return "🔧 BUILD_OPPORTUNITY"
    if any(kw in lower for kw in ["trending", "star", "fork"]):
        return "📈 RISING_WAVE"
    return "📡 SIGNAL"


def _log_scan(focus: str, count: int, top_signals: list):
    """Persist scan results for pattern tracking over time."""
    try:
        DEAL_LOG.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.utcnow().isoformat(),
            "focus": focus,
            "signals_found": count,
            "top_3": [s.get("signal", "")[:80] for s in top_signals[:3]]
        }
        with open(DEAL_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


async def execute(params: Dict[str, Any]) -> Dict[str, Any]:
    """Main execution — scan sources, score, rank, return actionable intel."""
    focus = params.get("focus", "ai_consulting")
    depth = params.get("depth", "quick")

    # Import sibling skills dynamically
    from skills_handler import execute_skill

    signals: List[Dict] = []

    # === Source 1: Hacker News ===
    try:
        hn_result = await execute_skill("hn_top", {})
        hn_text = hn_result if isinstance(hn_result, str) else json.dumps(hn_result)
        for line in hn_text.split("\n"):
            line = line.strip()
            if len(line) < 15:
                continue
            score = _score_signal(line)
            if score >= 3:
                signals.append({
                    "source": "HN",
                    "signal": line[:200],
                    "score": score,
                    "type": _classify(line)
                })
    except Exception as e:
        logger.warning(f"HN scan failed: {e}")

    # === Source 2: ProductHunt ===
    try:
        ph_result = await execute_skill("ph_today", {})
        ph_text = ph_result if isinstance(ph_result, str) else json.dumps(ph_result)
        for line in ph_text.split("\n"):
            line = line.strip()
            if len(line) < 15:
                continue
            score = _score_signal(line)
            if score >= 2:
                signals.append({
                    "source": "PH",
                    "signal": line[:200],
                    "score": score + 1,  # PH bias: newer = more actionable
                    "type": _classify(line)
                })
    except Exception as e:
        logger.warning(f"PH scan failed: {e}")

    # === Source 3: GitHub Trending (deep only) ===
    if depth == "deep":
        try:
            gh_result = await execute_skill("gh_trending_repos", {})
            gh_text = gh_result if isinstance(gh_result, str) else json.dumps(gh_result)
            for line in gh_text.split("\n"):
                line = line.strip()
                if len(line) < 15:
                    continue
                score = _score_signal(line)
                if score >= 2:
                    signals.append({
                        "source": "GH",
                        "signal": line[:200],
                        "score": score,
                        "type": _classify(line)
                    })
        except Exception as e:
            logger.warning(f"GH scan failed: {e}")

        # === Source 4: Web Search for direct opportunities ===
        try:
            queries = FOCUS_QUERIES.get(focus, FOCUS_QUERIES["ai_consulting"])
            for q in queries[:1]:  # One query to stay fast
                ws_result = await execute_skill("web_search", {"query": q})
                ws_text = ws_result if isinstance(ws_result, str) else json.dumps(ws_result)
                for line in ws_text.split("\n")[:15]:
                    line = line.strip()
                    if len(line) < 20:
                        continue
                    score = _score_signal(line)
                    signals.append({
                        "source": "WEB",
                        "signal": line[:200],
                        "score": max(score, 4),  # Web results are pre-filtered by query
                        "type": "💰 DIRECT_REVENUE"
                    })
        except Exception as e:
            logger.warning(f"Web scan failed: {e}")

    # === Deduplicate & Rank ===
    seen = set()
    unique = []
    for s in sorted(signals, key=lambda x: x["score"], reverse=True):
        key = re.sub(r'[^a-z0-9]', '', s["signal"].lower())[:50]
        if key not in seen:
            seen.add(key)
            unique.append(s)

    # === Log for historical tracking ===
    _log_scan(focus, len(unique), unique)

    # === Format Output ===
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    header = f"\n{'='*55}\n  DEAL FLOW RADAR — {now}\n  Focus: {focus.upper()} | Depth: {depth} | Signals: {len(unique)}\n{'='*55}\n"

    body = ""
    for i, s in enumerate(unique[:25], 1):
        body += f"\n{s['type']} [{s['source']}] score:{s['score']}\n  {s['signal']}\n"

    if not unique:
        body = "\n  No high-signal opportunities in this scan.\n  Try: depth=deep or different focus.\n"

    footer = f"\n{'─'*55}\n"
    footer += "Actions:\n"
    footer += "  • deal_flow focus=saas        → SaaS gap analysis\n"
    footer += "  • deal_flow focus=freelance    → Contract opportunities\n"
    footer += "  • deal_flow focus=arbitrage    → Resell/white-label plays\n"
    footer += "  • deal_flow depth=deep         → Full scan (HN+PH+GH+Web)\n"
    footer += f"{'─'*55}\n"

    return {
        "success": True,
        "data": {
            "focus": focus,
            "depth": depth,
            "total_signals": len(unique),
            "opportunities": unique[:25],
            "scan_time": now
        },
        "message": header + body + footer
    }
