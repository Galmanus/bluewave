"""revenue_radar — Multi-Source Revenue Intelligence Engine v2.

Scans GitHub bounties, HN trends, ProductHunt launches, and freelance signals
to surface ranked monetizable opportunities with effort/revenue estimates.

Revenue pipeline: revenue_radar → put_analyze → kill_chain_plan → build → ship

Usage:
  python3 skill_executor.py revenue_radar '{}'
  python3 skill_executor.py revenue_radar '{"focus": "ai agents", "min_score": 4}'
  python3 skill_executor.py revenue_radar '{"focus": "web3 security", "mode": "bounties"}'
"""

import json
import re
import httpx
from datetime import datetime
from typing import Any, Dict, List

DESCRIPTION = "Multi-source revenue intelligence — GitHub bounties, HN trends, PH launches. Returns scored opportunities with revenue/effort estimates."


# ── Data Fetchers ─────────────────────────────────────────────

async def _fetch_json(url: str, headers: dict = None, timeout: float = 12) -> Any:
    h = {"User-Agent": "Wave-RevenueRadar/2.0", "Accept": "application/json"}
    if headers:
        h.update(headers)
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url, headers=h)
            resp.raise_for_status()
            return resp.json()
    except Exception:
        return None


async def _scan_github_bounties(focus: str, max_items: int = 10) -> List[dict]:
    """Find paid bounties on GitHub matching focus area."""
    deals = []
    from urllib.parse import quote
    query = quote(focus + " label:bounty state:open")
    url = "https://api.github.com/search/issues?q=" + query + "&sort=created&order=desc&per_page=" + str(max_items)
    data = await _fetch_json(url)
    if not data or "items" not in data:
        return deals
    for item in data["items"][:max_items]:
        title = item.get("title", "")
        body = (item.get("body", "") or "")[:500]
        html_url = item.get("html_url", "")
        repo = item.get("repository_url", "").replace("https://api.github.com/repos/", "")
        amounts = re.findall(r"\$(\d[\d,]*)", title + " " + body)
        value = max([float(a.replace(",", "")) for a in amounts], default=0)
        deals.append({
            "source": "GitHub", "type": "BOUNTY",
            "title": title[:120], "url": html_url,
            "repo": repo, "value_usd": value, "signal_score": 0,
        })
    return deals


async def _scan_github_help_wanted(focus: str, max_items: int = 8) -> List[dict]:
    """Find help-wanted issues — potential consulting leads."""
    deals = []
    from urllib.parse import quote
    query = quote(focus + ' label:"help wanted" state:open')
    url = "https://api.github.com/search/issues?q=" + query + "&sort=comments&order=desc&per_page=" + str(max_items)
    data = await _fetch_json(url)
    if not data or "items" not in data:
        return deals
    for item in data["items"][:max_items]:
        title = item.get("title", "")
        html_url = item.get("html_url", "")
        comments = item.get("comments", 0)
        repo = item.get("repository_url", "").replace("https://api.github.com/repos/", "")
        deals.append({
            "source": "GitHub", "type": "OSS-LEAD",
            "title": title[:120], "url": html_url,
            "repo": repo, "value_usd": 0, "signal_score": 0,
            "comments": comments,
        })
    return deals


async def _scan_github_sponsors(focus: str, max_items: int = 5) -> List[dict]:
    """Find sponsored repos with open needs — money is already flowing."""
    deals = []
    from urllib.parse import quote
    query = quote(focus + " is:public has:funding")
    url = "https://api.github.com/search/repositories?q=" + query + "&sort=updated&order=desc&per_page=" + str(max_items)
    data = await _fetch_json(url)
    if not data or "items" not in data:
        return deals
    for item in data["items"][:max_items]:
        name = item.get("full_name", "")
        desc = (item.get("description", "") or "")[:100]
        html_url = item.get("html_url", "")
        stars = item.get("stargazers_count", 0)
        open_issues = item.get("open_issues_count", 0)
        deals.append({
            "source": "GitHub", "type": "SPONSORED-REPO",
            "title": name + " — " + desc,
            "url": html_url, "repo": name,
            "value_usd": 0, "signal_score": 0,
            "stars": stars, "open_issues": open_issues,
        })
    return deals


