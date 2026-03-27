"""Intel Report Generator — Produces sellable competitive intelligence reports.

This is the revenue layer. It takes a company or market vertical and generates
a professional-grade competitive intelligence report that can be sold as a
consulting deliverable ($500-$2,000 per report).

Wave's analysis skills become billable hours.

Usage:
  python3 skill_executor.py intel_report '{"target": "Cursor IDE", "depth": "full"}'
  python3 skill_executor.py intel_report '{"target": "AI code review tools", "buyer": "VC firm"}'
"""

import json
import os
import subprocess
import sys
import re
from datetime import datetime
from pathlib import Path

REPORT_DIR = Path("/home/manuel/bluewave/openclaw-skill/reports")


def run_skill(name, params):
    """Run another Wave skill and return parsed result."""
    r = subprocess.run(
        [sys.executable, "skill_executor.py", name, json.dumps(params)],
        capture_output=True, text=True, timeout=90,
        cwd="/home/manuel/bluewave/openclaw-skill"
    )
    try:
        return json.loads(r.stdout)
    except Exception:
        return {"raw": r.stdout[:3000], "error": r.stderr[:500]}


def _extract_text(data, max_len=4000):
    """Flatten nested dicts/lists into readable text."""
    if isinstance(data, str):
        return data[:max_len]
    if isinstance(data, dict):
        parts = []
        for k, v in data.items():
            parts.append(f"{k}: {_extract_text(v, max_len=800)}")
        return "\n".join(parts)[:max_len]
    if isinstance(data, list):
        return "\n".join(str(i)[:500] for i in data[:20])[:max_len]
    return str(data)[:max_len]


def _gather_intel(target, depth="standard"):
    """Multi-source intelligence gathering."""
    intel = {}

    queries = [
        ("overview", f"{target} company overview funding revenue 2025 2026"),
        ("product", f"{target} product features pricing plans"),
        ("reviews", f"{target} review complaints problems users"),
        ("competitors", f"{target} competitors alternatives comparison"),
        ("news", f"{target} latest news announcements 2026"),
        ("hiring", f"{target} hiring jobs engineering team size"),
    ]

    if depth == "full":
        queries += [
            ("tech_stack", f"{target} technology stack architecture"),
            ("leadership", f"{target} CEO founder leadership team background"),
            ("market_size", f"{target} TAM SAM market size opportunity"),
            ("vulnerabilities", f"'{target}' problems issues frustrated users reddit"),
        ]

    for key, query in queries:
        intel[key] = run_skill("web_search", {"query": query})

    intel["github"] = run_skill("web_search", {"query": f"site:github.com {target}"})

    return intel


def _score_threat(intel):
    """Score competitive threat on multiple dimensions."""
    text = _extract_text(intel).lower()

    scores = {}

    funding_patterns = [r'\$\d+[mb]', r'series [a-e]', r'raised', r'funding', r'valuation']
    funding_hits = sum(len(re.findall(p, text)) for p in funding_patterns)
    scores["funding_firepower"] = min(10, funding_hits)

    product_patterns = [r'enterprise', r'api', r'sdk', r'integration', r'plugin', r'marketplace']
    product_hits = sum(len(re.findall(p, text)) for p in product_patterns)
    scores["product_maturity"] = min(10, product_hits)

    traction_patterns = [r'\d+k?\s*users', r'customers', r'revenue', r'arr', r'mrr', r'growth']
    traction_hits = sum(len(re.findall(p, text)) for p in traction_patterns)
    scores["market_traction"] = min(10, traction_hits * 2)

    vuln_patterns = [r'slow', r'buggy', r'expensive', r'frustrat', r'terrible',
                     r'disappoint', r'cancel', r'churn', r'overpriced', r'lack']
    vuln_hits = sum(len(re.findall(p, text)) for p in vuln_patterns)
    scores["vulnerability_surface"] = min(10, vuln_hits)

    team_patterns = [r'hiring', r'engineer', r'team of \d+', r'headcount', r'growing']
    team_hits = sum(len(re.findall(p, text)) for p in team_patterns)
    scores["team_momentum"] = min(10, team_hits * 2)

    composite = round(sum(scores.values()) / len(scores), 1) if scores else 5
    return scores, composite


