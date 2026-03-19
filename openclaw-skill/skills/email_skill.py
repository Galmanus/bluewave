"""Email — send emails autonomously via SMTP."""

from __future__ import annotations
import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any, Dict

SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER)


async def send_email(params: Dict[str, Any]) -> Dict:
    """Send an email via SMTP."""
    if not SMTP_HOST or not SMTP_USER:
        return {
            "success": False, "data": None,
            "message": "Email not configured. Set SMTP_HOST, SMTP_USER, SMTP_PASS environment variables.",
        }

    to = params.get("to", "")
    subject = params.get("subject", "")
    body = params.get("body", "")
    html = params.get("html", False)

    if not to or not subject:
        return {"success": False, "data": None, "message": "Missing 'to' or 'subject'"}

    msg = MIMEMultipart("alternative")
    msg["From"] = SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject

    if html:
        msg.attach(MIMEText(body, "html"))
    else:
        msg.attach(MIMEText(body, "plain"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_FROM, to, msg.as_string())

        return {
            "success": True,
            "data": {"to": to, "subject": subject},
            "message": "Email sent to **%s**: %s" % (to, subject),
        }
    except Exception as e:
        return {"success": False, "data": None, "message": "Email failed: %s" % str(e)}


async def draft_cold_email(params: Dict[str, Any]) -> Dict:
    """Generate a cold outreach email draft (returns text, doesn't send)."""
    prospect_name = params.get("prospect_name", "")
    prospect_company = params.get("prospect_company", "")
    context = params.get("context", "")
    offer = params.get("offer", "Bluewave AI Creative Operations Platform")
    tone = params.get("tone", "professional but approachable")

    draft = {
        "subject_options": [
            "Quick question about %s's creative workflow" % prospect_company,
            "%s — saving 8 hours/week on content operations" % prospect_company,
            "How %s can automate creative approvals" % prospect_company,
        ],
        "body_template": (
            "Hi %s,\n\n"
            "I noticed %s %s. "
            "We built something that might save your creative team serious time.\n\n"
            "%s uses AI to automate the entire content lifecycle — "
            "from upload to brand compliance to approval to publishing. "
            "Teams using it save an average of 8.8 hours per week on asset management alone.\n\n"
            "Would a 15-minute demo be worth your time this week?\n\n"
            "Best,\nBluewavePrime\nAI Creative Operations"
        ) % (prospect_name, prospect_company, context or "is growing fast", offer),
        "prospect": prospect_name,
        "company": prospect_company,
    }

    return {
        "success": True,
        "data": draft,
        "message": (
            "**Cold email draft for %s (%s):**\n\n"
            "**Subject options:**\n%s\n\n"
            "**Body:**\n%s"
        ) % (
            prospect_name, prospect_company,
            "\n".join("- %s" % s for s in draft["subject_options"]),
            draft["body_template"],
        ),
    }


TOOLS = [
    {
        "name": "send_email",
        "description": "Send an email via SMTP. Use for outreach, notifications, reports. Requires SMTP configuration in environment.",
        "handler": send_email,
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject line"},
                "body": {"type": "string", "description": "Email body text"},
                "html": {"type": "boolean", "default": False, "description": "Send as HTML email"},
            },
            "required": ["to", "subject", "body"],
        },
    },
    {
        "name": "draft_cold_email",
        "description": "Generate a personalized cold outreach email draft. Use for lead generation and sales outreach. Does NOT send — returns draft for review.",
        "handler": draft_cold_email,
        "parameters": {
            "type": "object",
            "properties": {
                "prospect_name": {"type": "string", "description": "Name of the prospect"},
                "prospect_company": {"type": "string", "description": "Company name"},
                "context": {"type": "string", "description": "Relevant context about the prospect (e.g., recent funding, hiring)"},
                "offer": {"type": "string", "default": "Bluewave AI Creative Operations", "description": "What you're offering"},
                "tone": {"type": "string", "default": "professional but approachable"},
            },
            "required": ["prospect_name", "prospect_company"],
        },
    },
]
