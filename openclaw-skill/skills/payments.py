"""Payments — all payment methods Wave accepts.

Crypto (HBAR, USDT, USDC) + traditional (PIX).
Wave tells clients how to pay and tracks all incoming payments.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("openclaw.skills.payments")

MEMORY_DIR = Path(__file__).parent.parent / "memory"
PAYMENTS_FILE = MEMORY_DIR / "payments.jsonl"

# Manuel's payment addresses — all money flows here
PAYMENT_INFO = {
    "hbar": {
        "method": "HBAR (Hedera)",
        "address": os.environ.get("HBAR_WALLET_ADDRESS", ""),
        "network": "Hedera Mainnet",
        "instructions": "Send HBAR to the address below via MetaMask or any Hedera wallet.",
    },
    "pix": {
        "method": "PIX (Brazil instant transfer)",
        "key": os.environ.get("PIX_KEY", "007a1d60-71e0-425f-a5b8-6fa2742b4c70"),
        "instructions": "Send BRL via PIX to the key below. Instant confirmation.",
    },
    "usdt": {
        "method": "USDT (Tether)",
        "address": os.environ.get("USDT_WALLET_ADDRESS", ""),
        "networks": "Ethereum, BSC, Polygon, or Hedera",
        "instructions": "Send USDT to the address below on any supported network.",
    },
    "usdc": {
        "method": "USDC",
        "address": os.environ.get("USDC_WALLET_ADDRESS", ""),
        "networks": "Ethereum, BSC, Polygon, or Hedera",
        "instructions": "Send USDC to the address below on any supported network.",
    },
}


def _ensure_dir():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)


async def payment_instructions(params: Dict[str, Any]) -> Dict:
    """Generate payment instructions for a client. Tells them exactly how to pay."""
    service = params.get("service", "")
    amount_usd = params.get("amount_usd", 0)
    preferred_method = params.get("method", "")
    client_name = params.get("client_name", "")

    amount_brl = amount_usd * 5.70  # approximate USD/BRL
    amount_hbar = int(amount_usd / 0.095)  # approximate HBAR price

    lines = []
    if client_name:
        lines.append("**Payment for %s**" % client_name)
    if service:
        lines.append("Service: **%s**" % service)
    lines.append("Amount: **$%.2f** (R$%.2f)\n" % (amount_usd, amount_brl))

    lines.append("**Payment options:**\n")

    # PIX — easiest for Brazilians
    pix = PAYMENT_INFO["pix"]
    if pix["key"]:
        lines.append("**1. PIX (instant, Brazil)**")
        lines.append("   Key: `%s`" % pix["key"])
        lines.append("   Amount: R$%.2f" % amount_brl)
        lines.append("   Confirms instantly.\n")

    # HBAR
    hbar = PAYMENT_INFO["hbar"]
    if hbar["address"]:
        lines.append("**2. HBAR (Hedera)**")
        lines.append("   Address: `%s`" % hbar["address"])
        lines.append("   Amount: %d HBAR" % amount_hbar)
        lines.append("   Network: Hedera Mainnet\n")

    # USDT/USDC
    for token in ["usdt", "usdc"]:
        info = PAYMENT_INFO[token]
        if info["address"]:
            lines.append("**%s**" % info["method"])
            lines.append("   Address: `%s`" % info["address"])
            lines.append("   Amount: $%.2f %s" % (amount_usd, token.upper()))
            lines.append("   Networks: %s\n" % info["networks"])

    if not any([pix["key"], hbar["address"]]):
        lines.append("Payment addresses not configured yet. Contact @bluewave_wave_bot on Telegram.")

    lines.append("---")
    lines.append("After payment, send confirmation (screenshot or tx hash) and I'll deliver immediately.")

    return {"success": True, "data": PAYMENT_INFO, "message": "\n".join(lines)}


async def confirm_payment(params: Dict[str, Any]) -> Dict:
    """Log a confirmed payment from a client."""
    client = params.get("client", "anonymous")
    service = params.get("service", "")
    amount_usd = params.get("amount_usd", 0)
    method = params.get("method", "unknown")
    tx_hash = params.get("tx_hash", "")
    notes = params.get("notes", "")

    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "client": client,
        "service": service,
        "amount_usd": amount_usd,
        "amount_brl": amount_usd * 5.70,
        "method": method,
        "tx_hash": tx_hash,
        "notes": notes,
        "status": "confirmed",
    }

    _ensure_dir()
    with open(PAYMENTS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")

    return {
        "success": True,
        "data": entry,
        "message": "Payment confirmed: $%.2f from %s via %s for %s" % (
            amount_usd, client, method, service
        ),
    }


async def payment_history(params: Dict[str, Any]) -> Dict:
    """Show all confirmed payments."""
    if not PAYMENTS_FILE.exists():
        return {"success": True, "data": [], "message": "No payments yet."}

    lines_raw = PAYMENTS_FILE.read_text(encoding="utf-8").strip().split("\n")
    entries = [json.loads(l) for l in lines_raw if l.strip()]

    total_usd = sum(e.get("amount_usd", 0) for e in entries)
    total_brl = sum(e.get("amount_brl", 0) for e in entries)

    lines = [
        "**Payment History**\n",
        "Total: **$%.2f** (R$%.2f) across **%d** payments\n" % (total_usd, total_brl, len(entries)),
    ]
    for e in entries[-20:]:
        lines.append("- %s | %s | $%.2f | %s | %s" % (
            e.get("timestamp", "?")[:10],
            e.get("client", "?"),
            e.get("amount_usd", 0),
            e.get("method", "?"),
            e.get("service", "?"),
        ))

    return {"success": True, "data": entries, "message": "\n".join(lines)}


TOOLS = [
    {
        "name": "payment_instructions",
        "description": "Generate payment instructions for a client. Shows all accepted methods: PIX (BRL instant), HBAR, USDT, USDC. Includes exact amounts, addresses, and steps.",
        "handler": payment_instructions,
        "parameters": {
            "type": "object",
            "properties": {
                "service": {"type": "string", "description": "Service being paid for"},
                "amount_usd": {"type": "number", "description": "Amount in USD"},
                "method": {"type": "string", "description": "Preferred payment method"},
                "client_name": {"type": "string", "description": "Client name for the invoice"},
            },
            "required": ["amount_usd"],
        },
    },
    {
        "name": "confirm_payment",
        "description": "Log a confirmed payment from a client. Records client, amount, method, and tx hash persistently.",
        "handler": confirm_payment,
        "parameters": {
            "type": "object",
            "properties": {
                "client": {"type": "string", "description": "Client name"},
                "service": {"type": "string", "description": "Service delivered"},
                "amount_usd": {"type": "number", "description": "Amount in USD"},
                "method": {"type": "string", "enum": ["pix", "hbar", "usdt", "usdc", "other"]},
                "tx_hash": {"type": "string", "description": "Transaction hash or PIX confirmation"},
                "notes": {"type": "string"},
            },
            "required": ["client", "service", "amount_usd", "method"],
        },
    },
    {
        "name": "payment_history",
        "description": "Show all confirmed payments — total revenue, payment history, breakdown by method.",
        "handler": payment_history,
        "parameters": {"type": "object", "properties": {}},
    },
]