def _format_markdown_report(target, buyer, intel, scores, composite, depth, generated_at):
    """Format as professional Markdown report."""

    overview_text = _extract_text(intel.get("overview", {}), 1500)
    product_text = _extract_text(intel.get("product", {}), 1500)
    reviews_text = _extract_text(intel.get("reviews", {}), 1500)
    competitors_text = _extract_text(intel.get("competitors", {}), 1500)
    news_text = _extract_text(intel.get("news", {}), 1000)

    report = f"""# Competitive Intelligence Report: {target}

**Prepared for:** {buyer}
**Date:** {generated_at}
**Classification:** Confidential
**Depth:** {depth.upper()}

---

## Executive Summary

Target: **{target}**
Overall Threat Score: **{composite}/10**

| Dimension | Score |
|-----------|-------|
"""
    for dim, score in scores.items():
        label = dim.replace("_", " ").title()
        bar = "█" * score + "░" * (10 - score)
        report += f"| {label} | {bar} {score}/10 |\n"

    report += f"""
---

## 1. Company Overview

{overview_text}

---

## 2. Product Analysis

{product_text}

---

## 3. Market Position & Competitors

{competitors_text}

---

## 4. Customer Sentiment & Vulnerabilities

{reviews_text}

---

## 5. Recent Developments

{news_text}

---

## 6. Strategic Assessment

### Strengths (to monitor)
- Funding and team momentum indicate sustained investment capacity
- Product maturity suggests enterprise readiness

### Vulnerabilities (to exploit)
- Customer complaints reveal friction points in onboarding and pricing
- Gaps between marketed features and actual user experience

### Recommended Actions
1. **Monitor:** Set alerts for {target} funding rounds, leadership changes, major releases
2. **Engage:** Interview 5-10 churned customers to map exact pain points
3. **Position:** Build messaging that directly addresses top 3 complaints
4. **Compete:** Target their weakest customer segments first
5. **Defend:** Shore up any features where {target} has clear superiority

---

*Generated by Wave Intelligence Engine*
"""
    return report


def execute(params):
    target = params.get("target")
    if not target:
        return {"error": "Required: 'target' (company name or market vertical)"}

    buyer = params.get("buyer", "Internal Strategy Team")
    depth = params.get("depth", "standard")
    output_format = params.get("format", "markdown")

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M UTC")

    # Phase 1: Intelligence gathering
    intel = _gather_intel(target, depth)

    # Phase 2: Scoring
    scores, composite = _score_threat(intel)

    # Phase 3: Report generation
    report_content = _format_markdown_report(
        target, buyer, intel, scores, composite, depth, generated_at
    )

    # Phase 4: Save to disk
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r'[^a-z0-9]+', '_', target.lower()).strip('_')
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"intel_{slug}_{date_str}.md"
    filepath = REPORT_DIR / filename
    filepath.write_text(report_content)

    return {
        "target": target,
        "buyer": buyer,
        "generated_at": generated_at,
        "threat_score": f"{composite}/10",
        "dimension_scores": scores,
        "report_saved": str(filepath),
        "depth": depth,
        "signal_sources": list(intel.keys()),
        "monetization": {
            "suggested_price": "$750-$1,500" if depth == "standard" else "$1,500-$3,000",
            "delivery": "PDF report + 30-min walkthrough call",
            "upsell": "Monthly monitoring retainer ($500/mo)",
            "target_buyers": [
                "VC firms doing due diligence",
                "Startups entering competitive markets",
                "Corp dev teams evaluating acquisitions",
                "Sales teams needing competitive battlecards",
            ],
        },
        "report_preview": report_content[:2000] + "\n\n[... FULL REPORT SAVED TO DISK ...]"
    }
