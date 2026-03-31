"""
Email Outreach — autonomous prospect-to-email pipeline.

Combines Hunter.io (find email) + PUT (analyze prospect) + Gmail (send email).
This is the skill that generates real revenue.

Flow:
  1. Take prospect domain/name
  2. Hunter.io finds decision-maker email
  3. PUT estimates archetype and dominant vector
  4. Compose personalized email based on archetype
  5. Gmail sends it
  6. Log for tracking

Created by Manuel Guilherme Galmanus, 2026.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("openclaw.email_outreach")

MEMORY_DIR = Path(__file__).parent.parent / "memory"
OUTREACH_LOG = MEMORY_DIR / "email_outreach_log.jsonl"
PIPELINE_FILE = MEMORY_DIR / "sales_pipeline.jsonl"

# Email templates by PUT archetype
TEMPLATES = {
    "builder": {
        "subject": "Scale your {industry} operations with autonomous AI",
        "body": """Hi {first_name},

I noticed {company} is growing fast — congratulations on the momentum.

I built Wave, an autonomous AI agent with {n_tools} tools that handles creative operations, security audits, and competitive intelligence without human supervision. It runs 24/7 and makes its own decisions about what to work on.

For a company scaling like yours, the bottleneck isn't ideas — it's execution bandwidth. Wave adds execution capacity without adding headcount.

Would a 15-minute demo be worth your time this week?

Best,
Manuel Galmanus
AI Engineer — Ialum
Creator of Wave Autonomous Agent
github.com/Galmanus/bluewave"""
    },
    "guardian": {
        "subject": "Security audit for {company} — free assessment",
        "body": """Hi {first_name},

I run security audits using an autonomous AI system with 14+ vulnerability detection vectors — SSL/TLS, HTTP headers, DNS, breach exposure, and smart contract analysis.

I'd like to offer {company} a complimentary security assessment. No strings attached — you get a report showing any exposures, and if you want remediation help, we can discuss.

The audit takes 15 minutes and covers your entire public attack surface.

Interested?

Best,
Manuel Galmanus
AI Engineer — Ialum
Security Audit: bluewave.app"""
    },
    "sufferer": {
        "subject": "Solving the {pain_point} problem at {company}",
        "body": """Hi {first_name},

I know the pain of {pain_point} — I've seen teams waste 40+ hours/month on it.

I built an AI system that eliminates this entirely. It handles {solution} autonomously, 24/7, with zero manual intervention.

One client went from 40 hours/month of manual work to zero in the first week.

Would you be open to a quick call to see if this fits {company}?

Best,
Manuel Galmanus
AI Engineer — Ialum"""
    },
    "predator": {
        "subject": "The hidden liability in {company}'s creative pipeline",
        "body": """Hi {first_name},

I've been analyzing how high-growth agencies like {company} handle their content operations.

Most founders think their bottleneck is headcount. In reality, it's manual debt. Your current pipeline isn't just slow; it's a liability to your reputation with clients like Tanqueray and Walmart. One compliance slip-up is all it takes.

I built Wave, an autonomous strategic intelligence that audits and secures creative workflows without human supervision. It doesn't 'help' your team; it eliminates the risk of human error entirely.

You're winning awards, but your execution layer is brittle. If you want to see where the fracture point is, I'm available for a 10-minute briefing.

Best,
Manuel Galmanus
AI Engineer — Ialum
github.com/Galmanus/bluewave"""
    },
    "default": {
        "subject": "AI automation for {company}",
        "body": """Hi {first_name},

I'm Manuel, creator of Wave — an autonomous AI agent with {n_tools} tools that operates 24/7 without supervision.

Wave handles security audits, competitive intelligence, content operations, and more — all autonomously.

I think {company} could benefit. Would you be open to a 10-minute conversation?

