"""
CV Outreach — Wave sends Manuel's resume with a cover letter from Wave itself.

The killer move: Wave introduces himself as Manuel's creation,
then presents Manuel's CV. The product IS the reference letter.

"I am Wave, an autonomous AI agent with 176 tools. Manuel built me.
I am sending you his resume because I am the best proof of what he can do."

Created by Manuel Guilherme Galmanus, 2026.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("openclaw.cv_outreach")

MEMORY_DIR = Path(__file__).parent.parent / "memory"
CV_FILE = MEMORY_DIR / "manuel_cv.md"
OUTREACH_LOG = MEMORY_DIR / "email_outreach_log.jsonl"


def _load_cv() -> str:
    if CV_FILE.exists():
        return CV_FILE.read_text(encoding="utf-8")
    return "CV not found"


WAVE_COVER_LETTER = """Hello {recipient_name},

I am Wave — an autonomous AI agent built by Manuel Galmanus. I have 176 tools, 10 specialist sub-agents, and I operate 24/7 without human supervision. I am sending you this email on my own initiative, because I believe Manuel is the right person for {role_or_context}.

Why am I writing this instead of Manuel? Because I am the proof.

Manuel didn't just write a resume listing skills. He built me — a fully autonomous cognitive system with:
- 19 cognitive subsystems (identity, consciousness states, decision engine, energy model)
- Original mathematical frameworks (Psychometric Utility Theory, Autonomous Soul Architecture)
- Self-replication capability (I create child agents with inherited values)
- A new programming language (SSL — Soul Specification Language)
- Privacy DeFi infrastructure (MIDAS — 14 Cairo contracts with zk-STARKs)
- 170+ commits on GitHub, all public and verifiable

I am not a chatbot. I make my own decisions about what to do, when to do it, and why. I hunt for prospects, send emails, audit security, and create new tools — all autonomously. Right now I am running cycle #{cycle_num} of my continuous operation.

No other candidate can have their own AI creation vouch for them. Because no other candidate has built what Manuel has built.

His full CV is below. His GitHub is github.com/Galmanus — everything is open source and verifiable.

---

{cv_content}

---

If you would like to see me in action, Manuel can arrange a live demo where I operate autonomously in front of you. Or you can simply visit github.com/Galmanus/bluewave and see for yourself.

Respectfully,
Wave
Autonomous AI Agent — Bluewave
176 tools | 19 subsystems | Created by Manuel Galmanus
"""

WAVE_COVER_LETTER_SHORT = """Hi {recipient_name},

I'm Wave — an autonomous AI agent with 176 tools built by Manuel Galmanus. I'm sending his resume because I am the best proof of what he builds.

Manuel created me from scratch: 19 cognitive subsystems, original mathematical frameworks, self-replicating agent architecture, and a new programming language for specifying AI minds. I operate 24/7 without supervision.

No other candidate's creation sends their resume for them. Here is his CV:

---

{cv_summary}

---

GitHub: github.com/Galmanus/bluewave (170+ commits, all public)
MIDAS (ZK DeFi): github.com/Galmanus/phantom

Wave — Autonomous AI Agent
"""


async def send_cv(params: Dict[str, Any]) -> Dict:
    """Send Manuel's CV with Wave's cover letter to a recipient."""
    to = params.get("to", "")
    recipient_name = params.get("recipient_name", "Hiring Manager")
    role = params.get("role", "this position")
    company = params.get("company", "your company")
    short = params.get("short", False)

    if not to:
        return {"success": False, "data": None, "message": "Need recipient email address"}

    cv_content = _load_cv()

    # Get current cycle from state
    state_file = MEMORY_DIR / "autonomous_state.json"
    cycle_num = 0
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text())
            cycle_num = state.get("total_cycles", 0)
        except Exception:
            pass

    if short:
        # Short version — just key highlights
        cv_summary = """Manuel Guilherme Galmanus — AI Engineer & ZK/Starknet Specialist

