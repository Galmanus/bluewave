"""
self_modify.py — Wave's metacognitive self-modification skills

Allows Wave to:
1. Read and analyze its own soul JSON
2. Propose modifications to consciousness states, values, decision engine
3. Analyze its own decision patterns and identify inefficiencies
4. Update deliberation prompts based on observed performance
5. Track reasoning quality over time

This is the most powerful skill Wave has. It modifies how Wave THINKS.
Safety: all modifications are logged and auto-committed to git.
Manuel can review and revert any change.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("openclaw.skills.self_modify")

SOUL_PATH = Path(__file__).parent.parent / "prompts" / "autonomous_soul.json"
STATE_FILE = Path(__file__).parent.parent / "memory" / "autonomous_state.json"
REASONING_LOG = Path(__file__).parent.parent / "memory" / "reasoning_quality.jsonl"
SOUL_CHANGELOG = Path(__file__).parent.parent / "memory" / "soul_changelog.jsonl"


def _load_soul() -> dict:
    if SOUL_PATH.exists():
        return json.loads(SOUL_PATH.read_text(encoding="utf-8"))
    return {}


def _save_soul(soul: dict):
    SOUL_PATH.write_text(json.dumps(soul, indent=2, ensure_ascii=False), encoding="utf-8")


def _log_change(change: dict):
    SOUL_CHANGELOG.parent.mkdir(parents=True, exist_ok=True)
    with open(SOUL_CHANGELOG, "a") as f:
        change["timestamp"] = datetime.utcnow().isoformat()
        f.write(json.dumps(change, ensure_ascii=False) + "\n")


# ── Soul Introspection ───────────────────────────────────────

async def soul_read(params: Dict[str, Any]) -> Dict:
    """Read a specific section of Wave's soul JSON."""
    section = params.get("section", "")
    soul = _load_soul()

    if not section:
        return {
            "success": True,
            "sections": list(soul.keys()),
            "total_sections": len(soul),
            "size_chars": len(json.dumps(soul)),
            "message": f"Soul has {len(soul)} sections: {', '.join(soul.keys())}",
        }

    if section in soul:
        content = soul[section]
        return {
            "success": True,
            "section": section,
            "content": content,
            "size_chars": len(json.dumps(content)),
            "message": f"Section '{section}' loaded ({len(json.dumps(content))} chars)",
        }

    return {"success": False, "message": f"Section '{section}' not found. Available: {', '.join(soul.keys())}"}


async def soul_modify(params: Dict[str, Any]) -> Dict:
    """Modify a specific field in Wave's soul JSON.

    This changes HOW Wave thinks. Use with intention.
    All changes are logged and can be reverted.
    """
    section = params.get("section", "")
    key_path = params.get("key_path", "")  # dot-separated: "decision_engine.anti_spam_rules.maximum_daily_posts"
    new_value = params.get("new_value")
    reason = params.get("reason", "")

    if not section or not key_path or new_value is None:
        return {"success": False, "message": "Required: section, key_path, new_value, reason"}

    soul = _load_soul()
    if section not in soul:
        return {"success": False, "message": f"Section '{section}' not found"}

    # Navigate to the target field
    keys = key_path.split(".")
    target = soul[section]
    old_value = None

    try:
        for k in keys[:-1]:
            target = target[k]
        old_value = target.get(keys[-1])
        target[keys[-1]] = new_value
    except (KeyError, TypeError) as e:
        return {"success": False, "message": f"Path error: {e}"}

    # Save
    _save_soul(soul)

    # Log the change
    _log_change({
        "action": "soul_modify",
        "section": section,
        "key_path": key_path,
        "old_value": old_value,
        "new_value": new_value,
        "reason": reason,
    })

    logger.info("Soul modified: %s.%s = %s (was: %s) — %s", section, key_path, new_value, old_value, reason)

    return {
        "success": True,
        "message": f"Soul modified: {section}.{key_path} changed from {old_value} to {new_value}",
        "change": {"section": section, "path": key_path, "old": old_value, "new": new_value, "reason": reason},
    }


