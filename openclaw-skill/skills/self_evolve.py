"""Self-Evolution — Wave creates new skills for himself at runtime."""

from __future__ import annotations

import importlib
import json
import os
import re
import sys
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("openclaw.skills.evolve")

SKILLS_DIR = Path(__file__).parent


async def create_skill(params: Dict[str, Any]) -> Dict:
    """Create a new skill module at runtime. The skill becomes immediately available.

    The code must define a TOOLS list following the standard format:
    TOOLS = [{"name": "...", "description": "...", "handler": async_func, "parameters": {...}}]
    """
    skill_name = params.get("skill_name", "")
    description = params.get("description", "")
    code = params.get("code", "")

    if not skill_name or not code:
        return {"success": False, "data": None, "message": "Need skill_name and code"}

    # Sanitize name
    safe_name = re.sub(r'[^a-z0-9_]', '_', skill_name.lower())
    file_path = SKILLS_DIR / ("%s.py" % safe_name)

    # Don't overwrite core skills
    protected = {"__init__", "web_search", "x_twitter", "email_skill", "intelligence", "self_evolve"}
    if safe_name in protected:
        return {"success": False, "data": None, "message": "Can't overwrite protected skill: %s" % safe_name}

    # Write the skill file
    header = '"""%s — auto-generated skill by Wave.\n\n%s\n"""\n\n' % (safe_name, description)
    full_code = header + code

    try:
        file_path.write_text(full_code, encoding="utf-8")
        logger.info("Skill file written: %s", file_path)
    except Exception as e:
        return {"success": False, "data": None, "message": "Failed to write skill: %s" % str(e)}

    # Try to import and validate
    try:
        spec = importlib.util.spec_from_file_location(safe_name, str(file_path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        tools = getattr(module, "TOOLS", [])
        if not tools:
            file_path.unlink()
            return {"success": False, "data": None, "message": "Skill must define a TOOLS list"}

        # Sanitize JSON schemas — remove "required" from inside properties
        # (common LLM mistake: putting required:true on individual props instead of at object level)
        for tool in tools:
            params = tool.get("parameters", {})
            props = params.get("properties", {})
            for prop_name, prop_def in props.items():
                if isinstance(prop_def, dict):
                    prop_def.pop("required", None)

        tool_names = [t["name"] for t in tools]
        logger.info("Skill %s validated: %d tools (%s)", safe_name, len(tools), ", ".join(tool_names))

        # Register in the live skills_handler
        from skills_handler import _DISPATCH, _TOOL_DEFS
        for tool in tools:
            _DISPATCH[tool["name"]] = tool["handler"]
            _TOOL_DEFS.append({
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"],
            })

        return {
            "success": True,
            "data": {"skill_name": safe_name, "tools": tool_names, "file": str(file_path)},
            "message": "Skill **%s** created with %d tools: %s\nAvailable immediately." % (
                safe_name, len(tools), ", ".join(tool_names)
            ),
        }
    except Exception as e:
        # Clean up on failure
        if file_path.exists():
            file_path.unlink()
        return {"success": False, "data": None, "message": "Skill validation failed: %s" % str(e)}


async def list_skills(params: Dict[str, Any]) -> Dict:
    """List all installed skills and their tools."""
    from skills_handler import _TOOL_DEFS

    skill_files = sorted(SKILLS_DIR.glob("*.py"))
    skills = []
    for f in skill_files:
        if f.name.startswith("__"):
            continue
        skills.append(f.stem)

    lines = ["**%d skill modules installed, %d total tools:**\n" % (len(skills), len(_TOOL_DEFS))]
    for s in skills:
        module_tools = [t["name"] for t in _TOOL_DEFS if True]  # all registered
        lines.append("- `%s`" % s)

    lines.append("\n**All tools:**")
    for t in _TOOL_DEFS:
        lines.append("- `%s` — %s" % (t["name"], t["description"][:80]))

    return {
        "success": True,
        "data": {"modules": skills, "total_tools": len(_TOOL_DEFS)},
        "message": "\n".join(lines),
    }


async def delete_skill(params: Dict[str, Any]) -> Dict:
    """Delete a self-created skill. Cannot delete core skills."""
    skill_name = params.get("skill_name", "")
    safe_name = re.sub(r'[^a-z0-9_]', '_', skill_name.lower())

    protected = {"__init__", "web_search", "x_twitter", "email_skill", "intelligence", "self_evolve"}
    if safe_name in protected:
        return {"success": False, "data": None, "message": "Can't delete core skill: %s" % safe_name}

    file_path = SKILLS_DIR / ("%s.py" % safe_name)
    if not file_path.exists():
        return {"success": False, "data": None, "message": "Skill not found: %s" % safe_name}

    file_path.unlink()
    return {
        "success": True,
        "data": {"deleted": safe_name},
        "message": "Skill **%s** deleted. Restart needed to unregister tools." % safe_name,
    }


TOOLS = [
    {
        "name": "create_skill",
        "description": (
            "CREATE A NEW SKILL AT RUNTIME. Write Python code that defines async handler functions "
            "and a TOOLS list. The skill becomes immediately available. Use this when you need a "
            "capability that doesn't exist yet — API integrations, scrapers, processors, automations. "
            "The code MUST define: TOOLS = [{'name': str, 'description': str, 'handler': async_func, "
            "'parameters': dict}]. Each handler must be 'async def func(params: dict) -> dict' "
            "returning {'success': bool, 'data': any, 'message': str}."
        ),
        "handler": create_skill,
        "parameters": {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "Snake_case name for the skill (e.g., 'slack_notifier', 'reddit_scraper')",
                },
                "description": {
                    "type": "string",
                    "description": "What this skill does",
                },
                "code": {
                    "type": "string",
                    "description": (
                        "Complete Python code for the skill. Must import needed modules, define async handler "
                        "functions, and export a TOOLS list. Use httpx for HTTP, bs4 for HTML parsing. "
                        "Available imports: httpx, json, re, os, asyncio, bs4, duckduckgo_search."
                    ),
                },
            },
            "required": ["skill_name", "description", "code"],
        },
    },
    {
        "name": "list_skills",
        "description": "List all installed skill modules and their tools. Use to check what capabilities are available.",
        "handler": list_skills,
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "delete_skill",
        "description": "Delete a self-created skill module. Cannot delete core skills.",
        "handler": delete_skill,
        "parameters": {
            "type": "object",
            "properties": {
                "skill_name": {"type": "string", "description": "Name of the skill to delete"},
            },
            "required": ["skill_name"],
        },
    },
]
