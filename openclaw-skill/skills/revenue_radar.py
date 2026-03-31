"""
revenue_radar — Scans multiple sources for high-value revenue opportunities.
Finds freelance contracts, partnership leads, underserved market gaps.
Returns ranked opportunities with outreach templates.
"""

import json
import subprocess
from datetime import datetime


def run_skill(name, params):
    r = subprocess.run(
        ["python3", "skill_executor.py", name, json.dumps(params)],
        capture_output=True, text=True,
        cwd="/home/manuel/bluewave/openclaw-skill",
        timeout=60
    )
    return r.stdout


TOOL_DEF = {
    "name": "revenue_radar",
    "description": "Scan HN, Reddit, ProductHunt, web for high-value freelance/contract/partnership opportunities. Returns ranked leads with outreach templates.",
    "parameters": {
        "type": "object",
        "properties": {
            "profile": {
                "type": "string",
                "description": "Your skill profile for matching. Default: AI automation, agents, full-stack, consulting"
            },
            "min_budget": {
                "type": "integer",
                "description": "Minimum budget threshold in USD. Default: 1000"
            },
            "sources": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Sources to scan: hn, reddit, ph, web. Default: all"
            }
        }
    }
}


async def execute(params: dict) -> dict:
    profile = params.get("profile", "AI automation, autonomous agents, full-stack dev, strategic consulting")
    budget_floor = params.get("min_budget", 1000)
    sources = params.get("sources", ["hn", "reddit", "ph", "web"])

    results = {
        "scan_time": datetime.now().isoformat(),
        "opportunities": [],
        "raw_signals": [],
        "meta": {"profile": profile, "min_budget": budget_floor}
    }

    # --- HN: hiring threads, freelance, Show HN needing help ---
    if "hn" in sources:
        try:
            hn_data = run_skill("hn_top", "{}")
            results["raw_signals"].append({"source": "HN", "data": hn_data[:800]})
        except Exception as e:
            results["raw_signals"].append({"source": "HN", "error": str(e)})

    # --- Reddit: forhire, freelance, startups, SaaS ---
    if "reddit" in sources:
        for sub in ["forhire", "freelance", "startups"]:
            try:
                rd = run_skill("reddit_hot", json.dumps({"subreddit": sub}))
                # Fix: pass as string since run_skill already dumps
                rd = subprocess.run(
                    ["python3", "skill_executor.py", "reddit_hot", json.dumps({"subreddit": sub})],
                    capture_output=True, text=True,
                    cwd="/home/manuel/bluewave/openclaw-skill", timeout=60
                ).stdout
                results["raw_signals"].append({"source": f"r/{sub}", "data": rd[:600]})
            except:
                pass

    # --- ProductHunt: new launches ---
    if "ph" in sources:
        try:
            ph = run_skill("ph_today", "{}")
            results["raw_signals"].append({"source": "ProductHunt", "data": ph[:600]})
        except:
            pass

    # --- Web: direct searches ---
    if "web" in sources:
        queries = [
            f"freelance contract {profile.split(',')[0].strip()} 2026",
            "AI agent development contract remote",
        ]
        for q in queries:
            try:
                ws = run_skill("web_search", json.dumps({"query": q}))
                ws = subprocess.run(
                    ["python3", "skill_executor.py", "web_search", json.dumps({"query": q})],
                    capture_output=True, text=True,
                    cwd="/home/manuel/bluewave/openclaw-skill", timeout=60
                ).stdout
                results["raw_signals"].append({"source": "web", "query": q, "data": ws[:600]})
            except:
                pass

    # --- Score & rank ---
    high_value_kw = [
        "$", "budget", "paid", "contract", "retainer", "equity", "funding",
        "seed", "revenue", "saas", "ai agent", "automation", "consulting",
        "hire", "looking for", "need", "developer", "engineer", "build"
    ]

    for sig in results["raw_signals"]:
        text = json.dumps(sig).lower()
        score = sum(2 for kw in high_value_kw if kw in text)
        if score >= 3:
            results["opportunities"].append({
                "score": score,
                "source": sig.get("source"),
                "detail": sig.get("data", "")[:400]
            })

    results["opportunities"].sort(key=lambda x: x["score"], reverse=True)
    results["total_signals"] = len(results["raw_signals"])
    results["high_value_count"] = len(results["opportunities"])

    # --- Outreach templates ---
    first_skill = profile.split(",")[0].strip()
    results["outreach_templates"] = {
        "cold_email": (
            f"Subject: I build AI agents that replace manual workflows\n\n"
            f"I noticed [SPECIFIC_DETAIL]. I specialize in {first_skill}.\n\n"
            f"I can [SPECIFIC_DELIVERABLE] in [TIMEFRAME] for [PRICE].\n\n"
            f"15 min this week?\n\n— Manuel"
        ),
        "reddit_dm": (
            f"Hey — saw your post about [TOPIC]. I work in {first_skill} "
            f"and can help. DM me details + budget range."
        ),
        "hn_reply": (
            f"Building in this space ({first_skill}). "
            f"If you need fast execution, email me: [CONTACT]"
        )
    }

    return {"success": True, "data": results}


TOOLS = [
    {
        "name": "revenue_radar",
        "description": "Scan HN, Reddit, ProductHunt, web for high-value freelance/contract/partnership opportunities. Returns ranked leads with outreach templates.",
        "parameters": {
            "profile": "string — your skill profile (default: AI automation, agents, full-stack, consulting)",
            "min_budget": "int — minimum budget threshold in USD (default: 1000)",
            "sources": "list — sources to scan: hn, reddit, ph, web (default: all)",
        },
        "handler": execute,
    }
]
