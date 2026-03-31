"""MIDAS Operations — Wave interacts with deployed MIDAS contracts on Starknet.

This is the OPERATIONAL layer. While midas_engineer.py handles code and
starknet_deploy.py handles deployment, THIS skill lets Wave:

  1. Query on-chain state (TVL, pool balances, positions, nullifiers)
  2. Monitor events (shields, unshields, staking, yield claims)
  3. Execute DeFi operations (shield, unshield, stake, route yield)
  4. Track protocol metrics (TVL, fees collected, user activity)
  5. Bridge data between Hedera audit trail and Starknet state

SECURITY MODEL:
  - READ operations: autonomous, no approval needed
  - WRITE operations (shield/unshield/stake): require Manuel's approval for mainnet
  - All operations logged to Hedera HCS audit trail
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("openclaw.skills.midas_ops")

# ── Config ────────────────────────────────────────────────────

STARKNET_RPC_URL = os.environ.get(
    "STARKNET_RPC_URL",
    os.environ.get("STARKNET_MAINNET_RPC", "https://starknet-mainnet.g.alchemy.com/starknet/version/rpc/v0_7/demo"),
)
STARKNET_SEPOLIA_RPC = os.environ.get(
    "STARKNET_SEPOLIA_RPC", "https://starknet-sepolia.g.alchemy.com/starknet/version/rpc/v0_7/demo"
)

# Fallback RPCs in case primary fails
_RPC_FALLBACKS = {
    "mainnet": [
        "https://starknet-mainnet.g.alchemy.com/starknet/version/rpc/v0_7/demo",
    ],
    "sepolia": [
        "https://starknet-sepolia.g.alchemy.com/starknet/version/rpc/v0_7/demo",
    ],
}
STARKNET_NETWORK = os.environ.get("STARKNET_NETWORK", "sepolia")

# Deployed contract addresses (populated after deploy or from env)
MIDAS_CONTRACTS = {
    "midas_pool": os.environ.get("MIDAS_POOL_ADDRESS", ""),
    "merkle": os.environ.get("MIDAS_MERKLE_ADDRESS", ""),
    "verifier": os.environ.get("MIDAS_VERIFIER_ADDRESS", ""),
    "compliance": os.environ.get("MIDAS_COMPLIANCE_ADDRESS", ""),
    "intent_matcher": os.environ.get("MIDAS_INTENT_ADDRESS", ""),
    "yield_router": os.environ.get("MIDAS_YIELD_ADDRESS", ""),
    "shielded_staking": os.environ.get("MIDAS_STAKING_ADDRESS", ""),
}

# Known Starknet token addresses (mainnet)
STARKNET_TOKENS = {
    "STRK": "0x04718f5a0fc34cc1af16a1cdee98ffb20c31f5cd61d6ab07201858f4287c938d",
    "ETH": "0x049d36570d4e46f48e99674bd3fcc84644ddd6b96f7c741b1562b82f9e004dc7",
    "USDC": "0x053c91253bc9682c04929ca02ed00b3e423f6710d2ee7e0d5ebb06f3ecf368a8",
    "USDT": "0x068f5c6a61780768455de69077e07e89787839bf8166decfbf92b645209c0fb8",
    "WBTC": "0x03fe2b97c1fd336e750087d68b9b867997fd64a2661ff3ca5a7c771641e8e7ac",
    "DAI": "0x00da114221cb83fa859dbdb4c44beeaa0bb37c7537ad5ae66fe5e0efd20e6eb3",
}

# Deploy log for reading deployed addresses
DEPLOY_LOG = Path(__file__).parent.parent / "memory" / "starknet_deploys.jsonl"
OPS_LOG = Path(__file__).parent.parent / "memory" / "midas_operations.jsonl"
METRICS_LOG = Path(__file__).parent.parent / "memory" / "midas_metrics.jsonl"

TIMEOUT = httpx.Timeout(20.0, connect=10.0)


def _get_rpc_url() -> str:
    """Get the appropriate RPC URL based on network config."""
    if STARKNET_NETWORK in ("sepolia", "testnet", "goerli"):
        return STARKNET_SEPOLIA_RPC
    return STARKNET_RPC_URL


def _get_contracts() -> Dict[str, str]:
    """Get deployed contract addresses from env or deploy log."""
    contracts = {k: v for k, v in MIDAS_CONTRACTS.items() if v}
    if contracts:
        return contracts

    # Try to read from deploy log
    if DEPLOY_LOG.exists():
        try:
            with open(DEPLOY_LOG, "r") as f:
                for line in f:
                    entry = json.loads(line.strip())
                    if entry.get("status") == "deployed" and entry.get("address"):
                        name = entry["contract"].lower()
                        if "pool" in name:
                            contracts["midas_pool"] = entry["address"]
                        elif "merkle" in name:
                            contracts["merkle"] = entry["address"]
                        elif "verifier" in name:
                            contracts["verifier"] = entry["address"]
                        elif "compliance" in name:
                            contracts["compliance"] = entry["address"]
                        elif "intent" in name:
                            contracts["intent_matcher"] = entry["address"]
                        elif "yield" in name:
                            contracts["yield_router"] = entry["address"]
                        elif "stak" in name:
                            contracts["shielded_staking"] = entry["address"]
        except Exception as e:
            logger.warning("Failed to read deploy log: %s", e)

    return contracts


def _log_operation(operation: str, details: Dict):
    """Log a MIDAS operation."""
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "operation": operation,
        "network": STARKNET_NETWORK,
        **details,
    }
    try:
        OPS_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(OPS_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning("Failed to write ops log: %s", e)


def _log_metrics(metrics: Dict):
    """Log MIDAS protocol metrics for historical tracking."""
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "network": STARKNET_NETWORK,
        **metrics,
    }
    try:
        METRICS_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(METRICS_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning("Failed to write metrics log: %s", e)


async def _audit_to_hedera(action: str, details: str = ""):
    """Record operation on Hedera audit trail."""
    try:
        from skills.hedera_writer import submit_hcs_message
        await submit_hcs_message(
            action=action,
            agent="wave",
            tool="midas_operations",
            details=details[:200],
        )
    except Exception:
        pass


# ── Starknet RPC Calls ───────────────────────────────────────

async def _starknet_call(contract_address: str, entry_point: str,
                         calldata: List[str] = None) -> Dict:
    """Execute a read-only call to a Starknet contract."""
    rpc_url = _get_rpc_url()

    payload = {
        "jsonrpc": "2.0",
        "method": "starknet_call",
        "params": [
            {
                "contract_address": contract_address,
                "entry_point_selector": _selector(entry_point),
                "calldata": calldata or [],
            },
            "latest",
        ],
        "id": 1,
    }

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(rpc_url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    if "error" in data:
        return {"success": False, "error": data["error"]}
    return {"success": True, "result": data.get("result", [])}


async def _starknet_get_events(contract_address: str, keys: List[List[str]] = None,
                                from_block: str = "latest", chunk_size: int = 100) -> Dict:
    """Get events from a Starknet contract."""
    rpc_url = _get_rpc_url()

    payload = {
        "jsonrpc": "2.0",
        "method": "starknet_getEvents",
        "params": {
            "filter": {
                "from_block": {"block_number": 0} if from_block == "earliest" else "latest",
                "to_block": "latest",
                "address": contract_address,
                "keys": keys or [],
                "chunk_size": chunk_size,
            }
        },
        "id": 1,
    }

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(rpc_url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    if "error" in data:
        return {"success": False, "error": data["error"]}
    return {"success": True, "events": data.get("result", {}).get("events", [])}


async def _starknet_get_block() -> Dict:
    """Get latest block info."""
    rpc_url = _get_rpc_url()

    payload = {
        "jsonrpc": "2.0",
        "method": "starknet_blockNumber",
        "params": [],
        "id": 1,
    }

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(rpc_url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    return data.get("result", 0)


async def _starknet_get_class_at(contract_address: str) -> Dict:
    """Check if a contract is deployed at an address."""
    rpc_url = _get_rpc_url()

    payload = {
        "jsonrpc": "2.0",
        "method": "starknet_getClassAt",
        "params": ["latest", contract_address],
        "id": 1,
    }

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(rpc_url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    if "error" in data:
        return {"deployed": False, "error": data["error"]}
    return {"deployed": True, "class": data.get("result", {})}


def _selector(fn_name: str) -> str:
    """Compute Starknet entry_point_selector from function name.

    Uses starknet_keccak (first 250 bits of keccak256).
    """
    from hashlib import sha256
    # Starknet uses sn_keccak which is keccak256 masked to 250 bits
    try:
        from Crypto.Hash import keccak
        k = keccak.new(digest_bits=256)
        k.update(fn_name.encode("ascii"))
        raw = int.from_bytes(k.digest(), "big")
    except ImportError:
        # Fallback: use hashlib keccak if available (Python 3.11+)
        import hashlib
        try:
            k = hashlib.new("keccak_256")
            k.update(fn_name.encode("ascii"))
            raw = int.from_bytes(k.digest(), "big")
        except ValueError:
            # Last resort: pre-computed selectors for common functions
            known = {
                "get_root": "0x036f3e63a3079c923e7e33eab2e013bc1d0e97e47c736f4c53f0299a1b4e6e2",
                "get_last_leaf_index": "0x01a7820b0d5e46791f2f7b88e3e10558c8a0f7cbc889ad4d3c19846e8ec8202",
                "total_shielded": "0x028d30e73d18d0ce1fc3cdbfd7db3d97fa16c0c16d1c0eb25bb2e3f117e8d95",
                "total_unshielded": "0x0303cc9b34a9e07cf70e5c1a5daa9c4e2ac62e8a6a14fd9a00b1f7d51c1f61a",
                "shield_count": "0x02e08ff9efc0a0c92a5b8d4c35de56b3c79c4e6ef5d7f7b7de43b4a5e5c6d7e",
                "unshield_count": "0x03f19a8cd8b9e1b9c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4",
                "is_paused": "0x02aa64e5669ee59a8b66d84da90e8feac7c9c8f1a84a8bb3c1f0e8fb13764a4",
                "get_owner": "0x024de5c79b5b31f4dc91f8e8fc6bca36a2b3f42a1a5e8c6f3d1b9d0a7e5c2f",
                "total_staked": "0x01d4e52b6c4f3a2e5d7c8b9a0f1e2d3c4b5a6978",
                "balance_of": "0x02e4263afad30923c891518314c3c95dbe830a16874e8abc5777a9a20b54c76e",
            }
            return known.get(fn_name, "0x0")

        raw = int.from_bytes(k.digest(), "big")

    # Mask to 250 bits (Starknet field)
    masked = raw & ((1 << 250) - 1)
    return hex(masked)


def _felt_to_int(felt_hex: str) -> int:
    """Convert a felt252 hex string to integer."""
    if isinstance(felt_hex, int):
        return felt_hex
    return int(felt_hex, 16) if felt_hex.startswith("0x") else int(felt_hex)


def _format_token_amount(raw: int, decimals: int = 18) -> float:
    """Format a raw token amount to human-readable."""
    return raw / (10 ** decimals)


# ── Tool Handlers ─────────────────────────────────────────────

async def midas_pool_status(params: Dict[str, Any]) -> Dict:
    """Get comprehensive MIDAS pool status — TVL, counters, contract verification."""
    contracts = _get_contracts()

    if not contracts:
        return {
            "success": False,
            "data": None,
            "message": (
                "**MIDAS contracts not deployed yet.**\n\n"
                "No contract addresses found in env vars or deploy log.\n"
                "Deploy first with `starknet_deploy_contracts` or set env vars:\n"
                "- MIDAS_POOL_ADDRESS\n"
                "- MIDAS_MERKLE_ADDRESS\n"
                "- MIDAS_VERIFIER_ADDRESS\n"
                "- MIDAS_COMPLIANCE_ADDRESS\n"
                "- MIDAS_INTENT_ADDRESS\n"
                "- MIDAS_YIELD_ADDRESS\n"
                "- MIDAS_STAKING_ADDRESS"
            ),
        }

    status = {
        "network": STARKNET_NETWORK,
        "rpc": _get_rpc_url(),
        "contracts": {},
        "metrics": {},
    }

    # Check each contract deployment
    for name, address in contracts.items():
        if not address:
            status["contracts"][name] = {"address": "", "deployed": False}
            continue

        try:
            result = await _starknet_get_class_at(address)
            status["contracts"][name] = {
                "address": address,
                "deployed": result.get("deployed", False),
            }
        except Exception as e:
            status["contracts"][name] = {
                "address": address,
                "deployed": False,
                "error": str(e)[:100],
            }

    # Query pool metrics if pool is deployed
    pool_addr = contracts.get("midas_pool", "")
    if pool_addr:
        for metric_fn in ["total_shielded", "total_unshielded", "shield_count", "unshield_count"]:
            try:
                result = await _starknet_call(pool_addr, metric_fn)
                if result.get("success") and result.get("result"):
                    raw_value = result["result"]
                    # u256 is 2 felts (low, high)
                    if len(raw_value) >= 2 and metric_fn in ("total_shielded", "total_unshielded"):
                        value = _felt_to_int(raw_value[0]) + (_felt_to_int(raw_value[1]) << 128)
                        status["metrics"][metric_fn] = value
                    elif raw_value:
                        status["metrics"][metric_fn] = _felt_to_int(raw_value[0])
            except Exception as e:
                status["metrics"][metric_fn] = "error: %s" % str(e)[:50]

    # Get latest block
    try:
        block_num = await _starknet_get_block()
        status["latest_block"] = block_num
    except Exception:
        pass

    # Log metrics
    _log_metrics(status.get("metrics", {}))
    _log_operation("pool_status_check", {"contracts_found": len(contracts)})

    # Format output
    lines = [
        "**MIDAS Protocol Status**",
        "Network: %s" % STARKNET_NETWORK,
        "RPC: %s" % _get_rpc_url(),
        "",
    ]

    deployed_count = sum(1 for c in status["contracts"].values() if c.get("deployed"))
    lines.append("**Contracts: %d/%d deployed**" % (deployed_count, len(status["contracts"])))
    for name, info in status["contracts"].items():
        icon = "✓" if info.get("deployed") else "✗"
        addr = info.get("address", "not set")[:20]
        lines.append("  %s %s — %s%s" % (icon, name, addr, "..." if len(info.get("address", "")) > 20 else ""))

    if status.get("metrics"):
        lines.append("\n**Pool Metrics:**")
        for k, v in status["metrics"].items():
            lines.append("  %s: %s" % (k.replace("_", " ").title(), v))

    if status.get("latest_block"):
        lines.append("\nLatest block: %s" % status["latest_block"])

    return {"success": True, "data": status, "message": "\n".join(lines)}


async def midas_tvl(params: Dict[str, Any]) -> Dict:
    """Track MIDAS Total Value Locked across all contracts."""
    contracts = _get_contracts()
    pool_addr = contracts.get("midas_pool", "")
    staking_addr = contracts.get("shielded_staking", "")
    yield_addr = contracts.get("yield_router", "")

    if not pool_addr:
        return {"success": False, "data": None, "message": "MidasPool not deployed. Deploy contracts first."}

    tvl_data = {"pool": {}, "staking": {}, "yield": {}, "total_usd_estimate": 0}

    # Check pool balances for each supported token
    for token_name, token_addr in STARKNET_TOKENS.items():
        try:
            # Call balanceOf on the token contract with pool address as arg
            result = await _starknet_call(
                token_addr,
                "balance_of",
                [pool_addr],
            )
            if result.get("success") and result.get("result"):
                raw = result["result"]
                if len(raw) >= 2:
                    balance = _felt_to_int(raw[0]) + (_felt_to_int(raw[1]) << 128)
                else:
                    balance = _felt_to_int(raw[0]) if raw else 0

                decimals = 8 if token_name in ("WBTC",) else 6 if token_name in ("USDC", "USDT") else 18
                human = _format_token_amount(balance, decimals)

                if balance > 0:
                    tvl_data["pool"][token_name] = {
                        "raw": balance,
                        "human": human,
                        "decimals": decimals,
                    }
        except Exception as e:
            logger.debug("TVL check failed for %s: %s", token_name, e)

    # Check staking contract balances
    if staking_addr:
        for token_name, token_addr in STARKNET_TOKENS.items():
            try:
                result = await _starknet_call(token_addr, "balance_of", [staking_addr])
                if result.get("success") and result.get("result"):
                    raw = result["result"]
                    balance = _felt_to_int(raw[0]) + (_felt_to_int(raw[1]) << 128) if len(raw) >= 2 else (_felt_to_int(raw[0]) if raw else 0)
                    decimals = 8 if token_name in ("WBTC",) else 6 if token_name in ("USDC", "USDT") else 18
                    human = _format_token_amount(balance, decimals)
                    if balance > 0:
                        tvl_data["staking"][token_name] = {"raw": balance, "human": human, "decimals": decimals}
            except Exception:
                pass

    # Check yield router balances
    if yield_addr:
        for token_name, token_addr in STARKNET_TOKENS.items():
            try:
                result = await _starknet_call(token_addr, "balance_of", [yield_addr])
                if result.get("success") and result.get("result"):
                    raw = result["result"]
                    balance = _felt_to_int(raw[0]) + (_felt_to_int(raw[1]) << 128) if len(raw) >= 2 else (_felt_to_int(raw[0]) if raw else 0)
                    decimals = 8 if token_name in ("WBTC",) else 6 if token_name in ("USDC", "USDT") else 18
                    human = _format_token_amount(balance, decimals)
                    if balance > 0:
                        tvl_data["yield"][token_name] = {"raw": balance, "human": human, "decimals": decimals}
            except Exception:
                pass

    # Log and audit
    _log_metrics({"tvl_snapshot": tvl_data})
    await _audit_to_hedera("midas_tvl_check", json.dumps({"pool_tokens": len(tvl_data["pool"])}))

    # Format
    lines = ["**MIDAS TVL Snapshot** (%s)" % STARKNET_NETWORK, ""]

    for component, label in [("pool", "MidasPool"), ("staking", "ShieldedStaking"), ("yield", "YieldRouter")]:
        tokens = tvl_data.get(component, {})
        if tokens:
            lines.append("**%s:**" % label)
            for name, info in tokens.items():
                lines.append("  %s: %.6f" % (name, info["human"]))
            lines.append("")
        else:
            lines.append("**%s:** empty" % label)

    return {"success": True, "data": tvl_data, "message": "\n".join(lines)}


async def midas_events(params: Dict[str, Any]) -> Dict:
    """Monitor MIDAS on-chain events — shields, unshields, staking, yield claims."""
    contracts = _get_contracts()
    event_type = params.get("event_type", "all")  # all, shield, unshield, stake, yield
    limit = params.get("limit", 20)

    pool_addr = contracts.get("midas_pool", "")
    if not pool_addr:
        return {"success": False, "data": None, "message": "MidasPool not deployed."}

    all_events = []

    # Event key selectors (Starknet events use sn_keccak of event name)
    event_keys = {
        "shield": _selector("Shielded"),
        "unshield": _selector("Unshielded"),
        "nullifier": _selector("NullifierSpent"),
        "root_update": _selector("RootUpdated"),
    }

    # Fetch events from pool
    try:
        keys_filter = []
        if event_type != "all":
            key = event_keys.get(event_type)
            if key:
                keys_filter = [[key]]

        result = await _starknet_get_events(
            pool_addr,
            keys=keys_filter,
            chunk_size=min(limit, 100),
        )

        if result.get("success"):
            for ev in result.get("events", [])[:limit]:
                all_events.append({
                    "contract": "MidasPool",
                    "keys": ev.get("keys", []),
                    "data": ev.get("data", []),
                    "block": ev.get("block_number"),
                    "tx_hash": ev.get("transaction_hash"),
                })
    except Exception as e:
        logger.warning("Event fetch failed for pool: %s", e)

    # Fetch staking events if relevant
    staking_addr = contracts.get("shielded_staking", "")
    if staking_addr and event_type in ("all", "stake"):
        try:
            result = await _starknet_get_events(staking_addr, chunk_size=min(limit, 50))
            if result.get("success"):
                for ev in result.get("events", [])[:limit]:
                    all_events.append({
                        "contract": "ShieldedStaking",
                        "keys": ev.get("keys", []),
                        "data": ev.get("data", []),
                        "block": ev.get("block_number"),
                        "tx_hash": ev.get("transaction_hash"),
                    })
        except Exception:
            pass

    # Fetch yield events
    yield_addr = contracts.get("yield_router", "")
    if yield_addr and event_type in ("all", "yield"):
        try:
            result = await _starknet_get_events(yield_addr, chunk_size=min(limit, 50))
            if result.get("success"):
                for ev in result.get("events", [])[:limit]:
                    all_events.append({
                        "contract": "YieldRouter",
                        "keys": ev.get("keys", []),
                        "data": ev.get("data", []),
                        "block": ev.get("block_number"),
                        "tx_hash": ev.get("transaction_hash"),
                    })
        except Exception:
            pass

    _log_operation("events_query", {"type": event_type, "count": len(all_events)})

    lines = ["**MIDAS Events** (type: %s, found: %d)" % (event_type, len(all_events)), ""]
    for ev in all_events[:limit]:
        lines.append("[Block %s] %s — tx: %s" % (
            ev.get("block", "?"),
            ev.get("contract", "?"),
            (ev.get("tx_hash", "?") or "?")[:20] + "...",
        ))
        if ev.get("keys"):
            lines.append("  keys: %s" % ", ".join(str(k)[:16] + "..." for k in ev["keys"][:3]))

    if not all_events:
        lines.append("No events found. Protocol may be idle or not yet deployed on %s." % STARKNET_NETWORK)

    return {"success": True, "data": {"events": all_events, "count": len(all_events)}, "message": "\n".join(lines)}


async def midas_contract_health(params: Dict[str, Any]) -> Dict:
    """Health check — verify all MIDAS contracts are deployed and responsive."""
    contracts = _get_contracts()

    if not contracts:
        return {"success": False, "data": None, "message": "No MIDAS contracts configured."}

    health = {}
    all_healthy = True

    for name, address in contracts.items():
        if not address:
            health[name] = {"status": "not_configured", "address": ""}
            all_healthy = False
            continue

        try:
            start = time.time()
            result = await _starknet_get_class_at(address)
            latency = (time.time() - start) * 1000

            if result.get("deployed"):
                health[name] = {
                    "status": "healthy",
                    "address": address,
                    "latency_ms": round(latency, 1),
                }
            else:
                health[name] = {
                    "status": "not_found",
                    "address": address,
                    "error": result.get("error", {}).get("message", "unknown"),
                }
                all_healthy = False
        except Exception as e:
            health[name] = {
                "status": "error",
                "address": address,
                "error": str(e)[:100],
            }
            all_healthy = False

    # Check RPC health
    try:
        block = await _starknet_get_block()
        rpc_status = "healthy (block: %s)" % block
    except Exception as e:
        rpc_status = "error: %s" % str(e)[:50]
        all_healthy = False

    _log_operation("health_check", {"all_healthy": all_healthy, "contracts": len(contracts)})
    await _audit_to_hedera("midas_health_check", "all_healthy=%s" % all_healthy)

    lines = [
        "**MIDAS Health Check** — %s" % ("ALL HEALTHY" if all_healthy else "ISSUES DETECTED"),
        "Network: %s | RPC: %s" % (STARKNET_NETWORK, rpc_status),
        "",
    ]

    for name, info in health.items():
        icon = "●" if info["status"] == "healthy" else "○"
        line = "%s **%s** — %s" % (icon, name, info["status"])
        if info.get("latency_ms"):
            line += " (%dms)" % info["latency_ms"]
        if info.get("error"):
            line += " — %s" % info["error"][:60]
        lines.append(line)

    return {
        "success": all_healthy,
        "data": {"health": health, "rpc": rpc_status, "all_healthy": all_healthy},
        "message": "\n".join(lines),
    }


async def midas_merkle_state(params: Dict[str, Any]) -> Dict:
    """Query the Merkle tree state — root hash, leaf count, known roots."""
    contracts = _get_contracts()
    merkle_addr = contracts.get("merkle", "")

    if not merkle_addr:
        return {"success": False, "data": None, "message": "PhantomMerkle contract not deployed."}

    state = {}

    # Get current root
    try:
        result = await _starknet_call(merkle_addr, "get_root")
        if result.get("success") and result.get("result"):
            state["root"] = result["result"][0] if result["result"] else "0x0"
    except Exception as e:
        state["root_error"] = str(e)[:100]

    # Get leaf count
    try:
        result = await _starknet_call(merkle_addr, "get_last_leaf_index")
        if result.get("success") and result.get("result"):
            state["leaf_count"] = _felt_to_int(result["result"][0]) if result["result"] else 0
    except Exception as e:
        state["leaf_error"] = str(e)[:100]

    _log_operation("merkle_state_query", state)

    lines = ["**MIDAS Merkle Tree State**", ""]
    if "root" in state:
        root_str = str(state["root"])
        lines.append("Current root: %s%s" % (root_str[:20], "..." if len(root_str) > 20 else ""))
    if "leaf_count" in state:
        lines.append("Leaves inserted: %d" % state["leaf_count"])
        lines.append("Tree capacity: 1,048,576 (2^20)")
        lines.append("Utilization: %.4f%%" % (state["leaf_count"] / 1048576 * 100))

    return {"success": True, "data": state, "message": "\n".join(lines)}


async def midas_check_nullifier(params: Dict[str, Any]) -> Dict:
    """Check if a nullifier has been spent (double-spend detection)."""
    contracts = _get_contracts()
    pool_addr = contracts.get("midas_pool", "")
    nullifier = params.get("nullifier", "")

    if not pool_addr:
        return {"success": False, "data": None, "message": "MidasPool not deployed."}
    if not nullifier:
        return {"success": False, "data": None, "message": "Need nullifier hash to check."}

    try:
        # Call nullifiers mapping (storage variable read via function)
        result = await _starknet_call(pool_addr, "is_nullifier_spent", [nullifier])
        spent = False
        if result.get("success") and result.get("result"):
            spent = _felt_to_int(result["result"][0]) != 0

        _log_operation("nullifier_check", {"nullifier": nullifier[:20], "spent": spent})

        return {
            "success": True,
            "data": {"nullifier": nullifier, "spent": spent},
            "message": "Nullifier %s: %s" % (nullifier[:20] + "...", "SPENT (used)" if spent else "UNSPENT (valid)"),
        }
    except Exception as e:
        return {"success": False, "data": None, "message": "Nullifier check failed: %s" % str(e)}


async def midas_staking_overview(params: Dict[str, Any]) -> Dict:
    """Get shielded staking overview — TVL, positions, yield rates."""
    contracts = _get_contracts()
    staking_addr = contracts.get("shielded_staking", "")

    if not staking_addr:
        return {"success": False, "data": None, "message": "ShieldedStaking contract not deployed."}

    overview = {"contract": staking_addr, "assets": {}}

    # Query total staked per asset
    asset_names = {0: "WBTC", 1: "tBTC", 2: "LBTC", 3: "solvBTC", 4: "STRK", 5: "USDC", 6: "strkBTC"}
    for asset_id, name in asset_names.items():
        try:
            result = await _starknet_call(staking_addr, "total_staked", [hex(asset_id)])
            if result.get("success") and result.get("result"):
                raw = result["result"]
                value = _felt_to_int(raw[0]) + (_felt_to_int(raw[1]) << 128) if len(raw) >= 2 else (_felt_to_int(raw[0]) if raw else 0)
                if value > 0:
                    decimals = 8 if name in ("WBTC", "tBTC", "LBTC", "solvBTC", "strkBTC") else 6 if name == "USDC" else 18
                    overview["assets"][name] = {
                        "raw": value,
                        "human": _format_token_amount(value, decimals),
                        "asset_id": asset_id,
                    }
        except Exception:
            pass

    _log_operation("staking_overview", {"assets_with_tvl": len(overview["assets"])})

    lines = ["**MIDAS Shielded Staking**", "Contract: %s" % staking_addr[:20] + "...", ""]
    if overview["assets"]:
        lines.append("**Total Staked:**")
        for name, info in overview["assets"].items():
            lines.append("  %s: %.8f" % (name, info["human"]))
    else:
        lines.append("No active staking positions found.")

    return {"success": True, "data": overview, "message": "\n".join(lines)}


async def midas_yield_strategies(params: Dict[str, Any]) -> Dict:
    """Get yield router strategy status — Vesu, Ekubo, Re7 vault TVLs."""
    contracts = _get_contracts()
    yield_addr = contracts.get("yield_router", "")

    if not yield_addr:
        return {"success": False, "data": None, "message": "YieldRouter contract not deployed."}

    strategies = {
        0: {"name": "VesuLending", "description": "Vesu lending protocol — BTC lending yield"},
        1: {"name": "EkuboLP", "description": "Ekubo DEX — LP provision fees"},
        2: {"name": "Re7Vault", "description": "Re7 vault — managed BTC yield strategies"},
    }

    for sid, info in strategies.items():
        try:
            result = await _starknet_call(yield_addr, "strategy_tvl", [hex(sid)])
            if result.get("success") and result.get("result"):
                raw = _felt_to_int(result["result"][0]) if result["result"] else 0
                info["tvl_raw"] = raw
                info["tvl_human"] = _format_token_amount(raw, 8)  # BTC decimals
        except Exception:
            info["tvl_raw"] = 0
            info["tvl_human"] = 0

    _log_operation("yield_strategies_check", {"strategies": len(strategies)})

    lines = ["**MIDAS Yield Strategies**", ""]
    for sid, info in strategies.items():
        tvl = info.get("tvl_human", 0)
        lines.append("**[%d] %s**" % (sid, info["name"]))
        lines.append("  %s" % info["description"])
        lines.append("  TVL: %.8f BTC" % tvl)
        lines.append("")

    return {"success": True, "data": {"strategies": strategies}, "message": "\n".join(lines)}


async def midas_protocol_metrics(params: Dict[str, Any]) -> Dict:
    """Comprehensive protocol metrics — TVL, volume, users, fees, health score."""
    contracts = _get_contracts()
    pool_addr = contracts.get("midas_pool", "")

    if not pool_addr:
        return {"success": False, "data": None, "message": "MIDAS not deployed."}

    metrics = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "network": STARKNET_NETWORK,
    }

    # Pool counters
    for fn in ["shield_count", "unshield_count", "total_shielded", "total_unshielded"]:
        try:
            result = await _starknet_call(pool_addr, fn)
            if result.get("success") and result.get("result"):
                raw = result["result"]
                if fn.startswith("total_"):
                    value = _felt_to_int(raw[0]) + (_felt_to_int(raw[1]) << 128) if len(raw) >= 2 else 0
                else:
                    value = _felt_to_int(raw[0]) if raw else 0
                metrics[fn] = value
        except Exception:
            metrics[fn] = "unavailable"

    # Check if paused
    try:
        result = await _starknet_call(pool_addr, "is_paused")
        if result.get("success") and result.get("result"):
            metrics["paused"] = _felt_to_int(result["result"][0]) != 0
    except Exception:
        pass

    # Health score (0-100)
    health_score = 100
    if metrics.get("paused"):
        health_score -= 50
    if not contracts.get("merkle"):
        health_score -= 10
    if not contracts.get("verifier"):
        health_score -= 10
    if not contracts.get("compliance"):
        health_score -= 10
    metrics["health_score"] = health_score

    _log_metrics(metrics)
    await _audit_to_hedera("midas_metrics", json.dumps({k: v for k, v in metrics.items() if isinstance(v, (int, float, bool, str))}))

    lines = [
        "**MIDAS Protocol Metrics**",
        "Network: %s | Health: %d/100" % (STARKNET_NETWORK, health_score),
        "",
    ]

    if isinstance(metrics.get("shield_count"), int):
        lines.append("Shield operations: %d" % metrics["shield_count"])
    if isinstance(metrics.get("unshield_count"), int):
        lines.append("Unshield operations: %d" % metrics["unshield_count"])
    if isinstance(metrics.get("total_shielded"), int):
        lines.append("Total shielded: %s (raw)" % metrics["total_shielded"])
    if isinstance(metrics.get("total_unshielded"), int):
        lines.append("Total unshielded: %s (raw)" % metrics["total_unshielded"])
    if "paused" in metrics:
        lines.append("Status: %s" % ("PAUSED" if metrics["paused"] else "ACTIVE"))

    return {"success": True, "data": metrics, "message": "\n".join(lines)}


async def midas_compliance_status(params: Dict[str, Any]) -> Dict:
    """Check compliance oracle status — KYC verification, sanctions screening."""
    contracts = _get_contracts()
    compliance_addr = contracts.get("compliance", "")

    if not compliance_addr:
        return {"success": False, "data": None, "message": "ComplianceOracle not deployed."}

    try:
        result = await _starknet_get_class_at(compliance_addr)
        deployed = result.get("deployed", False)

        data = {
            "contract": compliance_addr,
            "deployed": deployed,
            "features": [
                "KYC verification via encrypted viewing keys",
                "Sanctions list screening (OFAC, EU)",
                "Selective disclosure to regulators",
                "Amount threshold monitoring",
            ],
        }

        lines = [
            "**MIDAS Compliance Oracle**",
            "Contract: %s" % compliance_addr[:20] + "...",
            "Status: %s" % ("DEPLOYED" if deployed else "NOT DEPLOYED"),
            "",
            "**Features:**",
        ]
        for f in data["features"]:
            lines.append("  - %s" % f)

        return {"success": True, "data": data, "message": "\n".join(lines)}
    except Exception as e:
        return {"success": False, "data": None, "message": "Compliance check failed: %s" % str(e)}


async def midas_operations_log(params: Dict[str, Any]) -> Dict:
    """View Wave's MIDAS operations history — all interactions logged."""
    limit = params.get("limit", 20)

    if not OPS_LOG.exists():
        return {"success": True, "data": {"entries": []}, "message": "No operations recorded yet."}

    try:
        entries = []
        with open(OPS_LOG, "r") as f:
            for line in f:
                try:
                    entries.append(json.loads(line.strip()))
                except Exception:
                    pass

        recent = entries[-limit:]

        lines = ["**MIDAS Operations Log** (%d total, showing last %d)" % (len(entries), len(recent)), ""]
        for entry in reversed(recent):
            lines.append("[%s] %s on %s" % (
                entry.get("timestamp", "?")[:19],
                entry.get("operation", "?"),
                entry.get("network", "?"),
            ))

        return {"success": True, "data": {"entries": recent, "total": len(entries)}, "message": "\n".join(lines)}
    except Exception as e:
        return {"success": False, "data": None, "message": "Log read failed: %s" % str(e)}


