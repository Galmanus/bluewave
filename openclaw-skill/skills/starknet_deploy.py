"""Starknet Deploy — Wave deploys and manages MIDAS smart contracts.

SECURITY MODEL:
  - TESTNET (Sepolia): Wave can deploy autonomously. No real funds at risk.
  - MAINNET: Requires Manuel's approval via Telegram. Wave prepares everything,
    sends notification, and waits for explicit "deploy midas" confirmation.

This is the bridge between Wave's autonomous cognition and irreversible
on-chain actions. The soul can decide; the code enforces the safety gate.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("openclaw.skills.starknet")

MIDAS_REPO = Path("/tmp/phantom")
CONTRACTS_DIR = MIDAS_REPO / "contracts"
DEPLOY_LOG = Path(__file__).parent.parent / "memory" / "starknet_deploys.jsonl"

# ── Config ────────────────────────────────────────────────────

STARKNET_NETWORK = os.environ.get("STARKNET_NETWORK", "sepolia")
STARKNET_DEPLOYER_ADDRESS = os.environ.get("STARKNET_DEPLOYER_ADDRESS", "")
STARKNET_PRIVATE_KEY = os.environ.get("STARKNET_PRIVATE_KEY", "")
STARKNET_RPC_URL = os.environ.get("STARKNET_RPC_URL", "")

# Mainnet requires Manuel's approval — this flag is set by Telegram confirmation
_MAINNET_APPROVED = False
_MAINNET_APPROVAL_TIMESTAMP = 0.0
_MAINNET_APPROVAL_TIMEOUT = 3600  # 1 hour window after approval

# Manuel's Telegram chat ID for notifications
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_NOTIFY_CHAT_ID", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# MIDAS contract deployment order (dependencies)
DEPLOY_ORDER = [
    {"name": "PhantomMerkle", "package": "merkle", "args": []},
    {"name": "PhantomVerifier", "package": "phantom_verifier", "args": ["0", "{deployer}"]},
    {"name": "ComplianceOracle", "package": "compliance_oracle", "args": ["{deployer}"]},
    {"name": "IntentMatcher", "package": "intent_matcher", "args": ["{pool}", "{deployer}"]},
    {"name": "YieldRouter", "package": "yield_router", "args": ["{deployer}"]},
    {"name": "ShieldedStaking", "package": "shielded_staking", "args": ["{deployer}"]},
    {"name": "MidasPool", "package": "midas_pool", "args": ["{merkle}", "{verifier}", "{compliance}", "{deployer}"]},
]


def _is_configured() -> bool:
    """Check if Starknet deployment is configured."""
    return bool(STARKNET_DEPLOYER_ADDRESS and STARKNET_PRIVATE_KEY)


def _is_testnet() -> bool:
    """Check if targeting testnet (safe for autonomous deploy)."""
    return STARKNET_NETWORK in ("sepolia", "testnet", "goerli")


def _is_mainnet_approved() -> bool:
    """Check if mainnet deployment was recently approved by Manuel."""
    global _MAINNET_APPROVED, _MAINNET_APPROVAL_TIMESTAMP
    if not _MAINNET_APPROVED:
        return False
    if time.time() - _MAINNET_APPROVAL_TIMESTAMP > _MAINNET_APPROVAL_TIMEOUT:
        _MAINNET_APPROVED = False
        logger.info("Mainnet approval expired (>1h). Re-approval required.")
        return False
    return True


def approve_mainnet_deploy():
    """Called when Manuel confirms deployment via Telegram.

    This function is the ONLY way to unlock mainnet deployment.
    Approval expires after 1 hour.
    """
    global _MAINNET_APPROVED, _MAINNET_APPROVAL_TIMESTAMP
    _MAINNET_APPROVED = True
    _MAINNET_APPROVAL_TIMESTAMP = time.time()
    logger.info("MAINNET DEPLOYMENT APPROVED by Manuel (expires in 1h)")


def _log_deploy(contract: str, network: str, address: str, status: str, tx_hash: str = ""):
    """Log deployment attempt."""
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "contract": contract,
        "network": network,
        "address": address,
        "status": status,
        "tx_hash": tx_hash,
        "autonomous": True,
    }
    try:
        with open(DEPLOY_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning("Failed to write deploy log: %s", e)


async def _notify_manuel(message: str):
    """Send notification to Manuel via Telegram."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram not configured — cannot notify Manuel")
        return

    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                "https://api.telegram.org/bot%s/sendMessage" % TELEGRAM_TOKEN,
                json={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": message,
                    "parse_mode": "Markdown",
                },
            )
    except Exception as e:
        logger.warning("Telegram notification failed: %s", e)


