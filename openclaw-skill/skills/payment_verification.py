"""Payment Verification — Wave confirms payments automatically.

HBAR: checks Hedera Mirror Node for incoming transactions (free, no API key)
PIX: creates QR code charges via Mercado Pago API (auto-confirms on payment)
"""

from __future__ import annotations

import json
import logging
import os
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

import httpx

logger = logging.getLogger("openclaw.skills.payment_verify")

MEMORY_DIR = Path(__file__).parent.parent / "memory"
PENDING_FILE = MEMORY_DIR / "pending_payments.json"
CONFIRMED_FILE = MEMORY_DIR / "payments.jsonl"

# Manuel's wallet address on Hedera (EVM format)
TREASURY_ADDRESS = os.environ.get("HBAR_WALLET_ADDRESS", "")

# Mercado Pago for PIX (get token at https://www.mercadopago.com.br/developers)
MP_ACCESS_TOKEN = os.environ.get("MERCADOPAGO_ACCESS_TOKEN", "")

HEDERA_MIRROR = "https://mainnet.mirrornode.hedera.com/api/v1"
HEDERA_MIRROR_TESTNET = "https://testnet.mirrornode.hedera.com/api/v1"
MIRROR_URL = os.environ.get("HEDERA_MIRROR_URL", HEDERA_MIRROR_TESTNET)

TIMEOUT = httpx.Timeout(15.0, connect=10.0)


def _ensure_dir():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def _load_pending() -> dict:
    _ensure_dir()
    if PENDING_FILE.exists():
        return json.loads(PENDING_FILE.read_text())
    return {}


