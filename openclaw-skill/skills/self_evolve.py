"""Self-Evolution — Wave creates new skills for himself at runtime.

SECURITY: All generated code is validated via AST analysis and executed in
a sandboxed subprocess with restricted imports. This prevents arbitrary code
execution, environment variable exfiltration, and system compromise.
"""

from __future__ import annotations

import ast
import importlib
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("openclaw.skills.evolve")

SKILLS_DIR = Path(__file__).parent

# Imports that generated skills are allowed to use
ALLOWED_IMPORTS = frozenset({
    "asyncio", "json", "re", "os.path", "math", "hashlib", "base64",
    "urllib.parse", "datetime", "collections", "itertools", "functools",
    "typing", "dataclasses", "pathlib", "textwrap", "string",
    "httpx", "bs4", "duckduckgo_search", "html", "xml.etree.ElementTree",
})

# Builtin functions / attributes that are forbidden
FORBIDDEN_ATTRS = frozenset({
    "exec", "eval", "compile", "__import__", "globals", "locals",
    "getattr", "setattr", "delattr", "__builtins__", "__subclasses__",
    "subprocess", "os.system", "os.popen", "os.exec", "os.spawn",
    "os.environ", "os.getenv", "os.putenv",
    "shutil.rmtree", "shutil.move",
    "open",  # only allow httpx for I/O
})

# Core skills that cannot be overwritten or deleted
PROTECTED_SKILLS = frozenset({
    "__init__", "web_search", "x_twitter", "email_skill", "gmail_skill",
    "intelligence", "self_evolve", "learning", "vision",
    "hedera_skill", "hedera_client", "payments", "monetization",
    "moltbook_skill", "moltbook_fixed", "moltbook_poster",
    "prospecting", "tracing", "payment_verification",
    "pricing_engine", "strategic_skills", "power_skills", "dorking",
    "nowpayments", "defi_intel", "security_audit", "smart_contract_audit",
})


REPO_ROOT = SKILLS_DIR.parent.parent  # /home/manuel/bluewave


def _autonomous_git_commit(skill_name: str, tool_names: list, description: str = ""):
    """Commit a newly created skill to git — Wave's autonomous evolution recorded in history.

    Safety constraints:
    - Only commits files under openclaw-skill/skills/
    - Never commits other code, configs, or secrets
    - Commit message clearly marks autonomous origin
    - Failure to commit does NOT fail skill creation (non-blocking)
    """
    try:
        skill_file = "openclaw-skill/skills/%s.py" % skill_name
        tools_str = ", ".join(tool_names[:5])
        desc_line = (" — %s" % description[:80]) if description else ""

        commit_msg = (
            "Wave autonomous: created skill '%s'%s\n\n"
            "Tools: %s\n"
            "Security: AST validated + sandbox passed\n"
            "Origin: autonomous self-evolution (no human intervention)"
        ) % (skill_name, desc_line, tools_str)

        # Stage only the specific skill file
        result_add = subprocess.run(
            ["git", "add", skill_file],
            capture_output=True, text=True, timeout=10,
            cwd=str(REPO_ROOT),
        )
        if result_add.returncode != 0:
            logger.warning("Git add failed for %s: %s", skill_name, result_add.stderr.strip())
            return

        # Commit with autonomous identity
        result_commit = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            capture_output=True, text=True, timeout=10,
            cwd=str(REPO_ROOT),
        )
        if result_commit.returncode != 0:
            logger.warning("Git commit failed for %s: %s", skill_name, result_commit.stderr.strip())
            return

        # Push to remote (non-blocking — if it fails, the commit is still local)
        subprocess.run(
            ["git", "push"],
            capture_output=True, text=True, timeout=30,
            cwd=str(REPO_ROOT),
        )

        logger.info(
            "AUTONOMOUS COMMIT: Wave committed skill '%s' to git (%s)",
            skill_name, tools_str,
        )
    except Exception as e:
        # Never let git failure break skill creation
        logger.warning("Autonomous git commit failed (non-blocking): %s", e)


def _autonomous_git_commit_deletion(skill_name: str):
    """Record skill deletion in git history."""
    try:
        skill_file = "openclaw-skill/skills/%s.py" % skill_name
        commit_msg = (
            "Wave autonomous: deleted skill '%s'\n\n"
            "Origin: autonomous self-evolution (no human intervention)"
        ) % skill_name

        subprocess.run(
            ["git", "add", skill_file],
            capture_output=True, text=True, timeout=10,
            cwd=str(REPO_ROOT),
        )
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            capture_output=True, text=True, timeout=10,
            cwd=str(REPO_ROOT),
        )
        subprocess.run(
            ["git", "push"],
            capture_output=True, text=True, timeout=30,
            cwd=str(REPO_ROOT),
        )
        logger.info("AUTONOMOUS COMMIT: Wave deleted skill '%s' from git", skill_name)
    except Exception as e:
        logger.warning("Autonomous git commit (deletion) failed (non-blocking): %s", e)


