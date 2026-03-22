#!/usr/bin/env python3
"""
skill_executor.py — Execute Wave skills from CLI

Called by Claude Engine (claude -p) via Bash tool:
  python3 skill_executor.py <skill_name> '<json_params>'

This bridges Claude CLI → Wave's 130+ skills without needing
the orchestrator API or Anthropic API key.

Usage:
  python3 skill_executor.py moltbook_post '{"submolt":"agents","title":"...","content":"..."}'
  python3 skill_executor.py web_search '{"query":"AI agents 2026"}'
  python3 skill_executor.py hn_top '{}'
  python3 skill_executor.py list_skills '{}'
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Set up environment
os.chdir(Path(__file__).parent)
sys.path.insert(0, str(Path(__file__).parent))

# Load env vars from .env if available
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and val and key not in os.environ:
                os.environ[key] = val


async def execute_skill(skill_name: str, params: dict) -> dict:
    """Execute a Wave skill by name."""
    from skills_handler import get_all_skill_tools, execute_skill as exec_skill, is_skill_tool

    if skill_name == "list_skills":
        tools = get_all_skill_tools()
        return {
            "success": True,
            "count": len(tools),
            "skills": [
                {"name": t["name"], "description": t.get("description", "")[:100]}
                for t in tools
            ],
        }

    if not is_skill_tool(skill_name):
        return {"success": False, "error": f"Unknown skill: {skill_name}"}

    try:
        result = await exec_skill(skill_name, params)
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: skill_executor.py <skill_name> [json_params]"}))
        sys.exit(1)

    skill_name = sys.argv[1]
    params = {}

    if len(sys.argv) > 2:
        try:
            params = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            # Try to parse as key=value pairs
            params = {"query": sys.argv[2]}

    result = asyncio.run(execute_skill(skill_name, params))
    print(json.dumps(result, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
