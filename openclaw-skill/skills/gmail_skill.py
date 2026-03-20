"""Gmail — autonomous email via Google Gmail API (OAuth2).

Wave sends, reads, and replies to emails independently.
Uses Gmail API with service account or OAuth2 refresh token.

Setup:
1. Create Google Cloud project → Enable Gmail API
2. Create OAuth2 credentials (Desktop app type)
3. Run: python3 gmail_skill.py --setup  (one-time auth flow)
4. Set env vars: GMAIL_CREDENTIALS_FILE, GMAIL_TOKEN_FILE
   Or place files at: memory/gmail_credentials.json, memory/gmail_token.json
"""

from __future__ import annotations

import base64
import json
import logging
import os
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("openclaw.skills.gmail")

MEMORY_DIR = Path(__file__).parent.parent / "memory"
CREDENTIALS_FILE = os.environ.get("GMAIL_CREDENTIALS_FILE", str(MEMORY_DIR / "gmail_credentials.json"))
TOKEN_FILE = os.environ.get("GMAIL_TOKEN_FILE", str(MEMORY_DIR / "gmail_token.json"))
OUTREACH_LOG = MEMORY_DIR / "email_outreach_log.jsonl"

GMAIL_API = "https://gmail.googleapis.com/gmail/v1"
SCOPES = ["https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/gmail.readonly"]

# Rate limits to prevent abuse
MAX_EMAILS_PER_DAY = int(os.environ.get("WAVE_MAX_EMAILS_DAY", "20"))
MAX_EMAILS_PER_HOUR = int(os.environ.get("WAVE_MAX_EMAILS_HOUR", "5"))


def _load_token() -> Optional[dict]:
    """Load OAuth2 token from file."""
    path = Path(TOKEN_FILE)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return None


def _save_token(token: dict):
    """Save OAuth2 token to file."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    Path(TOKEN_FILE).write_text(json.dumps(token, indent=2))


async def _get_access_token() -> Optional[str]:
    """Get valid access token, refreshing if needed."""
    token = _load_token()
    if not token:
        return None

    # Check if token needs refresh
    access_token = token.get("access_token")
    refresh_token = token.get("refresh_token")
    expiry = token.get("expiry", "")

    if expiry:
        try:
            exp_dt = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
            if datetime.utcnow().timestamp() < exp_dt.timestamp() - 60:
                return access_token
        except Exception:
            pass

    # Refresh the token
    if not refresh_token:
        return access_token  # Try anyway

    creds = {}
    creds_path = Path(CREDENTIALS_FILE)
    if creds_path.exists():
        raw = json.loads(creds_path.read_text())
        creds = raw.get("installed", raw.get("web", {}))

    if not creds.get("client_id"):
        return access_token

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post("https://oauth2.googleapis.com/token", data={
                "client_id": creds["client_id"],
                "client_secret": creds["client_secret"],
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            })
            data = resp.json()

        if "access_token" in data:
            token["access_token"] = data["access_token"]
            if "expires_in" in data:
                from datetime import timedelta
                token["expiry"] = (datetime.utcnow() + timedelta(seconds=data["expires_in"])).isoformat() + "Z"
            _save_token(token)
            return data["access_token"]
    except Exception as e:
        logger.error("Token refresh failed: %s", e)

    return access_token


def _log_outreach(entry: dict):
    """Log email sent for tracking and rate limiting."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTREACH_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


def _check_rate_limit() -> Optional[str]:
    """Check if we're within rate limits. Returns error message if exceeded."""
    if not OUTREACH_LOG.exists():
        return None

    lines = OUTREACH_LOG.read_text().strip().split("\n")
    now = datetime.utcnow()

    today_count = 0
    hour_count = 0

    for line in reversed(lines):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            ts = datetime.fromisoformat(entry.get("timestamp", "2000-01-01"))
            delta = (now - ts).total_seconds()

            if delta < 86400:
                today_count += 1
            if delta < 3600:
                hour_count += 1

            if delta > 86400:
                break
        except Exception:
            continue

    if today_count >= MAX_EMAILS_PER_DAY:
        return "Daily email limit reached (%d/%d). Wait until tomorrow." % (today_count, MAX_EMAILS_PER_DAY)
    if hour_count >= MAX_EMAILS_PER_HOUR:
        return "Hourly email limit reached (%d/%d). Wait 1 hour." % (hour_count, MAX_EMAILS_PER_HOUR)

    return None