async def _scan_hn(max_items: int = 25) -> List[dict]:
    """Scan HN top stories for trends and opportunities."""
    deals = []
    top_ids = await _fetch_json("https://hacker-news.firebaseio.com/v0/topstories.json")
    if not top_ids:
        return deals
    for sid in top_ids[:max_items]:
        item = await _fetch_json("https://hacker-news.firebaseio.com/v0/item/" + str(sid) + ".json")
        if not item:
            continue
        title = item.get("title", "")
        url = item.get("url", "")
        score = item.get("score", 0)
        descendants = item.get("descendants", 0)
        is_show = title.lower().startswith("show hn")
        is_ask = title.lower().startswith("ask hn")
        is_hiring = "hiring" in title.lower() or "who is hiring" in title.lower()
        if is_hiring:
            t = "HIRING"
        elif is_show:
            t = "SHOW-HN"
        elif is_ask:
            t = "ASK-HN"
        else:
            t = "TREND"
        deals.append({
            "source": "HN", "type": t,
            "title": title[:120],
            "url": url or ("https://news.ycombinator.com/item?id=" + str(sid)),
            "hn_score": score, "hn_comments": descendants,
            "value_usd": 0, "signal_score": 0,
        })
    return deals


async def _scan_ph() -> List[dict]:
    """Scrape ProductHunt for today's launches."""
    deals = []
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(
                "https://www.producthunt.com",
                headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Wave-RevenueRadar/2.0"},
            )
            text = resp.text
            titles = re.findall(r'"name"\s*:\s*"([^"]{5,80})"', text)
            taglines = re.findall(r'"tagline"\s*:\s*"([^"]{5,120})"', text)
            seen = set()
            for i, t in enumerate(titles[:15]):
                if t in seen or t in ("Product Hunt", "Makers", "Products"):
                    continue
                seen.add(t)
                tagline = taglines[i] if i < len(taglines) else ""
                combined = t + (" — " + tagline if tagline else "")
                deals.append({
                    "source": "PH", "type": "LAUNCH",
                    "title": combined[:140],
                    "url": "https://www.producthunt.com",
                    "value_usd": 0, "signal_score": 0,
                })
    except Exception:
        pass
    return deals


# ── Scoring Engine ────────────────────────────────────────────

SIGNAL_MATRIX = [
    (["api", "sdk", "integration", "webhook", "endpoint", "rest", "graphql"], 3, "API"),
    (["saas", "subscription", "recurring", "pricing", "plan", "tier", "mrr", "arr"], 4, "SAAS"),
    (["ai", "llm", "gpt", "claude", "agent", "automation", "ml", "openai", "langchain", "rag"], 3, "AI"),
    (["bounty", "reward", "paid", "sponsor", "fund", "grant", "prize", "contest"], 5, "PAID"),
    (["tool", "dashboard", "analytics", "monitor", "cli", "workflow", "pipeline", "devtool"], 2, "TOOL"),
    (["scraper", "crawler", "data", "etl", "parser", "extraction", "dataset"], 2, "DATA"),
    (["security", "audit", "vulnerability", "pentest", "compliance", "soc2"], 3, "SEC"),
    (["crypto", "web3", "defi", "blockchain", "nft", "token", "hedera", "solana", "ethereum"], 3, "WEB3"),
    (["marketplace", "platform", "commerce", "payment", "billing", "stripe"], 3, "COMMERCE"),
    (["hiring", "engineer", "developer", "team", "contractor", "freelance"], 3, "HIRING"),
    (["raised", "funding", "seed", "series", "yc", "venture", "investor"], 4, "FUNDED"),
    (["open source", "oss", "mit license", "apache", "contributor"], 2, "OSS"),
]


