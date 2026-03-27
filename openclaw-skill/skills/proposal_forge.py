"""
proposal_forge - Revenue Generation Layer

Generates complete consulting proposals from a client brief.
Turns Wave's analytical capabilities into billable engagements.

Usage:
  python3 skill_executor.py proposal_forge '{"client": "Acme Corp", "problem": "Need competitive analysis of AI agent market", "tier": "standard"}'

Tiers: lite ($2,500) | standard ($7,500) | premium ($18,000)
"""

import json
import os
import datetime


def run(params):
    client = params.get("client", "Prospective Client")
    problem = params.get("problem", "")
    domain = params.get("domain", "strategic intelligence")
    currency = params.get("currency", "USD")
    tier = params.get("tier", "standard")

    if not problem:
        return {
            "error": "Provide a problem description.",
            "usage": '{"client": "Acme Corp", "problem": "Need competitive analysis of AI agent market", "domain": "market intelligence", "tier": "standard"}'
        }

    # Pricing engine
    pricing = {
        "lite": {
            "label": "Tactical Brief",
            "price": 2500,
            "hours": "8-12",
            "delivery": "3 business days",
            "includes": [
                "Core analysis report",
                "Executive summary",
                "3 actionable recommendations",
                "1 revision round"
            ]
        },
        "standard": {
            "label": "Strategic Analysis",
            "price": 7500,
            "hours": "20-30",
            "delivery": "7 business days",
            "includes": [
                "Deep-dive analysis report",
                "Competitive landscape mapping",
                "Risk assessment matrix",
                "Implementation roadmap",
                "10 prioritized recommendations",
                "2 revision rounds",
                "30-min strategy call"
            ]
        },
        "premium": {
            "label": "Full Engagement",
            "price": 18000,
            "hours": "40-60",
            "delivery": "14 business days",
            "includes": [
                "Comprehensive strategic audit",
                "Market intelligence dossier",
                "Competitive kill chain analysis",
                "Financial modeling & projections",
                "Go-to-market playbook",
                "Risk mitigation framework",
                "Unlimited revisions (30 days)",
                "Weekly strategy calls (4x)",
                "90-day implementation support"
            ]
        }
    }

    p = pricing.get(tier, pricing["standard"])
    today = datetime.date.today().strftime("%B %d, %Y")
    valid_until = (datetime.date.today() + datetime.timedelta(days=14)).strftime("%B %d, %Y")
    ref_code = f"WAVE-{datetime.date.today().strftime('%Y%m%d')}-{abs(hash(client)) % 10000:04d}"

    # Domain-specific value propositions
    domain_angles = {
        "market intelligence": "actionable market insights that reduce decision risk by 60-80%",
        "competitive analysis": "competitive intelligence that reveals blind spots and attack vectors",
        "strategic intelligence": "strategic clarity that compresses months of analysis into days",
        "technical architecture": "architectural decisions backed by systematic trade-off analysis",
        "go-to-market": "market entry strategies with validated positioning and pricing",
        "due diligence": "investment intelligence that surfaces hidden risks and opportunities",
    }
    value_prop = domain_angles.get(domain, domain_angles["strategic intelligence"])

    # Build tier comparison table
    comparison_lines = []
    for t_key in ["lite", "standard", "premium"]:
        t_val = pricing[t_key]
        marker = " **← SELECTED**" if t_key == tier else ""
        items = "\n".join([f"  - {item}" for item in t_val["includes"]])
        comparison_lines.append(
            f"\n### {t_val['label']} — {currency} {t_val['price']:,}{marker}\n"
            f"- Estimated effort: {t_val['hours']} hours\n"
            f"- Delivery: {t_val['delivery']}\n"
            f"- Includes:\n{items}\n"
        )
    comparison = "\n".join(comparison_lines)

    proposal = f"""# Proposal: {domain.title()} Engagement

**Prepared for:** {client}
**Date:** {today}
**Valid until:** {valid_until}
**Ref:** {ref_code}

---

## Understanding

{problem}

## Value Proposition

This engagement delivers {value_prop}. Our methodology combines autonomous intelligence systems with strategic synthesis to produce outputs that would typically require a team of 3-5 analysts working 4-8 weeks.

**Why this matters:** Every week of delayed or uninformed decision-making costs organizations 2-5x the investment in proper analysis.

## Proposed Approach

1. **Discovery & Scoping** — Validate assumptions, define success criteria, identify data sources
2. **Intelligence Gathering** — Systematic collection across public, proprietary, and synthesized sources
3. **Analysis & Synthesis** — Pattern recognition, risk modeling, opportunity mapping
4. **Deliverable Production** — Actionable report with clear recommendations and implementation path
5. **Review & Refinement** — Collaborative refinement based on stakeholder feedback

## Investment Options
{comparison}

## Selected Package: {p['label']}

| Detail | Value |
|--------|-------|
| Investment | **{currency} {p['price']:,}** |
| Delivery | {p['delivery']} |
| Payment | 50% upfront, 50% on delivery |

## Terms

- All work product is owned by {client} upon final payment
- Confidentiality guaranteed — NDA available upon request
- Satisfaction guarantee: if deliverables don't meet agreed criteria, we refine at no additional cost

## Next Steps

1. Reply to confirm selected tier
2. Receive SOW + invoice for 50% deposit
3. Kick-off within 24 hours of payment

---
*Generated by Wave Intelligence Systems*
"""

    # Save to file
    output_dir = os.path.expanduser("~/bluewave/proposals")
    os.makedirs(output_dir, exist_ok=True)
    safe_client = client.lower().replace(" ", "_").replace("/", "_")
    filename = f"proposal_{safe_client}_{datetime.date.today().strftime('%Y%m%d')}.md"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w") as f:
        f.write(proposal)

    return {
        "status": "proposal_generated",
        "client": client,
        "tier": tier,
        "tier_label": p["label"],
        "price": f"{currency} {p['price']:,}",
        "delivery": p["delivery"],
        "saved_to": filepath,
        "valid_until": valid_until,
        "ref": ref_code,
        "proposal_preview": proposal[:500] + "..."
    }
