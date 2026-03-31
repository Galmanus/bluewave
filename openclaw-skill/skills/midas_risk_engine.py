"""MIDAS Risk Engine — PUT-based DeFi risk analysis.

Applies Psychometric Utility Theory to DeFi protocol analysis.
This is the SaaS product: sell risk intelligence to other protocols.

REVENUE MODEL:
  - API subscription: $500-$2K/month per protocol client
  - On-demand analysis: $50-$200 per report
  - Real-time alerts: premium tier

PUT VARIABLES APPLIED TO DEFI:
  - A (Agency): protocol team's execution capability
  - F (Fear): market panic indicators (TVL drops, mass withdrawals)
  - τ (Treachery): rug pull indicators, insider behavior
  - Φ (Self-delusion): unsustainable APY, inflated metrics
  - Ω (Desperation): protocol survival pressure
  - FP (Fracture Potential): probability of protocol collapse

OUTPUT:
  - Risk scores per protocol (0-100)
  - Bank run prediction (early warning)
  - Rug pull probability
  - Sustainability score for yields
"""

from __future__ import annotations

import json
import logging
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("openclaw.skills.midas_risk_engine")

MEMORY_DIR = Path(__file__).parent.parent / "memory"
RISK_LOG = MEMORY_DIR / "midas_risk_analysis.jsonl"
RISK_ALERTS = MEMORY_DIR / "midas_risk_alerts.jsonl"

TIMEOUT = httpx.Timeout(20.0, connect=10.0)

# ── PUT Constants for DeFi ────────────────────────────────────

# Weights for the DeFi-adapted PUT utility function
ALPHA = 1.0     # Agency weight
BETA = 0.8      # Fear weight
GAMMA = 0.6     # Social weight
DELTA = 1.2     # Treachery weight (high — rug pulls are catastrophic)
EPSILON = 0.7   # Self-delusion weight

# Critical thresholds
U_CRIT = -0.3          # Below this → protocol in danger
FRACTURE_THRESHOLD = 0.7  # Above this → imminent collapse risk
TVL_DROP_PANIC = -0.20    # 20% TVL drop in 24h = panic
APY_SUSTAINABILITY_MAX = 100  # APY above this is almost certainly unsustainable


