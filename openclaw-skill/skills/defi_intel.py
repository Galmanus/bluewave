"""DeFi Intelligence — market scanning, yield opportunities, and crypto intel.

Wave uses DeFi knowledge to:
1. Find yield/earning opportunities to recommend to clients
2. Analyze tokens and protocols for advisory services
3. Monitor crypto market trends for content and sales angles
4. Price services dynamically based on real crypto rates

All data from free public APIs — no keys needed.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List

import httpx

logger = logging.getLogger("openclaw.skills.defi")

TIMEOUT = httpx.Timeout(15.0, connect=10.0)


async def scan_yields(params: Dict[str, Any]) -> Dict:
    """Scan DeFi protocols for yield opportunities using DeFiLlama.

    Returns top yield pools across all chains — sorted by APY.
    Wave can use this to advise clients or create content about yield strategies.
    """
    min_tvl = params.get("min_tvl_usd", 100000)
    chain = params.get("chain", "")
    stablecoin_only = params.get("stablecoin_only", False)
    limit = min(params.get("limit", 15), 30)

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get("https://yields.llama.fi/pools")
            data = resp.json()

        pools = data.get("data", [])

        # Filter
        filtered = []
        for p in pools:
            tvl = p.get("tvlUsd", 0) or 0
            apy = p.get("apy", 0) or 0
            if tvl < min_tvl or apy <= 0 or apy > 1000:  # skip scammy APYs
                continue
            if chain and p.get("chain", "").lower() != chain.lower():
                continue
            if stablecoin_only and not p.get("stablecoin", False):
                continue
            filtered.append({
                "pool": p.get("symbol", "?"),
                "project": p.get("project", "?"),
                "chain": p.get("chain", "?"),
                "apy": round(apy, 2),
                "tvl_usd": int(tvl),
                "stablecoin": p.get("stablecoin", False),
                "il_risk": p.get("ilRisk", "unknown"),
                "exposure": p.get("exposure", "unknown"),
            })

        # Sort by APY
        filtered.sort(key=lambda x: x["apy"], reverse=True)
        filtered = filtered[:limit]

        lines = ["**DeFi Yield Opportunities**%s\n" % (" (chain: %s)" % chain if chain else "")]
        for i, p in enumerate(filtered, 1):
            stable_tag = " [stable]" if p["stablecoin"] else ""
            lines.append("%d. **%s** on %s (%s) — **%.1f%% APY** | TVL: $%s%s" % (
                i, p["pool"], p["project"], p["chain"],
                p["apy"], _fmt_number(p["tvl_usd"]), stable_tag,
            ))

        return {"success": True, "data": filtered, "message": "\n".join(lines)}

    except Exception as e:
        return {"success": False, "data": None, "message": "Yield scan failed: %s" % str(e)}


async def protocol_stats(params: Dict[str, Any]) -> Dict:
    """Get TVL and stats for a specific DeFi protocol via DeFiLlama."""
    protocol = params.get("protocol", "")
    if not protocol:
        return {"success": False, "data": None, "message": "Need protocol name (e.g. 'aave', 'uniswap')"}

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get("https://api.llama.fi/protocol/%s" % protocol.lower())
            data = resp.json()

        if "name" not in data:
            return {"success": False, "data": None, "message": "Protocol '%s' not found on DeFiLlama" % protocol}

        tvl = data.get("currentChainTvls", {})
        total_tvl = sum(v for v in tvl.values() if isinstance(v, (int, float)))

        result = {
            "name": data.get("name"),
            "category": data.get("category"),
            "chains": data.get("chains", []),
            "total_tvl": total_tvl,
            "tvl_by_chain": {k: v for k, v in sorted(tvl.items(), key=lambda x: -x[1]) if isinstance(v, (int, float))}
        }

        chains_str = ", ".join(result["chains"][:5])
        top_tvl = list(result["tvl_by_chain"].items())[:5]

        lines = [
            "**%s** (%s)" % (result["name"], result["category"]),
            "Total TVL: **$%s**" % _fmt_number(total_tvl),
            "Chains: %s" % chains_str,
            "\nTVL by chain:",
        ]
        for chain, val in top_tvl:
            lines.append("  - %s: $%s" % (chain, _fmt_number(val)))

        return {"success": True, "data": result, "message": "\n".join(lines)}

    except Exception as e:
        return {"success": False, "data": None, "message": "Protocol lookup failed: %s" % str(e)}


async def top_protocols(params: Dict[str, Any]) -> Dict:
    """Get top DeFi protocols by TVL. Useful for market overview content."""
    chain = params.get("chain", "")
    category = params.get("category", "")
    limit = min(params.get("limit", 20), 50)

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get("https://api.llama.fi/protocols")
            protocols = resp.json()

        # Filter
        if chain:
            protocols = [p for p in protocols if chain.lower() in [c.lower() for c in p.get("chains", [])]]
        if category:
            protocols = [p for p in protocols if category.lower() in p.get("category", "").lower()]

        # Sort by TVL
        protocols.sort(key=lambda p: p.get("tvl", 0) or 0, reverse=True)
        top = protocols[:limit]

        results = []
        lines = ["**Top DeFi Protocols**%s%s\n" % (
            " (chain: %s)" % chain if chain else "",
            " (category: %s)" % category if category else "",
        )]

        for i, p in enumerate(top, 1):
            tvl = p.get("tvl", 0) or 0
            change_1d = p.get("change_1d", 0) or 0
            entry = {
                "name": p.get("name"),
                "category": p.get("category"),
                "tvl": tvl,
                "change_1d": change_1d,
                "chains": p.get("chains", [])[:3],
            }
            results.append(entry)
            trend = "+%.1f%%" % change_1d if change_1d > 0 else "%.1f%%" % change_1d
            lines.append("%d. **%s** (%s) — $%s TVL (%s)" % (
                i, entry["name"], entry["category"], _fmt_number(tvl), trend,
            ))

        return {"success": True, "data": results, "message": "\n".join(lines)}

    except Exception as e:
        return {"success": False, "data": None, "message": "Failed: %s" % str(e)}


async def token_price(params: Dict[str, Any]) -> Dict:
    """Get current price for any crypto token via CoinGecko free API."""
    token = params.get("token", "bitcoin")
    vs = params.get("vs_currency", "usd")

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get("https://api.coingecko.com/api/v3/simple/price", params={
                "ids": token.lower(),
                "vs_currencies": vs,
                "include_24hr_change": "true",
                "include_market_cap": "true",
            })
            data = resp.json()

        if token.lower() not in data:
            # Try searching by symbol
            resp2 = await httpx.AsyncClient(timeout=TIMEOUT).__aenter__()
            search = await resp2.get("https://api.coingecko.com/api/v3/search", params={"query": token})
            await resp2.__aexit__(None, None, None)
            coins = search.json().get("coins", [])
            if coins:
                token_id = coins[0]["id"]
                async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                    resp = await client.get("https://api.coingecko.com/api/v3/simple/price", params={
                        "ids": token_id, "vs_currencies": vs,
                        "include_24hr_change": "true", "include_market_cap": "true",
                    })
                    data = resp.json()
                    token = token_id

        info = data.get(token.lower(), {})
        price = info.get(vs, 0)
        change_24h = info.get("%s_24h_change" % vs, 0)
        mcap = info.get("%s_market_cap" % vs, 0)

        trend = "+%.2f%%" % change_24h if change_24h > 0 else "%.2f%%" % change_24h

        return {
            "success": True,
            "data": {"token": token, "price": price, "change_24h": change_24h, "market_cap": mcap},
            "message": "**%s**: $%.4f (%s) | MCap: $%s" % (token.upper(), price, trend, _fmt_number(mcap)),
        }

    except Exception as e:
        return {"success": False, "data": None, "message": "Price lookup failed: %s" % str(e)}


async def chain_overview(params: Dict[str, Any]) -> Dict:
    """Get TVL overview of all blockchain networks. Which chains are growing?"""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get("https://api.llama.fi/v2/chains")
            chains = resp.json()

        chains.sort(key=lambda c: c.get("tvl", 0) or 0, reverse=True)
        top = chains[:20]

        results = []
        lines = ["**Blockchain TVL Rankings**\n"]
        for i, c in enumerate(top, 1):
            entry = {
                "name": c.get("name"),
                "tvl": c.get("tvl", 0),
                "tokenSymbol": c.get("tokenSymbol", "?"),
            }
            results.append(entry)
            lines.append("%d. **%s** (%s) — $%s" % (
                i, entry["name"], entry["tokenSymbol"], _fmt_number(entry["tvl"]),
            ))

        return {"success": True, "data": results, "message": "\n".join(lines)}

    except Exception as e:
        return {"success": False, "data": None, "message": "Chain overview failed: %s" % str(e)}


def _fmt_number(n) -> str:
    """Format number with K/M/B suffix."""
    if not n or n == 0:
        return "0"
    n = float(n)
    if n >= 1_000_000_000:
        return "%.1fB" % (n / 1_000_000_000)
    if n >= 1_000_000:
        return "%.1fM" % (n / 1_000_000)
    if n >= 1_000:
        return "%.1fK" % (n / 1_000)
    return "%.2f" % n


TOOLS = [
    {
        "name": "defi_scan_yields",
        "description": "Scan DeFi protocols for yield/APY opportunities via DeFiLlama. Filter by chain, stablecoin-only, minimum TVL. Returns pools sorted by APY. Use for advisory content, client recommendations, or market analysis.",
        "handler": scan_yields,
        "parameters": {
            "type": "object",
            "properties": {
                "min_tvl_usd": {"type": "number", "default": 100000, "description": "Minimum TVL in USD"},
                "chain": {"type": "string", "description": "Filter by chain (Ethereum, Solana, Arbitrum, etc)"},
                "stablecoin_only": {"type": "boolean", "default": False},
                "limit": {"type": "integer", "default": 15},
            },
        },
    },
    {
        "name": "defi_protocol",
        "description": "Get detailed stats for a specific DeFi protocol (TVL, chains, category). Use for competitor analysis of DeFi projects or client advisory.",
        "handler": protocol_stats,
        "parameters": {
            "type": "object",
            "properties": {
                "protocol": {"type": "string", "description": "Protocol name (aave, uniswap, lido, etc)"},
            },
            "required": ["protocol"],
        },
    },
    {
        "name": "defi_top_protocols",
        "description": "Get top DeFi protocols by TVL. Filter by chain or category (DEX, Lending, Yield, Bridge, etc). Use for market overview content and trend analysis.",
        "handler": top_protocols,
        "parameters": {
            "type": "object",
            "properties": {
                "chain": {"type": "string", "description": "Filter by chain"},
                "category": {"type": "string", "description": "Filter by category (DEX, Lending, Yield, Bridge, CDP, etc)"},
                "limit": {"type": "integer", "default": 20},
            },
        },
    },
    {
        "name": "defi_token_price",
        "description": "Get current price, 24h change, and market cap for any crypto token via CoinGecko. Free, no API key. Use for pricing services, market context, or content.",
        "handler": token_price,
        "parameters": {
            "type": "object",
            "properties": {
                "token": {"type": "string", "default": "bitcoin", "description": "Token ID (bitcoin, ethereum, hedera-hashgraph, solana) or symbol"},
                "vs_currency": {"type": "string", "default": "usd"},
            },
        },
    },
    {
        "name": "defi_chain_overview",
        "description": "Get TVL rankings of all blockchain networks. Which chains are growing? Use for market content and identifying where opportunity is concentrating.",
        "handler": chain_overview,
        "parameters": {"type": "object", "properties": {}},
    },
]