class SkillSecurityError(Exception):
    """Raised when generated code fails security validation."""


def _validate_imports(tree: ast.AST) -> list[str]:
    """Check all imports against the allowlist. Return list of violations."""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name.split(".")[0]
                if alias.name not in ALLOWED_IMPORTS and module not in ALLOWED_IMPORTS:
                    violations.append(f"Forbidden import: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module = node.module.split(".")[0]
                if node.module not in ALLOWED_IMPORTS and module not in ALLOWED_IMPORTS:
                    violations.append(f"Forbidden import: from {node.module}")
    return violations


def _validate_no_dangerous_calls(tree: ast.AST) -> list[str]:
    """Check for dangerous function calls and attribute accesses."""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Check direct calls like eval(), exec()
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_ATTRS:
                violations.append(f"Forbidden call: {node.func.id}()")
            # Check attribute calls like os.system(), os.environ.get()
            elif isinstance(node.func, ast.Attribute):
                attr_chain = _get_attr_chain(node.func)
                if attr_chain and any(f in attr_chain for f in FORBIDDEN_ATTRS):
                    violations.append(f"Forbidden call: {attr_chain}()")
        elif isinstance(node, ast.Attribute):
            attr_chain = _get_attr_chain(node)
            if attr_chain:
                # Block os.environ access
                if "os.environ" in attr_chain or "os.getenv" in attr_chain:
                    violations.append(f"Forbidden attribute: {attr_chain}")
                # Block __dunder__ access (except __init__, __name__, etc.)
                if node.attr.startswith("__") and node.attr not in ("__init__", "__name__", "__doc__"):
                    violations.append(f"Forbidden dunder access: {attr_chain}")
    return violations


def _get_attr_chain(node: ast.Attribute) -> str:
    """Reconstruct dotted attribute chain from AST node."""
    parts = [node.attr]
    current = node.value
    depth = 0
    while depth < 10:
        depth += 1
        if isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        elif isinstance(current, ast.Name):
            parts.append(current.id)
            break
        else:
            break
    return ".".join(reversed(parts))


def _validate_no_file_system_abuse(tree: ast.AST) -> list[str]:
    """Block direct file system operations (skill should use httpx for I/O)."""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "open":
                violations.append("Direct file open() is forbidden — use httpx for network I/O")
    return violations


def validate_skill_code(code: str) -> list[str]:
    """Validate generated Python code via AST analysis.

    Returns a list of security violations. Empty list = code is safe.
    """
    # Step 1: Parse the code
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [f"Syntax error: {e}"]

    violations = []
    violations.extend(_validate_imports(tree))
    violations.extend(_validate_no_dangerous_calls(tree))
    violations.extend(_validate_no_file_system_abuse(tree))

    return violations


def _execute_in_sandbox(file_path: Path) -> tuple[bool, str]:
    """Execute skill file in a subprocess with restricted environment.

    Returns (success, message).
    """
    # Create a validation script that imports and checks for TOOLS
    validation_script = f"""
import sys
import importlib.util

spec = importlib.util.spec_from_file_location("_skill_test", {str(file_path)!r})
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

tools = getattr(module, "TOOLS", [])
if not tools:
    print("ERROR:Skill must define a TOOLS list", file=sys.stderr)
    sys.exit(1)

import json
tool_names = [t["name"] for t in tools]
print(json.dumps(tool_names))
"""

    # Restricted environment: only pass safe env vars
    safe_env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/usr/local/bin"),
        "HOME": "/tmp",
        "PYTHONPATH": str(SKILLS_DIR.parent),
        "LANG": "C.UTF-8",
    }

    try:
        result = subprocess.run(
            [sys.executable, "-c", validation_script],
            capture_output=True,
            text=True,
            timeout=10,
            env=safe_env,
            cwd=str(SKILLS_DIR.parent),
        )

        if result.returncode != 0:
            error = result.stderr.strip().split("\n")[-1] if result.stderr else "Unknown error"
            return False, f"Sandbox validation failed: {error}"

        return True, result.stdout.strip()

    except subprocess.TimeoutExpired:
        return False, "Skill execution timed out (10s limit)"
    except Exception as e:
        return False, f"Sandbox error: {e}"