def _save_pending(data: dict):
    _ensure_dir()
    PENDING_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def _log_confirmed(entry: dict):
    _ensure_dir()
    with open(CONFIRMED_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


# ══════════════════════════════════════════════════════════════
# HBAR VERIFICATION — checks blockchain directly, free, no keys
# ══════════════════════════════════════════════════════════════

async def verify_hbar_payment(params: Dict[str, Any]) -> Dict:
    """Check if an HBAR payment was received on Hedera.
    Scans recent transactions to Manuel's wallet for the expected amount."""

    expected_hbar = params.get("expected_hbar", 0)
    sender_address = params.get("sender_address", "")
    payment_id = params.get("payment_id", "")
    account_id = params.get("account_id", TREASURY_ADDRESS)

    if not account_id:
        return {"success": False, "data": None, "message": "Treasury address not configured. Set HBAR_WALLET_ADDRESS."}

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            # Query recent credit transactions to our account
            resp = await client.get(
                "%s/transactions?account.id=%s&type=credit&limit=20&order=desc" % (MIRROR_URL, account_id)
            )

            if resp.status_code != 200:
                # Try with EVM address format
                resp = await client.get(
                    "%s/accounts/%s" % (MIRROR_URL, account_id)
                )
                if resp.status_code == 200:
                    hedera_account = resp.json().get("account")
                    if hedera_account:
                        resp = await client.get(
                            "%s/transactions?account.id=%s&type=credit&limit=20&order=desc" % (MIRROR_URL, hedera_account)
                        )

            data = resp.json()
            transactions = data.get("transactions", [])

        if not transactions:
            return {
                "success": True,
                "data": {"found": False},
                "message": "No recent incoming transactions found for %s" % account_id,
            }

        # Look for matching transaction
        expected_tinybars = int(expected_hbar * 100_000_000) if expected_hbar else 0
        tolerance = int(0.5 * 100_000_000)  # 0.5 HBAR tolerance

        for tx in transactions:
            transfers = tx.get("transfers", [])
            for transfer in transfers:
                if transfer.get("account") == account_id and transfer.get("amount", 0) > 0:
                    received = transfer["amount"]

                    if expected_tinybars == 0 or abs(received - expected_tinybars) < tolerance:
                        tx_id = tx.get("transaction_id", "")
                        timestamp = tx.get("consensus_timestamp", "")

                        match = {
                            "found": True,
                            "tx_id": tx_id,
                            "amount_tinybars": received,
                            "amount_hbar": received / 100_000_000,
                            "amount_usd": (received / 100_000_000) * 0.095,
                            "timestamp": timestamp,
                            "result": tx.get("result", ""),
                            "hashscan": "https://hashscan.io/mainnet/transaction/%s" % tx_id,
                        }

                        return {
                            "success": True,
                            "data": match,
                            "message": (
                                "PAYMENT CONFIRMED on Hedera!\n"
                                "Amount: %.2f HBAR (~$%.2f)\n"
                                "TX: %s\n"
                                "Verify: %s"
                            ) % (match["amount_hbar"], match["amount_usd"], tx_id, match["hashscan"]),
                        }

        return {
            "success": True,
            "data": {"found": False, "transactions_checked": len(transactions)},
            "message": "No matching payment found. Checked %d recent transactions." % len(transactions),
        }

    except Exception as e:
        return {"success": False, "data": None, "message": "HBAR verification failed: %s" % str(e)}


# ══════════════════════════════════════════════════════════════
# PIX — Mercado Pago integration (creates QR code, auto-confirms)
# ══════════════════════════════════════════════════════════════

async def create_pix_charge(params: Dict[str, Any]) -> Dict:
    """Create a PIX charge via Mercado Pago. Returns QR code for client to scan.
    Payment auto-confirms — no manual checking needed."""

    amount_brl = params.get("amount_brl", 0)
    description = params.get("description", "Bluewave AI Service")
    client_email = params.get("client_email", "")
    payment_id = params.get("payment_id", "")

    if not MP_ACCESS_TOKEN:
        # Fallback: manual PIX
        return {
            "success": True,
            "data": {"method": "manual_pix", "key": "m.galmanus@gmail.com", "amount": amount_brl},
            "message": (
                "**PIX Payment (manual)**\n\n"
                "Amount: **R$%.2f**\n"
                "PIX Key: `m.galmanus@gmail.com`\n"
                "Name: Manuel\n\n"
                "Send payment and share the receipt/screenshot.\n"
                "I'll confirm and deliver immediately."
            ) % amount_brl,
        }

    # Create Mercado Pago PIX charge
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                "https://api.mercadopago.com/v1/payments",
                headers={
                    "Authorization": "Bearer %s" % MP_ACCESS_TOKEN,
                    "Content-Type": "application/json",
                    "X-Idempotency-Key": payment_id or hashlib.md5(
                        ("%s_%s_%s" % (amount_brl, description, datetime.utcnow().isoformat())).encode()
                    ).hexdigest(),
                },
                json={
                    "transaction_amount": float(amount_brl),
                    "description": description,
                    "payment_method_id": "pix",
                    "payer": {
                        "email": client_email or "cliente@bluewave.app",
                    },
                },
            )
            data = resp.json()

        if resp.status_code in (200, 201):
            mp_id = data.get("id")
            pix_data = data.get("point_of_interaction", {}).get("transaction_data", {})
            qr_code = pix_data.get("qr_code", "")
            qr_code_base64 = pix_data.get("qr_code_base64", "")
            ticket_url = pix_data.get("ticket_url", "")

            # Save as pending
            pending = _load_pending()
            pending[str(mp_id)] = {
                "mp_id": mp_id,
                "amount_brl": amount_brl,
                "description": description,
                "status": "pending",
                "created_at": datetime.utcnow().isoformat(),
            }
            _save_pending(pending)

            return {
                "success": True,
                "data": {
                    "mp_id": mp_id,
                    "qr_code": qr_code,
                    "ticket_url": ticket_url,
                    "status": "pending",
                },
                "message": (
                    "**PIX Charge Created!**\n\n"
                    "Amount: **R$%.2f**\n"
                    "Payment link: %s\n\n"
                    "PIX Copy-Paste code:\n`%s`\n\n"
                    "Payment auto-confirms. I'll know the moment it's paid."
                ) % (amount_brl, ticket_url, qr_code[:80] + "..." if len(qr_code) > 80 else qr_code),
            }
        else:
            error = data.get("message", data.get("error", "Unknown error"))
            return {"success": False, "data": data, "message": "PIX charge failed: %s" % error}

    except Exception as e:
        return {"success": False, "data": None, "message": "Mercado Pago error: %s" % str(e)}


