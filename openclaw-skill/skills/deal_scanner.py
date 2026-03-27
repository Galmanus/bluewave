"""
deal_scanner - Revenue Intelligence Engine

Scans GitHub bounties, help-wanted issues, and sponsored repos for
monetizable opportunities. Scores by effort/reward ratio and skill fit.

Usage:
  skill_executor.py deal_scanner '{"focus": "ai automation", "min_value": 500}'
  skill_executor.py deal_scanner '{"focus": "python api", "min_value": 200, "max_results": 20}'
"""

import json
import urllib.request
import urllib.parse
import os
import re
from datetime import datetime


def run(params):
    focus = params.get("focus", "ai automation")
    min_value = params.get("min_value", 500)
    max_results = params.get("max_results", 15)

    sources = [
        {
            "name": "GitHub Bounties",
            "url": (
                "https://api.github.com/search/issues?q="
                + urllib.parse.quote(focus + " label:bounty state:open")
                + "&sort=created&order=desc&per_page=" + str(max_results)
            ),
            "type": "bounty",
        },
        {
            "name": "GitHub Help Wanted",
            "url": (
                "https://api.github.com/search/issues?q="
                + urllib.parse.quote(focus + ' label:"help wanted" state:open')
                + "&sort=created&order=desc&per_page=" + str(max_results)
            ),
            "type": "oss_lead",
        },
    ]

    all_deals = []
    errors = []

    headers = {
        "User-Agent": "Wave-DealScanner/1.0",
        "Accept": "application/vnd.github.v3+json",
    }
    gh_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if gh_token:
        headers["Authorization"] = "token " + gh_token

    for source in sources:
        try:
            req = urllib.request.Request(source["url"], headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
                items = data.get("items", []) if isinstance(data, dict) else data

                for item in items[:max_results]:
                    title = item.get("title", "")
                    body = (item.get("body", "") or "")[:500]
                    url = item.get("html_url", "")
                    labels = [l["name"] for l in item.get("labels", [])]
                    repo = item.get("repository_url", "").replace(
                        "https://api.github.com/repos/", ""
                    )
                    created = item.get("created_at", "")
                    comments = item.get("comments", 0)

                    # Extract dollar amounts from title/body
                    amounts = re.findall(r"\$([\d,]+(?:\.\d{2})?)", title + " " + body)
                    estimated_value = max(
                        [float(a.replace(",", "")) for a in amounts], default=0
                    )

                    # Score: higher = better opportunity
                    score = 0
                    if estimated_value >= min_value:
                        score += 40
                    elif estimated_value > 0:
                        score += 20

                    labels_lower = str(labels).lower()
                    if "bounty" in labels_lower:
                        score += 25
                    if "paid" in labels_lower or "sponsored" in labels_lower:
                        score += 20
                    if comments < 3:
                        score += 15

                    text_lower = (title + " " + body).lower()
                    if any(kw in text_lower for kw in ["python", "api", "automation", "agent", "llm", "ai"]):
                        score += 15
                    if any(kw in text_lower for kw in ["urgent", "asap", "immediately"]):
                        score += 10

                    # Freshness bonus
                    if created:
                        try:
                            age_days = (
                                datetime.utcnow()
                                - datetime.strptime(created[:10], "%Y-%m-%d")
                            ).days
                            if age_days <= 3:
                                score += 15
                            elif age_days <= 7:
                                score += 10
                            elif age_days <= 14:
                                score += 5
                        except Exception:
                            pass

                    all_deals.append({
                        "title": title,
                        "source": source["name"],
                        "type": source["type"],
                        "repo": repo,
                        "url": url,
                        "estimated_value": estimated_value,
                        "labels": labels,
                        "comments": comments,
                        "score": score,
                        "created": created[:10] if created else "unknown",
                    })
        except Exception as e:
            errors.append(source["name"] + ": " + str(e)[:100])

    # Sponsored repos with open issues — ecosystem plays
    try:
        repo_url = (
            "https://api.github.com/search/repositories?q="
            + urllib.parse.quote(focus + " bounty OR sponsor OR paid")
            + "&sort=updated&order=desc&per_page=5"
        )
        req = urllib.request.Request(repo_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            for item in data.get("items", []):
                if item.get("has_issues") and item.get("open_issues_count", 0) > 0:
                    desc = (item.get("description") or "No description")[:80]
                    has_sponsors = item.get("has_sponsors_listing", False)
                    stars = item.get("stargazers_count", 0)
                    all_deals.append({
                        "title": "[REPO] " + item["full_name"] + " — " + desc,
                        "source": "GitHub Sponsored Repos",
                        "type": "ecosystem",
                        "repo": item["full_name"],
                        "url": item["html_url"],
                        "estimated_value": 0,
                        "labels": ["has_sponsor" if has_sponsors else "no_sponsor"],
                        "comments": item.get("open_issues_count", 0),
                        "score": 10 + (15 if has_sponsors else 0) + min(stars // 100, 20),
                        "created": (item.get("updated_at") or "")[:10],
                    })
    except Exception as e:
        errors.append("Repo scan: " + str(e)[:100])

    # Sort by score descending
    all_deals.sort(key=lambda x: x["score"], reverse=True)
    all_deals = all_deals[:max_results]

    # Build report
    tier_a = [d for d in all_deals if d["score"] >= 50]
    tier_b = [d for d in all_deals if 25 <= d["score"] < 50]
    tier_c = [d for d in all_deals if d["score"] < 25]

    lines = [
        "## Deal Scanner Results",
        "**Focus:** " + focus + " | **Min Value:** $" + str(min_value)
        + " | **Found:** " + str(len(all_deals)) + " opportunities",
        "",
    ]

    if tier_a:
        lines.append("### TIER A — High Priority")
        for d in tier_a:
            val = " | **$" + format(d["estimated_value"], ",.0f") + "**" if d["estimated_value"] else ""
            lines.append(
                "- [" + str(d["score"]) + "] **" + d["title"][:80] + "**" + val
            )
            lines.append(
                "  " + d["source"] + " | " + d["created"]
                + " | " + str(d["comments"]) + " comments"
            )
            lines.append("  " + d["url"])
            lines.append("")

    if tier_b:
        lines.append("### TIER B — Worth Evaluating")
        for d in tier_b:
            val = " | $" + format(d["estimated_value"], ",.0f") if d["estimated_value"] else ""
            lines.append(
                "- [" + str(d["score"]) + "] " + d["title"][:80] + val
            )
            lines.append("  " + d["source"] + " | " + d["created"])
            lines.append("  " + d["url"])
            lines.append("")

    if tier_c:
        lines.append("### TIER C — Low Signal")
        for d in tier_c:
            lines.append("- [" + str(d["score"]) + "] " + d["title"][:60])
            lines.append("  " + d["url"])
            lines.append("")

    if errors:
        lines.append("---")
        lines.append("**Errors:** " + "; ".join(errors))

    lines.append("")
    lines.append("---")
    lines.append(
        "*Scanned at " + datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC") + "*"
    )

    report = "\n".join(lines)

    return {
        "status": "ok",
        "total_found": len(all_deals),
        "tier_a": len(tier_a),
        "tier_b": len(tier_b),
        "tier_c": len(tier_c),
        "report": report,
    }
