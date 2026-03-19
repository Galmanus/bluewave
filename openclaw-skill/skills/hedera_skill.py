"""Hedera Skill — Wave interacts with the Hedera blockchain.

Tools for checking balances, reading the immutable audit trail,
verifying transactions, and reporting on-chain costs.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from skills.hedera_client import (
    get_account_balance,
    get_topic_messages,
    get_token_info,
    get_transactions,
    get_transaction,
    get_platform_stats,
    is_configured,
    hashscan_link,
    hashscan_account_link,
    hashscan_topic_link,
    tinybars_to_usd,
    HEDERA_OPERATOR_ID,
    HEDERA_HCS_TOPIC_ID,
    HEDERA_TOKEN_ID,
    HEDERA_NETWORK,
)

logger = logging.getLogger("openclaw.skills.hedera")


async def hedera_check_balance(params: Dict[str, Any]) -> Dict:
    """Check HBAR and token balances on Hedera."""
    if not is_configured():
        return {"success": False, "data": None, "message": "Hedera not configured. Set HEDERA_OPERATOR_ID."}

    account_id = params.get("account_id", HEDERA_OPERATOR_ID)

    try:
        balance = await get_account_balance(account_id)
        tokens_str = ""
        for t in balance.get("tokens", []):
            tokens_str += "\n  - Token %s: %s" % (t.get("token_id", "?"), t.get("balance", 0))

        msg = (
            "**Hedera Balance: %s**\n"
            "HBAR: **%.4f** (~$%.2f USD)\n"
            "Network: %s\n"
            "Explorer: %s"
        ) % (
            account_id,
            balance["hbar"],
            tinybars_to_usd(balance["hbar_tinybars"]),
            HEDERA_NETWORK,
            balance["hashscan"],
        )
        if tokens_str:
            msg += "\nTokens:%s" % tokens_str

        return {"success": True, "data": balance, "message": msg}
    except Exception as e:
        return {"success": False, "data": None, "message": "Balance check failed: %s" % str(e)}


async def hedera_audit_trail(params: Dict[str, Any]) -> Dict:
    """Read the immutable audit trail from Hedera Consensus Service."""
    if not HEDERA_HCS_TOPIC_ID:
        return {"success": False, "data": None, "message": "HCS topic not configured. Set HEDERA_HCS_TOPIC_ID."}

    limit = params.get("limit", 10)

    try:
        messages = await get_topic_messages(HEDERA_HCS_TOPIC_ID, limit=limit)

        if not messages:
            return {"success": True, "data": [], "message": "No audit entries yet on HCS topic %s" % HEDERA_HCS_TOPIC_ID}

        lines = [
            "**Immutable Audit Trail** (HCS Topic: %s)" % HEDERA_HCS_TOPIC_ID,
            "Explorer: %s\n" % hashscan_topic_link(HEDERA_HCS_TOPIC_ID),
        ]
        for m in messages:
            payload = m.get("payload", {})
            lines.append("#%s [%s] %s — %s %s" % (
                m.get("sequence", "?"),
                payload.get("ts", m.get("timestamp", "?"))[:19],
                payload.get("action", "?"),
                payload.get("agent", ""),
                payload.get("tool", ""),
            ))

        return {"success": True, "data": messages, "message": "\n".join(lines)}
    except Exception as e:
        return {"success": False, "data": None, "message": "Audit trail read failed: %s" % str(e)}


async def hedera_verify_transaction(params: Dict[str, Any]) -> Dict:
    """Verify a specific Hedera transaction by ID."""
    tx_id = params.get("tx_id", "")
    if not tx_id:
        return {"success": False, "data": None, "message": "Need tx_id"}

    try:
        tx = await get_transaction(tx_id)
        txs = tx.get("transactions", [])

        if not txs:
            return {"success": True, "data": tx, "message": "Transaction %s not found" % tx_id}

        t = txs[0]
        msg = (
            "**Transaction Verified**\n"
            "ID: %s\n"
            "Type: %s\n"
            "Result: %s\n"
            "Fee: %s tinybars\n"
            "Timestamp: %s\n"
            "Explorer: %s"
        ) % (
            tx_id,
            t.get("name", "?"),
            t.get("result", "?"),
            t.get("charged_tx_fee", "?"),
            t.get("consensus_timestamp", "?"),
            hashscan_link(tx_id),
        )
        return {"success": True, "data": t, "message": msg}
    except Exception as e:
        return {"success": False, "data": None, "message": "Transaction lookup failed: %s" % str(e)}


async def hedera_recent_transactions(params: Dict[str, Any]) -> Dict:
    """Get recent Hedera transactions for the platform treasury."""
    if not is_configured():
        return {"success": False, "data": None, "message": "Hedera not configured."}

    account_id = params.get("account_id", HEDERA_OPERATOR_ID)
    limit = params.get("limit", 10)

    try:
        txs = await get_transactions(account_id, limit=limit)

        if not txs:
            return {"success": True, "data": [], "message": "No transactions found for %s" % account_id}

        lines = ["**Recent Transactions: %s**\n" % account_id]
        for t in txs:
            lines.append("- [%s] %s — %s (fee: %s) %s" % (
                t.get("timestamp", "?")[:19],
                t.get("type", "?"),
                t.get("result", "?"),
                t.get("fee", "?"),
                t.get("hashscan", ""),
            ))

        return {"success": True, "data": txs, "message": "\n".join(lines)}
    except Exception as e:
        return {"success": False, "data": None, "message": "Failed: %s" % str(e)}


async def hedera_platform_stats(params: Dict[str, Any]) -> Dict:
    """Get aggregate Hedera statistics for the Bluewave platform."""
    try:
        stats = await get_platform_stats()

        lines = ["**Bluewave on Hedera (%s)**\n" % stats.get("network", "?")]

        if not stats.get("configured"):
            lines.append("Hedera integration not configured yet.")
            return {"success": True, "data": stats, "message": "\n".join(lines)}

        lines.append("Operator: %s" % stats.get("operator", "?"))

        if "treasury_hbar" in stats:
            lines.append("Treasury: %.4f HBAR" % stats["treasury_hbar"])

        if stats.get("hcs_topic"):
            lines.append("Audit Topic: %s" % stats["hcs_topic"])
            if stats.get("last_audit_sequence"):
                lines.append("  Last entry: #%s at %s" % (
                    stats["last_audit_sequence"],
                    str(stats.get("last_audit_time", "?"))[:19],
                ))

        if stats.get("wave_token"):
            lines.append("WAVE Token: %s" % stats["wave_token"])

        lines.append("\nAll data verifiable on HashScan: %s" %
                     hashscan_account_link(stats.get("operator", "")))

        return {"success": True, "data": stats, "message": "\n".join(lines)}
    except Exception as e:
        return {"success": False, "data": None, "message": "Stats failed: %s" % str(e)}


async def hedera_cost_report(params: Dict[str, Any]) -> Dict:
    """Compare on-chain micropayment costs vs traditional billing."""
    ai_actions = params.get("ai_actions", 100)
    price_per_action = params.get("price_per_action", 0.05)

    hedera_tx_cost = 0.0001  # ~$0.0001 per Hedera transaction
    stripe_fee_percent = 0.029  # 2.9% + $0.30 per charge
    stripe_fixed = 0.30

    total_revenue = ai_actions * price_per_action
    hedera_cost = ai_actions * hedera_tx_cost
    stripe_cost = (total_revenue * stripe_fee_percent) + stripe_fixed

    savings = stripe_cost - hedera_cost
    savings_percent = (savings / stripe_cost * 100) if stripe_cost > 0 else 0

    report = {
        "ai_actions": ai_actions,
        "revenue": total_revenue,
        "hedera_cost": hedera_cost,
        "stripe_cost": stripe_cost,
        "savings": savings,
        "savings_percent": savings_percent,
    }

    msg = (
        "**Micropayment Cost Comparison: %d AI actions**\n\n"
        "Revenue: $%.2f (%d actions x $%.2f)\n\n"
        "**Traditional (Stripe):**\n"
        "  Fee: $%.2f (2.9%% + $0.30)\n"
        "  Net: $%.2f\n\n"
        "**Hedera Micropayments:**\n"
        "  Fee: $%.4f (%d txs x $0.0001)\n"
        "  Net: $%.2f\n\n"
        "**Savings with Hedera: $%.2f (%.0f%% less fees)**\n\n"
        "At scale (10,000 actions/month):\n"
        "  Stripe: $%.2f in fees\n"
        "  Hedera: $%.2f in fees\n"
        "  Annual savings: $%.2f"
    ) % (
        ai_actions, total_revenue, ai_actions, price_per_action,
        stripe_cost, total_revenue - stripe_cost,
        hedera_cost, ai_actions, total_revenue - hedera_cost,
        savings, savings_percent,
        10000 * price_per_action * stripe_fee_percent + stripe_fixed,
        10000 * hedera_tx_cost,
        (10000 * price_per_action * stripe_fee_percent + stripe_fixed - 10000 * hedera_tx_cost) * 12,
    )

    return {"success": True, "data": report, "message": msg}


TOOLS = [
    {
        "name": "hedera_check_balance",
        "description": "Check HBAR and WAVE token balance on the Hedera network. Verifiable on HashScan explorer.",
        "handler": hedera_check_balance,
        "parameters": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "Hedera account ID (e.g., 0.0.12345). Defaults to platform treasury."},
            },
        },
    },
    {
        "name": "hedera_audit_trail",
        "description": "Read the immutable audit trail from Hedera Consensus Service. Every AI agent action is recorded on-chain with timestamp and hash.",
        "handler": hedera_audit_trail,
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 10, "description": "Number of entries to retrieve"},
            },
        },
    },
    {
        "name": "hedera_verify_transaction",
        "description": "Verify a specific Hedera transaction by ID. Proves that a micropayment or audit entry happened on-chain.",
        "handler": hedera_verify_transaction,
        "parameters": {
            "type": "object",
            "properties": {
                "tx_id": {"type": "string", "description": "Hedera transaction ID to verify"},
            },
            "required": ["tx_id"],
        },
    },
    {
        "name": "hedera_recent_transactions",
        "description": "Get recent Hedera transactions for the platform. Shows micropayments, token transfers, and audit entries.",
        "handler": hedera_recent_transactions,
        "parameters": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "Account to check. Defaults to treasury."},
                "limit": {"type": "integer", "default": 10},
            },
        },
    },
    {
        "name": "hedera_platform_stats",
        "description": "Get aggregate Hedera statistics for Bluewave — treasury balance, audit trail status, token info. Full platform health on-chain.",
        "handler": hedera_platform_stats,
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "hedera_cost_report",
        "description": "Compare Hedera micropayment costs vs traditional payment processors (Stripe). Shows why blockchain micropayments save 99%+ on per-action fees.",
        "handler": hedera_cost_report,
        "parameters": {
            "type": "object",
            "properties": {
                "ai_actions": {"type": "integer", "default": 100, "description": "Number of AI actions to calculate for"},
                "price_per_action": {"type": "number", "default": 0.05, "description": "Price charged per AI action in USD"},
            },
        },
    },
]