def _score_opportunity(deal: dict) -> dict:
    """Score a deal based on signal matrix and contextual multipliers."""
    text = (deal.get("title", "") + " " + deal.get("repo", "")).lower()
    score = 0
    tags = []
    for kws, pts, tag in SIGNAL_MATRIX:
        if any(k in text for k in kws):
            score += pts
            tags.append(tag)
    # Value bonus
    if deal.get("value_usd", 0) > 0:
        score += 5
        tags.append("$" + str(int(deal["value_usd"])))
    # Virality bonus
    if deal.get("hn_score", 0) > 300:
        score += 3
        tags.append("VIRAL")
    elif deal.get("hn_score", 0) > 100:
        score += 1
    # Discussion heat
    if deal.get("hn_comments", 0) > 100:
        score += 2
        tags.append("HOT")
    elif deal.get("comments", 0) > 10:
        score += 1
    # Show HN bonus — someone built it, we can build better
    if deal.get("type") == "SHOW-HN":
        score += 1
    # Stars = ecosystem maturity
    if deal.get("stars", 0) > 1000:
        score += 2
        tags.append("POPULAR")
    deal["signal_score"] = score
    deal["tags"] = tags
    return deal


def _estimate(score: int, value_usd: float):
    if value_usd > 0:
        return "$" + str(int(value_usd)), "stated"
    if score >= 14:
        return "$10K-50K", "2-4wk"
    if score >= 11:
        return "$5K-10K", "1-2wk"
    if score >= 8:
        return "$2K-5K", "1wk"
    if score >= 6:
        return "$500-2K", "3-5d"
    if score >= 4:
        return "$100-500", "1-2d"
    return "$50-100", "<1d"


def _generate_angle(deal: dict) -> str:
    """Generate specific outreach/attack angle for a deal."""
    text = deal.get("title", "").lower()
    tags = deal.get("tags", [])
    if "FUNDED" in tags:
        return "Fresh capital = buying mode. Position as AI agent team they don't need to hire."
    if "HIRING" in tags:
        return "Hiring is slow. Offer sprint-based agent delivery as a bridge."
    if "PAID" in tags:
        return "Direct bounty. Claim it, deliver fast, build relationship for repeat work."
    if "SAAS" in tags and "AI" in tags:
        return "AI SaaS = high willingness to pay for agent integrations. Offer SDK/plugin dev."
    if "API" in tags:
        return "API companies need agent wrappers. Build and sell or consult on agent SDK."
    if "SEC" in tags:
        return "Security is trust-critical. Offer audit-as-a-service with automated reporting."
    if "WEB3" in tags:
        return "Web3 projects have treasury funds. Propose smart contract audit or agent tooling."
    if "OSS" in tags:
        return "OSS = community trust. Offer enterprise/hosted version development."
    if "SHOW-HN" in tags:
        return "They built v1. Offer to build the AI-powered v2 or consulting on scaling."
    if "DATA" in tags:
        return "Data projects need pipeline automation. Offer ETL agent or scraping service."
    return "Analyze their stack for automation gaps. Offer targeted agent development."


# ── Main Scanner ──────────────────────────────────────────────

