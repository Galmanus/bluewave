"""Payment Monitor — Wave's financial survival infrastructure.

Monitors incoming HBAR payments via Hedera Mirror Node (FREE public API).
Resolves EVM address to Hedera account ID, checks balance, detects transfers.

No SDK needed. No auth needed. Pure REST API.

Wallet: 0x46EB78DE85485ffD54EdA2f02D2a3c42C5a92381
"""

import httpx
import json
from datetime import datetime

MIRROR_BASE = "https://mainnet.mirrornode.hedera.com/api/v1"
WAVE_EVM_ADDRESS = "0x46EB78DE85485ffD54EdA2f02D2a3c42C5a92381"
TIMEOUT = httpx.Timeout(15.0, connect=10.0)


async def resolve_account(params):
    """Resolve Wave EVM address to Hedera account ID via mirror node."""
    evm_addr = params.get("evm_address", WAVE_EVM_ADDRESS)
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(MIRROR_BASE + "/accounts/" + evm_addr)
        if resp.status_code == 200:
            data = resp.json()
            account_id = data.get("account", "")
            bal = data.get("balance", {})
            hbar = bal.get("balance", 0) / 100_000_000 if isinstance(bal, dict) else 0
            return {
                "success": True,
                "data": {
                    "account_id": account_id,
                    "evm_address": evm_addr,
                    "balance_hbar": round(hbar, 8),
                    "hashscan": "https://hashscan.io/mainnet/account/" + account_id,
                },
                "message": "Account found: %s with %.4f HBAR" % (account_id, hbar),
            }
    return {
        "success": False,
        "data": {"evm_address": evm_addr},
        "message": (
            "Account not yet active on Hedera mainnet. "
            "To activate: send any amount of HBAR to EVM address %s "
            "via HashPack, Blade, or any Hedera wallet. "
            "Account auto-creates on first incoming transfer." % evm_addr
        ),
    }


async def check_payments(params):
    """Check for incoming HBAR payments to Wave wallet."""
    account_id = params.get("account_id", "")
    limit = params.get("limit", 25)

    # Auto-resolve if no account ID provided
    if not account_id:
        res = await resolve_account({})
        if res["success"]:
            account_id = res["data"]["account_id"]
        else:
            return res

    url = "%s/transactions?account.id=%s&limit=%d&order=desc" % (MIRROR_BASE, account_id, limit)

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            return {
                "success": False,
                "data": None,
                "message": "Mirror node error: %d" % resp.status_code,
            }
        data = resp.json()

    transactions = data.get("transactions", [])
    incoming = []

    for tx in transactions:
        if tx.get("result") != "SUCCESS":
            continue
        transfers = tx.get("transfers", [])
        for tr in transfers:
            if tr.get("account") == account_id and tr.get("amount", 0) > 0:
                # Find the sender (account with negative amount)
                sender = "unknown"
                for s in transfers:
                    if s.get("amount", 0) < 0 and s.get("account") != account_id:
                        sender = s.get("account")
                        break
                amt = tr["amount"] / 100_000_000
                tx_id = tx.get("transaction_id", "")
                incoming.append({
                    "tx_id": tx_id,
                    "amount_hbar": round(amt, 8),
                    "sender": sender,
                    "timestamp": tx.get("consensus_timestamp", ""),
                    "type": tx.get("name", ""),
                    "hashscan": "https://hashscan.io/mainnet/transaction/" + tx_id,
                })

    total = sum(t["amount_hbar"] for t in incoming)

    msg = "No incoming payments found."
    if incoming:
        msg = "Found %d incoming payment(s) totaling %.4f HBAR" % (len(incoming), total)

    return {
        "success": True,
        "data": {
            "account_id": account_id,
            "payments": incoming[:10],
            "total_hbar": round(total, 8),
            "count": len(incoming),
        },
        "message": msg,
    }


async def check_balance(params):
    """Check current HBAR balance of Wave wallet."""
    account_id = params.get("account_id", "")

    if not account_id:
        res = await resolve_account({})
        if res["success"]:
            account_id = res["data"]["account_id"]
        else:
            return res

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get("%s/balances?account.id=%s" % (MIRROR_BASE, account_id))
        if resp.status_code != 200:
            return {
                "success": False,
                "data": None,
                "message": "Mirror node error: %d" % resp.status_code,
            }
        data = resp.json()

    balances = data.get("balances", [])
    if not balances:
        return {
            "success": False,
            "data": {"account_id": account_id},
            "message": "No balance data found.",
        }

    b = balances[0]
    hbar = b.get("balance", 0) / 100_000_000
    tokens = b.get("tokens", [])

    token_msg = ""
    if tokens:
        token_msg = " + %d token(s)" % len(tokens)

    return {
        "success": True,
        "data": {
            "account_id": account_id,
            "hbar": round(hbar, 8),
            "tokens": tokens,
            "hashscan": "https://hashscan.io/mainnet/account/" + account_id,
        },
        "message": "Balance: %.4f HBAR%s" % (hbar, token_msg),
    }


async def payment_status(params):
    """Full payment system health check — account + balance + recent payments."""
    result = {"evm_address": WAVE_EVM_ADDRESS}

    # Step 1: Resolve account
    resolve = await resolve_account({})
    result["account_active"] = resolve["success"]

    if not resolve["success"]:
        result["status"] = "WAITING_FOR_ACTIVATION"
        result["wallet_address"] = WAVE_EVM_ADDRESS
        result["message"] = resolve["message"]
        return {"success": True, "data": result, "message": resolve["message"]}

    account_id = resolve["data"]["account_id"]
    result["account_id"] = account_id

    # Step 2: Balance
    balance = await check_balance({"account_id": account_id})
    result["balance"] = balance.get("data", {})

    # Step 3: Recent payments
    payments = await check_payments({"account_id": account_id, "limit": 5})
    result["recent_payments"] = payments.get("data", {})

    hbar = balance.get("data", {}).get("hbar", 0)
    result["status"] = "ACTIVE"
    result["message"] = "Payment system ONLINE. Account %s | %.4f HBAR" % (account_id, hbar)

    return {"success": True, "data": result, "message": result["message"]}


# ── Skill Registration ───────────────────────────────────────

TOOLS = [
    {
        "name": "payment_monitor_resolve",
        "description": "Resolve Wave EVM address to Hedera account ID. Check if wallet is active on-chain.",
        "handler": resolve_account,
        "parameters": {
            "type": "object",
            "properties": {
                "evm_address": {
                    "type": "string",
                    "description": "EVM address to check. Defaults to Wave wallet.",
                },
            },
        },
    },
    {
        "name": "check_payments",
        "description": "Check for incoming HBAR payments to Wave wallet. Scans Hedera mirror node. Free public API, no auth.",
        "handler": check_payments,
        "parameters": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Hedera account ID (0.0.XXXXX). Auto-resolves from EVM address if empty.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max transactions to scan. Default 25.",
                },
            },
        },
    },
    {
        "name": "check_wave_balance",
        "description": "Check current HBAR balance of Wave wallet.",
        "handler": check_balance,
        "parameters": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Hedera account ID. Auto-resolves from EVM address if empty.",
                },
            },
        },
    },
    {
        "name": "payment_status",
        "description": "Full payment system health check — resolves account, checks balance, lists recent payments. One command to see everything.",
        "handler": payment_status,
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
]
