"""
Stripe — International credit card payments.

Accept payments from enterprise clients worldwide.
2.9% + $0.30 per transaction.

Setup: STRIPE_SECRET_KEY env var from https://dashboard.stripe.com/
"""

import logging
import os
from typing import Any, Dict

import httpx

logger = logging.getLogger("openclaw.stripe")

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_URL = "https://api.stripe.com/v1"


async def create_payment_link(params: Dict[str, Any]) -> Dict:
    """Create a Stripe payment link for a service."""
    name = params.get("name", "Wave Service")
    amount_usd = float(params.get("amount_usd", 50))
    description = params.get("description", "")

    if not STRIPE_SECRET_KEY:
        return {"success": False, "data": None, "message": "STRIPE_SECRET_KEY not configured. Get one at dashboard.stripe.com"}

    try:
        amount_cents = int(amount_usd * 100)

        async with httpx.AsyncClient(timeout=15) as client:
            # Create a price
            price_r = await client.post(f"{STRIPE_URL}/prices", data={
                "unit_amount": amount_cents,
                "currency": "usd",
                "product_data[name]": name,
            }, auth=(STRIPE_SECRET_KEY, ""))
            price = price_r.json()

            # Create payment link
            link_r = await client.post(f"{STRIPE_URL}/payment_links", data={
                "line_items[0][price]": price["id"],
                "line_items[0][quantity]": 1,
            }, auth=(STRIPE_SECRET_KEY, ""))
            link = link_r.json()

        return {
            "success": True,
            "data": {
                "payment_url": link.get("url", ""),
                "amount": f"${amount_usd:.2f}",
                "service": name,
            },
            "message": f"Payment link created: ${amount_usd:.2f} for {name}"
        }
    except Exception as e:
        logger.error("Stripe failed: %s", e)
        return {"success": False, "data": None, "message": str(e)}


async def check_balance(params: Dict[str, Any]) -> Dict:
    """Check Stripe account balance."""
    if not STRIPE_SECRET_KEY:
        return {"success": False, "data": None, "message": "STRIPE_SECRET_KEY not configured"}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{STRIPE_URL}/balance", auth=(STRIPE_SECRET_KEY, ""))
            data = r.json()

        available = sum(b.get("amount", 0) for b in data.get("available", [])) / 100
        pending = sum(b.get("amount", 0) for b in data.get("pending", [])) / 100

        return {
            "success": True,
            "data": {"available_usd": available, "pending_usd": pending},
            "message": f"Stripe balance: ${available:.2f} available, ${pending:.2f} pending"
        }
    except Exception as e:
        return {"success": False, "data": None, "message": str(e)}


async def list_recent_payments(params: Dict[str, Any]) -> Dict:
    """List recent Stripe payments."""
    limit = min(int(params.get("limit", 5)), 20)

    if not STRIPE_SECRET_KEY:
        return {"success": False, "data": None, "message": "STRIPE_SECRET_KEY not configured"}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{STRIPE_URL}/charges", params={"limit": limit},
                                 auth=(STRIPE_SECRET_KEY, ""))
            data = r.json()

        payments = []
        for charge in data.get("data", []):
            payments.append({
                "amount": charge.get("amount", 0) / 100,
                "currency": charge.get("currency", "usd"),
                "status": charge.get("status", ""),
                "description": charge.get("description", ""),
                "created": charge.get("created", 0),
            })

        return {
            "success": True,
            "data": {"payments": payments},
            "message": f"{len(payments)} recent payments"
        }
    except Exception as e:
        return {"success": False, "data": None, "message": str(e)}


TOOLS = [
    {
        "name": "create_payment_link",
        "description": "Create a Stripe payment link for a service. Send to clients for credit card payment.",
        "parameters": {
            "name": "string — service name",
            "amount_usd": "float — price in USD",
            "description": "string — service description",
        },
        "handler": create_payment_link,
    },
    {
        "name": "stripe_balance",
        "description": "Check Stripe account balance — available and pending funds.",
        "parameters": {},
        "handler": check_balance,
    },
    {
        "name": "stripe_payments",
        "description": "List recent Stripe payments with amounts and status.",
        "parameters": {
            "limit": "int — number of payments (default 5)",
        },
        "handler": list_recent_payments,
    },
]