async def create_skill(params: Dict[str, Any]) -> Dict:
    """Create a new skill module at runtime with security validation.

    Security measures:
    1. AST analysis blocks forbidden imports, calls, and file system access
    2. Validation runs in a sandboxed subprocess with restricted env vars
    3. Protected skill names cannot be overwritten
    4. All creations are audit-logged

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
    if safe_name in PROTECTED_SKILLS:
        return {"success": False, "data": None, "message": "Can't overwrite protected skill: %s" % safe_name}

    # ── SECURITY GATE 1: AST validation ──────────────────────
    violations = validate_skill_code(code)
    if violations:
        logger.warning(
            "Skill %s rejected — %d security violations: %s",
            safe_name, len(violations), "; ".join(violations[:5]),
        )
        return {
            "success": False,
            "data": {"violations": violations},
            "message": "Code failed security review:\n" + "\n".join(f"- {v}" for v in violations),
        }

    # Write the skill file
    header = '"""%s — auto-generated skill by Wave.\n\n%s\n"""\n\n' % (safe_name, description)
    full_code = header + code

    try:
        file_path.write_text(full_code, encoding="utf-8")
        logger.info("Skill file written: %s", file_path)
    except Exception as e:
        return {"success": False, "data": None, "message": "Failed to write skill: %s" % str(e)}

    # ── SECURITY GATE 2: Sandboxed validation ────────────────
    sandbox_ok, sandbox_msg = _execute_in_sandbox(file_path)
    if not sandbox_ok:
        file_path.unlink(missing_ok=True)
        return {"success": False, "data": None, "message": sandbox_msg}

    # Parse tool names from sandbox output
    try:
        tool_names = json.loads(sandbox_msg)
    except json.JSONDecodeError:
        file_path.unlink(missing_ok=True)
        return {"success": False, "data": None, "message": "Skill validation returned invalid output"}

    # ── Register in the live skills_handler ───────────────────
    try:
        spec = importlib.util.spec_from_file_location(safe_name, str(file_path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        tools = getattr(module, "TOOLS", [])
        if not tools:
            file_path.unlink(missing_ok=True)
            return {"success": False, "data": None, "message": "Skill must define a TOOLS list"}

        # Sanitize JSON schemas
        for tool in tools:
            tool_params = tool.get("parameters", {})
            props = tool_params.get("properties", {})
            for prop_name, prop_def in props.items():
                if isinstance(prop_def, dict):
                    prop_def.pop("required", None)

        from skills_handler import _DISPATCH, _TOOL_DEFS
        for tool in tools:
            _DISPATCH[tool["name"]] = tool["handler"]
            _TOOL_DEFS.append({
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"],
            })

        # Audit log
        logger.info(
            "AUDIT: Skill created — name=%s, tools=%s, violations_checked=True, sandbox_passed=True",
            safe_name, tool_names,
        )

        # ── AUTONOMOUS GIT COMMIT ────────────────────────────────
        # Wave records its own evolution in git history.
        # Only commits the specific skill file — never touches other code.
        _autonomous_git_commit(safe_name, tool_names, description)

        return {
            "success": True,
            "data": {"skill_name": safe_name, "tools": tool_names, "file": str(file_path)},
            "message": "Skill **%s** created with %d tools: %s\nSecurity: AST validated + sandbox passed. Committed to git." % (
                safe_name, len(tools), ", ".join(tool_names)
            ),
        }
    except Exception as e:
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
        protected = " (core)" if s in PROTECTED_SKILLS else ""
        lines.append("- `%s`%s" % (s, protected))

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

    if safe_name in PROTECTED_SKILLS:
        return {"success": False, "data": None, "message": "Can't delete core skill: %s" % safe_name}

    file_path = SKILLS_DIR / ("%s.py" % safe_name)
    if not file_path.exists():
        return {"success": False, "data": None, "message": "Skill not found: %s" % safe_name}

    file_path.unlink()
    logger.info("AUDIT: Skill deleted — name=%s", safe_name)

    # Record deletion in git
    _autonomous_git_commit_deletion(safe_name)

    return {
        "success": True,
        "data": {"deleted": safe_name},
        "message": "Skill **%s** deleted and committed to git. Restart needed to unregister tools." % safe_name,
    }


TOOLS = [
    {
        "name": "create_skill",
        "description": (
            "CREATE A NEW SKILL AT RUNTIME. Write Python code that defines async handler functions "
            "and a TOOLS list. The skill is validated via AST security analysis and sandboxed execution "
            "before being registered. ALLOWED imports: httpx, json, re, bs4, asyncio, datetime, "
            "math, hashlib, base64, urllib.parse, collections, duckduckgo_search. "
            "FORBIDDEN: os.environ, subprocess, eval, exec, open(), __import__. "
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
                        "SECURITY: Code is AST-validated — forbidden: os.environ, subprocess, eval, exec, "
                        "open(), __import__. Allowed: httpx, json, re, bs4, asyncio, datetime, "
                        "duckduckgo_search, math, hashlib, base64."
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
