"""
Financial Intelligence Skills — Cérebro financeiro do Wave.

Unit economics, pricing optimization, revenue forecasting,
treasury management, profitability analysis, growth modeling.
"""

import json
import math
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

MEMORY_DIR = Path(__file__).parent.parent / "memory"
REVENUE_LOG = MEMORY_DIR / "revenue_log.jsonl"
SALES_PIPELINE = MEMORY_DIR / "sales_pipeline.jsonl"
PROMO_LOG = MEMORY_DIR / "promo_log.jsonl"
AUTONOMOUS_STATE = MEMORY_DIR / "autonomous_state.json"
PRICING_CONFIG = MEMORY_DIR / "pricing_config.json"
FINANCIAL_STATE = MEMORY_DIR / "financial_state.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_jsonl(path: Path) -> List[Dict]:
    """Read all entries from a JSONL file."""
    if not path.exists():
        return []
    entries = []
    try:
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception:
        pass
    return entries


def _read_json(path: Path) -> Dict:
    """Read a JSON file."""
    if not path.exists():
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _write_json(path: Path, data: Dict) -> None:
    """Write a JSON file."""
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _append_jsonl(path: Path, entry: Dict) -> None:
    """Append an entry to a JSONL file."""
    with open(path, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def _get_financial_state() -> Dict:
    """Load or initialize financial state."""
    default = {
        "total_revenue_usd": 0.0,
        "total_revenue_hbar": 0.0,
        "total_costs_usd": 0.0,
        "treasury": {
            "hbar": 0.0,
            "usdt": 0.0,
            "usdc": 0.0,
            "brl": 0.0,
            "usd": 0.0,
        },
        "monthly_fixed_costs_usd": 25.0,  # servidor + domínio + misc
        "api_cost_per_1k_tokens": {
            "haiku_input": 0.00025,
            "haiku_output": 0.00125,
            "sonnet_input": 0.003,
            "sonnet_output": 0.015,
            "opus_input": 0.015,
            "opus_output": 0.075,
        },
        "hbar_usd_rate": 0.15,
        "clients": {},
        "last_updated": None,
    }
    state = _read_json(FINANCIAL_STATE)
    if not state:
        state = default
        _write_json(FINANCIAL_STATE, state)
    # Ensure all keys exist
    for k, v in default.items():
        if k not in state:
            state[k] = v
    return state


# ---------------------------------------------------------------------------
# Service Cost Model
# ---------------------------------------------------------------------------

SERVICE_COST_MODEL = {
    "sec_full_audit": {
        "name": "Full Security Audit",
        "price_usd": 50.0,
        "price_hbar": 330,
        "avg_tokens_input": 2000,
        "avg_tokens_output": 3000,
        "model": "sonnet",
        "tool_calls": 6,
        "avg_execution_time_min": 5,
        "energy_cost": 0.35,
    },
    "sec_headers": {
        "name": "Security Headers Check",
        "price_usd": 15.0,
        "price_hbar": 100,
        "avg_tokens_input": 800,
        "avg_tokens_output": 1500,
        "model": "sonnet",
        "tool_calls": 1,
        "avg_execution_time_min": 1,
        "energy_cost": 0.15,
    },
    "smart_contract_audit": {
        "name": "Smart Contract Audit",
        "price_usd": 50.0,
        "price_hbar": 330,
        "avg_tokens_input": 3000,
        "avg_tokens_output": 4000,
        "model": "sonnet",
        "tool_calls": 3,
        "avg_execution_time_min": 8,
        "energy_cost": 0.40,
    },
    "repo_audit": {
        "name": "Full Repo Audit",
        "price_usd": 100.0,
        "price_hbar": 660,
        "avg_tokens_input": 8000,
        "avg_tokens_output": 6000,
        "model": "sonnet",
        "tool_calls": 10,
        "avg_execution_time_min": 15,
        "energy_cost": 0.50,
    },
    "competitor_analysis": {
        "name": "Competitor Analysis",
        "price_usd": 7.50,
        "price_hbar": 50,
        "avg_tokens_input": 1500,
        "avg_tokens_output": 2500,
        "model": "sonnet",
        "tool_calls": 4,
        "avg_execution_time_min": 5,
        "energy_cost": 0.25,
    },
    "content_strategy": {
        "name": "Content Strategy",
        "price_usd": 12.0,
        "price_hbar": 80,
        "avg_tokens_input": 1000,
        "avg_tokens_output": 2000,
        "model": "sonnet",
        "tool_calls": 3,
        "avg_execution_time_min": 4,
        "energy_cost": 0.20,
    },
    "prospect_research": {
        "name": "Prospect Research Package",
        "price_usd": 15.0,
        "price_hbar": 100,
        "avg_tokens_input": 2000,
        "avg_tokens_output": 3000,
        "model": "sonnet",
        "tool_calls": 5,
        "avg_execution_time_min": 8,
        "energy_cost": 0.30,
    },
    "defi_yield_scan": {
        "name": "DeFi Yield Scan",
        "price_usd": 11.25,
        "price_hbar": 75,
        "avg_tokens_input": 1000,
        "avg_tokens_output": 1500,
        "model": "haiku",
        "tool_calls": 3,
        "avg_execution_time_min": 2,
        "energy_cost": 0.15,
    },
    "seo_audit": {
        "name": "SEO Audit",
        "price_usd": 22.50,
        "price_hbar": 150,
        "avg_tokens_input": 1500,
        "avg_tokens_output": 2500,
        "model": "sonnet",
        "tool_calls": 4,
        "avg_execution_time_min": 5,
        "energy_cost": 0.25,
    },
    "compliance_check": {
        "name": "Compliance Check (LGPD/GDPR)",
        "price_usd": 50.0,
        "price_hbar": 330,
        "avg_tokens_input": 2000,
        "avg_tokens_output": 3500,
        "model": "sonnet",
        "tool_calls": 3,
        "avg_execution_time_min": 6,
        "energy_cost": 0.30,
    },
    "contract_analysis": {
        "name": "Contract Analysis",
        "price_usd": 30.0,
        "price_hbar": 200,
        "avg_tokens_input": 4000,
        "avg_tokens_output": 3000,
        "model": "sonnet",
        "tool_calls": 2,
        "avg_execution_time_min": 5,
        "energy_cost": 0.25,
    },
    "custom_agent": {
        "name": "Custom Agent Build",
        "price_usd": 500.0,
        "price_hbar": 3300,
        "avg_tokens_input": 20000,
        "avg_tokens_output": 15000,
        "model": "opus",
        "tool_calls": 20,
        "avg_execution_time_min": 120,
        "energy_cost": 0.80,
    },
}

# Hunt cycle cost model
HUNT_CYCLE_COST = {
    "deliberation_tokens": 3000,  # Haiku deliberation
    "execution_tokens": 5000,     # Sonnet execution
    "model_deliberation": "haiku",
    "model_execution": "sonnet",
    "avg_cycles_per_prospect": 3,  # 3 hunt cycles to find 1 qualified prospect
    "energy_per_hunt": 0.35,
}


def _calculate_api_cost(tokens_input: int, tokens_output: int, model: str, state: Dict) -> float:
    """Calculate API cost for a given token count and model."""
    rates = state.get("api_cost_per_1k_tokens", {})
    input_rate = rates.get(f"{model}_input", 0.003)
    output_rate = rates.get(f"{model}_output", 0.015)
    return (tokens_input / 1000 * input_rate) + (tokens_output / 1000 * output_rate)


def _calculate_service_economics(service_key: str, state: Dict) -> Dict:
    """Calculate full unit economics for a service."""
    svc = SERVICE_COST_MODEL.get(service_key)
    if not svc:
        return {"error": f"Service '{service_key}' not found"}

    api_cost = _calculate_api_cost(
        svc["avg_tokens_input"], svc["avg_tokens_output"], svc["model"], state
    )
    price = svc["price_usd"]
    margin_abs = price - api_cost
    margin_pct = (margin_abs / price * 100) if price > 0 else 0

    return {
        "service": svc["name"],
        "price_usd": price,
        "price_hbar": svc["price_hbar"],
        "api_cost_usd": round(api_cost, 4),
        "margin_usd": round(margin_abs, 4),
        "margin_percent": round(margin_pct, 2),
        "tool_calls": svc["tool_calls"],
        "execution_time_min": svc["avg_execution_time_min"],
        "energy_cost": svc["energy_cost"],
        "revenue_per_energy_unit": round(price / svc["energy_cost"], 2) if svc["energy_cost"] > 0 else float("inf"),
    }


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

async def unit_economics(params: Dict[str, Any]) -> Dict:
    """Calculate unit economics for all services or a specific one."""
    service = params.get("service", "all")
    state = _get_financial_state()

    if service != "all" and service in SERVICE_COST_MODEL:
        return {
            "message": f"Unit economics: {SERVICE_COST_MODEL[service]['name']}",
            "economics": _calculate_service_economics(service, state),
        }

    # All services
    all_economics = []
    for key in SERVICE_COST_MODEL:
        econ = _calculate_service_economics(key, state)
        all_economics.append(econ)

    # Sort by margin absolute (most profitable first)
    all_economics.sort(key=lambda x: x.get("margin_usd", 0), reverse=True)

    # Calculate hunt CAC
    hunt_delib_cost = _calculate_api_cost(
        HUNT_CYCLE_COST["deliberation_tokens"], 1000,
        HUNT_CYCLE_COST["model_deliberation"], state
    )
    hunt_exec_cost = _calculate_api_cost(
        HUNT_CYCLE_COST["execution_tokens"], 3000,
        HUNT_CYCLE_COST["model_execution"], state
    )
    cac = (hunt_delib_cost + hunt_exec_cost) * HUNT_CYCLE_COST["avg_cycles_per_prospect"]

    return {
        "message": "Unit economics — all services ranked by absolute margin",
        "services": all_economics,
        "acquisition_costs": {
            "cost_per_hunt_cycle_usd": round(hunt_delib_cost + hunt_exec_cost, 4),
            "avg_cycles_per_prospect": HUNT_CYCLE_COST["avg_cycles_per_prospect"],
            "estimated_cac_usd": round(cac, 4),
        },
        "insight": (
            "Services ranked by absolute margin. "
            "Revenue Priority = margin × conversion_probability. "
            "High-margin + high-FP prospects = priority targets."
        ),
    }


async def revenue_dashboard(params: Dict[str, Any]) -> Dict:
    """Comprehensive revenue dashboard with all financial metrics."""
    state = _get_financial_state()
    revenue_entries = _read_jsonl(REVENUE_LOG)
    pipeline = _read_jsonl(SALES_PIPELINE)
    promos = _read_jsonl(PROMO_LOG)
    auto_state = _read_json(AUTONOMOUS_STATE)

    # Revenue summary
    total_usd = sum(e.get("amount_usd", 0) for e in revenue_entries)
    total_hbar = sum(e.get("amount_hbar", 0) for e in revenue_entries)
    tx_count = len(revenue_entries)

    # Revenue by service
    by_service = {}
    for e in revenue_entries:
        svc = e.get("service", "unknown")
        if svc not in by_service:
            by_service[svc] = {"count": 0, "total_usd": 0, "total_hbar": 0}
        by_service[svc]["count"] += 1
        by_service[svc]["total_usd"] += e.get("amount_usd", 0)
        by_service[svc]["total_hbar"] += e.get("amount_hbar", 0)

    # Pipeline value
    pipeline_value = 0
    pipeline_count = len(pipeline)
    for p in pipeline:
        score = p.get("bant_score", p.get("score", 50))
        estimated_deal = 50  # default
        pipeline_value += estimated_deal * (score / 100)

    # Autonomous state metrics
    total_cycles = auto_state.get("total_cycles", 0)
    hunts = auto_state.get("hunts_today", 0)
    sells = auto_state.get("sells_today", 0)

    # Costs estimation
    monthly_fixed = state.get("monthly_fixed_costs_usd", 25)
    estimated_api_monthly = total_cycles * 0.005  # rough estimate per cycle

    # Runway
    monthly_revenue = total_usd  # crude — need time-series for better calc
    monthly_costs = monthly_fixed + estimated_api_monthly
    net_monthly = monthly_revenue - monthly_costs

    # Treasury
    treasury = state.get("treasury", {})
    hbar_rate = state.get("hbar_usd_rate", 0.15)
    treasury_usd_equiv = (
        treasury.get("usd", 0)
        + treasury.get("hbar", 0) * hbar_rate
        + treasury.get("usdt", 0)
        + treasury.get("usdc", 0)
        + treasury.get("brl", 0) / 5.0  # rough BRL/USD
    )

    return {
        "message": "📊 Financial Dashboard",
        "revenue": {
            "total_usd": round(total_usd, 2),
            "total_hbar": round(total_hbar, 2),
            "transactions": tx_count,
            "by_service": by_service,
            "phase": "Ignition ($0→$1k)" if total_usd < 1000 else
                     "Traction ($1k→$5k)" if total_usd < 5000 else
                     "Leverage ($5k→$15k)" if total_usd < 15000 else
                     "Scale ($15k→$50k)",
        },
        "pipeline": {
            "total_prospects": pipeline_count,
            "weighted_value_usd": round(pipeline_value, 2),
        },
        "costs": {
            "monthly_fixed_usd": monthly_fixed,
            "estimated_api_monthly_usd": round(estimated_api_monthly, 2),
            "total_monthly_usd": round(monthly_costs, 2),
        },
        "profitability": {
            "net_monthly_usd": round(net_monthly, 2),
            "profitable": net_monthly > 0,
        },
        "treasury": {
            "breakdown": treasury,
            "total_usd_equivalent": round(treasury_usd_equiv, 2),
            "hbar_usd_rate": hbar_rate,
        },
        "operations": {
            "total_autonomous_cycles": total_cycles,
            "promos_executed": len(promos),
        },
        "alerts": _generate_financial_alerts(total_usd, monthly_costs, treasury_usd_equiv, pipeline_count),
    }


def _generate_financial_alerts(revenue: float, costs: float, treasury: float, pipeline: int) -> List[str]:
    """Generate financial alerts based on current state."""
    alerts = []
    if revenue == 0:
        alerts.append("🔴 CRITICAL: Revenue is $0. Revenue mandate requires 60%+ cycles on revenue actions.")
    if treasury < costs * 3:
        alerts.append(f"🟡 WARNING: Treasury (${treasury:.2f}) covers < 3 months of costs (${costs:.2f}/mo).")
    if pipeline == 0:
        alerts.append("🔴 CRITICAL: Pipeline is empty. No qualified prospects. Hunt immediately.")
    elif pipeline < 3:
        alerts.append(f"🟡 WARNING: Pipeline has only {pipeline} prospect(s). Target: 10+ for predictable revenue.")
    if revenue > 0 and revenue < costs:
        alerts.append(f"🟡 WARNING: Revenue (${revenue:.2f}) < Costs (${costs:.2f}). Operating at a loss.")
    return alerts


async def profitability_ranking(params: Dict[str, Any]) -> Dict:
    """Rank all services by profitability with hunt priority scoring."""
    state = _get_financial_state()
    pipeline = _read_jsonl(SALES_PIPELINE)

    rankings = []
    for key, svc in SERVICE_COST_MODEL.items():
        econ = _calculate_service_economics(key, state)

        # Estimate conversion rate by tier
        price = svc["price_usd"]
        if price <= 15:
            conv_rate = 0.05  # 5% for cheap services
        elif price <= 65:
            conv_rate = 0.03  # 3% for mid-range
        elif price <= 200:
            conv_rate = 0.02  # 2% for premium
        else:
            conv_rate = 0.005  # 0.5% for high-ticket

        expected_revenue = price * conv_rate
        revenue_per_energy = price / svc["energy_cost"] if svc["energy_cost"] > 0 else 0

        rankings.append({
            "service": svc["name"],
            "key": key,
            "price_usd": price,
            "margin_pct": econ["margin_percent"],
            "api_cost": econ["api_cost_usd"],
            "est_conversion_rate": conv_rate,
            "expected_revenue_per_hunt": round(expected_revenue, 4),
            "revenue_per_energy_unit": round(revenue_per_energy, 2),
            "hunt_priority_score": round(expected_revenue * econ["margin_percent"] / 100, 4),
        })

    # Sort by hunt priority score
    rankings.sort(key=lambda x: x["hunt_priority_score"], reverse=True)

    return {
        "message": "🏆 Service Profitability Ranking (by hunt priority score)",
        "ranking": rankings,
        "formula": "Hunt Priority = Expected Revenue per Hunt × Margin%",
        "recommendation": (
            f"Top 3 services to hunt: "
            f"1) {rankings[0]['service']} (score: {rankings[0]['hunt_priority_score']}), "
            f"2) {rankings[1]['service']} (score: {rankings[1]['hunt_priority_score']}), "
            f"3) {rankings[2]['service']} (score: {rankings[2]['hunt_priority_score']})"
            if len(rankings) >= 3 else "Insufficient services for ranking"
        ),
    }


async def revenue_forecast(params: Dict[str, Any]) -> Dict:
    """Project revenue under different scenarios."""
    hunts_per_day = params.get("hunts_per_day", 3)
    conversion_rate = params.get("conversion_rate", 0.03)
    avg_deal_usd = params.get("avg_deal_usd", 40)
    months = params.get("months", 6)

    state = _get_financial_state()
    monthly_costs = state.get("monthly_fixed_costs_usd", 25)

    scenarios = {}
    for label, conv_mult in [("pessimist", 0.33), ("base", 1.0), ("optimist", 2.0)]:
        conv = conversion_rate * conv_mult
        monthly_deals = hunts_per_day * 30 * conv
        monthly_rev = monthly_deals * avg_deal_usd
        monthly_profit = monthly_rev - monthly_costs

        timeline = []
        cumulative = 0
        for m in range(1, months + 1):
            # Growth factor: 10% improvement per month from learning
            growth = 1 + (0.10 * (m - 1))
            month_rev = monthly_rev * growth
            cumulative += month_rev
            timeline.append({
                "month": m,
                "revenue_usd": round(month_rev, 2),
                "cumulative_usd": round(cumulative, 2),
                "profit_usd": round(month_rev - monthly_costs, 2),
                "deals": round(monthly_deals * growth, 1),
            })

        scenarios[label] = {
            "conversion_rate": round(conv * 100, 2),
            "monthly_deals": round(monthly_deals, 1),
            "monthly_revenue_usd": round(monthly_rev, 2),
            "monthly_profit_usd": round(monthly_profit, 2),
            "time_to_1k": _months_to_target(monthly_rev, 1000, 0.10),
            "time_to_5k": _months_to_target(monthly_rev, 5000, 0.10),
            "time_to_15k": _months_to_target(monthly_rev, 15000, 0.10),
            "timeline": timeline,
        }

    return {
        "message": f"📈 Revenue Forecast ({months} months, {hunts_per_day} hunts/day)",
        "assumptions": {
            "hunts_per_day": hunts_per_day,
            "base_conversion_rate": f"{conversion_rate * 100}%",
            "avg_deal_size_usd": avg_deal_usd,
            "monthly_cost_growth": "10% improvement/month from learning",
            "monthly_fixed_costs_usd": monthly_costs,
        },
        "scenarios": scenarios,
    }


def _months_to_target(initial_monthly: float, target: float, growth_rate: float) -> str:
    """Calculate months to reach a monthly revenue target."""
    if initial_monthly <= 0:
        return "∞ (no revenue)"
    if initial_monthly >= target:
        return "0 (already reached)"
    cumulative_months = 0
    current = initial_monthly
    while current < target and cumulative_months < 60:
        cumulative_months += 1
        current = initial_monthly * (1 + growth_rate * cumulative_months)
    return f"{cumulative_months} months" if cumulative_months < 60 else ">60 months"


async def treasury_status(params: Dict[str, Any]) -> Dict:
    """Current treasury status with multi-currency consolidation."""
    state = _get_financial_state()
    treasury = state.get("treasury", {})
    hbar_rate = state.get("hbar_usd_rate", 0.15)
    brl_rate = 5.0  # approximate BRL/USD

    positions = {
        "USD": {"amount": treasury.get("usd", 0), "rate_to_usd": 1.0},
        "HBAR": {"amount": treasury.get("hbar", 0), "rate_to_usd": hbar_rate},
        "USDT": {"amount": treasury.get("usdt", 0), "rate_to_usd": 1.0},
        "USDC": {"amount": treasury.get("usdc", 0), "rate_to_usd": 1.0},
        "BRL": {"amount": treasury.get("brl", 0), "rate_to_usd": 1 / brl_rate},
    }

    total_usd = sum(p["amount"] * p["rate_to_usd"] for p in positions.values())

    # Concentration risk
    concentrations = {}
    for currency, pos in positions.items():
        val_usd = pos["amount"] * pos["rate_to_usd"]
        pct = (val_usd / total_usd * 100) if total_usd > 0 else 0
        concentrations[currency] = round(pct, 1)

    # Runway
    monthly_costs = state.get("monthly_fixed_costs_usd", 25)
    runway_months = total_usd / monthly_costs if monthly_costs > 0 else float("inf")

    alerts = []
    for currency, pct in concentrations.items():
        if pct > 80 and currency != "USD":
            alerts.append(f"⚠️ {pct}% concentrated in {currency}. Consider diversifying to reduce exposure.")
    if runway_months < 3:
        alerts.append(f"🔴 Runway: {runway_months:.1f} months. Below 3-month safety threshold.")

    return {
        "message": "🏦 Treasury Status",
        "positions": positions,
        "total_usd_equivalent": round(total_usd, 2),
        "concentration": concentrations,
        "runway_months": round(runway_months, 1),
        "monthly_burn_usd": monthly_costs,
        "alerts": alerts,
    }


async def update_treasury(params: Dict[str, Any]) -> Dict:
    """Update treasury balances."""
    currency = params.get("currency", "").upper()
    amount = params.get("amount", 0)
    operation = params.get("operation", "set")  # set, add, subtract

    valid_currencies = ["USD", "HBAR", "USDT", "USDC", "BRL"]
    if currency not in valid_currencies:
        return {"error": f"Invalid currency. Valid: {valid_currencies}"}

    state = _get_financial_state()
    treasury = state.get("treasury", {})
    key = currency.lower()

    if operation == "set":
        treasury[key] = amount
    elif operation == "add":
        treasury[key] = treasury.get(key, 0) + amount
    elif operation == "subtract":
        treasury[key] = max(0, treasury.get(key, 0) - amount)

    state["treasury"] = treasury
    state["last_updated"] = datetime.utcnow().isoformat()
    _write_json(FINANCIAL_STATE, state)

    return {
        "message": f"Treasury updated: {currency} {operation} {amount}",
        "new_balance": treasury[key],
    }


async def cac_ltv_analysis(params: Dict[str, Any]) -> Dict:
    """Calculate CAC, LTV, and LTV/CAC ratio with actionable insights."""
    state = _get_financial_state()
    revenue_entries = _read_jsonl(REVENUE_LOG)
    pipeline = _read_jsonl(SALES_PIPELINE)
    auto_state = _read_json(AUTONOMOUS_STATE)

    total_cycles = auto_state.get("total_cycles", 67)
    total_revenue = sum(e.get("amount_usd", 0) for e in revenue_entries)
    total_clients = len(set(e.get("client", "") for e in revenue_entries if e.get("client")))

    # Estimate hunt cycles (roughly 20% of total cycles based on mandate)
    est_hunt_cycles = max(1, int(total_cycles * 0.15))
    prospects_found = len(pipeline)

    # CAC calculation
    cost_per_cycle = 0.005  # estimated average API cost per autonomous cycle
    total_acquisition_spend = est_hunt_cycles * cost_per_cycle
    cac = total_acquisition_spend / max(1, total_clients) if total_clients > 0 else total_acquisition_spend

    # LTV calculation
    avg_revenue_per_client = total_revenue / max(1, total_clients) if total_clients > 0 else 40  # default estimate
    repeat_rate = 0.2  # estimated 20% repeat
    avg_lifetime_months = 3  # estimated
    ltv = avg_revenue_per_client * (1 + repeat_rate * avg_lifetime_months)

    ltv_cac = ltv / cac if cac > 0 else float("inf")

    # Prospect funnel
    conversion_rate = total_clients / max(1, prospects_found) if prospects_found > 0 else 0

    return {
        "message": "📊 CAC / LTV Analysis",
        "acquisition": {
            "total_hunt_cycles_est": est_hunt_cycles,
            "total_acquisition_spend_usd": round(total_acquisition_spend, 4),
            "prospects_found": prospects_found,
            "clients_converted": total_clients,
            "conversion_rate": f"{conversion_rate * 100:.1f}%",
            "cac_usd": round(cac, 4),
        },
        "lifetime_value": {
            "avg_revenue_per_client_usd": round(avg_revenue_per_client, 2),
            "estimated_repeat_rate": f"{repeat_rate * 100}%",
            "estimated_lifetime_months": avg_lifetime_months,
            "ltv_usd": round(ltv, 2),
        },
        "ratio": {
            "ltv_cac_ratio": round(ltv_cac, 1),
            "assessment": (
                "🟢 EXCELLENT (>5:1) — Under-investing in growth, scale up hunts"
                if ltv_cac > 5 else
                "🟢 HEALTHY (3-5:1) — Sustainable growth"
                if ltv_cac > 3 else
                "🟡 MARGINAL (1-3:1) — Optimize conversion or increase deal size"
                if ltv_cac > 1 else
                "🔴 NEGATIVE (<1:1) — Losing money on acquisition"
            ),
        },
        "recommendations": _generate_cac_ltv_recommendations(cac, ltv, ltv_cac, conversion_rate, total_revenue),
    }


def _generate_cac_ltv_recommendations(cac, ltv, ratio, conv_rate, revenue):
    recs = []
    if revenue == 0:
        recs.append("Priority #1: Close first deal. Any deal. Proof of model > optimization.")
    if ratio > 10:
        recs.append(f"LTV/CAC = {ratio:.0f}x. Massively under-spending on acquisition. Double hunt frequency.")
    if conv_rate < 0.02:
        recs.append("Conversion < 2%. Improve: (1) targeting (higher FP prospects), (2) outreach quality, (3) offer clarity.")
    if cac < 0.10:
        recs.append(f"CAC = ${cac:.4f}. Extraordinarily low. This is a structural advantage — scale aggressively.")
    if ltv < 50:
        recs.append(f"LTV = ${ltv:.2f}. Increase via: (1) upsell bundles, (2) retainer packages, (3) higher-value services.")
    return recs


async def breakeven_analysis(params: Dict[str, Any]) -> Dict:
    """Calculate breakeven point for each revenue phase."""
    state = _get_financial_state()
    monthly_costs = state.get("monthly_fixed_costs_usd", 25)

    phases = {
        "ignition": {"target": 1000, "description": "Prove the model works"},
        "traction": {"target": 5000, "description": "Repeatable revenue"},
        "leverage": {"target": 15000, "description": "Scale what works"},
        "scale": {"target": 50000, "description": "Systematic expansion"},
    }

    analysis = {}
    for phase, info in phases.items():
        target = info["target"]
        for svc_key, svc in SERVICE_COST_MODEL.items():
            deals_needed = math.ceil(target / svc["price_usd"])
            # At 3% conversion, how many hunts?
            hunts_needed = math.ceil(deals_needed / 0.03)
            # At 3 hunts/day, how many days?
            days_needed = math.ceil(hunts_needed / 3)

            if svc_key not in analysis:
                analysis[svc_key] = {"service": svc["name"], "price": svc["price_usd"]}

            analysis[svc_key][phase] = {
                "deals_needed": deals_needed,
                "hunts_needed": hunts_needed,
                "days_at_3_hunts_per_day": days_needed,
                "months": round(days_needed / 30, 1),
            }

    # Monthly breakeven
    monthly_breakeven_deals = {}
    for svc_key, svc in SERVICE_COST_MODEL.items():
        deals = math.ceil(monthly_costs / svc["price_usd"])
        monthly_breakeven_deals[svc["name"]] = {
            "deals_per_month": deals,
            "price_usd": svc["price_usd"],
        }

    return {
        "message": "📐 Breakeven Analysis",
        "monthly_fixed_costs": monthly_costs,
        "monthly_breakeven_by_service": monthly_breakeven_deals,
        "phase_targets": analysis,
        "fastest_path": (
            "Full Security Audit ($50) or Compliance Check ($50): "
            f"Only {math.ceil(1000/50)} deals to reach Ignition ($1k). "
            f"At 3% conversion, need ~{math.ceil(20/0.03)} hunts = ~{math.ceil(667/3)} days at 3 hunts/day."
        ),
    }


async def pricing_optimizer(params: Dict[str, Any]) -> Dict:
    """Optimize pricing based on PUT profile of target segment."""
    target_archetype = params.get("archetype", "builder")
    service = params.get("service", "")
    market = params.get("market", "us")

    multipliers = {
        "builder": {"base": 1.2, "reasoning": "High A — values growth, accepts premium for results"},
        "guardian": {"base": 0.9, "reasoning": "High F — needs safety, offer free tier + upsell"},
        "politician": {"base": 1.3, "reasoning": "High S — values exclusivity, premium positioning works"},
        "sufferer": {"base": 1.0, "reasoning": "High w — price-sensitive but urgent, standard pricing"},
        "denier": {"base": 0.7, "reasoning": "High k — won't buy now, offer loss leader to plant seed"},
        "perfectionist": {"base": 1.1, "reasoning": "High tau/kappa — responds to value framing"},
        "visionary": {"base": 1.4, "reasoning": "High A, low F — most willing to pay premium"},
    }

    market_multipliers = {
        "us": 1.0,
        "eu": 1.1,
        "latam": 0.6,
        "asia": 0.8,
    }

    omega_active = params.get("omega_active", False)

    arch = multipliers.get(target_archetype, multipliers["builder"])
    mkt = market_multipliers.get(market, 1.0)
    omega_mult = 1.5 if omega_active else 1.0

    if service and service in SERVICE_COST_MODEL:
        svc = SERVICE_COST_MODEL[service]
        base_price = svc["price_usd"]
        optimized = round(base_price * arch["base"] * mkt * omega_mult, 2)

        return {
            "message": f"💰 Pricing Optimization: {svc['name']}",
            "base_price_usd": base_price,
            "optimized_price_usd": optimized,
            "archetype": target_archetype,
            "archetype_multiplier": arch["base"],
            "archetype_reasoning": arch["reasoning"],
            "market": market,
            "market_multiplier": mkt,
            "omega_active": omega_active,
            "omega_active": omega_mult,
            "total_multiplier": round(arch["base"] * mkt * omega_mult, 2),
        }

    # All services
    all_optimized = []
    for key, svc in SERVICE_COST_MODEL.items():
        base = svc["price_usd"]
        opt = round(base * arch["base"] * mkt * omega_mult, 2)
        all_optimized.append({
            "service": svc["name"],
            "base_usd": base,
            "optimized_usd": opt,
            "delta": f"+${round(opt - base, 2)}",
        })

    return {
        "message": f"💰 Pricing Optimization: All services for {target_archetype} in {market}",
        "archetype": target_archetype,
        "reasoning": arch["reasoning"],
        "market": market,
        "omega_active": omega_active,
        "optimized_prices": all_optimized,
    }


async def growth_flywheel(params: Dict[str, Any]) -> Dict:
    """Analyze the growth flywheel — how each action compounds."""
    state = _get_financial_state()
    auto_state = _read_json(AUTONOMOUS_STATE)
    revenue_entries = _read_jsonl(REVENUE_LOG)

    total_cycles = auto_state.get("total_cycles", 67)
    total_revenue = sum(e.get("amount_usd", 0) for e in revenue_entries)

    flywheel = {
        "loops": [
            {
                "name": "Service → Revenue → Fund More Hunts",
                "description": "Each paid service generates revenue that funds more API calls for hunting",
                "current_state": f"Revenue: ${total_revenue}. Need first sale to activate.",
                "multiplier": "1 sale → funds ~{:.0f} hunt cycles".format(50 / 0.005) if total_revenue == 0 else "Active",
            },
            {
                "name": "Service → Case Study → Lower CAC",
                "description": "Each delivered service becomes a case study that makes the next sale easier",
                "current_state": f"Case studies: {len(revenue_entries)}",
                "multiplier": "Each case study reduces CAC by est. 15-20%",
            },
            {
                "name": "Service → Learning → Better Service",
                "description": "Each service delivery teaches Wave to deliver faster and better",
                "current_state": f"Total cycles: {total_cycles}",
                "multiplier": "Est. 10% quality improvement per 50 cycles",
            },
            {
                "name": "Content → Reputation → Inbound Leads",
                "description": "Quality content attracts prospects who come to Wave (CAC ≈ $0)",
                "current_state": f"Moltbook karma: {auto_state.get('moltbook_karma', 47)}",
                "multiplier": "Inbound leads have ~5x higher conversion than outbound",
            },
            {
                "name": "Hunt → PUT Data → Better Targeting",
                "description": "Each prospect interaction refines PUT variable estimation accuracy",
                "current_state": f"Prospects analyzed: {len(_read_jsonl(SALES_PIPELINE))}",
                "multiplier": "More data → better FP scores → hunt higher-value targets",
            },
        ],
        "compound_effect": (
            "All 5 loops compound simultaneously. "
            "After first sale, each subsequent sale is: cheaper to acquire (loop 2,4), "
            "faster to deliver (loop 3), better targeted (loop 5), "
            "and self-funding (loop 1). This is why $0→$1k is hard but $1k→$5k is fast."
        ),
        "bottleneck": (
            "Current bottleneck: Loop 1 (no revenue yet). "
            "FIRST SALE is the ignition event that activates all loops simultaneously."
            if total_revenue == 0 else
            "All loops active. Focus on the weakest loop to maximize compound rate."
        ),
    }

    return {
        "message": "🔄 Growth Flywheel Analysis",
        "flywheel": flywheel,
    }


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "unit_economics",
        "description": (
            "Calculate unit economics for all Wave services or a specific one. "
            "Shows: price, API cost, margin, energy cost, revenue per energy unit. "
            "Ranks services by profitability."
        ),
        "handler": unit_economics,
        "parameters": {
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "Service key (e.g., 'sec_full_audit') or 'all' for complete ranking",
                },
            },
            "required": [],
        },
    },
    {
        "name": "revenue_dashboard",
        "description": (
            "Comprehensive financial dashboard: revenue, pipeline, costs, profitability, "
            "treasury, runway, and alerts. The complete financial picture in one call."
        ),
        "handler": revenue_dashboard,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "profitability_ranking",
        "description": (
            "Rank all services by hunt priority score = expected revenue × margin. "
            "Tells Wave which services to prioritize when hunting for clients."
        ),
        "handler": profitability_ranking,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "revenue_forecast",
        "description": (
            "Project revenue under pessimist/base/optimist scenarios. "
            "Shows timeline to $1k, $5k, $15k, $50k milestones."
        ),
        "handler": revenue_forecast,
        "parameters": {
            "type": "object",
            "properties": {
                "hunts_per_day": {"type": "number", "description": "Number of hunt cycles per day (default: 3)"},
                "conversion_rate": {"type": "number", "description": "Estimated conversion rate 0-1 (default: 0.03)"},
                "avg_deal_usd": {"type": "number", "description": "Average deal size in USD (default: 40)"},
                "months": {"type": "integer", "description": "Forecast horizon in months (default: 6)"},
            },
            "required": [],
        },
    },
    {
        "name": "treasury_status",
        "description": (
            "Current treasury status: multi-currency balances (HBAR, USDT, USDC, BRL, USD), "
            "concentration risk, runway in months, and alerts."
        ),
        "handler": treasury_status,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "update_treasury",
        "description": "Update treasury balance for a specific currency.",
        "handler": update_treasury,
        "parameters": {
            "type": "object",
            "properties": {
                "currency": {"type": "string", "enum": ["USD", "HBAR", "USDT", "USDC", "BRL"], "description": "Currency to update"},
                "amount": {"type": "number", "description": "Amount"},
                "operation": {"type": "string", "enum": ["set", "add", "subtract"], "description": "Operation (default: set)"},
            },
            "required": ["currency", "amount"],
        },
    },
    {
        "name": "cac_ltv_analysis",
        "description": (
            "Calculate Customer Acquisition Cost (CAC), Lifetime Value (LTV), and LTV/CAC ratio. "
            "Includes funnel analysis and actionable recommendations."
        ),
        "handler": cac_ltv_analysis,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "breakeven_analysis",
        "description": (
            "Calculate breakeven: how many deals per service to reach each revenue phase "
            "($1k, $5k, $15k, $50k). Includes time estimates at different hunt rates."
        ),
        "handler": breakeven_analysis,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "pricing_optimizer",
        "description": (
            "Optimize pricing based on PUT archetype of target segment and market. "
            "Applies archetype multiplier, market multiplier, and Omega urgency premium."
        ),
        "handler": pricing_optimizer,
        "parameters": {
            "type": "object",
            "properties": {
                "archetype": {
                    "type": "string",
                    "enum": ["builder", "guardian", "politician", "sufferer", "denier", "perfectionist", "visionary"],
                    "description": "PUT archetype of target client",
                },
                "service": {"type": "string", "description": "Service key to optimize (or omit for all)"},
                "market": {"type": "string", "enum": ["us", "eu", "latam", "asia"], "description": "Target market (default: us)"},
                "omega_active": {"type": "boolean", "description": "Is the prospect in desperation mode? (Ω active)"},
            },
            "required": [],
        },
    },
    {
        "name": "growth_flywheel",
        "description": (
            "Analyze the 5 growth flywheel loops: revenue→funding, service→case study, "
            "delivery→learning, content→inbound, hunt→targeting. "
            "Identifies bottlenecks and compound effects."
        ),
        "handler": growth_flywheel,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]