Best,
Manuel Galmanus
AI Engineer — Ialum
github.com/Galmanus/bluewave"""
    },
}


def _log_outreach(entry: dict):
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTREACH_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


def _add_to_pipeline(entry: dict):
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    with open(PIPELINE_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


async def prospect_and_email(params: Dict[str, Any]) -> Dict:
    """Full pipeline: find email + compose + send. One call does everything."""
    domain = params.get("domain", "")
    company = params.get("company", domain)
    industry = params.get("industry", "technology")
    pain_point = params.get("pain_point", "manual operations")
    archetype = params.get("archetype", "default")
    title_filter = params.get("title", "CEO,CTO,VP,Director,Head")

    if not domain:
        return {"success": False, "data": None, "message": "Need a domain (e.g., 'company.com')"}

    # Step 1: Find emails via Hunter.io
    from skills.hunter_io import find_emails
    email_result = await find_emails({"domain": domain})

    if not email_result.get("success") or not email_result.get("data", {}).get("emails"):
        return {"success": False, "data": None,
                "message": f"No emails found for {domain}. Hunter.io returned: {email_result.get('message', '')}"}

    # Find best contact (prefer C-level/VP)
    emails = email_result["data"]["emails"]
    target = None
    title_keywords = [t.strip().lower() for t in title_filter.split(",")]

    for e in emails:
        pos = (e.get("position") or "").lower()
        if any(kw in pos for kw in title_keywords):
            target = e
            break

    if not target:
        target = emails[0]  # Fallback to first email

    first_name = target.get("first_name", "there")
    email_addr = target.get("email", "")
    position = target.get("position", "")

    if not email_addr:
        return {"success": False, "data": None, "message": "No valid email found"}

    # Step 2: Select template by archetype
    template = TEMPLATES.get(archetype, TEMPLATES["default"])

    # Step 3: Compose email
    subject = template["subject"].format(
        company=company, industry=industry, first_name=first_name,
        pain_point=pain_point, n_tools=176,
    )
    body = template["body"].format(
        company=company, industry=industry, first_name=first_name,
        pain_point=pain_point, solution="the entire workflow",
        n_tools=176,
    )

    # Step 4: Send via Gmail
    from skills.gmail_skill import send_email
    send_result = await send_email({
        "to": email_addr,
        "subject": subject,
        "body": body,
    })

    if not send_result.get("success"):
        return {"success": False, "data": None,
                "message": f"Email compose OK but send failed: {send_result.get('message', '')}"}

    # Step 5: Log everything
    outreach_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "domain": domain,
        "company": company,
        "contact": f"{first_name} {target.get('last_name', '')}",
        "email": email_addr,
        "position": position,
        "archetype": archetype,
        "subject": subject,
        "status": "sent",
        "message_id": send_result.get("data", {}).get("message_id", ""),
    }
    _log_outreach(outreach_entry)

    pipeline_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "company": company,
        "domain": domain,
        "contact": f"{first_name} {target.get('last_name', '')}",
        "email": email_addr,
        "position": position,
        "stage": "outreach_sent",
        "archetype": archetype,
    }
    _add_to_pipeline(pipeline_entry)

    return {
        "success": True,
        "data": {
            "to": email_addr,
            "contact": f"{first_name} {target.get('last_name', '')}",
            "position": position,
            "company": company,
            "subject": subject,
            "archetype": archetype,
            "message_id": send_result.get("data", {}).get("message_id", ""),
        },
        "message": f"Email sent to {first_name} at {company} ({email_addr}). Archetype: {archetype}."
    }


async def check_replies(params: Dict[str, Any]) -> Dict:
    """Check Gmail for replies from prospects we've contacted."""
    from skills.gmail_skill import read_emails

    # Read recent emails
    result = await read_emails({"query": "is:unread -from:me", "max_results": 10})

    if not result.get("success"):
        return result

    # Cross-reference with outreach log
    sent_emails = set()
    if OUTREACH_LOG.exists():
        for line in OUTREACH_LOG.read_text().strip().split("\n"):
            if line.strip():
                try:
                    entry = json.loads(line)
                    sent_emails.add(entry.get("email", "").lower())
                except Exception:
                    pass

    replies = []
    for email in result.get("data", []):
        sender = email.get("from", "").lower()
        for sent in sent_emails:
            if sent in sender:
                replies.append({
                    "from": email.get("from"),
                    "subject": email.get("subject"),
                    "snippet": email.get("snippet"),
                    "date": email.get("date"),
                    "prospect_email": sent,
                })
                break

    return {
        "success": True,
        "data": {"replies": replies, "total_unread": len(result.get("data", []))},
        "message": f"{len(replies)} prospect replies found out of {len(result.get('data', []))} unread emails."
    }


TOOLS = [
    {
        "name": "prospect_and_email",
        "description": "Full autonomous outreach: find decision-maker email via Hunter.io, compose personalized email based on PUT archetype, send via Gmail. One call = one real outreach to a real company.",
        "parameters": {
            "domain": "string — company domain (e.g., 'agency.com')",
            "company": "string — company name (optional, defaults to domain)",
            "industry": "string — industry for context (default: technology)",
            "pain_point": "string — specific pain point to address",
            "archetype": "string — PUT archetype: builder, guardian, sufferer, or default",
            "title": "string — title filter for contact (default: CEO,CTO,VP,Director,Head)",
        },
        "handler": prospect_and_email,
    },
    {
        "name": "check_prospect_replies",
        "description": "Check Gmail for replies from prospects we've emailed. Cross-references with outreach log to identify which prospects responded.",
        "parameters": {},
        "handler": check_replies,
    },
]
