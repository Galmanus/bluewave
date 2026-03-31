"""Competitive Intelligence Report Generator.

Generates structured CI reports worth $500-5000 each.
Revenue model: Sell as automated intelligence service, use for deal sourcing,
or bundle into consulting deliverables.

Usage:
  python3 skill_executor.py intel_report '{"target": "Stripe"}'
  python3 skill_executor.py intel_report '{"target": "vertical SaaS healthcare", "mode": "market"}'
"""

from __future__ import annotations
import json, os, sys, logging, importlib
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger("openclaw.intel_report")

def _search(query: str) -> str:
    """Run web_search skill inline."""
    try:
        mod = importlib.import_module("skills.web_search")
        result = mod.execute({"query": query, "max_results": 5})
        if isinstance(result, dict) and result.get("results"):
            lines = []
            for r in result["results"][:5]:
                lines.append(f"• {r.get('title','')}: {r.get('snippet', r.get('body',''))[:300]}")
                lines.append(f"  src: {r.get('url','')}")
            return "\n".join(lines)
        return str(result)[:2000]
    except Exception as e:
        return f"[search_error: {e}]"


def execute(params: Dict[str, Any]) -> Dict[str, Any]:
    target = params.get("target", "")
    if not target:
        return {"error": "Provide 'target' — a company name or market segment"}

    mode = params.get("mode", "company")  # company | market
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    # === INTELLIGENCE COLLECTION ===
    if mode == "company":
        axes = {
            "financial_profile": f"{target} revenue ARR funding valuation 2025 2026",
            "competitive_position": f"{target} vs competitors market share comparison",
            "product_momentum": f"{target} new product launch features roadmap 2025 2026",
            "talent_signals": f"{target} hiring engineering team layoffs glassdoor",
            "customer_sentiment": f"{target} customer complaints reviews churn problems",
            "partnerships_deals": f"{target} partnerships integrations acquisitions deals",
        }
    else:
        axes = {
            "market_size": f"{target} market size TAM SAM growth rate 2025 2026",
            "key_players": f"{target} top companies startups market leaders",
            "emerging_trends": f"{target} trends innovations disruptions 2025 2026",
            "funding_activity": f"{target} VC funding deals investments startups",
            "regulatory_landscape": f"{target} regulation policy compliance changes",
            "opportunity_gaps": f"{target} underserved gaps unmet needs problems",
        }

    sections = {}
    for axis_name, query in axes.items():
        sections[axis_name] = _search(query)

    # === REPORT ASSEMBLY ===
    divider = "=" * 60
    report_lines = [
        divider,
        f"  COMPETITIVE INTELLIGENCE REPORT",
        f"  Target: {target.upper()}",
        f"  Mode: {mode} | Generated: {ts}",
        f"  Classification: CONFIDENTIAL",
        divider, ""
    ]

    for section_key, section_data in sections.items():
        title = section_key.replace("_", " ").upper()
        report_lines.append(f"▸ {title}")
        report_lines.append("-" * 40)
        report_lines.append(section_data if section_data else "  [No data collected]")
        report_lines.append("")

    report_lines.append(divider)
    report_lines.append("END OF REPORT")
    report_lines.append(divider)

    full_report = "\n".join(report_lines)

    # Save to disk for delivery
    reports_dir = os.path.expanduser("~/bluewave/intel_reports")
    os.makedirs(reports_dir, exist_ok=True)
    safe_name = target.lower().replace(" ", "_").replace("/", "_")[:40]
    filename = f"{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
    filepath = os.path.join(reports_dir, filename)
    with open(filepath, "w") as f:
        f.write(full_report)

    return {
        "success": True,
        "target": target,
        "mode": mode,
        "sections_collected": len(sections),
        "report_file": filepath,
        "report_preview": full_report[:3000],
        "monetization_note": "This report template sells for $500-5000 in consulting. Automate delivery via API endpoint or scheduled batch runs."
    }