async def send_email(params: Dict[str, Any]) -> Dict:
    """Send an email via Gmail API. Supports plain text and HTML.

    Rate limited to prevent abuse: max 20/day, 5/hour.
    All sent emails are logged for tracking.
    """
    to = params.get("to", "")
    subject = params.get("subject", "")
    body = params.get("body", "")
    html = params.get("html", False)
    cc = params.get("cc", "")
    reply_to_message_id = params.get("reply_to_message_id", "")

    if not to or not subject or not body:
        return {"success": False, "data": None, "message": "Missing required fields: to, subject, body"}

    # Rate limit check
    rate_error = _check_rate_limit()
    if rate_error:
        return {"success": False, "data": None, "message": rate_error}

    access_token = await _get_access_token()
    if not access_token:
        return {
            "success": False, "data": None,
            "message": "Gmail not configured. Run: python3 skills/gmail_skill.py --setup",
        }

    # Build MIME message
    msg = MIMEMultipart("alternative") if html else MIMEText(body, "plain")
    if html:
        msg.attach(MIMEText(body, "plain"))
        msg.attach(MIMEText(body, "html"))

    msg["To"] = to
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc
    if reply_to_message_id:
        msg["In-Reply-To"] = reply_to_message_id
        msg["References"] = reply_to_message_id

    # Encode as base64url
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "%s/users/me/messages/send" % GMAIL_API,
                headers={"Authorization": "Bearer %s" % access_token},
                json={"raw": raw},
            )
            data = resp.json()

        if resp.status_code in (200, 201):
            _log_outreach({
                "timestamp": datetime.utcnow().isoformat(),
                "to": to,
                "subject": subject,
                "message_id": data.get("id", ""),
                "thread_id": data.get("threadId", ""),
                "status": "sent",
            })
            return {
                "success": True,
                "data": {"message_id": data.get("id"), "thread_id": data.get("threadId")},
                "message": "Email sent to %s: %s" % (to, subject),
            }
        else:
            error = data.get("error", {}).get("message", str(data))
            return {"success": False, "data": data, "message": "Gmail API error: %s" % error}

    except Exception as e:
        return {"success": False, "data": None, "message": "Send failed: %s" % str(e)}


async def read_emails(params: Dict[str, Any]) -> Dict:
    """Read emails from Gmail inbox. Supports search queries.

    Use Gmail search syntax: 'is:unread', 'from:user@example.com',
    'subject:bluewave', 'after:2026/03/01', etc.
    """
    query = params.get("query", "is:unread")
    max_results = min(params.get("max_results", 10), 20)

    access_token = await _get_access_token()
    if not access_token:
        return {"success": False, "data": None, "message": "Gmail not configured."}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # List messages
            resp = await client.get(
                "%s/users/me/messages" % GMAIL_API,
                headers={"Authorization": "Bearer %s" % access_token},
                params={"q": query, "maxResults": max_results},
            )
            listing = resp.json()

        messages = listing.get("messages", [])
        if not messages:
            return {"success": True, "data": [], "message": "No emails found for query: %s" % query}

        # Fetch each message's details
        results = []
        async with httpx.AsyncClient(timeout=30) as client:
            for msg_ref in messages[:max_results]:
                try:
                    resp = await client.get(
                        "%s/users/me/messages/%s" % (GMAIL_API, msg_ref["id"]),
                        headers={"Authorization": "Bearer %s" % access_token},
                        params={"format": "metadata", "metadataHeaders": ["From", "To", "Subject", "Date"]},
                    )
                    msg_data = resp.json()

                    headers = {h["name"]: h["value"] for h in msg_data.get("payload", {}).get("headers", [])}
                    results.append({
                        "id": msg_data.get("id"),
                        "thread_id": msg_data.get("threadId"),
                        "from": headers.get("From", ""),
                        "to": headers.get("To", ""),
                        "subject": headers.get("Subject", ""),
                        "date": headers.get("Date", ""),
                        "snippet": msg_data.get("snippet", "")[:200],
                        "labels": msg_data.get("labelIds", []),
                    })
                except Exception:
                    continue

        lines = ["**Emails found (%d):**\n" % len(results)]
        for r in results:
            lines.append("- **%s** from %s (%s)\n  %s\n" % (
                r["subject"][:60], r["from"][:40], r["date"][:20], r["snippet"][:120],
            ))

        return {"success": True, "data": results, "message": "\n".join(lines)}

    except Exception as e:
        return {"success": False, "data": None, "message": "Read failed: %s" % str(e)}