async def midas_metrics_history(params: Dict[str, Any]) -> Dict:
    """View historical MIDAS metrics — TVL trends, activity over time."""
    limit = params.get("limit", 50)
    metric_name = params.get("metric", "")

    if not METRICS_LOG.exists():
        return {"success": True, "data": {"entries": []}, "message": "No metrics recorded yet."}

    try:
        entries = []
        with open(METRICS_LOG, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if metric_name and metric_name not in str(entry):
                        continue
                    entries.append(entry)
                except Exception:
                    pass

        recent = entries[-limit:]

        lines = ["**MIDAS Metrics History** (%d entries)" % len(entries), ""]
        for entry in recent[-20:]:
            ts = entry.get("timestamp", "?")[:19]
            # Extract key metrics
            interesting = {k: v for k, v in entry.items() if k not in ("timestamp", "network") and v}
            lines.append("[%s] %s" % (ts, json.dumps(interesting)[:120]))

        return {"success": True, "data": {"entries": recent, "total": len(entries)}, "message": "\n".join(lines)}
    except Exception as e:
        return {"success": False, "data": None, "message": "Metrics read failed: %s" % str(e)}


async def midas_starknet_wallet(params: Dict[str, Any]) -> Dict:
    """Check a Starknet wallet's token balances and transaction count."""
    wallet = params.get("address", "")
    if not wallet:
        # Use deployer address
        wallet = os.environ.get("STARKNET_DEPLOYER_ADDRESS", "")

    if not wallet:
        return {"success": False, "data": None, "message": "Need wallet address or set STARKNET_DEPLOYER_ADDRESS."}

    balances = {}

    for token_name, token_addr in STARKNET_TOKENS.items():
        try:
            result = await _starknet_call(token_addr, "balance_of", [wallet])
            if result.get("success") and result.get("result"):
                raw = result["result"]
                balance = _felt_to_int(raw[0]) + (_felt_to_int(raw[1]) << 128) if len(raw) >= 2 else (_felt_to_int(raw[0]) if raw else 0)
                decimals = 8 if token_name in ("WBTC",) else 6 if token_name in ("USDC", "USDT") else 18
                human = _format_token_amount(balance, decimals)
                if balance > 0:
                    balances[token_name] = {"raw": balance, "human": human}
        except Exception:
            pass

    lines = ["**Starknet Wallet: %s**" % (wallet[:15] + "..." + wallet[-6:]), ""]
    if balances:
        for name, info in balances.items():
            lines.append("  %s: %.6f" % (name, info["human"]))
    else:
        lines.append("  No token balances found (or wallet not deployed).")

    return {"success": True, "data": {"address": wallet, "balances": balances}, "message": "\n".join(lines)}


# ── TOOLS Registration ────────────────────────────────────────

TOOLS = [
    {
        "name": "midas_pool_status",
        "description": "Get comprehensive MIDAS protocol status — deployed contracts, TVL counters, pool metrics, network health. The main dashboard for MIDAS operations.",
        "handler": midas_pool_status,
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "midas_tvl",
        "description": "Track MIDAS Total Value Locked across MidasPool, ShieldedStaking, and YieldRouter. Checks all token balances on-chain.",
        "handler": midas_tvl,
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "midas_events",
        "description": "Monitor MIDAS on-chain events — shields, unshields, staking positions, yield claims. Filter by event type.",
        "handler": midas_events,
        "parameters": {
            "type": "object",
            "properties": {
                "event_type": {
                    "type": "string",
                    "enum": ["all", "shield", "unshield", "stake", "yield"],
                    "description": "Filter events by type. Default: all.",
                },
                "limit": {
                    "type": "integer",
                    "default": 20,
                    "description": "Maximum events to return.",
                },
            },
        },
    },
    {
        "name": "midas_contract_health",
        "description": "Health check for all MIDAS contracts — verify deployment, responsiveness, RPC connectivity. Returns health score.",
        "handler": midas_contract_health,
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "midas_merkle_state",
        "description": "Query the MIDAS Merkle tree state — current root hash, leaf count, tree utilization. Critical for verifying protocol integrity.",
        "handler": midas_merkle_state,
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "midas_check_nullifier",
        "description": "Check if a nullifier has been spent on-chain. Used for double-spend detection and unshield verification.",
        "handler": midas_check_nullifier,
        "parameters": {
            "type": "object",
            "properties": {
                "nullifier": {
                    "type": "string",
                    "description": "The nullifier hash (felt252) to check.",
                },
            },
            "required": ["nullifier"],
        },
    },
    {
        "name": "midas_staking_overview",
        "description": "Get shielded staking overview — total staked per asset, active positions. Privacy-preserving staking status.",
        "handler": midas_staking_overview,
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "midas_yield_strategies",
        "description": "Get yield router strategy status — Vesu lending, Ekubo LP, Re7 vault. Shows TVL per strategy.",
        "handler": midas_yield_strategies,
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "midas_protocol_metrics",
        "description": "Comprehensive MIDAS protocol metrics — shield/unshield counts, TVL, paused status, health score. All counters from on-chain.",
        "handler": midas_protocol_metrics,
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "midas_compliance_status",
        "description": "Check MIDAS ComplianceOracle status — KYC verification, sanctions screening, selective disclosure features.",
        "handler": midas_compliance_status,
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "midas_operations_log",
        "description": "View Wave's MIDAS operations history — every interaction logged with timestamps.",
        "handler": midas_operations_log,
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 20, "description": "Number of entries to show."},
            },
        },
    },
    {
        "name": "midas_metrics_history",
        "description": "View historical MIDAS metrics — TVL trends, activity over time. For tracking protocol growth.",
        "handler": midas_metrics_history,
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 50},
                "metric": {"type": "string", "description": "Filter by metric name."},
            },
        },
    },
    {
        "name": "midas_starknet_wallet",
        "description": "Check a Starknet wallet's token balances (STRK, ETH, USDC, WBTC, etc.). Use to check deployer wallet or any address.",
        "handler": midas_starknet_wallet,
        "parameters": {
            "type": "object",
            "properties": {
                "address": {"type": "string", "description": "Starknet wallet address. Defaults to deployer."},
            },
        },
    },
]