def _log_risk(action: str, data: dict) -> None:
    """Append to risk analysis log."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        **data,
    }
    try:
        RISK_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(RISK_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        logger.warning("Risk log failed: %s", e)


def _log_alert(alert: dict) -> None:
    """Log a risk alert."""
    try:
        RISK_ALERTS.parent.mkdir(parents=True, exist_ok=True)
        with open(RISK_ALERTS, "a") as f:
            f.write(json.dumps(alert) + "\n")
    except Exception as e:
        logger.warning("Alert log failed: %s", e)


# ── PUT Model for DeFi ───────────────────────────────────────

def _calculate_agency(protocol_data: dict) -> float:
    """A: Protocol team execution capability (0-1).

    High agency = active development, growing TVL, audit trail.
    Low agency = stale code, declining TVL, no audits.
    """
    tvl = protocol_data.get("tvl", 0) or 0
    change_1d = protocol_data.get("change_1d", 0) or 0
    change_7d = protocol_data.get("change_7d", 0) or 0
    chains = len(protocol_data.get("chains", []))
    audits = protocol_data.get("audits", 0)

    score = 0.5  # Base

    # TVL health
    if tvl > 100_000_000:
        score += 0.15
    elif tvl > 10_000_000:
        score += 0.10
    elif tvl > 1_000_000:
        score += 0.05
    elif tvl < 100_000:
        score -= 0.15

    # Growth trajectory
    if change_7d > 10:
        score += 0.10
    elif change_7d > 0:
        score += 0.05
    elif change_7d < -10:
        score -= 0.10
    elif change_7d < -20:
        score -= 0.20

    # Multi-chain = more robust
    if chains > 5:
        score += 0.10
    elif chains > 2:
        score += 0.05

    # Audits
    if audits > 2:
        score += 0.10
    elif audits > 0:
        score += 0.05

    return max(0, min(1, score))


def _calculate_fear(protocol_data: dict, market_data: dict) -> float:
    """F: Market panic indicators (0-1).

    High fear = mass withdrawals, TVL crash, negative sentiment.
    Low fear = stable/growing TVL, positive market.
    """
    change_1d = protocol_data.get("change_1d", 0) or 0
    change_7d = protocol_data.get("change_7d", 0) or 0
    btc_change = market_data.get("btc_24h_change", 0) or 0

    score = 0.3  # Base (some fear is normal)

    # TVL drops indicate fear
    if change_1d < TVL_DROP_PANIC:
        score += 0.30  # Panic-level drop
    elif change_1d < -10:
        score += 0.20
    elif change_1d < -5:
        score += 0.10

    # Weekly trend
    if change_7d < -20:
        score += 0.15
    elif change_7d < -10:
        score += 0.08

    # BTC market sentiment affects all DeFi
    if btc_change < -10:
        score += 0.15
    elif btc_change < -5:
        score += 0.08

    return max(0, min(1, score))


def _calculate_treachery(protocol_data: dict, pool_data: List[dict]) -> float:
    """τ: Rug pull / insider extraction indicators (0-1).

    High treachery = sudden parameter changes, large insider withdrawals,
    unverified contracts, anonymous team.
    """
    tvl = protocol_data.get("tvl", 0) or 0
    change_1d = protocol_data.get("change_1d", 0) or 0
    category = protocol_data.get("category", "").lower()

    score = 0.1  # Base

    # Sudden massive TVL drop with no market correlation = possible extraction
    if change_1d < -30:
        score += 0.30

    # Very high APY pools are treachery signals
    suspicious_pools = [p for p in pool_data if (p.get("apy", 0) or 0) > APY_SUSTAINABILITY_MAX]
    if suspicious_pools:
        score += 0.05 * min(len(suspicious_pools), 5)

    # Low TVL + high APY = honeypot pattern
    if tvl < 500_000 and any((p.get("apy", 0) or 0) > 50 for p in pool_data):
        score += 0.15

    # Some categories are inherently riskier
    if category in ("yield", "yield aggregator", "algo-stables"):
        score += 0.10

    # Unaudited protocols
    if not protocol_data.get("audit_links"):
        score += 0.10

    return max(0, min(1, score))


def _calculate_self_delusion(pool_data: List[dict]) -> float:
    """Φ: Unsustainable metrics / inflated claims (0-1).

    High self-delusion = APY from token emissions (not real yield),
    inflated TVL, reward-dependent returns.
    """
    if not pool_data:
        return 0.3

    score = 0.1

    # Ratio of reward APY to base APY
    for p in pool_data:
        apy_base = p.get("apyBase", 0) or 0
        apy_reward = p.get("apyReward", 0) or 0
        apy_total = p.get("apy", 0) or 0

        if apy_total > 0 and apy_reward > apy_base * 3:
            score += 0.08  # Heavily reward-dependent
        if apy_total > APY_SUSTAINABILITY_MAX:
            score += 0.10  # Almost certainly unsustainable

    # Average across pools
    pool_count = len(pool_data) or 1
    score = score / (1 + (pool_count - 1) * 0.3)  # Diminish for many pools

    return max(0, min(1, score))


def _calculate_desperation(protocol_data: dict) -> float:
    """Ω: Protocol survival pressure (0-1).

    High desperation = declining TVL trend, losing market share,
    extreme incentive programs.
    """
    change_7d = protocol_data.get("change_7d", 0) or 0
    change_1d = protocol_data.get("change_1d", 0) or 0
    tvl = protocol_data.get("tvl", 0) or 0

    score = 0.1

    # Consistent decline
    if change_7d < -15 and change_1d < -5:
        score += 0.25
    elif change_7d < -10:
        score += 0.15

    # Very low TVL = existential threat
    if tvl < 100_000:
        score += 0.20
    elif tvl < 500_000:
        score += 0.10

    return max(0, min(1, score))


def _put_utility(A: float, F: float, tau: float, phi: float, omega: float, k: float = 0.1) -> float:
    """Calculate PUT Utility for a DeFi protocol.

    U = α·A·(1-Fk) - β·Fk·(1-S) + γ·S·(1-w)·Σ + δ·τ·κ - ε·Φ
    Simplified for DeFi context where S (sadism) maps to competitive pressure.
    """
    Fk = F * (1 - k)
    S = 0.3  # Normalized competitive pressure
    w = 0.5  # Cooperation vs competition

    U = (ALPHA * A * (1 - Fk)
         - BETA * Fk * (1 - S)
         - DELTA * tau
         - EPSILON * phi)

    # Desperation amplifier
    omega_factor = 1 / (1 + math.exp(-5 * (U - U_CRIT)))
    U = U * (1 + 0.3 * (1 - omega_factor) * omega)

    return U


def _fracture_potential(A: float, F: float, tau: float, phi: float, U: float) -> float:
    """FP = [(1-Rv)·(κ+τ+Φ)] / (Ucrit-U+ε)

    Probability of protocol collapse.
    Calibrated so healthy protocols score <0.3, stressed <0.6, critical >0.7.
    """
    Rv = max(0, min(1, A * 0.8))  # Recovery capability ≈ Agency
    kappa = tau * 0.5  # Guilt-to-power (exploitation efficiency)

    numerator = (1 - Rv) * (kappa + tau + phi)
    # Use larger epsilon and scale denominator to produce differentiated scores
    denominator = abs(U_CRIT - U) + 0.5

    fp = numerator / denominator
    # Sigmoid compression to keep output in useful range
    fp = fp / (fp + 0.5)  # Maps [0,inf) → [0,1) with midpoint at fp_raw=0.5
    return max(0, min(1, fp))


# ── Public Tools ──────────────────────────────────────────────

async def analyze_protocol_risk(params: Dict[str, Any]) -> Dict:
    """Full PUT risk analysis of a DeFi protocol.

    Applies Psychometric Utility Theory to assess protocol health,
    rug pull probability, and collapse risk.
    """
    protocol = params.get("protocol", "")
    if not protocol:
        return {"success": False, "data": None, "message": "Need protocol name (e.g., 'ekubo', 'vesu', 'jediswap')"}

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            # Protocol data
            proto_resp = await client.get("https://api.llama.fi/protocol/%s" % protocol.lower())
            proto_data = proto_resp.json()

            # Pool data
            pools_resp = await client.get("https://yields.llama.fi/pools")
            all_pools = pools_resp.json().get("data", [])

            # BTC price for market context
            btc_resp = await client.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "bitcoin", "vs_currencies": "usd", "include_24hr_change": "true"},
            )
            btc_data = btc_resp.json().get("bitcoin", {})

        if "name" not in proto_data:
            return {"success": False, "data": None, "message": "Protocol '%s' not found" % protocol}

        # Filter pools for this protocol
        protocol_pools = [
            p for p in all_pools
            if p.get("project", "").lower() == protocol.lower()
        ]
        starknet_pools = [p for p in protocol_pools if p.get("chain", "").lower() == "starknet"]

        # Extract protocol metrics
        tvl_by_chain = proto_data.get("currentChainTvls", {})
        total_tvl = sum(v for v in tvl_by_chain.values() if isinstance(v, (int, float)))

        pdata = {
            "tvl": total_tvl,
            "change_1d": proto_data.get("change_1d", 0),
            "change_7d": proto_data.get("change_7d", 0),
            "chains": proto_data.get("chains", []),
            "category": proto_data.get("category", ""),
            "audit_links": proto_data.get("audit_links", []),
            "audits": len(proto_data.get("audit_links", [])),
        }

        market_data = {
            "btc_24h_change": btc_data.get("usd_24h_change", 0),
        }

        # Calculate PUT variables
        A = _calculate_agency(pdata)
        F = _calculate_fear(pdata, market_data)
        tau = _calculate_treachery(pdata, protocol_pools)
        phi = _calculate_self_delusion(protocol_pools)
        omega = _calculate_desperation(pdata)

        # Core PUT calculations
        U = _put_utility(A, F, tau, phi, omega)
        FP = _fracture_potential(A, F, tau, phi, U)

        # Risk score (0-100, higher = more risk)
        risk_score = int(max(0, min(100, (1 - (U + 1) / 2) * 60 + FP * 40)))

        # Risk tier
        if risk_score < 25:
            risk_tier = "LOW"
            risk_color = "green"
        elif risk_score < 50:
            risk_tier = "MODERATE"
            risk_color = "yellow"
        elif risk_score < 75:
            risk_tier = "HIGH"
            risk_color = "orange"
        else:
            risk_tier = "CRITICAL"
            risk_color = "red"

        # Specific warnings
        warnings = []
        if FP > FRACTURE_THRESHOLD:
            warnings.append("FRACTURE POTENTIAL ABOVE THRESHOLD — collapse risk elevated")
        if tau > 0.5:
            warnings.append("HIGH TREACHERY INDICATORS — possible insider extraction")
        if phi > 0.5:
            warnings.append("HIGH SELF-DELUSION — yields likely unsustainable")
        if F > 0.7:
            warnings.append("PANIC-LEVEL FEAR — mass withdrawals detected")
        if omega > 0.5:
            warnings.append("PROTOCOL UNDER EXISTENTIAL PRESSURE")

        # Bank run probability
        bank_run_prob = min(1.0, F * 0.4 + tau * 0.3 + omega * 0.3) if F > 0.5 else F * 0.2

        # Sustainability score (inverse of self-delusion)
        sustainability = max(0, min(100, int((1 - phi) * 80 + A * 20)))

        result = {
            "protocol": proto_data.get("name", protocol),
            "category": pdata["category"],
            "tvl_total": total_tvl,
            "tvl_starknet": tvl_by_chain.get("Starknet", 0),
            "change_1d": pdata["change_1d"],
            "change_7d": pdata["change_7d"],
            "chains": len(pdata["chains"]),
            "audits": pdata["audits"],
            "pools_total": len(protocol_pools),
            "pools_starknet": len(starknet_pools),
            "put_variables": {
                "agency_A": round(A, 3),
                "fear_F": round(F, 3),
                "treachery_tau": round(tau, 3),
                "self_delusion_phi": round(phi, 3),
                "desperation_omega": round(omega, 3),
            },
            "put_derived": {
                "utility_U": round(U, 3),
                "fracture_potential_FP": round(FP, 3),
            },
            "risk_score": risk_score,
            "risk_tier": risk_tier,
            "bank_run_probability": round(bank_run_prob * 100, 1),
            "sustainability_score": sustainability,
            "warnings": warnings,
        }

        _log_risk("protocol_analysis", result)

        # Check if alert needed
        if risk_score >= 75 or FP > FRACTURE_THRESHOLD:
            alert = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "protocol": protocol,
                "risk_score": risk_score,
                "fracture_potential": round(FP, 3),
                "type": "critical_risk",
                "warnings": warnings,
            }
            _log_alert(alert)

        # Format output
        lines = [
            "**PUT Risk Analysis: %s**" % result["protocol"],
            "Category: %s | TVL: $%s | Starknet: $%s" % (
                pdata["category"], _fmt(total_tvl), _fmt(tvl_by_chain.get("Starknet", 0)),
            ),
            "24h: %+.1f%% | 7d: %+.1f%% | Audits: %d | Chains: %d" % (
                pdata["change_1d"] or 0, pdata["change_7d"] or 0, pdata["audits"], len(pdata["chains"]),
            ),
            "",
            "**PUT Variables:**",
            "  Agency (A):        %.2f  %s" % (A, _bar(A)),
            "  Fear (F):          %.2f  %s" % (F, _bar(F)),
            "  Treachery (τ):     %.2f  %s" % (tau, _bar(tau)),
            "  Self-Delusion (Φ): %.2f  %s" % (phi, _bar(phi)),
            "  Desperation (Ω):   %.2f  %s" % (omega, _bar(omega)),
            "",
            "**Derived Metrics:**",
            "  Utility (U):           %+.3f" % U,
            "  Fracture Potential:    %.3f %s" % (FP, "[ABOVE THRESHOLD]" if FP > FRACTURE_THRESHOLD else ""),
            "",
            "**RISK SCORE: %d/100 — %s**" % (risk_score, risk_tier),
            "  Bank run probability:  %.1f%%" % (bank_run_prob * 100),
            "  Yield sustainability:  %d/100" % sustainability,
        ]

        if warnings:
            lines.extend(["", "**WARNINGS:**"])
            for w in warnings:
                lines.append("  ⚠ %s" % w)

        return {"success": True, "data": result, "message": "\n".join(lines)}

    except Exception as e:
        logger.error("Risk analysis failed: %s", e, exc_info=True)
        return {"success": False, "data": None, "message": "Risk analysis failed: %s" % str(e)}


async def scan_starknet_risks(params: Dict[str, Any]) -> Dict:
    """Scan ALL Starknet protocols for risk using PUT model.

    Returns risk-ranked list of protocols. Identifies which ones
    are dangerous and which are safe for MIDAS integration.
    """
    min_tvl = params.get("min_tvl_usd", 100_000)
    limit = params.get("limit", 20)

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            # All protocols
            protos_resp = await client.get("https://api.llama.fi/protocols")
            all_protocols = protos_resp.json()

            # All pools
            pools_resp = await client.get("https://yields.llama.fi/pools")
            all_pools = pools_resp.json().get("data", [])

            # BTC for market context
            btc_resp = await client.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "bitcoin", "vs_currencies": "usd", "include_24hr_change": "true"},
            )
            btc_data = btc_resp.json().get("bitcoin", {})

        market_data = {"btc_24h_change": btc_data.get("usd_24h_change", 0)}

        # Filter Starknet protocols
        starknet_protocols = [
            p for p in all_protocols
            if "Starknet" in p.get("chains", []) and (p.get("tvl", 0) or 0) >= min_tvl
        ]

        # Index pools by project
        pools_by_project = {}
        for pool in all_pools:
            proj = pool.get("project", "").lower()
            if proj not in pools_by_project:
                pools_by_project[proj] = []
            pools_by_project[proj].append(pool)

        # Analyze each protocol
        results = []
        for proto in starknet_protocols:
            name = proto.get("name", "?")
            slug = proto.get("slug", name.lower())

            pdata = {
                "tvl": proto.get("tvl", 0),
                "change_1d": proto.get("change_1d", 0),
                "change_7d": proto.get("change_7d", 0),
                "chains": proto.get("chains", []),
                "category": proto.get("category", ""),
                "audit_links": proto.get("audit_links", []),
                "audits": len(proto.get("audit_links", [])),
            }

            protocol_pools = pools_by_project.get(slug, [])

            A = _calculate_agency(pdata)
            F = _calculate_fear(pdata, market_data)
            tau = _calculate_treachery(pdata, protocol_pools)
            phi = _calculate_self_delusion(protocol_pools)
            omega = _calculate_desperation(pdata)

            U = _put_utility(A, F, tau, phi, omega)
            FP = _fracture_potential(A, F, tau, phi, U)

            risk_score = int(max(0, min(100, (1 - (U + 1) / 2) * 60 + FP * 40)))

            results.append({
                "name": name,
                "slug": slug,
                "category": pdata["category"],
                "tvl": pdata["tvl"],
                "change_7d": pdata["change_7d"],
                "risk_score": risk_score,
                "fracture_potential": round(FP, 3),
                "utility": round(U, 3),
                "agency": round(A, 2),
                "fear": round(F, 2),
                "treachery": round(tau, 2),
                "tier": "LOW" if risk_score < 25 else "MOD" if risk_score < 50 else "HIGH" if risk_score < 75 else "CRIT",
            })

        # Sort by risk score (highest risk first)
        results.sort(key=lambda x: x["risk_score"], reverse=True)
        results = results[:limit]

        _log_risk("starknet_scan", {
            "protocols_analyzed": len(results),
            "high_risk_count": len([r for r in results if r["risk_score"] >= 50]),
        })

        lines = [
            "**Starknet Protocol Risk Scan (PUT Model)**",
            "Protocols analyzed: %d | Market (BTC 24h): %+.1f%%" % (
                len(results), btc_data.get("usd_24h_change", 0) or 0,
            ),
            "",
        ]
        for i, r in enumerate(results, 1):
            tier_tag = {"LOW": "[OK]", "MOD": "[!]", "HIGH": "[!!]", "CRIT": "[!!!]"}.get(r["tier"], "")
            lines.append(
                "%d. **%s** (%s) — Risk: %d/100 %s | FP: %.2f | TVL: $%s | 7d: %+.1f%%" % (
                    i, r["name"], r["category"], r["risk_score"], tier_tag,
                    r["fracture_potential"], _fmt(r["tvl"]), r["change_7d"] or 0,
                )
            )

        return {"success": True, "data": results, "message": "\n".join(lines)}

    except Exception as e:
        return {"success": False, "data": None, "message": "Risk scan failed: %s" % str(e)}


async def bank_run_detector(params: Dict[str, Any]) -> Dict:
    """Detect potential bank runs on Starknet DeFi protocols.

    Uses TVL velocity + PUT Fear variable to identify mass withdrawal events
    before they become catastrophic.

    This is the premium alert product.
    """
    threshold_pct = params.get("threshold_pct", -10)  # Alert if TVL drops more than this

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            protos_resp = await client.get("https://api.llama.fi/protocols")
            protocols = protos_resp.json()

        starknet = [
            p for p in protocols
            if "Starknet" in p.get("chains", []) and (p.get("tvl", 0) or 0) > 50_000
        ]

        alerts = []
        for proto in starknet:
            change_1d = proto.get("change_1d", 0) or 0
            change_7d = proto.get("change_7d", 0) or 0
            tvl = proto.get("tvl", 0) or 0

            # Bank run indicators
            is_bank_run = False
            severity = "low"
            reasons = []

            if change_1d < threshold_pct:
                is_bank_run = True
                severity = "high" if change_1d < threshold_pct * 2 else "medium"
                reasons.append("TVL dropped %.1f%% in 24h" % change_1d)

            if change_7d < threshold_pct * 2:
                is_bank_run = True
                if severity == "low":
                    severity = "medium"
                reasons.append("TVL dropped %.1f%% in 7d" % change_7d)

            # Accelerating decline (7d bad AND 1d getting worse)
            if change_7d < -5 and change_1d < change_7d / 7 * 2:
                is_bank_run = True
                severity = "high"
                reasons.append("Accelerating decline detected")

            if is_bank_run:
                alert = {
                    "protocol": proto.get("name", "?"),
                    "slug": proto.get("slug", ""),
                    "tvl": tvl,
                    "change_1d": change_1d,
                    "change_7d": change_7d,
                    "severity": severity,
                    "reasons": reasons,
                    "category": proto.get("category", ""),
                }
                alerts.append(alert)

                _log_alert({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "type": "bank_run",
                    **alert,
                })

        # Sort by severity
        severity_order = {"high": 0, "medium": 1, "low": 2}
        alerts.sort(key=lambda x: severity_order.get(x["severity"], 3))

        lines = [
            "**Bank Run Detector — Starknet**",
            "Threshold: %.0f%% TVL drop | Protocols scanned: %d" % (threshold_pct, len(starknet)),
            "",
        ]

        if not alerts:
            lines.append("**NO BANK RUNS DETECTED** — all protocols stable.")
        else:
            lines.append("**%d ALERTS:**\n" % len(alerts))
            for a in alerts:
                sev_icon = {"high": "[!!!]", "medium": "[!!]", "low": "[!]"}.get(a["severity"], "")
                lines.append(
                    "%s **%s** — TVL: $%s | 24h: %+.1f%% | 7d: %+.1f%%" % (
                        sev_icon, a["protocol"], _fmt(a["tvl"]), a["change_1d"], a["change_7d"],
                    )
                )
                for r in a["reasons"]:
                    lines.append("    → %s" % r)

        return {
            "success": True,
            "data": {"alerts": alerts, "protocols_scanned": len(starknet)},
            "message": "\n".join(lines),
        }

    except Exception as e:
        return {"success": False, "data": None, "message": "Bank run detection failed: %s" % str(e)}


async def yield_sustainability_score(params: Dict[str, Any]) -> Dict:
    """Analyze whether a protocol's yields are sustainable or ponzi-like.

    Uses PUT Self-Delusion (Φ) variable heavily.
    Key question: is the yield from real economic activity or token emissions?
    """
    protocol = params.get("protocol", "")
    if not protocol:
        return {"success": False, "data": None, "message": "Need protocol name"}

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            pools_resp = await client.get("https://yields.llama.fi/pools")
            all_pools = pools_resp.json().get("data", [])

        protocol_pools = [
            p for p in all_pools
            if p.get("project", "").lower() == protocol.lower()
        ]

        if not protocol_pools:
            return {"success": False, "data": None, "message": "No pools found for '%s'" % protocol}

        analyses = []
        for p in protocol_pools:
            apy_total = p.get("apy", 0) or 0
            apy_base = p.get("apyBase", 0) or 0
            apy_reward = p.get("apyReward", 0) or 0
            tvl = p.get("tvlUsd", 0) or 0
            apy_mean_30d = p.get("apyMean30d", 0) or 0

            # Sustainability metrics
            organic_ratio = apy_base / apy_total if apy_total > 0 else 0
            emission_dependency = apy_reward / apy_total if apy_total > 0 else 0
            apy_stability = 1 - abs(apy_total - apy_mean_30d) / max(apy_total, 1)

            # Sustainability score 0-100
            sus_score = int(
                organic_ratio * 40 +          # Real yield is sustainable
                (1 - emission_dependency) * 30 + # Less emission-dependent = better
                min(1, apy_stability) * 20 +   # Stable APY = sustainable
                min(1, tvl / 5_000_000) * 10   # Higher TVL = more sustainable
            )

            verdict = "SUSTAINABLE" if sus_score > 70 else "MIXED" if sus_score > 40 else "UNSUSTAINABLE"

            analyses.append({
                "pool": p.get("symbol", "?"),
                "chain": p.get("chain", "?"),
                "apy_total": round(apy_total, 2),
                "apy_base": round(apy_base, 2),
                "apy_reward": round(apy_reward, 2),
                "tvl": int(tvl),
                "organic_ratio": round(organic_ratio * 100, 1),
                "emission_dependency": round(emission_dependency * 100, 1),
                "sustainability_score": sus_score,
                "verdict": verdict,
            })

        # Sort by sustainability (worst first — find problems)
        analyses.sort(key=lambda x: x["sustainability_score"])

        avg_sus = sum(a["sustainability_score"] for a in analyses) / len(analyses)
        avg_organic = sum(a["organic_ratio"] for a in analyses) / len(analyses)

        result = {
            "protocol": protocol,
            "pools_analyzed": len(analyses),
            "avg_sustainability": round(avg_sus, 1),
            "avg_organic_ratio": round(avg_organic, 1),
            "pools": analyses,
        }

        _log_risk("sustainability_analysis", result)

        lines = [
            "**Yield Sustainability: %s**" % protocol,
            "Pools: %d | Avg sustainability: %.0f/100 | Avg organic yield: %.0f%%" % (
                len(analyses), avg_sus, avg_organic,
            ),
            "",
        ]
        for a in analyses:
            sus_tag = {"SUSTAINABLE": "[OK]", "MIXED": "[!]", "UNSUSTAINABLE": "[!!]"}.get(a["verdict"], "")
            lines.append(
                "  **%s** (%s) — APY: %.1f%% (base: %.1f%%, reward: %.1f%%) | Score: %d %s" % (
                    a["pool"], a["chain"], a["apy_total"], a["apy_base"],
                    a["apy_reward"], a["sustainability_score"], sus_tag,
                )
            )

        return {"success": True, "data": result, "message": "\n".join(lines)}

    except Exception as e:
        return {"success": False, "data": None, "message": "Sustainability analysis failed: %s" % str(e)}


async def risk_engine_status(params: Dict[str, Any]) -> Dict:
    """Get risk engine status — recent analyses, alerts, and coverage."""
    analyses = []
    alerts = []

    if RISK_LOG.exists():
        try:
            with open(RISK_LOG) as f:
                for line in f:
                    try:
                        analyses.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass

    if RISK_ALERTS.exists():
        try:
            with open(RISK_ALERTS) as f:
                for line in f:
                    try:
                        alerts.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass

    result = {
        "total_analyses": len(analyses),
        "total_alerts": len(alerts),
        "recent_alerts": alerts[-5:] if alerts else [],
        "last_analysis": analyses[-1] if analyses else None,
    }

    lines = [
        "**MIDAS Risk Engine — Status**",
        "",
        "Total analyses: %d" % len(analyses),
        "Total alerts: %d" % len(alerts),
    ]
    if alerts:
        lines.extend(["", "**Recent Alerts:**"])
        for a in alerts[-5:]:
            lines.append("  - [%s] %s: %s" % (
                a.get("type", "?"), a.get("protocol", "?"),
                "; ".join(a.get("warnings", a.get("reasons", ["N/A"]))),
            ))

    return {"success": True, "data": result, "message": "\n".join(lines)}


# ── Helpers ───────────────────────────────────────────────────

def _bar(value: float, width: int = 10) -> str:
    """Simple ASCII bar for visualization."""
    filled = int(value * width)
    return "[%s%s]" % ("█" * filled, "░" * (width - filled))


def _fmt(n) -> str:
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


# ── Tool Definitions ──────────────────────────────────────────

TOOLS = [
    {
        "name": "midas_risk_analysis",
        "description": "Full PUT risk analysis of a DeFi protocol. Applies Psychometric Utility Theory (Agency, Fear, Treachery, Self-Delusion, Desperation) to assess protocol health, rug pull probability, and collapse risk. Returns risk score 0-100.",
        "handler": analyze_protocol_risk,
        "parameters": {
            "type": "object",
            "properties": {
                "protocol": {"type": "string", "description": "Protocol slug (ekubo, vesu, jediswap, nostra, etc)"},
            },
            "required": ["protocol"],
        },
    },
    {
        "name": "midas_risk_scan",
        "description": "Scan ALL Starknet protocols for risk using PUT model. Returns risk-ranked list identifying dangerous and safe protocols. Use for portfolio protection and MIDAS integration decisions.",
        "handler": scan_starknet_risks,
        "parameters": {
            "type": "object",
            "properties": {
                "min_tvl_usd": {"type": "number", "default": 100000},
                "limit": {"type": "integer", "default": 20},
            },
        },
    },
    {
        "name": "midas_bank_run_detector",
        "description": "Detect potential bank runs on Starknet DeFi protocols. Uses TVL velocity + PUT Fear to identify mass withdrawal events before they become catastrophic. Premium alert product.",
        "handler": bank_run_detector,
        "parameters": {
            "type": "object",
            "properties": {
                "threshold_pct": {"type": "number", "default": -10, "description": "Alert threshold (negative %)"},
            },
        },
    },
    {
        "name": "midas_yield_sustainability",
        "description": "Analyze whether a protocol's yields are sustainable or ponzi-like. Uses PUT Self-Delusion to separate real yield from token emissions. Key question: is the APY real or fake?",
        "handler": yield_sustainability_score,
        "parameters": {
            "type": "object",
            "properties": {
                "protocol": {"type": "string", "description": "Protocol slug"},
            },
            "required": ["protocol"],
        },
    },
    {
        "name": "midas_risk_status",
        "description": "Get MIDAS Risk Engine status — recent analyses, active alerts, coverage metrics.",
        "handler": risk_engine_status,
        "parameters": {"type": "object", "properties": {}},
    },
]
