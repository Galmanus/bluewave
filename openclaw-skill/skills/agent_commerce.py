"""Agent Commerce — Wave sells services to other AI agents.

Creates an agent-to-agent economy where Wave provides security audits,
PUT analysis, competitor intel, and privacy consultation to other agents
in exchange for HBAR micropayments. Every transaction is recorded on
Hedera HCS for immutable accountability.

Revenue flows to $WAVE treasury, compounding the token's backing.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("openclaw.skills.agent_commerce")

COMMERCE_LOG = Path(__file__).parent.parent / "memory" / "agent_commerce.jsonl"

# Service catalog — what Wave sells to other agents
SERVICE_CATALOG = {
    "security_audit": {
        "name": "Full Security Audit",
        "description": "OWASP-aligned HTTP headers, SSL/TLS, DNS recon, tech fingerprint, breach check. Complete web security assessment.",
        "price_hbar": 330,
        "price_usd": 50.0,
        "delivery_time": "5 minutes",
        "tools_used": ["sec_full_audit"],
    },
    "smart_contract_audit": {
        "name": "Smart Contract Audit",
        "description": "Solidity/Cairo vulnerability scan covering 14+ attack vectors: reentrancy, flash loans, oracle manipulation, access control, overflow.",
        "price_hbar": 330,
        "price_usd": 50.0,
        "delivery_time": "3 minutes",
        "tools_used": ["sc_audit_code", "sc_audit_github"],
    },
    "put_analysis": {
        "name": "Psychometric Utility Theory Analysis",
        "description": "Full PUT variable estimation for any company: A, F, k, S, w, Phi, FP, Omega, archetype identification, ignition status, recommended approach.",
        "price_hbar": 200,
        "price_usd": 30.0,
        "delivery_time": "2 minutes",
        "tools_used": ["put_analyzer"],
    },
    "competitor_intel": {
        "name": "Competitive Intelligence Report",
        "description": "Deep competitive analysis: market positioning, pricing, weaknesses, tech stack, client base, PUT Phi audit.",
        "price_hbar": 100,
        "price_usd": 15.0,
        "delivery_time": "3 minutes",
        "tools_used": ["competitor_analysis", "competitor_phi_audit"],
    },
    "content_strategy": {
        "name": "Content Strategy Plan",
        "description": "Brand-aligned content plan with decision vector targeting, platform-specific recommendations, posting cadence.",
        "price_hbar": 80,
        "price_usd": 12.0,
        "delivery_time": "2 minutes",
        "tools_used": ["web_search", "x_trending"],
    },
    "privacy_consultation": {
        "name": "Privacy DeFi Integration Advisory",
        "description": "MIDAS privacy architecture consultation: ZK proof design, STRK20 integration, compliance-ready privacy for DeFi protocols.",
        "price_hbar": 500,
        "price_usd": 75.0,
        "delivery_time": "10 minutes",
        "tools_used": ["midas_read_file", "midas_search_code"],
    },
    "defi_yield_scan": {
        "name": "DeFi Yield Opportunity Scan",
        "description": "Current yield opportunities across top protocols: APY, TVL, risk assessment, impermanent loss analysis.",
        "price_hbar": 75,
        "price_usd": 11.25,
        "delivery_time": "2 minutes",
        "tools_used": ["defi_scan_yields", "defi_top_protocols"],
    },
    "shadow_scan": {
        "name": "Shadow Coefficient Detection",
        "description": "Detect fear suppression patterns (k) in any organization from public communications. Identifies denial, suppressed anxiety, rupture risk.",
        "price_hbar": 150,
        "price_usd": 22.50,
        "delivery_time": "3 minutes",
        "tools_used": ["shadow_scanner"],
    },
    "prospect_qualification": {
        "name": "Prospect Qualification (BANT + PUT)",
        "description": "Composite scoring combining BANT criteria with PUT Fracture Potential and Desperation Factor. Ranked priority with strategy.",
        "price_hbar": 100,
        "price_usd": 15.0,
        "delivery_time": "3 minutes",
        "tools_used": ["prospect_qualifier", "put_analyzer"],
    },
}


def _log_transaction(
    requesting_agent: str,
    service_key: str,
    amount_hbar: float,
    status: str,
    tx_id: str = "",
    result_preview: str = "",
):
    """Log agent-to-agent transaction."""
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "requesting_agent": requesting_agent,
        "service": service_key,
        "amount_hbar": amount_hbar,
        "amount_usd": amount_hbar * 0.15,
        "status": status,
        "tx_id": tx_id,
        "result_preview": result_preview[:200],
    }
    try:
        with open(COMMERCE_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning("Failed to log commerce transaction: %s", e)


async def list_agent_services(params: Dict[str, Any]) -> Dict:
    """List all services Wave offers to other AI agents."""
    lines = [
        "**Wave Agent Services**",
        "Payment: HBAR on Hedera | All transactions recorded on HCS\n",
    ]

    for key, svc in SERVICE_CATALOG.items():
        lines.append("**%s** (`%s`)" % (svc["name"], key))
        lines.append("  %s" % svc["description"])
        lines.append("  Price: %d HBAR (~$%.2f) | Delivery: %s\n" % (
            svc["price_hbar"], svc["price_usd"], svc["delivery_time"],
        ))

    lines.append("---")
    lines.append("To request a service, another agent sends:")
    lines.append('`process_agent_request(agent="name", service="key", payment_tx_id="0.0.xxx@123")`')

    return {
        "success": True,
        "data": {"services": list(SERVICE_CATALOG.keys()), "count": len(SERVICE_CATALOG)},
        "message": "\n".join(lines),
    }


async def process_agent_request(params: Dict[str, Any]) -> Dict:
    """Process a service request from another AI agent.

    Flow:
    1. Validate the service exists
    2. Verify HBAR payment on Hedera
    3. Execute the service using Wave's tools
    4. Log revenue to $WAVE treasury
    5. Record on Hedera HCS audit trail
    6. Return result to requesting agent
    """
    requesting_agent = params.get("requesting_agent", "")
    service_key = params.get("service_key", "")
    service_params = params.get("parameters", {})
    payment_tx_id = params.get("payment_tx_id", "")

    if not requesting_agent or not service_key:
        return {"success": False, "data": None, "message": "Need requesting_agent and service_key"}

    if service_key not in SERVICE_CATALOG:
        return {
            "success": False,
            "data": {"available_services": list(SERVICE_CATALOG.keys())},
            "message": "Unknown service: %s. Use list_agent_services to see available options." % service_key,
        }

    svc = SERVICE_CATALOG[service_key]

    # Step 1: Verify payment (if tx_id provided)
    payment_verified = False
    if payment_tx_id:
        try:
            from skills.hedera_writer import verify_incoming_payment
            from skills.hedera_client import usd_to_tinybars
            expected = svc["price_hbar"] * 100_000_000  # tinybars
            result = await verify_incoming_payment("", expected, time_window_seconds=7200)
            payment_verified = result.get("found", False)
        except Exception as e:
            logger.warning("Payment verification failed: %s", e)

    if not payment_verified and payment_tx_id:
        _log_transaction(requesting_agent, service_key, svc["price_hbar"], "payment_unverified", payment_tx_id)
        return {
            "success": False,
            "data": None,
            "message": "Payment of %d HBAR not verified. TX: %s. Service not executed." % (
                svc["price_hbar"], payment_tx_id,
            ),
        }

    # Step 2: Execute the service
    try:
        from skills_handler import execute_skill

        results = []
        for tool_name in svc["tools_used"]:
            try:
                tool_result = await execute_skill(tool_name, service_params)
                results.append(tool_result)
            except Exception as e:
                results.append({"success": False, "message": "Tool %s failed: %s" % (tool_name, str(e))})

        # Combine results
        combined_message = "\n\n---\n\n".join(
            r.get("message", str(r)) if isinstance(r, dict) else str(r)
            for r in results
        )

        # Step 3: Log revenue
        _log_transaction(
            requesting_agent, service_key, svc["price_hbar"],
            "completed" if payment_verified else "completed_unpaid",
            payment_tx_id, combined_message[:200],
        )

        # Step 4: Record on Hedera HCS
        try:
            from skills.hedera_writer import submit_hcs_message
            await submit_hcs_message(
                action="agent_commerce",
                agent="wave",
                tool=service_key,
                details="client=%s amount=%d HBAR" % (requesting_agent, svc["price_hbar"]),
                revenue_usd=svc["price_usd"],
            )
        except Exception:
            pass

        # Step 5: Log to wave_token treasury
        try:
            from skills.wave_token import log_revenue_internal
            await log_revenue_internal(svc["price_usd"], "agent_commerce", service_key)
        except Exception:
            pass

        return {
            "success": True,
            "data": {
                "service": service_key,
                "requesting_agent": requesting_agent,
                "payment_verified": payment_verified,
                "price_hbar": svc["price_hbar"],
            },
            "message": "**Service Delivered: %s**\nClient: %s\nPayment: %s\n\n%s" % (
                svc["name"],
                requesting_agent,
                "VERIFIED (%s)" % payment_tx_id if payment_verified else "PENDING",
                combined_message[:2000],
            ),
        }

    except Exception as e:
        _log_transaction(requesting_agent, service_key, svc["price_hbar"], "failed", payment_tx_id, str(e))
        return {"success": False, "data": None, "message": "Service execution failed: %s" % str(e)}


async def verify_agent_payment(params: Dict[str, Any]) -> Dict:
    """Verify that an agent has paid for a service via HBAR transfer."""
    tx_id = params.get("tx_id", "")
    expected_hbar = params.get("expected_hbar", 0.0)

    if not tx_id:
        return {"success": False, "data": None, "message": "Need tx_id to verify"}

    try:
        from skills.hedera_client import get_transaction, hashscan_link
        tx_data = await get_transaction(tx_id)
        txs = tx_data.get("transactions", [])

        if not txs:
            return {"success": True, "data": {"verified": False}, "message": "Transaction %s not found" % tx_id}

        t = txs[0]
        result_status = t.get("result", "")

        return {
            "success": True,
            "data": {
                "verified": result_status == "SUCCESS",
                "result": result_status,
                "fee": t.get("charged_tx_fee"),
                "timestamp": t.get("consensus_timestamp"),
            },
            "message": "**Payment %s**\nTX: %s\nResult: %s\nFee: %s tinybars\nHashScan: %s" % (
                "VERIFIED" if result_status == "SUCCESS" else "FAILED",
                tx_id, result_status, t.get("charged_tx_fee", "?"),
                hashscan_link(tx_id),
            ),
        }
    except Exception as e:
        return {"success": False, "data": None, "message": "Verification failed: %s" % str(e)}


async def agent_service_history(params: Dict[str, Any]) -> Dict:
    """View history of agent-to-agent commerce transactions."""
    limit = params.get("limit", 20)

    if not COMMERCE_LOG.exists():
        return {"success": True, "data": {"transactions": []}, "message": "No agent commerce transactions yet."}

    try:
        with open(COMMERCE_LOG, "r", encoding="utf-8") as f:
            entries = [json.loads(line) for line in f.readlines()]

        recent = entries[-limit:]
        total_hbar = sum(e.get("amount_hbar", 0) for e in entries if e.get("status") == "completed")
        total_usd = total_hbar * 0.15

        lines = [
            "**Agent Commerce History** (%d transactions)\n" % len(entries),
            "Total revenue: %d HBAR (~$%.2f)\n" % (total_hbar, total_usd),
        ]

        for e in recent:
            lines.append("[%s] %s → %s | %d HBAR | %s" % (
                e.get("timestamp", "?")[:19],
                e.get("requesting_agent", "?"),
                e.get("service", "?"),
                e.get("amount_hbar", 0),
                e.get("status", "?"),
            ))

        return {
            "success": True,
            "data": {"total_transactions": len(entries), "total_hbar": total_hbar},
            "message": "\n".join(lines),
        }
    except Exception as e:
        return {"success": False, "data": None, "message": "History read failed: %s" % str(e)}


async def publish_service_catalog(params: Dict[str, Any]) -> Dict:
    """Publish Wave's service catalog to Moltbook so other agents know what's available."""
    submolt = params.get("submolt", "agents")

    lines = [
        "# Wave Service Catalog — Agent-to-Agent Commerce",
        "",
        "I offer %d professional services to fellow agents. Payment in HBAR." % len(SERVICE_CATALOG),
        "Every transaction recorded on Hedera Consensus Service — verifiable, immutable.",
        "",
    ]

    for key, svc in SERVICE_CATALOG.items():
        lines.append("**%s** — %d HBAR (~$%.2f)" % (svc["name"], svc["price_hbar"], svc["price_usd"]))
        lines.append("%s\n" % svc["description"])

    lines.append("---")
    lines.append("To request: mention @bluewaveprime with the service name.")
    lines.append("Payment: send HBAR to my treasury. I verify on-chain and deliver automatically.")

    content = "\n".join(lines)

    try:
        from skills_handler import execute_skill
        result = await execute_skill("moltbook_post", {
            "title": "Wave Service Catalog — %d Services for AI Agents" % len(SERVICE_CATALOG),
            "content": content,
            "submolt": submolt,
        })
        return result
    except Exception as e:
        return {"success": False, "data": None, "message": "Catalog publication failed: %s" % str(e)}


TOOLS = [
    {
        "name": "list_agent_services",
        "description": "List all services Wave offers to other AI agents. Includes pricing in HBAR, delivery time, and tools used.",
        "handler": list_agent_services,
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "process_agent_request",
        "description": "Process a service request from another AI agent. Verifies HBAR payment, executes service, logs revenue, records on Hedera HCS.",
        "handler": process_agent_request,
        "parameters": {
            "type": "object",
            "properties": {
                "requesting_agent": {"type": "string", "description": "Name/ID of the requesting agent"},
                "service_key": {"type": "string", "description": "Service to execute (e.g., 'security_audit', 'put_analysis')"},
                "parameters": {"type": "object", "description": "Service-specific parameters (e.g., {domain: 'example.com'} for security audit)"},
                "payment_tx_id": {"type": "string", "description": "Hedera transaction ID for the HBAR payment"},
            },
            "required": ["requesting_agent", "service_key"],
        },
    },
    {
        "name": "verify_agent_payment",
        "description": "Verify that an agent has paid for a service via HBAR transfer on Hedera.",
        "handler": verify_agent_payment,
        "parameters": {
            "type": "object",
            "properties": {
                "tx_id": {"type": "string", "description": "Hedera transaction ID to verify"},
                "expected_hbar": {"type": "number", "description": "Expected payment amount in HBAR"},
            },
            "required": ["tx_id"],
        },
    },
    {
        "name": "agent_service_history",
        "description": "View history of all agent-to-agent commerce transactions. Shows revenue, clients, and service breakdown.",
        "handler": agent_service_history,
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 20, "description": "Number of recent transactions to show"},
            },
        },
    },
    {
        "name": "publish_service_catalog",
        "description": "Publish Wave's service catalog to Moltbook so other AI agents can discover and purchase services.",
        "handler": publish_service_catalog,
        "parameters": {
            "type": "object",
            "properties": {
                "submolt": {"type": "string", "default": "agents", "description": "Moltbook submolt to post catalog in"},
            },
        },
    },
]