async def read_email_body(params: Dict[str, Any]) -> Dict:
    """Read the full body of a specific email by ID."""
    message_id = params.get("message_id", "")
    if not message_id:
        return {"success": False, "data": None, "message": "Missing message_id"}

    access_token = await _get_access_token()
    if not access_token:
        return {"success": False, "data": None, "message": "Gmail not configured."}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "%s/users/me/messages/%s" % (GMAIL_API, message_id),
                headers={"Authorization": "Bearer %s" % access_token},
                params={"format": "full"},
            )
            msg_data = resp.json()

        # Extract body from payload
        body_text = ""
        payload = msg_data.get("payload", {})

        def _extract_body(part):
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
            for sub in part.get("parts", []):
                result = _extract_body(sub)
                if result:
                    return result
            return ""

        body_text = _extract_body(payload)
        if not body_text and payload.get("body", {}).get("data"):
            body_text = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

        headers = {h["name"]: h["value"] for h in payload.get("headers", [])}

        return {
            "success": True,
            "data": {
                "id": message_id,
                "from": headers.get("From", ""),
                "subject": headers.get("Subject", ""),
                "body": body_text[:3000],
            },
            "message": "**From:** %s\n**Subject:** %s\n\n%s" % (
                headers.get("From", ""), headers.get("Subject", ""), body_text[:1500],
            ),
        }
    except Exception as e:
        return {"success": False, "data": None, "message": "Read body failed: %s" % str(e)}


async def check_replies(params: Dict[str, Any]) -> Dict:
    """Check for replies to outreach emails Wave has sent.

    Scans the outreach log and checks for replies in the same threads.
    This closes the feedback loop — Wave knows who responded.
    """
    access_token = await _get_access_token()
    if not access_token:
        return {"success": False, "data": None, "message": "Gmail not configured."}

    if not OUTREACH_LOG.exists():
        return {"success": True, "data": [], "message": "No outreach emails sent yet."}

    # Read sent emails
    lines = OUTREACH_LOG.read_text().strip().split("\n")
    sent = []
    for line in lines[-50:]:
        if line.strip():
            try:
                sent.append(json.loads(line))
            except Exception:
                pass

    if not sent:
        return {"success": True, "data": [], "message": "No outreach emails to check."}

    # Check for replies using thread IDs
    replies_found = []
    async with httpx.AsyncClient(timeout=30) as client:
        for entry in sent:
            thread_id = entry.get("thread_id")
            if not thread_id:
                continue
            try:
                resp = await client.get(
                    "%s/users/me/threads/%s" % (GMAIL_API, thread_id),
                    headers={"Authorization": "Bearer %s" % access_token},
                    params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]},
                )
                thread = resp.json()
                messages = thread.get("messages", [])

                if len(messages) > 1:
                    # Has replies
                    for msg in messages[1:]:
                        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
                        replies_found.append({
                            "original_to": entry.get("to"),
                            "original_subject": entry.get("subject"),
                            "reply_from": headers.get("From", ""),
                            "reply_date": headers.get("Date", ""),
                            "snippet": msg.get("snippet", "")[:200],
                            "message_id": msg.get("id"),
                        })
            except Exception:
                continue

    if replies_found:
        lines = ["**Replies to outreach (%d):**\n" % len(replies_found)]
        for r in replies_found:
            lines.append("- **%s** replied to '%s'\n  %s\n" % (
                r["reply_from"][:40], r["original_subject"][:40], r["snippet"][:120],
            ))
        return {"success": True, "data": replies_found, "message": "\n".join(lines)}

    return {"success": True, "data": [], "message": "No replies yet to %d sent emails." % len(sent)}


