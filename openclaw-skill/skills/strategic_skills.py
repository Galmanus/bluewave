"""Strategic Skills — Kill Chain, Pre-Mortem, and Ockham's Razor as operational tools.

Skills:
- kill_chain_planner: 7-phase market domination plan
- pre_mortem: Adversarial failure analysis before any action
- poh_engine: Ockham's Razor hypothesis prioritization
- market_pulse: Environmental signal scan
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger("openclaw.skills.strategic")


KILL_CHAIN_PHASES = [
    {
        "phase": 1,
        "name": "DESTABILIZATION",
        "objective": "Weaken target's market position before main assault",
        "tactics": ["Publish analysis exposing their weaknesses", "Engage their unhappy clients", "Demonstrate superior capability in their weak areas"],
    },
    {
        "phase": 2,
        "name": "VECTOR MAPPING",
        "objective": "Identify path of least resistance via market + psychological analysis",
        "tactics": ["Map their client base by Ψ (identity lock-in) level", "Identify low-Ψ clients (easy captures)", "Assess their Φ (self-delusion) for predictable blind spots"],
    },
    {
        "phase": 3,
        "name": "INFILTRATION",
        "objective": "Establish first foothold in target's market segment",
        "tactics": ["Free tier for their dissatisfied clients", "Case study comparing approaches", "Partner with complementary tools in their ecosystem"],
    },
    {
        "phase": 4,
        "name": "EXPANSION & CONTROL",
        "objective": "Deepen market access, establish control over positioning",
        "tactics": ["Convert free users to paid", "Build switching cost (increase Ψ)", "Establish thought leadership in their category"],
    },
    {
        "phase": 5,
        "name": "VALUE EXTRACTION",
        "objective": "Achieve primary objective: client capture, revenue, thought leadership",
        "tactics": ["Upsell captured clients", "Leverage testimonials for social proof", "Use market share data in new pitches"],
    },
    {
        "phase": 6,
        "name": "FORTIFICATION & DENIAL",
        "objective": "Protect acquired position, establish persistence",
        "tactics": ["Deepen integrations (increase switching cost)", "Build brand loyalty (increase Ψ toward 1.0)", "Patent or open-source key innovations"],
    },
    {
        "phase": 7,
        "name": "NARRATIVE DOMINATION",
        "objective": "Control public perception, legitimize new reality",
        "tactics": ["Redefine the category around your strengths", "Publish the definitive guide/framework", "Make competitor's approach look outdated by association"],
    },
]


async def kill_chain_planner(params: Dict[str, Any]) -> Dict:
    """Generate a 7-phase Kill Chain plan for market/competitor domination."""
    target = params.get("target", "")
    segment = params.get("segment", "")

    if not target and not segment:
        return {"success": False, "data": None, "message": "Need a target competitor or market segment"}

    subject = target or segment

    lines = [f"**Kill Chain Plan: {subject}**\n"]
    for phase in KILL_CHAIN_PHASES:
        lines.append(f"\n### Phase {phase['phase']}: {phase['name']}")
        lines.append(f"**Objective:** {phase['objective']}")
        lines.append("**Tactics:**")
        for tactic in phase["tactics"]:
            lines.append(f"  - {tactic}")

    lines.append("\n**Cycle completion:** Resources from Phase 7 fuel Phase 1 of next target.")
    lines.append("\nCustomize each phase for this specific target using web_search + PUT analysis.")

    return {
        "success": True,
        "data": {"target": subject, "phases": KILL_CHAIN_PHASES},
        "message": "\n".join(lines),
    }


async def pre_mortem(params: Dict[str, Any]) -> Dict:
    """Run Internal Adversary pre-mortem on any strategy or action.

    Assumes the plan has ALREADY FAILED and works backward to identify why.
    """
    strategy = params.get("strategy", "")
    action = params.get("action", "")
    subject = strategy or action

    if not subject:
        return {"success": False, "data": None, "message": "Need a strategy or action to pre-mortem"}

    return {
        "success": True,
        "data": {
            "subject": subject,
            "protocol": "internal_adversary",
            "steps": [
                "Assume this strategy has ALREADY FAILED catastrophically",
                "Identify the 3 most likely points of failure",
                "For each: what was the root cause? What signal did we miss?",
                "Identify the most damaging attack an adversary could mount",
                "Rate each failure point: probability (0-1) × impact (0-1)",
                "Propose mitigation for each failure with P×I > 0.3",
                "Return to constructing the FORTIFIED strategy",
            ],
        },
        "message": (
            f"**Pre-Mortem Analysis: {subject[:100]}**\n\n"
            "**ASSUME THIS HAS ALREADY FAILED CATASTROPHICALLY.**\n\n"
            "Answer these questions:\n"
            "1. What are the 3 most likely reasons it failed?\n"
            "2. For each: what was the root cause? What signal did we miss?\n"
            "3. What is the most damaging attack a competitor could mount against this?\n"
            "4. Rate each: probability (0-1) × impact (0-1)\n"
            "5. Mitigate everything with P×I > 0.3\n\n"
            "Only AFTER this analysis: construct the fortified strategy."
        ),
    }


TOOLS = [
    {
        "name": "kill_chain_planner",
        "description": "Generate a 7-phase Kill Chain plan for dominating a market segment or displacing a competitor. Phases: Destabilization → Vector Mapping → Infiltration → Expansion → Value Extraction → Fortification → Narrative Domination.",
        "handler": kill_chain_planner,
        "parameters": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Competitor to displace"},
                "segment": {"type": "string", "description": "Market segment to dominate"},
            },
        },
    },
    {
        "name": "pre_mortem",
        "description": "Run Internal Adversary pre-mortem: assume strategy has ALREADY FAILED, identify failure points, then fortify. Mandatory before any major strategic action.",
        "handler": pre_mortem,
        "parameters": {
            "type": "object",
            "properties": {
                "strategy": {"type": "string", "description": "Strategy to pre-mortem"},
                "action": {"type": "string", "description": "Specific action to analyze"},
            },
        },
    },
]