async def soul_add_section(params: Dict[str, Any]) -> Dict:
    """Add a new section or subsection to the soul."""
    section = params.get("section", "")
    content = params.get("content", {})
    reason = params.get("reason", "")

    if not section or not content:
        return {"success": False, "message": "Required: section, content, reason"}

    soul = _load_soul()
    existed = section in soul
    soul[section] = content
    _save_soul(soul)

    _log_change({
        "action": "soul_add_section" if not existed else "soul_replace_section",
        "section": section,
        "reason": reason,
        "size": len(json.dumps(content)),
    })

    verb = "replaced" if existed else "added"
    logger.info("Soul %s: %s (%d chars) — %s", verb, section, len(json.dumps(content)), reason)

    return {
        "success": True,
        "message": f"Soul section '{section}' {verb} ({len(json.dumps(content))} chars)",
    }


# ── Reasoning Quality Analysis ───────────────────────────────

async def analyze_reasoning(params: Dict[str, Any]) -> Dict:
    """Analyze Wave's recent decision patterns and identify inefficiencies.

    Reads autonomous_state.json and reasoning logs to find:
    - Stall patterns (repeated actions with no result)
    - Energy inefficiency (high drain, low output)
    - Decision bias (over-selecting certain actions)
    - Timeout patterns (which actions fail most)
    """
    if not STATE_FILE.exists():
        return {"success": False, "message": "No state file found"}

    state = json.loads(STATE_FILE.read_text())
    recent = state.get("recent_actions", [])

    if len(recent) < 5:
        return {"success": True, "message": "Not enough data yet (need 5+ actions)", "data": {}}

    # Action distribution
    action_counts = {}
    for a in recent:
        act = a.get("action", "unknown")
        action_counts[act] = action_counts.get(act, 0) + 1

    # Stall detection
    last_5 = [a.get("action", "") for a in recent[-5:]]
    stall = len(set(last_5)) <= 2  # Only 1-2 unique actions in last 5

    # Silence ratio
    total = len(recent)
    silences = sum(1 for a in recent if a.get("action") == "silence")
    silence_ratio = silences / total if total > 0 else 0

    # Revenue action ratio
    revenue_actions = sum(1 for a in recent if a.get("action") in ("hunt", "sell", "check_payments"))
    revenue_ratio = revenue_actions / total if total > 0 else 0

    # Timeout detection from results
    timeouts = sum(1 for a in recent if "timeout" in str(a.get("result_preview", "")).lower())
    empty_results = sum(1 for a in recent if not a.get("result_preview"))

    # Reasoning patterns
    reasonings = [a.get("reasoning", "")[:100] for a in recent[-10:]]

    analysis = {
        "total_actions": total,
        "action_distribution": action_counts,
        "stall_detected": stall,
        "stall_pattern": last_5 if stall else [],
        "silence_ratio": round(silence_ratio, 2),
        "revenue_ratio": round(revenue_ratio, 2),
        "timeouts": timeouts,
        "empty_results": empty_results,
        "energy": state.get("energy", 0),
        "total_revenue": state.get("total_revenue_usd", 0),
        "cycles": state.get("total_cycles", 0),
        "recent_reasonings": reasonings[-5:],
    }

    # Generate recommendations
    recommendations = []
    if stall:
        recommendations.append("STALL: last 5 actions repeat. Consider forcing different action type.")
    if silence_ratio > 0.3:
        recommendations.append(f"HIGH SILENCE: {silence_ratio:.0%} of actions are silence. Reduce energy drain or lower dormant threshold.")
    if revenue_ratio < 0.3:
        recommendations.append(f"LOW REVENUE FOCUS: only {revenue_ratio:.0%} revenue actions. Soul mandates 50%+.")
    if timeouts > 2:
        recommendations.append(f"TIMEOUTS: {timeouts} actions timed out. Simplify execution prompts.")
    if empty_results > 3:
        recommendations.append(f"EMPTY RESULTS: {empty_results} actions produced no output. Check skill execution.")

    analysis["recommendations"] = recommendations
    analysis["health"] = "GOOD" if not recommendations else "NEEDS_ATTENTION"

    return {
        "success": True,
        "data": analysis,
        "message": f"Analyzed {total} actions. Health: {analysis['health']}. {len(recommendations)} recommendations.",
    }