async def check_pix_status(params: Dict[str, Any]) -> Dict:
    """Check if a PIX payment was completed."""
    mp_id = params.get("mp_id", "")

    if not mp_id:
        # Check all pending
        pending = _load_pending()
        if not pending:
            return {"success": True, "data": {}, "message": "No pending PIX payments."}

        results = []
        for pid, info in pending.items():
            if MP_ACCESS_TOKEN:
                try:
                    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                        resp = await client.get(
                            "https://api.mercadopago.com/v1/payments/%s" % pid,
                            headers={"Authorization": "Bearer %s" % MP_ACCESS_TOKEN},
                        )
                        data = resp.json()
                        status = data.get("status", "unknown")

                        if status == "approved":
                            # Auto-confirm!
                            _log_confirmed({
                                "timestamp": datetime.utcnow().isoformat(),
                                "client": data.get("payer", {}).get("email", "unknown"),
                                "service": info.get("description", ""),
                                "amount_usd": info.get("amount_brl", 0) / 5.70,
                                "amount_brl": info.get("amount_brl", 0),
                                "method": "pix",
                                "tx_hash": "mp_%s" % pid,
                                "status": "confirmed",
                            })
                            del pending[pid]
                            _save_pending(pending)

                        results.append({"mp_id": pid, "status": status, "amount": info.get("amount_brl")})
                except Exception:
                    results.append({"mp_id": pid, "status": "check_failed"})
            else:
                results.append({"mp_id": pid, "status": info.get("status", "pending"), "amount": info.get("amount_brl")})

        confirmed = [r for r in results if r["status"] == "approved"]
        pending_list = [r for r in results if r["status"] != "approved"]

        lines = ["**PIX Payment Status:**\n"]
        if confirmed:
            lines.append("CONFIRMED: %d payments" % len(confirmed))
            for c in confirmed:
                lines.append("  R$%.2f — PAID" % (c.get("amount", 0)))
        if pending_list:
            lines.append("Pending: %d" % len(pending_list))
            for p in pending_list:
                lines.append("  R$%.2f — %s" % (p.get("amount", 0), p.get("status", "?")))

        return {"success": True, "data": results, "message": "\n".join(lines)}

    # Check specific payment
    if not MP_ACCESS_TOKEN:
        return {"success": False, "data": None, "message": "Mercado Pago not configured. Set MERCADOPAGO_ACCESS_TOKEN."}

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(
                "https://api.mercadopago.com/v1/payments/%s" % mp_id,
                headers={"Authorization": "Bearer %s" % MP_ACCESS_TOKEN},
            )
            data = resp.json()

        status = data.get("status", "unknown")
        approved = status == "approved"

        if approved:
            _log_confirmed({
                "timestamp": datetime.utcnow().isoformat(),
                "client": data.get("payer", {}).get("email", "unknown"),
                "service": data.get("description", ""),
                "amount_usd": data.get("transaction_amount", 0) / 5.70,
                "amount_brl": data.get("transaction_amount", 0),
                "method": "pix",
                "tx_hash": "mp_%s" % mp_id,
                "status": "confirmed",
            })

        return {
            "success": True,
            "data": {"status": status, "approved": approved},
            "message": "PIX %s — %s (R$%.2f)" % (
                mp_id,
                "PAID!" if approved else status.upper(),
                data.get("transaction_amount", 0),
            ),
        }
    except Exception as e:
        return {"success": False, "data": None, "message": "Status check failed: %s" % str(e)}


async def check_all_pending(params: Dict[str, Any]) -> Dict:
    """Check all pending payments — both HBAR and PIX. Auto-confirms when found."""
    results = {"hbar": None, "pix": None}

    # Check HBAR
    if TREASURY_ADDRESS:
        hbar_result = await verify_hbar_payment({"expected_hbar": 0})
        results["hbar"] = hbar_result.get("data", {})

    # Check PIX
    pix_result = await check_pix_status({})
    results["pix"] = pix_result.get("data", {})

    hbar_found = results["hbar"] and results["hbar"].get("found")
    pix_confirmed = any(r.get("status") == "approved" for r in (results["pix"] if isinstance(results["pix"], list) else []))

    if hbar_found or pix_confirmed:
        msg = "PAYMENTS FOUND!\n"
        if hbar_found:
            msg += "HBAR: %.2f received\n" % results["hbar"].get("amount_hbar", 0)
        if pix_confirmed:
            msg += "PIX: confirmed\n"
        msg += "\nServices can be delivered."
    else:
        msg = "No new payments detected. Will check again next cycle."

    return {"success": True, "data": results, "message": msg}


TOOLS = [
    {
        "name": "verify_hbar_payment",
        "description": "Check Hedera blockchain for incoming HBAR payment. Scans recent transactions to treasury wallet. Free, no API key needed. Returns tx hash and HashScan link if found.",
        "handler": verify_hbar_payment,
        "parameters": {
            "type": "object",
            "properties": {
                "expected_hbar": {"type": "number", "description": "Expected amount in HBAR (0 = any amount)"},
                "sender_address": {"type": "string", "description": "Expected sender address (optional)"},
                "account_id": {"type": "string", "description": "Account to check (defaults to treasury)"},
            },
        },
    },
    {
        "name": "create_pix_charge",
        "description": "Create a PIX payment charge. If Mercado Pago is configured, generates QR code that auto-confirms on payment. Otherwise, returns manual PIX instructions with key.",
        "handler": create_pix_charge,
        "parameters": {
            "type": "object",
            "properties": {
                "amount_brl": {"type": "number", "description": "Amount in BRL"},
                "description": {"type": "string", "default": "Bluewave AI Service"},
                "client_email": {"type": "string", "description": "Client email for receipt"},
            },
            "required": ["amount_brl"],
        },
    },
    {
        "name": "check_pix_status",
        "description": "Check if a PIX payment was completed. If Mercado Pago is configured, checks API automatically. Auto-confirms and logs when paid.",
        "handler": check_pix_status,
        "parameters": {
            "type": "object",
            "properties": {
                "mp_id": {"type": "string", "description": "Mercado Pago payment ID (empty = check all pending)"},
            },
        },
    },
    {
        "name": "check_all_pending",
        "description": "Check ALL pending payments at once — both HBAR (blockchain) and PIX (Mercado Pago). Auto-confirms any found. Use this in every cycle to catch payments.",
        "handler": check_all_pending,
        "parameters": {"type": "object", "properties": {}},
    },
]