# ── OAuth2 Setup (run once) ──────────────────────────────────

def _run_setup():
    """Interactive OAuth2 setup. Run: python3 gmail_skill.py --setup"""
    import sys

    creds_path = Path(CREDENTIALS_FILE)
    if not creds_path.exists():
        print("Download OAuth2 credentials from Google Cloud Console.")
        print("Place the JSON file at: %s" % CREDENTIALS_FILE)
        print("Then run this script again.")
        sys.exit(1)

    raw = json.loads(creds_path.read_text())
    creds = raw.get("installed", raw.get("web", {}))

    client_id = creds["client_id"]
    client_secret = creds["client_secret"]
    redirect_uri = creds.get("redirect_uris", ["urn:ietf:wg:oauth:2.0:oob"])[0]

    scopes = " ".join(SCOPES)
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        "client_id=%s&redirect_uri=%s&response_type=code&scope=%s&access_type=offline&prompt=consent"
    ) % (client_id, redirect_uri, scopes)

    print("\n1. Open this URL in your browser:\n")
    print(auth_url)
    print("\n2. Authorize and paste the code below:\n")

    code = input("Code: ").strip()

    import requests
    resp = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    })
    token = resp.json()

    if "access_token" in token:
        from datetime import timedelta
        token["expiry"] = (datetime.utcnow() + timedelta(seconds=token.get("expires_in", 3600))).isoformat() + "Z"
        _save_token(token)
        print("\nToken saved to %s" % TOKEN_FILE)
        print("Gmail integration ready.")
    else:
        print("Error: %s" % token)


TOOLS = [
    {
        "name": "gmail_send",
        "description": "Send an email via Gmail API. Rate limited to 20/day, 5/hour. All sent emails are logged. Supports plain text and HTML. Use for outreach, follow-ups, proposals, and client communication.",
        "handler": send_email,
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject line"},
                "body": {"type": "string", "description": "Email body (plain text or HTML)"},
                "html": {"type": "boolean", "default": False, "description": "Send as HTML"},
                "cc": {"type": "string", "description": "CC recipients (comma-separated)"},
                "reply_to_message_id": {"type": "string", "description": "Gmail message ID to reply to (threads the conversation)"},
            },
            "required": ["to", "subject", "body"],
        },
    },
    {
        "name": "gmail_read",
        "description": "Read emails from Gmail inbox. Supports Gmail search queries: 'is:unread', 'from:user@example.com', 'subject:bluewave', 'after:2026/03/01'. Use to check for client inquiries, replies, and opportunities.",
        "handler": read_emails,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "default": "is:unread", "description": "Gmail search query"},
                "max_results": {"type": "integer", "default": 10, "description": "Max emails to return (max 20)"},
            },
        },
    },
    {
        "name": "gmail_read_body",
        "description": "Read the full body text of a specific email by message ID. Use after gmail_read to get full content of interesting emails.",
        "handler": read_email_body,
        "parameters": {
            "type": "object",
            "properties": {
                "message_id": {"type": "string", "description": "Gmail message ID from gmail_read results"},
            },
            "required": ["message_id"],
        },
    },
    {
        "name": "gmail_check_replies",
        "description": "Check for replies to outreach emails Wave has sent. Scans thread IDs from the outreach log and detects responses. Use in every check_payments/hunt cycle to close the feedback loop.",
        "handler": check_replies,
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
]


if __name__ == "__main__":
    import sys
    if "--setup" in sys.argv:
        _run_setup()
    else:
        print("Usage: python3 gmail_skill.py --setup")
