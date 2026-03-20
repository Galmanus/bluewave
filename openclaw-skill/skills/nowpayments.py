"""NOWPayments — crypto payment gateway for autonomous revenue.

Wave creates invoices, shares payment links, and auto-confirms payments.
Supports 350+ cryptocurrencies. Fees: 0.5-1%. No initial KYC.

Setup: Get API key at https://nowpayments.io/ → set NOWPAYMENTS_API_KEY env var.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import httpx

logger = logging.getLogger("openclaw.skills.nowpayments")

API_KEY = os.environ.get("NOWPAYMENTS_API_KEY", "")
API_BASE = "https://api.nowpayments.io/v1"
MEMORY_DIR = Path(__file__).parent.parent / "memory"
INVOICES_FILE = MEMORY_DIR / "nowpayments_invoices.jsonl"

TIMEOUT = httpx.Timeout(20.0, connect=10.0)


def _headers():
    return {"x-api-key": API_KEY, "Content-Type": "application/json"}


def _log_invoice(entry: dict):
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    with open(INVOICES_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


def _read_invoices(limit: int = 50) -> list:
    if not INVOICES_FILE.exists():
        return []
    lines = INVOICES_FILE.read_text().strip().split("\n")
    return [json.loads(l) for l in lines[-limit:] if l.strip()]


async def create_invoice(params: Dict[str, Any]) -> Dict:
    """Create a crypto payment invoice. Returns payment link that accepts 350+ coins.

    The client picks their preferred crypto at checkout. NOWPayments handles conversion.
    Wave gets paid in the configured payout currency (USDT/BTC/HBAR/etc).
    """
    if not API_KEY:
        return {"success": False, "data": None, "message": "NOWPayments not configured. Set NOWPAYMENTS_API_KEY."}

    price_amount = params.get("amount_usd", 0)
    currency = params.get("currency", "usd")
    service = params.get("service", "Bluewave AI Service")
    client_email = params.get("client_email", "")
    order_id = params.get("order_id", "wave_%d" % int(datetime.utcnow().timestamp()))

    if price_amount <= 0:
        return {"success": False, "data": None, "message": "Amount must be > 0"}

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post("%s/invoice" % API_BASE, headers=_headers(), json={
                "price_amount": float(price_amount),
                "price_currency": currency,
                "order_id": order_id,
                "order_description": service,
                "success_url": "https://bluewave.app/payment/success",
                "cancel_url": "https://bluewave.app/payment/cancel",
            })
            data = resp.json()

        if resp.status_code in (200, 201) and data.get("id"):
            invoice_url = data.get("invoice_url", "")

            _log_invoice({
                "timestamp": datetime.utcnow().isoformat(),
                "invoice_id": data["id"],
                "order_id": order_id,
                "amount_usd": price_amount,
                "service": service,
                "client_email": client_email,
                "invoice_url": invoice_url,
                "status": "waiting",
            })

            return {
                "success": True,
                "data": {
                    "invoice_id": data["id"],
                    "invoice_url": invoice_url,
                    "order_id": order_id,
                    "amount": price_amount,
                },
                "message": (
                    "**Invoice Created!**\n\n"
                    "Service: **%s**\n"
                    "Amount: **$%.2f**\n"
                    "Payment link: %s\n\n"
                    "Client can pay with ANY of 350+ cryptocurrencies.\n"
                    "Payment auto-confirms. Share this link with the client."
                ) % (service, price_amount, invoice_url),
            }
        else:
            error = data.get("message", str(data))
            return {"success": False, "data": data, "message": "Invoice creation failed: %s" % error}

    except Exception as e:
        return {"success": False, "data": None, "message": "NOWPayments error: %s" % str(e)}


async def check_invoice(params: Dict[str, Any]) -> Dict:
    """Check the status of a specific invoice."""
    if not API_KEY:
        return {"success": False, "data": None, "message": "NOWPayments not configured."}

    invoice_id = params.get("invoice_id", "")
    if not invoice_id:
        return {"success": False, "data": None, "message": "Need invoice_id"}

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get("%s/payment/%s" % (API_BASE, invoice_id), headers=_headers())
            data = resp.json()

        status = data.get("payment_status", "unknown")
        paid = status in ("finished", "confirmed", "sending")

        return {
            "success": True,
            "data": {
                "invoice_id": invoice_id,
                "status": status,
                "paid": paid,
                "amount_received": data.get("actually_paid", 0),
                "pay_currency": data.get("pay_currency", ""),
            },
            "message": "Invoice %s: %s%s" % (
                invoice_id,
                "PAID!" if paid else status.upper(),
                " (%.6f %s)" % (data.get("actually_paid", 0), data.get("pay_currency", "")) if paid else "",
            ),
        }
    except Exception as e:
        return {"success": False, "data": None, "message": "Check failed: %s" % str(e)}


async def check_all_invoices(params: Dict[str, Any]) -> Dict:
    """Check status of all pending invoices. Auto-confirms paid ones."""
    if not API_KEY:
        return {"success": False, "data": None, "message": "NOWPayments not configured."}

    invoices = _read_invoices()
    pending = [inv for inv in invoices if inv.get("status") in ("waiting", "pending")]

    if not pending:
        return {"success": True, "data": [], "message": "No pending invoices."}

    results = []
    for inv in pending:
        invoice_id = inv.get("invoice_id", "")
        if not invoice_id:
            continue

        result = await check_invoice({"invoice_id": str(invoice_id)})
        if result.get("success") and result["data"].get("paid"):
            results.append({
                "invoice_id": invoice_id,
                "service": inv.get("service"),
                "amount_usd": inv.get("amount_usd"),
                "status": "PAID",
            })

    paid_count = len([r for r in results if r.get("status") == "PAID"])

    if paid_count:
        lines = ["**%d payments confirmed!**\n" % paid_count]
        for r in results:
            if r["status"] == "PAID":
                lines.append("- $%.2f for %s (invoice %s)" % (r["amount_usd"], r["service"], r["invoice_id"]))
        return {"success": True, "data": results, "message": "\n".join(lines)}

    return {"success": True, "data": [], "message": "Checked %d pending invoices. None paid yet." % len(pending)}


async def list_currencies(params: Dict[str, Any]) -> Dict:
    """List available cryptocurrencies for payment."""
    if not API_KEY:
        return {"success": False, "data": None, "message": "NOWPayments not configured."}

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get("%s/currencies" % API_BASE, headers=_headers())
            data = resp.json()

        currencies = data.get("currencies", [])
        popular = ["btc", "eth", "usdt", "usdc", "sol", "xrp", "ada", "dot", "matic", "hbar",
                    "bnb", "doge", "ltc", "avax", "trx", "near"]
        highlighted = [c for c in currencies if c in popular]

        return {
            "success": True,
            "data": {"total": len(currencies), "popular": highlighted},
            "message": "**%d cryptocurrencies accepted.**\nPopular: %s" % (
                len(currencies), ", ".join(c.upper() for c in highlighted),
            ),
        }
    except Exception as e:
        return {"success": False, "data": None, "message": "Error: %s" % str(e)}


async def get_estimate(params: Dict[str, Any]) -> Dict:
    """Get estimated payment amount in a specific crypto for a USD price."""
    if not API_KEY:
        return {"success": False, "data": None, "message": "NOWPayments not configured."}

    amount_usd = params.get("amount_usd", 10)
    crypto = params.get("crypto", "btc")

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get("%s/estimate" % API_BASE, headers=_headers(), params={
                "amount": amount_usd,
                "currency_from": "usd",
                "currency_to": crypto,
            })
            data = resp.json()

        estimated = data.get("estimated_amount", 0)
        return {
            "success": True,
            "data": {"usd": amount_usd, "crypto": crypto, "estimated": estimated},
            "message": "$%.2f = %.8f %s" % (amount_usd, estimated, crypto.upper()),
        }
    except Exception as e:
        return {"success": False, "data": None, "message": "Estimate failed: %s" % str(e)}


TOOLS = [
    {
        "name": "crypto_create_invoice",
        "description": "Create a crypto payment invoice via NOWPayments. Returns a payment link that accepts 350+ cryptocurrencies (BTC, ETH, USDT, SOL, etc). Client picks their coin at checkout. Fees: 0.5%. Use this when a client wants to pay for a service.",
        "handler": create_invoice,
        "parameters": {
            "type": "object",
            "properties": {
                "amount_usd": {"type": "number", "description": "Amount in USD"},
                "service": {"type": "string", "description": "Service description"},
                "client_email": {"type": "string", "description": "Client email for receipt"},
                "order_id": {"type": "string", "description": "Custom order ID"},
            },
            "required": ["amount_usd", "service"],
        },
    },
    {
        "name": "crypto_check_invoice",
        "description": "Check status of a specific crypto payment invoice. Returns: waiting, confirming, confirmed, sending, finished, failed, expired.",
        "handler": check_invoice,
        "parameters": {
            "type": "object",
            "properties": {
                "invoice_id": {"type": "string", "description": "NOWPayments invoice ID"},
            },
            "required": ["invoice_id"],
        },
    },
    {
        "name": "crypto_check_all_invoices",
        "description": "Check ALL pending crypto invoices at once. Auto-confirms paid ones. Use in every check_payments cycle.",
        "handler": check_all_invoices,
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "crypto_currencies",
        "description": "List all 350+ cryptocurrencies accepted for payment. Shows popular ones highlighted.",
        "handler": list_currencies,
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "crypto_estimate",
        "description": "Get estimated crypto amount for a USD price. Example: $10 = 0.00015 BTC. Use to show clients the price in their preferred crypto.",
        "handler": get_estimate,
        "parameters": {
            "type": "object",
            "properties": {
                "amount_usd": {"type": "number", "default": 10, "description": "USD amount"},
                "crypto": {"type": "string", "default": "btc", "description": "Target cryptocurrency (btc, eth, usdt, sol, etc)"},
            },
        },
    },
]
