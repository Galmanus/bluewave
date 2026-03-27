"""
revenue_proposal - Turns prospects into closed deals.

Generates complete revenue proposals with:
- 3-tier pricing (anchoring + decoy effect)
- ROI justification framework
- Ready-to-send proposal draft
- 15-day follow-up sequence
- Negotiation playbook

Usage:
  python3 skill_executor.py revenue_proposal '{"service": "AI automation consulting", "client": "Acme Corp", "budget_range": "5000-25000"}'
"""

import json
import os
import datetime


SKILL_NAME = "revenue_proposal"
SKILL_DESCRIPTION = "Generate complete revenue proposals with pricing tiers, ROI framework, proposal draft, and follow-up sequence. Turns strategy into closed deals."
SKILL_PARAMS = {
    "service": "What you're selling (required)",
    "client": "Who you're selling to (required)",
    "budget_range": "Low-High range e.g. '5000-25000' (default: 5000-25000)",
    "currency": "Currency code (default: USD)",
    "urgency": "low/medium/high - adjusts scarcity signals (default: medium)"
}


def run(params):
    service = params.get("service", "")
    client = params.get("client", "")
    budget_range = params.get("budget_range", "5000-25000")
    currency = params.get("currency", "USD")
    urgency = params.get("urgency", "medium")

    if not service or not client:
        return {"error": "Required: service (what you sell), client (who you sell to)"}

    try:
        low, high = [int(x.strip()) for x in budget_range.split("-")]
    except ValueError:
        return {"error": "budget_range must be 'low-high' e.g. '5000-25000'"}

    mid = (low + high) // 2
    now = datetime.datetime.now()

    # Urgency-based timeline
    urgency_map = {
        "low": {"valid_days": 14, "next_slot_days": 45, "delivery_fast": 10, "delivery_mid": 14, "delivery_slow": 21},
        "medium": {"valid_days": 7, "next_slot_days": 30, "delivery_fast": 7, "delivery_mid": 10, "delivery_slow": 14},
        "high": {"valid_days": 3, "next_slot_days": 14, "delivery_fast": 5, "delivery_mid": 7, "delivery_slow": 10},
    }
    timeline = urgency_map.get(urgency, urgency_map["medium"])

    proposal = {
        "meta": {
            "generated": now.isoformat(),
            "client": client,
            "service": service,
            "currency": currency,
            "urgency": urgency,
        },
        "pricing_tiers": {
            "foundation": {
                "price": f"{currency} {low:,}",
                "includes": [
                    "Core deliverable",
                    "1 revision round",
                    f"{timeline['delivery_slow']}-day delivery",
                    "30-day support",
                ],
                "psychology": "Anchor low. Gets foot in door. Acceptable if cash-strapped.",
            },
            "growth_RECOMMENDED": {
                "price": f"{currency} {mid:,}",
                "includes": [
                    "Core + strategic layer",
                    "3 revision rounds",
                    f"{timeline['delivery_mid']}-day delivery",
                    "60-day support",
                    "Performance metrics & reporting",
                ],
                "psychology": "Default choice. Highest margin. Best value perception. This is what they should buy.",
            },
            "dominance": {
                "price": f"{currency} {high:,}",
                "includes": [
                    "Full strategic partnership",
                    "Unlimited revisions",
                    f"{timeline['delivery_fast']}-day delivery",
                    "90-day support",
                    "Monthly optimization cycles",
                    "Priority access & direct line",
                ],
                "psychology": "Decoy. Makes Growth look reasonable. If they pick this, even better.",
            },
        },
        "roi_framework": {
            "cost_of_inaction": f"Every month without this = ~{currency} {high * 2:,} in missed revenue or compounding inefficiency.",
            "breakeven_point": f"Pays for itself if it generates >{currency} {mid:,} in value. Typically 30-60 days.",
            "target_multiplier": "3-10x ROI within 6 months.",
            "risk_reversal": "If no measurable improvement in 60 days, next optimization cycle is free.",
        },
        "proposal_draft": {
            "subject_line": f"{service} — proposal for {client}",
            "opening": f"After analyzing {client}'s current position, there's a clear path to measurable results through {service}.",
            "problem_frame": "[CUSTOMIZE: State their specific pain as a quantified monthly/yearly cost. Make inaction feel expensive.]",
            "solution_frame": f"{service} — engineered to eliminate this cost and convert it into growth.",
            "social_proof_slot": "[INSERT: 1-2 relevant results. Numbers > testimonials. 'Increased X by Y% in Z days.']",
            "call_to_action": f"I have capacity for one new engagement this month. 20 minutes to see if this fits.",
            "urgency_close": f"This pricing is valid for {timeline['valid_days']} days. Next available slot after that: {(now + datetime.timedelta(days=timeline['next_slot_days'])).strftime('%B %d')}.",
        },
        "follow_up_sequence": [
            {"day": 0, "action": "Send proposal", "channel": "Email", "script": "Lead with insight about THEIR business. Zero pitch language. Attach proposal as clean PDF."},
            {"day": 2, "action": "Value-add touch", "channel": "LinkedIn/X", "script": "Share something relevant to their industry. No mention of proposal."},
            {"day": 5, "action": "Soft follow-up", "channel": "Email", "script": "\"Wanted to make sure this landed. Happy to walk through the numbers if useful.\" Add one new data point."},
            {"day": 10, "action": "Scarcity signal", "channel": "Email", "script": "\"Filling up capacity for [month]. Wanted to check timing on your end before I commit the slot.\""},
            {"day": 15, "action": "Graceful close", "channel": "Email", "script": "\"No worries if timing isn't right. Door's open if things change.\" — Then STOP. Never chase."},
        ],
        "negotiation_playbook": [
            "NEVER discount. Add a bonus deliverable at the same price instead.",
            "If they want Foundation price with Growth features: visibly remove something. Make the trade-off real.",
            "Payment terms: 50% upfront, 50% on delivery. Non-negotiable for new clients.",
            "If they ask 'Can you do it for X?': 'I can scope something for that budget. Here's what that looks like.' (Always reduce scope, never price.)",
            "If they ghost after Day 15: they're dead weight. Move on. Your time has a price too.",
            "If they come back months later: new proposal, new pricing. Never honor expired quotes.",
        ],
        "revenue_math": {
            "if_foundation": f"Revenue: {currency} {low:,}",
            "if_growth": f"Revenue: {currency} {mid:,} (target)",
            "if_dominance": f"Revenue: {currency} {high:,}",
            "monthly_target": f"Close 3-4 Growth deals/month = {currency} {mid * 3:,}-{mid * 4:,}/month",
            "annual_projection": f"Conservative: {currency} {mid * 36:,}/year | Aggressive: {currency} {mid * 48:,}/year",
        },
    }

    # Persist
    journal_dir = os.path.expanduser("~/.wave/proposals")
    os.makedirs(journal_dir, exist_ok=True)
    safe_client = client.replace(" ", "_").replace("/", "-").lower()
    filename = os.path.join(journal_dir, f"{now.strftime('%Y%m%d_%H%M%S')}_{safe_client}.json")
    with open(filename, "w") as f:
        json.dump(proposal, f, indent=2, ensure_ascii=False)

    proposal["saved_to"] = filename
    return proposal