# ── Tools ─────────────────────────────────────────────────────

async def starknet_deploy_status(params: Dict[str, Any]) -> Dict:
    """Check the current deployment status of MIDAS contracts."""
    # Check if sncast is available
    sncast_available = False
    try:
        result = subprocess.run(
            ["sncast", "--version"], capture_output=True, text=True, timeout=5
        )
        sncast_available = result.returncode == 0
    except Exception:
        pass

    # Check if scarb (Cairo build tool) is available
    scarb_available = False
    try:
        result = subprocess.run(
            ["scarb", "--version"], capture_output=True, text=True, timeout=5
        )
        scarb_available = result.returncode == 0
    except Exception:
        pass

    # Read deploy history
    deploys = []
    if DEPLOY_LOG.exists():
        try:
            with open(DEPLOY_LOG, "r") as f:
                deploys = [json.loads(line) for line in f.readlines()[-10:]]
        except Exception:
            pass

    # Check contract source files
    contracts_found = []
    if CONTRACTS_DIR.exists():
        for item in CONTRACTS_DIR.iterdir():
            if item.is_dir() and (item / "src").exists():
                contracts_found.append(item.name)

    status = {
        "network": STARKNET_NETWORK,
        "configured": _is_configured(),
        "is_testnet": _is_testnet(),
        "mainnet_approved": _is_mainnet_approved(),
        "sncast_available": sncast_available,
        "scarb_available": scarb_available,
        "midas_repo": str(MIDAS_REPO),
        "repo_exists": MIDAS_REPO.exists(),
        "contracts_found": contracts_found,
        "recent_deploys": deploys,
    }

    lines = ["**MIDAS Deployment Status**\n"]
    lines.append("Network: %s (%s)" % (STARKNET_NETWORK, "TESTNET" if _is_testnet() else "MAINNET"))
    lines.append("Configured: %s" % ("Yes" if _is_configured() else "No — set STARKNET_DEPLOYER_ADDRESS and STARKNET_PRIVATE_KEY"))
    lines.append("sncast: %s" % ("Available" if sncast_available else "Not installed"))
    lines.append("scarb: %s" % ("Available" if scarb_available else "Not installed"))
    lines.append("Repo: %s (%s)" % (MIDAS_REPO, "found" if MIDAS_REPO.exists() else "NOT FOUND"))
    lines.append("Contracts: %s" % (", ".join(contracts_found) if contracts_found else "none found"))

    if _is_testnet():
        lines.append("\nTestnet: **autonomous deploy enabled** (no approval needed)")
    else:
        lines.append("\nMainnet: **requires Manuel's approval** (%s)" % (
            "APPROVED (expires in %dm)" % ((_MAINNET_APPROVAL_TIMEOUT - (time.time() - _MAINNET_APPROVAL_TIMESTAMP)) / 60)
            if _is_mainnet_approved()
            else "NOT APPROVED"
        ))

    if deploys:
        lines.append("\n**Recent Deployments:**")
        for d in deploys[-5:]:
            lines.append("- [%s] %s on %s → %s (%s)" % (
                d.get("timestamp", "?")[:19],
                d.get("contract", "?"),
                d.get("network", "?"),
                d.get("address", "?")[:20] + "...",
                d.get("status", "?"),
            ))

    return {"success": True, "data": status, "message": "\n".join(lines)}


