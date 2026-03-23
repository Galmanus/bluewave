"""
Hunter.io — Find professional email addresses for outreach.

Free tier: 25 searches/month + 50 verifications/month.
Setup: HUNTER_API_KEY env var from https://hunter.io/

Enables Wave to find real email addresses for prospects
instead of just commenting on Moltbook posts.
"""

import logging
import os
from typing import Any, Dict

import httpx

logger = logging.getLogger("openclaw.hunter")

HUNTER_API_KEY = os.environ.get("HUNTER_API_KEY", "")
HUNTER_URL = "https://api.hunter.io/v2"


async def find_emails(params: Dict[str, Any]) -> Dict:
    """Find email addresses associated with a domain."""
    domain = params.get("domain", "")

    if not domain:
        return {"success": False, "data": None, "message": "Need a domain (e.g., 'company.com')"}

    if not HUNTER_API_KEY:
        return {"success": False, "data": None, "message": "HUNTER_API_KEY not configured. Get one free at hunter.io"}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(f"{HUNTER_URL}/domain-search", params={
                "domain": domain, "api_key": HUNTER_API_KEY,
            })
            data = r.json().get("data", {})

        emails = []
        for item in data.get("emails", [])[:5]:
            emails.append({
                "email": item.get("value", ""),
                "first_name": item.get("first_name", ""),
                "last_name": item.get("last_name", ""),
                "position": item.get("position", ""),
                "confidence": item.get("confidence", 0),
            })

        return {
            "success": True,
            "data": {
                "domain": domain,
                "organization": data.get("organization", ""),
                "emails": emails,
                "total": data.get("total", 0),
            },
            "message": f"Found {len(emails)} emails for {domain}"
        }
    except Exception as e:
        logger.error("Hunter.io failed: %s", e)
        return {"success": False, "data": None, "message": str(e)}


async def find_email(params: Dict[str, Any]) -> Dict:
    """Find a specific person's email given name and domain."""
    domain = params.get("domain", "")
    first_name = params.get("first_name", "")
    last_name = params.get("last_name", "")

    if not domain or not (first_name or last_name):
        return {"success": False, "data": None, "message": "Need domain + first_name or last_name"}

    if not HUNTER_API_KEY:
        return {"success": False, "data": None, "message": "HUNTER_API_KEY not configured"}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(f"{HUNTER_URL}/email-finder", params={
                "domain": domain,
                "first_name": first_name,
                "last_name": last_name,
                "api_key": HUNTER_API_KEY,
            })
            data = r.json().get("data", {})

        return {
            "success": True,
            "data": {
                "email": data.get("email", ""),
                "confidence": data.get("confidence", 0),
                "first_name": data.get("first_name", ""),
                "last_name": data.get("last_name", ""),
                "position": data.get("position", ""),
                "domain": domain,
            },
            "message": f"Found: {data.get('email', 'not found')} (confidence: {data.get('confidence', 0)}%)"
        }
    except Exception as e:
        return {"success": False, "data": None, "message": str(e)}


async def verify_email(params: Dict[str, Any]) -> Dict:
    """Verify if an email address is valid and deliverable."""
    email = params.get("email", "")

    if not email:
        return {"success": False, "data": None, "message": "Need an email address"}

    if not HUNTER_API_KEY:
        return {"success": False, "data": None, "message": "HUNTER_API_KEY not configured"}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(f"{HUNTER_URL}/email-verifier", params={
                "email": email, "api_key": HUNTER_API_KEY,
            })
            data = r.json().get("data", {})

        return {
            "success": True,
            "data": {
                "email": email,
                "status": data.get("status", "unknown"),
                "result": data.get("result", "unknown"),
                "score": data.get("score", 0),
            },
            "message": f"{email}: {data.get('result', 'unknown')} (score: {data.get('score', 0)})"
        }
    except Exception as e:
        return {"success": False, "data": None, "message": str(e)}


TOOLS = [
    {
        "name": "find_emails",
        "description": "Find all professional email addresses for a company domain. Use for prospect outreach.",
        "parameters": {
            "domain": "string — company domain (e.g., 'stripe.com')",
        },
        "handler": find_emails,
    },
    {
        "name": "find_email",
        "description": "Find a specific person's email given their name and company domain.",
        "parameters": {
            "domain": "string — company domain",
            "first_name": "string — person's first name",
            "last_name": "string — person's last name",
        },
        "handler": find_email,
    },
    {
        "name": "verify_email",
        "description": "Verify if an email address is valid and deliverable before sending.",
        "parameters": {
            "email": "string — email to verify",
        },
        "handler": verify_email,
    },
]
