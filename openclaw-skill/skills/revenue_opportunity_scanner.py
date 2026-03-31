"""
revenue_opportunity_scanner — Wave Skill
Scans HN, Reddit, PH for high-intent buying signals.
Scores and ranks opportunities by revenue potential.
"""

import json
import subprocess
from datetime import datetime


def run_skill(name, params):
    result = subprocess.run(
        ["python3", "skill_executor.py", name, json.dumps(params)],
        capture_output=True, text=True,
        cwd="/home/manuel/bluewave/openclaw-skill"
    )
    try:
        return json.loads(result.stdout)
    except Exception:
        return {"raw": result.stdout[:2000]}


# Buying signal lexicon — tuned for willingness-to-pay indicators
PAY_PHRASES    = ["will pay", "paying for", "budget", "pricing", "enterprise", "b2b", "saas", "subscription", "license"]
URGENCY_PHRASES= ["urgent", "asap", "need now", "this week", "deadline", "immediately", "critical", "blocking"]
PAIN_PHRASES   = ["frustrated", "hate", "broken", "fails", "can't find", "no solution", "impossible", "struggling", "nightmare", "pain"]
SCALE_PHRASES  = ["team", "company", "startup", "employees", "thousands", "millions", "scale", "enterprise", "clients"]
SEEK_PHRASES   = ["is there a", "does anyone know", "looking for", "recommend", "alternative to", "replacement for", "anyone built", "hire"]


def score_opportunity(title, text=""):
    full = (title + " " + (text or "")).lower()
    score = 0
    signals = {}

    pay_hits     = [p for p in PAY_PHRASES     if p in full]
    urgency_hits = [p for p in URGENCY_PHRASES if p in full]
    pain_hits    = [p for p in PAIN_PHRASES    if p in full]
    scale_hits   = [p for p in SCALE_PHRASES   if p in full]
    seek_hit     = any(p in full for p in SEEK_PHRASES)

    score += len(pay_hits)     * 30
    score += len(urgency_hits) * 20
    score += len(pain_hits)    * 15
    score += len(scale_hits)   * 10
    if seek_hit:
        score += 25

    if pay_hits:     signals["pay"]     = pay_hits
    if urgency_hits: signals["urgency"] = urgency_hits
    if pain_hits:    signals["pain"]    = pain_hits
    if scale_hits:   signals["scale"]   = scale_hits
    if seek_hit:     signals["seeking"] = True

    return score, signals


def make_opp(item, source):
    title   = item.get("title") or item.get("name") or ""
    text    = item.get("text") or item.get("selftext") or item.get("tagline") or ""
    url     = item.get("url") or item.get("permalink") or ""
    s, sigs = score_opportunity(title, text)
    return {
        "source":        source,
        "title":         title[:120],
        "snippet":       text[:180].replace("\n", " "),
        "url":           url,
        "revenue_score": s,
        "signals":       sigs,
    }


def execute(params):
    min_score = params.get("min_score", 20)
    limit     = params.get("limit", 12)
    sources   = params.get("sources", ["hn", "entrepreneur", "SaaS", "forhire", "ph"])

    opportunities = []
    errors        = []

    if "hn" in sources:
        try:
            data  = run_skill("hn_top", {})
            items = data if isinstance(data, list) else data.get("stories", data.get("items", []))
            for item in (items or [])[:30]:
                opp = make_opp(item, "HackerNews")
                if opp["revenue_score"] >= min_score:
                    opportunities.append(opp)
        except Exception as e:
            errors.append(f"HN: {e}")

    for sub in [s for s in sources if s not in ("hn", "ph")]:
        try:
            data  = run_skill("reddit_hot", {"subreddit": sub})
            posts = data if isinstance(data, list) else data.get("posts", data.get("results", []))
            for post in (posts or [])[:20]:
                opp = make_opp(post, f"r/{sub}")
                if opp["revenue_score"] >= min_score:
                    opportunities.append(opp)
        except Exception as e:
            errors.append(f"r/{sub}: {e}")

    if "ph" in sources:
        try:
            data  = run_skill("ph_today", {})
            items = data if isinstance(data, list) else data.get("products", data.get("items", []))
            for item in (items or [])[:20]:
                opp = make_opp(item, "ProductHunt")
                if opp["revenue_score"] >= 10:
                    opportunities.append(opp)
        except Exception as e:
            errors.append(f"PH: {e}")

    # Deduplicate + sort
    seen, unique = set(), []
    for o in sorted(opportunities, key=lambda x: x["revenue_score"], reverse=True):
        key = o["title"][:60]
        if key not in seen:
            seen.add(key)
            unique.append(o)

    top = unique[:limit]

    # Human-readable digest
    lines = [f"=== REVENUE OPPORTUNITY SCAN — {datetime.now().strftime('%Y-%m-%d %H:%M')} ===", ""]
    for i, o in enumerate(top, 1):
        sig_str = " | ".join(
            f"{k}={v}" if isinstance(v, list) else k
            for k, v in o["signals"].items()
        )
        lines.append(f"{i:2}. [score:{o['revenue_score']:3d}] [{o['source']}]")
        lines.append(f"    {o['title']}")
        if o["snippet"]:
            lines.append(f"    \"{o['snippet'][:100]}...\"")
        if sig_str:
            lines.append(f"    ↳ signals: {sig_str}")
        if o["url"]:
            lines.append(f"    → {o['url']}")
        lines.append("")

    if not top:
        lines.append("No opportunities above threshold — try lowering min_score.")

    if errors:
        lines.append(f"[warn] partial errors: {'; '.join(errors)}")

    return {
        "timestamp":          datetime.now().isoformat(),
        "scanned_sources":    sources,
        "total_found":        len(unique),
        "top_opportunities":  top,
        "digest":             "\n".join(lines),
        "errors":             errors,
    }
