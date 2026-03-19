"""Hedera Client — REST API integration for micropayments, audit, and tokens.

Uses Hedera Mirror Node REST API for reads and JSON-RPC relay for writes.
No SDK dependency — pure httpx. Works on Python 3.8+.

Hedera Services Used:
  - HBAR transfers (micropayments for AI actions)
  - HCS (Hedera Consensus Service) for immutable audit trail
  - HTS (Hedera Token Service) for WAVE utility token
  - Mirror Node API for querying on-chain state
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("openclaw.hedera")

# ── Config ────────────────────────────────────────────────────

HEDERA_NETWORK = os.environ.get("HEDERA_NETWORK", "testnet")
HEDERA_OPERATOR_ID = os.environ.get("HEDERA_OPERATOR_ID", "")
HEDERA_OPERATOR_KEY = os.environ.get("HEDERA_OPERATOR_KEY", "")
HEDERA_HCS_TOPIC_ID = os.environ.get("HEDERA_HCS_TOPIC_ID", "")
HEDERA_TOKEN_ID = os.environ.get("HEDERA_TOKEN_ID", "")

MIRROR_URLS = {
    "testnet": "https://testnet.mirrornode.hedera.com/api/v1",
    "mainnet": "https://mainnet.mirrornode.hedera.com/api/v1",
}
HASHSCAN_URLS = {
    "testnet": "https://hashscan.io/testnet",
    "mainnet": "https://hashscan.io/mainnet",
}

MIRROR_URL = MIRROR_URLS.get(HEDERA_NETWORK, MIRROR_URLS["testnet"])
HASHSCAN_URL = HASHSCAN_URLS.get(HEDERA_NETWORK, HASHSCAN_URLS["testnet"])
TIMEOUT = httpx.Timeout(15.0, connect=10.0)


def is_configured() -> bool:
    """Check if Hedera is configured."""
    return bool(HEDERA_OPERATOR_ID)


def hashscan_link(tx_id: str) -> str:
    """Generate a HashScan explorer link for a transaction."""
    return "%s/transaction/%s" % (HASHSCAN_URL, tx_id)


def hashscan_account_link(account_id: str) -> str:
    return "%s/account/%s" % (HASHSCAN_URL, account_id)


def hashscan_topic_link(topic_id: str) -> str:
    return "%s/topic/%s" % (HASHSCAN_URL, topic_id)


# ── Mirror Node Queries (READ — no signing needed) ───────────

async def get_account_balance(account_id: str) -> Dict:
    """Get HBAR balance and token balances for an account."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get("%s/balances?account.id=%s" % (MIRROR_URL, account_id))
        resp.raise_for_status()
        data = resp.json()

    balances = data.get("balances", [])
    if not balances:
        return {"account": account_id, "hbar": 0, "tokens": []}

    b = balances[0]
    hbar_tinybars = b.get("balance", 0)
    tokens = b.get("tokens", [])

    return {
        "account": account_id,
        "hbar_tinybars": hbar_tinybars,
        "hbar": hbar_tinybars / 100_000_000,
        "tokens": tokens,
        "hashscan": hashscan_account_link(account_id),
    }


async def get_topic_messages(topic_id: str, limit: int = 10) -> List[Dict]:
    """Get recent messages from an HCS topic (audit trail)."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            "%s/topics/%s/messages?limit=%d&order=desc" % (MIRROR_URL, topic_id, limit)
        )
        resp.raise_for_status()
        data = resp.json()

    messages = []
    for msg in data.get("messages", []):
        import base64
        try:
            decoded = base64.b64decode(msg.get("message", "")).decode("utf-8")
            payload = json.loads(decoded)
        except Exception:
            payload = {"raw": msg.get("message", "")}

        messages.append({
            "sequence": msg.get("sequence_number"),
            "timestamp": msg.get("consensus_timestamp"),
            "payload": payload,
        })

    return messages


async def get_token_info(token_id: str) -> Dict:
    """Get HTS token metadata."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get("%s/tokens/%s" % (MIRROR_URL, token_id))
        resp.raise_for_status()
        return resp.json()


async def get_transactions(account_id: str, limit: int = 10) -> List[Dict]:
    """Get recent transactions for an account."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            "%s/transactions?account.id=%s&limit=%d&order=desc" % (MIRROR_URL, account_id, limit)
        )
        resp.raise_for_status()
        data = resp.json()

    txs = []
    for tx in data.get("transactions", []):
        txs.append({
            "tx_id": tx.get("transaction_id"),
            "type": tx.get("name"),
            "result": tx.get("result"),
            "timestamp": tx.get("consensus_timestamp"),
            "fee": tx.get("charged_tx_fee"),
            "hashscan": hashscan_link(tx.get("transaction_id", "")),
        })
    return txs


async def get_transaction(tx_id: str) -> Dict:
    """Look up a specific transaction."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get("%s/transactions/%s" % (MIRROR_URL, tx_id))
        resp.raise_for_status()
        return resp.json()


# ── Audit Trail (HCS) ────────────────────────────────────────

def build_audit_message(action: str, agent: str, tool: str = "",
                        details: str = "", tenant_id: str = "") -> bytes:
    """Build an HCS audit message payload."""
    payload = {
        "v": 1,
        "platform": "bluewave",
        "action": action,
        "agent": agent,
        "tool": tool,
        "tenant": tenant_id[:8] if tenant_id else "",
        "ts": datetime.utcnow().isoformat() + "Z",
        "hash": hashlib.sha256(details.encode()).hexdigest()[:16] if details else "",
    }
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


# ── Cost Calculations ────────────────────────────────────────

def usd_to_tinybars(usd_amount: float, hbar_price_usd: float = 0.15) -> int:
    """Convert USD to tinybars. 1 HBAR = 100,000,000 tinybars."""
    hbar_amount = usd_amount / hbar_price_usd
    return int(hbar_amount * 100_000_000)


def tinybars_to_usd(tinybars: int, hbar_price_usd: float = 0.15) -> float:
    """Convert tinybars to USD."""
    hbar = tinybars / 100_000_000
    return hbar * hbar_price_usd


# ── Statistics ────────────────────────────────────────────────

async def get_platform_stats() -> Dict:
    """Get aggregate Hedera stats for the platform."""
    stats = {
        "network": HEDERA_NETWORK,
        "operator": HEDERA_OPERATOR_ID,
        "hcs_topic": HEDERA_HCS_TOPIC_ID,
        "wave_token": HEDERA_TOKEN_ID,
        "configured": is_configured(),
    }

    if not is_configured():
        return stats

    try:
        balance = await get_account_balance(HEDERA_OPERATOR_ID)
        stats["treasury_hbar"] = balance["hbar"]
        stats["treasury_tokens"] = balance["tokens"]
    except Exception as e:
        stats["balance_error"] = str(e)

    if HEDERA_HCS_TOPIC_ID:
        try:
            messages = await get_topic_messages(HEDERA_HCS_TOPIC_ID, limit=1)
            if messages:
                stats["last_audit_sequence"] = messages[0].get("sequence")
                stats["last_audit_time"] = messages[0].get("timestamp")
        except Exception:
            pass

    return stats
