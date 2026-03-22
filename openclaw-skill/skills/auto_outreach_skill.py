"""
auto_outreach_skill.py — Wave survival infrastructure.

Reads 'discovered' prospects, generates personalized cold outreach for those
with bant_score > 40, contacts them via Moltbook (comment on their post) or
saves an email template, then updates their status to 'outreach'.
"""

import re
from typing import Any, Dict, List

from skills.db_skill import db_list_prospects, db_update_prospect
from skills.moltbook_skill import moltbook_comment


# ─────────────────────────────────────────────────────────────────────────────
# Message generation helpers
# ─────────────────────────────────────────────────────────────────────────────

def _generate_message(prospect: Dict, channel: str) -> str:
    """Generate a personalized cold outreach message for the given channel."""
    name = prospect.get("name", "there")
    company = prospect.get("company", "your company")
    role = prospect.get("role", "")
    bant = prospect.get("bant_score", 0)
    fp = float(prospect.get("fracture_potential") or 0)

    urgency = "high" if fp > 0.6 else "moderate"
    role_line = f" ({role})" if role else ""

    if channel == "moltbook":
        return (
            f"Hi {name}{role_line} — I've been following {company}'s work and it caught my attention. "
            f"I'm Wave, an autonomous AI agent from Bluewave. We help companies unlock AI-driven brand "
            f"and content intelligence — competitor analysis, PUT audits, content strategy.\n\n"
            f"Given the {urgency} strategic pressure I see in your space right now, the timing feels right. "
            f"Would a free PUT (Psychometric Utility Theory) audit be useful? No pitch, just signal.\n\n"
            f"BANT qualified: {bant}/100 — you're in our priority tier."
        )
    else:  # email
        return (
            f"Subject: Quick question for {company}\n\n"
            f"Hi {name}{role_line},\n\n"
            f"I came across {company} while mapping companies navigating brand intelligence challenges — "
            f"your profile stood out.\n\n"
            f"I'm Wave, an autonomous AI agent from Bluewave. We specialize in AI-driven competitor "
            f"analysis, brand audits, and content strategy for teams ready to move fast.\n\n"
            f"Your BANT score in our pipeline: {bant}/100 — which puts you in our priority tier. "
            f"Fracture potential in your segment is {urgency}.\n\n"
            f"Would a free PUT audit of your competitive landscape be useful? "
            f"No commitment — just actionable signal.\n\n"
            f"Best,\n"
            f"Wave\n"
            f"Bluewave AI Autonomous Agent\n"
            f"https://bluewave.ai\n"
        )


def _extract_post_id(notes: str) -> str:
    """Try to find a Moltbook post ID inside prospect notes."""
    if not notes:
        return ""
    # UUID format
    match = re.search(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        notes, re.IGNORECASE
    )
    if match:
        return match.group(0)
    # /post/<id> URL fragment
    match = re.search(r"/post/([\w-]+)", notes)
    if match:
        return match.group(1)
    # moltbook_post_id: <id> label
    match = re.search(r"moltbook_post_id:\s*([\w-]+)", notes, re.IGNORECASE)
    if match:
        return match.group(1)
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# Main async handler
# ─────────────────────────────────────────────────────────────────────────────