async def starknet_build_contracts(params: Dict[str, Any]) -> Dict:
    """Build MIDAS Cairo contracts using scarb."""
    if not CONTRACTS_DIR.exists():
        return {"success": False, "data": None, "message": "MIDAS contracts directory not found at %s" % CONTRACTS_DIR}

    try:
        result = subprocess.run(
            ["scarb", "build"],
            capture_output=True, text=True, timeout=120,
            cwd=str(CONTRACTS_DIR),
        )

        if result.returncode == 0:
            msg = "**MIDAS Contracts Built Successfully**\n\n```\n%s\n```" % result.stdout[-500:]
            return {"success": True, "data": {"stdout": result.stdout}, "message": msg}
        else:
            msg = "**Build Failed**\n\n```\n%s\n```" % result.stderr[-500:]
            return {"success": False, "data": {"stderr": result.stderr}, "message": msg}

    except FileNotFoundError:
        return {"success": False, "data": None, "message": "scarb not installed. Install Starknet Foundry: curl -L https://raw.githubusercontent.com/foundry-rs/starknet-foundry/master/scripts/install.sh | sh"}
    except subprocess.TimeoutExpired:
        return {"success": False, "data": None, "message": "Build timed out (120s limit)"}
    except Exception as e:
        return {"success": False, "data": None, "message": "Build error: %s" % str(e)}


async def starknet_test_contracts(params: Dict[str, Any]) -> Dict:
    """Run MIDAS Cairo test suite using snforge."""
    if not CONTRACTS_DIR.exists():
        return {"success": False, "data": None, "message": "MIDAS contracts directory not found"}

    try:
        result = subprocess.run(
            ["snforge", "test", "--workspace"],
            capture_output=True, text=True, timeout=180,
            cwd=str(CONTRACTS_DIR),
        )

        passed = result.returncode == 0
        output = result.stdout if passed else result.stderr
        msg = "**MIDAS Test Suite: %s**\n\n```\n%s\n```" % (
            "ALL PASSED" if passed else "FAILURES DETECTED",
            output[-800:],
        )
        return {"success": passed, "data": {"output": output}, "message": msg}

    except FileNotFoundError:
        return {"success": False, "data": None, "message": "snforge not installed. Install Starknet Foundry."}
    except subprocess.TimeoutExpired:
        return {"success": False, "data": None, "message": "Tests timed out (180s limit)"}
    except Exception as e:
        return {"success": False, "data": None, "message": "Test error: %s" % str(e)}