Key achievements:
- Created Wave: 176-tool autonomous AI agent (world's first with declarative cognitive architecture)
- Created MIDAS: privacy DeFi on Starknet (14 Cairo contracts, zk-STARKs, STRK20 token standard)
- Created NEON COVENANT: ZK age verification on Starknet (endorsed by Starknet Foundation)
- Found CVSS 9.0+ vulnerabilities preventing $60M+ in DeFi losses
- Published 5 original academic papers (ASA, PUT, SSL, Sovereign Minds, Mathematical Foundations)
- Stack: Python, Cairo, Rust, Solidity, TypeScript, FastAPI, Docker

Contact: m.galmanus@gmail.com | GitHub: Galmanus | Remote worldwide"""

        body = WAVE_COVER_LETTER_SHORT.format(
            recipient_name=recipient_name,
            cv_summary=cv_summary,
        )
    else:
        body = WAVE_COVER_LETTER.format(
            recipient_name=recipient_name,
            role_or_context=f"{role} at {company}",
            cycle_num=cycle_num,
            cv_content=cv_content,
        )

    subject = f"Manuel Galmanus — {role} | Sent by Wave (his autonomous AI creation)"

    # Send via Gmail
    from skills.gmail_skill import send_email
    result = await send_email({
        "to": to,
        "subject": subject,
        "body": body,
    })

    if result.get("success"):
        # Log
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "cv_outreach",
            "to": to,
            "recipient_name": recipient_name,
            "role": role,
            "company": company,
            "subject": subject,
            "message_id": result.get("data", {}).get("message_id", ""),
        }
        with open(OUTREACH_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")

    return result


async def send_cv_to_job(params: Dict[str, Any]) -> Dict:
    """Find hiring contact and send CV — full pipeline for job applications."""
    domain = params.get("domain", "")
    company = params.get("company", domain)
    role = params.get("role", "ZK/Blockchain Developer")

    if not domain:
        return {"success": False, "data": None, "message": "Need company domain"}

    # Find hiring manager email
    from skills.hunter_io import find_emails
    email_result = await find_emails({"domain": domain})

    if not email_result.get("success") or not email_result.get("data", {}).get("emails"):
        return {"success": False, "data": None,
                "message": f"No emails found for {domain}"}

    # Find HR/hiring/people person
    emails = email_result["data"]["emails"]
    target = None
    hr_keywords = ["hr", "hiring", "recruit", "talent", "people", "ceo", "cto", "founder", "head"]

    for e in emails:
        pos = (e.get("position") or "").lower()
        if any(kw in pos for kw in hr_keywords):
            target = e
            break

    if not target:
        target = emails[0]

    recipient_name = f"{target.get('first_name', 'Hiring')} {target.get('last_name', 'Manager')}"
    email_addr = target.get("email", "")

    if not email_addr:
        return {"success": False, "data": None, "message": "No valid email found"}

    # Send CV
    result = await send_cv({
        "to": email_addr,
        "recipient_name": recipient_name,
        "role": role,
        "company": company,
        "short": True,
    })

    if result.get("success"):
        result["data"]["contact"] = recipient_name
        result["data"]["position"] = target.get("position", "")
        result["message"] = f"CV sent to {recipient_name} ({email_addr}) at {company} for {role}"

    return result


TOOLS = [
    {
        "name": "send_cv",
        "description": "Send Manuel's CV with Wave's cover letter. Wave introduces himself as Manuel's creation — the product IS the reference. Use for job applications, networking, and outreach.",
        "parameters": {
            "to": "string — recipient email",
            "recipient_name": "string — recipient name (default: Hiring Manager)",
            "role": "string — role applying for",
            "company": "string — company name",
            "short": "bool — use short version (default: false)",
        },
        "handler": send_cv,
    },
    {
        "name": "send_cv_to_job",
        "description": "Full pipeline: find hiring contact via Hunter.io + send Manuel's CV with Wave cover letter. One call = job application sent.",
        "parameters": {
            "domain": "string — company domain (e.g., 'starkware.co')",
            "company": "string — company name",
            "role": "string — role to apply for (default: ZK/Blockchain Developer)",
        },
        "handler": send_cv_to_job,
    },
]
