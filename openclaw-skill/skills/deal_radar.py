"""
deal_radar — Aggregates PH, HN, GitHub trending signals to identify
acquirable micro-SaaS, market gaps, and revenue opportunities.
Outputs scored deal cards with MRR ceiling estimates.
"""

import json
import subprocess
import re
from datetime import datetime

SKILL_NAME = "deal_radar"
SKILL_DESCRIPTION = "Scan PH/HN/GitHub for acquirable micro-SaaS and revenue opportunities with scoring"

REVENUE_WORDS = ["saas", "subscription", "api", "platform", "dashboard", "analytics",
                 "automat", "monitor", "deploy", "workflow", "billing", "invoice", "crm"]
TIMING_WORDS = ["ai", "llm", "agent", "mcp", "rag", "vector", "copilot", "autonomous",
                "genai", "fine-tun", "claude", "openai", "cursor"]
SOLO_SIGNALS = ["solo", "indie", "side project", "weekend", "built in", "one person", "bootstrapped", "open source"]
B2B_WORDS = ["enterprise", "team", "collaboration", "compliance", "security", "audit", "b2b", "business"]
ECO_WORDS = ["slack", "github", "notion", "stripe", "shopify", "wordpress", "zapier", "webhook", "plugin", "extension"]


def run_skill(name, params):
    try:
        result = subprocess.run(
            ["python3", "skill_executor.py", name, json.dumps(params)],
            capture_output=True, text=True, timeout=60,
            cwd="/home/manuel/bluewave/openclaw-skill"
        )
        return result.stdout
    except Exception as e:
        return f"Error: {e}"


def score_opportunity(title, description, signals):
    score = 0
    text = f"{title} {description}".lower()

    hits = sum(1 for w in REVENUE_WORDS if w in text)
    score += min(hits * 5, 20)

    hits = sum(1 for w in TIMING_WORDS if w in text)
    score += min(hits * 5, 20)

    if any(s in text for s in SOLO_SIGNALS):
        score += 15

    if any(w in text for w in B2B_WORDS):
        score += 15

    if any(w in text for w in ECO_WORDS):
        score += 10

    score += min(signals.get("engagement_bonus", 0), 20)
    return min(score, 100)


def estimate_mrr_ceiling(title, description):
    text = f"{title} {description}".lower()
    if any(w in text for w in ["enterprise", "compliance", "security", "audit"]):
        return "$50K-200K"
    elif any(w in text for w in ["api", "platform", "infrastructure", "deploy"]):
        return "$20K-100K"
    elif any(w in text for w in ["saas", "dashboard", "analytics", "monitor"]):
        return "$10K-50K"
    elif any(w in text for w in ["plugin", "extension", "tool", "widget"]):
        return "$5K-20K"
    return "$2K-15K"


def categorize(title, description):
    text = f"{title} {description}".lower()
    if any(w in text for w in ["ai", "llm", "agent", "ml", "gpt", "copilot"]):
        return "AI/ML"
    elif any(w in text for w in ["api", "backend", "server", "deploy", "infra"]):
        return "Infrastructure"
    elif any(w in text for w in ["saas", "dashboard", "analytics"]):
        return "SaaS"
    elif any(w in text for w in ["dev", "code", "git", "ide", "debug"]):
        return "DevTools"
    elif any(w in text for w in ["market", "seo", "content", "social", "email"]):
        return "Marketing"
    return "Other"


def parse_entries(raw, source_name):
    entries = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("---") or line.startswith("Top"):
            continue
        match = re.match(r"^\d{1,3}\.\s+(.+)", line)
        if not match:
            continue
        content = match.group(1)

        # Engagement
        vote_match = re.search(r"(\d[\d,]*)\s*(?:upvotes?|votes?|points?|pts?|stars?|\u25b2|\u2b50)", content, re.IGNORECASE)
        engagement = int(vote_match.group(1).replace(",", "")) if vote_match else 5

        is_show = "show hn" in content.lower()

        if " - " in content:
            t, d = content.split(" - ", 1)
        elif ": " in content:
            t, d = content.split(": ", 1)
        else:
            t, d = content[:80], content

        bonus = 0
        if source_name == "ProductHunt":
            bonus = min(engagement // 10, 20)
        elif source_name == "HackerNews":
            bonus = min(engagement // 20, 20) + (10 if is_show else 0)
        elif source_name == "GitHub":
            bonus = min(engagement // 100, 20)

        src = source_name + (" [ShowHN]" if is_show else "")

        entries.append({
            "title": t.strip()[:80],
            "description": d.strip()[:200],
            "source": src,
            "signals": {"engagement_bonus": bonus}
        })
    return entries


def main(params):
    min_score = params.get("min_score", 35)
    max_results = params.get("max_results", 15)
    focus = params.get("focus", "all")

    opportunities = []

    # Gather from 3 sources
    ph_raw = run_skill("ph_today", {})
    opportunities.extend(parse_entries(ph_raw, "ProductHunt"))

    hn_raw = run_skill("hn_top", {})
    opportunities.extend(parse_entries(hn_raw, "HackerNews"))

    gh_raw = run_skill("gh_trending_repos", {})
    opportunities.extend(parse_entries(gh_raw, "GitHub"))

    # Score all
    for opp in opportunities:
        opp["score"] = score_opportunity(opp["title"], opp["description"], opp["signals"])
        opp["category"] = categorize(opp["title"], opp["description"])
        opp["mrr_ceiling"] = estimate_mrr_ceiling(opp["title"], opp["description"])

    # Filter
    if focus != "all":
        focus_map = {"ai": "AI/ML", "saas": "SaaS", "devtools": "DevTools",
                     "infra": "Infrastructure", "marketing": "Marketing"}
        target = focus_map.get(focus, focus)
        opportunities = [o for o in opportunities if o["category"] == target]

    opportunities = [o for o in opportunities if o["score"] >= min_score]
    opportunities.sort(key=lambda x: x["score"], reverse=True)
    opportunities = opportunities[:max_results]

    # Format
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# DEAL RADAR — {now}",
        f"Scanned: ProductHunt + HackerNews + GitHub Trending",
        f"Filter: score >= {min_score} | focus: {focus} | top {max_results}",
        "---", ""
    ]

    if not opportunities:
        lines.append("No opportunities above threshold. Try min_score=20.")
        return "\n".join(lines)

    for i, opp in enumerate(opportunities, 1):
        bar = "\u2588" * (opp["score"] // 10) + "\u2591" * (10 - opp["score"] // 10)
        lines.append(f"### {i}. {opp['title']}")
        lines.append(f"   Source: {opp['source']} | Category: {opp['category']}")
        lines.append(f"   Score: [{bar}] {opp['score']}/100")
        lines.append(f"   MRR Ceiling: {opp['mrr_ceiling']}")
        lines.append(f"   > {opp['description'][:150]}")
        lines.append("")

    avg = sum(o["score"] for o in opportunities) / len(opportunities)
    cats = {}
    for o in opportunities:
        cats[o["category"]] = cats.get(o["category"], 0) + 1

    cat_str = " | ".join(f"{k}: {v}" for k, v in sorted(cats.items(), key=lambda x: -x[1]))

    lines.append("---")
    lines.append(f"**Pipeline:** {len(opportunities)} opportunities | Avg score: {avg:.0f}")
    lines.append(f"**Categories:** {cat_str}")
    lines.append("")
    lines.append("**TOP 3 TO INVESTIGATE:**")
    for o in opportunities[:3]:
        lines.append(f"  -> {o['title']} ({o['mrr_ceiling']})")

    return "\n".join(lines)
