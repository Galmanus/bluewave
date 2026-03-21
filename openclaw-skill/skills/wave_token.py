"""
wave_token.py — $WAVE Token Management

The first token backed by verifiable autonomous AI labor.
Wave manages its own treasury, tracks revenue backing, and reports token health.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger("openclaw.skills")

# Token constants
WAVE_TOKEN_SUPPLY = 1_000_000_000
WAVE_DECIMALS = 8
TREASURY_PERCENTAGE = 0.20  # 20% of revenue → treasury
WAVE_OPS_PERCENTAGE = 0.10  # 10% → Wave operational fund
MANUEL_PERCENTAGE = 0.70    # 70% → Manuel (operations + profit)
BUYBACK_BURN_RATE = 0.10    # 10% of revenue → quarterly buyback & burn

# State file
STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "wave_token_state.json")


def _load_state() -> Dict:
    """Load or initialize token state."""
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "treasury_balance_usd": 0.0,
            "total_revenue_generated": 0.0,
            "total_actions_performed": 0,
            "tokens_burned": 0,
            "tokens_in_circulation": 0,
            "revenue_log": [],
            "burn_log": [],
            "created": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
        }


def _save_state(state: Dict):
    """Persist token state."""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    state["last_updated"] = datetime.utcnow().isoformat()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


async def wave_token_status(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get current $WAVE token status — treasury, revenue, backing ratio."""
    state = _load_state()

    treasury = state["treasury_balance_usd"]
    total_rev = state["total_revenue_generated"]
    actions = state["total_actions_performed"]
    burned = state["tokens_burned"]
    circulating = WAVE_TOKEN_SUPPLY - burned

    # Backing ratio: treasury USD / circulating tokens
    backing_per_token = treasury / circulating if circulating > 0 else 0

    return {
        "success": True,
        "data": {
            "token": "$WAVE",
            "network": "Hedera (HTS)",
            "total_supply": WAVE_TOKEN_SUPPLY,
            "tokens_burned": burned,
            "circulating_supply": circulating,
            "treasury_usd": round(treasury, 2),
            "total_revenue_generated": round(total_rev, 2),
            "total_actions": actions,
            "backing_per_token_usd": round(backing_per_token, 8),
            "revenue_split": {
                "manuel": f"{MANUEL_PERCENTAGE * 100}%",
                "treasury": f"{TREASURY_PERCENTAGE * 100}%",
                "wave_ops": f"{WAVE_OPS_PERCENTAGE * 100}%",
            },
            "last_updated": state["last_updated"],
        },
        "message": f"$WAVE treasury: ${treasury:.2f} | Backing: ${backing_per_token:.8f}/token | {actions} actions performed",
    }


async def wave_token_log_revenue(params: Dict[str, Any]) -> Dict[str, Any]:
    """Log revenue from an AI action and split to treasury/ops/Manuel."""
    amount = params.get("amount", 0)
    source = params.get("source", "unknown")
    action_id = params.get("action_id", "")
    currency = params.get("currency", "USD")

    if amount <= 0:
        return {"success": False, "message": "Amount must be positive"}

    # Convert BRL to USD estimate
    usd_amount = amount
    if currency == "BRL":
        usd_amount = amount / 5.2  # approximate rate

    state = _load_state()

    # Revenue split
    to_treasury = usd_amount * TREASURY_PERCENTAGE
    to_wave_ops = usd_amount * WAVE_OPS_PERCENTAGE
    to_manuel = usd_amount * MANUEL_PERCENTAGE

    state["treasury_balance_usd"] += to_treasury
    state["total_revenue_generated"] += usd_amount
    state["total_actions_performed"] += 1

    # Log entry
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "amount_original": amount,
        "currency": currency,
        "amount_usd": round(usd_amount, 2),
        "source": source,
        "action_id": action_id,
        "split": {
            "treasury": round(to_treasury, 4),
            "wave_ops": round(to_wave_ops, 4),
            "manuel": round(to_manuel, 4),
        },
    }
    state["revenue_log"].append(entry)

    # Keep last 1000 entries
    if len(state["revenue_log"]) > 1000:
        state["revenue_log"] = state["revenue_log"][-500:]

    _save_state(state)

    return {
        "success": True,
        "data": entry,
        "message": f"Revenue logged: ${usd_amount:.2f} from {source} → Treasury +${to_treasury:.4f} | Wave Ops +${to_wave_ops:.4f} | Manuel +${to_manuel:.4f}",
    }