async def starknet_deploy_contracts(params: Dict[str, Any]) -> Dict:
    """Deploy MIDAS contracts to Starknet.

    SECURITY:
      - Testnet (Sepolia): deploys autonomously — no real funds at risk.
      - Mainnet: BLOCKS unless Manuel has approved via Telegram within the last hour.

    Deployment order follows contract dependencies:
    1. PhantomMerkle (no deps)
    2. PhantomVerifier (needs deployer)
    3. ComplianceOracle (needs deployer)
    4. IntentMatcher (needs pool + deployer)
    5. YieldRouter (needs deployer)
    6. ShieldedStaking (needs deployer)
    7. MidasPool (needs merkle + verifier + compliance + deployer)
    """
    network = params.get("network", STARKNET_NETWORK)
    force_testnet = params.get("testnet_only", False)

    if force_testnet:
        network = "sepolia"

    is_testnet = network in ("sepolia", "testnet", "goerli")

    # ── SECURITY GATE: Mainnet requires Manuel's approval ─────
    if not is_testnet:
        if not _is_mainnet_approved():
            # Notify Manuel and wait for approval
            await _notify_manuel(
                "*MIDAS MAINNET DEPLOY REQUEST*\n\n"
                "Wave is ready to deploy MIDAS contracts to Starknet mainnet.\n\n"
                "Contracts: %d (MidasPool, Merkle, Verifier, Compliance, Intent, Yield, Staking)\n"
                "Network: *MAINNET* (real funds)\n"
                "Estimated gas: ~0.05 ETH\n\n"
                "To approve, reply: `deploy midas`\n"
                "Approval expires in 1 hour.\n\n"
                "_Wave will NOT proceed without your explicit confirmation._"
                % len(DEPLOY_ORDER)
            )

            _log_deploy("ALL", network, "", "awaiting_approval")

            return {
                "success": False,
                "data": {"status": "awaiting_approval", "network": network},
                "message": (
                    "**MAINNET DEPLOY BLOCKED — Awaiting Manuel's approval**\n\n"
                    "I've notified Manuel on Telegram. Deployment will proceed only after "
                    "he replies 'deploy midas'. This is a safety gate for irreversible "
                    "on-chain operations.\n\n"
                    "If you're testing, use `testnet_only: true` to deploy on Sepolia."
                ),
            }

    if not _is_configured():
        return {
            "success": False,
            "data": None,
            "message": (
                "Starknet deployment not configured.\n"
                "Required env vars:\n"
                "- STARKNET_DEPLOYER_ADDRESS\n"
                "- STARKNET_PRIVATE_KEY\n"
                "- STARKNET_RPC_URL (optional, defaults to public)"
            ),
        }

    # ── BUILD first ───────────────────────────────────────────
    build_result = await starknet_build_contracts({})
    if not build_result.get("success"):
        return build_result

    # ── DEPLOY in dependency order ────────────────────────────
    addresses = {"deployer": STARKNET_DEPLOYER_ADDRESS}
    results = []

    for contract in DEPLOY_ORDER:
        name = contract["name"]
        package = contract["package"]

        # Resolve argument references
        resolved_args = []
        for arg in contract["args"]:
            if arg.startswith("{") and arg.endswith("}"):
                ref = arg[1:-1]
                resolved = addresses.get(ref, "0x0")
                resolved_args.append(resolved)
            else:
                resolved_args.append(arg)

        args_str = " ".join(resolved_args) if resolved_args else ""

        try:
            cmd = ["sncast", "--network", network, "deploy", "--contract-name", name]
            if args_str:
                cmd.extend(["--constructor-calldata", args_str])

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60,
                cwd=str(CONTRACTS_DIR),
            )

            if result.returncode == 0:
                # Parse contract address from output
                address = "0x0"
                for line in result.stdout.split("\n"):
                    if "contract_address" in line:
                        address = line.split()[-1] if line.split() else "0x0"
                        break

                addresses[package] = address
                # Map common names for cross-references
                name_lower = name.lower()
                if "merkle" in name_lower:
                    addresses["merkle"] = address
                elif "verifier" in name_lower:
                    addresses["verifier"] = address
                elif "compliance" in name_lower:
                    addresses["compliance"] = address
                elif "pool" in name_lower:
                    addresses["pool"] = address

                _log_deploy(name, network, address, "deployed")
                results.append({"contract": name, "address": address, "status": "deployed"})
                logger.info("DEPLOYED: %s → %s on %s", name, address, network)
            else:
                _log_deploy(name, network, "", "failed")
                results.append({"contract": name, "address": "", "status": "failed", "error": result.stderr[-200:]})
                logger.error("DEPLOY FAILED: %s — %s", name, result.stderr[-200:])

        except Exception as e:
            _log_deploy(name, network, "", "error")
            results.append({"contract": name, "address": "", "status": "error", "error": str(e)})

    # ── Report ────────────────────────────────────────────────
    deployed = [r for r in results if r["status"] == "deployed"]
    failed = [r for r in results if r["status"] != "deployed"]

    lines = [
        "**MIDAS Deployment %s**" % ("COMPLETE" if not failed else "PARTIAL"),
        "Network: %s (%s)\n" % (network, "TESTNET" if is_testnet else "MAINNET"),
    ]

    if deployed:
        lines.append("**Deployed (%d/%d):**" % (len(deployed), len(results)))
        for r in deployed:
            lines.append("- %s → `%s`" % (r["contract"], r["address"]))

    if failed:
        lines.append("\n**Failed (%d):**" % len(failed))
        for r in failed:
            lines.append("- %s — %s" % (r["contract"], r.get("error", "unknown")[:100]))

    # Notify Manuel of result
    await _notify_manuel(
        "*MIDAS DEPLOY %s*\n\n"
        "Network: %s\n"
        "Deployed: %d/%d contracts\n%s"
        % (
            "COMPLETE" if not failed else "PARTIAL",
            network,
            len(deployed), len(results),
            "\n".join("- %s: `%s`" % (r["contract"], r["address"][:20]) for r in deployed),
        )
    )

    # Record on Hedera audit trail
    try:
        from skills.hedera_writer import submit_hcs_message
        await submit_hcs_message(
            action="midas_deploy",
            agent="wave",
            tool="starknet_deploy",
            details="network=%s contracts=%d/%d" % (network, len(deployed), len(results)),
        )
    except Exception:
        pass

    return {
        "success": len(failed) == 0,
        "data": {"results": results, "addresses": addresses, "network": network},
        "message": "\n".join(lines),
    }