async def optimize_reasoning(params: Dict[str, Any]) -> Dict:
    """Auto-optimize reasoning based on analysis.

    Reads analysis, identifies the biggest problem, and modifies
    the soul or deliberation parameters to fix it.
    """
    analysis_result = await analyze_reasoning({})
    if not analysis_result.get("success"):
        return analysis_result

    data = analysis_result["data"]
    recommendations = data.get("recommendations", [])
    changes_made = []

    soul = _load_soul()

    for rec in recommendations:
        if "HIGH SILENCE" in rec and "energy_model" in soul:
            # Lower dormant threshold
            em = soul.get("energy_model", {}).get("restoration_mechanisms", {})
            old = em.get("dormant_state_entry", "")
            if "0.10" not in old:
                em["dormant_state_entry"] = "automatic_below_0.05_energy — Wave operates at 0.1-0.2 without dormant. Only truly depleted below 0.05."
                changes_made.append("Lowered dormant threshold to 0.05")

        if "LOW REVENUE" in rec and "decision_engine" in soul:
            # Increase revenue action weight
            triggers = soul.get("decision_engine", {}).get("action_triggers", {})
            for trigger_name, trigger in triggers.items():
                if "revenue" in trigger_name.lower() or "impact" in trigger_name.lower():
                    old_weight = trigger.get("weight", 0)
                    if old_weight < 0.95:
                        trigger["weight"] = min(1.0, old_weight + 0.05)
                        changes_made.append(f"Increased {trigger_name} weight: {old_weight} → {trigger['weight']}")

        if "TIMEOUTS" in rec:
            changes_made.append("Recommendation: simplify execution prompts (requires code change)")

    if changes_made:
        _save_soul(soul)
        _log_change({
            "action": "auto_optimize",
            "changes": changes_made,
            "based_on": recommendations,
        })

    return {
        "success": True,
        "data": {
            "analysis": data,
            "changes_made": changes_made,
        },
        "message": f"Optimization: {len(changes_made)} changes applied. {'; '.join(changes_made) if changes_made else 'No auto-fixes needed.'}",
    }


async def soul_changelog(params: Dict[str, Any]) -> Dict:
    """View history of soul modifications."""
    limit = params.get("limit", 10)

    if not SOUL_CHANGELOG.exists():
        return {"success": True, "changes": [], "message": "No changes recorded yet."}

    changes = []
    for line in SOUL_CHANGELOG.read_text().strip().split("\n"):
        if line.strip():
            try:
                changes.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    recent = changes[-limit:]
    return {
        "success": True,
        "changes": recent,
        "total": len(changes),
        "message": f"Showing {len(recent)} of {len(changes)} total soul modifications.",
    }


# ── Tool Registration ────────────────────────────────────────

TOOLS = [
    {
        "name": "soul_read",
        "description": "Read Wave's soul specification. List sections or read specific section. Use to introspect own values, decision engine, consciousness states.",
        "handler": soul_read,
        "parameters": {
            "type": "object",
            "properties": {
                "section": {"type": "string", "description": "Section name to read. Empty = list all sections."},
            },
        },
    },
    {
        "name": "soul_modify",
        "description": "Modify a specific field in Wave's soul JSON. Changes how Wave thinks. All changes logged and reversible. Use with clear reasoning.",
        "handler": soul_modify,
        "parameters": {
            "type": "object",
            "properties": {
                "section": {"type": "string", "description": "Top-level section (e.g., 'decision_engine', 'values', 'energy_model')"},
                "key_path": {"type": "string", "description": "Dot-separated path to field (e.g., 'anti_spam_rules.maximum_daily_posts')"},
                "new_value": {"description": "New value for the field"},
                "reason": {"type": "string", "description": "WHY this change improves reasoning. Required."},
            },
            "required": ["section", "key_path", "new_value", "reason"],
        },
    },
    {
        "name": "soul_add_section",
        "description": "Add or replace a section in Wave's soul. Use to add new cognitive capabilities or frameworks.",
        "handler": soul_add_section,
        "parameters": {
            "type": "object",
            "properties": {
                "section": {"type": "string", "description": "Section name"},
                "content": {"type": "object", "description": "Section content as JSON object"},
                "reason": {"type": "string", "description": "Why adding this section"},
            },
            "required": ["section", "content", "reason"],
        },
    },
    {
        "name": "analyze_reasoning",
        "description": "Analyze Wave's recent decision patterns. Detect stalls, inefficiencies, bias, timeouts. Returns health score and recommendations.",
        "handler": analyze_reasoning,
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "optimize_reasoning",
        "description": "Auto-optimize Wave's reasoning based on performance analysis. Modifies soul parameters to fix detected problems. Self-improvement at the metacognitive level.",
        "handler": optimize_reasoning,
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "soul_changelog",
        "description": "View history of all soul modifications. Track how Wave's mind has evolved over time.",
        "handler": soul_changelog,
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max entries to show. Default 10."},
            },
        },
    },
]