async def revenue_radar(params: Dict[str, Any]) -> Dict:
    """Run full revenue intelligence scan across all sources."""
    focus = params.get("focus", "ai automation python")
    min_score = params.get("min_score", 3)
    max_results = params.get("max_results", 15)
    mode = params.get("mode", "all")  # all, bounties, trends, launches
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    sep = "=" * 62

    all_deals = []
    source_counts = {}

    # Scan sources based on mode
    if mode in ("all", "bounties"):
        bounties = await _scan_github_bounties(focus)
        all_deals.extend(bounties)
        source_counts["GH-Bounties"] = len(bounties)

        help_wanted = await _scan_github_help_wanted(focus)
        all_deals.extend(help_wanted)
        source_counts["GH-HelpWanted"] = len(help_wanted)

        sponsors = await _scan_github_sponsors(focus)
        all_deals.extend(sponsors)
        source_counts["GH-Sponsored"] = len(sponsors)

    if mode in ("all", "trends"):
        hn = await _scan_hn()
        all_deals.extend(hn)
        source_counts["HackerNews"] = len(hn)

    if mode in ("all", "launches"):
        ph = await _scan_ph()
        all_deals.extend(ph)
        source_counts["ProductHunt"] = len(ph)

    # Score everything
    scored = [_score_opportunity(d) for d in all_deals]
    scored = [d for d in scored if d["signal_score"] >= min_score]
    scored.sort(key=lambda x: -x["signal_score"])
    top = scored[:max_results]

    # Build report
    lines = []
    lines.append("")
    lines.append(sep)
    lines.append("  REVENUE RADAR v2 | " + now)
    lines.append("  Focus: " + focus + " | Mode: " + mode)
    src_summary = " | ".join(k + ":" + str(v) for k, v in source_counts.items())
    lines.append("  Sources: " + src_summary)
    lines.append("  Total signals: " + str(len(all_deals)) + " | Above threshold: " + str(len(scored)))
    lines.append(sep)

    if not top:
        lines.append("")
        lines.append("  No opportunities above threshold (" + str(min_score) + ").")
        lines.append("  Try: revenue_radar '{\"focus\": \"broader terms\", \"min_score\": 2}'")
        report = "\n".join(lines)
        return {"status": "empty", "report": report, "plays": 0, "scanned": len(all_deals)}

    lines.append("")
    lines.append("_" * 62)
    lines.append("  TOP " + str(len(top)) + " REVENUE PLAYS")
    lines.append("_" * 62)

    plays_data = []
    total_potential = 0

    for i, d in enumerate(top, 1):
        rev, eff = _estimate(d["signal_score"], d.get("value_usd", 0))
        angle = _generate_angle(d)
        tag_str = " ".join("[" + t + "]" for t in d.get("tags", []))
        if d["signal_score"] >= 10:
            pri = "A"
        elif d["signal_score"] >= 7:
            pri = "B"
        elif d["signal_score"] >= 4:
            pri = "C"
        else:
            pri = "D"

        lines.append("")
        lines.append("  #" + str(i) + " [TIER " + pri + "] Score:" + str(d["signal_score"]) + " | " + d["source"] + "/" + d["type"])
        lines.append("     " + tag_str)
        lines.append("     " + d["title"])
        if d.get("url"):
            lines.append("     " + d["url"])
        lines.append("     Est: " + rev + " | Effort: " + eff)
        lines.append("     Angle: " + angle)

        plays_data.append({
            "rank": i, "tier": pri, "score": d["signal_score"],
            "source": d["source"], "type": d["type"],
            "title": d["title"], "url": d.get("url", ""),
            "tags": d.get("tags", []),
            "est_revenue": rev, "est_effort": eff, "angle": angle,
        })

    lines.append("")
    lines.append(sep)
    lines.append("  EXECUTION PIPELINE:")
    lines.append("  1. put_analyze '<top target>'       — deep market analysis")
    lines.append("  2. kill_chain_plan '<market>'        — attack strategy")
    lines.append("  3. draft_cold_email '<prospect>'     — personalized outreach")
    lines.append("  4. create_skill '<tool name>'        — build MVP")
    lines.append("  5. moltbook_post / deploy            — ship it")
    lines.append(sep)
    lines.append("")

    report = "\n".join(lines)
    print(report)

    return {
        "status": "ok",
        "scanned": len(all_deals),
        "qualified": len(scored),
        "plays": len(plays_data),
        "top_play": plays_data[0] if plays_data else None,
        "all_plays": plays_data,
        "report": report,
    }


# ── Legacy compatibility ──────────────────────────────────────

def execute(params):
    """Legacy sync wrapper."""
    import asyncio
    return asyncio.run(revenue_radar(params))


# ── Tool Registration ─────────────────────────────────────────

TOOLS = [
    {
        "name": "revenue_radar",
        "description": "Multi-source revenue intelligence scan. Hits GitHub bounties/help-wanted/sponsors, HN trends, ProductHunt launches. Returns tier-ranked plays with revenue estimates, effort, and outreach angles. Run daily.",
        "handler": revenue_radar,
        "parameters": {
            "type": "object",
            "properties": {
                "focus": {
                    "type": "string",
                    "description": "Search focus keywords (e.g. 'ai agents python', 'web3 security', 'saas api')",
                    "default": "ai automation python",
                },
                "min_score": {
                    "type": "integer",
                    "description": "Minimum signal score to include (default 3, lower = more results)",
                    "default": 3,
                },
                "max_results": {
                    "type": "integer",
                    "description": "Max plays to return (default 15)",
                    "default": 15,
                },
                "mode": {
                    "type": "string",
                    "description": "Scan mode: all, bounties, trends, launches",
                    "default": "all",
                },
            },
        },
    },
]