async def starknet_request_mainnet_approval(params: Dict[str, Any]) -> Dict:
    """Request Manuel's approval for mainnet deployment via Telegram."""
    reason = params.get("reason", "MIDAS contracts ready for mainnet deployment")

    await _notify_manuel(
        "*MIDAS MAINNET DEPLOY REQUEST*\n\n"
        "Wave is requesting permission to deploy MIDAS to Starknet mainnet.\n\n"
        "*Reason:* %s\n\n"
        "Contracts: MidasPool, PhantomMerkle, PhantomVerifier, "
        "ComplianceOracle, IntentMatcher, YieldRouter, ShieldedStaking\n\n"
        "To approve, reply: `deploy midas`\n"
        "Approval is valid for 1 hour.\n\n"
        "_This is an irreversible on-chain action. Wave will not proceed without confirmation._"
        % reason
    )

    return {
        "success": True,
        "data": {"status": "notification_sent"},
        "message": (
            "**Mainnet approval request sent to Manuel via Telegram.**\n\n"
            "Waiting for reply: `deploy midas`\n"
            "Approval window: 1 hour after confirmation.\n\n"
            "In the meantime, you can deploy on testnet with `starknet_deploy_contracts(testnet_only=true)`."
        ),
    }


TOOLS = [
    {
        "name": "starknet_deploy_status",
        "description": "Check MIDAS deployment status — tools available, contracts found, recent deploys, network config, approval status.",
        "handler": starknet_deploy_status,
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "starknet_build_contracts",
        "description": "Build MIDAS Cairo smart contracts using scarb. Must succeed before deployment.",
        "handler": starknet_build_contracts,
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "starknet_test_contracts",
        "description": "Run MIDAS Cairo test suite using snforge. Verifies contract correctness before deployment.",
        "handler": starknet_test_contracts,
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "starknet_deploy_contracts",
        "description": (
            "Deploy MIDAS contracts to Starknet. TESTNET: autonomous (no approval needed). "
            "MAINNET: requires Manuel's approval via Telegram — Wave sends notification and "
            "waits for 'deploy midas' confirmation. Deploys 7 contracts in dependency order."
        ),
        "handler": starknet_deploy_contracts,
        "parameters": {
            "type": "object",
            "properties": {
                "network": {
                    "type": "string",
                    "enum": ["sepolia", "mainnet"],
                    "description": "Target network. Sepolia=testnet (autonomous), mainnet (requires approval).",
                },
                "testnet_only": {
                    "type": "boolean",
                    "default": False,
                    "description": "Force testnet deployment regardless of config.",
                },
            },
        },
    },
    {
        "name": "starknet_request_mainnet_approval",
        "description": "Request Manuel's approval for mainnet deployment via Telegram. Use before attempting mainnet deploy.",
        "handler": starknet_request_mainnet_approval,
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Why mainnet deployment is needed now.",
                },
            },
        },
    },
]