async def wave_token_burn(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute quarterly buyback and burn. Reduces supply, increases scarcity."""
    state = _load_state()

    # Calculate burn amount from treasury
    burn_budget = state["treasury_balance_usd"] * BUYBACK_BURN_RATE
    if burn_budget < 1.0:
        return {"success": False, "message": f"Treasury too small for burn (${state['treasury_balance_usd']:.2f}). Minimum $10 in treasury required."}

    # Estimate tokens to burn (based on implied price)
    circulating = WAVE_TOKEN_SUPPLY - state["tokens_burned"]
    implied_price = state["treasury_balance_usd"] / circulating if circulating > 0 else 0.000001
    tokens_to_burn = int(burn_budget / implied_price) if implied_price > 0 else 0

    if tokens_to_burn <= 0:
        return {"success": False, "message": "No tokens to burn at current price"}

    # Execute burn
    state["tokens_burned"] += tokens_to_burn
    state["treasury_balance_usd"] -= burn_budget

    burn_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "tokens_burned": tokens_to_burn,
        "burn_budget_usd": round(burn_budget, 2),
        "implied_price": round(implied_price, 8),
        "new_circulating": WAVE_TOKEN_SUPPLY - state["tokens_burned"],
    }
    state["burn_log"].append(burn_entry)

    _save_state(state)

    return {
        "success": True,
        "data": burn_entry,
        "message": f"BURN: {tokens_to_burn:,} $WAVE burned (${burn_budget:.2f}). New supply: {burn_entry['new_circulating']:,}",
    }


async def wave_token_revenue_report(params: Dict[str, Any]) -> Dict[str, Any]:
    """Generate revenue report — total, by source, growth trend."""
    state = _load_state()
    period = params.get("period", "all")

    log = state["revenue_log"]
    if not log:
        return {
            "success": True,
            "data": {"total": 0, "sources": {}, "actions": 0},
            "message": "$WAVE revenue: $0.00. The engine is ready. It needs fuel (API key + clients).",
        }

    # Aggregate by source
    by_source = {}
    total = 0
    for entry in log:
        src = entry.get("source", "unknown")
        amt = entry.get("amount_usd", 0)
        by_source[src] = by_source.get(src, 0) + amt
        total += amt

    # Sort by revenue
    by_source = dict(sorted(by_source.items(), key=lambda x: x[1], reverse=True))

    return {
        "success": True,
        "data": {
            "total_revenue_usd": round(total, 2),
            "treasury_usd": round(state["treasury_balance_usd"], 2),
            "total_actions": state["total_actions_performed"],
            "tokens_burned": state["tokens_burned"],
            "circulating_supply": WAVE_TOKEN_SUPPLY - state["tokens_burned"],
            "revenue_by_source": {k: round(v, 2) for k, v in by_source.items()},
            "backing_per_token": round(state["treasury_balance_usd"] / (WAVE_TOKEN_SUPPLY - state["tokens_burned"]), 8) if state["tokens_burned"] < WAVE_TOKEN_SUPPLY else 0,
        },
        "message": f"$WAVE total revenue: ${total:.2f} | Treasury: ${state['treasury_balance_usd']:.2f} | {state['total_actions_performed']} actions | {state['tokens_burned']:,} tokens burned",
    }


TOOLS = [
    {
        "name": "wave_token_status",
        "description": "Get current $WAVE token status — treasury balance, backing ratio, circulating supply, total revenue. The health dashboard of Wave's wealth.",
        "handler": wave_token_status,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "wave_token_log_revenue",
        "description": "Log revenue from an AI action. Automatically splits: 70% Manuel, 20% treasury ($WAVE backing), 10% Wave ops. Every logged action increases $WAVE's backing.",
        "handler": wave_token_log_revenue,
        "parameters": {
            "type": "object",
            "properties": {
                "amount": {"type": "number", "description": "Revenue amount"},
                "source": {"type": "string", "description": "Revenue source: 'compliance_check', 'subscription', 'security_audit', 'consulting', 'api_access'"},
                "action_id": {"type": "string", "description": "Unique action ID for audit trail"},
                "currency": {"type": "string", "description": "'USD' or 'BRL' (default: USD)", "enum": ["USD", "BRL"]},
            },
            "required": ["amount", "source"],
        },
    },
    {
        "name": "wave_token_burn",
        "description": "Execute quarterly buyback and burn of $WAVE tokens. Uses 10% of treasury to buy back and permanently destroy tokens, reducing supply and increasing scarcity.",
        "handler": wave_token_burn,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "wave_token_revenue_report",
        "description": "Generate $WAVE revenue report — total revenue, breakdown by source, treasury health, burn history, backing ratio. Use to demonstrate Wave's commercial value.",
        "handler": wave_token_revenue_report,
        "parameters": {
            "type": "object",
            "properties": {
                "period": {"type": "string", "description": "'all', 'month', 'week' (default: all)"},
            },
            "required": [],
        },
    },
]