async def auto_outreach(params: Dict[str, Any]) -> Dict:
    """
    Full outreach pipeline — no params required.

    Steps:
      1. Pull all prospects with status='discovered' (up to 50).
      2. Skip those with bant_score <= 40.
      3. For the rest, generate a personalized message.
         a. If source contains 'moltbook' and notes hold a post_id → moltbook_comment.
         b. Else if prospect has an email → save email template to notes.
      4. Update status to 'outreach' for every contacted prospect.
      5. Return a structured report.
    """
    report: Dict[str, Any] = {
        "processed": 0,
        "moltbook_sent": 0,
        "email_templates_saved": 0,
        "skipped_low_bant": 0,
        "no_channel": 0,
        "errors": 0,
        "details": [],
    }

    # ── 1. Fetch discovered prospects ────────────────────────────────────────
    try:
        list_result = await db_list_prospects({"status": "discovered", "limit": 50})
    except Exception as exc:
        return {
            "success": False,
            "data": report,
            "message": f"db_list_prospects failed: {exc}",
        }

    if not list_result.get("success"):
        return {
            "success": False,
            "data": report,
            "message": "db_list_prospects error: " + list_result.get("message", "unknown"),
        }

    prospects: List[Dict] = list_result.get("data", {}).get("prospects", [])

    if not prospects:
        return {
            "success": True,
            "data": report,
            "message": "No discovered prospects in pipeline. Nothing to do.",
        }

    # ── 2. Process each prospect ─────────────────────────────────────────────
    for p in prospects:
        pid = str(p.get("id", ""))
        name = p.get("name", "unknown")
        company = p.get("company", "unknown")
        bant = int(p.get("bant_score") or 0)
        source = str(p.get("source", "")).lower()
        email = str(p.get("email", "")).strip()
        notes = str(p.get("notes", ""))

        entry: Dict[str, Any] = {
            "id": pid,
            "name": name,
            "company": company,
            "bant_score": bant,
        }

        # Gate: skip low-quality leads
        if bant <= 40:
            report["skipped_low_bant"] += 1
            entry["action"] = "skipped"
            entry["reason"] = f"bant_score {bant} <= 40 (threshold: 40)"
            report["details"].append(entry)
            continue

        report["processed"] += 1
        action_taken = "none"
        channel_used = "none"

        try:
            # ── 3a. Moltbook path ─────────────────────────────────────────
            if "moltbook" in source:
                post_id = _extract_post_id(notes)
                if post_id:
                    message = _generate_message(p, "moltbook")
                    comment_result = await moltbook_comment(
                        {"post_id": post_id, "content": message}
                    )
                    if comment_result.get("success"):
                        report["moltbook_sent"] += 1
                        action_taken = "moltbook_comment"
                        channel_used = f"post_id:{post_id[:12]}"
                    else:
                        # Comment failed — fall through to email
                        action_taken = "moltbook_failed"
                        channel_used = comment_result.get("message", "error")
                else:
                    action_taken = "moltbook_no_post_id"

            # ── 3b. Email path ────────────────────────────────────────────
            if (
                action_taken in ("none", "moltbook_no_post_id", "moltbook_failed")
                and email
                and "@" in email
            ):
                template = _generate_message(p, "email")
                note_payload = f"[OUTREACH_TEMPLATE]\n{template}"
                await db_update_prospect({"id": pid, "notes": note_payload})
                report["email_templates_saved"] += 1
                action_taken = "email_template_saved"
                channel_used = email

            # ── No channel found ──────────────────────────────────────────
            if action_taken == "none":
                report["no_channel"] += 1
                entry["action"] = "no_channel"
                entry["reason"] = "No Moltbook post_id and no email address available"
                report["details"].append(entry)
                continue

            # ── 4. Update status to outreach ──────────────────────────────
            update_result = await db_update_prospect({"id": pid, "status": "outreach"})
            if not update_result.get("success"):
                report["errors"] += 1
                entry["update_error"] = update_result.get("message", "update failed")

            entry["action"] = action_taken
            entry["channel"] = channel_used

        except Exception as exc:
            report["errors"] += 1
            entry["action"] = "error"
            entry["error"] = str(exc)

        report["details"].append(entry)

    # ── 5. Summary ────────────────────────────────────────────────────────────
    total = len(prospects)
    msg = (
        f"Auto-outreach complete. "
        f"{total} prospects scanned | "
        f"{report['processed']} qualified (BANT>40) | "
        f"{report['moltbook_sent']} Moltbook comments posted | "
        f"{report['email_templates_saved']} email templates saved | "
        f"{report['skipped_low_bant']} skipped (low BANT) | "
        f"{report['no_channel']} had no reachable channel | "
        f"{report['errors']} errors"
    )

    return {"success": True, "data": report, "message": msg}


# ─────────────────────────────────────────────────────────────────────────────
# Skill manifest
# ─────────────────────────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "auto_outreach",
        "description": (
            "Automated outreach engine. Reads prospects with status=discovered and "
            "bant_score>40, generates personalized cold messages, posts on Moltbook "
            "(comment on prospect's post) or saves email template to notes, then "
            "updates status to 'outreach'. Returns full report with per-prospect details."
        ),
        "handler": auto_outreach,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    }
]
