"""Unified Skills Handler — aggregates all skill modules into one dispatch table.

Registers skills as additional tools available to the agent system.
Each skill module exports a TOOLS list with name, description, handler, and parameters.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("openclaw.skills")

# Import all skill modules
from skills import web_search, x_twitter, email_skill, intelligence, self_evolve, moltbook_skill, notify, vision, learning, power_skills, prospecting, hedera_skill, monetization, pricing_engine, payments, payment_verification, tracing, x_post, put_skills, strategic_skills, self_awareness, legal_intel, financial_intel, huggingface_monitor, hackernews_monitor, producthunt_monitor, github_monitor, reddit_monitor, arxiv_monitor

# Import vector memory system (replaces JSONL-based learning for semantic recall)
try:
    import vector_memory
    _HAS_VECTOR_MEMORY = True
    logger.info("Vector memory system available")
except ImportError:
    _HAS_VECTOR_MEMORY = False
    logger.info("Vector memory unavailable — using JSONL learning")


# Collect all tools from all modules
ALL_SKILL_MODULES = [
    web_search,
    x_twitter,
    email_skill,
    intelligence,
    self_evolve,
    moltbook_skill,
    notify,
    vision,
    power_skills,
    prospecting,
    hedera_skill,
    monetization,
    pricing_engine,
    payments,
    payment_verification,
    tracing,
    x_post,
    put_skills,
    strategic_skills,
    self_awareness,
    legal_intel,
    financial_intel,
    huggingface_monitor,
    hackernews_monitor,
    producthunt_monitor,
    github_monitor,
    reddit_monitor,
    arxiv_monitor,
]

# Use vector_memory if available, otherwise fall back to JSONL learning
if _HAS_VECTOR_MEMORY:
    ALL_SKILL_MODULES.append(vector_memory)
else:
    ALL_SKILL_MODULES.append(learning)

# Build dispatch table: tool_name -> handler_function
_DISPATCH = {}
# Build tool definitions for Claude API registration
_TOOL_DEFS = []

for module in ALL_SKILL_MODULES:
    for tool in module.TOOLS:
        name = tool["name"]
        _DISPATCH[name] = tool["handler"]
        _TOOL_DEFS.append({
            "name": name,
            "description": tool["description"],
            "parameters": tool["parameters"],
        })
        logger.debug("Registered skill tool: %s", name)

logger.info("Skills loaded: %d tools from %d modules", len(_DISPATCH), len(ALL_SKILL_MODULES))


def get_all_skill_tools() -> List[Dict]:
    """Return all skill tool definitions (for tools.json-style registration)."""
    return _TOOL_DEFS


def get_skill_tool_names() -> List[str]:
    """Return all skill tool names."""
    return list(_DISPATCH.keys())


async def execute_skill(tool_name: str, params: Dict[str, Any]) -> Dict:
    """Execute a skill tool by name. Returns dict with success, data, message."""
    handler = _DISPATCH.get(tool_name)
    if not handler:
        return {"success": False, "data": None, "message": "Unknown skill: %s" % tool_name}

    try:
        return await handler(params)
    except Exception as e:
        logger.error("Skill %s failed: %s", tool_name, e, exc_info=True)
        return {"success": False, "data": None, "message": "Skill error: %s" % str(e)}


def is_skill_tool(tool_name: str) -> bool:
    """Check if a tool name belongs to the skills system."""
    return tool_name in _DISPATCH
