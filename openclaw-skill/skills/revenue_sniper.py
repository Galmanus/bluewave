import json, os, subprocess, sys, re
from datetime import datetime

def run_skill(name, params):
    """Run another skill and return parsed result."""
    r = subprocess.run(
        [sys.executable, "skill_executor.py", name, json.dumps(params)],
        capture_output=True, text=True, timeout=60,
        cwd="/home/manuel/bluewave/openclaw-skill"
    )
    try:
        return json.loads(r.stdout)
    except:
        return {"raw": r.stdout[:2000], "error": r.stderr[:500]}

def execute(params):
    vertical = params.get("vertical", "AI tools for developers")
    depth = params.get("depth", "standard")
    budget = params.get("max_budget", "$500")

    signals = {}

    # 1. Demand signals - people in pain
    for q in [f"{vertical} frustrated", f"{vertical} alternative needed"]:
        r = run_skill("web_search", {"query": f"site:reddit.com {q} 2025 2026"})
        signals[f"reddit_{q[:25]}"] = r

    # 2. HN signal - builder demand
    hn = run_skill("web_search", {"query": f"site:news.ycombinator.com Ask HN {vertical} 2025"})
    signals["hn_demand"] = hn

    # 3. Supply landscape
    supply = run_skill("web_search", {"query": f"{vertical} tools pricing comparison 2026"})
    signals["existing_supply"] = supply

    # 4. Trend momentum
    trends = run_skill("google_trends", {"query": vertical})
    signals["trend_momentum"] = trends

    # 5. Recent launches
    ph = run_skill("web_search", {"query": f"site:producthunt.com {vertical} 2025 2026"})
    signals["ph_launches"] = ph

    # Synthesize signals
    pain_points = []
    competitors = []

    for key, data in signals.items():
        if isinstance(data, dict):
            raw = json.dumps(data)[:3000]
            for pattern in [r'frustrat\w+', r'wish\s+\w+', r'need\s+a\s+\w+',
                          r'looking\s+for', r'alternative\s+to', r'broken',
                          r'expensive', r'slow', r'unreliable', r'terrible',
                          r'hate\s+\w+', r'sucks', r'overpriced', r'clunky']:
                matches = re.findall(pattern, raw, re.IGNORECASE)
                pain_points.extend(matches)
            for pattern in [r'\$\d+[/\w]*', r'\b[A-Z][a-z]+(?:ly|io|ai|app|ify)\b']:
                matches = re.findall(pattern, raw)
                competitors.extend(matches[:5])

    # Frequency analysis
    pain_freq = {}
    for p in pain_points:
        k = p.lower().strip()
        pain_freq[k] = pain_freq.get(k, 0) + 1

    top_pains = sorted(pain_freq.items(), key=lambda x: -x[1])[:10]
    unique_competitors = list(set(competitors))[:15]

    # Scoring
    demand_score = min(10, len(pain_points) / 2)
    competition_score = max(1, 10 - len(unique_competitors))
    trend_score = 7
    if isinstance(signals.get("trend_momentum"), dict):
        t_raw = json.dumps(signals["trend_momentum"])
        if "rising" in t_raw.lower() or "breakout" in t_raw.lower():
            trend_score = 9

    composite = round((demand_score * 0.4 + competition_score * 0.3 + trend_score * 0.3), 1)

    # 72-hour blitz plan
    lead_pain = top_pains[0][0] if top_pains else vertical
    action_plan = [
        {"hour": "0-4", "action": f"Validate: DM 10 Reddit/HN users who complained about '{lead_pain}'"},
        {"hour": "4-12", "action": f"Build landing page targeting '{lead_pain}' with email capture + pricing"},
        {"hour": "12-24", "action": f"Launch: post to 3 subreddits + HN Show. Budget {budget} for ads"},
        {"hour": "24-48", "action": "Collect signups, run 5 discovery calls, refine positioning"},
        {"hour": "48-72", "action": "Ship MVP or concierge version. Close first paying customer."}
    ]

    # Revenue model
    if len(unique_competitors) > 8:
        pricing_strategy = "Undercut: $19/mo (competitors are $40+). Win on price, expand on value."
        target_mrr = "$2,000-$8,000"
    elif len(unique_competitors) > 3:
        pricing_strategy = "Mid-market: $39/mo. Differentiate on UX and speed."
        target_mrr = "$3,000-$10,000"
    else:
        pricing_strategy = "Premium: $79/mo. Low competition = price power. Own the niche."
        target_mrr = "$5,000-$20,000"

    return {
        "vertical": vertical,
        "analysis_date": datetime.now().isoformat()[:10],
        "opportunity_score": f"{composite}/10",
        "verdict": "STRONG" if composite >= 7 else "MODERATE" if composite >= 5 else "WEAK",
        "scores": {
            "demand_signal_strength": f"{demand_score}/10",
            "competition_gap": f"{competition_score}/10",
            "trend_momentum": f"{trend_score}/10"
        },
        "top_pain_points": top_pains,
        "known_competitors": unique_competitors,
        "raw_signal_count": len(pain_points),
        "action_plan_72h": action_plan,
        "revenue_model": {
            "strategy": pricing_strategy,
            "target_mrr_90_days": target_mrr,
            "channels": "Reddit + HN + cold email to people who complained publicly"
        },
        "signal_sources": list(signals.keys())
    }
